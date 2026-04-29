# Building AI Coding Agents with DeepAgents — Part 8: Building a CLI

> Tie it all together into a command-line interface.

---

## Architecture Overview

A production CLI has three layers:

```
┌─────────────────────────────────────────┐
│           CLI Layer                     │
│  - Argument parsing                     │
│  - Environment setup                    │
│  - Entry point                          │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Adapter Layer                   │
│  - Protocol translation                 │
│  - Event streaming                      │
│  - Approval handling                    │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         DeepAgents Layer                │
│  - Agent configuration                  │
│  - Tool execution                       │
│  - Memory management                    │
└─────────────────────────────────────────┘
```

## The Protocol Pattern

Define a protocol that your CLI expects:

```python
from typing import Protocol, AsyncIterator, Any
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_END = "message_end"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"

@dataclass
class AgentEvent:
    type: EventType
    text: str = ""
    tool_name: str = None
    tool_args: dict = None
    tool_output: str = None

class AgentProtocol(Protocol):
    """Protocol that all agent backends must implement."""
    
    async def stream(self, message: str, thread_id: str = None) -> AsyncIterator[AgentEvent]:
        """Stream events for a user message."""
        ...
    
    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        """Respond to a tool approval request."""
        ...
    
    async def cancel(self) -> None:
        """Cancel current execution."""
        ...
```

## The DeepAgents Adapter

Implement the protocol for DeepAgents:

```python
import asyncio
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents.middleware import InterruptOnConfig

class DeepAgentsAdapter:
    """Implements AgentProtocol using DeepAgents."""
    
    def __init__(self, model: str = "openai:gpt-4o"):
        self.model = model
        self.agent = None
        self.approval_event = asyncio.Event()
        self.approval_result = False
        self._translator = EventTranslator()
        
    def _ensure_agent(self):
        if self.agent is None:
            backend = LocalShellBackend(
                root_dir=Path.cwd(),
                virtual_mode=True
            )
            
            self.agent = create_deep_agent(
                model=self.model,
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
        return self.agent
    
    async def stream(self, message: str, thread_id: str = None) -> AsyncIterator[AgentEvent]:
        agent = self._ensure_agent()
        config = {"configurable": {"thread_id": thread_id or "default"}}
        
        async for event in agent.astream_events({
            "messages": [{"role": "user", "content": message}]
        }, config):
            # Translate DeepAgents events to AgentEvent
            for agent_event in self._translator.translate(event):
                
                # Handle approval for tool calls
                if agent_event.type == EventType.TOOL_CALL:
                    self.approval_event.clear()
                    yield agent_event
                    
                    # Wait for approval
                    await self.approval_event.wait()
                    if not self.approval_result:
                        continue  # Skip results if denied
                else:
                    yield agent_event
    
    async def approve_tool(self, tool_id: str, approved: bool) -> None:
        self.approval_result = approved
        self.approval_event.set()
    
    async def cancel(self) -> None:
        # Implementation depends on your cancellation strategy
        pass
```

## The Event Translator

Convert DeepAgents events to your protocol:

```python
class EventTranslator:
    """Translates DeepAgents/LangGraph events to AgentEvent."""
    
    def translate(self, event: dict) -> Iterator[AgentEvent]:
        event_type = event.get("event") or event.get("event_type", "")
        data = event.get("data", {})
        
        if event_type == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content"):
                yield AgentEvent(
                    type=EventType.MESSAGE_CHUNK,
                    text=chunk.content
                )
        
        elif event_type == "on_tool_start":
            tool_name = event.get("name") or data.get("name")
            tool_input = data.get("input", {})
            
            yield AgentEvent(
                type=EventType.TOOL_CALL,
                tool_name=tool_name,
                tool_args=tool_input,
                tool_id=event.get("run_id")
            )
        
        elif event_type == "on_tool_end":
            tool_output = data.get("output", "")
            
            yield AgentEvent(
                type=EventType.TOOL_RESULT,
                tool_name=event.get("name"),
                tool_output=str(tool_output)
            )
        
        elif event_type == "on_chain_end":
            yield AgentEvent(type=EventType.MESSAGE_END)
        
        elif event_type == "on_tool_error":
            yield AgentEvent(
                type=EventType.ERROR,
                text=str(data.get("error", "Unknown error"))
            )
```

## The CLI Interface

Build the user-facing CLI:

```python
import argparse
import asyncio
from pathlib import Path

class AgentCLI:
    """Command-line interface for the coding agent."""
    
    def __init__(self, adapter: AgentProtocol):
        self.adapter = adapter
        self.current_thread = "default"
    
    async def run_interactive(self):
        """Run in interactive mode."""
        print("🤖 AI Coding Agent")
        print("Type 'exit' to quit, 'cancel' to stop current operation\n")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() == "exit":
                    break
                
                if user_input.lower() == "cancel":
                    await self.adapter.cancel()
                    continue
                
                if not user_input:
                    continue
                
                await self._process_message(user_input)
                
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
                continue
            except EOFError:
                break
    
    async def _process_message(self, message: str):
        """Process a single message."""
        async for event in self.adapter.stream(message, self.current_thread):
            if event.type == EventType.MESSAGE_CHUNK:
                print(event.text, end="", flush=True)
            
            elif event.type == EventType.TOOL_CALL:
                print(f"\n[Tool: {event.tool_name}]")
                approval = input(f"Approve {event.tool_name}? (y/n): ").lower() == "y"
                await self.adapter.approve_tool(event.tool_id, approval)
            
            elif event.type == EventType.TOOL_RESULT:
                print(f"\n[Result]: {event.tool_output[:200]}...")
            
            elif event.type == EventType.ERROR:
                print(f"\n[Error]: {event.text}")
            
            elif event.type == EventType.MESSAGE_END:
                print()  # New line after complete message

async def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent CLI")
    parser.add_argument(
        "--model", 
        default="openai:gpt-4o",
        help="Model to use (default: openai:gpt-4o)"
    )
    parser.add_argument(
        "--thread",
        default="default",
        help="Conversation thread ID"
    )
    
    args = parser.parse_args()
    
    # Create adapter
    adapter = DeepAgentsAdapter(model=args.model)
    
    # Create and run CLI
    cli = AgentCLI(adapter)
    cli.current_thread = args.thread
    
    await cli.run_interactive()

if __name__ == "__main__":
    asyncio.run(main())
```

## Environment Configuration

Use environment variables for configuration:

```python
import os
from dataclasses import dataclass

@dataclass
class Settings:
    openai_api_key: str
    deepagents_model: str
    tavily_api_key: str | None
    allowed_dirs: list[str]
    
    @classmethod
    def from_env(cls):
        return cls(
            openai_api_key=os.getenv(
                "AGENT_TUI_OPENAI_API_KEY"
            ) or os.getenv("OPENAI_API_KEY"),
            deepagents_model=os.getenv("DEEPAGENTS_MODEL", "openai:gpt-4o"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            allowed_dirs=os.getenv(
                "DEEPAGENTS_ALLOWED_DIRS", "."
            ).split(":")
        )
```

## CLI Commands with Structured Output

Add commands that output structured data for scripting:

```python
from pydantic import BaseModel, Field
from typing import List
import json

class FileAnalysis(BaseModel):
    """Structured file analysis result."""
    file_path: str = Field(description="Path to analyzed file")
    language: str = Field(description="Detected programming language")
    line_count: int = Field(description="Total lines of code")
    complexity_score: int = Field(description="Complexity score 1-10")
    suggestions: List[str] = Field(description="Improvement suggestions")

class AgentCLI:
    """CLI with structured output support."""
    
    def __init__(self, adapter: AgentProtocol):
        self.adapter = adapter
        self.current_thread = "default"
    
    async def analyze_file(self, file_path: str, output_format: str = "text"):
        """Analyze a file with optional structured output."""
        # Create agent with structured output for analysis
        agent = create_deep_agent(
            model="openai:gpt-4o",
            backend=LocalShellBackend(root_dir=Path.cwd()),
            response_format=FileAnalysis,
            system_prompt="Analyze code files and return structured analysis."
        )
        
        result = agent.invoke({
            "messages": [{"role": "user", "content": f"Analyze {file_path}"}]
        }, {"configurable": {"thread_id": self.current_thread}})
        
        analysis = result["structured_response"]
        
        if output_format == "json":
            # Output raw JSON for scripting
            print(json.dumps(analysis.model_dump(), indent=2))
        else:
            # Pretty print for humans
            print(f"📄 {analysis.file_path}")
            print(f"   Language: {analysis.language}")
            print(f"   Lines: {analysis.line_count}")
            print(f"   Complexity: {analysis.complexity_score}/10")
            print("   Suggestions:")
            for suggestion in analysis.suggestions:
                print(f"     • {suggestion}")

# Usage in CLI
# my-agent analyze src/main.py --format json
# my-agent analyze src/main.py --format text (default)
```

## Batch Processing with Structured Output

Process multiple files with consistent structured results:

```python
from typing import List
import asyncio

class BatchAnalysis(BaseModel):
    """Results from analyzing multiple files."""
    files_analyzed: int
    total_lines: int
    average_complexity: float
    issues_found: List[dict]
    recommendations: List[str]

async def analyze_project(files: List[str]) -> BatchAnalysis:
    """Analyze multiple files and return aggregated results."""
    agent = create_deep_agent(
        model="openai:gpt-4o",
        backend=LocalShellBackend(root_dir=Path.cwd()),
        response_format=BatchAnalysis
    )
    
    file_list = "\n".join(files)
    result = agent.invoke({
        "messages": [{
            "role": "user", 
            "content": f"Analyze these files:\n{file_list}"
        }]
    })
    
    return result["structured_response"]

# Use in CLI for batch operations
# my-agent analyze-batch "src/*.py" --output report.json
```

## Putting It Together

File structure:

```
my_agent_cli/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── cli.py               # CLI interface
│   ├── adapter.py           # DeepAgents adapter
│   ├── protocol.py          # AgentProtocol
│   └── translator.py        # Event translation
├── .deepagents/
│   └── AGENTS.md            # Project memory
├── pyproject.toml
└── README.md
```

Running the CLI:

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Run interactive mode
python -m my_agent_cli

# With specific model
python -m my_agent_cli --model anthropic:claude-sonnet-4-6

# With specific thread
python -m my_agent_cli --thread feature-branch-work
```

## Key Takeaway

The CLI is the integration layer. It translates between DeepAgents events and user interactions, handles configuration, and provides the interface your users actually see.

---

*Previous: [Part 7: Human-in-the-Loop](part-7-hitl.md)*  
*Next: [Part 9: Testing and Debugging](part-9-testing.md)*
