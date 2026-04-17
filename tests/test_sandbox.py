"""Tests for SandboxBackend."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_tui.services.deep_agents.sandbox import SandboxBackend


class TestSandboxBackendInit:
    """Tests for sandbox initialization."""

    def test_default_root_dir(self, tmp_path, monkeypatch):
        """Sandbox defaults to .agent-sandbox in cwd."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        assert backend.root_dir == tmp_path / ".agent-sandbox"
        assert backend.root_dir.exists()

    def test_custom_root_dir(self, tmp_path):
        """Sandbox can use custom root directory."""
        custom_dir = tmp_path / "custom-sandbox"
        backend = SandboxBackend(root_dir=custom_dir)
        assert backend.root_dir == custom_dir
        assert backend.root_dir.exists()

    def test_root_dir_as_string(self, tmp_path):
        """Root dir can be provided as string."""
        custom_dir = tmp_path / "string-sandbox"
        backend = SandboxBackend(root_dir=str(custom_dir))
        assert backend.root_dir == custom_dir
        assert backend.root_dir.exists()

    def test_cleanup_flag_default_true(self, tmp_path, monkeypatch):
        """Cleanup flag defaults to True."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        assert backend.auto_cleanup is True

    def test_cleanup_flag_false(self, tmp_path):
        """Cleanup flag can be set to False."""
        custom_dir = tmp_path / "persist-sandbox"
        backend = SandboxBackend(root_dir=custom_dir, cleanup=False)
        assert backend.auto_cleanup is False


class TestPathResolution:
    """Tests for path security and resolution."""

    def test_resolve_simple_path(self, tmp_path, monkeypatch):
        """Simple paths resolve correctly."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        resolved = backend._resolve_path("test.txt")
        assert resolved == backend.root_dir / "test.txt"

    def test_resolve_absolute_path(self, tmp_path, monkeypatch):
        """Absolute paths are treated as relative to sandbox."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        resolved = backend._resolve_path("/test.txt")
        assert resolved == backend.root_dir / "test.txt"

    def test_resolve_nested_path(self, tmp_path, monkeypatch):
        """Nested paths resolve correctly."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        resolved = backend._resolve_path("dir/subdir/file.txt")
        assert resolved == backend.root_dir / "dir" / "subdir" / "file.txt"

    def test_block_traversal_attack(self, tmp_path, monkeypatch):
        """Path traversal attacks are blocked."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        with pytest.raises(ValueError, match="traversal attack"):
            backend._resolve_path("../outside.txt")

    def test_block_traversal_in_middle(self, tmp_path, monkeypatch):
        """Path traversal in middle of path is blocked."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        with pytest.raises(ValueError, match="traversal attack"):
            backend._resolve_path("dir/../../outside.txt")

    def test_absolute_path_resolved_in_sandbox(self, tmp_path, monkeypatch):
        """Absolute paths are resolved within sandbox root."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        # Absolute path /etc/passwd is treated as relative to sandbox root
        resolved = backend._resolve_path("/etc/passwd")
        assert resolved == backend.root_dir / "etc" / "passwd"

    def test_block_traversal_with_absolute_escape(self, tmp_path, monkeypatch):
        """Absolute path with traversal is blocked."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        # This would try to escape via absolute path with ..
        with pytest.raises(ValueError, match="traversal attack"):
            backend._resolve_path("/../etc/passwd")

    def test_allow_dot_path(self, tmp_path, monkeypatch):
        """Single dot in path is allowed."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        resolved = backend._resolve_path("./test.txt")
        assert resolved == backend.root_dir / "test.txt"

    def test_resolve_normalizes_path(self, tmp_path, monkeypatch):
        """Path normalization works correctly."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        resolved = backend._resolve_path("dir/../test.txt")
        assert resolved == backend.root_dir / "test.txt"


class TestRead:
    """Tests for read operation."""

    def test_read_existing_file(self, tmp_path, monkeypatch):
        """Can read existing file in sandbox."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        test_file = backend.root_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = backend.read("test.txt")

        assert result["error"] is None
        assert result["file_data"] is not None
        assert result["file_data"]["content"] == "Hello, World!"

    def test_read_nonexistent_file(self, tmp_path, monkeypatch):
        """Reading nonexistent file returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.read("nonexistent.txt")

        assert result["error"] is not None
        assert "not found" in result["error"]
        assert result["file_data"] is None

    def test_read_directory(self, tmp_path, monkeypatch):
        """Reading directory returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "subdir").mkdir()

        result = backend.read("subdir")

        assert result["error"] is not None
        assert "not a file" in result["error"]

    def test_read_with_offset(self, tmp_path, monkeypatch):
        """Can read file with offset."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        test_file = backend.root_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = backend.read("test.txt", offset=7)

        assert result["error"] is None
        assert result["file_data"]["content"] == "World!"

    def test_read_with_limit(self, tmp_path, monkeypatch):
        """Can read file with limit."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        test_file = backend.root_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = backend.read("test.txt", limit=5)

        assert result["error"] is None
        assert result["file_data"]["content"] == "Hello"

    def test_read_with_offset_and_limit(self, tmp_path, monkeypatch):
        """Can read file with offset and limit."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        test_file = backend.root_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = backend.read("test.txt", offset=7, limit=5)

        assert result["error"] is None
        assert result["file_data"]["content"] == "World"

    def test_read_traversal_attack_blocked(self, tmp_path, monkeypatch):
        """Read blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.read("../outside.txt")

        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    @pytest.mark.asyncio
    async def test_aread_existing_file(self, tmp_path, monkeypatch):
        """Async read works for existing file."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        test_file = backend.root_dir / "test.txt"
        test_file.write_text("Hello, World!")

        result = await backend.aread("test.txt")

        assert result["error"] is None
        assert result["file_data"]["content"] == "Hello, World!"


class TestWrite:
    """Tests for write operation."""

    def test_write_new_file(self, tmp_path, monkeypatch):
        """Can write new file in sandbox."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.write("test.txt", "Hello, World!")

        assert result["error"] is None
        assert result["path"] == "test.txt"
        assert (backend.root_dir / "test.txt").read_text() == "Hello, World!"

    def test_write_overwrites_existing(self, tmp_path, monkeypatch):
        """Write overwrites existing file."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Old content")

        result = backend.write("test.txt", "New content")

        assert result["error"] is None
        assert (backend.root_dir / "test.txt").read_text() == "New content"

    def test_write_creates_parent_dirs(self, tmp_path, monkeypatch):
        """Write creates parent directories."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.write("dir/subdir/test.txt", "Nested content")

        assert result["error"] is None
        assert (backend.root_dir / "dir" / "subdir" / "test.txt").read_text() == "Nested content"

    def test_write_traversal_attack_blocked(self, tmp_path, monkeypatch):
        """Write blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.write("../outside.txt", "content")

        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    @pytest.mark.asyncio
    async def test_awrite_new_file(self, tmp_path, monkeypatch):
        """Async write works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = await backend.awrite("test.txt", "Hello, World!")

        assert result["error"] is None
        assert (backend.root_dir / "test.txt").read_text() == "Hello, World!"


class TestEdit:
    """Tests for edit operation."""

    def test_edit_single_occurrence(self, tmp_path, monkeypatch):
        """Edit replaces single occurrence."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello, World!")

        result = backend.edit("test.txt", "World", "Universe")

        assert result["error"] is None
        assert result["occurrences"] == 1
        assert (backend.root_dir / "test.txt").read_text() == "Hello, Universe!"

    def test_edit_only_first_occurrence(self, tmp_path, monkeypatch):
        """Edit replaces only first occurrence by default."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World World")

        result = backend.edit("test.txt", "World", "Universe")

        assert result["error"] is None
        assert result["occurrences"] == 1
        assert (backend.root_dir / "test.txt").read_text() == "Hello Universe World"

    def test_edit_all_occurrences(self, tmp_path, monkeypatch):
        """Edit can replace all occurrences."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World World")

        result = backend.edit("test.txt", "World", "Universe", replace_all=True)

        assert result["error"] is None
        assert result["occurrences"] == 2
        assert (backend.root_dir / "test.txt").read_text() == "Hello Universe Universe"

    def test_edit_nonexistent_file(self, tmp_path, monkeypatch):
        """Edit nonexistent file returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.edit("nonexistent.txt", "old", "new")

        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_edit_string_not_found(self, tmp_path, monkeypatch):
        """Edit with non-matching string returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello, World!")

        result = backend.edit("test.txt", "xyz", "new")

        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_edit_traversal_attack_blocked(self, tmp_path, monkeypatch):
        """Edit blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.edit("../outside.txt", "old", "new")

        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    @pytest.mark.asyncio
    async def test_aedit_file(self, tmp_path, monkeypatch):
        """Async edit works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello, World!")

        result = await backend.aedit("test.txt", "World", "Universe")

        assert result["error"] is None
        assert (backend.root_dir / "test.txt").read_text() == "Hello, Universe!"


class TestLs:
    """Tests for ls operation."""

    def test_ls_empty_directory(self, tmp_path, monkeypatch):
        """Ls on empty directory returns empty entries."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.ls(".")

        assert result["error"] is None
        assert result["entries"] == []

    def test_ls_with_files(self, tmp_path, monkeypatch):
        """Ls returns files and directories."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "file1.txt").write_text("content")
        (backend.root_dir / "file2.txt").write_text("content")
        (backend.root_dir / "subdir").mkdir()

        result = backend.ls(".")

        assert result["error"] is None
        assert len(result["entries"]) == 3
        paths = {e["path"] for e in result["entries"]}
        assert "file1.txt" in paths
        assert "file2.txt" in paths
        assert "subdir" in paths

    def test_ls_file_info(self, tmp_path, monkeypatch):
        """Ls returns correct file info."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello, World!")
        (backend.root_dir / "subdir").mkdir()

        result = backend.ls(".")

        assert result["error"] is None
        entries = {e["path"]: e for e in result["entries"]}

        assert entries["test.txt"]["is_dir"] is False
        assert entries["test.txt"]["size"] == 13
        assert entries["subdir"]["is_dir"] is True

    def test_ls_nonexistent_directory(self, tmp_path, monkeypatch):
        """Ls on nonexistent directory returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.ls("nonexistent")

        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_ls_on_file(self, tmp_path, monkeypatch):
        """Ls on file returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = backend.ls("test.txt")

        assert result["error"] is not None
        assert "not a directory" in result["error"]

    def test_ls_traversal_attack_blocked(self, tmp_path, monkeypatch):
        """Ls blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.ls("../outside")

        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    def test_ls_info(self, tmp_path, monkeypatch):
        """ls_info returns list of FileInfo."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = backend.ls_info(".")

        assert len(result) == 1
        assert result[0]["path"] == "test.txt"

    @pytest.mark.asyncio
    async def test_als_directory(self, tmp_path, monkeypatch):
        """Async ls works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = await backend.als(".")

        assert result["error"] is None
        assert len(result["entries"]) == 1


class TestGlob:
    """Tests for glob operation."""

    def test_glob_files(self, tmp_path, monkeypatch):
        """Glob finds matching files."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "file1.txt").write_text("content")
        (backend.root_dir / "file2.txt").write_text("content")
        (backend.root_dir / "script.py").write_text("code")

        result = backend.glob("*.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 2
        paths = {m["path"] for m in result["matches"]}
        assert "file1.txt" in paths
        assert "file2.txt" in paths

    def test_glob_recursive(self, tmp_path, monkeypatch):
        """Glob supports recursive patterns."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "dir1").mkdir()
        (backend.root_dir / "dir2").mkdir()
        (backend.root_dir / "dir1" / "file.txt").write_text("content")
        (backend.root_dir / "dir2" / "file.txt").write_text("content")

        result = backend.glob("**/*.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 2

    def test_glob_no_matches(self, tmp_path, monkeypatch):
        """Glob returns empty list when no matches."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.glob("*.nonexistent")

        assert result["error"] is None
        assert result["matches"] == []

    def test_glob_info(self, tmp_path, monkeypatch):
        """glob_info returns list of FileInfo."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = backend.glob_info("*.txt")

        assert len(result) == 1
        assert result[0]["path"] == "test.txt"

    @pytest.mark.asyncio
    async def test_aglob_files(self, tmp_path, monkeypatch):
        """Async glob works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = await backend.aglob("*.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 1


class TestGrep:
    """Tests for grep operation."""

    def test_grep_in_file(self, tmp_path, monkeypatch):
        """Grep finds matches in file."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World\nGoodbye World\n")

        result = backend.grep("World", "test.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 2
        assert result["matches"][0]["line"] == 1
        assert result["matches"][0]["text"] == "Hello World"

    def test_grep_in_directory(self, tmp_path, monkeypatch):
        """Grep searches recursively in directory."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "file1.txt").write_text("Hello World")
        (backend.root_dir / "file2.txt").write_text("Hello Universe")

        result = backend.grep("Hello", ".")

        assert result["error"] is None
        assert len(result["matches"]) == 2

    def test_grep_no_matches(self, tmp_path, monkeypatch):
        """Grep returns empty list when no matches."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World")

        result = backend.grep("xyz", "test.txt")

        assert result["error"] is None
        assert result["matches"] == []

    def test_grep_regex(self, tmp_path, monkeypatch):
        """Grep supports regex patterns."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World 123\nGoodbye 456")

        result = backend.grep(r"\d+", "test.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 2
        assert "123" in result["matches"][0]["text"]
        assert "456" in result["matches"][1]["text"]

    def test_grep_skips_binary(self, tmp_path, monkeypatch):
        """Grep skips binary files."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        # Create a binary file
        (backend.root_dir / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
        (backend.root_dir / "text.txt").write_text("Hello World")

        result = backend.grep("Hello", ".")

        assert result["error"] is None
        assert len(result["matches"]) == 1

    def test_grep_traversal_attack_blocked(self, tmp_path, monkeypatch):
        """Grep blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.grep("pattern", "../outside")

        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    def test_grep_raw(self, tmp_path, monkeypatch):
        """grep_raw returns matches list."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World")

        result = backend.grep_raw("World", "test.txt")

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_agrep_file(self, tmp_path, monkeypatch):
        """Async grep works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello World")

        result = await backend.agrep("World", "test.txt")

        assert result["error"] is None
        assert len(result["matches"]) == 1


class TestExecute:
    """Tests for execute operation."""

    def test_execute_echo(self, tmp_path, monkeypatch):
        """Execute can run echo command."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute('echo "Hello, World!"')

        assert result.exit_code == 0
        assert "Hello, World!" in result.output

    def test_execute_in_sandbox_directory(self, tmp_path, monkeypatch):
        """Execute runs in sandbox directory."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("content")

        result = backend.execute("ls -la")

        assert result.exit_code == 0
        assert "test.txt" in result.output

    def test_execute_with_error(self, tmp_path, monkeypatch):
        """Execute captures error output."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute("cat nonexistent_file_12345")

        assert result.exit_code != 0
        assert "Exit code:" in result.output

    def test_execute_empty_command(self, tmp_path, monkeypatch):
        """Execute handles empty command."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute("")

        assert result.exit_code == 1
        assert "non-empty string" in result.output

    def test_execute_invalid_timeout(self, tmp_path, monkeypatch):
        """Execute handles invalid timeout."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute("echo test", timeout=0)

        assert result.exit_code == 1
        assert "timeout must be positive" in result.output

    def test_execute_timeout(self, tmp_path, monkeypatch):
        """Execute respects timeout."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute("sleep 10", timeout=1)

        assert result.exit_code == 124
        assert "timed out" in result.output

    def test_execute_stderr(self, tmp_path, monkeypatch):
        """Execute captures stderr."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.execute("echo error >&2")

        assert result.exit_code == 0
        assert "[stderr]" in result.output
        assert "error" in result.output

    @pytest.mark.asyncio
    async def test_aexecute_command(self, tmp_path, monkeypatch):
        """Async execute works."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = await backend.aexecute('echo "Hello"')

        assert result.exit_code == 0
        assert "Hello" in result.output


class TestUploadDownload:
    """Tests for upload and download operations."""

    def test_upload_single_file(self, tmp_path, monkeypatch):
        """Can upload single file."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.upload_files([("test.txt", b"Hello, World!")])

        assert len(result) == 1
        assert result[0]["success"] is True
        assert (backend.root_dir / "test.txt").read_bytes() == b"Hello, World!"

    def test_upload_multiple_files(self, tmp_path, monkeypatch):
        """Can upload multiple files."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.upload_files(
            [
                ("file1.txt", b"content1"),
                ("file2.txt", b"content2"),
            ]
        )

        assert len(result) == 2
        assert all(r["success"] for r in result)
        assert (backend.root_dir / "file1.txt").read_bytes() == b"content1"
        assert (backend.root_dir / "file2.txt").read_bytes() == b"content2"

    def test_upload_creates_directories(self, tmp_path, monkeypatch):
        """Upload creates parent directories."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.upload_files([("dir/subdir/file.txt", b"content")])

        assert result[0]["success"] is True
        assert (backend.root_dir / "dir" / "subdir" / "file.txt").read_bytes() == b"content"

    def test_upload_traversal_blocked(self, tmp_path, monkeypatch):
        """Upload blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.upload_files([("../outside.txt", b"content")])

        assert result[0]["success"] is False
        assert "traversal attack" in result[0]["error"]

    def test_download_single_file(self, tmp_path, monkeypatch):
        """Can download single file."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "test.txt").write_text("Hello, World!")

        result = backend.download_files(["test.txt"])

        assert len(result) == 1
        assert result[0]["success"] is True
        assert result[0]["content"] == b"Hello, World!"

    def test_download_nonexistent_file(self, tmp_path, monkeypatch):
        """Download nonexistent file returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.download_files(["nonexistent.txt"])

        assert len(result) == 1
        assert result[0]["success"] is False
        assert "not found" in result[0]["error"]

    def test_download_directory(self, tmp_path, monkeypatch):
        """Download directory returns error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        (backend.root_dir / "subdir").mkdir()

        result = backend.download_files(["subdir"])

        assert result[0]["success"] is False
        assert "not a file" in result[0]["error"]

    def test_download_traversal_blocked(self, tmp_path, monkeypatch):
        """Download blocks path traversal attacks."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.download_files(["../outside.txt"])

        assert result[0]["success"] is False
        assert "traversal attack" in result[0]["error"]


class TestCleanup:
    """Tests for sandbox cleanup."""

    def test_cleanup_removes_directory(self, tmp_path, monkeypatch):
        """Cleanup removes sandbox directory."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend(cleanup=True)
        (backend.root_dir / "test.txt").write_text("content")
        assert backend.root_dir.exists()

        backend.cleanup()

        assert not backend.root_dir.exists()

    def test_no_cleanup_persists_directory(self, tmp_path, monkeypatch):
        """No cleanup keeps sandbox directory."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend(cleanup=False)
        (backend.root_dir / "test.txt").write_text("content")

        backend.cleanup()

        assert backend.root_dir.exists()
        assert (backend.root_dir / "test.txt").exists()

    def test_cleanup_on_nonexistent_dir(self, tmp_path, monkeypatch):
        """Cleanup on nonexistent directory doesn't error."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()
        backend.root_dir.rmdir()
        assert not backend.root_dir.exists()

        backend.cleanup()  # Should not raise


class TestSandboxIsolation:
    """Tests for sandbox isolation guarantees."""

    def test_cannot_read_outside_sandbox(self, tmp_path, monkeypatch):
        """Cannot read files outside sandbox."""
        monkeypatch.chdir(tmp_path)
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("secret")

        backend = SandboxBackend()

        # Attempt to read outside file
        result = backend.read("../outside.txt")
        assert result["error"] is not None
        assert "traversal attack" in result["error"]

    def test_cannot_write_outside_sandbox(self, tmp_path, monkeypatch):
        """Cannot write files outside sandbox."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        result = backend.write("../outside.txt", "content")
        assert result["error"] is not None
        assert "traversal attack" in result["error"]

        # Verify file wasn't created
        assert not (tmp_path / "outside.txt").exists()

    def test_cannot_execute_outside_sandbox(self, tmp_path, monkeypatch):
        """Commands run in sandbox directory, not outside."""
        monkeypatch.chdir(tmp_path)
        outside_file = tmp_path / "outside_marker.txt"
        outside_file.write_text("outside")

        backend = SandboxBackend()

        # Command should not see outside file
        result = backend.execute("ls")
        assert "outside_marker.txt" not in result.output

    def test_symlink_escape_blocked(self, tmp_path, monkeypatch):
        """Symlink escape attempts are contained within resolved path."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        # Create a symlink inside sandbox pointing outside
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("secret")

        symlink_path = backend.root_dir / "escape"
        symlink_path.symlink_to(outside_dir)

        # Attempt to read through symlink
        result = backend.read("escape/secret.txt")
        # Should be blocked because resolved path is outside sandbox
        assert result["error"] is not None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unicode_content(self, tmp_path, monkeypatch):
        """Can handle unicode content."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        unicode_content = "Hello 世界 🌍"
        backend.write("unicode.txt", unicode_content)

        result = backend.read("unicode.txt")
        assert result["file_data"]["content"] == unicode_content

    def test_large_file(self, tmp_path, monkeypatch):
        """Can handle large files."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        large_content = "x" * 100000
        backend.write("large.txt", large_content)

        # Read with high limit to get full content
        result = backend.read("large.txt", limit=200000)
        assert result["file_data"]["content"] == large_content

    def test_special_characters_in_filename(self, tmp_path, monkeypatch):
        """Can handle special characters in filenames."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        backend.write("file with spaces.txt", "content")
        result = backend.read("file with spaces.txt")
        assert result["file_data"]["content"] == "content"

    def test_empty_file(self, tmp_path, monkeypatch):
        """Can handle empty files."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        backend.write("empty.txt", "")
        result = backend.read("empty.txt")
        assert result["file_data"]["content"] == ""

    def test_deeply_nested_path(self, tmp_path, monkeypatch):
        """Can handle deeply nested paths."""
        monkeypatch.chdir(tmp_path)
        backend = SandboxBackend()

        deep_path = "a/b/c/d/e/f/g/h/i/j/file.txt"
        backend.write(deep_path, "deep content")

        result = backend.read(deep_path)
        assert result["file_data"]["content"] == "deep content"
