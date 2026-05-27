# Moxo Agent

AI 驱动的工作流生成器，通过 LLM Function Calling 将自然语言转换为结构化的工作流 JSON 定义，支持多轮对话迭代修改工作流。

## 功能特性

- **自然语言生成工作流** — 用自然语言描述需求，LLM 自动拆解为结构化的操作步骤
- **多轮对话迭代** — 在已有工作流基础上插入、删除、更新、重排步骤
- **插件化 Action 系统** — 内置表单提交、审批、邮件通知、待办四种类型，支持自定义扩展
- **OpenAI 兼容** — 可对接任何 OpenAI 兼容的 LLM API（DeepSeek、OpenAI、本地模型等）
- **会话管理** — 基于 Session 的上下文保持，支持多用户并行

## 快速开始

### 前置要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd moxo-agent

# 安装依赖
uv sync --all-extras
```

### 配置

复制环境变量模板并填入你的 LLM 配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少需要配置 `LLM_API_KEY`：

```env
LLM_API_KEY=sk-your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

详见 [.env.example](.env.example) 获取完整配置说明。

### 启动服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

服务启动后访问 `http://localhost:8000/docs` 查看交互式 API 文档。

## API 接口

### 对话生成/修改工作流

```
POST /api/chat
```

**请求体：**

```json
{
  "session_id": "可选，不传则自动生成",
  "message": "帮我创建一个请假审批流程"
}
```

**响应：**

```json
{
  "session_id": "abc123",
  "reply": "已为您生成工作流「请假审批流程」，包含 3 个步骤：填写请假申请表、主管审批、邮件通知。",
  "workflow": {
    "id": "wf_a1b2c3d4",
    "name": "请假审批流程",
    "description": "员工请假审批的标准流程",
    "version": "1.0",
    "assignees": {
      "employee": { "role": "employee", "description": "发起请假的员工" },
      "manager": { "role": "manager", "description": "审批主管" }
    },
    "actions": [
      {
        "id": "action_1",
        "type": "form_action",
        "name": "填写请假申请表",
        "description": "员工填写请假类型、起止日期等信息",
        "order": 1,
        "assignee": { "ref": "employee", "role": "employee" },
        "custom_data": {}
      }
    ]
  }
}
```

### 获取可用 Action 类型

```
GET /api/workflow/actions
```

**响应：**

```json
[
  {
    "type": "form_action",
    "display_name": "表单提交",
    "description": "需要用户填写指定字段的表单",
    "custom_data_schema": {}
  }
]
```

### 健康检查

```
GET /health
```

## 项目结构

```
moxo-agent/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── actions/                # Action 类型插件系统
│   │   ├── base.py             # 抽象基类
│   │   ├── registry.py         # 注册表
│   │   ├── form_action.py      # 表单提交
│   │   ├── approval_action.py  # 审批
│   │   ├── email_action.py     # 邮件通知
│   │   └── todo_action.py      # 待办
│   ├── agent/                  # 核心 Agent 逻辑
│   │   ├── workflow_agent.py   # 工作流生成/修改编排器
│   │   ├── prompt_builder.py   # 系统提示词 & 工具定义构建
│   │   └── session.py          # 会话管理
│   ├── api/                    # HTTP 接口层
│   │   └── chat.py             # 对话 & Action 列表接口
│   ├── config/                 # 配置
│   │   └── settings.py         # Pydantic Settings
│   ├── llm/                    # LLM 客户端
│   │   └── client.py           # OpenAI SDK 封装
│   └── models/                 # Pydantic 数据模型
│       ├── assignee.py
│       ├── action.py
│       └── workflow.py
└── tests/                      # 测试套件
```

## 架构概览

```
用户消息 → API 层 → WorkflowAgent
  ↓
PromptBuilder（根据注册表构建系统提示词 + 工具 Schema）
  ↓
LLM Client（调用 OpenAI 兼容 API）
  ↓
Tool Call 处理（create_workflow / modify_workflow）
  ↓
工作流校验（Action 类型、Assignee 引用）
  ↓
Session 更新 + 响应返回
```

**核心设计：**

- **WorkflowAgent** — 中心编排器，路由 LLM 返回的 `create_workflow` 或 `modify_workflow` 工具调用
- **Action Registry** — 插件式注册表，每种 Action 定义自己的 `custom_data_schema()`，PromptBuilder 动态聚合所有 Schema 生成 LLM 工具定义
- **Lazy Agent 初始化** — Agent 实例在首次请求时才创建，方便测试时 mock

## 开发指南

### 运行测试

```bash
uv run pytest           # 全部测试
uv run pytest -v        # 详细输出
uv run pytest --cov=app # 覆盖率
```

### 代码质量

```bash
uv run ruff check app/ tests/  # Lint
uv run black app/ tests/       # 格式化
uv run isort app/ tests/       # Import 排序
uv run mypy app/               # 类型检查
```

### 扩展新的 Action 类型

1. 创建 `app/actions/your_action.py`，继承 `BaseAction` 并实现 `custom_data_schema()`
2. 在 `app/actions/__init__.py` 中注册

新的 Action 类型会自动出现在 LLM 的工具定义中，无需修改其他代码。

## 许可证

MIT
