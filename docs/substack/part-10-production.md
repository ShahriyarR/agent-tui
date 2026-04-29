# Building AI Coding Agents with DeepAgents — Part 10: Production Considerations

> Deploy and operate your agent at scale with confidence.

---

## This Series in Review

Over the past 9 articles, we've built a coding agent from scratch:

1. **Part 1**: Understood why DeepAgents accelerates development
2. **Part 2**: Created our first agent with `create_deep_agent`
3. **Part 3**: Added custom tools with the `@tool` decorator
4. **Part 4**: Configured filesystem and shell backends
5. **Part 5**: Implemented memory with AGENTS.md
6. **Part 6**: Built an on-demand skills system
7. **Part 7**: Added human-in-the-loop approval workflows
8. **Part 8**: Created a CLI interface
9. **Part 9**: Wrote tests and learned debugging strategies

Now let's make it production-ready.

## Security Checklist

### 1. Access Control

```python
from pathlib import Path

# Restrict agent to specific directories
backend = LocalShellBackend(
    root_dir=Path("/safe/projects"),  # Not root!
    virtual_mode=True
)

# Or via environment
export DEEPAGENTS_ALLOWED_DIRS="/home/user/projects:/tmp/scratch"
```

### 2. Approval for Dangerous Operations

```python
from langchain.agents.middleware import InterruptOnConfig

interrupt_on = InterruptOnConfig(
    tools={
        "execute": True,        # Shell commands need approval
        "write_file": True,     # Writes need approval
        "edit_file": True,      # Edits need approval
        "delete_file": True,    # Deletes need approval
    }
)
```

### 3. Input Validation

```python
from pydantic import BaseModel, validator

class SafePath(BaseModel):
    path: str
    
    @validator('path')
    def no_traversal(cls, v):
        if '..' in v or v.startswith('/'):
            raise ValueError('Path traversal not allowed')
        return v

@tool
def safe_read_file(path: str) -> str:
    """Read a file with path validation."""
    validated = SafePath(path=path)
    # Proceed with validated.path
```

### 4. API Key Management

```python
import os
from dataclasses import dataclass

@dataclass
class Secrets:
    """Load secrets from environment only."""
    openai_key: str
    tavily_key: str | None
    
    @classmethod
    def load(cls):
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY required")
        
        return cls(
            openai_key=openai_key,
            tavily_key=os.getenv("TAVILY_API_KEY")
        )

# Never hardcode secrets!
# BAD: agent = create_deep_agent(api_key="sk-...")
# GOOD: agent = create_deep_agent(api_key=secrets.openai_key)
```

## Performance Optimization

### 1. Connection Pooling

```python
import httpx
from langchain.tools import tool

# Reuse HTTP client
_http_client = httpx.AsyncClient(timeout=30)

@tool
async def fetch_url(url: str) -> str:
    """Fetch URL with connection reuse."""
    response = await _http_client.get(url)
    return response.text[:10000]
```

### 2. Response Caching

```python
from functools import lru_cache
from langchain.tools import tool

@tool
@lru_cache(maxsize=100)
def search_docs_cached(query: str) -> str:
    """Search documentation (cached)."""
    # Expensive operation here
    return results
```

### 3. Streaming for Long Operations

```python
# Always stream for user-facing agents
async for event in agent.astream_events({...}, config):
    if event.get("event") == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        yield chunk.content  # User sees progress
```

### 4. Context Window Management

```python
# Monitor token usage
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = agent.invoke({...}, config)
    print(f"Tokens: {cb.total_tokens}")
    print(f"Cost: ${cb.total_cost:.4f}")
```

## Observability

### 1. Structured Logging

```python
import logging
import json
from pythonjsonlogger import jsonlogger

# JSON logging for production
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger("agent")
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Log structured events
logger.info("Tool executed", extra={
    "tool_name": tool_name,
    "duration_ms": duration,
    "success": success
})
```

### 2. Metrics Collection

```python
from prometheus_client import Counter, Histogram

tool_calls = Counter('agent_tool_calls_total', 'Total tool calls', ['tool_name'])
tool_duration = Histogram('agent_tool_duration_seconds', 'Tool execution time')

@tool
def my_tool():
    with tool_duration.time():
        result = do_work()
        tool_calls.labels(tool_name="my_tool").inc()
        return result
```

### 3. Tracing

```python
from langsmith import Client
from langchain.callbacks.tracers import LangChainTracer

# Enable LangSmith tracing
tracer = LangChainTracer(
    project_name="my-agent",
    client=Client()
)

agent = create_deep_agent(
    callbacks=[tracer]
)
```

## Deployment Options

### Option 1: CLI Tool

```bash
# Package as pip-installable CLI
pip install my-agent-cli
my-agent --model openai:gpt-4o
```

### Option 2: Library

```python
# Import and embed in other applications
from my_agent import create_coding_agent

agent = create_coding_agent(
    model="openai:gpt-4o",
    project_root="./my-project"
)
```

### Option 3: Server (API)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/chat")
async def chat(message: str, thread_id: str):
    async def event_generator():
        async for event in agent.astream_events({...}, config):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Error Handling Strategy

```python
from enum import Enum

class ErrorSeverity(Enum):
    WARNING = "warning"      # Log and continue
    ERROR = "error"          # Log and notify
    CRITICAL = "critical"    # Stop and alert

async def handle_agent_error(error: Exception, severity: ErrorSeverity):
    if severity == ErrorSeverity.CRITICAL:
        await alert_oncall(error)
        raise  # Stop execution
    elif severity == ErrorSeverity.ERROR:
        logger.error(f"Agent error: {error}")
        await notify_user(error)
    else:
        logger.warning(f"Agent warning: {error}")
```

## Maintenance Best Practices

### 1. Version Pinning

```toml
# pyproject.toml
[project]
dependencies = [
    "deepagents>=0.1.0,<0.2.0",
    "langchain-openai>=0.1.0,<0.2.0",
    "langgraph>=0.0.50,<0.1.0",
]
```

### 2. Health Checks

```python
@app.get("/health")
async def health_check():
    """Verify agent and dependencies are healthy."""
    checks = {
        "agent": check_agent_initializes(),
        "openai": check_openai_connection(),
        "filesystem": check_backend_accessible()
    }
    
    all_healthy = all(checks.values())
    status = 200 if all_healthy else 503
    
    return JSONResponse(
        content={"healthy": all_healthy, "checks": checks},
        status_code=status
    )
```

### 3. Graceful Degradation

```python
async def safe_tool_call(tool_name: str, args: dict) -> str:
    """Call tool with fallback on failure."""
    try:
        return await call_tool(tool_name, args)
    except ToolError as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return f"Error: Could not execute {tool_name}"
```

## Structured Output Best Practices

### 1. Schema Design

Design schemas that match your domain:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class ProductionMetric(BaseModel):
    """Metrics for production monitoring."""
    metric_name: str = Field(description="Name of the metric")
    value: float = Field(description="Current value")
    unit: str = Field(description="Unit of measurement")
    timestamp: str = Field(description="ISO 8601 timestamp")
    
    @validator('value')
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError("Metric value must be non-negative")
        return v

class Alert(BaseModel):
    """Production alert structure."""
    severity: str = Field(description="'critical', 'warning', or 'info'")
    service: str = Field(description="Affected service")
    message: str = Field(description="Alert description")
    metrics: List[ProductionMetric] = Field(description="Related metrics")
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed = {'critical', 'warning', 'info'}
        if v not in allowed:
            raise ValueError(f"Severity must be one of {allowed}")
        return v
```

### 2. Versioning Schemas

Version your schemas for backward compatibility:

```python
class ApiResponseV1(BaseModel):
    """API response schema version 1."""
    status: str
    data: dict

class ApiResponseV2(BaseModel):
    """API response schema version 2 with metadata."""
    status: str
    data: dict
    metadata: dict
    request_id: str

# Use versioned schemas
RESPONSE_SCHEMAS = {
    "v1": ApiResponseV1,
    "v2": ApiResponseV2,
}

def create_agent_with_version(version: str = "v2"):
    schema = RESPONSE_SCHEMAS.get(version, ApiResponseV2)
    return create_deep_agent(
        model="openai:gpt-4o",
        response_format=schema
    )
```

### 3. Handling Partial Data

Use Optional fields for potentially missing data:

```python
class AnalysisResult(BaseModel):
    """Analysis with optional fields for incomplete data."""
    primary_finding: str
    confidence_score: float
    secondary_findings: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    metadata: Optional[dict] = None
```

## Cost Management

### 1. Token Budgets

```python
class BudgetManager:
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.used_tokens = 0
    
    def check_budget(self, estimated_tokens: int) -> bool:
        if self.used_tokens + estimated_tokens > self.max_tokens:
            raise BudgetExceeded("Token budget exhausted")
        self.used_tokens += estimated_tokens
        return True
```

### 2. Model Selection

```python
# Use cheaper models for simple tasks
def select_model(complexity: str) -> str:
    models = {
        "simple": "openai:gpt-4o-mini",    # $0.15/M tokens
        "complex": "openai:gpt-4o",         # $2.50/M tokens
    }
    return models.get(complexity, models["complex"])
```

## What You've Built

Congratulations! You now have:

✅ A production-ready coding agent CLI  
✅ With file and shell access  
✅ Human approval for safety  
✅ Persistent memory  
✅ On-demand skills  
✅ **Structured output** with Pydantic schemas  
✅ Comprehensive tests  
✅ Security controls  
✅ Monitoring and observability  

### Structured Output Throughout

You've implemented structured output across the entire system:

| Component | Schema Purpose |
|-----------|----------------|
| **Part 2** | Typed responses for programmatic use |
| **Part 3** | Tool inputs (`args_schema`) and outputs (`response_format`) |
| **Part 4** | File analysis results with code quality metrics |
| **Part 5** | Persistent preference storage |
| **Part 6** | Skill-based test generation |
| **Part 7** | Approval decision tracking |
| **Part 8** | CLI command outputs (JSON/text modes) |
| **Part 9** | Schema validation in tests |
| **Part 10** | Production monitoring metrics and alerts |  

## Next Steps

1. **Add more skills** — Database, deployment, testing
2. **Improve the UI** — Rich formatting, syntax highlighting
3. **Add voice input** — Speech-to-text integration
4. **Build a team** — Multi-agent collaboration
5. **Share your agent** — Open source it!

## Resources

- [DeepAgents Documentation](https://github.com/langchain-ai/deepagents/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools Guide](https://python.langchain.com/docs/how_to/custom_tools/)

## Thank You

You've completed the series! You now have the knowledge to build sophisticated AI agents with DeepAgents.

Happy building! 🚀

---

*Previous: [Part 9: Testing and Debugging](part-9-testing.md)*
