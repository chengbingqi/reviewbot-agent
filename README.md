# 🤖 ReviewBot: 基于 LangGraph 的 DevOps 自动化代码审查智能体

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)
![FastAPI](https://img.shields.io/badge/FastAPI-Streaming-009688)
![React Ink](https://img.shields.io/badge/React_Ink-CLI_TUI-61DAFB)

ReviewBot 是一个面向 DevOps 场景的自动化代码审查与测试多智能体（Multi-Agent）系统。本项目采用 `Plan-Execute` 与 `ReAct` 架构，结合本地 RAG（检索增强生成）记忆库，能够自动拆解代码审查任务，并流式输出结合企业内部规范的专业审查报告。

## ✨ 核心特性

- **🧠 多智能体协同编排**：基于 LangChain 和 LangGraph 构建。包含 PlannerAgent（结构化任务规划）、CoordinatorAgent（任务调度分发）、以及专职子智能体（静态规范扫描、安全漏洞检测）。
- **📚 领域知识增强 (RAG)**：集成 `HuggingFace` 本地轻量级向量模型与 `SQLite-Vec` 向量数据库。在审查代码前，智能体会自动检索本地库中的“企业内部开发规范”，确保审查建议贴合实际业务场景。
- **⚡ 流式 API 微服务**：后端采用 FastAPI 框架，利用 Server-Sent Events (SSE) 技术将 LangGraph 复杂工作流的底层执行状态实时推送到客户端。
- **💻 沉浸式终端交互 (CLI TUI)**：前端摒弃传统网页，使用 TypeScript 结合 React Ink 跨界开发，打造具备动态动画与流式 Markdown 渲染的极客风终端界面。

## 🛠️ 技术选型

* **大语言模型**：DeepSeek API (兼容 OpenAI 接口标准，利用 `JsonOutputParser` 实现高稳定性结构化输出)
* **智能体框架**：Python, LangChain, LangGraph
* **向量检索与持久化**：SQLite, SQLite-Vec, sentence-transformers
* **后端服务**：FastAPI, Uvicorn, Pydantic
* **前端展示**：TypeScript, React, Ink, tsx

## 🚀 快速开始

### 1. 环境准备

确保本地已安装 **Python 3.10+** 和 **Node.js (LTS)**。建议使用 Conda 创建独立的 Python 虚拟环境。

```bash
# 克隆仓库
git clone [https://github.com/你的用户名/reviewbot-agent.git](https://github.com/你的用户名/reviewbot-agent.git)
cd reviewbot-agent

# 创建并激活虚拟环境 (可选)
conda create -n reviewbot python=3.10 -y
conda activate reviewbot
2. 配置后端 (Python)
安装核心依赖包并配置大模型 API 密钥：
# 安装 Python 依赖
pip install langchain langgraph sqlite-vec fastapi uvicorn langchain-openai pydantic sentence-transformers langchain-huggingface requests
# 初始化本地知识库 (首次运行会自动下载 HuggingFace 轻量级模型)
python rag_db.py
注意：请在 core_graph.py 中将 os.environ["OPENAI_API_KEY"] 替换为你自己的 DeepSeek/OpenAI API 密钥。
3. 配置前端 (Node.js)
进入前端 TUI 目录并安装依赖：
cd cli-tui
npm install
4. 运行系统
本项目采用前后端分离架构，需要开启两个终端窗口。

终端 1：启动 FastAPI 后端服务
# 在项目根目录下运行
python api_server.py
# 服务将运行在 [http://127.0.0.1:8000](http://127.0.0.1:8000)
终端 2：启动交互式命令行界面
# 在 cli-tui 目录下运行
npx tsx ui.tsx

📁 项目结构
reviewbot-agent/
├── core_graph.py       # LangGraph 多智能体状态机与核心工作流定义
├── rag_db.py           # 本地向量模型初始化与 SQLite-Vec 检索逻辑
├── api_server.py       # FastAPI 后端服务与 SSE 流式推送接口
├── test_client.py      # Python 命令行测试脚本
├── reviewbot_memory.db # SQLite 本地持久化与向量数据库文件
└── cli-tui/            # TypeScript 终端前端界面目录
    ├── package.json    # Node.js 依赖配置 (启用 ESM 规范)
    ├── tsconfig.json   # TypeScript 编译配置
    └── ui.tsx          # React Ink 核心渲染逻辑与状态管理