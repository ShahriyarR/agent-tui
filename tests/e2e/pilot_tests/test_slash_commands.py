"""E2E tests for slash commands using StubAgent.

Commands are dispatched directly via _handle_command to avoid autocomplete
interference from the ChatInput widget when typing slash commands.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_help_command_mounts_app_message(e2e_stub_app):
    """'/help' should mount an AppMessage with the command list."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    before = len(app.query(AppMessage))
    await app._handle_command("/help")
    await pilot.pause(0.3)

    assert len(app.query(AppMessage)) > before


@pytest.mark.asyncio
async def test_help_command_content_mentions_commands(e2e_stub_app):
    """'/help' output should mention key slash commands."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    await app._handle_command("/help")
    await pilot.pause(0.3)

    contents = [str(m._content) for m in app.query(AppMessage)]
    combined = " ".join(contents).lower()
    assert "/clear" in combined
    assert "/quit" in combined


@pytest.mark.asyncio
async def test_version_command_shows_version_text(e2e_stub_app):
    """'/version' should mount an AppMessage containing 'version'."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    await app._handle_command("/version")
    await pilot.pause(0.3)

    contents = [str(m._content) for m in app.query(AppMessage)]
    assert any("version" in c.lower() for c in contents)


@pytest.mark.asyncio
async def test_clear_command_changes_thread_id(e2e_stub_app):
    """'/clear' should reset the session to a new thread ID."""
    app, pilot = e2e_stub_app

    await pilot.pause(0.5)
    original_thread = app._session_state.thread_id

    await app._handle_command("/clear")
    await pilot.pause(0.3)

    assert app._session_state.thread_id != original_thread


@pytest.mark.asyncio
async def test_tokens_command_with_no_prior_usage(e2e_stub_app):
    """'/tokens' before any agent message should report no token usage yet."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    await app._handle_command("/tokens")
    await pilot.pause(0.3)

    contents = [str(m._content) for m in app.query(AppMessage)]
    assert any("no token usage" in c.lower() for c in contents)


@pytest.mark.asyncio
async def test_skills_command_mounts_app_message(e2e_stub_app):
    """'/skills' should always mount an AppMessage (skills list or 'no skills')."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    before = len(app.query(AppMessage))
    await app._handle_command("/skills")
    await pilot.pause(0.3)

    assert len(app.query(AppMessage)) > before


@pytest.mark.asyncio
async def test_memory_command_mounts_app_message(e2e_stub_app):
    """'/memory' should mount an AppMessage with memory summary."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    before = len(app.query(AppMessage))
    await app._handle_command("/memory")
    await pilot.pause(0.3)

    assert len(app.query(AppMessage)) > before


@pytest.mark.asyncio
async def test_unknown_command_shows_unknown_message(e2e_stub_app):
    """An unrecognized slash command should mount 'Unknown command:' in an AppMessage."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AppMessage

    await app._handle_command("/notarealcommand")
    await pilot.pause(0.3)

    contents = [str(m._content) for m in app.query(AppMessage)]
    assert any("unknown command" in c.lower() for c in contents)
