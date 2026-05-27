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
