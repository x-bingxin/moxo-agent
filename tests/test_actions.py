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
