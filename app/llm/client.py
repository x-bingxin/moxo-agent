import json
from dataclasses import dataclass, field

from openai import OpenAI


@dataclass
class ToolCall:
    call_id: str
    function_name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None = None


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        try:
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            print("MESSAGES: ", messages)
            print("TOOLS: ", tools)

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            tool_calls = None
            if message.tool_calls:
                tool_calls = []
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        call_id=tc.id,
                        function_name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    ))

            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
            )
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e
