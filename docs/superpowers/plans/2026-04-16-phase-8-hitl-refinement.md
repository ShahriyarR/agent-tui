# Phase 8: Human-in-the-Loop Refinement - Implementation Plan

**Date:** 2026-04-16
**Status:** Ready for Implementation
**Branch:** phase/8-hitl-refinement
**Merge Into:** phase/7-memory-skills
**Goal:** Full interrupt/resume flow with proper LangGraph integration

---

## Overview

Phase 8 completes the Human-in-the-Loop (HITL) implementation by integrating LangGraph's interrupt/resume mechanism with the TUI approval system. This enables the agent to pause on sensitive operations, wait for user approval, and correctly resume execution after a decision.

---

## Current State

**Already Implemented:**
- ✅ `AgentProtocol` with `approve_tool()` method
- ✅ Basic `TOOL_CALL` event emission and approval widget display
- ✅ `INTERRUPT` event type in protocol
- ✅ `MemorySaver` checkpointer in adapter
- ✅ Shell safety patterns (Phase 3)
- ✅ File operation approval (Phase 2)

**Missing for Full HITL:**
- ❌ `interrupt_on` configuration for `create_deep_agent()`
- ❌ LangGraph interrupt → resume flow integration
- ❌ Proper `INTERRUPT` event handling in services adapter
- ❌ Interrupt overlay UI with edit/reject options
- ❌ Complete `request_tool_approval()` implementation

---

## Architecture

### Interrupt Flow

```
User sends message
  ↓
Agent processes → Hits sensitive tool (execute, write_file, etc.)
  ↓
LangGraph INTERRUPT (with interrupt_on config)
  ↓
EventTranslator → INTERRUPT event
  ↓
Adapter._dispatch() → TUI pause + show approval state
  ↓
TUI shows InterruptOverlay with options:
    - Approve (run tool)
    - Edit (modify args)
    - Reject (skip tool)
  ↓
User makes decision
  ↓
Command(resume=...) → LangGraph resumes
  ↓
Agent continues execution
```

---

## Implementation Tasks

### Task 8.1: Configure interrupt_on per-tool in adapter.py

**File:** `src/agent_tui/services/deep_agents/adapter.py`

**Changes:**
1. Add `interrupt_on` parameter to `create_deep_agent()` call
2. Configure which tools should trigger interrupts
3. Import `InterruptOnConfig` from langchain.agents.middleware

**Code Pattern:**
```python
from langchain.agents.middleware import InterruptOnConfig

interrupt_on = InterruptOnConfig(
    tools={
        "execute": True,        # Always interrupt on shell commands
        "write_file": True,     # Interrupt on file writes
        "edit_file": True,      # Interrupt on file edits
        "read_file": False,     # Auto-approve reads (safe)
        "glob": False,          # Auto-approve searches (safe)
        "grep": False,          # Auto-approve searches (safe)
        "web_search": True,     # Interrupt on external calls
        "fetch_url": True,      # Interrupt on external calls
    }
)

self._agent = create_deep_agent(
    ...
    interrupt_on=interrupt_on,
)
```

**Verification:**
- [ ] `execute` tool triggers interrupt
- [ ] `write_file` tool triggers interrupt
- [ ] `read_file` does NOT trigger interrupt
- [ ] Config is passed to `create_deep_agent()`

---

### Task 8.2: Implement INTERRUPT event handling in services/adapter.py

**File:** `src/agent_tui/services/adapter.py`

**Changes:**
1. Replace placeholder INTERRUPT handler with full implementation
2. Call TUI method to show interrupt overlay
3. Handle user response (approve/edit/reject)
4. Call `answer_question()` or appropriate method to resume

**Current Code:**
```python
case EventType.INTERRUPT:
    logger.debug("Agent interrupted")
```

**New Implementation:**
```python
case EventType.INTERRUPT:
    logger.info("Agent interrupted, showing HITL overlay")
    # Extract interrupt details from event
    tool_name = event.tool_name
    tool_args = event.tool_args
    tool_id = event.tool_id
    
    # Show interrupt overlay with approve/edit/reject options
    result = await self.app.show_interrupt_overlay(
        tool_name=tool_name,
        tool_args=tool_args,
        tool_id=tool_id,
    )
    
    # Handle result
    match result["action"]:
        case "approve":
            # Resume with original args
            await self.agent.approve_tool(tool_id, True)
        case "edit":
            # Resume with edited args
            edited_args = result["edited_args"]
            # TODO: How to pass edited args back to LangGraph?
            await self.agent.approve_tool(tool_id, True)
        case "reject":
            # Skip this tool
            await self.agent.approve_tool(tool_id, False)
```

**Questions to Resolve:**
- How does LangGraph handle edited tool arguments on resume?
- Does `approve_tool()` accept modified arguments or just boolean?

**Verification:**
- [ ] INTERRUPT event pauses the agent
- [ ] TUI shows interrupt overlay
- [ ] Agent resumes after user decision

---

### Task 8.3: Add checkpointer configuration for resume support

**File:** `src/agent_tui/services/deep_agents/adapter.py`

**Changes:**
1. Verify `MemorySaver` is properly configured for interrupt/resume
2. Ensure thread_id is properly passed through to checkpointer
3. May need to configure checkpointer with persistence path

**Current Code:**
```python
checkpointer = MemorySaver()
```

**Potential Enhancement:**
```python
# MemorySaver with optional persistence
checkpointer = MemorySaver(
    # If we want persistence across restarts:
    # saver=FileSystemSaver(path=settings.checkpoint_dir)
)
```

**Note:** `MemorySaver` should work for in-memory interrupts. Persistence across TUI restarts is Phase 8+ enhancement.

**Verification:**
- [ ] Interrupt state is preserved in checkpointer
- [ ] Resume works within same TUI session

---

### Task 8.4: Implement interrupt overlay UI in app.py

**File:** `src/agent_tui/entrypoints/app.py`

**Changes:**
1. Create new `show_interrupt_overlay()` method
2. Display tool name, args, and action buttons
3. Support approve/edit/reject actions
4. Return user decision to adapter

**UI Design:**
```
┌─────────────────────────────────────────────┐
│ ⚠️  Tool Execution Requested                │
├─────────────────────────────────────────────┤
│ Tool: execute                               │
│ Command: ls -la                             │
├─────────────────────────────────────────────┤
│ [1] Approve (y)                             │
│ [2] Edit Args (e)                           │
│ [3] Reject (n)                              │
├─────────────────────────────────────────────┤
│ Edit mode: [Text area for arg editing]      │
├─────────────────────────────────────────────┤
│ ↑/↓ navigate • Enter select • y/e/n keys   │
└─────────────────────────────────────────────┘
```

**Method Signature:**
```python
async def show_interrupt_overlay(
    self,
    tool_name: str,
    tool_args: dict[str, Any],
    tool_id: str,
) -> dict[str, Any]:
    """Show interrupt overlay and return user decision.
    
    Returns:
        dict with keys:
        - action: "approve" | "edit" | "reject"
        - edited_args: dict (only if action="edit")
    """
```

**Implementation Notes:**
- Can reuse existing `_request_approval()` infrastructure
- Add edit mode toggle
- Return structured result for adapter to process

**Verification:**
- [ ] Overlay displays tool info
- [ ] All three actions work
- [ ] Edit mode allows arg modification
- [ ] Returns correct result structure

---

### Task 8.5: Complete request_tool_approval() implementation

**File:** `src/agent_tui/entrypoints/app.py`

**Current State:** `request_tool_approval()` exists but may not fully support HITL

**Changes:**
1. Ensure it integrates with interrupt overlay
2. Support auto-approval for allow-listed commands
3. Handle both file tools and shell commands
4. Return proper boolean or structured result

**Integration with INTERRUPT:**
- Option A: `request_tool_approval()` is called by INTERRUPT handler
- Option B: Separate `show_interrupt_overlay()` method

**Recommendation:** Enhance `request_tool_approval()` to support all HITL features:
- Approve/Reject (existing)
- Edit args (new)
- Auto-approval based on allow-list (existing from shell safety)

**Verification:**
- [ ] Works for file tools
- [ ] Works for shell commands
- [ ] Works for web tools
- [ ] Edit mode functional
- [ ] Auto-approval for safe commands

---

## Testing Strategy

### Unit Tests
1. Test `interrupt_on` configuration is created correctly
2. Test INTERRUPT event is emitted on configured tools
3. Test adapter handles INTERRUPT event
4. Test UI overlay renders correctly

### Integration Tests
1. Test full flow: message → interrupt → approval → resume → result
2. Test edit mode: modify args → resume with new args
3. Test reject: skip tool → continue execution
4. Test auto-approval: safe commands bypass interrupt

### Manual Tests
1. `execute ls -la` → should interrupt → approve → see output
2. `write_file dangerous.txt` → should interrupt → edit filename → approve → file created
3. `read_file README.md` → should NOT interrupt → immediate read
4. Reject shell command → should skip and continue

---

## Files to Modify

| File | Task | Lines |
|------|------|-------|
| `services/deep_agents/adapter.py` | 8.1, 8.3 | +15 |
| `services/adapter.py` | 8.2 | +30 |
| `entrypoints/app.py` | 8.4, 8.5 | +50 |

---

## Dependencies

- `langchain.agents.middleware.InterruptOnConfig`
- `langgraph.checkpoint.memory.MemorySaver` (already in use)
- Existing `AgentProtocol` methods: `approve_tool()`, `answer_question()`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LangGraph API changed | Check latest docs before implementing |
| Edit args on resume unclear | Research LangGraph resume patterns |
| UI complexity | Start with approve/reject, add edit later |
| Test flakiness | Use deterministic thread_ids in tests |

---

## Definition of Done

- [ ] `interrupt_on` configured for all sensitive tools
- [ ] INTERRUPT events properly handled in services adapter
- [ ] TUI shows interrupt overlay with approve/edit/reject
- [ ] Agent resumes correctly after approval
- [ ] Agent skips tool after rejection
- [ ] Edit mode allows arg modification (stretch goal)
- [ ] Auto-approval works for safe commands
- [ ] All 44+ tests pass
- [ ] Manual testing confirms full flow works

---

## Post-Phase 8

After Phase 8, the TUI will have:
- ✅ Complete HITL for all sensitive operations
- ✅ Full interrupt/resume with LangGraph
- ✅ User control over tool execution
- ✅ Edit capability for tool arguments

Next: Phase 9 (MCP & Sandboxes) - Future work
