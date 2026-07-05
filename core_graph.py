import time
from typing import Any, TypedDict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import NotRequired

from config import ConfigError, get_config, require_api_key
from logging_config import logger
from prompt_loader import load_prompt
from rag_db import init_rag_db, search_similar_knowledge
from tools import scan_python_code, scan_python_files


class AgentState(TypedDict):
    code_snippet: str
    plan: list[str]
    current_task: str
    review_results: list[str]
    final_report: str
    errors: NotRequired[list[dict[str, str]]]
    rag_results: NotRequired[list[dict[str, Any]]]
    tool_results: NotRequired[dict[str, dict[str, Any]]]
    timings: NotRequired[dict[str, float]]
    review_files: NotRequired[list[dict[str, str]]]


class PlanOutput(BaseModel):
    tasks: list[str] = Field(
        description="Tasks to execute. Allowed values: style_check, security_check."
    )


def create_initial_state(code: str, review_files: list[dict[str, str]] | None = None) -> AgentState:
    return {
        "code_snippet": code,
        "plan": [],
        "current_task": "",
        "review_results": [],
        "final_report": "",
        "errors": [],
        "rag_results": [],
        "tool_results": {},
        "timings": {},
        "review_files": review_files or [],
    }


def _append_error(state: AgentState, node: str, message: str, exc: Exception | None = None) -> None:
    error = str(exc) if exc else message
    state.setdefault("errors", []).append({"node": node, "message": message, "error": error})
    logger.warning("%s: %s%s", node, message, f" error={error}" if exc else "")


def _record_timing(state: AgentState, node: str, started_at: float) -> None:
    elapsed = round(time.perf_counter() - started_at, 4)
    state.setdefault("timings", {})[node] = elapsed
    logger.info("node=%s elapsed_seconds=%s", node, elapsed)


def _scan_state_files(state: AgentState) -> dict[str, dict[str, Any]]:
    cfg = get_config()
    review_files = state.get("review_files") or []
    if review_files:
        return scan_python_files(review_files, timeout_seconds=cfg.tool_timeout_seconds)
    return scan_python_code(state["code_snippet"], timeout_seconds=cfg.tool_timeout_seconds)


def get_llm() -> ChatOpenAI:
    cfg = get_config()
    api_key = require_api_key()
    kwargs: dict[str, Any] = {
        "model": cfg.model_name,
        "temperature": 0,
        "api_key": api_key,
    }
    if cfg.openai_api_base:
        kwargs["base_url"] = cfg.openai_api_base
    return ChatOpenAI(**kwargs)


def planner_node(state: AgentState) -> AgentState:
    node = "planner"
    started_at = time.perf_counter()
    logger.info("node=%s start", node)
    try:
        parser = JsonOutputParser(pydantic_object=PlanOutput)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    load_prompt("planner") + "\n\nFormat instructions:\n{format_instructions}",
                ),
                ("user", "Code:\n{code}"),
            ]
        )
        result = (prompt | get_llm() | parser).invoke(
            {
                "code": state["code_snippet"],
                "format_instructions": parser.get_format_instructions(),
            }
        )
        tasks = [task for task in result.get("tasks", []) if task in {"style_check", "security_check"}]
        state["plan"] = tasks or ["style_check", "security_check"]
    except ConfigError as exc:
        _append_error(state, node, "LLM configuration missing; using default review plan.", exc)
        state["plan"] = ["style_check", "security_check"]
    except Exception as exc:
        _append_error(state, node, "Planning failed; using default review plan.", exc)
        state["plan"] = ["style_check", "security_check"]
    finally:
        _record_timing(state, node, started_at)
    return state


def coordinator_node(state: AgentState) -> AgentState:
    node = "coordinator"
    started_at = time.perf_counter()
    logger.info("node=%s start", node)
    if state["plan"]:
        state["current_task"] = state["plan"].pop(0)
    else:
        state["current_task"] = "done"
    _record_timing(state, node, started_at)
    return state


def _format_tool_result(name: str, result: dict[str, Any] | None) -> str:
    if not result:
        return f"### {name.title()}\n- Status: skipped\n- Findings: no result"
    output = result.get("stdout") or result.get("stderr") or result.get("message") or "No findings."
    output = output[:3000]
    return (
        f"### {name.title()}\n"
        f"- Status: {result.get('status')}\n"
        f"- Return code: {result.get('returncode')}\n"
        f"- Findings:\n```text\n{output}\n```"
    )


def style_checker_node(state: AgentState) -> AgentState:
    node = "style_checker"
    started_at = time.perf_counter()
    logger.info("node=%s start", node)
    try:
        state["tool_results"] = _scan_state_files(state)
        ruff_result = state["tool_results"].get("ruff")
        logger.info("ruff status=%s", ruff_result.get("status") if ruff_result else "missing")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", load_prompt("style_checker")),
                ("user", "Code:\n{code}\n\nRuff result:\n{ruff_result}"),
            ]
        )
        try:
            response = (prompt | get_llm()).invoke(
                {"code": state["code_snippet"], "ruff_result": _format_tool_result("ruff", ruff_result)}
            )
            state["review_results"].append(f"Style review:\n{response.content}")
        except ConfigError as exc:
            _append_error(state, node, "LLM style review skipped because API key is missing.", exc)
            state["review_results"].append(_format_tool_result("ruff", ruff_result))
        except Exception as exc:
            _append_error(state, node, "LLM style review failed; keeping Ruff result.", exc)
            state["review_results"].append(_format_tool_result("ruff", ruff_result))
    except Exception as exc:
        _append_error(state, node, "Style check failed.", exc)
    finally:
        _record_timing(state, node, started_at)
    return state


def security_scanner_node(state: AgentState) -> AgentState:
    node = "security_scanner"
    started_at = time.perf_counter()
    logger.info("node=%s start", node)
    try:
        cfg = get_config()
        if "tool_results" not in state or not state["tool_results"]:
            state["tool_results"] = _scan_state_files(state)
        bandit_result = state["tool_results"].get("bandit")
        logger.info("bandit status=%s", bandit_result.get("status") if bandit_result else "missing")

        try:
            db = init_rag_db(cfg.rag_db_path)
            state["rag_results"] = search_similar_knowledge(
                db, state["code_snippet"], top_k=cfg.rag_top_k
            )
        except Exception as exc:
            _append_error(state, node, "RAG retrieval failed; fallback to LLM-only review.", exc)
            state["rag_results"] = []

        rag_context = "\n".join(
            f"- {item.get('source', 'internal-rules')}: "
            f"{item.get('title') or item.get('rule_id') or item.get('content')}"
            for item in state.get("rag_results", [])
        ) or "No RAG rule hit."

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", load_prompt("security_scanner")),
                (
                    "user",
                    "Code:\n{code}\n\nBandit result:\n{bandit_result}\n\nRAG rules:\n{rag_context}",
                ),
            ]
        )
        try:
            response = (prompt | get_llm()).invoke(
                {
                    "code": state["code_snippet"],
                    "bandit_result": _format_tool_result("bandit", bandit_result),
                    "rag_context": rag_context,
                }
            )
            state["review_results"].append(f"Security review:\n{response.content}")
        except ConfigError as exc:
            _append_error(state, node, "LLM security review skipped because API key is missing.", exc)
            state["review_results"].append(_format_tool_result("bandit", bandit_result))
        except Exception as exc:
            _append_error(state, node, "LLM security review failed; keeping Bandit and RAG results.", exc)
            state["review_results"].append(_format_tool_result("bandit", bandit_result))
    except Exception as exc:
        _append_error(state, node, "Security scan failed.", exc)
    finally:
        _record_timing(state, node, started_at)
    return state


def _tool_summary_markdown(state: AgentState) -> str:
    tool_results = state.get("tool_results", {})
    return "\n\n".join(
        [
            "## Tool Summary",
            _format_tool_result("ruff", tool_results.get("ruff")),
            _format_tool_result("bandit", tool_results.get("bandit")),
        ]
    )


def _rag_markdown(state: AgentState) -> str:
    rag_results = state.get("rag_results", [])
    if not rag_results:
        return "## Reference Rules\n\n- No RAG rule hit."
    lines = ["## Reference Rules"]
    for item in rag_results:
        label = item.get("title") or item.get("rule_id") or "Untitled rule"
        distance = item.get("distance")
        suffix = f" (distance: {distance:.4f})" if isinstance(distance, (float, int)) else ""
        lines.append(f"- {item.get('source', 'internal-rules')}: {label}{suffix}")
    return "\n".join(lines)


def _fallback_report(state: AgentState) -> str:
    sections = [
        "# Code Review Report",
        "## Review Results",
        "\n\n".join(state.get("review_results", [])) or "No review result was generated.",
        _tool_summary_markdown(state),
        _rag_markdown(state),
    ]
    if state.get("errors"):
        sections.append("## Recoverable Errors")
        sections.extend(f"- {err['node']}: {err['message']}" for err in state["errors"])
    return "\n\n".join(sections)


def summary_node(state: AgentState) -> AgentState:
    node = "summary"
    started_at = time.perf_counter()
    logger.info("node=%s start", node)
    try:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", load_prompt("summary")),
                (
                    "user",
                    "Original code:\n{code}\n\nReview results:\n{results}\n\n"
                    "Tool summary:\n{tool_summary}\n\nRAG rules:\n{rag_rules}",
                ),
            ]
        )
        try:
            response = (prompt | get_llm()).invoke(
                {
                    "code": state["code_snippet"],
                    "results": "\n\n".join(state.get("review_results", [])),
                    "tool_summary": _tool_summary_markdown(state),
                    "rag_rules": _rag_markdown(state),
                }
            )
            state["final_report"] = (
                response.content
                + "\n\n"
                + _tool_summary_markdown(state)
                + "\n\n"
                + _rag_markdown(state)
            )
        except ConfigError as exc:
            _append_error(state, node, "LLM summary skipped because API key is missing.", exc)
            state["final_report"] = _fallback_report(state)
        except Exception as exc:
            _append_error(state, node, "LLM summary failed; using fallback report.", exc)
            state["final_report"] = _fallback_report(state)
    finally:
        logger.info("final_report_generated=%s", bool(state.get("final_report")))
        _record_timing(state, node, started_at)
    return state


def route_task(state: AgentState) -> str:
    task = state.get("current_task")
    if task == "style_check":
        return "style_checker"
    if task == "security_check":
        return "security_scanner"
    return "summary"


workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("style_checker", style_checker_node)
workflow.add_node("security_scanner", security_scanner_node)
workflow.add_node("summary", summary_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "coordinator")
workflow.add_conditional_edges(
    "coordinator",
    route_task,
    {
        "style_checker": "style_checker",
        "security_scanner": "security_scanner",
        "summary": "summary",
    },
)
workflow.add_edge("style_checker", "coordinator")
workflow.add_edge("security_scanner", "coordinator")
workflow.add_edge("summary", END)

app = workflow.compile()


if __name__ == "__main__":
    demo_code = """
def connect_database(user, pwd):
    connection_string = f"mysql://{user}:{pwd}@localhost/db"
    return connection_string
"""
    final_state = app.invoke(create_initial_state(demo_code))
    print(final_state["final_report"])
