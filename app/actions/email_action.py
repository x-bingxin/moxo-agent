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
