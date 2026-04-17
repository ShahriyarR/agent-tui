# Phase 9: MCP & Sandboxes - Implementation Plan

**Date:** 2026-04-17
**Status:** Ready for Implementation
**Branch:** phase/9-mcp-sandboxes
**Merge Into:** phase/8-hitl-refinement
**Goal:** MCP tool loading, sandbox isolation

---

## Overview

Phase 9 implements **Model Context Protocol (MCP)** support and sandbox isolation for the agent-tui. MCP is a protocol for connecting AI assistants to external tools and data sources. This phase adds:

1. **MCP Server Discovery** - Parse `.mcp.json` configs and discover available tools
2. **Sandbox Backend** - Isolate agent operations in sandboxed environments
3. **MCP Tools Panel** - UI for managing and viewing MCP tools

---

## What is MCP?

**Model Context Protocol (MCP)** is an open protocol that standardizes how applications provide context to LLMs. Think of it as a "USB-C port for AI applications" - a universal way to connect AI systems to data sources, tools, and services.

### MCP Concepts:
- **Servers**: Provide tools, resources, and prompts to the agent
- **Tools**: Functions the agent can call (like web_search, calculator, etc.)
- **Resources**: Data the agent can access (files, databases, etc.)
- **Prompts**: Template prompts that can be invoked

### Example `.mcp.json`:
```json
{
  "servers": {
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    }
  }
}
```

---

## Architecture

### MCP Integration Flow

```
User has .mcp.json in project
  ↓
MCP discovery parses config
  ↓
Starts MCP servers (subprocesses)
  ↓
Discovers available tools
  ↓
Registers tools with DeepAgents
  ↓
Agent can call MCP tools via standard tool interface
  ↓
HITL approval for sensitive MCP tools (via Phase 8)
```

### Sandbox Integration Flow

```
Agent requests sandboxed execution
  ↓
SandboxBackend creates isolated environment
  ↓
Command/file operation runs in sandbox
  ↓
Results returned to agent
  ↓
Sandbox cleaned up (or persisted based on config)
```

---

## Implementation Tasks

### Task 9.1: MCP Server Discovery & Tool Loading

**File:** `src/agent_tui/services/deep_agents/mcp.py` (NEW)

**Responsibilities:**
1. Parse `.mcp.json` configuration files
2. Start MCP servers as subprocesses
3. Discover tools via MCP protocol
4. Convert MCP tools to DeepAgents-compatible format
5. Register tools with the agent

**Implementation Outline:**
```python
"""MCP integration for DeepAgents.

Handles MCP server discovery, tool registration, and communication.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPToolManager:
    """Manages MCP servers and their tools."""
    
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path.cwd() / ".mcp.json"
        self.servers: dict[str, subprocess.Popen] = {}
        self.tools: dict[str, Any] = {}
    
    def load_config(self) -> dict[str, Any] | None:
        """Load .mcp.json configuration."""
        if not self.config_path.exists():
            return None
        with open(self.config_path) as f:
            return json.load(f)
    
    async def start_servers(self) -> None:
        """Start all configured MCP servers."""
        config = self.load_config()
        if not config:
            return
        
        for name, server_config in config.get("servers", {}).items():
            await self._start_server(name, server_config)
    
    async def _start_server(self, name: str, config: dict) -> None:
        """Start a single MCP server."""
        # Start subprocess
        # Connect via MCP protocol
        # Discover tools
        # Store for later use
        pass
    
    def get_tools(self) -> list[Any]:
        """Return list of all MCP tools for registration."""
        return list(self.tools.values())
    
    async def cleanup(self) -> None:
        """Stop all MCP servers."""
        for name, process in self.servers.items():
            process.terminate()


def discover_mcp_tools(project_dir: Path | None = None) -> list[Any]:
    """Discover and return all MCP tools from .mcp.json.
    
    Args:
        project_dir: Directory to look for .mcp.json
        
    Returns:
        List of tool objects ready for DeepAgents registration
    """
    manager = MCPToolManager(
        config_path=(project_dir or Path.cwd()) / ".mcp.json"
    )
    # Start servers and discover tools
    # Return converted tools
    pass
```

**Key Libraries:**
- `mcp` - Official MCP Python SDK
- `mcp.client.stdio` - For stdio-based MCP servers

**Verification:**
- [ ] Parses `.mcp.json` correctly
- [ ] Starts MCP servers as subprocesses
- [ ] Discovers tools from servers
- [ ] Converts MCP tools to DeepAgents format
- [ ] Handles server lifecycle (start/cleanup)
- [ ] Works with multiple MCP servers

---

### Task 9.2: Sandbox Backend Integration

**File:** `src/agent_tui/services/deep_agents/sandbox.py` (NEW)

**Responsibilities:**
1. Create sandboxed execution environments
2. Isolate file operations and shell commands
3. Provide sandbox lifecycle management
4. Integrate with existing backend infrastructure

**Implementation Outline:**
```python
"""Sandbox backend for isolated agent execution.

Provides sandboxed file and shell operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents.backends import SandboxBackendProtocol


class SandboxBackend(SandboxBackendProtocol):
    """Backend that executes operations in isolated sandbox.
    
    All file and shell operations are contained within the sandbox,
    preventing access to the host system outside the sandbox root.
    """
    
    def __init__(
        self,
        root_dir: Path | None = None,
        cleanup: bool = True,
    ) -> None:
        self.root_dir = root_dir or Path.cwd() / ".agent-sandbox"
        self.cleanup = cleanup
        self._ensure_sandbox()
    
    def _ensure_sandbox(self) -> None:
        """Create sandbox directory if it doesn't exist."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
    
    async def read(self, path: str) -> Any:
        """Read file from sandbox."""
        # Resolve path within sandbox
        # Read file
        # Return result
        pass
    
    async def write(self, path: str, content: str) -> Any:
        """Write file to sandbox."""
        # Resolve path within sandbox
        # Write file
        # Return result
        pass
    
    async def execute(
        self,
        command: str,
        timeout: float | None = None,
    ) -> Any:
        """Execute command in sandbox environment."""
        # Run command with sandbox as cwd
        # Capture output
        # Return result
        pass
    
    async def cleanup(self) -> None:
        """Clean up sandbox if configured."""
        if self.cleanup:
            # Remove sandbox directory
            pass
```

**Sandbox Options:**
1. **Directory-based**: Simple isolation via directory (implemented above)
2. **Container-based**: Docker/containerd isolation (future enhancement)
3. **VM-based**: Full VM isolation (future enhancement)

**Verification:**
- [ ] Creates sandbox directory
- [ ] All operations contained in sandbox
- [ ] Path traversal blocked (../ escapes)
- [ ] Cleanup works correctly
- [ ] Integrates with CompositeBackend

---

### Task 9.3: MCP Tools Panel in UI

**File:** `src/agent_tui/entrypoints/app.py` (MODIFY)

**Responsibilities:**
1. Add MCP tools panel/sidebar
2. Display discovered MCP tools
3. Show MCP server status
4. Allow manual refresh of MCP tools

**UI Design:**
```
┌──────────────────────────────────────────────────────┐
│ MCP Tools                           [Refresh] [×]   │
├──────────────────────────────────────────────────────┤
│ 🔌 fetch-server              ● connected (3 tools)  │
│   - fetch_url                                        │
│   - fetch_html                                       │
│   - extract_content                                  │
│                                                      │
│ 🔌 filesystem-server          ● connected (4 tools)   │
│   - read_file                                        │
│   - write_file                                       │
│   - list_directory                                   │
│   - search_files                                     │
│                                                      │
│ 🔌 calculator-server          ○ disconnected        │
├──────────────────────────────────────────────────────┤
│ Config: .mcp.json                                    │
└────────────────────────────────────────────────────────┘
```

**Implementation:**
- Add toggle button in main UI to show/hide MCP panel
- Display server connection status (connected/disconnected)
- List tools under each server
- Allow refresh to reload MCP config

**Verification:**
- [ ] Panel displays correctly
- [ ] Shows server status
- [ ] Lists tools per server
- [ ] Refresh button works
- [ ] Toggle show/hide works

---

## Integration with Existing Phases

### Integration with Phase 8 (HITL)
MCP tools should respect the HITL configuration:
```python
# In interrupt_on config, MCP tools can be added:
interrupt_on = InterruptOnConfig(
    tools={
        # ... existing tools
        "fetch_url": True,      # MCP tool - interrupt
        "filesystem_write": True,  # MCP tool - interrupt
    }
)
```

### Integration with Phase 7 (Memory/Skills)
MCP resources can feed into memory system:
```
MCP resource (e.g., database) 
  → Agent reads via MCP
  → Stored in memory
  → Used in future conversations
```

---

## Files to Create/Modify

| File | Type | Task |
|------|------|------|
| `services/deep_agents/mcp.py` | NEW | 9.1 - MCP discovery |
| `services/deep_agents/sandbox.py` | NEW | 9.2 - Sandbox backend |
| `entrypoints/app.py` | MODIFY | 9.3 - MCP panel |
| `entrypoints/widgets/mcp_panel.py` | NEW | 9.3 - MCP UI widget |
| `pyproject.toml` | MODIFY | Add mcp dependency |

---

## Dependencies

**New Package:**
```toml
[project.dependencies]
mcp = ">=1.0.0"  # Official MCP SDK
```

---

## Testing Strategy

### Unit Tests
1. Test MCP config parsing
2. Test MCP server lifecycle
3. Test sandbox path isolation
4. Test sandbox cleanup

### Integration Tests
1. Test full MCP discovery flow
2. Test agent using MCP tools
3. Test sandbox file operations
4. Test sandbox shell execution

### Manual Tests
1. Create `.mcp.json` with fetch server
2. Start agent, verify tools discovered
3. Use fetch_url MCP tool
4. Verify sandbox isolation

---

## Definition of Done

- [ ] MCP config parsing works
- [ ] MCP servers start and provide tools
- [ ] MCP tools integrate with DeepAgents
- [ ] Sandbox backend isolates operations
- [ ] MCP panel shows in UI
- [ ] All tests pass
- [ ] Manual testing confirms full flow

---

## Post-Phase 9

After Phase 9, the TUI will have:
- ✅ MCP server discovery and tool loading
- ✅ Multiple MCP servers can run simultaneously
- ✅ Sandboxed execution environment
- ✅ UI panel for managing MCP tools
- ✅ Full integration with HITL (Phase 8)

**Next:** Phase 10 could be advanced features like:
- Multi-agent coordination
- Advanced sandboxing (containers)
- Plugin system
- Custom tool registry
