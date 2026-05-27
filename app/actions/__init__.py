from app.actions.registry import ActionRegistry
from app.actions.form_action import FormAction
from app.actions.approval_action import ApprovalAction
from app.actions.email_action import EmailAction
from app.actions.todo_action import TodoAction

registry = ActionRegistry()
registry.register(FormAction)
registry.register(ApprovalAction)
registry.register(EmailAction)
registry.register(TodoAction)

__all__ = ["registry", "FormAction", "ApprovalAction", "EmailAction", "TodoAction"]
