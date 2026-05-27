# app/models/workflow.py
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.action import ActionDefinition


class WorkflowAssignee(BaseModel):
    role: str
    description: str = ""


class Workflow(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    assignees: dict[str, WorkflowAssignee] = {}
    actions: list[ActionDefinition] = []
