import json
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 引入我们写好的智能体工作流和状态定义
from core_graph import app as agent_workflow, AgentState

# 创建 FastAPI 应用
app = FastAPI(title="ReviewBot API Server")

# 定义前端传过来的数据格式：只需要传一段代码字符串
class CodeRequest(BaseModel):
    code: str

# 核心流式处理函数 (SSE 生成器)
def stream_agent_execution(code: str):
    # 1. 初始化状态
    initial_state = AgentState(
        code_snippet=code, plan=[], current_task="", review_results=[], final_report=""
    )
    
    # 2. agent_workflow.stream() 会在每个节点执行完后，吐出当前的状态
    for output in agent_workflow.stream(initial_state):
        # output 类似于 {"planner": {"plan": [...]}}，我们提取出节点名字
        for node_name, state_update in output.items():
            # 构造一条进度消息
            progress_msg = {
                "status": "processing", 
                "message": f"🤖 节点 [{node_name}] 执行完毕..."
            }
            # yield 关键字配合特定格式发送 SSE 数据流
            yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
            
    # 3. 整个图跑完后，最后一步肯定在 summary 节点，我们提取出最终报告
    final_report = state_update.get("final_report", "抱歉，未生成报告。")
    final_msg = {
        "status": "done", 
        "report": final_report
    }
    yield f"data: {json.dumps(final_msg, ensure_ascii=False)}\n\n"

# 开放一个 /review 的 POST 接口
@app.post("/review")
def review_code_endpoint(request: CodeRequest):
    # 返回流式响应，前端可以像接收直播数据一样持续获取进度
    return StreamingResponse(
        stream_agent_execution(request.code), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    # 启动服务器，运行在本地的 8000 端口
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000)