#!/usr/bin/env python3
"""Quick test to see if agent_engine can call LLMs"""

import os
os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'

from agent_engine import Engine

config_dir = "/home/ndev/help_chatbot/config"
engine = Engine.from_config_dir(config_dir)

result = engine.run({"user_input": "hello"})
print("Result:", result)
print("\nExecution time:", result.get('execution_time_ms'), "ms")

# Check if any LLM was actually called
for node in result.get('history', []):
    if node.get('node_kind') == 'agent':
        print(f"\nAgent node '{node['node_id']}':")
        print(f"  - Status: {node['node_status']}")
        print(f"  - Tokens: {node.get('context_metadata', {}).get('total_tokens', 0)}")
        if 'llm_error' in node.get('output', {}):
            print(f"  - LLM Error: {node['output']['llm_error']}")
