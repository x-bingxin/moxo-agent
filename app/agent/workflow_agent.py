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
            return {"reply": f"生成工作流时发生错误：{e}", "workflow": None}

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
            return {"reply": f"修改工作流时发生错误：{e}", "workflow": session.workflow}

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
