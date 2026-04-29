# Building AI Coding Agents with DeepAgents — Part 3: Adding Custom Tools

> Extend your agent with domain-specific capabilities using the @tool decorator.

---

## Why Custom Tools?

Built-in tools handle files and planning. But your agent needs domain-specific capabilities:

- Querying a database
- Calling external APIs
- Running tests
- Checking code style
- Fetching documentation

DeepAgents makes adding tools trivial.

## The @tool Decorator

Define a tool with a docstring and type hints:

```python
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.
    
    Args:
        city: The city name (e.g., "Tokyo", "New York")
    
    Returns:
        A weather description string
    """
    return f"The weather in {city} is sunny and 72°F"
```

**The docstring is critical** — the LLM uses it to decide when to call your tool.

## Adding Tools to Your Agent

```python
from deepagents import create_deep_agent
from langchain.tools import tool

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    
    Args:
        expression: Math expression like "2 + 2" or "10 * 5"
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[calculate, get_current_time],
    system_prompt="You are a helpful assistant with math and time tools"
)
```

The agent automatically decides when to use each tool based on the user's request.

## Tool Schemas (Input)

For complex tools, use Pydantic for strict input typing:

```python
from pydantic import BaseModel, Field
from langchain.tools import tool

class SearchQuery(BaseModel):
    query: str = Field(description="The search query")
    max_results: int = Field(default=5, description="Max results to return")

@tool(args_schema=SearchQuery)
def search_docs(query: str, max_results: int = 5) -> str:
    """Search documentation for relevant pages.
    
    Use this when the user asks about specific functions or APIs.
    """
    # Implementation here
    return f"Found {max_results} results for: {query}"
```

## Structured Output (Response Format)

Just as tools benefit from structured input, your agent's responses benefit from structured output. Use `response_format` with Pydantic models:

```python
from pydantic import BaseModel, Field
from deepagents import create_deep_agent

class WeatherReport(BaseModel):
    """A structured weather report."""
    location: str = Field(description="The location")
    temperature: float = Field(description="Current temperature in Celsius")
    condition: str = Field(description="Weather condition (sunny, cloudy, etc.)")
    humidity: int = Field(description="Humidity percentage")
    forecast: str = Field(description="24-hour forecast summary")

agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[web_search],
    response_format=WeatherReport  # Structured output!
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the weather in Paris?"}]
})

# Access structured response
print(result["structured_response"])
# WeatherReport(location='Paris', temperature=22.5, condition='Sunny', ...)
```

### Why Use Structured Output?

| Without `response_format` | With `response_format` |
|---------------------------|------------------------|
| Parse text responses | Get typed objects |
| Handle inconsistent formatting | Validation built-in |
| Manual extraction | Direct property access |
| Error-prone | Reliable and testable |

### Code Analysis Example

```python
from pydantic import BaseModel, Field
from typing import List

class CodeIssue(BaseModel):
    """A single code issue found during analysis."""
    line_number: int = Field(description="Line where issue occurs")
    severity: str = Field(description="'error', 'warning', or 'info'")
    message: str = Field(description="Description of the issue")
    suggestion: str = Field(description="How to fix it")

class CodeReview(BaseModel):
    """Complete code review results."""
    summary: str = Field(description="Overall assessment")
    issues: List[CodeIssue] = Field(description="List of issues found")
    score: int = Field(description="Code quality score 1-10")

agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[read_file],  # From backend
    response_format=CodeReview,
    system_prompt="You are a code reviewer. Analyze files and report issues."
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Review src/main.py"}]
})

review = result["structured_response"]
print(f"Score: {review.score}/10")
for issue in review.issues:
    print(f"Line {issue.line_number}: {issue.message}")
```

### Best Practice: Schema Consistency

Use Pydantic for both tool inputs AND agent outputs:

```python
# Tool input schema
class SearchParams(BaseModel):
    query: str
    filters: dict = {}

# Agent output schema  
class SearchResults(BaseModel):
    query: str
    results: List[dict]
    total_count: int

# Tool uses input schema
@tool(args_schema=SearchParams)
def search_database(query: str, filters: dict = {}) -> str:
    """Search the database."""
    results = db.search(query, filters)
    return json.dumps(results)

# Agent uses output schema
agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[search_database],
    response_format=SearchResults
)
```

## Async Tools

For I/O-bound operations, use async:

```python
import httpx
from langchain.tools import tool

@tool
async def fetch_url(url: str) -> str:
    """Fetch content from a URL.
    
    Args:
        url: The URL to fetch
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        return response.text[:5000]  # Limit response size
```

DeepAgents handles both sync and async tools seamlessly.

## Tool Results and Context

Tools can return structured data:

```python
import json
from langchain.tools import tool

@tool
def list_python_files(directory: str = ".") -> str:
    """List Python files in a directory.
    
    Args:
        directory: Directory path to search
    """
    from pathlib import Path
    
    files = list(Path(directory).glob("*.py"))
    result = {
        "count": len(files),
        "files": [f.name for f in files]
    }
    return json.dumps(result)
```

Return JSON for structured data — the LLM handles it better than plain text.

## Web Search Example

Here's a complete web search tool using Tavily:

```python
import os
import json
from langchain.tools import tool
from tavily import TavilyClient

@tool
def web_search(query: str) -> str:
    """Search the web for current information.
    
    Use this for:
    - Current events and news
    - Recent documentation
    - Facts that might have changed
    
    Args:
        query: The search query
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not configured"
    
    client = TavilyClient(api_key=api_key)
    response = client.search(query, max_results=5)
    
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", "")[:200]
        }
        for r in response.get("results", [])
    ]
    
    return json.dumps({"query": query, "results": results})
```

Add it to your agent:

```python
agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[web_search],
    system_prompt="You can search the web for current information"
)
```

## Best Practices

### 1. Clear Descriptions

```python
# BAD
@tool
def func(x): return x

# GOOD
@tool
def calculate_sum(numbers: list[float]) -> str:
    """Calculate the sum of a list of numbers.
    
    Use this for adding multiple values together.
    
    Args:
        numbers: List of numbers to sum
    """
    return str(sum(numbers))
```

### 2. Use Structured Output

Always use `response_format` with Pydantic models for reliable, typed responses:

```python
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    findings: list[str]
    recommendation: str
    confidence: float

agent = create_deep_agent(
    model="openai:gpt-4o",
    tools=[my_tool],
    response_format=AnalysisResult  # Enforces structure
)

result = agent.invoke({...})
analysis = result["structured_response"]  # Typed object
print(analysis.confidence)  # Direct access, no parsing
```

### 3. Error Handling

```python
@tool
def read_config(path: str) -> str:
    """Read a configuration file."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
```

### 4. Limit Output Size

```python
@tool
def read_large_file(path: str) -> str:
    """Read a file (truncated to 10KB)."""
    with open(path) as f:
        return f.read(10000)  # Limit size
```

## Exercise

Create a tool that:
1. Takes a Python file path
2. Runs `flake8` on it
3. Returns the style issues found

```python
from langchain.tools import tool
import subprocess

@tool
def check_style(file_path: str) -> str:
    """Check Python code style with flake8."""
    # Your implementation here
    pass
```

## Key Takeaway

Tools are just functions with good documentation. DeepAgents handles the hard parts — calling them, passing arguments, and returning results to the LLM.

**Best Practice**: Use Pydantic schemas for both tool inputs (`args_schema`) and agent outputs (`response_format`). Structured data is more reliable than text parsing.

---

*Previous: [Part 2: Your First Agent](part-2-first-agent.md)*  
*Next: [Part 4: Filesystem and Shell Backends](part-4-backends.md)*
