"""Main entry point and CLI for agent-tui (TUI-only)."""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from agent_tui.configurator.version import __version__

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional-tools check (ripgrep, tavily)
# ---------------------------------------------------------------------------

_RIPGREP_URL = "https://github.com/BurntSushi/ripgrep#installation"
"""Fallback installation URL when no platform package manager is detected."""

_SUPPRESS_HINT_TUI = "Use /notifications to manage warnings."
"""Suppression hint for TUI toasts, referencing the in-app settings screen."""


def _ripgrep_install_hint() -> str:
    """Return a platform-specific install command for ripgrep."""
    plat = sys.platform
    if plat == "darwin":
        if shutil.which("brew"):
            return "brew install ripgrep"
        if shutil.which("port"):
            return "sudo port install ripgrep"
    elif plat == "linux":
        if shutil.which("apt-get"):
            return "sudo apt-get install ripgrep"
        if shutil.which("dnf"):
            return "sudo dnf install ripgrep"
        if shutil.which("pacman"):
            return "sudo pacman -S ripgrep"
        if shutil.which("zypper"):
            return "sudo zypper install ripgrep"
        if shutil.which("apk"):
            return "sudo apk add ripgrep"
        if shutil.which("nix-env"):
            return "nix-env -iA nixpkgs.ripgrep"
    elif plat == "win32":
        if shutil.which("choco"):
            return "choco install ripgrep"
        if shutil.which("scoop"):
            return "scoop install ripgrep"
        if shutil.which("winget"):
            return "winget install BurntSushi.ripgrep"
    if shutil.which("cargo"):
        return "cargo install ripgrep"
    if shutil.which("conda"):
        return "conda install -c conda-forge ripgrep"
    return _RIPGREP_URL


def check_optional_tools(*, config_path: Path | None = None) -> list[str]:
    """Check for recommended external tools and return missing tool names.

    Skips tools that the user has suppressed via ``[warnings].suppress`` in
    ``config.toml``.

    Args:
        config_path: Path to config file.  Defaults to
            ``~/.agent-tui/config.toml``.

    Returns:
        List of missing tool names (e.g. ``["ripgrep"]``).
    """
    from agent_tui.configurator.model_config import is_warning_suppressed

    missing: list[str] = []
    if shutil.which("rg") is None and not is_warning_suppressed("ripgrep", config_path):
        missing.append("ripgrep")

    from agent_tui.configurator.settings import settings

    if not settings.has_tavily and not is_warning_suppressed("tavily", config_path):
        missing.append("tavily")

    return missing


def format_tool_warning_tui(tool: str) -> str:
    """Format a missing-tool warning for the TUI toast.

    Args:
        tool: Name of the missing tool.

    Returns:
        Plain-text warning suitable for ``App.notify``.
    """
    if tool == "ripgrep":
        hint = _ripgrep_install_hint()
        return (
            "ripgrep is not installed; the grep tool will use a slower fallback.\n"
            f"\nInstall: {hint}\n\n"
            f"{_SUPPRESS_HINT_TUI}"
        )
    if tool == "tavily":
        return (
            "Web search is disabled \u2014 TAVILY_API_KEY is not set.\n"
            "\nGet a key at https://tavily.com\n\n"
            f"{_SUPPRESS_HINT_TUI}"
        )
    return f"{tool} is not installed."


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Agent TUI - Terminal User Interface for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"agent-tui {__version__}",
    )

    parser.add_argument(
        "--agent",
        choices=["stub", "deepagents"],
        default="stub",
        help="Agent backend to use",
    )

    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web interface instead of TUI",
    )

    return parser.parse_args()


def cli_main() -> None:
    """Entry point for console script."""
    # Fix for gRPC fork issue on macOS
    # https://github.com/grpc/grpc/issues/37642
    if sys.platform == "darwin":
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"

    # Note: LANGSMITH_PROJECT override is handled lazily by config.py's
    # _ensure_bootstrap() (triggered on first access of `settings`).
    # This ensures agent traces use AGENT_TUI_LANGSMITH_PROJECT while
    # shell commands use the user's original LANGSMITH_PROJECT.

    # Fast path: print version without loading heavy dependencies
    if len(sys.argv) == 2 and sys.argv[1] in {"-v", "--version"}:  # noqa: PLR2004
        print(f"agent-tui {__version__}")  # noqa: T201
        sys.exit(0)

    try:
        _args = parse_args()

        # Start web interface if requested
        if _args.web:
            from agent_tui.entrypoints.web import main as web_main

            # Pass agent type to web interface via environment variable
            os.environ['AGENT_TUI_WEB_AGENT'] = _args.agent
            logger.info(f"Starting web interface with {_args.agent} agent")
            web_main()
            return

        # Bootstrap config (triggers _ensure_bootstrap via settings access)
        from agent_tui.configurator.settings import settings  # noqa: F401

        from agent_tui.entrypoints.app import AgentTuiApp

        if _args.agent == "deepagents":
            from agent_tui.services.deep_agents import DeepAgentsAdapter

            agent = DeepAgentsAdapter.from_settings()
        else:
            from agent_tui.services.stub_agent import StubAgent

            agent = StubAgent()

        app = AgentTuiApp(agent=agent)
        app.run()

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C — suppress ugly traceback.
        sys.stderr.write("\n\nInterrupted\n")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
