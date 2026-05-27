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
