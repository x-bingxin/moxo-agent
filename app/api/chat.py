import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.actions import registry
from app.agent.session import SessionManager
from app.agent.workflow_agent import WorkflowAgent
from app.config import get_settings
from app.llm.client import LLMClient

router = APIRouter()

_session_manager = SessionManager()
_agent: WorkflowAgent | None = None


def _get_agent() -> WorkflowAgent:
    global _agent
    if _agent is None:
        settings = get_settings()
        llm_client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
        _agent = WorkflowAgent(
            llm_client=llm_client,
            registry=registry,
            session_manager=_session_manager,
        )
    return _agent


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    workflow: dict | None = None


class ActionInfo(BaseModel):
    type: str
    display_name: str
    description: str


class ActionsResponse(BaseModel):
    actions: list[ActionInfo]


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    session_id = request.session_id or uuid.uuid4().hex[:12]
    agent = _get_agent()

    try:
        result = agent.process(session_id, request.message)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(**result)


@router.get("/api/workflow/actions", response_model=ActionsResponse)
async def list_actions():
    schemas = registry.get_schemas()
    actions = [
        ActionInfo(
            type=s["action_type"],
            display_name=s["display_name"],
            description=s["description"],
        )
        for s in schemas
    ]
    return ActionsResponse(actions=actions)
