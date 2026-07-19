
<<<<<<< HEAD

=======
>>>>>>> 8853d97 (修改readme)
<div align="center">
  <h1>🧠 Advanced RAG System</h1>
  <p>
    <strong>生产级 Agentic RAG 智能问答系统</strong><br>
    自主决策 · 知识图谱 · 混合检索 · 流式输出 · 文档管理 · 生产级工程化
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/LangGraph-0.2-1c3c3c?logo=langchain" alt="LangGraph">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>
</div>

---

## 📖 项目简介

Advanced RAG System 是一个 **从零实现的工业级检索增强生成系统**，支持 **Agentic 智能体自主决策**、**知识图谱多跳推理**、**多路混合检索（向量 + BM25 + 图谱）**、**流式输出（SSE）**、**文档全生命周期管理** 以及 **多轮对话记忆**。

系统以 **LangGraph** 编排智能体流程，以 **FastAPI** 提供高性能异步服务，前端采用模块化 SPA 界面。项目强调 **可观测性、可扩展性、安全性与生产部署能力**，既可作为学习 RAG 技术的参考实现，也可作为企业知识库问答的原型基座，更是 AI 应用工程师求职的硬核作品。

---

## ✨ 核心功能

### 🧠 Agentic RAG – 自主决策闭环
- **自主规划**：LLM 根据用户问题动态生成工具调用计划，支持线性步骤与并行组。
- **工具调用**：集成 `local_search`（本地知识库）、`web_search`（联网搜索）、`graph_search`（知识图谱），并支持自定义扩展。
- **自我反思**：生成答案后自动评估质量，不满足则清空计划重试，最多重试可配置。
- **失败回退**：单工具调用自动重试，网络搜索失败自动降级到本地检索，保障流程不中断。
- **并行执行**：计划中的并行工具组使用线程池同时执行，提升响应速度。

### 🕸️ Graph RAG – 知识图谱多跳推理
- **实体关系抽取**：文档入库时，LLM 自动抽取三元组（subject-relation-object）构建知识图谱。
- **多跳检索**：支持实体查询、邻居遍历，回答实体关系类问题（如“张三的导师的毕业院校”）。
- **三路融合**：图谱检索与向量检索、BM25 检索统一通过 RRF 融合，互补优势。

### 🔍 多路混合检索 + 重排序
- **稠密向量检索**：基于 ChromaDB 的语义搜索。
- **稀疏关键词检索**：基于 BM25 的精确关键词匹配。
- **图谱检索**：结构化实体关系查询。
- **RRF 融合**：无需归一化的倒数秩融合算法，稳定合并多路结果。
- **重排序**：使用 Embedding 相似度对候选文档精排，提升答案相关性。

### 🌐 联网搜索
- 当本地知识不足时，Agent 可自主选择 DuckDuckGo 联网搜索，获得实时信息。
- 网络异常时自动回退至本地检索，确保可用性。

### 💬 多轮对话与记忆
- 携带最近 3 轮对话历史作为上下文，支持指代消解、连续追问。
- 前端自动维护对话历史，后端注入 Prompt 保持连贯。

### 📄 文档全生命周期管理
- 支持 **PDF / Markdown / TXT** 上传，自动解析、智能分块、去重入库。
- 上传任务异步执行，前端轮询进度，大文件不阻塞。
- 可选持久化向量库，重启不丢数据。

### ⚡ 流式输出
- 提供 SSE（Server-Sent Events）流式接口，答案逐字返回，体验类似 ChatGPT。

### 🛡️ 安全与健壮性
- 前端引入 **DOMPurify** 清洗 Markdown 输出，防止 XSS。
- 后端使用 `pydantic-settings` + `SecretStr` 保护 API Key。
- 全局异常中间件、请求级别日志追踪、输入校验。

### 📊 可观测性
- 结构化日志（`structlog`），支持 dev/prod 环境切换（JSON/Console）。
- 每个请求自动绑定 `request_id`，可追踪全链路。
- `/health` 端点检查所有外部依赖（ChromaDB、BM25、LLM API）。

### 🐳 生产部署
- `Dockerfile` + `docker-compose.yml` 一键启动。
- 支持挂载持久化目录，可快速集成 Redis 等缓存。

---

## 🏗️ 系统架构

```
用户交互 (Web UI)
        │
        ▼
┌─────────────────────────────────────────┐
│              FastAPI 路由层              │
│   /chat (Agentic)  /chat/stream  /upload │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│         LangGraph 智能体引擎             │
│                                         │
│   ┌──────┐   ┌──────────┐   ┌────────┐  │
│   │ Plan │──▶│ Tool Select │──▶│ Execute│  │
│   └──────┘   └──────────┘   │ (local, │  │
│        ▲                     │ web,    │  │
│        │                     │ graph)  │  │
│        │                     └────────┘  │
│        │                          │      │
│   ┌────┴─────┐              ┌─────▼────┐ │
│   │ Reflection│◀─────────────│ Generate │ │
│   └──────────┘              └──────────┘ │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│              检索 & 存储层               │
│  ┌──────────┐  ┌────────┐  ┌─────────┐  │
│  │ ChromaDB │  │  BM25  │  │ Graph   │  │
│  └──────────┘  └────────┘  │ (networkx)│  │
│                             └─────────┘  │
└─────────────────────────────────────────┘
```

**技术栈**：

| 层级 | 技术 / 组件 |
|------|-------------|
| LLM 服务 | 智谱 AI (GLM-4-Flash) |
| Embedding | 智谱 AI (Embedding-2) |
| 向量数据库 | ChromaDB |
| 稀疏检索 | BM25 (rank_bm25 + jieba) |
| 知识图谱 | networkx + LLM 三元组抽取 |
| 重排序 | Embedding 余弦相似度 |
| 流程编排 | LangGraph |
| API 框架 | FastAPI (异步) |
| 文档解析 | PyPDF, LangChain Document Loaders |
| 前端 | 原生 ES Module SPA (HTML/CSS/JS) |
| 日志 | structlog |
| 部署 | Docker / Docker Compose |

---

## 🚀 快速开始

### 1. 环境要求
- Python 3.11+
- pip
- Git
- (可选) Docker

### 2. 克隆仓库
```bash
git clone https://github.com/lingdugongsheng/rag.git
cd rag
```

### 3. 安装依赖
```bash
python -m venv ai
source ai/bin/activate   # Windows: ai\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置 API 密钥
```bash
cp .env.example .env
# 编辑 .env，填入你的智谱 AI API Key
```

### 5. 启动服务
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```
浏览器访问 `http://localhost:8000`，即可使用前端界面。

### 6. 使用 Docker 启动（可选）
```bash
docker compose up -d
```

---

## 📂 项目结构

```
rag/
├── api/                # FastAPI 路由、中间件、全局异常处理
│   ├── main.py         # 应用入口，lifespan 初始化存储与检索器
│   └── routes.py       # 接口路由 (/chat, /chat/stream, /upload, /task)
├── core/               # 核心配置与封装
│   ├── config.py       # 配置中心 (pydantic-settings)
│   ├── llm.py          # LLM & Embedding 工厂
│   ├── cache.py        # 缓存抽象 (MemoryCache + Redis 预留)
│   └── logger.py       # 结构化日志
├── storage/            # 底层存储
│   ├── vector_store.py # ChromaDB 封装
│   ├── bm25_index.py   # BM25 索引
│   └── graph_store.py  # 知识图谱存储 (networkx)
├── ingestion/          # 文档入库管道
│   ├── loaders.py      # 多格式加载 (PDF/MD/TXT)
│   ├── splitter.py     # 智能文本分块
│   ├── graph_builder.py# LLM 抽取三元组
│   └── pipeline.py     # 完整入库流程 (加载→分块→建图→向量化→入库)
├── retrieval/          # 检索模块
│   ├── searchers.py    # 混合检索器 (向量 + BM25 + 图谱)
│   ├── fusion.py       # RRF 融合算法
│   ├── reranker.py     # 重排序
│   ├── rewriter.py     # 查询改写
│   ├── context.py      # 上下文构建
│   ├── graph_retriever.py # 图谱检索器
│   └── web_search.py   # DuckDuckGo 网络搜索
├── generation/         # 生成模块
│   └── generator.py    # 同步 + 流式生成 (支持历史注入)
├── graphs/             # LangGraph 智能体图
│   ├── states.py       # AgentState 定义
│   ├── nodes.py        # 规划、工具、生成、反思等节点实现
│   └── agentic_rag.py  # 图编译与导出
├── static/             # 前端 SPA
│   ├── index.html
│   ├── styles.css
│   └── js/
│       ├── utils.js    # 工具函数
│       ├── api.js      # API 客户端 (流式/同步/上传)
│       ├── store.js    # 对话状态管理 (localStorage)
│       ├── renderer.js # UI 渲染 (消息、历史、滚动)
│       └── main.js     # 入口，事件绑定
├── docs/
│   └── DESIGN_DECISIONS.md  # 架构决策记录
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧩 使用指南

1. **上传文档**  
   点击左侧边栏「📄 上传文档」，选择 PDF / MD / TXT 文件。上传过程显示进度，完成后即可提问。

2. **开始对话**  
   在输入框输入问题，按 Enter 发送。系统会根据问题自动决定检索策略（本地/图谱/联网），并生成答案。  
   对话历史保存在左侧边栏，可随时切换或删除。

3. **多轮对话**  
   系统会记住最近 3 轮对话，支持指代（如“他”指代之前提到的人）和上下文追问。

4. **联网搜索**  
   当本地知识不足时，Agent 会自动调用 DuckDuckGo 搜索互联网信息，并融入回答。

---

## ⚙️ 配置项

所有配置均在 `.env` 文件中，主要参数：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | 智谱 AI API 密钥 | - |
| `LLM_BASE_URL` | 智谱 API 地址 | `https://open.bigmodel.cn/api/paas/v4/` |
| `LLM_MODEL` | 对话模型 | `glm-4-flash` |
| `EMBEDDING_MODEL` | 嵌入模型 | `embedding-2` |
| `ENVIRONMENT` | 运行环境 (dev/production) | `dev` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `RETRIEVAL_TOP_K` | 检索召回数量 | `10` |
| `MAX_RETRIES` | 反思最大重试次数 | `2` |
| `WEB_SEARCH_ENABLED` | 是否启用联网搜索 | `True` |
| `TOOL_RETRY_ATTEMPTS` | 工具调用失败重试次数 | `2` |

更多配置见 `core/config.py`。

---

## 🗺️ 路线图

- [x] 基础 RAG (向量 + BM25 + 重排序)
- [x] 查询改写
- [x] 流式输出 (SSE)
- [x] 文档上传与管理
- [x] 多轮对话记忆
- [x] Agentic RAG (规划、工具调用、反思)
- [x] 复杂任务分解与并行执行
- [x] 工具异常重试与回退
- [x] Graph RAG (知识图谱构建与多跳推理)
- [x] 生产级工程化 (Docker、日志、中间件、健康检查)
- [x] 前端模块化 SPA + XSS 防护
- [ ] RAGAS 自动评估体系
- [ ] 多模态文档解析 (图片、表格)
- [ ] 用户反馈收集与 RLHF 微调
- [ ] 认证鉴权与多租户

---

## 📚 设计决策

项目涉及多种技术选型和架构权衡，详见 [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md)，包括为什么选择 ChromaDB、RRF 融合、LangGraph、Graph RAG、缓存抽象等。

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

---

**如果觉得不错，欢迎 Star ⭐ 支持一下！**
```
