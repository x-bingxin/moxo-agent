# app/models/assignee.py
from pydantic import BaseModel


class Assignee(BaseModel):
    """全局角色定义"""
    role: str
    name: str | None = None
    email: str | None = None
    department: str | None = None


class AssigneeRef(BaseModel):
    """Action 中对全局 assignee 的引用"""
    ref: str
    role: str
