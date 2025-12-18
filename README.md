# Ask - AI-Powered Codebase Assistant

A CLI tool that helps you understand and navigate codebases using AI agents powered by agent_engine.

## Installation

```bash
cd /home/ndev/help_chatbot
make install
```

This will:
- Create a Python virtual environment
- Install the `ask` command globally (within the venv)
- Automatically add `ask` to your PATH in `~/.bashrc`, `~/.zshrc`, etc.
- Set up all dependencies

**After installation**, reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc depending on your shell
```

Now `ask` is available anywhere without needing to activate the venv!

## Usage

### Single-Shot Queries

Ask a question about any codebase from anywhere:

```bash
# From any project directory
cd ~/my-project
ask "what is this project about"
ask "what files are in this directory"
ask "where is the main entry point"
```

### Using Make

From the help_chatbot directory:

```bash
make run                      # Start interactive REPL
make query QUERY="your question"  # Run single query
```

### Interactive REPL Mode

```bash
ask
# Then type your questions at the prompt
```

## How It Works

1. **Question Analysis**: The AI agent analyzes your question
2. **Codebase Search**: Searches the current directory for relevant files and documentation
3. **Answer Generation**: Provides a clear answer based on what it finds

## Current Features

- ✅ Works from any directory (analyzes your current working directory)
- ✅ CLI installation via `pip install -e .`
- ✅ Single-shot query mode
- ✅ Interactive REPL mode
- ✅ File search and README parsing
- ✅ Anthropic Claude Haiku integration

## Model Support

Currently supported:
- **Anthropic Claude** (Haiku, Sonnet) - Default

### Using Different Models

Set the `ASK_MODEL` environment variable or use the `--model` flag:

```bash
ASK_MODEL=sonnet ask "what is this project"
ask --model sonnet "what is this project"
```

Available profiles:
- `haiku` - Claude 3.5 Haiku (default, fastest)
- `sonnet` - Claude 3.5 Sonnet (more capable)
- `gpt-mini` - GPT-4o Mini (requires OpenAI API key)

**Note**: Ollama support is planned but not yet available in agent_engine v1.

## Configuration

The system uses YAML configuration files in `config/`:

- `agents.yaml` - Agent definitions and prompts
- `workflow.yaml` - Workflow structure
- `tools.yaml` - Available tools
- `cli_profiles.yaml` - Model profiles
- `provider_credentials.yaml` - API credentials

## Requirements

- Python 3.8+
- ANTHROPIC_API_KEY environment variable set
- agent_engine (installed automatically from `/home/ndev/agent_engine`)

## Development

### Project Structure

```
help_chatbot/
├── main.py              # CLI entry point
├── tools.py             # Codebase search tools
├── setup.py             # Package configuration
├── Makefile             # Build and run commands
├── config/              # Agent engine configuration
│   ├── agents.yaml      # Agent definitions
│   ├── workflow.yaml    # Workflow structure
│   ├── tools.yaml       # Tool definitions
│   └── ...
└── docs/                # Documentation
```

### Make Commands

```bash
make install      # Install the package
make run          # Start interactive REPL
make ask QUERY="..." # Run single query
make reinstall    # Reinstall after config changes
make clean        # Clean build artifacts
```

## Troubleshooting

### "ask: command not found"

Make sure you completed the installation and reloaded your shell:

```bash
cd /home/ndev/help_chatbot
make install
source ~/.bashrc  # or ~/.zshrc
```

If that doesn't work, you can use the direct path:
```bash
/home/ndev/help_chatbot/venv/bin/ask "your question"
```

Or use the Makefile targets which don't require PATH setup:
```bash
cd /home/ndev/help_chatbot
make query QUERY="your question"
```

### API Key Issues

Ensure your Anthropic API key is set:

```bash
export ANTHROPIC_API_KEY="your-key-here"
export AGENT_ENGINE_USE_ANTHROPIC=1
```

The Makefile sets `AGENT_ENGINE_USE_ANTHROPIC=1` automatically.

### No Answers Returned

The agent may need better prompting. The system is designed to:
1. Call the `search_codebase` tool to find files
2. Analyze the results
3. Generate an answer

If you're not getting answers, check the raw output for debugging info.

## Future Enhancements

- [ ] Ollama local model support (waiting for agent_engine support)
- [ ] Better multi-agent workflows
- [ ] More sophisticated code search (grep, AST parsing)
- [ ] Code explanations and examples
- [ ] Git history analysis
- [ ] Dependency tree visualization

## License

MIT
