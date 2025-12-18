#!/usr/bin/env python3
"""Test chatbot with Anthropic Claude Haiku"""

import os

# Enable Anthropic LLM usage
os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'

# Check if API key is set
if not os.getenv('ANTHROPIC_API_KEY'):
    print("ERROR: ANTHROPIC_API_KEY environment variable not set")
    print("\nPlease set it with:")
    print("  export ANTHROPIC_API_KEY='your-key-here'")
    exit(1)

from agent_engine import Engine

# Load engine
print("Loading engine with Haiku...")
config_dir = 'config'
engine = Engine.from_config_dir(config_dir)

print("LLM Client:", "Available" if engine.agent_runtime.llm_client else "NOT AVAILABLE")

if not engine.agent_runtime.llm_client:
    print("\nERROR: LLM client not initialized!")
    print("Make sure ANTHROPIC_API_KEY is set correctly")
    exit(1)

# Test with a simple question first
print("\n" + "=" * 60)
print("Test 1: Simple greeting")
print("=" * 60)
result = engine.run({'user_input': 'Hello'})
print(f"Status: {result['status']}")
print(f"Output: {result['output'][:200]}..." if len(str(result['output'])) > 200 else f"Output: {result['output']}")

# Test with codebase question
print("\n" + "=" * 60)
print("Test 2: Codebase question (should use search_codebase tool)")
print("=" * 60)
result = engine.run({'user_input': 'What files are in this codebase?'})

print(f"\nStatus: {result['status']}")
print(f"\nFinal Output:\n{result['output']}\n")

# Check tool usage
print("=" * 60)
print("Tool Usage Analysis:")
for node in result['history']:
    if node['node_id'] == 'answer_question':
        print(f"  Tool plan: {node.get('tool_plan')}")
        tool_calls = node.get('tool_calls', [])
        print(f"  Tool calls: {len(tool_calls)}")
        for i, call in enumerate(tool_calls):
            print(f"    {i+1}. {call.get('tool_id')}: {call.get('status')}")
            if call.get('error'):
                print(f"       Error: {call.get('error')}")
        if node.get('error'):
            print(f"  Node Error: {node['error']}")

print("\n" + "=" * 60)
print("Tests completed!")
