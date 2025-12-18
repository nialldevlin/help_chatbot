# Changelog: Ask - AI-Powered Codebase Assistant

## 2025-12-18

### Completed Work Consolidated
- **Chatbot Tool Integration**: Fixed `search_codebase` tool availability issue by enabling Anthropic API initialization
  - Configured Claude 3.5 Haiku as default LLM (see STATUS.md)
  - Tools now execute successfully and return results
  - Verified single-shot and interactive REPL modes working

- **Output Display Fix**: Resolved tool results not showing to users
  - Modified main.py to extract tool results from `output['tool_calls']`
  - Single-shot mode now displays search results properly
  - Interactive REPL mode custom-built to format and display results
  - Users now see actual search results instead of planning messages (see FIX_COMPLETE.md)

- **Test Suite Implementation**: Added comprehensive pytest suite
  - Created 37 passing tests covering tools, CLI, and engine integration
  - 54% code coverage (tools.py: 85%, main.py: 65%, ollama_client.py: 80%)
  - All tests green; CI/CD ready with Makefile targets (see PYTEST_SETUP.md)

- **Documentation**: Created detailed implementation guides
  - README_TESTING.md: Testing documentation
  - OUTPUT_FIX.md: Technical explanation of output display fix
  - PYTEST_SETUP.md: Test suite configuration and usage
  - TEST_QUICK_REFERENCE.md: Quick testing guide

### Architecture & Planning
- **Workflow Redesign Proposal**: Documented multi-stage workflow architecture (see WORKFLOW_REDESIGN.md)
  - Proposed 3-stage workflow: Question Analysis → Search Execution → Answer Synthesis
  - Would enable better result summarization and targeted searches

- **CLI Tool Enhancement Plan**: Prepared architectural improvements (see MINION_PLAN.md)
  - Planned specialized agent roles: question_analyzer, code_searcher, response_formatter
  - Model selection system to support Haiku, GPT-4o-mini, and Ollama
  - Working directory support for analyzing user's current codebase

- **Improvements Plan**: Created comprehensive enhancement strategy (see IMPROVEMENT_PLAN.md)
  - Phase 1: Smart Result Filtering (high impact, low risk)
  - Phase 2: DAG-Based Question Classification with specialized agents
  - Phase 2b: RAG Index Optimization (auto-build + incremental updates)
  - Phase 3: Smart Result Filtering implementation
  - Phases 4-5: Response validation and UI enhancements

### Repository Cleanup
- Removed Agent Engine documentation that belonged in agent_engine repo:
  - Deleted `docs/canonical/AGENT_ENGINE_SPEC.md`
  - Deleted `docs/canonical/AGENT_ENGINE_OVERVIEW.md`
  - Deleted `docs/canonical/RESEARCH.md`
  - Deleted `docs/operational/PLAN_BUILD_AGENT_ENGINE.md`
  - Deleted `docs/operational/AGENT_ENGINE_FIX_PLAN.md`
- Consolidated root-level completion documents into this changelog
- Kept Ask project-specific documentation only
