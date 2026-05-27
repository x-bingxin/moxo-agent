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
