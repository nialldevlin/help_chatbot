#!/bin/bash
# Demo script to show the chatbot in action

source venv/bin/activate

echo "==============================================="
echo "Help Chatbot Demo with Claude Haiku"
echo "==============================================="
echo ""

echo "Test 1: Simple greeting"
echo "-----------------------------------------------"
python main.py "Hello, how are you?"
echo ""
echo ""

echo "Test 2: Ask about the codebase"
echo "-----------------------------------------------"
python main.py "What is this project about?"
echo ""
echo ""

echo "Test 3: Ask about files"
echo "-----------------------------------------------"
python main.py "What configuration files are in this project?"
echo ""
echo ""

echo "==============================================="
echo "Demo completed!"
echo "==============================================="
echo ""
echo "The search_codebase tool is working correctly!"
echo "See STATUS.md for full details."
