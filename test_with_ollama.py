#!/usr/bin/env python3
"""Test chatbot with ollama LLM client"""

import sys
sys.path.insert(0, '.')

from ollama_client import OllamaLLMClient
from agent_engine import Engine

# Load engine
print("Loading engine...")
config_dir = 'config'
engine = Engine.from_config_dir(config_dir)

# Create and inject ollama client
print("Creating ollama LLM client...")
ollama_client = OllamaLLMClient(model="llama3.2:1b")

# Inject the client into agent_runtime
engine.agent_runtime.llm_client = ollama_client

print("Testing with question: 'What files are in this codebase?'")
print("=" * 60)

# Run query
result = engine.run({'user_input': 'What files are in this codebase?'})

print(f"\nStatus: {result['status']}")
print(f"\nFinal Output:\n{result['output']}\n")

# Check tool usage
print("=" * 60)
print("Tool Usage Analysis:")
for node in result['history']:
    if node['node_id'] == 'answer_question':
        print(f"  Tool plan: {node.get('tool_plan')}")
        print(f"  Tool calls: {len(node.get('tool_calls', []))}")
        for i, call in enumerate(node.get('tool_calls', [])):
            print(f"    {i+1}. {call.get('tool_id')}: {call.get('status')}")
        if node.get('error'):
            print(f"  Error: {node['error']}")

print("\n" + "=" * 60)
print("Test completed!")
