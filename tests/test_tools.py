"""Unit tests for tools.py"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path so we can import tools
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import search_codebase_tool, format_response_tool


class TestSearchCodebaseTool:
    """Tests for search_codebase_tool function."""

    @pytest.mark.unit
    def test_search_codebase_basic(self, mock_codebase):
        """Test basic codebase search functionality."""
        result = search_codebase_tool(
            query="test",
            workspace_root=str(mock_codebase)
        )

        assert "**Project File Listing:**" in result
        assert "**README:**" in result
        assert "README.md" in result
        assert "main.py" in result

    @pytest.mark.unit
    def test_search_codebase_finds_readme(self, mock_codebase):
        """Test that README content is extracted."""
        result = search_codebase_tool(
            query="project",
            workspace_root=str(mock_codebase)
        )

        assert "Test Project" in result
        assert "This is a test project" in result

    @pytest.mark.unit
    def test_search_codebase_excludes_common_dirs(self, mock_codebase):
        """Test that .git, venv, and __pycache__ are excluded."""
        # Create directories that should be excluded
        (mock_codebase / ".git").mkdir()
        (mock_codebase / ".git" / "config").write_text("git config")
        (mock_codebase / "venv").mkdir()
        (mock_codebase / "venv" / "lib").mkdir()
        (mock_codebase / "__pycache__").mkdir()

        result = search_codebase_tool(
            query="test",
            workspace_root=str(mock_codebase)
        )

        # These directories should NOT appear in the results
        assert ".git" not in result
        assert "venv" not in result
        assert "__pycache__" not in result

    @pytest.mark.unit
    def test_search_codebase_no_readme(self, temp_workspace):
        """Test behavior when no README exists."""
        # Create a workspace without README
        (temp_workspace / "file.py").write_text("print('hello')")

        result = search_codebase_tool(
            query="test",
            workspace_root=str(temp_workspace)
        )

        assert "**Project File Listing:**" in result
        assert "No README file found" in result

    @pytest.mark.unit
    def test_search_codebase_with_focus_areas(self, mock_codebase):
        """Test search with focus_areas parameter."""
        result = search_codebase_tool(
            query="config",
            focus_areas=["config", "settings"],
            workspace_root=str(mock_codebase)
        )

        assert "**Project File Listing:**" in result
        # Should find config directory
        assert "config" in result

    @pytest.mark.unit
    def test_search_codebase_error_handling(self):
        """Test error handling with invalid workspace."""
        # Note: glob doesn't error on nonexistent paths, just returns empty list
        # So we test that it still returns a valid response structure
        result = search_codebase_tool(
            query="test",
            workspace_root="/nonexistent/path"
        )

        # Should still have the expected structure, just with empty results
        assert "**Project File Listing:**" in result
        assert "**README:**" in result


class TestFormatResponseTool:
    """Tests for format_response_tool function."""

    @pytest.mark.unit
    def test_format_response_basic(self):
        """Test basic response formatting."""
        result = format_response_tool(
            original_question="What is this?",
            analysis="This is a test project",
            code_snippets="def main():\n    pass"
        )

        assert "## Your Question:" in result
        assert "What is this?" in result
        assert "## Agent Analysis:" in result
        assert "This is a test project" in result
        assert "## Relevant Code/Information:" in result
        assert "def main():" in result

    @pytest.mark.unit
    def test_format_response_with_workspace(self, mock_codebase):
        """Test formatting with workspace_root parameter."""
        result = format_response_tool(
            original_question="Where are the files?",
            analysis="Files found in workspace",
            code_snippets="file1.py, file2.py",
            workspace_root=str(mock_codebase)
        )

        assert "Where are the files?" in result
        assert "Files found in workspace" in result
        assert "file1.py" in result

    @pytest.mark.unit
    def test_format_response_empty_inputs(self):
        """Test formatting with empty inputs."""
        result = format_response_tool(
            original_question="",
            analysis="",
            code_snippets=""
        )

        # Should still have headers
        assert "## Your Question:" in result
        assert "## Agent Analysis:" in result
        assert "## Relevant Code/Information:" in result


class TestToolIntegration:
    """Integration tests for tools working together."""

    @pytest.mark.integration
    def test_search_and_format_workflow(self, mock_codebase):
        """Test typical workflow: search then format."""
        # First, search the codebase
        search_result = search_codebase_tool(
            query="project structure",
            workspace_root=str(mock_codebase)
        )

        # Then format the response
        formatted = format_response_tool(
            original_question="What is the project structure?",
            analysis="Found project files and README",
            code_snippets=search_result
        )

        assert "What is the project structure?" in formatted
        assert "Test Project" in formatted
        assert "README.md" in formatted
        assert "main.py" in formatted
