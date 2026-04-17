"""E2E tests for agent event flows using StubAgent scenarios.

StubAgent cycles through three scenarios per message:
  0 → tool call flow (TOOL_CALL, waits for approval)
  1 → ask-user flow (ASK_USER, waits for answer)
  2 → error flow (ERROR event, runs to completion unblocked)
"""

from __future__ import annotations

import pytest


async def _make_app(agent, *, auto_approve: bool = False):
    """Local helper matching conftest._create_app."""
    from agent_tui.entrypoints.app import AgentTuiApp
    from tests.e2e.conftest import PilotHelper

    app = AgentTuiApp(agent=agent, auto_approve=auto_approve)
    async with app.run_test() as pilot:
        yield app, PilotHelper(pilot)


@pytest.fixture
async def error_scenario_stub_app():
    """StubAgent app pre-seeded to scenario 2 so first message triggers an error flow."""
    from agent_tui.services.stub_agent import StubAgent

    agent = StubAgent()
    agent._message_count = 2  # Scenario index = _message_count % 3 = 2 → error flow
    async for result in _make_app(agent):
        yield result


@pytest.mark.asyncio
async def test_message_submission_creates_user_message(e2e_stub_app):
    """Submitting a message should add a UserMessage widget to the chat."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import UserMessage

    before = len(app.query(UserMessage))
    await pilot.click("#input-area")
    await pilot.type("hello from test")
    await pilot.press("enter")
    await pilot.pause(0.5)

    assert len(app.query(UserMessage)) > before


@pytest.mark.asyncio
async def test_tool_call_shows_approval_menu(e2e_stub_app):
    """First message (scenario 0) emits TOOL_CALL, which should show an ApprovalMenu."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.approval import ApprovalMenu

    await pilot.click("#input-area")
    await pilot.type("trigger tool call")
    await pilot.press("enter")
    await pilot.pause(2.0)  # Wait for stream to reach TOOL_CALL and mount the menu

    assert len(app.query(ApprovalMenu)) > 0


@pytest.mark.asyncio
async def test_agent_response_creates_assistant_message(e2e_stub_app):
    """Any message should produce an AssistantMessage from the opening stream chunks."""
    app, pilot = e2e_stub_app
    from agent_tui.entrypoints.widgets.messages import AssistantMessage

    before = len(app.query(AssistantMessage))
    await pilot.click("#input-area")
    await pilot.type("hello agent")
    await pilot.press("enter")
    await pilot.pause(1.0)  # Opening chunks stream before any blocking event

    assert len(app.query(AssistantMessage)) > before


@pytest.mark.asyncio
async def test_error_event_shows_error_message(error_scenario_stub_app):
    """Agent ERROR event (scenario 2) should produce an ErrorMessage widget."""
    app, pilot = error_scenario_stub_app
    from agent_tui.entrypoints.widgets.messages import ErrorMessage

    before = len(app.query(ErrorMessage))
    await pilot.click("#input-area")
    await pilot.type("trigger error")
    await pilot.press("enter")
    await pilot.pause(3.0)  # Wait for the error flow to complete

    assert len(app.query(ErrorMessage)) > before


@pytest.mark.asyncio
async def test_token_count_updates_after_stream_completion(error_scenario_stub_app):
    """TOKEN_UPDATE event should update app._last_token_count once the stream ends."""
    app, pilot = error_scenario_stub_app

    assert app._last_token_count == 0
    await pilot.click("#input-area")
    await pilot.type("update tokens")
    await pilot.press("enter")
    await pilot.pause(3.0)  # Scenario 2 runs to completion: chunks + ERROR + chunks + TOKEN_UPDATE

    assert app._last_token_count > 0


@pytest.mark.asyncio
async def test_escape_interrupts_stream_and_app_stays_running(error_scenario_stub_app):
    """Escape during an active stream should cancel the agent but keep the app alive."""
    app, pilot = error_scenario_stub_app

    await pilot.click("#input-area")
    await pilot.type("start a stream to interrupt")
    await pilot.press("enter")
    await pilot.pause(0.3)  # Let the stream start (no blocking event in scenario 2)

    await pilot.press("escape")
    await pilot.pause(0.5)

    assert app.is_running
