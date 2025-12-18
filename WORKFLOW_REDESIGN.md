# Workflow Redesign Proposal

## Current Problems

1. **No Result Summarization**: Tools execute but results aren't summarized into natural language
2. **No Search Strategy**: Treats all questions the same way
3. **Raw Output**: Users see file listings instead of answers like "This workspace contains agent_engine..."

## Proposed Solution: Multi-Stage Workflow

### Stage 1: Question Analysis (Decision Node)
**Purpose**: Route questions to appropriate search strategy

**Routes**:
- `project_overview` → Search README, docs, overview files first
- `code_specific` → Search code files, functions, classes
- `structure` → Focus on directory layout and organization
- `dependencies` → Search package files, requirements

**Example Classifications**:
- "what is this codebase" → project_overview
- "how does X function work" → code_specific
- "what's the folder structure" → structure

### Stage 2: Search Execution (Agent + Tools)
**Purpose**: Execute targeted search based on question type

**Different strategies per route**:
- **project_overview**: Search README.md, docs/*.md files ONLY (no code files)
- **code_specific**: Search .py/.js files, focus on specific files
- **structure**: Get directory tree, main folders only
- **dependencies**: package.json, requirements.txt, setup.py

### Stage 3: Answer Synthesis (Agent, No Tools)
**Purpose**: Read tool results and generate natural language answer

**Input**: Search results from Stage 2 (file listings, README content, etc.)
**Output**: Natural language answer like:
> "This workspace contains the agent_engine framework, which is a Python-based system for building AI agents. The main components are..."

## Benefits

1. ✅ Users get actual answers, not raw file dumps
2. ✅ Faster searches (docs-first for overview questions)
3. ✅ Better context understanding (decision node knows intent)
4. ✅ Cleaner output (summarized, not overwhelming)

## Implementation

Update `config/workflow.yaml` with:
```yaml
nodes:
  - start
  - classify_question (decision node)
  - search_overview (agent + tools, for README/docs)
  - search_code (agent + tools, for code files)
  - synthesize_answer (agent, no tools, summarizes results)
  - exit

edges:
  start → classify_question
  classify_question → search_overview (if project_overview)
  classify_question → search_code (if code_specific)
  search_overview → synthesize_answer
  search_code → synthesize_answer
  synthesize_answer → exit
```
