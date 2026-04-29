# Building AI Coding Agents with DeepAgents — Part 5: Memory and AGENTS.md

> Give your agent persistent memory that survives restarts.

---

## Two Types of Memory

DeepAgents provides two memory mechanisms:

1. **Conversation Memory** — What was said (checkpointer + thread_id)
2. **Knowledge Memory** — What the agent should know (AGENTS.md)

## Conversation Memory

By default, conversations are ephemeral. To persist them, add a checkpointer:

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="openai:gpt-4o",
    checkpointer=MemorySaver()  # In-memory persistence
)
```

Now conversations survive within the same process:

```python
config = {"configurable": {"thread_id": "session-1"}}

# Conversation 1
agent.invoke({
    "messages": [{"role": "user", "content": "Remember: I prefer TypeScript"}]
}, config)

# Later... (same process)
agent.invoke({
    "messages": [{"role": "user", "content": "What language do I prefer?"}]
}, config)
# Response: "You prefer TypeScript."
```

For true persistence across restarts, use SQLite:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

agent = create_deep_agent(
    model="openai:gpt-4o",
    checkpointer=SqliteSaver("./conversations.db")
)
```

## Knowledge Memory: AGENTS.md

AGENTS.md files provide **contextual knowledge** to your agent. They're perfect for:

- Project conventions and coding standards
- Architecture decisions
- API documentation
- Preferred patterns

### Creating AGENTS.md

Create a file at `~/.deepagents/AGENTS.md` (user-level) or `./.deepagents/AGENTS.md` (project-level):

```markdown
# Project Context

## Coding Standards
- Use type hints on all functions
- Follow PEP 8 for style
- Maximum line length: 100 characters

## Architecture
- Use repository pattern for data access
- Services handle business logic
- Controllers handle HTTP concerns

## Preferred Libraries
- FastAPI for web frameworks
- Pydantic for validation
- pytest for testing
```

### Loading AGENTS.md

```python
from deepagents import create_deep_agent

def get_memory_sources():
    """Find AGENTS.md files."""
    from pathlib import Path
    
    sources = []
    candidates = [
        "~/.deepagents/AGENTS.md",      # User-level
        "./.deepagents/AGENTS.md",      # Project-level
    ]
    
    for candidate in candidates:
        path = Path(candidate).expanduser().resolve()
        if path.is_file():
            sources.append(str(path))
    
    return sources

agent = create_deep_agent(
    model="openai:gpt-4o",
    memory=get_memory_sources()  # Loads AGENTS.md content
)
```

The agent now knows your conventions without you repeating them.

## How Memory Works

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              DeepAgents Agent                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │  System Prompt                                  │   │
│  │  + AGENTS.md content (memory)                   │   │
│  │  + Conversation history (checkpointer)          │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LLM generates response using all context       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Practical Example

Let's say you're working on a FastAPI project. Your `./.deepagents/AGENTS.md`:

```markdown
# FastAPI Project Context

## Patterns
- Use dependency injection for database sessions
- All routes return Pydantic models
- Use async/await for I/O operations

## Testing
- Test files in `tests/` mirror `src/` structure
- Use pytest-asyncio for async tests
- Mock external services with pytest-mock

## Database
- Use SQLAlchemy 2.0 with async support
- Migrations with Alembic
- Never commit .env files
```

Now when you ask:

```
User: "Create a new endpoint for user registration"

Agent: (knows to use FastAPI patterns, dependency injection, 
        Pydantic models, and async/await)
```

## Memory Best Practices

### 1. Keep It Concise

```markdown
# GOOD: Specific and actionable
- Use snake_case for functions
- All public functions need docstrings
- Prefer list comprehensions over map()

# BAD: Too vague
- Write good code
- Follow best practices
```

### 2. Organize by Topic

```markdown
## Style Guide
- Line length: 88 characters (Black default)
- Use trailing commas in multi-line collections

## Testing
- Minimum 80% coverage
- Unit tests in tests/unit/
- Integration tests in tests/integration/

## Dependencies
- Pin major versions in requirements.txt
- Use `>=` only for internal packages
```

### 3. Update Regularly

AGENTS.md should evolve with your project. Outdated memory is worse than no memory.

### 4. Use Both Levels

```
~/.deepagents/AGENTS.md      (your personal preferences)
./.deepagents/AGENTS.md      (project-specific rules)
```

User-level for your habits, project-level for team conventions.

## Cross-Thread Memory with Store

For memory that persists across different conversation threads, use the Store:

```python
from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_deep_agent(
    model="openai:gpt-4o",
    store=store,  # Cross-thread persistence
    checkpointer=MemorySaver()  # Per-thread persistence
)
```

The Store is especially useful for:
- User preferences across all their conversations
- Learned patterns and improvements
- Long-term knowledge accumulation

## Structured Output with Memory

Structured output works seamlessly with memory. The agent remembers your schema preferences:

```python
from pydantic import BaseModel, Field
from typing import List

class UserPreference(BaseModel):
    """User preferences for code style."""
    preferred_language: str
    style_rules: List[str]
    indentation: str

# First interaction - agent learns preferences
result = agent.invoke({
    "messages": [{"role": "user", "content": "I prefer Python with 4-space indentation"}]
}, config)

# Later - agent remembers and uses structured output
result = agent.invoke({
    "messages": [{"role": "user", "content": "What are my coding preferences?"}]
}, config)

preferences = result["structured_response"]
print(f"Language: {preferences.preferred_language}")  # "Python"
print(f"Indentation: {preferences.indentation}")  # "4-space"
```

## Exercise

Create an AGENTS.md for a Python project that includes:
1. Coding style preferences
2. Testing requirements
3. Two custom rules specific to your workflow

Then test it:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-4o",
    memory=["./.deepagents/AGENTS.md"]
)

# Ask: "What's our coding style for function names?"
```

## Key Takeaway

Memory separates configuration from conversation. AGENTS.md provides persistent context; checkpointers provide conversation history. Together, they make your agent feel truly knowledgeable.

---

*Previous: [Part 4: Filesystem and Shell Backends](part-4-backends.md)*  
*Next: [Part 6: Skills System](part-6-skills.md)*
