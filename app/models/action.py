# app/models/action.py
from typing import Any

from pydantic import BaseModel

from app.models.assignee import AssigneeRef


class ActionDependency(BaseModel):
    triggered_by: str
    condition: str | None = None


class ActionDefinition(BaseModel):
    id: str
    type: str
    name: str
    description: str
    order: int
    assignee: AssigneeRef | None = None
    custom_data: dict[str, Any] = {}
    dependencies: ActionDependency | None = None
