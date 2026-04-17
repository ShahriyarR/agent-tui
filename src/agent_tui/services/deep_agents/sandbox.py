"""Sandbox backend for isolated agent execution.

Provides sandboxed file and shell operations.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from deepagents.backends.protocol import (
    BackendProtocol,
    EditResult,
    ExecuteResponse,
    FileData,
    FileInfo,
    GlobResult,
    GrepMatch,
    GrepResult,
    LsResult,
    ReadResult,
    SandboxBackendProtocol,
    WriteResult,
)

logger = logging.getLogger(__name__)


class SandboxBackend(SandboxBackendProtocol):
    """Backend that executes operations in isolated sandbox.

    All file and shell operations are contained within the sandbox,
    preventing access to the host system outside the sandbox root.
    """

    def __init__(
        self,
        root_dir: Path | str | None = None,
        cleanup: bool = True,
        max_output_bytes: int = 100000,
        default_timeout: int = 60,
    ) -> None:
        """Initialize sandbox backend.

        Args:
            root_dir: Sandbox root directory. Defaults to .agent-sandbox in cwd.
            cleanup: Whether to clean up sandbox on destruction.
            max_output_bytes: Maximum bytes to capture from command output.
            default_timeout: Default timeout in seconds for shell commands.
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd() / ".agent-sandbox"
        self._should_cleanup = cleanup
        self._max_output_bytes = max_output_bytes
        self._default_timeout = default_timeout
        self._ensure_sandbox()

    @property
    def auto_cleanup(self) -> bool:
        """Whether sandbox will be cleaned up on destruction."""
        return self._should_cleanup

    def _ensure_sandbox(self) -> None:
        """Create sandbox directory if it doesn't exist."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Sandbox initialized at %s", self.root_dir)

    def _resolve_path(self, path: str) -> Path:
        """Resolve path within sandbox, blocking traversal attacks.

        Args:
            path: User-provided path (may contain .. or be absolute)

        Returns:
            Resolved Path within sandbox

        Raises:
            ValueError: If path attempts directory traversal outside sandbox
        """
        # Handle absolute paths by stripping leading /
        if path.startswith("/"):
            path = path[1:]

        # Resolve relative to sandbox root
        target = (self.root_dir / path).resolve()

        # Security check: ensure resolved path is within sandbox
        try:
            target.relative_to(self.root_dir.resolve())
        except ValueError as e:
            raise ValueError(f"Path '{path}' attempts to escape sandbox (detected traversal attack)") from e

        return target

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        """Read file from sandbox.

        Args:
            file_path: Path to file within sandbox
            offset: Starting position in file
            limit: Maximum bytes to read

        Returns:
            ReadResult with file data or error
        """
        try:
            target = self._resolve_path(file_path)

            if not target.exists():
                return {"error": f"File '{file_path}' not found in sandbox", "file_data": None}

            if not target.is_file():
                return {"error": f"'{file_path}' is not a file", "file_data": None}

            content = target.read_text(encoding="utf-8")

            # Apply offset and limit
            if offset:
                content = content[offset:]
            if limit:
                content = content[:limit]

            file_data: FileData = {
                "content": content,
                "encoding": "utf-8",
            }

            return {
                "error": None,
                "file_data": file_data,
            }
        except ValueError as e:
            return {"error": str(e), "file_data": None}
        except Exception as e:
            logger.exception("Sandbox read error")
            return {"error": f"Failed to read '{file_path}': {e!s}", "file_data": None}

    async def aread(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        """Async read file from sandbox."""
        return self.read(file_path, offset, limit)

    def write(
        self,
        file_path: str,
        content: str,
    ) -> WriteResult:
        """Write file to sandbox.

        Args:
            file_path: Path to file within sandbox
            content: Content to write

        Returns:
            WriteResult with success info or error
        """
        try:
            target = self._resolve_path(file_path)

            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)

            target.write_text(content, encoding="utf-8")

            return {
                "error": None,
                "path": file_path,
                "files_update": None,
            }
        except ValueError as e:
            return {"error": str(e), "path": None, "files_update": None}
        except Exception as e:
            logger.exception("Sandbox write error")
            return {"error": f"Failed to write '{file_path}': {e!s}", "path": None, "files_update": None}

    async def awrite(
        self,
        file_path: str,
        content: str,
    ) -> WriteResult:
        """Async write file to sandbox."""
        return self.write(file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit file in sandbox.

        Args:
            file_path: Path to file within sandbox
            old_string: String to replace
            new_string: Replacement string
            replace_all: Whether to replace all occurrences

        Returns:
            EditResult with success info or error
        """
        try:
            target = self._resolve_path(file_path)

            if not target.exists():
                return {
                    "error": f"File '{file_path}' not found",
                    "path": None,
                    "files_update": None,
                    "occurrences": None,
                }

            content = target.read_text(encoding="utf-8")

            if old_string not in content:
                return {
                    "error": f"Old string not found in '{file_path}'",
                    "path": None,
                    "files_update": None,
                    "occurrences": None,
                }

            if replace_all:
                new_content = content.replace(old_string, new_string)
                occurrences = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                occurrences = 1

            target.write_text(new_content, encoding="utf-8")

            return {
                "error": None,
                "path": file_path,
                "files_update": None,
                "occurrences": occurrences,
            }
        except ValueError as e:
            return {"error": str(e), "path": None, "files_update": None, "occurrences": None}
        except Exception as e:
            logger.exception("Sandbox edit error")
            return {
                "error": f"Failed to edit '{file_path}': {e!s}",
                "path": None,
                "files_update": None,
                "occurrences": None,
            }

    async def aedit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Async edit file in sandbox."""
        return self.edit(file_path, old_string, new_string, replace_all)

    def ls(
        self,
        path: str,
    ) -> LsResult:
        """List directory in sandbox.

        Args:
            path: Directory path within sandbox

        Returns:
            LsResult with entries or error
        """
        try:
            target = self._resolve_path(path)

            if not target.exists():
                return {"error": f"Directory '{path}' not found", "entries": None}

            if not target.is_dir():
                return {"error": f"'{path}' is not a directory", "entries": None}

            entries: list[FileInfo] = []
            for entry in target.iterdir():
                stat = entry.stat()
                file_info: FileInfo = {
                    "path": str(entry.relative_to(self.root_dir)),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else None,
                }
                entries.append(file_info)

            return {
                "error": None,
                "entries": entries,
            }
        except ValueError as e:
            return {"error": str(e), "entries": None}
        except Exception as e:
            logger.exception("Sandbox ls error")
            return {"error": f"Failed to list '{path}': {e!s}", "entries": None}

    async def als(
        self,
        path: str,
    ) -> LsResult:
        """Async list directory in sandbox."""
        return self.ls(path)

    def ls_info(
        self,
        path: str,
    ) -> list[FileInfo]:
        """List directory and return FileInfo list."""
        result = self.ls(path)
        if result.get("error") or result.get("entries") is None:
            return []
        return result["entries"]

    async def als_info(
        self,
        path: str,
    ) -> list[FileInfo]:
        """Async list directory and return FileInfo list."""
        return self.ls_info(path)

    def glob(
        self,
        pattern: str,
        path: str = "/",
    ) -> GlobResult:
        """Search files in sandbox using glob pattern.

        Args:
            pattern: Glob pattern to match
            path: Base path within sandbox

        Returns:
            GlobResult with matches or error
        """
        try:
            # Resolve base path
            base_path = self._resolve_path(path)

            if not base_path.exists():
                return {"error": f"Path '{path}' not found", "matches": None}

            # Search for matches
            matches: list[FileInfo] = []
            for match in base_path.glob(pattern):
                if match.is_file():
                    stat = match.stat()
                    file_info: FileInfo = {
                        "path": str(match.relative_to(self.root_dir)),
                        "is_dir": False,
                        "size": stat.st_size,
                    }
                    matches.append(file_info)

            return {
                "error": None,
                "matches": matches,
            }
        except ValueError as e:
            return {"error": str(e), "matches": None}
        except Exception as e:
            logger.exception("Sandbox glob error")
            return {"error": f"Failed to glob '{pattern}': {e!s}", "matches": None}

    async def aglob(
        self,
        pattern: str,
        path: str = "/",
    ) -> GlobResult:
        """Async search files in sandbox using glob pattern."""
        return self.glob(pattern, path)

    def glob_info(
        self,
        pattern: str,
        path: str = "/",
    ) -> list[FileInfo]:
        """Search files and return FileInfo list."""
        result = self.glob(pattern, path)
        if result.get("error") or result.get("matches") is None:
            return []
        return result["matches"]

    async def aglob_info(
        self,
        pattern: str,
        path: str = "/",
    ) -> list[FileInfo]:
        """Async search files and return FileInfo list."""
        return self.glob_info(pattern, path)

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        """Search content in sandbox files.

        Args:
            pattern: Regex pattern to search for
            path: File or directory path within sandbox
            glob: Optional glob pattern to filter files

        Returns:
            GrepResult with matches or error
        """
        import re

        try:
            if path is None:
                path = "/"

            target = self._resolve_path(path)

            if not target.exists():
                return {"error": f"Path '{path}' not found", "matches": None}

            matches: list[GrepMatch] = []

            if target.is_file():
                files_to_search = [target]
            else:
                # Search all files in directory recursively
                if glob:
                    files_to_search = [f for f in target.rglob(glob) if f.is_file()]
                else:
                    files_to_search = [f for f in target.rglob("*") if f.is_file()]

            for file_path in files_to_search:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for i, line in enumerate(content.split("\n"), 1):
                        if re.search(pattern, line):
                            rel_path = file_path.relative_to(self.root_dir)
                            match: GrepMatch = {
                                "path": str(rel_path),
                                "line": i,
                                "text": line.strip(),
                            }
                            matches.append(match)
                except (UnicodeDecodeError, IOError):
                    # Skip binary or unreadable files
                    continue

            return {
                "error": None,
                "matches": matches,
            }
        except ValueError as e:
            return {"error": str(e), "matches": None}
        except Exception as e:
            logger.exception("Sandbox grep error")
            return {"error": f"Failed to grep '{pattern}': {e!s}", "matches": None}

    async def agrep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        """Async search content in sandbox files."""
        return self.grep(pattern, path, glob)

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """Search content and return raw matches or error string."""
        result = self.grep(pattern, path, glob)
        if result.get("error"):
            return result["error"]
        return result.get("matches") or []

    async def agrep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """Async search content and return raw matches or error string."""
        return self.grep_raw(pattern, path, glob)

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute command in sandbox environment.

        Args:
            command: Shell command to execute
            timeout: Maximum time in seconds

        Returns:
            ExecuteResponse with output and exit code
        """
        if not command or not isinstance(command, str):
            return ExecuteResponse(
                output="Error: Command must be a non-empty string.",
                exit_code=1,
                truncated=False,
            )

        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            return ExecuteResponse(
                output=f"Error: timeout must be positive, got {effective_timeout}",
                exit_code=1,
                truncated=False,
            )

        try:
            # Run command with sandbox as working directory
            result = subprocess.run(
                command,
                check=False,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=str(self.root_dir),
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
            )

            # Combine stdout and stderr
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                stderr_lines = result.stderr.strip().split("\n")
                output_parts.extend(f"[stderr] {line}" for line in stderr_lines)

            output = "\n".join(output_parts) if output_parts else "<no output>"

            # Check for truncation
            truncated = False
            if len(output) > self._max_output_bytes:
                output = output[: self._max_output_bytes]
                output += f"\n\n... Output truncated at {self._max_output_bytes} bytes."
                truncated = True

            # Add exit code info if non-zero
            if result.returncode != 0:
                output = f"{output.rstrip()}\n\nExit code: {result.returncode}"

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
                truncated=truncated,
            )
        except subprocess.TimeoutExpired:
            msg = f"Error: Command timed out after {effective_timeout} seconds."
            return ExecuteResponse(
                output=msg,
                exit_code=124,
                truncated=False,
            )
        except Exception as e:
            logger.exception("Sandbox execute error")
            return ExecuteResponse(
                output=f"Error executing command ({type(e).__name__}): {e}",
                exit_code=1,
                truncated=False,
            )

    async def aexecute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Async execute command in sandbox environment."""
        return self.execute(command, timeout=timeout)

    def upload_files(
        self,
        files: list[tuple[str, bytes]],
    ) -> list[dict[str, Any]]:
        """Upload files to sandbox.

        Args:
            files: List of (path, content) tuples

        Returns:
            List of upload results
        """
        results = []
        for file_path, content in files:
            try:
                target = self._resolve_path(file_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                results.append(
                    {
                        "path": file_path,
                        "success": True,
                        "error": None,
                    }
                )
            except ValueError as e:
                results.append(
                    {
                        "path": file_path,
                        "success": False,
                        "error": str(e),
                    }
                )
            except Exception as e:
                logger.exception("Sandbox upload error")
                results.append(
                    {
                        "path": file_path,
                        "success": False,
                        "error": str(e),
                    }
                )
        return results

    async def aupload_files(
        self,
        files: list[tuple[str, bytes]],
    ) -> list[dict[str, Any]]:
        """Async upload files to sandbox."""
        return self.upload_files(files)

    def download_files(
        self,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        """Download files from sandbox.

        Args:
            paths: List of file paths within sandbox

        Returns:
            List of download results with content or error
        """
        results = []
        for file_path in paths:
            try:
                target = self._resolve_path(file_path)
                if not target.exists():
                    results.append(
                        {
                            "path": file_path,
                            "success": False,
                            "error": f"File '{file_path}' not found",
                            "content": None,
                        }
                    )
                elif not target.is_file():
                    results.append(
                        {
                            "path": file_path,
                            "success": False,
                            "error": f"'{file_path}' is not a file",
                            "content": None,
                        }
                    )
                else:
                    content = target.read_bytes()
                    results.append(
                        {
                            "path": file_path,
                            "success": True,
                            "error": None,
                            "content": content,
                        }
                    )
            except ValueError as e:
                results.append(
                    {
                        "path": file_path,
                        "success": False,
                        "error": str(e),
                        "content": None,
                    }
                )
            except Exception as e:
                logger.exception("Sandbox download error")
                results.append(
                    {
                        "path": file_path,
                        "success": False,
                        "error": str(e),
                        "content": None,
                    }
                )
        return results

    async def adownload_files(
        self,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        """Async download files from sandbox."""
        return self.download_files(paths)

    def cleanup(self) -> None:
        """Clean up sandbox if configured."""
        if self._should_cleanup and self.root_dir.exists():
            try:
                shutil.rmtree(self.root_dir)
                logger.info("Cleaned up sandbox at %s", self.root_dir)
            except Exception as e:
                logger.warning("Failed to cleanup sandbox: %s", e)

    def __del__(self) -> None:
        """Destructor - attempt cleanup if cleanup wasn't called."""
        if self._should_cleanup and hasattr(self, "root_dir") and self.root_dir.exists():
            try:
                shutil.rmtree(self.root_dir)
            except Exception:
                pass  # Best effort in destructor
