#!/usr/bin/env python3
"""Debug script to check if tools are available to agents"""

import os
os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'

from agent_engine import Engine

config_dir = "/home/ndev/help_chatbot/config"
engine = Engine.from_config_dir(config_dir)

print("=" * 60)
print("WORKFLOW NODES:")
for node in engine.workflow.nodes:
    print(f"\nNode: {node.id}")
    print(f"  Kind: {node.kind}")
    if hasattr(node, 'tools'):
        print(f"  Tools: {node.tools}")
    if hasattr(node, 'agent_id'):
        print(f"  Agent: {node.agent_id}")

print("\n" + "=" * 60)
print("AGENTS:")
for agent in engine.agents:
    print(f"\nAgent: {agent.get('id')}")
    print(f"  LLM: {agent.get('llm')}")

print("\n" + "=" * 60)
print("TOOLS IN ENGINE:")
print(f"  Total tools: {len(engine.tool_definitions)}")
for tool in engine.tool_definitions:
    if hasattr(tool, 'tool_id'):
        print(f"    - {tool.tool_id}")
    elif isinstance(tool, dict) and 'id' in tool:
        print(f"    - {tool['id']}")

print("\n" + "=" * 60)
print("ADAPTER REGISTRY:")
for tool_id in engine.adapters.tools.keys():
    print(f"  - {tool_id}")

print("\n" + "=" * 60)
print("Testing tool call...")

result = engine.run({"user_input": "what files are here"})
print(f"\nResult status: {result.get('status')}")
print(f"Execution time: {result.get('execution_time_ms')}ms")

# Check if tool was called
history = result.get('history', [])
for node in history:
    if node.get('node_id') == 'answer_question':
        print(f"\nAnswer Question Node:")
        print(f"  Tool calls: {len(node.get('tool_calls', []))}")
        for call in node.get('tool_calls', []):
            print(f"    - {call.get('tool_id')}: {call.get('error', 'OK')}")
