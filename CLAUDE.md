# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Moxo Agent is an AI-powered workflow generator that uses LLM Function Calling to convert natural language into structured workflow JSON definitions. It supports multi-turn conversations for iterative workflow refinement.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_agent.py

# Run with verbose output
pytest -v

# Run with coverage (if pytest-cov installed)
pytest --cov=app
```

### Running the Application
```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type checking
mypy app/

# Linting
ruff check app/ tests/
```

## Architecture

### Core Components

**WorkflowAgent** (`app/agent/workflow_agent.py`)
- Central orchestrator that processes user messages
- Routes LLM responses to `create_workflow` or `modify_workflow` handlers
- Validates generated workflows against registered action types and assignee references
- Uses lazy initialization pattern for LLM client (initialized on first use)

**Action Registry** (`app/actions/`)
- Plugin-like system for action types (form, approval, email)
- Each action inherits from `BaseAction` and defines `custom_data_schema()`
- Actions registered at module load time in `app/actions/__init__.py`
- Registry provides schemas to PromptBuilder for LLM tool definitions

**PromptBuilder** (`app/agent/prompt_builder.py`)
- Dynamically generates system prompts with all registered action schemas
- Builds OpenAI function calling tool definitions
- Injects existing workflow context for multi-turn modifications

**Session Management** (`app/agent/session.py`)
- In-memory session storage (dict-based, no persistence)
- Tracks conversation history and current workflow state
- Session ID can be client-provided or auto-generated

### Data Flow

```
User Message → API Layer → WorkflowAgent
  ↓
PromptBuilder (builds system prompt + tool schemas from registry)
  ↓
LLM Client (OpenAI-compatible API call)
  ↓
Tool Call Handler (create_workflow or modify_workflow)
  ↓
Workflow Validation (action types, assignee refs)
  ↓
Session Update + Response
```

### Key Patterns

**Lazy Agent Initialization** (`app/api/chat.py`)
```python
def _get_agent() -> WorkflowAgent:
    global _agent
    if _agent is None:
        # Initialize only when first needed
        # Allows tests to mock without real LLM credentials
```

**Action Registration** (`app/actions/__init__.py`)
- All action types registered at import time
- New actions: create class inheriting `BaseAction`, add to registry here

**Workflow Structure**
- `assignees`: dict of role definitions (employee, manager, etc.)
- `actions`: list of action instances with `assignee_ref` pointing to global assignees
- `custom_data`: action-type-specific configuration following JSON Schema

## Configuration

Environment variables (`.env` file or shell):
- `LLM_API_KEY`: Required for LLM calls
- `LLM_BASE_URL`: OpenAI-compatible API endpoint (default: DeepSeek)
- `LLM_MODEL`: Model name (default: deepseek-chat)

Settings loaded via `pydantic-settings` in `app/config/settings.py`.

## Testing Strategy

Tests use FastAPI's `TestClient` and mock LLM responses:
- `tests/test_agent.py`: Core workflow generation/modification logic
- `tests/test_api.py`: HTTP endpoints with mocked agent
- `tests/test_actions.py`: Action schema validation
- `tests/test_llm_client.py`: LLM client wrapper with mocked OpenAI

LLM calls are always mocked in tests—never make real API calls.

## Extending the System

### Adding a New Action Type

1. Create `app/actions/your_action.py`:
```python
from app.actions.base import BaseAction

class YourAction(BaseAction):
    @classmethod
    def custom_data_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
```

2. Register in `app/actions/__init__.py`:
```python
from app.actions.your_action import YourAction
registry.register(YourAction)
```

The action automatically becomes available to the LLM via PromptBuilder.

### Adding New LLM Providers

Modify `.env` to point to any OpenAI-compatible API:
```
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
LLM_API_KEY=sk-...
```

## API Endpoints

- `POST /api/chat`: Process user message, generate/modify workflow
  - Request: `{session_id?: str, message: str}`
  - Response: `{session_id: str, reply: str, workflow?: dict}`

- `GET /api/workflow/actions`: List available action types with schemas

- `GET /health`: Health check

## Common Issues

**Import errors when running tests**: Ensure you're using the venv's pytest:
```bash
.venv/bin/python -m pytest
```

**LLM client initialization in tests**: The `_get_agent()` function is lazy to allow mocking. Tests patch `app.api.chat._get_agent` before making requests.

**Action validation failures**: Check that action types in workflow match registered types in `app/actions/__init__.py`, and that `assignee_ref` values exist in the workflow's `assignees` dict.
