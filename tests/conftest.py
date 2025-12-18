"""Pytest configuration and shared fixtures"""

import os
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_codebase(temp_workspace):
    """Create a mock codebase structure for testing."""
    # Create some sample files
    (temp_workspace / "README.md").write_text("# Test Project\n\nThis is a test project.")
    (temp_workspace / "main.py").write_text("def main():\n    pass\n")

    # Create a subdirectory
    src_dir = temp_workspace / "src"
    src_dir.mkdir()
    (src_dir / "utils.py").write_text("def helper():\n    return 42\n")

    # Create a config directory
    config_dir = temp_workspace / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text("debug: true\n")

    return temp_workspace


@pytest.fixture
def config_dir():
    """Return the path to the test config directory."""
    return Path(__file__).parent.parent / "config"


@pytest.fixture
def enable_anthropic():
    """Enable Anthropic API for tests that need it."""
    original = os.environ.get('AGENT_ENGINE_USE_ANTHROPIC')
    os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'
    yield
    if original is None:
        os.environ.pop('AGENT_ENGINE_USE_ANTHROPIC', None)
    else:
        os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = original


@pytest.fixture
def has_anthropic_key():
    """Check if Anthropic API key is available."""
    return bool(os.environ.get('ANTHROPIC_API_KEY'))
