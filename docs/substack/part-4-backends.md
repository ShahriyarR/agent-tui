# Building AI Coding Agents with DeepAgents — Part 4: Filesystem and Shell Backends

> Give your agent safe access to files and shell commands.

---

## The Backend Pattern

Backends provide context to your agent. Without a backend, the agent has no access to files or the shell.

DeepAgents provides several backends:

| Backend | Best For |
|---------|----------|
| `FilesystemBackend` | Read-only file operations |
| `LocalShellBackend` | File operations + shell commands |
| `StoreBackend` | In-memory/virtual filesystem |

## LocalShellBackend: The All-in-One Solution

For coding agents, `LocalShellBackend` is the go-to choice. It provides:

- **File operations**: `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`
- **Shell execution**: `execute` tool for running commands

```python
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from pathlib import Path

backend = LocalShellBackend(
    root_dir=Path.cwd(),      # Root for all operations
    virtual_mode=True,        # Treat root_dir as virtual root
    inherit_env=True,         # Inherit current environment
)

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=backend,
    system_prompt="You are a coding assistant with file and shell access"
)
```

## Virtual Mode Explained

With `virtual_mode=True`:

```
Agent sees:    /src/main.py
Actually is:   /home/user/project/src/main.py
```

This keeps paths clean in the LLM's context while operating on real files.

```python
# In virtual mode, both work:
agent.invoke({
    "messages": [{"role": "user", "content": "Read /src/main.py"}]
}, config)

agent.invoke({
    "messages": [{"role": "user", "content": "Read src/main.py"}]
}, config)
```

## Shell Command Safety

The `execute` tool runs commands in the `root_dir`:

```python
# User asks: "Run the tests"
# Agent executes:
execute(command="pytest tests/")
# Runs in: /home/user/project (the root_dir)
```

**Security considerations**:
- Commands run with the user's permissions
- Environment variables are inherited by default
- No sandboxing — this is not a security boundary

For production, consider:
- Restricting `root_dir` to a specific project directory
- Setting `inherit_env=False` for sensitive environments
- Using `DEEPAGENTS_ALLOWED_DIRS` environment variable

## Complete Example: File Analysis Agent

```python
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain.tools import tool

# Create backend rooted at current directory
backend = LocalShellBackend(
    root_dir=Path.cwd(),
    virtual_mode=True,
    inherit_env=True,
)

# Optional: Add web search
@tool
def web_search(query: str) -> str:
    """Search for Python documentation."""
    # Implementation from Part 3
    pass

# Define structured output for code reviews
class CodeIssue(BaseModel):
    """A single code issue."""
    file_path: str = Field(description="File where issue was found")
    line_number: int = Field(description="Line number of the issue")
    severity: str = Field(description="'error', 'warning', or 'info'")
    message: str = Field(description="Description of the issue")
    suggestion: str = Field(description="How to fix it")

class CodeReview(BaseModel):
    """Structured code review results."""
    summary: str = Field(description="Overall assessment")
    issues: List[CodeIssue] = Field(description="List of issues found")
    score: int = Field(description="Code quality score 1-10")

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=backend,
    tools=[web_search],
    response_format=CodeReview,  # Get structured review output
    system_prompt="""You are a Python code reviewer.

When asked to review code:
1. Read the relevant files
2. Analyze for bugs, style issues, and improvements
3. Run tests if available
4. Provide structured feedback"""
)

# Use the agent
config = {"configurable": {"thread_id": "review-session"}}
result = agent.invoke({
    "messages": [{
        "role": "user", 
        "content": "Review the src/ directory and run tests"
    }]
}, config)

# Access structured review data
review = result["structured_response"]
print(f"Code Quality Score: {review.score}/10")
print(f"Summary: {review.summary}")
for issue in review.issues:
    print(f"  {issue.severity.upper()}: {issue.file_path}:{issue.line_number}")
    print(f"    {issue.message}")
    print(f"    Suggestion: {issue.suggestion}")
```

## Restricting Access

Control what the agent can access:

```python
from pathlib import Path

# Only allow access to specific directories
backend = LocalShellBackend(
    root_dir=Path("/home/user/projects/myapp"),
    virtual_mode=True,
)
```

Or via environment variable:

```bash
export DEEPAGENTS_ALLOWED_DIRS="/home/user/projects:/tmp/scratch"
```

## Watching Operations

To monitor what the agent does:

```python
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

backend = LocalShellBackend(
    root_dir=Path.cwd(),
    virtual_mode=True,
)

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=backend
)

# Stream events to see tool calls
async for event in agent.astream_events({...}, config):
    if event.get("event") == "on_tool_start":
        print(f"Tool: {event.get('name')}")
        print(f"Input: {event['data'].get('input')}")
```

## Common Patterns

### Reading Multiple Files

The agent handles this automatically:

```
User: "Compare main.py and utils.py"

Agent:
1. Calls read_file("main.py")
2. Calls read_file("utils.py")  
3. Analyzes and responds
```

### Running Tests

```
User: "Run the test suite"

Agent:
1. Calls ls(".") to find test directory
2. Calls execute("pytest tests/ -v")
3. Reports results
```

### Editing Files

```
User: "Add error handling to the fetch_data function"

Agent:
1. Calls grep("def fetch_data") to find the function
2. Calls read_file to see current implementation
3. Calls edit_file with changes
4. Verifies with read_file
```

## Exercise

Create an agent that:
1. Lists all Python files in the current directory
2. Reads each file
3. Reports the total lines of code
4. Identifies any files without docstrings

```python
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from pathlib import Path

# Your implementation here
```

## Key Takeaway

The backend is the bridge between your agent and the filesystem. `LocalShellBackend` provides everything a coding agent needs: file operations and shell execution, all rooted at a directory you control.

---

*Previous: [Part 3: Custom Tools](part-3-custom-tools.md)*  
*Next: [Part 5: Memory and AGENTS.md](part-5-memory.md)*
