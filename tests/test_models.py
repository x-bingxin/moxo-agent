# tests/test_models.py
import pytest
from pydantic import ValidationError

from app.models.assignee import Assignee, AssigneeRef
from app.models.action import ActionDefinition, ActionDependency
from app.models.workflow import Workflow, WorkflowAssignee


class TestAssignee:
    def test_create_with_role_only(self):
        a = Assignee(role="Employee")
        assert a.role == "Employee"
        assert a.name is None
        assert a.email is None
        assert a.department is None

    def test_create_with_all_fields(self):
        a = Assignee(role="Manager", name="张三", email="zhang@example.com", department="工程部")
        assert a.name == "张三"
        assert a.email == "zhang@example.com"

    def test_role_required(self):
        with pytest.raises(ValidationError):
            Assignee()

    def test_assignee_ref(self):
        ref = AssigneeRef(ref="employee", role="Employee")
        assert ref.ref == "employee"

    def test_assignee_ref_required_fields(self):
        with pytest.raises(ValidationError):
            AssigneeRef()


class TestActionDefinition:
    def test_minimal_action(self):
        action = ActionDefinition(
            id="action_1",
            type="form_action",
            name="费用提交",
            description="填写报销表",
            order=1,
            assignee=None,
            custom_data={},
        )
        assert action.id == "action_1"
        assert action.assignee is None

    def test_action_with_assignee(self):
        action = ActionDefinition(
            id="action_1",
            type="form_action",
            name="费用提交",
            description="填写报销表",
            order=1,
            assignee=AssigneeRef(ref="employee", role="Employee"),
            custom_data={"fields": []},
        )
        assert action.assignee.ref == "employee"

    def test_action_with_dependency(self):
        dep = ActionDependency(triggered_by="action_2", condition="approved")
        action = ActionDefinition(
            id="action_3",
            type="email_action",
            name="通知",
            description="发送通知",
            order=3,
            assignee=None,
            custom_data={},
            dependencies=dep,
        )
        assert action.dependencies.triggered_by == "action_2"


class TestWorkflow:
    def test_create_workflow(self):
        wf = Workflow(
            id="wf_001",
            name="费用审批",
            description="费用报销审批流程",
            version="1.0",
            assignees={
                "employee": WorkflowAssignee(role="Employee", description="提交报销的员工"),
            },
            actions=[
                ActionDefinition(
                    id="action_1",
                    type="form_action",
                    name="费用提交",
                    description="填写报销表",
                    order=1,
                    assignee=AssigneeRef(ref="employee", role="Employee"),
                    custom_data={},
                )
            ],
        )
        assert wf.name == "费用审批"
        assert len(wf.actions) == 1
