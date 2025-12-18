# Pytest Quick Reference

## Install & Setup

```bash
# Install dev dependencies
make install-dev

# Or manually
source venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Skip slow and API tests
make test-fast

# With coverage report
make test-cov
```

## Pytest Commands

```bash
source venv/bin/activate

# Run all tests
pytest

# Verbose output
pytest -v

# Run specific file
pytest tests/test_tools.py

# Run specific class
pytest tests/test_tools.py::TestSearchCodebaseTool

# Run specific test
pytest tests/test_tools.py::TestSearchCodebaseTool::test_search_codebase_basic

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"
pytest -m "not requires_api"

# Show output (disable capture)
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Show coverage
pytest --cov=.

# Generate HTML coverage report
pytest --cov=. --cov-report=html
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.requires_api` - Needs API keys

## Fixtures

```python
def test_example(temp_workspace):
    """Use temporary directory"""

def test_example(mock_codebase):
    """Use pre-populated codebase"""

def test_example(config_dir):
    """Use project config directory"""
```

## Test Structure

```python
import pytest

class TestMyFeature:
    @pytest.mark.unit
    def test_basic(self):
        assert True

    @pytest.mark.integration
    def test_with_deps(self, mock_codebase):
        assert mock_codebase.exists()
```

## Current Stats

- **37 tests** total
- **100% pass rate**
- **54% coverage**
- **~15 seconds** runtime

## Files

- `pytest.ini` - Configuration
- `.coveragerc` - Coverage config
- `tests/conftest.py` - Fixtures
- `tests/test_tools.py` - Tool tests
- `tests/test_main.py` - CLI tests
- `tests/test_integration.py` - Integration tests
- `tests/README.md` - Full documentation

## Coverage Report

```bash
make test-cov
open htmlcov/index.html
```
