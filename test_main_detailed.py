#!/usr/bin/env python3
"""Test main.py workflow with detailed output"""

import os
os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'

from agent_engine import Engine

engine = Engine.from_config_dir('config')

print("Testing: What files are in this codebase?")
print("=" * 60)

result = engine.run({'user_input': 'What files are in this codebase?'})

print(f"Status: {result['status']}")
print(f"Execution time: {result['execution_time_ms']}ms\n")

# Show answer_question node details
for node in result['history']:
    if node['node_id'] == 'answer_question':
        print("Answer Question Node:")
        print(f"  Status: {node['node_status']}")
        print(f"  Tool plan: {node.get('tool_plan')}")
        print(f"  Tool calls: {len(node.get('tool_calls', []))}\n")

        # Show tool call details
        for i, call in enumerate(node.get('tool_calls', [])):
            print(f"Tool Call {i+1}:")
            print(f"  Tool: {call.get('tool_id')}")
            print(f"  Inputs: {call.get('inputs')}")
            print(f"  Output (first 200 chars): {str(call.get('output', ''))[:200]}...")
            print()

# Extract final answer
output = result.get('output')
if isinstance(output, dict):
    if 'result' in output:
        print("Final Answer:")
        print(output['result'])
    elif 'main_result' in output:
        print("Main Result:")
        print(output['main_result'])
    else:
        print("Output dict keys:", list(output.keys()))
else:
    print("Final Output:", output)
