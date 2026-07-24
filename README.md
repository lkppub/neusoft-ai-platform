# 东软智慧商务AI助手平台

基于Python的AI应用开发实训项目 —— 企业级AI智能应用平台

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + Pinia + Vue Router + Axios + Element Plus + ECharts |
| 后端 | FastAPI + SQLAlchemy (async) + Pydantic v2 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 缓存 | Redis |
| AI引擎 | DeepSeek API (推荐) / OpenAI兼容接口 |
| AI框架 | LangChain + LangGraph |
| 向量数据库 | Chroma (嵌入式) |
| 低代码 | Dify (可选) |
| 部署 | Docker Compose |

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 20+
- Docker (可选，用于容器化部署)

### 1. 克隆并配置环境

```bash
# 复制环境变量文件（已预配置，可直接使用）
cp .env.example .env

# 编辑 .env，填入 DeepSeek API Key（可选，默认使用Mock模式）
# AI_PROVIDER=mock  -> 使用模拟AI，无需API Key
# AI_PROVIDER=deepseek -> 使用真实DeepSeek API
```

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库并创建种子数据
python -m app.seed

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看Swagger API文档。

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173 打开前端界面。

### 4. Docker Compose 一键部署

```bash
docker compose up -d
```

服务启动后访问 http://localhost 即可。

## 演示账号

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| `admin` | `123456` | 管理员 | 系统管理、用户管理、AI配置、查看报告 |
| `cs_staff` | `123456` | 客服人员 | 工单管理、AI辅助回复、FAQ维护 |
| `enterprise` | `123456` | 企业用户 | AI对话、知识库问答、提交工单 |
| `decision` | `123456` | 决策者 | 数据大屏、统计分析 |

## 功能模块

### 企业用户端
- 🤖 **AI智能对话助手**：多轮对话、SSE流式输出、上下文记忆、Markdown渲染
- 📚 **知识库问答**：RAG检索增强生成、文档上传、Chroma向量存储、来源引用
- 🎤 **语音交互**：语音转文字、文字转语音

### 客服人员端
- 📋 **智能工单管理**：AI自动分类、AI回复建议、工单状态跟踪
- 📝 **FAQ管理**：常见问题维护、分类管理
- 📄 **回复模板**：模板创建、变量替换、一键使用

### 管理员端
- 👥 **用户管理**：用户CRUD、角色分配、权限控制
- 📁 **知识库管理**：文档上传、分段配置、索引管理
- ⚙️ **AI配置管理**：模型选择、提示词模板编辑、参数调优
- 📊 **对话记录查看**：所有对话记录浏览与统计
- 📈 **智能分析报告**：AI生成运营分析报告

### 决策者端（数据大屏）
- 📊 **KPI概览卡片**：咨询量、工单量、解决率、满意度
- 🥧 **分类分布饼图**：问题类型分布
- 📈 **趋势折线图**：满意度和咨询量趋势
- 💡 **AI洞察卡片**：AI自动识别关键趋势
- 🔥 **热门话题**：高频FAQ关键词

## AI架构

```
用户输入 → FastAPI → LangGraph多Agent协作
                     ├── 分类Agent (意图识别)
                     ├── 查询Agent (知识库检索)
                     ├── 回复Agent (生成回复)
                     └── 质检Agent (质量审查)

RAG流程: 文档上传 → 文本分割 → 向量嵌入 → Chroma存储 → 相似度检索 → AI生成回复
```

## 项目结构

```
├── backend/           # FastAPI后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── core/              # 配置、安全、数据库
│   │   ├── models/            # SQLAlchemy数据模型
│   │   ├── schemas/           # Pydantic请求/响应模型
│   │   ├── api/v1/            # REST API路由
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── ai/            # AI Provider (DeepSeek/Mock)
│   │   │   ├── knowledge/     # RAG、向量存储、文档处理
│   │   │   ├── voice/         # 语音服务
│   │   │   └── analytics/     # 统计分析
│   │   └── agents/            # LangGraph多Agent
│   └── requirements.txt
├── frontend/          # Vue3前端
│   └── src/
│       ├── api/               # Axios API模块
│       ├── stores/            # Pinia状态管理
│       ├── router/            # Vue Router路由
│       ├── composables/       # 可复用组合式函数
│       ├── layouts/           # 布局组件
│       ├── views/             # 页面视图
│       └── components/        # UI组件
├── docker/            # Docker配置文件
│   └── nginx/nginx.conf
├── docker-compose.yml # Docker Compose编排
└── .env               # 环境变量
```

## API端点概览

所有API位于 `/api/v1/` 下：

- **认证**: `/auth` — 注册、登录、刷新令牌、个人信息
- **对话**: `/conversations` — CRUD + SSE流式消息
- **知识库**: `/knowledge` — 文档上传、RAG查询、FAQ管理
- **工单**: `/tickets` — 工单管理、AI分类、AI回复建议
- **模板**: `/templates` — 回复模板CRUD
- **管理**: `/admin` — 用户管理、AI配置、提示词、报告
- **仪表盘**: `/dashboard` — KPI概览、趋势图、洞察
- **语音**: `/voice` — 语音识别、语音合成
- **智能体**: `/agent` — 单Agent对话、多Agent分析

## 切换AI模式

在 `.env` 中修改：

```env
# Mock模式（无需API Key，返回模拟回复）
AI_PROVIDER=mock

# DeepSeek模式（需要API Key）
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-key
```

## 许可

本实训项目仅用于教学目的。


## 开始

uvicorn app.main:app --reload --port 8000
npm run dev