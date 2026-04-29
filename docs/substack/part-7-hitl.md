# Building AI Coding Agents with DeepAgents — Part 7: Human-in-the-Loop

> Add safety and control with approval workflows for sensitive operations.

---

## Why Human-in-the-Loop?

Your agent can:
- Read any file
- Write to files
- Execute shell commands
- Search the web

That's powerful. And potentially dangerous.

Human-in-the-loop (HITL) lets you review sensitive operations before they execute.

## How It Works

```
1. Agent decides to use a sensitive tool
2. Execution pauses (interrupts)
3. Human reviews and approves/denies
4. Execution resumes with decision
```

## Configuring Interrupts

Use `interrupt_on` to specify which tools need approval:

```python
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import InterruptOnConfig

backend = LocalShellBackend(root_dir=".", virtual_mode=True)

# Configure which tools trigger interrupts
interrupt_on = InterruptOnConfig(
    tools={
        "execute": True,        # Always ask for shell commands
        "write_file": True,     # Ask for file writes
        "edit_file": True,      # Ask for file edits
        "read_file": False,     # Auto-approve reads (safe)
        "ls": False,            # Auto-approve directory listing
        "web_search": True,     # Ask for external calls
    }
)

agent = create_deep_agent(
    model="openai:gpt-4o",
    backend=backend,
    checkpointer=MemorySaver(),  # Required for interrupts!
    interrupt_on=interrupt_on,
)
```

**Critical**: Interrupts require a checkpointer. Without it, interrupts won't work.

## Handling Interrupts in Code

When an interrupt occurs, the agent stops and waits for a `Command`:

```python
from langgraph.types import Command

# Start a conversation
thread_id = "session-1"
config = {"configurable": {"thread_id": thread_id}}

# Stream the agent
for event in agent.stream({
    "messages": [{"role": "user", "content": "Delete all files in temp/"}]
}, config):
    
    # Check for interrupts
    if event.get("__interrupt__"):
        interrupt_info = event["__interrupt__"]
        tool_name = interrupt_info.get("tool_name")
        tool_args = interrupt_info.get("tool_args")
        
        print(f"Tool '{tool_name}' wants to execute:")
        print(f"  Args: {tool_args}")
        
        # Get user decision
        decision = input("Approve? (y/n): ").lower() == "y"
        
        # Resume with Command
        if decision:
            result = agent.invoke(
                Command(resume=True),
                config
            )
        else:
            result = agent.invoke(
                Command(resume=False),
                config
            )
```

## Complete HITL Example

Here's a full CLI with approval workflow:

```python
import asyncio
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import InterruptOnConfig
from langgraph.types import Command

class HITLAgent:
    def __init__(self):
        backend = LocalShellBackend(root_dir=".", virtual_mode=True)
        
        self.agent = create_deep_agent(
            model="openai:gpt-4o",
            backend=backend,
            checkpointer=MemorySaver(),
            interrupt_on=InterruptOnConfig(
                tools={
                    "execute": True,
                    "write_file": True,
                    "edit_file": True,
                }
            ),
        )
        self.config = {"configurable": {"thread_id": "cli-session"}}
    
    async def run(self, message: str):
        async for event in self.agent.astream_events({
            "messages": [{"role": "user", "content": message}]
        }, self.config):
            
            event_type = event.get("event")
            
            # Handle regular events
            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content"):
                    print(chunk.content, end="", flush=True)
            
            # Handle interrupts
            elif event_type == "on_interrupt":
                tool_name = event["data"].get("tool_name")
                tool_args = event["data"].get("tool_args")
                
                print(f"\n\n[APPROVAL REQUIRED]")
                print(f"Tool: {tool_name}")
                print(f"Arguments: {tool_args}")
                
                decision = input("\nApprove? (y/n): ").lower().strip()
                
                # Resume agent
                await self.agent.ainvoke(
                    Command(resume=decision == "y"),
                    self.config
                )

# Usage
async def main():
    hitl = HITLAgent()
    await hitl.run("Create a new file called hello.txt with 'Hello World'")

asyncio.run(main())
```

## Approval UI Patterns

For a better user experience, show context:

```python
def format_approval_prompt(tool_name: str, tool_args: dict) -> str:
    """Format a user-friendly approval prompt."""
    
    if tool_name == "write_file":
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 APPROVAL REQUIRED: File Write
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: {tool_args.get('file_path', 'unknown')}
Content preview:
{tool_args.get('content', '')[:500]}...

Allow this operation? (y/n): """
    
    elif tool_name == "execute":
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 APPROVAL REQUIRED: Shell Command
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Command: {tool_args.get('command', 'unknown')}

⚠️  This will execute in your shell!

Allow this operation? (y/n): """
    
    else:
        return f"""
🔒 Approve {tool_name}?
Args: {tool_args}

(y/n): """
```

## Selective Approvals

You can make approval smarter:

```python
from langchain.agents.middleware import InterruptOnConfig

def should_approve_write(file_path: str) -> bool:
    """Auto-approve safe paths, ask for sensitive ones."""
    safe_patterns = [".txt", ".md", ".json", ".yaml"]
    sensitive_patterns = [".env", "config", "secret"]
    
    if any(p in file_path for p in sensitive_patterns):
        return True  # Require approval
    if any(file_path.endswith(p) for p in safe_patterns):
        return False  # Auto-approve
    return True  # Default to approval

# Note: DeepAgents doesn't support dynamic approval yet,
# but you can implement this logic in your interrupt handler
```

## Security Best Practices

### 1. Default to Approval

```python
interrupt_on = InterruptOnConfig(
    tools={
        "execute": True,      # Always ask
        "write_file": True,   # Always ask
        "edit_file": True,    # Always ask
        # Everything else is safe
    }
)
```

### 2. Review Commands Carefully

```
🔒 APPROVAL REQUIRED: Shell Command
Command: rm -rf /

❌ DENY (obviously!)
```

### 3. Log All Approvals

```python
import logging

logger = logging.getLogger("approvals")

async def handle_approval(tool_name: str, tool_args: dict, approved: bool):
    logger.info(f"Tool: {tool_name}, Approved: {approved}, Args: {tool_args}")
    # ... proceed with Command(resume=approved)
```

### 4. Timeouts

Add timeouts to prevent indefinite waiting:

```python
import asyncio

async def get_approval_with_timeout(tool_name: str, timeout: int = 60) -> bool:
    try:
        decision = await asyncio.wait_for(
            get_user_input(f"Approve {tool_name}? (y/n): "),
            timeout=timeout
        )
        return decision.lower() == "y"
    except asyncio.TimeoutError:
        print("Approval timeout - denying operation")
        return False
```

## Structured Output for Approval Decisions

Use structured output to track and analyze approval patterns:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ApprovalDecision(BaseModel):
    """Record of a single approval decision."""
    tool_name: str = Field(description="Tool that was approved/denied")
    tool_args: dict = Field(description="Arguments passed to the tool")
    approved: bool = Field(description="Whether operation was approved")
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: Optional[str] = Field(description="Why decision was made")

class ApprovalSummary(BaseModel):
    """Summary of approval activity."""
    total_requests: int
    approved_count: int
    denied_count: int
    approval_rate: float
    most_common_tools: List[str]

# Track approvals with structured output
approval_history: List[ApprovalDecision] = []

async def handle_approval(tool_name: str, tool_args: dict) -> bool:
    """Handle approval with structured logging."""
    # Get user decision
    decision = input(f"Approve {tool_name}? (y/n): ").lower() == "y"
    reason = input("Reason (optional): ") if not decision else None
    
    # Record structured decision
    approval_history.append(ApprovalDecision(
        tool_name=tool_name,
        tool_args=tool_args,
        approved=decision,
        reason=reason
    ))
    
    return decision

# Later: analyze approval patterns
agent = create_deep_agent(
    model="openai:gpt-4o",
    response_format=ApprovalSummary,
    system_prompt="Analyze approval history and provide summary"
)

result = agent.invoke({
    "messages": [{
        "role": "user", 
        "content": f"Analyze: {[a.model_dump() for a in approval_history]}"
    }]
})

summary = result["structured_response"]
print(f"Approval rate: {summary.approval_rate:.1%}")
print(f"Most common tools: {summary.most_common_tools}")
```

## Exercise

Implement an approval system that:
1. Shows a formatted prompt for each tool type
2. Logs all approvals to a file using structured output
3. Has a 30-second timeout
4. Remembers the user's last decision for similar operations

## Key Takeaway

Human-in-the-loop adds a critical safety layer. Configure it once, and your agent becomes both powerful and safe.

---

*Previous: [Part 6: Skills System](part-6-skills.md)*  
*Next: [Part 8: Building a CLI](part-8-cli.md)*
