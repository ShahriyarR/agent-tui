# Building AI Coding Agents with DeepAgents — Part 2: Your First Agent

> Create a working agent in 10 lines of code.

---

## Installation

First, install the required packages:

```bash
pip install deepagents langchain-openai
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## The Simplest Agent

Here's a fully functional DeepAgent:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-4o",
    system_prompt="You are a helpful coding assistant"
)

# Run it
result = agent.invoke({
    "messages": [{"role": "user", "content": "Hello!"}]
})
print(result["messages"][-1].content)
```

That's it. You now have an agent that can:
- Maintain conversation context
- Use built-in planning tools
- Access the filesystem (with configuration)

## Understanding the Components

### 1. The Model

The `model` parameter uses the format `provider:model`:

```python
# OpenAI models
"openai:gpt-4o"
"openai:gpt-4o-mini"

# Anthropic models
"anthropic:claude-sonnet-4-6"
```

DeepAgents uses `init_chat_model` under the hood, so any LangChain-compatible model works.

### 2. The System Prompt

The `system_prompt` defines your agent's behavior:

```python
agent = create_deep_agent(
    model="openai:gpt-4o",
    system_prompt="""You are a Python expert. 
    
When helping users:
1. Always explain your reasoning
2. Provide working code examples
3. Consider edge cases"""
)
```

Be specific. The system prompt shapes every interaction.

### 3. Conversation Context

DeepAgents maintains context automatically via `thread_id`:

```python
config = {"configurable": {"thread_id": "user-123"}}

# First message
agent.invoke({
    "messages": [{"role": "user", "content": "My name is Alice"}]
}, config)

# Follow-up (remembers the name)
result = agent.invoke({
    "messages": [{"role": "user", "content": "What's my name?"}]
}, config)
# Output: "Your name is Alice."
```

**Important**: Use the same `thread_id` to maintain conversation continuity.

## Streaming Responses

For interactive applications, stream responses instead of waiting:

```python
async for event in agent.astream_events({
    "messages": [{"role": "user", "content": "Explain Python decorators"}]
}, config):
    event_type = event.get("event")
    
    if event_type == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if hasattr(chunk, "content"):
            print(chunk.content, end="", flush=True)
```

This yields tokens as they're generated, essential for real-time UIs.

## Structured Output

For programmatic use, get typed responses instead of text:

```python
from pydantic import BaseModel, Field

class CodeExplanation(BaseModel):
    """Structured explanation of code."""
    concept: str = Field(description="The concept being explained")
    key_points: list[str] = Field(description="Key points to understand")
    example: str = Field(description="A practical code example")

agent = create_deep_agent(
    model="openai:gpt-4o",
    response_format=CodeExplanation
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Explain Python decorators"}]
}, config)

# Access structured data directly
explanation = result["structured_response"]
print(f"Concept: {explanation.concept}")
print(f"Key points: {explanation.key_points}")
print(f"Example:\n{explanation.example}")
```

Structured output is ideal when you need to process the response programmatically rather than just displaying it.

## What You Get For Free

Every DeepAgent has these built-in tools:

| Tool | Purpose |
|------|---------|
| `write_todos` | Track multi-step tasks |
| `ls` | List directory contents |
| `read_file` | Read file contents |
| `write_file` | Write to files |
| `edit_file` | Make targeted file edits |
| `glob` | Find files by pattern |
| `grep` | Search file contents |
| `task` | Spawn specialized subagents |

These tools are **not active by default** — you need to configure a backend first (covered in Part 4).

## Common Mistake

```python
# WRONG: No thread_id
agent.invoke({"messages": [...]})
agent.invoke({"messages": [...]})  # New conversation, no memory

# CORRECT: Consistent thread_id
config = {"configurable": {"thread_id": "session-1"}}
agent.invoke({"messages": [...]}, config)
agent.invoke({"messages": [...]}, config)  # Same conversation
```

## Exercise

Create an agent that:
1. Takes a user's programming question
2. Streams the response
3. Remembers the conversation

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-4o",
    system_prompt="You are a patient Python tutor"
)

config = {"configurable": {"thread_id": "tutorial-session"}}

# Your code here
```

## Key Takeaway

DeepAgents reduces agent creation to **configuration, not code**. In 10 lines, you have a working agent with conversation memory and planning capabilities.

---

*Previous: [Part 1: Why DeepAgents?](part-1-why-deepagents.md)*  
*Next: [Part 3: Adding Custom Tools](part-3-custom-tools.md)*
