from pathlib import Path


PROMPT_DIR = Path(__file__).parent / "prompts"


FALLBACK_PROMPTS = {
    "planner": (
        "You are a senior code review planner. Return JSON only. "
        "Choose tasks from style_check and security_check. "
        "Schema: {\"tasks\": [\"style_check\", \"security_check\"]}."
    ),
    "style_checker": (
        "You are a Python style reviewer. Use the Ruff result when available, "
        "then explain the most important style or maintainability issues briefly."
    ),
    "security_scanner": (
        "You are a Python security reviewer. Use the Bandit result and RAG rules "
        "when available. Identify concrete security risks and practical fixes."
    ),
    "summary": (
        "Write a concise Markdown code review report. Include Tool Summary and "
        "Reference Rules sections when data is available."
    ),
}


def load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return FALLBACK_PROMPTS[name]
