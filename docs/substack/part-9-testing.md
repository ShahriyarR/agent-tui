# Building AI Coding Agents with DeepAgents — Part 9: Testing and Debugging

> Ensure your agent works reliably with unit tests, integration tests, and debugging strategies.

---

## Testing Strategy

Agent applications need three types of tests:

| Test Type | What It Tests | Speed |
|-----------|---------------|-------|
| **Unit** | Individual components | Fast |
| **Integration** | Agent + tools together | Medium |
| **E2E** | Full user workflows | Slow |

## Unit Testing Components

Test individual pieces in isolation:

```python
# test_translator.py
import pytest
from src.translator import EventTranslator

def test_translate_message_chunk():
    translator = EventTranslator()
    
    event = {
        "event": "on_chat_model_stream",
        "data": {
            "chunk": type("Chunk", (), {"content": "Hello"})()
        }
    }
    
    results = list(translator.translate(event))
    
    assert len(results) == 1
    assert results[0].type == EventType.MESSAGE_CHUNK
    assert results[0].text == "Hello"

def test_translate_tool_call():
    translator = EventTranslator()
    
    event = {
        "event": "on_tool_start",
        "name": "read_file",
        "run_id": "tool-123",
        "data": {
            "input": {"file_path": "test.py"}
        }
    }
    
    results = list(translator.translate(event))
    
    assert results[0].type == EventType.TOOL_CALL
    assert results[0].tool_name == "read_file"
    assert results[0].tool_args["file_path"] == "test.py"
```

## Mocking the Agent

Test your CLI without calling real LLMs:

```python
# test_cli.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.cli import AgentCLI

@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    return adapter

@pytest.fixture
def cli(mock_adapter):
    return AgentCLI(adapter=mock_adapter)

@pytest.mark.asyncio
async def test_cli_processes_message(cli, mock_adapter):
    # Arrange
    mock_adapter.stream.return_value = [
        AgentEvent(type=EventType.MESSAGE_CHUNK, text="Hello"),
        AgentEvent(type=EventType.MESSAGE_END)
    ]
    
    # Act
    await cli._process_message("Hi there")
    
    # Assert
    mock_adapter.stream.assert_called_once_with(
        "Hi there", 
        "default"
    )
```

## Testing with StubAgent

Create a stub implementation for integration tests:

```python
# stub_agent.py
from typing import AsyncIterator
import asyncio

class StubAgent:
    """Stub implementation for testing without API calls."""
    
    async def stream(self, message: str, thread_id: str = None) -> AsyncIterator[AgentEvent]:
        # Simulate thinking
        yield AgentEvent(
            type=EventType.MESSAGE_CHUNK, 
            text=f"I received: {message}\n"
        )
        
        # Simulate a tool call if message contains specific words
        if "read" in message.lower():
            yield AgentEvent(
                type=EventType.TOOL_CALL,
                tool_name="read_file",
                tool_args={"file_path": "example.txt"},
                tool_id="stub-123"
            )
            
            yield AgentEvent(
                type=EventType.TOOL_RESULT,
                tool_name="read_file",
                tool_output="File contents here"
            )
        
        yield AgentEvent(type=EventType.MESSAGE_END)
    
    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        pass
    
    async def cancel(self) -> None:
        pass
```

## Integration Testing

Test agent + tools together:

```python
# test_integration.py
import pytest
import tempfile
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        project_dir = Path(tmpdir)
        (project_dir / "main.py").write_text("print('hello')")
        (project_dir / "test_main.py").write_text("def test_main(): pass")
        yield project_dir

@pytest.mark.asyncio
async def test_agent_reads_files(temp_project):
    backend = LocalShellBackend(
        root_dir=temp_project,
        virtual_mode=True
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o",
        backend=backend
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    result = agent.invoke({
        "messages": [{
            "role": "user", 
            "content": "List the Python files"
        }]
    }, config)
    
    # Verify the agent used the ls tool
    # (This depends on your specific implementation)
```

## Debugging Techniques

### 1. Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# DeepAgents logs
deepagents_logger = logging.getLogger("deepagents")
deepagents_logger.setLevel(logging.DEBUG)
```

### 2. Event Inspection

```python
async def debug_stream(agent, message, config):
    """Print all events for debugging."""
    async for event in agent.astream_events({
        "messages": [{"role": "user", "content": message}]
    }, config):
        print(f"\n{'='*50}")
        print(f"Event Type: {event.get('event')}")
        print(f"Data: {event.get('data')}")
        print(f"Run ID: {event.get('run_id')}")
```

### 3. Tool Call Tracing

```python
class TracedAdapter:
    """Wrapper that logs all tool calls."""
    
    def __init__(self, base_adapter):
        self.base = base_adapter
        self.tool_history = []
    
    async def stream(self, message: str, thread_id: str = None):
        async for event in self.base.stream(message, thread_id):
            if event.type == EventType.TOOL_CALL:
                self.tool_history.append({
                    "tool": event.tool_name,
                    "args": event.tool_args,
                    "thread": thread_id
                })
                print(f"[TRACE] Tool called: {event.tool_name}")
            yield event
```

### 4. State Inspection

```python
# Check conversation state
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

agent = create_deep_agent(
    checkpointer=checkpointer
)

# After some interactions, inspect state
config = {"configurable": {"thread_id": "debug-session"}}
state = checkpointer.get(config)
print(f"Messages: {len(state['messages'])}")
print(f"Last message: {state['messages'][-1]}")
```

## Common Issues and Solutions

### Issue: Agent Not Using Tools

```python
# Check your system prompt
agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=backend,
    system_prompt="""You have access to file tools.
    
USE THEM when the user asks about files.
Don't just say you can't access files."""
)
```

### Issue: Events Not Translating

```python
# Add debugging to translator
def translate(self, event: dict) -> Iterator[AgentEvent]:
    event_type = event.get("event") or event.get("event_type", "")
    
    print(f"[DEBUG] Raw event: {event_type}")
    print(f"[DEBUG] Full event: {event}")
    
    # ... rest of translation logic
```

### Issue: Interrupts Not Working

```python
# Common mistake: forgetting checkpointer
agent = create_deep_agent(
    model="openai:gpt-4o",
    interrupt_on=InterruptOnConfig(tools={"execute": True})
    # WRONG: No checkpointer!
)

# CORRECT
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="openai:gpt-4o",
    checkpointer=MemorySaver(),  # Required!
    interrupt_on=InterruptOnConfig(tools={"execute": True})
)
```

### Issue: Memory Not Persisting

```python
# Check you're using the same thread_id
config1 = {"configurable": {"thread_id": "session-1"}}
config2 = {"configurable": {"thread_id": "session-2"}}

# These are different conversations!
agent.invoke({...}, config1)
agent.invoke({...}, config2)  # Won't see config1's messages
```

## Testing Structured Output

Test your Pydantic schemas to ensure they validate correctly:

```python
# test_schemas.py
import pytest
from pydantic import ValidationError
from src.schemas import CodeReview, CodeIssue

def test_code_issue_valid():
    """Test valid CodeIssue creation."""
    issue = CodeIssue(
        file_path="src/main.py",
        line_number=42,
        severity="warning",
        message="Unused import",
        suggestion="Remove the import"
    )
    assert issue.line_number == 42
    assert issue.severity == "warning"

def test_code_issue_invalid_severity():
    """Test that invalid severity is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        CodeIssue(
            file_path="src/main.py",
            line_number=42,
            severity="invalid",  # Should be 'error', 'warning', or 'info'
            message="Test",
            suggestion="Fix it"
        )
    assert "severity" in str(exc_info.value)

def test_code_review_schema():
    """Test complete CodeReview schema."""
    review = CodeReview(
        summary="Good code overall",
        issues=[
            CodeIssue(
                file_path="src/main.py",
                line_number=10,
                severity="info",
                message="Consider adding docstring",
                suggestion="Add function documentation"
            )
        ],
        score=8
    )
    assert review.score == 8
    assert len(review.issues) == 1
    assert review.issues[0].line_number == 10
```

### Testing Agent with Structured Output

```python
# test_structured_output.py
import pytest
from deepagents import create_deep_agent
from pydantic import BaseModel, Field

class SimpleResult(BaseModel):
    """Simple result for testing."""
    answer: str = Field(description="The answer")
    confidence: int = Field(description="Confidence 0-100")

@pytest.mark.asyncio
async def test_agent_returns_structured_output():
    """Test that agent returns valid structured output."""
    agent = create_deep_agent(
        model="openai:gpt-4o",
        response_format=SimpleResult
    )
    
    result = agent.invoke({
        "messages": [{"role": "user", "content": "Say hello with confidence 95"}]
    })
    
    # Verify structured response exists
    assert "structured_response" in result
    
    # Verify it's the correct type
    structured = result["structured_response"]
    assert isinstance(structured, SimpleResult)
    
    # Verify fields
    assert structured.answer == "hello"
    assert structured.confidence == 95

@pytest.mark.asyncio
async def test_structured_output_validation():
    """Test that invalid structured output is caught."""
    class StrictSchema(BaseModel):
        """Schema with strict validation."""
        count: int = Field(ge=0, le=100, description="Count 0-100")
    
    agent = create_deep_agent(
        model="openai:gpt-4o",
        response_format=StrictSchema
    )
    
    # This should work
    result = agent.invoke({
        "messages": [{"role": "user", "content": "Return count 50"}]
    })
    assert result["structured_response"].count == 50
```

## Testing Checklist

Before shipping your agent:

- [ ] Unit tests for all components
- [ ] Unit tests for Pydantic schemas (validation, edge cases)
- [ ] Integration tests for agent + backend
- [ ] Integration tests for structured output
- [ ] E2E tests for common workflows
- [ ] Error handling verified
- [ ] Tool approval flow tested
- [ ] Memory persistence verified
- [ ] Performance tested with large files
- [ ] Cancellation works correctly

## Exercise

Write tests for:
1. Event translation (all event types)
2. Tool approval flow
3. Error handling in the adapter
4. CLI argument parsing
5. Pydantic schema validation (valid and invalid cases)
6. Structured output from agent responses

## Key Takeaway

Testing agents requires a layered approach: mock at the unit level, stub at the integration level, and use controlled environments for E2E tests. Debug with verbose logging and state inspection.

---

*Previous: [Part 8: Building a CLI](part-8-cli.md)*  
*Next: [Part 10: Production Considerations](part-10-production.md)*
