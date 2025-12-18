SHELL := /bin/bash
PYTHON ?= python3
VENV ?= venv
ACTIVATE = . $(VENV)/bin/activate

# Default target
all: install

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)

install: $(VENV)/bin/activate
	$(ACTIVATE) && $(PYTHON) -m pip install --upgrade pip
	$(ACTIVATE) && $(PYTHON) -m pip install -e /home/ndev/agent_engine
	$(ACTIVATE) && $(PYTHON) -m pip install -e .
	@bash -c '\
		VENV_BIN="$$(cd $(VENV)/bin && pwd)"; \
		BASHRC="$$HOME/.bashrc"; \
		ZSHRC="$$HOME/.zshrc"; \
		PROFILE="$$HOME/.bash_profile"; \
		PATTERN="export PATH=\"$$VENV_BIN:\$$PATH\""; \
		for FILE in "$$BASHRC" "$$ZSHRC" "$$PROFILE"; do \
			if [ -f "$$FILE" ]; then \
				if ! grep -q "$$VENV_BIN" "$$FILE"; then \
					echo "" >> "$$FILE"; \
					echo "# Added by ask-chatbot installer" >> "$$FILE"; \
					echo "export PATH=\"$$VENV_BIN:\$$PATH\"" >> "$$FILE"; \
					echo "Added PATH to $$FILE"; \
				fi; \
			fi; \
		done; \
		echo ""; \
		echo "✅ Installation complete!"; \
		echo ""; \
		echo "To activate ask in your current shell, run:"; \
		echo "  export PATH=\"$$VENV_BIN:\$$PATH\""; \
		echo ""; \
		echo "Or restart your terminal and ask will be available globally."; \
		echo ""; \
		echo "Usage:"; \
		echo "  ask \"what is this project\""; \
		echo "  ask \"where is the main file\""; \
	'

uninstall:
	$(ACTIVATE) && $(PYTHON) -m pip uninstall -y ask-chatbot

reinstall: uninstall install

run:
	export AGENT_ENGINE_USE_ANTHROPIC=1 && $(VENV)/bin/ask

dev-run:
	$(ACTIVATE) && export AGENT_ENGINE_USE_ANTHROPIC=1 && $(PYTHON) main.py

query:
	export AGENT_ENGINE_USE_ANTHROPIC=1 && $(VENV)/bin/ask "$(QUERY)"

install-dev:
	@echo "Installing with development dependencies..."
	python3 -m venv venv 2>/dev/null || true
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -e ".[dev]"
	@echo ""
	@echo "Development installation complete!"
	@echo "Run 'source venv/bin/activate' to activate the environment"
	@echo "Then run 'make test' to run the test suite"

test:
	@echo "Running all tests..."
	. venv/bin/activate && pytest -v

test-unit:
	@echo "Running unit tests only..."
	. venv/bin/activate && pytest -v -m unit

test-integration:
	@echo "Running integration tests only..."
	. venv/bin/activate && pytest -v -m integration

test-fast:
	@echo "Running fast tests (skipping slow and API tests)..."
	. venv/bin/activate && pytest -v -m "not slow and not requires_api"

test-cov:
	@echo "Running tests with coverage..."
	. venv/bin/activate && pytest -v --cov=. --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage

.PHONY: all install install-dev uninstall reinstall run dev-run query test test-unit test-integration test-fast test-cov clean