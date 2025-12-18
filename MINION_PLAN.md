# Minion Implementation Plan: CLI Tool Enhancement

## Overview
Transform the help_chatbot into a CLI tool called `ask` with improved agent architecture and model flexibility.

## Task Scope
This plan covers 4 major areas:
1. **CLI Installation Setup** - Make `ask` installable as a global CLI tool
2. **Specialized Agents** - Replace single debug_agent with role-specific agents
3. **Model Selection System** - Support Haiku, GPT-4o-mini, and Ollama models
4. **Working Directory Support** - Make tools work from user's current directory

**Note**: Hardware detection is handled by agent_engine, not this package.

---

## 1. CLI Installation Setup

### Files to Create:
- **`/home/ndev/help_chatbot/setup.py`**
  - Configure as installable Python package
  - Entry point: `ask` command → `main:main` function
  - Package name: `ask-chatbot`
  - Include package data: `config/**/*`, `*.py`
  - Dependency: `agent_engine` (from `/home/ndev/agent_engine`)

### Files to Modify:
- **`/home/ndev/help_chatbot/main.py`**
  - Add CLI argument parsing (argparse)
  - Support modes:
    - `ask "question"` → single-shot query mode
    - `ask` → interactive REPL mode
  - Fix config directory resolution:
    - Use `pkg_resources` or `importlib.resources` to find installed config
    - Fallback to local `./config` for development
  - Single-shot mode: run query, print final_answer, exit

### Expected Behavior:
```bash
# After installation
cd /home/ndev/help_chatbot
pip install -e .

# Usage from any directory
cd ~/my-project
ask "what is this codebase"  # Analyzes ~/my-project
ask                           # Interactive REPL
```

---

## 2. Specialized Agent Architecture

### Files to Modify:
- **`/home/ndev/help_chatbot/config/agents.yaml`**

Replace single `debug_agent` with three specialized agents:

#### Agent: `question_analyzer`
- **Purpose**: Analyze user questions and formulate search strategies
- **LLM**: (dynamically set by profile, default: ollama/qwen2.5:3b)
- **Config**: `temperature: 0.1`, `max_tokens: 1000`
- **Prompt**:
  ```
  You are the Question Analyzer. Your job is to understand the user's request and prepare a search strategy.

  Input: user_input (string)

  Tasks:
  1. Analyze what the user is asking for
  2. Formulate a search query for the codebase
  3. Identify focus areas (e.g., ["README", "config files", "main code"])

  Output JSON:
  {
    "search_query": "<concise search terms>",
    "focus_areas": ["<area1>", "<area2>"],
    "analysis": "<brief explanation of what user wants>"
  }
  ```

#### Agent: `code_searcher`
- **Purpose**: Execute codebase searches using tools
- **LLM**: (dynamically set, default: ollama/qwen2.5:1.5b)
- **Config**: `temperature: 0.0`, `max_tokens: 500`
- **Tools**: `["search_codebase"]`
- **Prompt**:
  ```
  You are the Code Searcher. Execute searches and pass results forward.

  Input:
  - search_query (string)
  - focus_areas (array)
  - analysis (string)

  Tasks:
  1. Call search_codebase tool with query and focus_areas
  2. Capture the search results

  Output JSON:
  {
    "search_results": "<tool output>",
    "original_question": "{{user_input}}",
    "analysis_from_prev": "{{analysis}}"
  }
  ```

#### Agent: `response_formatter`
- **Purpose**: Generate final formatted answer
- **LLM**: (dynamically set, default: ollama/qwen2.5:3b)
- **Config**: `temperature: 0.2`, `max_tokens: 2000`
- **Tools**: `["format_response"]`
- **Prompt**:
  ```
  You are the Response Formatter. Create the final user-facing answer.

  Input:
  - original_question (string)
  - analysis_from_prev (string)
  - search_results (string)

  Tasks:
  1. Call format_response tool to structure the answer
  2. Ensure it's clear, helpful, and answers the original question

  Output JSON:
  {
    "final_answer": "<formatted response from tool>"
  }
  ```

### Files to Modify:
- **`/home/ndev/help_chatbot/config/workflow.yaml`**

Update agent references:
- `analyze_question` node: `agent_id: "question_analyzer"`
- `execute_search` node: `agent_id: "code_searcher"`
- `generate_response` node: `agent_id: "response_formatter"`

---

## 3. Model Selection System

### Files to Modify:
- **`/home/ndev/help_chatbot/config/cli_profiles.yaml`**

Replace existing profiles with:

```yaml
profiles:
  - id: ollama
    label: "Ollama (Default)"
    description: "Local Ollama model (qwen2.5:3b)"
    is_default: true
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "ollama/qwen2.5:3b"

  - id: ollama-1b
    label: "Ollama 1.5B"
    description: "Smallest, fastest local model"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "ollama/qwen2.5:1.5b"

  - id: ollama-3b
    label: "Ollama 3B"
    description: "Balanced local model"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "ollama/qwen2.5:3b"

  - id: ollama-7b
    label: "Ollama 7B"
    description: "Best quality local model (requires 16GB+ RAM)"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "ollama/qwen2.5:7b"

  - id: ollama-14b
    label: "Ollama 14B"
    description: "Highest quality local model (requires 32GB+ RAM)"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "ollama/qwen2.5:14b"

  - id: haiku
    label: "Claude Haiku"
    description: "Fast cloud model from Anthropic"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "anthropic/claude-3-5-haiku"

  - id: gpt-mini
    label: "GPT-4o Mini"
    description: "Fast cloud model from OpenAI"
    input_mappings:
      default:
        user_input: "{{user_text}}"
        dynamic_params:
          llm: "openai/gpt-4o-mini"
```

### Files to Modify:
- **`/home/ndev/help_chatbot/main.py`**

Add environment variable and CLI flag support:
- Check `ASK_MODEL` environment variable
- Add `--model` CLI flag
- Priority: CLI flag > env var > default profile
- Pass selected model to engine via profile selection or dynamic override

Example:
```bash
ask "what is this"  # Uses default ollama profile
ASK_MODEL=haiku ask "what is this"  # Uses Haiku
ask --model gpt-mini "what is this"  # Uses GPT-4o-mini
```

---

## 4. Working Directory Support

### Files to Modify:
- **`/home/ndev/help_chatbot/tools.py`**

Update `search_codebase_tool`:
- **Current behavior**: Searches relative to script location
- **New behavior**: Search relative to `os.getcwd()` (user's working directory)
- Change `glob.glob("**/*", recursive=True)` to use absolute path of cwd
- Update file reading to work from cwd

Example fix:
```python
def search_codebase_tool(query: str, focus_areas: List[str] = None) -> str:
    """Search the codebase in the user's current working directory."""
    cwd = os.getcwd()
    print(f"DEBUG: Searching {cwd} for query: '{query}'")

    # Search from cwd, not script location
    all_files = glob.glob(os.path.join(cwd, "**/*"), recursive=True)
    # ... rest of logic
```

---

## Implementation Constraints

1. **DO NOT** modify these files:
   - `/home/ndev/help_chatbot/tools.py` → format_response_tool (keep as-is)
   - `/home/ndev/help_chatbot/config/tools.yaml` (keep existing tools)
   - `/home/ndev/help_chatbot/config/schemas/workflow_schemas.yaml` (schemas stay the same)

2. **DO** preserve existing functionality:
   - REPL mode must still work
   - Tool calling mechanism must remain compatible
   - Schema validation must pass

3. **Testing requirements**:
   - After changes, verify:
     ```bash
     cd /home/ndev/help_chatbot
     pip install -e .
     cd /tmp
     mkdir test-workspace && cd test-workspace
     echo "# Test Project" > README.md
     ask "what is this workspace"  # Should analyze /tmp/test-workspace
     ```

---

## Expected Output Format

For each file modified/created, provide:

1. **Full file path**
2. **Complete new contents** (not diffs)
3. **Brief explanation** of changes made

Example:
```
### File: /home/ndev/help_chatbot/setup.py
```python
# setup.py content here
```

**Changes**: Created setup.py to enable pip installation of `ask` CLI tool.
```

---

## Validation Checklist

After implementation, verify:
- [ ] `pip install -e .` succeeds without errors
- [ ] `which ask` shows the installed command
- [ ] `ask "test"` runs in single-shot mode from any directory
- [ ] `ask` starts interactive REPL
- [ ] Tools search the current working directory (not install location)
- [ ] `--model` flag overrides default model
- [ ] All three specialized agents are defined
- [ ] Workflow connects to correct agent IDs

---

## Notes for Minion

- Use full file contents (not diffs) for all changes
- Preserve YAML indentation (2 spaces)
- Test that agent_engine can parse all config files
- Ensure no syntax errors in YAML or Python
- Keep existing debug output in tools for troubleshooting
