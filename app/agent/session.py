from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Session:
    session_id: str
    workflow: dict | None = None
    history: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def set_workflow(self, workflow: dict):
        self.workflow = workflow


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self._sessions)
