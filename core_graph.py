import os
from rag_db import init_rag_db, search_similar_knowledge
from langchain_core.output_parsers import JsonOutputParser
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

# ==========================================
# 0. 配置大模型 API (这里以兼容 OpenAI 格式的 DeepSeek 为例)
# 你需要替换成你自己的 API_KEY 和对应的 BASE_URL
# ==========================================
os.environ["OPENAI_API_KEY"] = "sk-10a8539439d04ded8d9c230a6fdf3eef" 
os.environ["OPENAI_API_BASE"] = "https://api.deepseek.com/v1" # 如果用原生OpenAI，删掉这行

# 初始化 LLM
llm = ChatOpenAI(model="deepseek-chat", temperature=0) # 审查代码需要严谨，temperature 设为 0

# ==========================================
# 1. 定义状态 (保持不变)
# ==========================================
class AgentState(TypedDict):
    code_snippet: str
    plan: List[str]
    current_task: str
    review_results: List[str]
    final_report: str

# ==========================================
# 1.5 定义 Planner 的输出结构
# ==========================================
class PlanOutput(BaseModel):
    tasks: List[str] = Field(
        description="需要执行的任务列表，只能从以下选项中选择：['style_check', 'security_check']"
    )

# ==========================================
# 2. 升级智能体节点 (Nodes) - 接入真实 LLM
# ==========================================

def planner_node(state: AgentState):
    print("🧠 [PlannerAgent] 正在呼叫大模型分析代码并制定计划...")
    code = state["code_snippet"]
    
    # 1. 实例化通用 JSON 解析器，并绑定我们的 PlanOutput 结构
    parser = JsonOutputParser(pydantic_object=PlanOutput)
    
    # 2. 修改提示词：把解析器自动生成的“格式指令”塞进系统提示词中
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深的 DevOps 架构师。请分析以下代码，决定需要进行哪些审查。目前我们支持的审查工具只有 'style_check' (规范检查) 和 'security_check' (安全扫描)。如果代码涉及数据处理或变量定义，请加入 'style_check'；如果涉及密码、鉴权、数据库，请加入 'security_check'。\n\n必须严格按照以下 JSON 格式输出：\n{format_instructions}"),
        ("user", "代码如下：\n{code}")
    ])
    
    # 3. 重新组装 Chain：Prompt -> LLM -> JSON 解析器
    planner_chain = prompt | llm | parser
    
    # 4. 执行时传入所需的变量
    try:
        result = planner_chain.invoke({
            "code": code,
            "format_instructions": parser.get_format_instructions()
        })
        # 解析器返回的是一个字典，我们直接提取 'tasks' 列表
        state["plan"] = result["tasks"]
        print(f"   -> 制定计划: {state['plan']}")
    except Exception as e:
        print(f"   ❌ 解析大模型输出失败: {e}")
        state["plan"] = [] # 解析失败时的兜底逻辑
        
    return state

def coordinator_node(state: AgentState):
    print("👔 [CoordinatorAgent] 正在分配任务...")
    if state["plan"]:
        state["current_task"] = state["plan"].pop(0) 
        print(f"   -> 当前委派任务: {state['current_task']}")
    else:
        state["current_task"] = "done"
    return state

# 静态分析和安全扫描节点暂不接入真实工具，我们先用简单逻辑模拟，后续步骤再加
def style_checker_node(state: AgentState):
    print("🔍 [静态分析智能体] 正在检查代码规范...")
    if "review_results" not in state:
        state["review_results"] = []
    
    if "def " in state["code_snippet"] and ":" in state["code_snippet"]:
        # 简单模拟：让 LLM 帮忙看一眼规范
        response = llm.invoke(f"请用一句话指出这段代码的命名或格式不规范之处（如果没有则说'无'）：{state['code_snippet']}")
        state["review_results"].append(f"规范检查：{response.content}")
    return state

def security_scanner_node(state: AgentState):
    print("🛡️ [安全扫描智能体] 正在扫描安全漏洞...")
    if "review_results" not in state:
        state["review_results"] = []
    
    code = state["code_snippet"]
    
    # --- RAG 检索环节 ---
    print("   -> 正在检索本地项目规范记忆库...")
    db = init_rag_db()
    # 根据当前代码去搜寻相关的内部规范
    context_list = search_similar_knowledge(db, code, limit=1)
    context = context_list[0] if context_list else "无特定内部规范"
    print(f"   -> 检索到背景知识: {context}")
    
    # --- 结合记忆生成审查意见 ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个代码安全审计专家。请结合【内部背景知识】，指出下面代码的安全漏洞。\n\n【内部背景知识】\n{context}"),
        ("user", "代码如下：\n{code}")
    ])
    
    security_chain = prompt | llm
    response = security_chain.invoke({
        "context": context,
        "code": code
    })
    
    state["review_results"].append(f"安全扫描：{response.content}")
    return state

def summary_node(state: AgentState):
    print("📝 [SummaryAgent] 正在呼叫大模型生成最终报告...")
    results_str = "\n".join(state["review_results"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个负责代码审查的技术主管。请根据以下子智能体收集到的问题，用 Markdown 格式写一份专业、语气温和的代码审查报告。"),
        ("user", "原始代码：\n{code}\n\n审查问题汇总：\n{results}")
    ])
    
    summary_chain = prompt | llm
    response = summary_chain.invoke({
        "code": state["code_snippet"],
        "results": results_str
    })
    
    state["final_report"] = response.content
    return state

# ==========================================
# 3. 路由逻辑与构建图 (保持不变)
# ==========================================
def route_task(state: AgentState) -> str:
    task = state.get("current_task")
    if task == "style_check": return "style_checker"
    elif task == "security_check": return "security_scanner"
    return "summary" 

workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("style_checker", style_checker_node)
workflow.add_node("security_scanner", security_scanner_node)
workflow.add_node("summary", summary_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "coordinator")
workflow.add_conditional_edges("coordinator", route_task, {"style_checker": "style_checker", "security_scanner": "security_scanner", "summary": "summary"})
workflow.add_edge("style_checker", "coordinator")
workflow.add_edge("security_scanner", "coordinator")
workflow.add_edge("summary", END)

app = workflow.compile()

# ==========================================
# 4. 运行测试
# ==========================================
if __name__ == "__main__":
    print("🚀 启动 ReviewBot (LLM驱动版) 工作流测试...\n")
    
    test_code = """
def ConnectDatabase(user, pwd):
    # connecting to db
    connection_string = f"mysql://{user}:{pwd}@localhost/db"
    return connection_string
    """
    
    initial_state = AgentState(
        code_snippet=test_code,
        plan=[], current_task="", review_results=[], final_report=""
    )
    
    final_state = app.invoke(initial_state)
    
    print("\n✅ 工作流执行完毕！最终输出：\n")
    print(final_state["final_report"])