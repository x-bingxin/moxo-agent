import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.llm.client import LLMResponse, ToolCall


def _mock_create_workflow_response():
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(
            call_id="call_1",
            function_name="create_workflow",
            arguments={
                "name": "费用审批",
                "description": "费用报销审批流程",
                "assignees": [
                    {"key": "employee", "role": "Employee", "description": "员工"},
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
            },
        )],
    )


def _mock_text_response():
    return LLMResponse(
        content="你好！请告诉我你想创建什么工作流。",
        tool_calls=None,
    )


class TestChatAPI:
    @patch("app.api.chat._get_agent")
    def test_chat_generates_workflow(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.process.return_value = {
            "session_id": "s1",
            "reply": "已为您生成工作流「费用审批」。",
            "workflow": {"name": "费用审批", "actions": []},
        }
        mock_get_agent.return_value = mock_agent

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={
            "message": "创建一个费用审批流程",
        })

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["reply"] is not None
        assert data["workflow"]["name"] == "费用审批"

    @patch("app.api.chat._get_agent")
    def test_chat_with_session_id(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.process.return_value = {
            "session_id": "existing-session",
            "reply": "你好！",
            "workflow": None,
        }
        mock_get_agent.return_value = mock_agent

        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={
            "session_id": "existing-session",
            "message": "你好",
        })

        assert response.status_code == 200
        assert response.json()["session_id"] == "existing-session"

    def test_chat_missing_message(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={})
        assert response.status_code == 422


class TestActionsAPI:
    def test_list_actions(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/workflow/actions")
        assert response.status_code == 200
        data = response.json()
        types = [a["type"] for a in data["actions"]]
        assert "form_action" in types
        assert "approval_action" in types
        assert "email_action" in types
