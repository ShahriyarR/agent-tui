"""Skills module for agent-tui.

Public API:
- ExtendedSkillMetadata: Extended skill metadata with source tracking
- list_skills: Discover skills from filesystem directories
- load_skill_content: Read raw SKILL.md content
- discover_skills_and_roots: High-level discovery + root resolution
- build_skill_invocation_envelope: Build prompt envelope for a skill
"""

from agent_tui.services.skills.invocation import (
    SkillInvocationEnvelope,
    build_skill_invocation_envelope,
    discover_skills_and_roots,
)
from agent_tui.services.skills.load import ExtendedSkillMetadata, list_skills, load_skill_content

__all__ = [
    "ExtendedSkillMetadata",
    "SkillInvocationEnvelope",
    "build_skill_invocation_envelope",
    "discover_skills_and_roots",
    "list_skills",
    "load_skill_content",
]
