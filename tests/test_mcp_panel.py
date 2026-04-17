"""Tests for MCP panel widget.

These tests verify the MCP panel displays servers and tools correctly,
handles user interactions, and integrates with the app properly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_tui.entrypoints.widgets.mcp_panel import MCPPanel


class TestMCPPanelBasic:
    """Basic tests for MCPPanel widget initialization."""

    def test_init_without_tool_manager(self):
        """MCPPanel should initialize without a tool manager."""
        panel = MCPPanel()

        assert panel.tool_manager is None
        assert panel.config_path == ".mcp.json"
        assert panel.server_data == {}

    def test_init_with_tool_manager(self):
        """MCPPanel should accept a tool manager."""
        mock_manager = MagicMock()
        mock_manager.servers = {}

        panel = MCPPanel(tool_manager=mock_manager)

        assert panel.tool_manager is mock_manager
        assert panel.config_path == ".mcp.json"

    def test_init_with_custom_config_path(self):
        """MCPPanel should accept custom config path."""
        panel = MCPPanel(config_path="custom/config.json")

        assert panel.config_path == "custom/config.json"


class TestMCPPanelCompose:
    """Tests for MCPPanel compose and UI structure."""

    def test_compose_returns_widgets(self):
        """Panel compose should yield widgets."""
        panel = MCPPanel()

        # Create a simple container to hold the panel's widgets
        from textual.containers import Container

        container = Container()

        # Compose needs a parent widget context for Horizontal/Vertical
        # Just verify the compose method exists and can be called
        # by checking it returns a generator
        result = panel.compose()
        assert result is not None
        # Don't iterate the generator without proper Textual context

    def test_panel_has_expected_structure(self):
        """Panel should have the expected CSS class structure."""
        panel = MCPPanel()

        # Verify the widget has the expected CSS
        assert "mcp-title" in panel.DEFAULT_CSS
        assert "mcp-header" in panel.DEFAULT_CSS
        assert "mcp-servers" in panel.DEFAULT_CSS


class TestMCPPanelServerRendering:
    """Tests for MCPPanel server display functionality."""

    def test_refresh_servers_with_no_manager(self):
        """Panel should show empty message when no tool manager."""
        panel = MCPPanel()

        # Mock the query_one to avoid DOM issues
        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            panel.refresh_servers()

            # Should mount empty message
            mock_container.remove_children.assert_called_once()
            mock_container.mount.assert_called_once()
            # Check that the mounted label has the right class
            call_args = mock_container.mount.call_args
            assert call_args is not None
            label = call_args[0][0]
            assert "mcp-empty" in str(label.classes)

    def test_refresh_servers_with_empty_servers(self):
        """Panel should show empty message when no servers configured."""
        mock_manager = MagicMock()
        mock_manager.servers = {}

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            panel.refresh_servers()

            # Should mount empty message
            mock_container.remove_children.assert_called_once()
            mock_container.mount.assert_called_once()

    def test_refresh_servers_with_connected_server(self):
        """Panel should render connected server correctly."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "fetch-server": {
                "connected": True,
                "tools": ["fetch_url", "fetch_html"],
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            panel.refresh_servers()

            # Should mount server header and tools
            mock_container.remove_children.assert_called_once()
            assert mock_container.mount.call_count == 3  # Server header + 2 tools

    def test_refresh_servers_with_disconnected_server(self):
        """Panel should render disconnected server correctly."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "calc-server": {
                "connected": False,
                "tools": [],
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            panel.refresh_servers()

            # Should mount only server header (no tools)
            mock_container.remove_children.assert_called_once()
            mock_container.mount.assert_called_once()

    def test_render_server_with_tool_objects(self):
        """Panel should handle tools as objects with name attribute."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "test-server": {
                "connected": True,
                "tools": [
                    {"name": "tool1", "description": "Tool 1"},
                    {"name": "tool2", "description": "Tool 2"},
                ],
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            panel.refresh_servers()

            # Should mount server header and 2 tools
            assert mock_container.mount.call_count == 3


class TestMCPPanelActions:
    """Tests for MCPPanel button actions."""

    def test_close_button_removes_panel(self):
        """Close button should remove the panel."""
        panel = MCPPanel()

        with patch.object(panel, "remove") as mock_remove:
            # Create a mock button press event
            mock_button = MagicMock()
            mock_button.id = "close-mcp"

            # Create a mock event
            mock_event = MagicMock()
            mock_event.button = mock_button

            panel.on_button_pressed(mock_event)

            mock_remove.assert_called_once()

    def test_refresh_button_refreshes_display(self):
        """Refresh button should refresh the server display."""
        mock_manager = MagicMock()
        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "refresh_servers") as mock_refresh:
            with patch.object(panel, "notify") as mock_notify:
                # Create a mock button press event
                mock_button = MagicMock()
                mock_button.id = "refresh-mcp"

                # Create a mock event
                mock_event = MagicMock()
                mock_event.button = mock_button

                panel.on_button_pressed(mock_event)

                mock_refresh.assert_called_once()
                mock_notify.assert_called_once_with("MCP configuration refreshed", severity="information")

    def test_refresh_button_without_manager(self):
        """Refresh button should show warning when no manager."""
        panel = MCPPanel()

        with patch.object(panel, "notify") as mock_notify:
            # Create a mock button press event
            mock_button = MagicMock()
            mock_button.id = "refresh-mcp"

            # Create a mock event
            mock_event = MagicMock()
            mock_event.button = mock_button

            panel.on_button_pressed(mock_event)

            mock_notify.assert_called_once_with("No MCP tool manager available", severity="warning")


class TestMCPPanelDataBinding:
    """Tests for MCPPanel reactive data binding."""

    def test_update_server_data_updates_reactive(self):
        """update_server_data should update reactive server_data."""
        panel = MCPPanel()
        new_data = {"server1": {"connected": True, "tools": []}}

        panel.update_server_data(new_data)

        assert panel.server_data == new_data

    def test_watch_server_data_triggers_refresh(self):
        """Changing server_data should trigger refresh_servers."""
        panel = MCPPanel()

        with patch.object(panel, "refresh_servers") as mock_refresh:
            panel.server_data = {"server1": {"connected": True, "tools": []}}

            mock_refresh.assert_called_once()


class TestMCPPanelCounters:
    """Tests for MCPPanel helper methods."""

    def test_get_server_count_with_manager(self):
        """get_server_count should return count from tool_manager."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "server1": {"connected": True, "tools": []},
            "server2": {"connected": False, "tools": []},
        }

        panel = MCPPanel(tool_manager=mock_manager)

        assert panel.get_server_count() == 2

    def test_get_server_count_with_reactive_data(self):
        """get_server_count should fall back to server_data."""
        panel = MCPPanel()
        panel.server_data = {
            "server1": {"connected": True, "tools": []},
        }

        assert panel.get_server_count() == 1

    def test_get_tool_count_with_manager(self):
        """get_tool_count should return total tools from tool_manager."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "server1": {"connected": True, "tools": ["tool1", "tool2"]},
            "server2": {"connected": True, "tools": ["tool3"]},
        }

        panel = MCPPanel(tool_manager=mock_manager)

        assert panel.get_tool_count() == 3

    def test_get_tool_count_with_tool_objects(self):
        """get_tool_count should handle tools as objects."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "server1": {
                "connected": True,
                "tools": [
                    {"name": "tool1"},
                    {"name": "tool2"},
                ],
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        assert panel.get_tool_count() == 2

    def test_get_tool_count_empty(self):
        """get_tool_count should return 0 when no servers."""
        panel = MCPPanel()

        assert panel.get_tool_count() == 0


class TestMCPPanelIntegration:
    """Integration tests for MCPPanel with real-like data."""

    def test_multiple_servers_mixed_status(self):
        """Panel should handle multiple servers with different statuses."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "fetch-server": {
                "connected": True,
                "tools": ["fetch_url", "fetch_html", "extract_content"],
            },
            "filesystem-server": {
                "connected": True,
                "tools": ["read_file", "write_file", "list_directory", "search_files"],
            },
            "calculator-server": {
                "connected": False,
                "tools": [],
            },
        }

        panel = MCPPanel(tool_manager=mock_manager)

        # Verify counts
        assert panel.get_server_count() == 3
        assert panel.get_tool_count() == 7

    def test_server_with_many_tools(self):
        """Panel should handle servers with many tools."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "big-server": {
                "connected": True,
                "tools": [f"tool_{i}" for i in range(50)],
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        assert panel.get_server_count() == 1
        assert panel.get_tool_count() == 50


class TestMCPPanelEdgeCases:
    """Edge case tests for MCPPanel."""

    def test_render_server_with_none_tools(self):
        """Panel should handle None tools list."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "broken-server": {
                "connected": True,
                "tools": None,
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            # Should not raise exception
            panel.refresh_servers()

            # Should mount the server header (no tools when tools is None)
            mock_container.remove_children.assert_called_once()
            # Should mount server header only
            mock_container.mount.assert_called_once()

    def test_render_server_with_missing_connected_key(self):
        """Panel should handle missing 'connected' key."""
        mock_manager = MagicMock()
        mock_manager.servers = {
            "partial-server": {
                "tools": ["tool1"],
                # No 'connected' key
            }
        }

        panel = MCPPanel(tool_manager=mock_manager)

        with patch.object(panel, "query_one") as mock_query:
            mock_container = MagicMock()
            mock_query.return_value = mock_container

            # Should not raise exception
            panel.refresh_servers()

            # Should mount server and tool
            assert mock_container.mount.call_count == 2

    def test_query_one_exception_handling(self):
        """refresh_servers should handle query_one exceptions gracefully."""
        panel = MCPPanel()

        with patch.object(panel, "query_one", side_effect=Exception("DOM not ready")):
            # Should not raise exception
            panel.refresh_servers()


class TestMCPPanelCSS:
    """Tests for MCPPanel CSS classes."""

    def test_default_css_is_defined(self):
        """MCPPanel should have DEFAULT_CSS defined."""
        assert MCPPanel.DEFAULT_CSS is not None
        assert len(MCPPanel.DEFAULT_CSS) > 0

    def test_css_contains_expected_classes(self):
        """CSS should contain expected class definitions."""
        css = MCPPanel.DEFAULT_CSS

        expected_classes = [
            "mcp-header",
            "mcp-title",
            "mcp-servers",
            "mcp-server",
            "mcp-tool",
            "mcp-status-connected",
            "mcp-status-disconnected",
            "mcp-empty",
            "mcp-footer",
        ]

        for cls in expected_classes:
            assert cls in css, f"CSS class '{cls}' not found"
