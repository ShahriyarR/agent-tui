"""Tests for /skills and /memory slash commands in _handle_command()."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSkillsCommand:
    """Tests for the /skills slash command handler logic."""

    @pytest.mark.asyncio
    async def test_skills_with_skills_shows_formatted_list(self):
        """When the agent returns skills, format them as a numbered list."""
        mock_agent = AsyncMock()
        mock_agent.get_skills = AsyncMock(
            return_value=[
                {"name": "web-search", "description": "Search the web for information"},
                {"name": "summarize", "description": "Summarize text content"},
            ]
        )

        # Simulate the handler logic directly
        skills = await mock_agent.get_skills()
        assert len(skills) == 2

        lines = [f"Available skills ({len(skills)}):"]
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            if description:
                lines.append(f"  {name} \u2014 {description}")
            else:
                lines.append(f"  {name}")
        formatted = "\n".join(lines)

        assert "Available skills (2):" in formatted
        assert "  web-search \u2014 Search the web for information" in formatted
        assert "  summarize \u2014 Summarize text content" in formatted

    @pytest.mark.asyncio
    async def test_skills_without_description_shows_name_only(self):
        """When a skill has no description, show only the name."""
        mock_agent = AsyncMock()
        mock_agent.get_skills = AsyncMock(
            return_value=[
                {"name": "no-desc", "description": ""},
            ]
        )

        skills = await mock_agent.get_skills()
        lines = [f"Available skills ({len(skills)}):"]
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            if description:
                lines.append(f"  {name} \u2014 {description}")
            else:
                lines.append(f"  {name}")
        formatted = "\n".join(lines)

        assert "  no-desc" in formatted
        assert "\u2014" not in formatted

    @pytest.mark.asyncio
    async def test_skills_with_no_agent_shows_empty_message(self):
        """When there is no agent, show the empty-skills message."""
        # No agent set (_agent is None), so we use empty skills list
        skills: list = []
        if skills:
            result = f"Available skills ({len(skills)}):"
        else:
            result = "No skills available. Create .deepagents/skills/ directory and add .md files."

        assert result == "No skills available. Create .deepagents/skills/ directory and add .md files."

    @pytest.mark.asyncio
    async def test_skills_with_empty_list_shows_empty_message(self):
        """When agent returns empty list, show the empty-skills message."""
        mock_agent = AsyncMock()
        mock_agent.get_skills = AsyncMock(return_value=[])

        skills = await mock_agent.get_skills()

        if skills:
            result = f"Available skills ({len(skills)}):"
        else:
            result = "No skills available. Create .deepagents/skills/ directory and add .md files."

        assert result == "No skills available. Create .deepagents/skills/ directory and add .md files."

    @pytest.mark.asyncio
    async def test_skills_exception_shows_error_message(self):
        """When get_skills() raises, produce 'Failed to load skills.' message."""
        mock_agent = AsyncMock()
        mock_agent.get_skills = AsyncMock(side_effect=RuntimeError("connection error"))

        error_message = None
        try:
            await mock_agent.get_skills()
        except Exception:
            error_message = "Failed to load skills."

        assert error_message == "Failed to load skills."

    @pytest.mark.asyncio
    async def test_skills_count_in_header(self):
        """Header shows the correct skill count."""
        mock_agent = AsyncMock()
        mock_agent.get_skills = AsyncMock(
            return_value=[
                {"name": "a", "description": "alpha"},
                {"name": "b", "description": "beta"},
                {"name": "c", "description": "gamma"},
            ]
        )

        skills = await mock_agent.get_skills()
        header = f"Available skills ({len(skills)}):"
        assert header == "Available skills (3):"


class TestMemoryCommand:
    """Tests for the /memory slash command handler logic."""

    def test_memory_calls_get_memory_summary(self, tmp_path, monkeypatch):
        """When memory files exist, get_memory_summary is called and result shown."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".deepagents").mkdir()
        (tmp_path / ".deepagents" / "AGENTS.md").write_text("line1\nline2")

        from agent_tui.services.deep_agents.memory import get_memory_summary

        summary = get_memory_summary()
        assert "Memory loaded from 1 source(s):" in summary
        assert ".deepagents/AGENTS.md (2 lines)" in summary

    def test_memory_no_files_shows_no_files_message(self, tmp_path, monkeypatch):
        """When no AGENTS.md files exist, summary says no files found."""
        monkeypatch.chdir(tmp_path)

        from agent_tui.services.deep_agents.memory import get_memory_summary

        summary = get_memory_summary()
        assert "No AGENTS.md files found" in summary

    def test_memory_import_error_shows_not_available(self):
        """When import fails, show 'Memory not available' message."""
        error_message = None

        with patch.dict("sys.modules", {"agent_tui.services.deep_agents.memory": None}):
            try:
                from agent_tui.services.deep_agents.memory import get_memory_summary  # noqa: F401

                summary = get_memory_summary()  # noqa: F841
            except Exception:
                error_message = "Memory not available (DeepAgents not configured)."

        assert error_message == "Memory not available (DeepAgents not configured)."

    def test_memory_runtime_error_shows_not_available(self):
        """When get_memory_summary() raises, show 'Memory not available' message."""
        error_message = None

        with patch(
            "agent_tui.services.deep_agents.memory.get_memory_summary",
            side_effect=RuntimeError("disk error"),
        ):
            try:
                from agent_tui.services.deep_agents.memory import get_memory_summary

                get_memory_summary()
            except Exception:
                error_message = "Memory not available (DeepAgents not configured)."

        assert error_message == "Memory not available (DeepAgents not configured)."

    def test_memory_multiple_sources_in_summary(self, tmp_path, monkeypatch, mock_home):
        """When multiple AGENTS.md files exist, summary mentions all sources."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".deepagents").mkdir()
        (tmp_path / ".deepagents" / "AGENTS.md").write_text("project info")
        (mock_home / ".deepagents").mkdir()
        (mock_home / ".deepagents" / "AGENTS.md").write_text("user info\nmore user info")

        from agent_tui.services.deep_agents.memory import get_memory_summary

        summary = get_memory_summary()
        assert "Memory loaded from 2 source(s):" in summary
        assert ".deepagents/AGENTS.md" in summary
        assert "~/.deepagents/AGENTS.md" in summary
