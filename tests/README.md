# Help Chatbot Test Suite

Comprehensive pytest test suite for the help_chatbot project.

## Test Coverage

### Unit Tests (test_tools.py)
- `TestSearchCodebaseTool` - Tests for the search_codebase_tool function
  - Basic search functionality
  - README extraction
  - Directory filtering (.git, venv, __pycache__)
  - Focus areas parameter
  - Error handling

- `TestFormatResponseTool` - Tests for the format_response_tool function
  - Basic formatting
  - Workspace parameter handling
  - Empty input handling

- `TestToolIntegration` - Integration tests for tools working together
  - Search and format workflow

### Unit Tests (test_main.py)
- `TestGetConfigDir` - Tests for config directory resolution
  - Local config detection
  - Directory existence
  - Required files presence

- `TestGetModelProfile` - Tests for model profile lookup
  - Profile found
  - Profile not found
  - Missing profiles key
  - Empty profiles list

- `TestMainFunction` - Tests for main() CLI function
  - Single-shot query mode
  - Interactive REPL mode
  - Model flag handling
  - Config directory not found
  - Engine error handling

- `TestOutputExtraction` - Tests for output parsing logic
  - Direct final_answer extraction
  - Nested output extraction
  - Result field extraction

### Integration Tests (test_integration.py)
- `TestEngineIntegration` - Engine loading and configuration
  - Loading from config directory
  - Tool registration
  - Workflow node structure

- `TestEngineWithAnthropicAPI` - Tests requiring Anthropic API
  - Full workflow execution
  - Tool execution with LLM
  - (Marked with @pytest.mark.requires_api)

- `TestEngineWithoutAPI` - Tests that work without external APIs
  - Basic engine structure
  - Tool handler loading
  - Fallback behavior without LLM

- `TestOllamaClient` - Custom Ollama client tests
  - Client creation
  - Custom URL configuration
  - Generate method (requires running Ollama)

## Running Tests

### Install Dev Dependencies

```bash
make install-dev
# or
source venv/bin/activate
pip install -e ".[dev]"
```

### Run All Tests

```bash
make test
# or
source venv/bin/activate
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Fast tests (skip slow and API tests)
make test-fast

# Tests with coverage report
make test-cov
```

### Run Individual Test Files

```bash
source venv/bin/activate

# Tool tests
pytest tests/test_tools.py -v

# Main tests
pytest tests/test_main.py -v

# Integration tests
pytest tests/test_integration.py -v
```

### Run Specific Tests

```bash
source venv/bin/activate

# Single test class
pytest tests/test_tools.py::TestSearchCodebaseTool -v

# Single test method
pytest tests/test_tools.py::TestSearchCodebaseTool::test_search_codebase_basic -v
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests for multiple components
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.requires_api` - Tests that require API keys (Anthropic, OpenAI, etc.)

### Running by Marker

```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Exclude API tests
pytest -m "not requires_api"

# Fast tests only (no slow, no API)
pytest -m "not slow and not requires_api"
```

## Test Configuration

### pytest.ini
Main pytest configuration:
- Test discovery patterns
- Test paths
- Output options
- Coverage configuration
- Test markers

### .coveragerc
Coverage configuration:
- Source paths
- Excluded files and patterns
- Report options

### conftest.py
Shared fixtures:
- `temp_workspace` - Temporary directory for tests
- `mock_codebase` - Mock codebase structure with sample files
- `config_dir` - Path to test config directory
- `enable_anthropic` - Enable Anthropic API for tests
- `has_anthropic_key` - Check if Anthropic API key is available

## Coverage Report

After running tests with coverage:

```bash
make test-cov
```

View the HTML report:

```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Current coverage: ~54% overall
- `tools.py`: 85%
- `main.py`: 65%
- `ollama_client.py`: 80%

## CI/CD Integration

The test suite is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest --cov=. --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Structure

```python
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from your_module import your_function


class TestYourFeature:
    """Tests for your feature."""

    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic functionality."""
        result = your_function(input_data)
        assert result == expected_output

    @pytest.mark.integration
    def test_with_dependencies(self, mock_codebase):
        """Test with dependencies."""
        # Use fixtures for setup
        result = your_function(mock_codebase)
        assert "expected" in result
```

### Using Fixtures

```python
def test_with_temp_workspace(self, temp_workspace):
    """Use temporary workspace fixture."""
    test_file = temp_workspace / "test.txt"
    test_file.write_text("content")
    # ... test code

def test_with_mock_codebase(self, mock_codebase):
    """Use pre-populated mock codebase."""
    # mock_codebase already has README.md, main.py, etc.
    assert (mock_codebase / "README.md").exists()
```

### Mocking

```python
from unittest.mock import Mock, patch, MagicMock

@patch('module.external_dependency')
def test_with_mock(self, mock_dependency):
    """Test with mocked dependency."""
    mock_dependency.return_value = "mocked result"
    # ... test code
```

## Troubleshooting

### Tests Not Found

Make sure pytest can import modules:
```bash
# Add parent directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Import Errors

Install the package in editable mode:
```bash
pip install -e .
```

### API Tests Failing

Skip API tests if you don't have keys:
```bash
pytest -m "not requires_api"
```

Or set the API key:
```bash
export ANTHROPIC_API_KEY="your-key"
pytest
```

### Slow Tests Timing Out

Increase timeout or skip slow tests:
```bash
pytest -m "not slow"
```

## Best Practices

1. **Test Isolation** - Each test should be independent
2. **Clear Names** - Test names should describe what they test
3. **Arrange-Act-Assert** - Follow the AAA pattern
4. **Use Fixtures** - Don't repeat setup code
5. **Mock External Dependencies** - Keep tests fast and reliable
6. **Mark Tests Appropriately** - Use markers for categorization
7. **Write Docstrings** - Explain what each test verifies

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [Coverage.py](https://coverage.readthedocs.io/)
