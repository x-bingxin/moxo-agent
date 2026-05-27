import pytest

from app.agent.session import Session, SessionManager


class TestSession:
    def test_create_session(self):
        s = Session(session_id="test-1")
        assert s.session_id == "test-1"
        assert s.workflow is None
        assert s.history == []

    def test_add_message(self):
        s = Session(session_id="test-1")
        s.add_message("user", "你好")
        s.add_message("assistant", "你好！")
        assert len(s.history) == 2
        assert s.history[0] == {"role": "user", "content": "你好"}

    def test_set_workflow(self):
        s = Session(session_id="test-1")
        wf = {"name": "测试流程", "actions": []}
        s.set_workflow(wf)
        assert s.workflow == wf


class TestSessionManager:
    def test_get_or_create_new(self):
        mgr = SessionManager()
        session = mgr.get_or_create("new-session")
        assert session.session_id == "new-session"

    def test_get_existing(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("s1")
        s1.add_message("user", "你好")
        s2 = mgr.get_or_create("s1")
        assert len(s2.history) == 1

    def test_multiple_sessions(self):
        mgr = SessionManager()
        mgr.get_or_create("a")
        mgr.get_or_create("b")
        assert mgr.count() == 2

    def test_remove_session(self):
        mgr = SessionManager()
        mgr.get_or_create("to-remove")
        mgr.remove("to-remove")
        assert mgr.count() == 0

    def test_remove_nonexistent_no_error(self):
        mgr = SessionManager()
        mgr.remove("nonexistent")  # 不应抛异常
