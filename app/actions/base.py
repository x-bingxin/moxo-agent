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
