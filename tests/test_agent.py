import json
from unittest.mock import MagicMock

import pytest

from app.agent.workflow_agent import WorkflowAgent
from app.agent.session import SessionManager
from app.llm.client import LLMResponse, ToolCall
from app.actions import registry


class TestWorkflowAgent:
    def _make_agent(self, mock_response: LLMResponse) -> WorkflowAgent:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_response
        session_mgr = SessionManager()
        return WorkflowAgent(
            llm_client=mock_client,
            registry=registry,
            session_manager=session_mgr,
        )

    def test_generate_new_workflow(self):
        workflow_data = {
            "name": "费用审批",
            "description": "费用报销审批流程",
            "assignees": [
                {"key": "employee", "role": "Employee", "description": "提交报销的员工"},
                {"key": "manager", "role": "Manager", "description": "审批经理"},
            ],
            "actions": [
                {
                    "type": "form_action",
                    "name": "费用提交",
                    "description": "填写报销表",
                    "order": 1,
                    "assignee_ref": "employee",
                    "custom_data": {"fields": []},
                }
            ],
        }

        mock_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments=workflow_data,
            )],
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-1", "创建一个费用审批流程")

        assert result["reply"] is not None
        assert result["workflow"] is not None
        assert result["workflow"]["name"] == "费用审批"
        assert result["session_id"] == "session-1"

    def test_text_reply_without_tool_call(self):
        mock_response = LLMResponse(
            content="你好！请告诉我你想创建什么样的工作流。",
            tool_calls=None,
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-2", "你好")

        assert result["reply"] == "你好！请告诉我你想创建什么样的工作流。"
        assert result["workflow"] is None

    def test_modify_existing_workflow(self):
        # 先创建一个 workflow
        create_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments={
                    "name": "费用审批",
                    "description": "流程",
                    "assignees": [
                        {"key": "employee", "role": "Employee", "description": "员工"},
                    ],
                    "actions": [
                        {
                            "type": "form_action",
                            "name": "提交",
                            "description": "提交表单",
                            "order": 1,
                            "assignee_ref": "employee",
                            "custom_data": {"fields": []},
                        }
                    ],
                },
            )],
        )

        mock_client = MagicMock()
        mock_client.chat.return_value = create_response
        session_mgr = SessionManager()

        agent = WorkflowAgent(
            llm_client=mock_client,
            registry=registry,
            session_manager=session_mgr,
        )
        agent.process("session-3", "创建流程")

        # 然后修改 workflow
        modify_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_2",
                function_name="modify_workflow",
                arguments={
                    "operations": [
                        {
                            "type": "insert",
                            "position": 2,
                            "action_data": {
                                "type": "approval_action",
                                "name": "审批",
                                "description": "经理审批",
                                "order": 2,
                                "assignee_ref": "employee",
                                "custom_data": {"approver_role": "Manager", "available_actions": ["approve", "reject"]},
                            },
                        }
                    ]
                },
            )],
        )
        mock_client.chat.return_value = modify_response
        result = agent.process("session-3", "加一个审批步骤")

        assert result["workflow"] is not None
        assert len(result["workflow"]["actions"]) == 2

    def test_invalid_action_type_in_response(self):
        workflow_data = {
            "name": "测试",
            "description": "测试",
            "assignees": [],
            "actions": [
                {
                    "type": "nonexistent_action",
                    "name": "测试",
                    "description": "测试",
                    "order": 1,
                    "custom_data": {},
                }
            ],
        }

        mock_response = LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                call_id="call_1",
                function_name="create_workflow",
                arguments=workflow_data,
            )],
        )

        agent = self._make_agent(mock_response)
        result = agent.process("session-4", "创建流程")

        assert "错误" in result["reply"] or "error" in result["reply"].lower()
        assert result["workflow"] is None
