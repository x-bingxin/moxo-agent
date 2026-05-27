# Workflow Agent 设计文档

## 概述

一个基于 LLM Function Calling 的 AI Agent，通过统一的 Chat API 接收用户自然语言输入，分析用户意图，自动生成结构化的 Workflow JSON 定义。支持多轮对话逐步完善 workflow。

## 技术选型

- **语言**：Python
- **框架**：FastAPI
- **LLM**：国产大模型（DeepSeek / 通义千问），要求支持 Function Calling
- **输出格式**：JSON
- **扩展机制**：类继承体系

## 核心职责

Agent 是**纯生成器**：分析用户意图 → 生成 workflow 定义（JSON），不负责 workflow 的执行。

## 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI 服务                        │
│                                                       │
│  POST /api/chat                                       │
│  ┌─────────────────────────────────────────────┐      │
│  │           WorkflowAgent                      │      │
│  │                                              │      │
│  │  用户消息 + Session 上下文                    │      │
│  │       │                                      │      │
│  │       ▼                                      │      │
│  │  Prompt 构建（含 action schemas）             │      │
│  │       │                                      │      │
│  │       ▼                                      │      │
│  │  LLM Function Calling                        │      │
│  │  （create_workflow / modify_workflow）        │      │
│  │       │                                      │      │
│  │       ▼                                      │      │
│  │  解析响应 → Pydantic 验证 → 输出 JSON         │      │
│  └─────────────────────────────────────────────┘      │
│                                                       │
│  Action 类型注册表：                                    │
│  ┌──────────┐ ┌───────────────┐ ┌────────────┐       │
│  │form_action│ │approval_action│ │email_action│ ...   │
│  └──────────┘ └───────────────┘ └────────────┘       │
└─────────────────────────────────────────────────────┘
```

## Action 类型体系

### 基类 BaseAction

```python
class BaseAction:
    action_type: str          # 如 "form_action"
    name: str                 # action 名称，如 "费用提交"
    description: str          # action 描述
    assignee: Assignee | None # 执行者（可选，系统自动执行的 action 无需 assignee）
    order: int                # 在 workflow 中的顺序

    def to_function_schema() -> dict:
        """生成 LLM function calling 的工具定义"""

    def validate(data: dict) -> bool:
        """验证 action 数据合法性"""
```

### Assignee 模型

```python
class Assignee:
    role: str                 # 角色，如 "Employee", "Manager"
    name: str | None          # 具体人名（可选）
    email: str | None         # 邮箱（可选）
    department: str | None    # 部门（可选）
```

**assignee 是可选的**：需要人工参与的 action（form_action、approval_action）有 assignee；系统自动执行的 action（email_action）不需要 assignee。

### 具体 Action 类型

```python
class FormAction(BaseAction):
    action_type = "form_action"
    # custom_data 中包含：
    # fields: list[FormField]  表单字段定义

class ApprovalAction(BaseAction):
    action_type = "approval_action"
    # custom_data 中包含：
    # approver_role: str         审批人角色
    # available_actions: list    可选操作 ["approve", "reject"]
    # on_reject: dict            拒绝后的行为

class EmailAction(BaseAction):
    action_type = "email_action"
    # custom_data 中包含：
    # trigger: str               触发条件
    # subject: str               邮件主题
    # template: str              邮件模板
    # recipients: list           收件人
```

### Action Registry

```python
class ActionRegistry:
    _actions: dict[str, type[BaseAction]]

    def register(action_class):
        """注册新的 action 类型"""

    def get_schemas() -> list[dict]:
        """获取所有已注册 action 的 function calling schema"""

    def validate_action(action_type, data) -> bool:
        """验证特定类型 action 的数据"""
```

**扩展方式**：新增 action 类型只需创建继承 `BaseAction` 的新类，用 `@registry.register` 装饰器注册。

## Workflow 数据模型

### 输出 JSON 结构

```json
{
  "workflow": {
    "id": "wf_generated_001",
    "name": "费用报销审批",
    "description": "员工提交费用报销，经理审批，系统自动通知",
    "version": "1.0",
    "created_at": "2026-05-27T14:30:00Z",
    "assignees": {
      "employee": {
        "role": "Employee",
        "description": "提交报销申请的员工"
      },
      "manager": {
        "role": "Manager",
        "description": "负责审批的直属经理"
      }
    },
    "actions": [
      {
        "id": "action_1",
        "type": "form_action",
        "name": "费用提交",
        "description": "员工填写报销申请表",
        "order": 1,
        "assignee": {
          "ref": "employee",
          "role": "Employee"
        },
        "custom_data": {
          "fields": [
            {"name": "expense_title", "type": "text", "label": "费用标题", "required": true},
            {"name": "expense_date", "type": "date", "label": "费用日期", "required": true},
            {"name": "amount", "type": "number", "label": "金额", "required": true},
            {"name": "category", "type": "select", "label": "费用类别", "required": true,
             "options": ["差旅", "办公用品", "餐饮", "交通", "其他"]},
            {"name": "business_purpose", "type": "textarea", "label": "商业用途说明", "required": true},
            {"name": "receipt", "type": "file", "label": "收据上传", "required": true},
            {"name": "notes", "type": "textarea", "label": "附加备注", "required": false}
          ]
        }
      },
      {
        "id": "action_2",
        "type": "approval_action",
        "name": "经理审批",
        "description": "经理审核费用报销申请",
        "order": 2,
        "assignee": {
          "ref": "manager",
          "role": "Manager"
        },
        "custom_data": {
          "approver_role": "Manager",
          "available_actions": ["approve", "reject"],
          "on_reject": {
            "action": "return_to",
            "target_ref": "employee",
            "description": "退回员工修改后重新提交"
          }
        }
      },
      {
        "id": "action_3",
        "type": "email_action",
        "name": "审批通知",
        "description": "审批通过后自动发送通知邮件",
        "order": 3,
        "assignee": null,
        "custom_data": {
          "trigger": "on_approval",
          "subject": "Your Expense Has Been Approved",
          "template": "Dear {{employee.name}}, your expense '{{expense_title}}' for {{amount}} has been approved.",
          "recipients": [{"ref": "employee"}]
        },
        "dependencies": {
          "triggered_by": "action_2",
          "condition": "approved"
        }
      }
    ]
  }
}
```

### 关键设计点

- **全局 assignees 定义**：workflow 顶层定义所有参与角色，actions 通过 `ref` 引用
- **assignee 可选**：系统自动执行的 action（如 email_action）的 assignee 为 null
- **action 顺序**：`order` 字段 + 数组顺序双重保证
- **依赖关系**：`dependencies` 字段表达 action 间的触发条件
- **custom_data**：每种 action 特有的配置放在 `custom_data` 中，由 ActionRegistry 中对应类型的 schema 约束

## LLM 集成

### Function Calling 工具

#### create_workflow

当 session 中尚无 workflow 时，LLM 调用此工具生成新 workflow。

```
create_workflow(
  name: str,
  description: str,
  assignees: [{role, description}],
  actions: [{
    type: str,        # action 类型（form_action/approval_action/email_action/...）
    name: str,
    description: str,
    order: int,
    assignee_ref: str | null,   # 引用全局 assignees 中的 key
    custom_data: {...}           # action 类型特有的数据
  }]
)
```

#### modify_workflow

当 session 中已有 workflow 时，LLM 调用此工具修改现有 workflow。

```
modify_workflow(
  operations: [{
    type: "insert" | "delete" | "update" | "reorder",
    target_action_id: str,     # 目标 action（delete/update/reorder 时）
    position: int,             # 插入位置（insert 时）
    action_data: {...},        # 新的 action 数据（insert/update 时）
  }]
)
```

### Prompt 构建

- **System Prompt**：定义 Agent 角色为 workflow 规划专家，要求分析用户意图并拆分为 actions
- **核心约束**：每个需要人工参与的 action 必须有 assignee；系统自动执行的 action assignee 为 null
- **动态工具定义**：从 ActionRegistry 动态生成 function calling schema，新增 action 类型自动可用
- **上下文注入**：多轮对话时，将当前 workflow JSON 注入 prompt 作为上下文

### 验证层

- Pydantic 模型验证 workflow 结构完整性
- ActionRegistry 校验每个 action 的类型是否已注册
- 检查 assignee 引用合法性（action 中的 assignee_ref 必须在全局 assignees 中存在）
- 检查 action 顺序连续性

## API 设计

### 统一 Chat 端点

```
POST /api/chat
```

**请求：**
```json
{
  "session_id": "abc123",
  "message": "创建一个费用审批流程"
}
```

**响应：**
```json
{
  "session_id": "abc123",
  "reply": "已为您生成费用报销审批流程，包含3个步骤：...",
  "workflow": { ... }
}
```

### 查询可用 Action 类型

```
GET /api/workflow/actions
```

**响应：**
```json
{
  "actions": [
    {"type": "form_action", "name": "表单提交", "description": "..."},
    {"type": "approval_action", "name": "审批", "description": "..."},
    {"type": "email_action", "name": "邮件通知", "description": "..."}
  ]
}
```

## Session 管理

```python
class Session:
    session_id: str
    workflow: dict | None       # 当前 workflow
    history: list[Message]      # 对话历史
    created_at: datetime
```

- **存储方式**：内存优先（dict），后续可扩展为 Redis/数据库
- **生命周期**：session 首次消息时自动创建，超时后自动清理
- **LLM 路由逻辑**：
  - session 中无 workflow → LLM 调用 `create_workflow`
  - session 中有 workflow → LLM 调用 `modify_workflow`
  - 用户问问题 → LLM 直接回复，不修改 workflow

## 错误处理

| 场景 | 处理 |
|------|------|
| LLM 调用失败 | 返回 502，提示用户重试 |
| LLM 返回格式错误 | 自动重试一次（附加错误提示），仍失败返回 422 |
| Action 类型不存在 | 返回 400，提示可用类型列表 |
| Assignee 引用无效 | 验证层拦截，返回 422 附带具体错误 |
| Session 不存在 | 自动创建新 session |

## 项目结构

```
moxo-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py             # /api/chat 路由
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── workflow_agent.py   # WorkflowAgent 核心引擎
│   │   ├── prompt_builder.py   # Prompt 模板构建
│   │   └── session.py          # Session 管理
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── base.py             # BaseAction 基类
│   │   ├── registry.py         # ActionRegistry
│   │   ├── form_action.py      # FormAction
│   │   ├── approval_action.py  # ApprovalAction
│   │   └── email_action.py     # EmailAction
│   ├── models/
│   │   ├── __init__.py
│   │   ├── workflow.py         # Workflow Pydantic 模型
│   │   ├── action.py           # Action Pydantic 模型
│   │   └── assignee.py         # Assignee 模型
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py           # LLM 客户端封装
│   └── config/
│       ├── __init__.py
│       └── settings.py         # 配置管理
├── tests/
│   ├── test_agent.py
│   ├── test_actions.py
│   └── test_api.py
├── requirements.txt
└── .env.example
```
