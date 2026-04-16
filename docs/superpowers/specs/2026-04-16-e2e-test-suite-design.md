# E2E Test Suite Design for agent-tui

**Date:** 2026-04-16
**Status:** Approved

## Overview

A full end-to-end test suite that runs the agent-tui TUI, acts as a human user (sending keystrokes, approvals), and validates the correctness of Phases 1-3 (DeepAgents integration, file tool approval, shell execution with safety controls).

## Goals

- Validate all three phases work together in an integrated flow
- Run the actual TUI application (not mocked/stubbed internals)
- Act as a human user: send messages, approve tools, handle errors
- Fail fast with detailed logs when something goes wrong
- Two execution layers: fast Textual Pilot tests + full terminal PTY tests

## Architecture

### Dual-Layer Approach

| Layer | Tool | Speed | Fidelity | Use Case |
|-------|------|-------|----------|----------|
| Pilot | `TextualPilot` + `run_test()` | Fast (~100ms/test) | Widget state, events | 90% of tests, CI-like runs |
| PTY | `pty_spawn` | Slower (~1s/test) | True terminal, escape codes | Terminal rendering, key handling |

### Directory Structure

```
tests/e2e/
├── conftest.py              # Shared fixtures
├── pilot_tests/
│   ├── test_phase1_agent.py         # Agent streaming, model switch
│   ├── test_phase2_file_tools.py    # File read/write/edit approval
│   ├── test_phase3_shell.py        # Shell execution, dangerous patterns
│   └── test_integration.py          # Full Phase 1+2+3 flow
├── pty_tests/
│   └── test_terminal.py            # True terminal rendering
└── run_e2e.py                      # CLI runner
```

**Important:** Pilot tests use the **DeepAgentsAdapter** backend by default (not StubAgent).

## Fixtures

### `e2e_app_factory(deepagents_mode=True)`
- Creates `AgentTuiApp` with `DeepAgentsAdapter` (or `StubAgent` if `deepagents_mode=False`)
- Returns `(app, pilot)` tuple
- App runs via `app.run_test()`

### `captured_events`
- Records all `AgentEvent` objects during test execution
- Returns list of events for assertions

### `pty_session()`
- Spawns actual TUI process via `pty_spawn`
- Provides `send()`, `read_until()`, `expect()` interface
- Used only in `pty_tests/`

## Test Scenarios

### Phase 1: Agent Integration
- Agent streams message chunks correctly
- Model can be switched
- Thread history loads/resumes

### Phase 2: File Tool Approval
- `Read test.txt` → approval widget appears → user approves → content displayed
- `Write test.txt` with content → approval → file created with content
- `Edit test.txt` → approval → file modified correctly
- Path normalization: `/test.txt` shows as `test.txt` in UI

### Phase 3: Shell Execution
- `execute echo hello` → approval → command runs → output displayed
- Dangerous patterns blocked:
  - `$(rm -rf /)` → error: "dangerous pattern detected"
  - `` `cat /etc/passwd` `` → blocked
  - `$VAR` in commands → blocked
  - `>>` redirects → blocked

### Integration Tests
- Full conversation: message → thinking → tool call → approval → result → next message
- Interrupt with Ctrl+C mid-stream
- Auto-approve toggle (Ctrl+T)
- Error recovery

### Terminal Fidelity (PTY)
- Colors render correctly
- Unicode renders correctly
- Key bindings work (arrows, enter, escape)
- iTerm2 cursor guide disabled on startup

## Failure Handling

**Fail Fast** — When a test assertion fails:
1. Capture test name, assertion, and expected vs actual
2. Record last 50 lines of TUI output / widget states
3. Print detailed failure report to console
4. Test marked as FAILED
5. Human investigates manually

No automatic fix proposals. Human reviews logs and fixes directly.

## CLI Usage

```bash
# Run all E2E tests (deepagents backend)
uv run python tests/e2e/run_e2e.py

# Run only pilot tests (fast, deepagents backend)
uv run python tests/e2e/run_e2e.py --pilot-only

# Run with stub backend (debugging only)
uv run python tests/e2e/run_e2e.py --agent=stub

# Run only PTY tests
uv run python tests/e2e/run_e2e.py --pty-only

# Run specific test file
uv run pytest tests/e2e/pilot_tests/test_phase2_file_tools.py -v
```

## Test Execution Model

- **Local only** — No CI automation
- Requires `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) for deepagents tests
- Stub agent tests work without API keys

## Dependencies

- `pytest>=9.0.3`
- `pytest-asyncio>=1.3.0`
- `textual>=8.0.0` (provides `run_test()` and `TextualPilot`)

## Non-Goals

- No approval workflow for fixes (fail fast only)
- No automatic test generation from specs
- No screenshot/visual regression testing
- Not run in CI
