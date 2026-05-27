# Workflow Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 LLM Function Calling 的 AI Agent，通过统一 Chat API 将用户自然语言输入转化为结构化的 Workflow JSON 定义。

**Architecture:** FastAPI 服务接收用户消息，通过 Session 管理维护对话上下文，WorkflowAgent 使用 OpenAI SDK 调用国产大模型（DeepSeek/通义千问）的 Function Calling 能力，Action Registry 动态注册 action 类型并生成工具 schema，验证层确保输出合法性。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, OpenAI SDK, pytest, httpx

---

## 文件结构

```
moxo-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口 + lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py                # /api/chat, /api/workflow/actions 路由
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── workflow_agent.py      # WorkflowAgent 核心引擎
│   │   ├── prompt_builder.py      # System prompt + tool schema 构建
│   │   └── session.py             # Session 管理（内存存储）
│   ├── actions/
│   │   ├── __init__.py            # 自动注册所有 action 类型
│   │   ├── base.py                # BaseAction 抽象基类
│   │   ├── registry.py            # ActionRegistry 注册表
│   │   ├── form_action.py         # FormAction
│   │   ├── approval_action.py     # ApprovalAction
│   │   └── email_action.py        # EmailAction
│   ├── models/
│   │   ├── __init__.py
│   │   ├── workflow.py            # Workflow Pydantic 模型
│   │   ├── action.py              # ActionDefinition Pydantic 模型
│   │   └── assignee.py            # Assignee Pydantic 模型
│   ├── llm/
│   │   ├── __init__.py
│   │   └── client.py              # LLM 客户端封装
│   └── config/
│       ├── __init__.py
│       └── settings.py            # pydantic-settings 配置管理
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   ├── test_models.py             # 模型验证测试
│   ├── test_actions.py            # Action 类型 + Registry 测试
│   ├── test_prompt_builder.py     # Prompt 构建测试
│   ├── test_session.py            # Session 管理测试
│   ├── test_llm_client.py         # LLM 客户端测试（mock）
│   ├── test_agent.py              # WorkflowAgent 核心逻辑测试（mock LLM）
│   └── test_api.py                # API 端到端测试（mock LLM）
├── requirements.txt
└── .env.example
```

---

### Task 1: 项目初始化

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config/__init__.py`
- Create: `app/config/settings.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.115.0
uvicorn==0.30.0
pydantic==2.9.0
pydantic-settings==2.5.0
openai==1.50.0
python-dotenv==1.0.1
pytest==8.3.0
httpx==0.27.0
```

- [ ] **Step 2: 创建 .env.example**

```env
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

- [ ] **Step 3: 创建 app/config/settings.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    session_timeout_minutes: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 创建 app/config/__init__.py**

```python
from app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

- [ ] **Step 5: 创建 app/main.py**

```python
from fastapi import FastAPI

app = FastAPI(title="Moxo Workflow Agent", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 创建空的 __init__.py 和 tests 基础设施**

```python
# app/__init__.py
# (empty)
```

```python
# tests/__init__.py
# (empty)
```

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
```

- [ ] **Step 7: 安装依赖并验证项目可运行**

Run: `pip install -r requirements.txt`
Expected: 安装成功，无报错

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest --co -q`
Expected: 收集到 0 个测试，无导入错误

Run: `cd /Users/bingxinxia/workspace/moxo-agent && uvicorn app.main:app --port 8000 &` 然后 `curl http://localhost:8000/health` 然后 `kill %1`
Expected: 返回 `{"status":"ok"}`

- [ ] **Step 8: 提交**

```bash
git add requirements.txt .env.example app/ tests/
git commit -m "feat: project scaffold with FastAPI, config, and test setup"
```

---

### Task 2: Pydantic 数据模型

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/assignee.py`
- Create: `app/models/action.py`
- Create: `app/models/workflow.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 编写模型测试**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError

from app.models.assignee import Assignee, AssigneeRef
from app.models.action import ActionDefinition, ActionDependency
from app.models.workflow import Workflow, WorkflowAssignee


class TestAssignee:
    def test_create_with_role_only(self):
        a = Assignee(role="Employee")
        assert a.role == "Employee"
        assert a.name is None
        assert a.email is None
        assert a.department is None

    def test_create_with_all_fields(self):
        a = Assignee(role="Manager", name="张三", email="zhang@example.com", department="工程部")
        assert a.name == "张三"
        assert a.email == "zhang@example.com"

    def test_role_required(self):
        with pytest.raises(ValidationError):
            Assignee()

    def test_assignee_ref(self):
        ref = AssigneeRef(ref="employee", role="Employee")
        assert ref.ref == "employee"

    def test_assignee_ref_required_fields(self):
        with pytest.raises(ValidationError):
            AssigneeRef()


class TestActionDefinition:
    def test_minimal_action(self):
        action = ActionDefinition(
            id="action_1",
            type="form_action",
            name="费用提交",
            description="填写报销表",
            order=1,
            assignee=None,
            custom_data={},
        )
        assert action.id == "action_1"
        assert action.assignee is None

    def test_action_with_assignee(self):
        action = ActionDefinition(
            id="action_1",
            type="form_action",
            name="费用提交",
            description="填写报销表",
            order=1,
            assignee=AssigneeRef(ref="employee", role="Employee"),
            custom_data={"fields": []},
        )
        assert action.assignee.ref == "employee"

    def test_action_with_dependency(self):
        dep = ActionDependency(triggered_by="action_2", condition="approved")
        action = ActionDefinition(
            id="action_3",
            type="email_action",
            name="通知",
            description="发送通知",
            order=3,
            assignee=None,
            custom_data={},
            dependencies=dep,
        )
        assert action.dependencies.triggered_by == "action_2"


class TestWorkflow:
    def test_create_workflow(self):
        wf = Workflow(
            id="wf_001",
            name="费用审批",
            description="费用报销审批流程",
            version="1.0",
            assignees={
                "employee": WorkflowAssignee(role="Employee", description="提交报销的员工"),
            },
            actions=[
                ActionDefinition(
                    id="action_1",
                    type="form_action",
                    name="费用提交",
                    description="填写报销表",
                    order=1,
                    assignee=AssigneeRef(ref="employee", role="Employee"),
                    custom_data={},
                )
            ],
        )
        assert wf.name == "费用审批"
        assert len(wf.actions) == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_models.py -v`
Expected: FAIL，模块导入错误

- [ ] **Step 3: 实现 Assignee 模型**

```python
# app/models/assignee.py
from pydantic import BaseModel


class Assignee(BaseModel):
    """全局角色定义"""
    role: str
    name: str | None = None
    email: str | None = None
    department: str | None = None


class AssigneeRef(BaseModel):
    """Action 中对全局 assignee 的引用"""
    ref: str
    role: str
```

- [ ] **Step 4: 实现 Action 模型**

```python
# app/models/action.py
from typing import Any

from pydantic import BaseModel

from app.models.assignee import AssigneeRef


class ActionDependency(BaseModel):
    triggered_by: str
    condition: str | None = None


class ActionDefinition(BaseModel):
    id: str
    type: str
    name: str
    description: str
    order: int
    assignee: AssigneeRef | None = None
    custom_data: dict[str, Any] = {}
    dependencies: ActionDependency | None = None
```

- [ ] **Step 5: 实现 Workflow 模型**

```python
# app/models/workflow.py
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.action import ActionDefinition


class WorkflowAssignee(BaseModel):
    role: str
    description: str = ""


class Workflow(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    assignees: dict[str, WorkflowAssignee] = {}
    actions: list[ActionDefinition] = []
```

- [ ] **Step 6: 创建 models __init__.py**

```python
# app/models/__init__.py
from app.models.assignee import Assignee, AssigneeRef
from app.models.action import ActionDefinition, ActionDependency
from app.models.workflow import Workflow, WorkflowAssignee

__all__ = [
    "Assignee",
    "AssigneeRef",
    "ActionDefinition",
    "ActionDependency",
    "Workflow",
    "WorkflowAssignee",
]
```

- [ ] **Step 7: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_models.py -v`
Expected: 全部 PASS

- [ ] **Step 8: 提交**

```bash
git add app/models/ tests/test_models.py
git commit -m "feat: add Pydantic models for Assignee, Action, Workflow"
```

---

### Task 3: Action 基类与注册表

**Files:**
- Create: `app/actions/__init__.py`
- Create: `app/actions/base.py`
- Create: `app/actions/registry.py`
- Test: `tests/test_actions.py`

- [ ] **Step 1: 编写 Action 基类和注册表测试**

```python
# tests/test_actions.py
import pytest

from app.actions.base import BaseAction
from app.actions.registry import ActionRegistry


class TestActionRegistry:
    def test_register_and_get(self):
        registry = ActionRegistry()

        class DummyAction(BaseAction):
            action_type = "dummy_action"
            display_name = "测试动作"
            description = "用于测试的动作类型"

            @classmethod
            def custom_data_schema(cls) -> dict:
                return {"type": "object", "properties": {}}

        registry.register(DummyAction)
        assert "dummy_action" in registry.list_types()
        assert registry.get("dummy_action") is DummyAction

    def test_get_nonexistent_raises(self):
        registry = ActionRegistry()
        with pytest.raises(KeyError, match="unknown_action"):
            registry.get("unknown_action")

    def test_get_schemas_returns_list(self):
        registry = ActionRegistry()

        class AnotherAction(BaseAction):
            action_type = "another_action"
            display_name = "另一个动作"
            description = "另一个动作类型"

            @classmethod
            def custom_data_schema(cls) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "field1": {"type": "string", "description": "字段1"},
                    },
                    "required": ["field1"],
                }

        registry.register(AnotherAction)
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["action_type"] == "another_action"
        assert "custom_data_schema" in schemas[0]

    def test_list_types(self):
        registry = ActionRegistry()

        class A(BaseAction):
            action_type = "a"
            display_name = "A"
            description = "A"

            @classmethod
            def custom_data_schema(cls):
                return {}

        class B(BaseAction):
            action_type = "b"
            display_name = "B"
            description = "B"

            @classmethod
            def custom_data_schema(cls):
                return {}

        registry.register(A)
        registry.register(B)
        assert sorted(registry.list_types()) == ["a", "b"]

    def test_duplicate_register_raises(self):
        registry = ActionRegistry()

        class Dup(BaseAction):
            action_type = "dup"
            display_name = "Dup"
            description = "Dup"

            @classmethod
            def custom_data_schema(cls):
                return {}

        registry.register(Dup)
        with pytest.raises(ValueError, match="dup"):
            registry.register(Dup)

    def test_register_decorator(self):
        registry = ActionRegistry()

        @registry.register
        class DecoAction(BaseAction):
            action_type = "deco_action"
            display_name = "装饰器动作"
            description = "通过装饰器注册"

            @classmethod
            def custom_data_schema(cls):
                return {}

        assert registry.get("deco_action") is DecoAction
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_actions.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 BaseAction**

```python
# app/actions/base.py
from abc import ABC, abstractmethod


class BaseAction(ABC):
    """所有 action 类型的抽象基类"""

    action_type: str
    display_name: str
    description: str

    @classmethod
    @abstractmethod
    def custom_data_schema(cls) -> dict:
        """返回此 action 类型的 custom_data JSON Schema"""
        ...
```

- [ ] **Step 4: 实现 ActionRegistry**

```python
# app/actions/registry.py
from app.actions.base import BaseAction


class ActionRegistry:
    def __init__(self):
        self._actions: dict[str, type[BaseAction]] = {}

    def register(self, action_class: type[BaseAction]) -> type[BaseAction]:
        """注册 action 类型，可作为装饰器使用"""
        action_type = action_class.action_type
        if action_type in self._actions:
            raise ValueError(f"Action type '{action_type}' already registered")
        self._actions[action_type] = action_class
        return action_class

    def get(self, action_type: str) -> type[BaseAction]:
        """获取已注册的 action 类"""
        if action_type not in self._actions:
            raise KeyError(f"Unknown action type: {action_type}")
        return self._actions[action_type]

    def list_types(self) -> list[str]:
        """返回所有已注册的 action 类型名称"""
        return list(self._actions.keys())

    def get_schemas(self) -> list[dict]:
        """返回所有 action 类型的 schema 信息"""
        schemas = []
        for action_type, action_class in self._actions.items():
            schemas.append({
                "action_type": action_type,
                "display_name": action_class.display_name,
                "description": action_class.description,
                "custom_data_schema": action_class.custom_data_schema(),
            })
        return schemas
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_actions.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/actions/base.py app/actions/registry.py tests/test_actions.py
git commit -m "feat: add BaseAction abstract class and ActionRegistry"
```

---

### Task 4: 具体 Action 类型实现

**Files:**
- Create: `app/actions/form_action.py`
- Create: `app/actions/approval_action.py`
- Create: `app/actions/email_action.py`
- Create: `app/actions/__init__.py`
- Modify: `tests/test_actions.py`（追加具体类型测试）

- [ ] **Step 1: 追加具体 Action 类型测试**

在 `tests/test_actions.py` 文件末尾追加：

```python
class TestConcreteActions:
    def test_form_action_schema(self):
        from app.actions.form_action import FormAction

        schema = FormAction.custom_data_schema()
        assert "properties" in schema
        assert "fields" in schema["properties"]

    def test_approval_action_schema(self):
        from app.actions.approval_action import ApprovalAction

        schema = ApprovalAction.custom_data_schema()
        assert "properties" in schema
        assert "approver_role" in schema["properties"]

    def test_email_action_schema(self):
        from app.actions.email_action import EmailAction

        schema = EmailAction.custom_data_schema()
        assert "properties" in schema
        assert "subject" in schema["properties"]

    def test_all_actions_registered(self):
        from app.actions import registry

        types = registry.list_types()
        assert "form_action" in types
        assert "approval_action" in types
        assert "email_action" in types
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_actions.py::TestConcreteActions -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 FormAction**

```python
# app/actions/form_action.py
from app.actions.base import BaseAction


class FormAction(BaseAction):
    action_type = "form_action"
    display_name = "表单提交"
    description = "收集用户填写的表单信息，支持文本、日期、数字、下拉选择、文件上传等字段类型"

    @classmethod
    def custom_data_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "description": "表单字段列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "字段标识名"},
                            "type": {
                                "type": "string",
                                "enum": ["text", "textarea", "number", "date", "select", "file"],
                                "description": "字段类型",
                            },
                            "label": {"type": "string", "description": "字段显示名称"},
                            "required": {"type": "boolean", "description": "是否必填"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "下拉选项（仅 type=select 时需要）",
                            },
                        },
                        "required": ["name", "type", "label", "required"],
                    },
                }
            },
            "required": ["fields"],
        }
```

- [ ] **Step 4: 实现 ApprovalAction**

```python
# app/actions/approval_action.py
from app.actions.base import BaseAction


class ApprovalAction(BaseAction):
    action_type = "approval_action"
    display_name = "审批"
    description = "需要指定角色对提交的内容进行审核，支持批准或拒绝操作"

    @classmethod
    def custom_data_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "approver_role": {
                    "type": "string",
                    "description": "审批人的角色，如 Manager、Director",
                },
                "available_actions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["approve", "reject"]},
                    "description": "审批人可执行的操作",
                },
                "on_reject": {
                    "type": "object",
                    "description": "拒绝后的处理行为",
                    "properties": {
                        "action": {"type": "string", "enum": ["return_to", "end"]},
                        "target_ref": {"type": "string", "description": "退回目标角色的 ref"},
                        "description": {"type": "string"},
                    },
                    "required": ["action"],
                },
            },
            "required": ["approver_role", "available_actions"],
        }
```

- [ ] **Step 5: 实现 EmailAction**

```python
# app/actions/email_action.py
from app.actions.base import BaseAction


class EmailAction(BaseAction):
    action_type = "email_action"
    display_name = "邮件通知"
    description = "系统自动发送邮件通知，无需人工参与。通常在前置条件满足时触发"

    @classmethod
    def custom_data_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "trigger": {
                    "type": "string",
                    "description": "触发条件，如 on_approval、on_rejection、on_submission",
                },
                "subject": {
                    "type": "string",
                    "description": "邮件主题",
                },
                "template": {
                    "type": "string",
                    "description": "邮件正文模板，支持 {{variable}} 占位符",
                },
                "recipients": {
                    "type": "array",
                    "description": "收件人列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ref": {"type": "string", "description": "引用全局 assignee 的 key"},
                        },
                        "required": ["ref"],
                    },
                },
            },
            "required": ["trigger", "subject", "template", "recipients"],
        }
```

- [ ] **Step 6: 创建 actions __init__.py 实现自动注册**

```python
# app/actions/__init__.py
from app.actions.registry import ActionRegistry
from app.actions.form_action import FormAction
from app.actions.approval_action import ApprovalAction
from app.actions.email_action import EmailAction

registry = ActionRegistry()
registry.register(FormAction)
registry.register(ApprovalAction)
registry.register(EmailAction)

__all__ = ["registry", "FormAction", "ApprovalAction", "EmailAction"]
```

- [ ] **Step 7: 运行全部 action 测试**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_actions.py -v`
Expected: 全部 PASS

- [ ] **Step 8: 提交**

```bash
git add app/actions/ tests/test_actions.py
git commit -m "feat: implement FormAction, ApprovalAction, EmailAction with auto-registration"
```

---

### Task 5: LLM 客户端封装

**Files:**
- Create: `app/llm/__init__.py`
- Create: `app/llm/client.py`
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: 编写 LLM 客户端测试**

```python
# tests/test_llm_client.py
import json
from unittest.mock import MagicMock, patch

import pytest

from app.llm.client import LLMClient, LLMResponse


class TestLLMClient:
    def _make_mock_response(self, content=None, tool_calls=None):
        """构造 mock OpenAI ChatCompletion 响应"""
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_chat_without_tools(self):
        mock_response = self._make_mock_response(content="你好！")

        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")
            result = client.chat(messages=[{"role": "user", "content": "你好"}])

        assert isinstance(result, LLMResponse)
        assert result.content == "你好！"
        assert result.tool_calls is None

    def test_chat_with_tool_calls(self):
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "create_workflow"
        tool_call.function.arguments = json.dumps({"name": "测试流程", "actions": []})

        mock_response = self._make_mock_response(content=None, tool_calls=[tool_call])

        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")
            result = client.chat(
                messages=[{"role": "user", "content": "创建流程"}],
                tools=[{"type": "function", "function": {"name": "create_workflow"}}],
            )

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function_name == "create_workflow"
        assert result.tool_calls[0].arguments["name"] == "测试流程"

    def test_api_error_raises(self):
        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")

            with pytest.raises(RuntimeError, match="LLM 调用失败"):
                client.chat(messages=[{"role": "user", "content": "测试"}])
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_llm_client.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 LLM 客户端**

```python
# app/llm/client.py
import json
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class ToolCall:
    call_id: str
    function_name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None = None


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        try:
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        call_id=tc.id,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    ))

            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
            )
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e
```

- [ ] **Step 4: 创建 llm __init__.py**

```python
# app/llm/__init__.py
from app.llm.client import LLMClient, LLMResponse, ToolCall

__all__ = ["LLMClient", "LLMResponse", "ToolCall"]
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_llm_client.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/llm/ tests/test_llm_client.py
git commit -m "feat: add LLM client wrapper with tool call support"
```

---

### Task 6: Prompt 构建器

**Files:**
- Create: `app/agent/__init__.py`
- Create: `app/agent/prompt_builder.py`
- Test: `tests/test_prompt_builder.py`

- [ ] **Step 1: 编写 Prompt 构建器测试**

```python
# tests/test_prompt_builder.py
import json

from app.agent.prompt_builder import PromptBuilder
from app.actions.registry import ActionRegistry
from app.actions.base import BaseAction


def _make_test_registry() -> ActionRegistry:
    registry = ActionRegistry()

    class TestFormAction(BaseAction):
        action_type = "form_action"
        display_name = "表单提交"
        description = "收集表单信息"

        @classmethod
        def custom_data_schema(cls):
            return {
                "type": "object",
                "properties": {
                    "fields": {"type": "array", "description": "表单字段"},
                },
                "required": ["fields"],
            }

    registry.register(TestFormAction)
    return registry


class TestPromptBuilder:
    def test_build_system_prompt(self):
        registry = _make_test_registry()
        builder = PromptBuilder(registry)
        system_prompt = builder.build_system_prompt()

        assert "workflow" in system_prompt.lower() or "工作流" in system_prompt
        assert "action" in system_prompt.lower() or "动作" in system_prompt
        assert "assignee" in system_prompt.lower() or "assignee" in system_prompt

    def test_build_tools(self):
        registry = _make_test_registry()
        builder = PromptBuilder(registry)
        tools = builder.build_tools(has_workflow=False)

        assert len(tools) == 1
        func = tools[0]["function"]
        assert func["name"] == "create_workflow"
        params = func["parameters"]
        assert "name" in params["properties"]
        assert "actions" in params["properties"]

    def test_build_tools_with_workflow(self):
        registry = _make_test_registry()
        builder = PromptBuilder(registry)
        tools = builder.build_tools(has_workflow=True)

        tool_names = [t["function"]["name"] for t in tools]
        assert "create_workflow" in tool_names
        assert "modify_workflow" in tool_names

    def test_build_messages_new_workflow(self):
        registry = _make_test_registry()
        builder = PromptBuilder(registry)
        messages = builder.build_messages(
            user_message="创建一个费用审批流程",
            workflow=None,
        )

        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "创建一个费用审批流程"

    def test_build_messages_existing_workflow(self):
        registry = _make_test_registry()
        builder = PromptBuilder(registry)
        existing_wf = {"name": "旧流程", "actions": []}
        messages = builder.build_messages(
            user_message="加一个步骤",
            workflow=existing_wf,
        )

        system_content = messages[0]["content"]
        assert "旧流程" in system_content or json.dumps(existing_wf, ensure_ascii=False) in system_content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_prompt_builder.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 PromptBuilder**

```python
# app/agent/prompt_builder.py
import json

from app.actions.registry import ActionRegistry

SYSTEM_PROMPT_TEMPLATE = """你是一个专业的 workflow 规划助手。你的任务是分析用户的自然语言输入，将其转化为结构化的 workflow 定义。

## 核心规则

1. 分析用户意图，将流程拆分为有序的 actions
2. 每个需要人工参与的 action 必须指定 assignee（通过 assignee_ref 引用全局角色）
3. 系统自动执行的 action（如邮件通知）的 assignee_ref 设为 null
4. 每个 action 的 custom_data 必须严格遵循该 action 类型的 schema

## 可用的 action 类型

{action_types_desc}

## 输出要求

- 调用 create_workflow 工具来创建新的 workflow
- 如果已有 workflow，调用 modify_workflow 工具来修改
- 如果用户只是在提问（而非要求创建或修改），直接回复即可，无需调用工具
{workflow_context}"""

ACTION_TYPE_TEMPLATE = """### {display_name} ({action_type})
{description}
custom_data schema:
```json
{schema}
```"""


class PromptBuilder:
    def __init__(self, registry: ActionRegistry):
        self._registry = registry

    def build_system_prompt(self, workflow: dict | None = None) -> str:
        schemas = self._registry.get_schemas()
        action_types_desc = "\n\n".join(
            ACTION_TYPE_TEMPLATE.format(
                display_name=s["display_name"],
                action_type=s["action_type"],
                description=s["description"],
                schema=json.dumps(s["custom_data_schema"], ensure_ascii=False, indent=2),
            )
            for s in schemas
        )

        workflow_context = ""
        if workflow:
            workflow_context = (
                "\n\n## 当前 Workflow\n\n"
                f"以下是用户已有的 workflow，请在此基础上修改：\n"
                f"```json\n{json.dumps(workflow, ensure_ascii=False, indent=2)}\n```"
            )

        return SYSTEM_PROMPT_TEMPLATE.format(
            action_types_desc=action_types_desc,
            workflow_context=workflow_context,
        )

    def build_tools(self, has_workflow: bool = False) -> list[dict]:
        schemas = self._registry.get_schemas()
        action_type_enum = [s["action_type"] for s in schemas]

        action_schema = {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": action_type_enum,
                    "description": "action 类型",
                },
                "name": {"type": "string", "description": "action 名称"},
                "description": {"type": "string", "description": "action 描述"},
                "order": {"type": "integer", "description": "在 workflow 中的顺序，从 1 开始"},
                "assignee_ref": {
                    "type": "string",
                    "nullable": True,
                    "description": "引用全局 assignees 中的 key，系统自动执行的 action 设为 null",
                },
                "custom_data": {
                    "type": "object",
                    "description": "action 类型特有的配置数据，需遵循对应类型的 schema",
                },
            },
            "required": ["type", "name", "description", "order", "custom_data"],
        }

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_workflow",
                    "description": "创建一个新的 workflow 定义",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "workflow 名称"},
                            "description": {"type": "string", "description": "workflow 描述"},
                            "assignees": {
                                "type": "array",
                                "description": "全局角色定义列表",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "key": {"type": "string", "description": "角色标识 key，如 employee, manager"},
                                        "role": {"type": "string", "description": "角色名称"},
                                        "description": {"type": "string", "description": "角色描述"},
                                    },
                                    "required": ["key", "role", "description"],
                                },
                            },
                            "actions": {
                                "type": "array",
                                "description": "workflow 中的 action 列表",
                                "items": action_schema,
                            },
                        },
                        "required": ["name", "description", "assignees", "actions"],
                    },
                },
            }
        ]

        if has_workflow:
            tools.append({
                "type": "function",
                "function": {
                    "name": "modify_workflow",
                    "description": "修改已有的 workflow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operations": {
                                "type": "array",
                                "description": "修改操作列表",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["insert", "delete", "update", "reorder"],
                                            "description": "操作类型",
                                        },
                                        "target_action_id": {
                                            "type": "string",
                                            "description": "目标 action 的 id（delete/update/reorder 时需要）",
                                        },
                                        "position": {
                                            "type": "integer",
                                            "description": "插入位置（insert 时需要）",
                                        },
                                        "action_data": {
                                            "type": "object",
                                            "description": "新的 action 数据（insert/update 时需要）",
                                        },
                                    },
                                    "required": ["type"],
                                },
                            },
                        },
                        "required": ["operations"],
                    },
                },
            })

        return tools

    def build_messages(
        self,
        user_message: str,
        workflow: dict | None = None,
        history: list[dict] | None = None,
    ) -> list[dict]:
        messages = [
            {"role": "system", "content": self.build_system_prompt(workflow=workflow)},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages
```

- [ ] **Step 4: 创建 agent __init__.py**

```python
# app/agent/__init__.py
# (empty)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_prompt_builder.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/agent/ tests/test_prompt_builder.py
git commit -m "feat: add PromptBuilder with dynamic tool schema generation"
```

---

### Task 7: Session 管理

**Files:**
- Create: `app/agent/session.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: 编写 Session 管理测试**

```python
# tests/test_session.py
import pytest

from app.agent.session import Session, SessionManager


class TestSession:
    def test_create_session(self):
        s = Session(session_id="test-1")
        assert s.session_id == "test-1"
        assert s.workflow is None
        assert s.history == []

    def test_add_message(self):
        s = Session(session_id="test-1")
        s.add_message("user", "你好")
        s.add_message("assistant", "你好！")
        assert len(s.history) == 2
        assert s.history[0] == {"role": "user", "content": "你好"}

    def test_set_workflow(self):
        s = Session(session_id="test-1")
        wf = {"name": "测试流程", "actions": []}
        s.set_workflow(wf)
        assert s.workflow == wf


class TestSessionManager:
    def test_get_or_create_new(self):
        mgr = SessionManager()
        session = mgr.get_or_create("new-session")
        assert session.session_id == "new-session"

    def test_get_existing(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("s1")
        s1.add_message("user", "你好")
        s2 = mgr.get_or_create("s1")
        assert len(s2.history) == 1

    def test_multiple_sessions(self):
        mgr = SessionManager()
        mgr.get_or_create("a")
        mgr.get_or_create("b")
        assert mgr.count() == 2

    def test_remove_session(self):
        mgr = SessionManager()
        mgr.get_or_create("to-remove")
        mgr.remove("to-remove")
        assert mgr.count() == 0

    def test_remove_nonexistent_no_error(self):
        mgr = SessionManager()
        mgr.remove("nonexistent")  # 不应抛异常
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_session.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 Session 和 SessionManager**

```python
# app/agent/session.py
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Session:
    session_id: str
    workflow: dict | None = None
    history: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def set_workflow(self, workflow: dict):
        self.workflow = workflow


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self._sessions)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_session.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/agent/session.py tests/test_session.py
git commit -m "feat: add Session and SessionManager for conversation state"
```

---

### Task 8: WorkflowAgent 核心引擎

**Files:**
- Create: `app/agent/workflow_agent.py`
- Test: `tests/test_agent.py`

- [ ] **Step 1: 编写 WorkflowAgent 测试**

```python
# tests/test_agent.py
import json
from unittest.mock import MagicMock

import pytest

from app.agent.workflow_agent import WorkflowAgent
from app.agent.session import SessionManager
from app.llm.client import LLMResponse, ToolCall
from app.actions import registry


class TestWorkflowAgent:
    def _make_agent(self, mock_response: LLMResponse) -> WorkflowAgent:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        session_mgr = SessionManager()
        return WorkflowAgent(
            llm_client=mock_client,
            registry=registry,
            session_manager=session_mgr,
        )

    def test_generate_new_workflow(self):
        workflow_data = {
            "name": "费用审批",
            "description": "费用报销审批流程",
            "assignees": [
                {"key": "employee", "role": "Employee", "description": "提交报销的员工"},
                {"key": "manager", "role": "Manager", "description": "审批经理"},
            ],
            "actions": [
                {
                    "type": "form_action",
                    "name": "费用提交",
                    "description": "填写报销表",
                    "order": 1,
                    "assignee_ref": "employee",
                    "custom_data": {"fields": []},
                }
            ],
        }

        mock_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments=workflow_data,
            )],
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-1", "创建一个费用审批流程")

        assert result["reply"] is not None
        assert result["workflow"] is not None
        assert result["workflow"]["name"] == "费用审批"
        assert result["session_id"] == "session-1"

    def test_text_reply_without_tool_call(self):
        mock_response = LLMResponse(
            content="你好！请告诉我你想创建什么样的工作流。",
            tool_calls=None,
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-2", "你好")

        assert result["reply"] == "你好！请告诉我你想创建什么样的工作流。"
        assert result["workflow"] is None

    def test_modify_existing_workflow(self):
        # 先创建一个 workflow
        create_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments={
                    "name": "费用审批",
                    "description": "流程",
                    "assignees": [
                        {"key": "employee", "role": "Employee", "description": "员工"},
                    ],
                    "actions": [
                        {
                            "type": "form_action",
                            "name": "提交",
                            "description": "提交表单",
                            "order": 1,
                            "assignee_ref": "employee",
                            "custom_data": {"fields": []},
                        }
                    ],
                },
            )],
        )

        mock_client = MagicMock()
        mock_client.chat.return_value = create_response
        session_mgr = SessionManager()

        agent = WorkflowAgent(
            llm_client=mock_client,
            registry=registry,
            session_manager=session_mgr,
        )
        agent.process("session-3", "创建流程")

        # 然后修改 workflow
        modify_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_2",
                function_name="modify_workflow",
                arguments={
                    "operations": [
                        {
                            "type": "insert",
                            "position": 2,
                            "action_data": {
                                "type": "approval_action",
                                "name": "审批",
                                "description": "经理审批",
                                "order": 2,
                                "assignee_ref": "employee",
                                "custom_data": {"approver_role": "Manager", "available_actions": ["approve", "reject"]},
                            },
                        }
                    ]
                },
            )],
        )
        mock_client.chat.return_value = modify_response
        result = agent.process("session-3", "加一个审批步骤")

        assert result["workflow"] is not None
        assert len(result["workflow"]["actions"]) == 2

    def test_invalid_action_type_in_response(self):
        workflow_data = {
            "name": "测试",
            "description": "测试",
            "assignees": [],
            "actions": [
                {
                    "type": "nonexistent_action",
                    "name": "测试",
                    "description": "测试",
                    "order": 1,
                    "custom_data": {},
                }
            ],
        }

        mock_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments=workflow_data,
            )],
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-4", "创建流程")

        assert "错误" in result["reply"] or "error" in result["reply"].lower()
        assert result["workflow"] is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_agent.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 WorkflowAgent**

```python
# app/agent/workflow_agent.py
import uuid

from app.actions.registry import ActionRegistry
from app.agent.prompt_builder import PromptBuilder
from app.agent.session import SessionManager
from app.llm.client import LLMClient, LLMResponse


class WorkflowAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        registry: ActionRegistry,
        session_manager: SessionManager,
    ):
        self._llm = llm_client
        self._registry = registry
        self._sessions = session_manager
        self._prompt_builder = PromptBuilder(registry)

    def process(self, session_id: str, user_message: str) -> dict:
        session = self._sessions.get_or_create(session_id)
        session.add_message("user", user_message)

        has_workflow = session.workflow is not None
        tools = self._prompt_builder.build_tools(has_workflow=has_workflow)
        messages = self._prompt_builder.build_messages(
            user_message=user_message,
            workflow=session.workflow,
            history=session.history[:-1],  # 排除刚加入的当前消息，避免重复
        )

        response = self._llm.chat(messages=messages, tools=tools)

        if response.tool_calls:
            result = self._handle_tool_calls(session, response)
        else:
            result = {"reply": response.content or "", "workflow": session.workflow}

        session.add_message("assistant", result["reply"])
        return {
            "session_id": session_id,
            "reply": result["reply"],
            "workflow": result.get("workflow"),
        }

    def _handle_tool_calls(self, session, response: LLMResponse) -> dict:
        for tool_call in response.tool_calls:
            if tool_call.function_name == "create_workflow":
                return self._handle_create_workflow(session, tool_call.arguments)
            elif tool_call.function_name == "modify_workflow":
                return self._handle_modify_workflow(session, tool_call.arguments)

        return {"reply": "抱歉，我无法理解您的请求。", "workflow": session.workflow}

    def _handle_create_workflow(self, session, args: dict) -> dict:
        try:
            workflow = self._build_workflow(args)
            self._validate_workflow(workflow)
            session.set_workflow(workflow)
            action_count = len(workflow["actions"])
            action_names = "、".join(a["name"] for a in workflow["actions"])
            return {
                "reply": f"已为您生成工作流「{workflow['name']}」，包含 {action_count} 个步骤：{action_names}。",
                "workflow": workflow,
            }
        except Exception as e:
            return {"reply": f"生成工作流时出错：{e}", "workflow": None}

    def _handle_modify_workflow(self, session, args: dict) -> dict:
        if session.workflow is None:
            return {"reply": "当前没有可修改的工作流。", "workflow": None}

        try:
            workflow = session.workflow.copy()
            actions = list(workflow.get("actions", []))

            for op in args.get("operations", []):
                op_type = op["type"]
                if op_type == "insert":
                    action_data = op.get("action_data", {})
                    action_id = f"action_{len(actions) + 1}"
                    action_data["id"] = action_id
                    position = op.get("position", len(actions))
                    actions.insert(position - 1, action_data)
                elif op_type == "delete":
                    target_id = op.get("target_action_id")
                    actions = [a for a in actions if a.get("id") != target_id]
                elif op_type == "update":
                    target_id = op.get("target_action_id")
                    for i, a in enumerate(actions):
                        if a.get("id") == target_id:
                            actions[i] = {**a, **op.get("action_data", {})}
                            break
                elif op_type == "reorder":
                    # 简单处理：按 order 字段重新排序
                    actions.sort(key=lambda a: a.get("order", 0))

            workflow["actions"] = actions
            self._validate_workflow(workflow)
            session.set_workflow(workflow)

            action_names = "、".join(a["name"] for a in actions)
            return {
                "reply": f"已更新工作流，当前包含 {len(actions)} 个步骤：{action_names}。",
                "workflow": workflow,
            }
        except Exception as e:
            return {"reply": f"修改工作流时出错：{e}", "workflow": session.workflow}

    def _build_workflow(self, args: dict) -> dict:
        assignees = {}
        for a in args.get("assignees", []):
            assignees[a["key"]] = {
                "role": a["role"],
                "description": a.get("description", ""),
            }

        actions = []
        for i, a in enumerate(args.get("actions", [])):
            action = {
                "id": f"action_{i + 1}",
                "type": a["type"],
                "name": a["name"],
                "description": a.get("description", ""),
                "order": a.get("order", i + 1),
                "assignee": None,
                "custom_data": a.get("custom_data", {}),
            }
            if a.get("assignee_ref") and a["assignee_ref"] in assignees:
                ref = a["assignee_ref"]
                action["assignee"] = {
                    "ref": ref,
                    "role": assignees[ref]["role"],
                }
            actions.append(action)

        return {
            "id": f"wf_{uuid.uuid4().hex[:8]}",
            "name": args["name"],
            "description": args.get("description", ""),
            "version": "1.0",
            "assignees": assignees,
            "actions": actions,
        }

    def _validate_workflow(self, workflow: dict):
        registered_types = set(self._registry.list_types())
        assignee_keys = set(workflow.get("assignees", {}).keys())

        for action in workflow.get("actions", []):
            if action["type"] not in registered_types:
                raise ValueError(
                    f"未知的 action 类型: {action['type']}，可用类型: {', '.join(sorted(registered_types))}"
                )
            if action.get("assignee") and action["assignee"].get("ref"):
                ref = action["assignee"]["ref"]
                if ref not in assignee_keys:
                    raise ValueError(
                        f"action '{action['name']}' 引用了不存在的 assignee: {ref}"
                    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_agent.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/agent/workflow_agent.py tests/test_agent.py
git commit -m "feat: implement WorkflowAgent core engine with create/modify handling"
```

---

### Task 9: API 路由层

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/chat.py`
- Modify: `app/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: 编写 API 测试**

```python
# tests/test_api.py
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.llm.client import LLMResponse, ToolCall


def _mock_create_workflow_response():
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(
            call_id="call_1",
            function_name="create_workflow",
            arguments={
                "name": "费用审批",
                "description": "费用报销审批流程",
                "assignees": [
                    {"key": "employee", "role": "Employee", "description": "员工"},
                ],
                "actions": [
                    {
                        "type": "form_action",
                        "name": "费用提交",
                        "description": "填写报销表",
                        "order": 1,
                        "assignee_ref": "employee",
                        "custom_data": {"fields": []},
                    }
                ],
            },
        )],
    )


def _mock_text_response():
    return LLMResponse(
        content="你好！请告诉我你想创建什么工作流。",
        tool_calls=None,
    )


class TestChatAPI:
    @patch("app.api.chat._get_agent")
    def test_chat_generates_workflow(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.process.return_value = {
            "session_id": "s1",
            "reply": "已为您生成工作流「费用审批」。",
            "workflow": {"name": "费用审批", "actions": []},
        }
        mock_get_agent.return_value = mock_agent

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={
            "message": "创建一个费用审批流程",
        })

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["reply"] is not None
        assert data["workflow"]["name"] == "费用审批"

    @patch("app.api.chat._get_agent")
    def test_chat_with_session_id(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.process.return_value = {
            "session_id": "existing-session",
            "reply": "你好！",
            "workflow": None,
        }
        mock_get_agent.return_value = mock_agent

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={
            "session_id": "existing-session",
            "message": "你好",
        })

        assert response.status_code == 200
        assert response.json()["session_id"] == "existing-session"

    def test_chat_missing_message(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={})
        assert response.status_code == 422


class TestActionsAPI:
    def test_list_actions(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/workflow/actions")
        assert response.status_code == 200
        data = response.json()
        types = [a["type"] for a in data["actions"]]
        assert "form_action" in types
        assert "approval_action" in types
        assert "email_action" in types
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_api.py -v`
Expected: FAIL，导入错误

- [ ] **Step 3: 实现 API 路由**

```python
# app/api/__init__.py
# (empty)
```

```python
# app/api/chat.py
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.actions import registry
from app.agent.session import SessionManager
from app.agent.workflow_agent import WorkflowAgent
from app.config import get_settings
from app.llm.client import LLMClient

router = APIRouter()

_session_manager = SessionManager()
_agent: WorkflowAgent | None = None


def _get_agent() -> WorkflowAgent:
    global _agent
    if _agent is None:
        settings = get_settings()
        llm_client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
        _agent = WorkflowAgent(
            llm_client=llm_client,
            registry=registry,
            session_manager=_session_manager,
        )
    return _agent


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    workflow: dict | None = None


class ActionInfo(BaseModel):
    type: str
    display_name: str
    description: str


class ActionsResponse(BaseModel):
    actions: list[ActionInfo]


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    session_id = request.session_id or uuid.uuid4().hex[:12]
    agent = _get_agent()

    try:
        result = agent.process(session_id, request.message)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(**result)


@router.get("/api/workflow/actions", response_model=ActionsResponse)
async def list_actions():
    schemas = registry.get_schemas()
    actions = [
        ActionInfo(
            type=s["action_type"],
            display_name=s["display_name"],
            description=s["description"],
        )
        for s in schemas
    ]
    return ActionsResponse(actions=actions)
```

- [ ] **Step 4: 更新 main.py 注册路由**

```python
# app/main.py
from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(title="Moxo Workflow Agent", version="0.1.0")

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest tests/test_api.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 运行全部测试**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest -v`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add app/api/ app/main.py tests/test_api.py
git commit -m "feat: add /api/chat and /api/workflow/actions endpoints"
```

---

### Task 10: 端到端集成验证

**Files:**
- Modify: `app/actions/__init__.py`（确保已注册）

- [ ] **Step 1: 启动服务并测试 health 端点**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && uvicorn app.main:app --port 8000 &`

Run: `curl -s http://localhost:8000/health | python -m json.tool`
Expected: `{"status": "ok"}`

- [ ] **Step 2: 测试 actions 端点**

Run: `curl -s http://localhost:8000/api/workflow/actions | python -m json.tool`
Expected: 返回包含 form_action、approval_action、email_action 的 JSON

- [ ] **Step 3: 关闭服务**

Run: `kill %1`

- [ ] **Step 4: 最终全量测试**

Run: `cd /Users/bingxinxia/workspace/moxo-agent && python -m pytest -v`
Expected: 全部 PASS

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "chore: final integration verification"
```
