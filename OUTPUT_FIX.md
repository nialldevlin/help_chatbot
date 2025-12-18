# Output Display Fix

## Problem

The chatbot was successfully calling tools and getting results, but only displaying planning messages like "I'll search the codebase..." instead of the actual search results.

## Root Cause

Agent_engine's workflow:
1. LLM receives prompt + tool definitions
2. LLM generates tool_plan (JSON with tool calls to make)
3. Agent_engine executes the tools
4. Tool results stored in `output['tool_calls']`
5. **BUT**: No second LLM call to summarize results

The output structure was:
```python
{
  'result': None,  # or planning text
  'tool_calls': [
    {
      'tool_id': 'search_codebase',
      'output': '**Project File Listing:**\n...\n\n**README:**\n...'
    }
  ]
}
```

## Solution

Modified `main.py` to extract and display tool results when `result` is None or missing:

### For Single-Shot Mode (line ~127)
```python
# If result is None but tool_calls exist, show tool results
elif "tool_calls" in output and len(output["tool_calls"]) > 0:
    answer = "Here's what I found:\n\n"
    for tool_call in output["tool_calls"]:
        tool_output = tool_call.get("output", "")
        if tool_output:
            answer += str(tool_output) + "\n"
```

### For REPL Mode (line ~139+)
Created custom REPL loop that:
- Reads user input
- Calls `engine.run()`
- Extracts tool results from `output['tool_calls']`
- Displays them properly
- Truncates long outputs for readability

## Testing

**Before:**
```
Output:
------------------------------------------------------------
I notice that I have the search_codebase tool available, so I'll formulate a plan to investigate...
------------------------------------------------------------
```

**After:**
```
Here's what I found:

**Project File Listing:**
/home/ndev/help_chatbot/README.md
/home/ndev/help_chatbot/main.py
...

**README:**
# Ask - AI-Powered Codebase Assistant
A CLI tool that helps you understand and navigate codebases...
```

## Files Modified

1. `main.py` - Lines 108-145
   - Updated output extraction logic in single-shot mode
   - Replaced `engine.create_repl()` with custom REPL loop

2. `config/agents.yaml` - Simplified prompt
   - Removed confusing JSON output instructions
   - Focused on just using tools

3. `config/workflow.yaml` - Simplified to single agent node
   - Removed multi-agent approach
   - Uses single `answer_question` node with tools

## How It Works Now

1. User asks: "What is this codebase?"
2. Agent generates tool_plan to call `search_codebase`
3. Agent_engine executes `search_codebase` tool
4. Tool returns file listings + README
5. **main.py** extracts tool results and displays them
6. User sees actual search results!

## Limitations

- LLM doesn't summarize/interpret results (just shows raw tool output)
- This is a limitation of agent_engine's single-pass execution
- For better answers, would need:
  - Second LLM call after tools execute, OR
  - Multi-agent workflow with separate analysis step

## Alternative Approach Considered

Tried multi-agent workflow with:
- Agent 1: Search (calls tools)
- Agent 2: Analyze (reads tool results, formats answer)

**Problem**: Agent_engine doesn't pass tool results between nodes automatically. The second agent couldn't see the first agent's tool results.

Current solution (extracting tool results in main.py) is simpler and works well for now.
