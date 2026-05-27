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
