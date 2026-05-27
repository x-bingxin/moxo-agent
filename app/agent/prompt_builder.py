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
