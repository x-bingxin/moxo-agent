# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Moxo Agent is an AI-powered workflow generator that uses LLM Function Calling to convert natural language into structured workflow JSON definitions. It supports multi-turn conversations for iterative workflow refinement.

## Development Commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. All commands should be run with `uv run` to use the project's virtual environment.

### Setup
```bash
# Install all dependencies (including dev tools)
uv sync --all-extras

# Add a runtime dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_agent.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=app
```

### Running the Application
```bash
# Start development server
uv run uvicorn app.main:app --reload --port 8000

# Production server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Code Quality
```bash
# Format code
uv run black app/ tests/

# Sort imports
uv run isort app/ tests/

# Type checking
uv run mypy app/

# Linting
uv run ruff check app/ tests/
```

## Architecture

### Core Components

**WorkflowAgent** (`app/agent/workflow_agent.py`)
- Central orchestrator that processes user messages
- Routes LLM responses to `create_workflow` or `modify_workflow` handlers
- Validates generated workflows against registered action types and assignee references
- Uses lazy initialization pattern for LLM client (initialized on first use)

**Action Registry** (`app/actions/`)
- Plugin-like system for action types (form, approval, email, todo)
- Each action inherits from `BaseAction` and defines `custom_data_schema()`
- Actions registered at module load time in `app/actions/__init__.py`
- Registry provides schemas to PromptBuilder for LLM tool definitions

**PromptBuilder** (`app/agent/prompt_builder.py`)
- Dynamically generates system prompts with all registered action schemas
- Builds OpenAI function calling tool definitions (`create_workflow` and `modify_workflow`)
- `modify_workflow` supports four operation types: insert, delete, update, reorder
- Injects existing workflow context for multi-turn modifications

**LLM Client** (`app/llm/client.py`)
- Thin wrapper around OpenAI SDK with `ToolCall` and `LLMResponse` dataclasses
- Supports any OpenAI-compatible API via configurable `base_url`
- All exceptions caught and re-raised as `RuntimeError` with Chinese message

**Pydantic Models** (`app/models/`)
- Defines `Assignee`, `AssigneeRef`, `ActionDefinition`, `ActionDependency`, `Workflow` models
- These models exist for type documentation but are **not used in runtime code**—the agent/session layers pass workflow data as plain dicts

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
- `LLM_BASE_URL`: OpenAI-compatible API endpoint (default: `https://api.deepseek.com`)
- `LLM_MODEL`: Model name (default: `deepseek-chat`)
- `SESSION_TIMEOUT_MINUTES`: Session idle timeout in minutes (default: 60, currently unused)

Settings loaded via `pydantic-settings` in `app/config/settings.py`. See `.env.example` for a template.

## Testing Strategy

Tests use FastAPI's `TestClient` and mock LLM responses:
- `tests/test_agent.py`: Core workflow generation/modification logic
- `tests/test_api.py`: HTTP endpoints with mocked agent
- `tests/test_actions.py`: Action schema validation and registry
- `tests/test_llm_client.py`: LLM client wrapper with mocked OpenAI
- `tests/test_models.py`: Pydantic model validation (Assignee, ActionDefinition, Workflow)
- `tests/test_prompt_builder.py`: System prompt generation, tool definitions, message ordering
- `tests/test_session.py`: Session and SessionManager lifecycle

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

**Import errors when running tests**: Always use `uv run pytest` to ensure the correct virtual environment is used:
```bash
uv run pytest
```

**LLM client initialization in tests**: The `_get_agent()` function is lazy to allow mocking. Tests patch `app.api.chat._get_agent` before making requests.

**Action validation failures**: Check that action types in workflow match registered types in `app/actions/__init__.py`, and that `assignee_ref` values exist in the workflow's `assignees` dict.
