import pytest
from agent_tui.services.deep_agents.title import TitleGenerator


@pytest.fixture
def title_generator():
    return TitleGenerator()


@pytest.mark.asyncio
async def test_generate_title_returns_string(title_generator):
    result = await title_generator.generate_title(
        user_message="Create FastAPI endpoint in main.py",
        assistant_response="I'll create a FastAPI endpoint for you..."
    )
    assert isinstance(result, str)
    assert len(result) <= 40


@pytest.mark.asyncio
async def test_generate_title_handles_empty(title_generator):
    result = await title_generator.generate_title("", "")
    assert result == "Untitled Chat"
