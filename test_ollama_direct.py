#!/usr/bin/env python3
"""Direct test of ollama with agent_engine"""

import os
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from agent_engine import Engine

config_dir = 'config'
print("Loading engine from config...")
engine = Engine.from_config_dir(config_dir)

print("\nRunning query: 'What files are in this project?'")
result = engine.run({'user_input': 'What files are in this project?'})

print("\n=== RESULT ===")
print(f"Status: {result['status']}")
print(f"\nFinal Output Type: {type(result['output'])}")
print(f"\nFinal Output: {result['output']}")

print("\n=== EXECUTION HISTORY ===")
for i, node in enumerate(result['history']):
    print(f"\n[{i+1}] Node: {node['node_id']}")
    print(f"    Kind: {node['node_kind']}")
    print(f"    Status: {node['node_status']}")
    print(f"    Error: {node.get('error', 'None')}")

    if node['node_id'] == 'answer_question':
        print(f"    Tool Plan: {node.get('tool_plan')}")
        print(f"    Tool Calls: {len(node.get('tool_calls', []))}")
        print(f"    Output: {str(node.get('output'))[:200]}...")
