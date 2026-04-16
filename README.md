# agent-tui

Standalone TUI scaffold for building AI coding agent CLIs.

Extracted from the deepagents CLI — full UI with all agent interactions stubbed behind an `AgentProtocol`.

## Quick Start

```bash
uv run agent-tui
```

## Architecture

The TUI communicates with any agent backend through `AgentProtocol` — a Python protocol class that emits typed `AgentEvent` objects. A `StubAgent` is included for development and testing.

See `agent_tui/protocol.py` for the contract.


## Implementation Phases

Phase 1 Summary
Completed
Branch: phase/1-foundation (commits b045582 → 7e3e127)

Files Created

services/deep_agents/__init__.py
services/deep_agents/adapter.py
services/deep_agents/event_translator.py
tests/test_deep_agents_adapter.py
tests/test_event_translator.py
docs/superpowers/specs/2026-04-14-deepagents-integration-architecture.md
docs/superpowers/plans/2026-04-14-deepagents-integration.md

Files Modified

domain/protocol.py	+5 EventType values, +4 AgentEvent fields
services/adapter.py	+5 new event handlers
entrypoints/main.py	--agent flag (stub/deepagents)
entrypoints/app.py	+5 stub methods for new events
configurator/settings.py	+deepagents_model property
pyproject.toml	+deepagents>=0.5.2, langchain-openai>=0.3.0

Verification
- uv run agent-tui --agent=stub ✓
- uv run agent-tui --agent=deepagents ✓ (TUI launches)
- 44 tests pass

Key Fixes Applied
1. __init__.py lazy loading — was blocking runtime imports
2. DeepAgentsAdapter.from_settings() — was missing class method
3. create_deep_agent() — was incorrectly using deepagents.Agent

Phase 2 Summary
Completed
Branch: phase/2-file-operations (merges into phase/1-foundation)
Goal: File tools (read, write, edit) flow through TUI approval system

Files Modified

services/deep_agents/event_translator.py	+on_chat_model_stream handler, +path normalization
docs/superpowers/specs/2026-04-14-deepagents-integration-architecture.md	+filesystem backend spec

Key Technical Fixes

1. Event Key Mismatch (event_translator.py)
   LangGraph uses "event" key, not "event_type"
   
2. Tool Name Location (event_translator.py)
   Tool name is at top level in LangGraph events, not in data dict
   
3. Message Chunk Handler (event_translator.py)
   Added _handle_chat_model_stream for DeepAgents message streaming
   
4. Approval Flow Fix (adapter.py)
   Yield TOOL_CALL event FIRST, then wait for approval (prevents deadlock)
   
5. Comparison Fix (adapter.py)
   Fixed: agent_event.type == EventType.TOOL_CALL
   Was: agent_event.type == AgentEvent.type (always False)
   
6. TOOL_RESULT Metadata (event_translator.py)
   Added tool_name and tool_id to tool result events for widget display
   
7. Filesystem Backend (adapter.py)
   Added FilesystemBackend with virtual_mode=True
   /test.txt resolves to <cwd>/test.txt instead of system root
   
8. Path Normalization (event_translator.py)
   Converts /test.txt to test.txt for UI display (user-friendly paths)

Verification
- "Read README.md" → approval widget appears ✓
- Approve → file content displays ✓
- "Create test.txt" → writes to current directory ✓
- All file operations resolve against cwd, not system root ✓
- 44 tests pass

Event Flow
User message → on_chat_model_stream → MESSAGE_CHUNK (thinking)
  → on_tool_start → TOOL_CALL event → Yield event
  → TUI shows ApprovalMenu → User approves → approval_event.set()
  → Stream resumes → Tool executes → on_tool_end
  → TOOL_RESULT event → TUI shows ToolCallMessage with output

Architecture Notes
- Path normalization in translator affects UI display only
- virtual_mode=True in backend affects actual file operations
- Both work together: UI shows relative paths, backend resolves them correctly

Phase 3 Summary
Completed
Branch: phase/3-shell-execution (merges into phase/2-file-operations)
Goal: execute tool works with TUI safety controls

Files Created

services/deep_agents/backend.py	LocalShellBackend (extends FilesystemBackend)

Files Modified

services/deep_agents/adapter.py	Use LocalShellBackend with shell support
services/adapter.py	+DANGEROUS_SHELL_PATTERNS check for execute tool

Key Implementation

1. LocalShellBackend (backend.py)
   Extends FilesystemBackend: file operations (read, write, edit, glob, grep, ls)
   Adds shell execution: execute tool (shell commands)
   virtual_mode=True: /file.txt maps to <cwd>/file.txt
   Both rooted at current working directory
   inherit_env=True passes current environment to shell commands

2. Shell Safety (adapter.py)
   Dangerous pattern detection for execute tool
   Blocks: command substitution $(...), backticks `...`, redirects >>
   Blocks: variable expansion $VAR, process substitution <(...)

3. Approval Integration
   execute tool appears in approval widget like file tools
   User must approve before shell command runs
   TUI shows command preview in styled format

Verification
- "execute echo hello" → approval widget → command runs ✓
- "execute $(rm -rf /)" → blocked by dangerous pattern check ✓
- "execute cat file.txt" → approved → outputs to TUI ✓
- Shell commands execute in current working directory ✓
- 64 tests pass (7 pre-existing test issues unrelated to Phase 3)

Shell Safety Patterns Blocked
$(  `  $'  \n  \r  \t  <(  >(  <<<  <<  >>  >  <  ${  $VAR  &

Event Flow (Shell)
User: "Run ls -la"
  → on_chat_model_stream → thinking
  → on_tool_start → TOOL_CALL (execute)
  → adapter checks contains_dangerous_patterns()
  → Blocked? → show_error() + reject
  → Safe? → yield TOOL_CALL → TUI approval widget
  → User approves → approval_event.set()
  → LocalShellBackend.execute() runs command
  → on_tool_end → TOOL_RESULT with output
  → TUI displays command output