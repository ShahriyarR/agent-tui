"""MCP tools panel widget for displaying and managing MCP servers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from agent_tui.services.deep_agents.mcp import MCPToolManager


class MCPPanel(Static):
    """Panel displaying MCP servers and their tools.

    This widget provides a sidebar view of MCP server status, showing:
    - Connected/disconnected status for each server
    - Tool names under each server
    - Refresh button to reload MCP configuration
    - Close button to hide the panel

    Example:
        panel = MCPPanel(tool_manager=manager)
        app.mount(panel)
    """

    # Reactive data binding - triggers re-render when servers change
    server_data: reactive[dict[str, Any]] = reactive({}, init=False)

    DEFAULT_CSS = """
    MCPPanel {
        width: 40;
        height: 100%;
        dock: right;
        background: $surface;
        border-left: solid $primary;
        padding: 0;
    }

    MCPPanel .mcp-header {
        height: 3;
        padding: 0 1;
        border-bottom: solid $primary-darken-2;
    }

    MCPPanel .mcp-title {
        text-style: bold;
        width: 1fr;
        content-align-vertical: center;
    }

    MCPPanel .mcp-header Button {
        width: auto;
        margin: 0 0 0 1;
    }

    MCPPanel .mcp-servers {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    MCPPanel .mcp-server {
        color: $primary;
        margin: 1 0 0 0;
        text-style: bold;
    }

    MCPPanel .mcp-server-connected {
        color: $success;
    }

    MCPPanel .mcp-server-disconnected {
        color: $error;
    }

    MCPPanel .mcp-tool {
        color: $text-muted;
        margin: 0 0 0 2;
    }

    MCPPanel .mcp-status-connected {
        color: $success;
    }

    MCPPanel .mcp-status-disconnected {
        color: $error;
    }

    MCPPanel .mcp-empty {
        color: $text-muted;
        text-style: italic;
        text-align: center;
        margin-top: 2;
    }

    MCPPanel .mcp-footer {
        height: 1;
        padding: 0 1;
        border-top: solid $primary-darken-2;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        tool_manager: MCPToolManager | None = None,
        *,
        config_path: str = ".mcp.json",
        **kwargs: Any,
    ) -> None:
        """Initialize the MCP panel.

        Args:
            tool_manager: MCPToolManager instance for accessing MCP data
            config_path: Path to MCP configuration file (for display)
            **kwargs: Additional arguments passed to Static
        """
        self.tool_manager = tool_manager
        self.config_path = config_path
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """Compose the panel UI."""
        with Horizontal(classes="mcp-header"):
            yield Label("MCP Tools", classes="mcp-title")
            yield Button("Refresh", id="refresh-mcp", variant="primary")
            yield Button("×", id="close-mcp", variant="error")

        yield Vertical(id="mcp-servers", classes="mcp-servers")

        yield Label(f"Config: {self.config_path}", classes="mcp-footer")

    def on_mount(self) -> None:
        """Initialize panel on mount."""
        self.refresh_servers()

    def watch_server_data(self, _new_data: dict[str, Any]) -> None:
        """React to server data changes."""
        self.refresh_servers()

    def refresh_servers(self) -> None:
        """Refresh the list of MCP servers and tools."""
        try:
            servers_container = self.query_one("#mcp-servers", Vertical)
        except Exception:
            # Container not yet mounted
            return

        servers_container.remove_children()

        if not self.tool_manager:
            servers_container.mount(Label("No MCP configuration found", classes="mcp-empty"))
            return

        # Use either reactive data or the tool manager directly
        servers = self.server_data or self.tool_manager.servers

        if not servers:
            servers_container.mount(Label("No MCP servers configured", classes="mcp-empty"))
            return

        for server_name, server_info in servers.items():
            self._render_server(servers_container, server_name, server_info)

    def _render_server(
        self,
        container: Vertical,
        server_name: str,
        server_info: dict[str, Any],
    ) -> None:
        """Render a single server and its tools.

        Args:
            container: The container to mount server UI into
            server_name: Name of the MCP server
            server_info: Server data dict with 'connected' and 'tools' keys
        """
        is_connected = server_info.get("connected", False)
        tools = server_info.get("tools") or []
        tool_count = len(tools)

        # Status indicator (● connected, ○ disconnected)
        status_icon = "●" if is_connected else "○"
        status_class = "mcp-status-connected" if is_connected else "mcp-status-disconnected"
        server_class = "mcp-server-connected" if is_connected else "mcp-server-disconnected"

        # Server header with status
        status_text = f"connected ({tool_count} tools)" if is_connected else "disconnected"
        server_label = Label(
            f"{status_icon} {server_name} - {status_text}",
            classes=f"mcp-server {server_class}",
        )
        container.mount(server_label)

        # Tool list
        if tools:
            for tool in tools:
                tool_name = tool if isinstance(tool, str) else tool.get("name", str(tool))
                container.mount(Label(f"  - {tool_name}", classes="mcp-tool"))

    def update_server_data(self, servers: dict[str, Any]) -> None:
        """Update server data from external source.

        Args:
            servers: Dictionary of server_name -> server_info
        """
        self.server_data = servers

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "refresh-mcp":
            self._handle_refresh()
        elif button_id == "close-mcp":
            self._handle_close()

    def _handle_refresh(self) -> None:
        """Handle refresh button press.

        Reloads MCP configuration and refreshes the display.
        """
        if self.tool_manager:
            # Trigger a refresh from the tool manager
            self.refresh_servers()
            self.notify("MCP configuration refreshed", severity="information")
        else:
            self.notify("No MCP tool manager available", severity="warning")

    def _handle_close(self) -> None:
        """Handle close button press.

        Removes the panel from the DOM.
        """
        self.remove()

    def get_server_count(self) -> int:
        """Get the number of servers displayed.

        Returns:
            Number of MCP servers in the panel
        """
        if self.tool_manager:
            return len(self.tool_manager.servers)
        return len(self.server_data)

    def get_tool_count(self) -> int:
        """Get the total number of tools across all servers.

        Returns:
            Total count of MCP tools
        """
        total = 0
        servers = self.tool_manager.servers if self.tool_manager else self.server_data
        for server_info in servers.values():
            tools = server_info.get("tools", [])
            total += len(tools)
        return total
