import json
from unittest.mock import MagicMock, patch

import pytest

from app.llm.client import LLMClient, LLMResponse


class TestLLMClient:
    def _make_mock_response(self, content=None, tool_calls=None):
        """构造 mock OpenAI ChatCompletion 响应"""
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_chat_without_tools(self):
        mock_response = self._make_mock_response(content="你好！")

        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")
            result = client.chat(messages=[{"role": "user", "content": "你好"}])

        assert isinstance(result, LLMResponse)
        assert result.content == "你好！"
        assert result.tool_calls is None

    def test_chat_with_tool_calls(self):
        tool_call = MagicMock()
        tool_call.id = "call_1"
        tool_call.function.name = "create_workflow"
        tool_call.function.arguments = json.dumps({"name": "测试流程", "actions": []})

        mock_response = self._make_mock_response(content=None, tool_calls=[tool_call])

        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")
            result = client.chat(
                messages=[{"role": "user", "content": "创建流程"}],
                tools=[{"type": "function", "function": {"name": "create_workflow"}}],
            )

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].function_name == "create_workflow"
        assert result.tool_calls[0].arguments["name"] == "测试流程"

    def test_api_error_raises(self):
        with patch("app.llm.client.OpenAI") as MockOpenAI:
            mock_client = MockOpenAI.return_value
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            client = LLMClient(api_key="test-key", base_url="http://test", model="test-model")

            with pytest.raises(RuntimeError, match="LLM 调用失败"):
                client.chat(messages=[{"role": "user", "content": "测试"}])
