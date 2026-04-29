# Building AI Coding Agents with DeepAgents — Part 6: Skills System

> Load specialized capabilities on-demand without bloating your agent.

---

## The Problem: Bloated Agents

As your agent grows, you add more tools:

- Database queries
- API integrations
- Testing tools
- Deployment tools
- Documentation tools

Soon your agent has 50+ tools. The LLM struggles to choose. Latency increases. Costs rise.

## The Solution: Skills

Skills are **on-demand** capabilities. Instead of loading all tools upfront, the agent loads skills when needed.

```
User: "Run the database migrations"

Agent: "I need the database skill for this"
       [Loads database skill]
       [Executes migration]
```

## How Skills Work

A skill is a markdown file with a specific format:

```markdown
---
name: python-testing
description: Python testing with pytest, fixtures, and mocking
---

# Python Testing

## When to Use
Use this skill when:
- Writing new tests
- Debugging test failures
- Setting up test infrastructure

## Tools Available

### run_tests
```python
@tool
def run_tests(path: str = ".", verbose: bool = True) -> str:
    """Run pytest on the given path."""
    import subprocess
    cmd = ["pytest", path]
    if verbose:
        cmd.append("-v")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr
```

### create_fixture
```python
@tool
def create_fixture(name: str, scope: str = "function") -> str:
    """Generate a pytest fixture template."""
    template = f'''
@pytest.fixture(scope="{scope}")
def {name}():
    # Setup
    yield
    # Teardown
'''
    return template
```

## Best Practices
1. Use fixtures for shared setup
2. Mock external services
3. One assertion per test
```

## Creating a Skill Directory

1. Create a skills folder:

```bash
mkdir -p ~/.deepagents/skills
```

2. Add your skill files:

```
~/.deepagents/skills/
├── python-testing.md
├── docker-deployment.md
└── aws-operations.md
```

3. Configure your agent:

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["~/.deepagents/skills"]  # Skills directory
)
```

## Skill Frontmatter

The YAML frontmatter is required:

```markdown
---
name: unique-skill-name
description: Clear, specific description for the LLM
---
```

**Important**: The description helps the LLM decide when to use the skill. Make it specific:

```markdown
# GOOD
description: Docker deployment with compose, build, and push operations

# BAD  
description: Docker stuff
```

## Real-World Example: Database Skill

```markdown
---
name: database-operations
description: PostgreSQL database operations including migrations, queries, and backups
---

# Database Operations

## Overview
This skill provides tools for PostgreSQL database management.

## Tools

### run_migration
```python
@tool
def run_migration(direction: str = "upgrade") -> str:
    """Run Alembic migrations.
    
    Args:
        direction: "upgrade" or "downgrade"
    """
    import subprocess
    cmd = ["alembic", direction, "head"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout
```

### execute_query
```python
@tool  
def execute_query(query: str, params: dict = None) -> str:
    """Execute a SQL query.
    
    Use only for SELECT statements.
    For modifications, use the dedicated tools.
    
    Args:
        query: SQL SELECT query
        params: Optional query parameters
    """
    # Implementation with proper connection handling
    pass
```

### create_backup
```python
@tool
def create_backup(filename: str = None) -> str:
    """Create a database backup.
    
    Args:
        filename: Optional custom filename
    """
    import datetime
    if not filename:
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    cmd = ["pg_dump", "-Fc", "mydb", "-f", filename]
    # ... implementation
```

## When to Load

Use this skill when the user asks about:
- Database migrations
- Running queries
- Creating backups
- Schema changes
```

## Loading Skills Dynamically

The agent decides when to load skills based on the user's request and skill descriptions.

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["~/.deepagents/skills"],
    system_prompt="You have access to specialized skills. Load them when needed."
)

# User asks about testing
result = agent.invoke({
    "messages": [{"role": "user", "content": "How do I write a test for this function?"}]
}, config)
# Agent loads python-testing skill automatically
```

## Skills with Structured Output

Skills work great with structured output for complex tasks:

```python
from pydantic import BaseModel, Field
from typing import List

# Define output schema for test generation
class TestCase(BaseModel):
    """A single test case."""
    name: str = Field(description="Test function name")
    description: str = Field(description="What this test verifies")
    code: str = Field(description="The test code")

class TestSuite(BaseModel):
    """Complete test suite for a function."""
    function_name: str = Field(description="Function being tested")
    test_cases: List[TestCase] = Field(description="List of test cases")
    fixtures_needed: List[str] = Field(description="Required pytest fixtures")

# Create agent with skills and structured output
agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["~/.deepagents/skills/testing"],
    response_format=TestSuite,
    system_prompt="Generate tests using the testing skill and structured output."
)

# Generate structured tests
result = agent.invoke({
    "messages": [{"role": "user", "content": "Write tests for calculate_discount()"}]
}, config)

test_suite = result["structured_response"]
print(f"Testing function: {test_suite.function_name}")
for test in test_suite.test_cases:
    print(f"\nTest: {test.name}")
    print(f"Description: {test.description}")
    print(f"Code:\n{test.code}")
```

## Skills vs Memory

| | Skills | Memory (AGENTS.md) |
|---|--------|-------------------|
| **When loaded** | On-demand | Always |
| **Contains** | Tools + instructions | Context + conventions |
| **Size** | Can be large | Should be concise |
| **Use case** | Specialized capabilities | General context |

## Organizing Skills

Organize by domain:

```
skills/
├── testing/
│   ├── python-testing.md
│   ├── javascript-testing.md
│   └── e2e-testing.md
├── deployment/
│   ├── docker.md
│   ├── kubernetes.md
│   └── aws.md
├── databases/
│   ├── postgresql.md
│   ├── mongodb.md
│   └── redis.md
└── apis/
    ├── rest-design.md
    └── graphql.md
```

Reference subdirectories:

```python
agent = create_deep_agent(
    skills=[
        "~/.deepagents/skills/testing",
        "~/.deepagents/skills/deployment",
    ]
)
```

## Exercise

Create a skill for Git operations that includes:
1. A `commit_changes` tool
2. A `create_branch` tool
3. Best practices for commit messages

Save it as `~/.deepagents/skills/git-operations.md` and test it.

## Key Takeaway

Skills keep your agent lean and focused. Load capabilities on-demand instead of overwhelming the LLM with every possible tool.

---

*Previous: [Part 5: Memory and AGENTS.md](part-5-memory.md)*  
*Next: [Part 7: Human-in-the-Loop](part-7-hitl.md)*
