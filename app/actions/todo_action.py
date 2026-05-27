from app.actions.base import BaseAction


class TodoAction(BaseAction):
    action_type = "todo_action"
    display_name = "待办"
    description = "创建一个待办事项，可以指定负责人和截止日期"

    @classmethod
    def custom_data_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "assignee_role": {
                    "type": "string",
                    "description": "负责人的角色，如 Developer、Designer",
                },
                "available_actions": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["complete"]},
                    "description": "负责人可执行的操作",
                },
            },
            "required": ["assignee_role", "available_actions"],
        }
