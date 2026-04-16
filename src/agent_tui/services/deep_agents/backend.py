"""DeepAgents backend configuration.

This module configures the LocalShellBackend that provides:
- File operations (read, write, edit, glob, grep, ls) via FilesystemBackend inheritance
- Shell execution (execute tool) via LocalShellBackend

Both are rooted at the current working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from deepagents.backends import LocalShellBackend


def create_backend(
    root_dir: Path | None = None,
    inherit_env: bool = True,
) -> LocalShellBackend:
    """Create a backend for DeepAgents with file and shell support.

    LocalShellBackend extends FilesystemBackend, so it provides both
    file operations and shell command execution. Both are rooted at
    the current working directory.

    Args:
        root_dir: Root directory for file operations and shell execution.
            Defaults to current working directory.
        inherit_env: Whether shell commands inherit the current environment.
            Defaults to True.

    Returns:
        Configured LocalShellBackend instance.

    Example:
        >>> backend = create_backend()
        >>> # File operations resolve to cwd
        >>> # Shell commands execute in cwd
    """
    root_dir = root_dir or Path.cwd()

    # LocalShellBackend provides both:
    # - File operations (from FilesystemBackend parent class)
    # - Shell execution (execute tool)
    # Commands run in root_dir with inherited environment
    shell_env = os.environ.copy() if inherit_env else {}

    return LocalShellBackend(
        root_dir=root_dir,
        virtual_mode=True,  # Treat root_dir as virtual root - /file.txt maps to cwd/file.txt
        inherit_env=inherit_env,
        env=shell_env,
    )
