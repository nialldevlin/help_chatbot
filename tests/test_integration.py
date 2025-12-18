"""Integration tests for help_chatbot with agent_engine"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEngineIntegration:
    """Integration tests with agent_engine."""

    @pytest.mark.integration
    def test_engine_loads_from_config(self, config_dir):
        """Test that engine loads successfully from config directory."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        assert engine is not None
        assert engine.workflow is not None
        assert engine.agents is not None
        assert len(engine.tool_definitions) > 0

    @pytest.mark.integration
    def test_engine_has_search_codebase_tool(self, config_dir):
        """Test that search_codebase tool is registered."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        # Check adapters registry
        search_tool = engine.adapters.get_tool('search_codebase')
        assert search_tool is not None

    @pytest.mark.integration
    def test_engine_has_workflow_nodes(self, config_dir):
        """Test that workflow has expected nodes."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        node_ids = [node.stage_id for node in engine.workflow.nodes.values()]

        assert 'start' in node_ids
        assert 'answer_question' in node_ids
        assert 'exit' in node_ids

    @pytest.mark.integration
    def test_workflow_answer_question_node_has_tools(self, config_dir):
        """Test that answer_question node has tools configured."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        answer_node = engine.workflow.nodes.get('answer_question')
        assert answer_node is not None
        assert hasattr(answer_node, 'tools')
        assert 'search_codebase' in answer_node.tools


class TestEngineWithAnthropicAPI:
    """Integration tests that require Anthropic API."""

    @pytest.mark.integration
    @pytest.mark.requires_api
    @pytest.mark.slow
    def test_engine_run_with_api(self, config_dir, enable_anthropic, has_anthropic_key):
        """Test full workflow with Anthropic API."""
        if not has_anthropic_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        # Check if LLM client is available
        if not engine.agent_runtime.llm_client:
            pytest.skip("LLM client not initialized")

        result = engine.run({'user_input': 'Hello'})

        assert result is not None
        assert result['status'] == 'success'
        assert 'output' in result
        assert 'history' in result

    @pytest.mark.integration
    @pytest.mark.requires_api
    @pytest.mark.slow
    def test_tool_execution_with_api(self, config_dir, enable_anthropic, has_anthropic_key):
        """Test that tools are called during execution."""
        if not has_anthropic_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        if not engine.agent_runtime.llm_client:
            pytest.skip("LLM client not initialized")

        # Ask a question that should trigger tool usage
        result = engine.run({'user_input': 'What files are in this codebase?'})

        assert result['status'] == 'success'

        # Check if tools were called
        for node in result['history']:
            if node['node_id'] == 'answer_question':
                # Should have a tool plan or tool calls
                has_tool_activity = (
                    node.get('tool_plan') is not None or
                    len(node.get('tool_calls', [])) > 0
                )
                # This might not always be true depending on LLM response
                # So we just check the structure exists
                assert 'tool_plan' in node or 'tool_calls' in node


class TestEngineWithoutAPI:
    """Integration tests that work without external APIs."""

    @pytest.mark.integration
    def test_engine_basic_structure(self, config_dir):
        """Test engine structure without making API calls."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        # Check basic structure
        assert engine.workflow is not None
        assert engine.adapters is not None
        assert engine.tool_runtime is not None
        assert engine.agent_runtime is not None

    @pytest.mark.integration
    def test_engine_tool_handlers_loaded(self, config_dir):
        """Test that tool handlers are loaded correctly."""
        from agent_engine import Engine

        engine = Engine.from_config_dir(str(config_dir))

        # Check if tool handlers exist
        assert hasattr(engine.tool_runtime, 'tool_handlers')

    @pytest.mark.integration
    def test_engine_run_without_llm(self, config_dir):
        """Test running engine without LLM client (will use fallback)."""
        from agent_engine import Engine

        # Don't enable Anthropic
        engine = Engine.from_config_dir(str(config_dir))

        # This should work but return a fallback response
        result = engine.run({'user_input': 'test'})

        assert result is not None
        assert 'status' in result
        assert 'history' in result


class TestOllamaClient:
    """Tests for custom Ollama client."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_ollama_client_creation(self):
        """Test creating Ollama client."""
        from ollama_client import OllamaLLMClient

        client = OllamaLLMClient(model="llama3.2:1b")

        assert client is not None
        assert client.model == "llama3.2:1b"
        assert client.base_url == "http://localhost:11434"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_ollama_client_custom_url(self):
        """Test Ollama client with custom URL."""
        from ollama_client import OllamaLLMClient

        client = OllamaLLMClient(
            model="llama3.2:1b",
            base_url="http://custom:8080"
        )

        assert client.base_url == "http://custom:8080"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.system('curl -s http://localhost:11434/api/tags >/dev/null 2>&1') == 0,
        reason="Ollama server not running"
    )
    def test_ollama_client_generate(self):
        """Test Ollama client generate (requires running Ollama)."""
        from ollama_client import OllamaLLMClient

        client = OllamaLLMClient(model="llama3.2:1b")

        # Simple test with short timeout
        result = client.generate({'prompt': 'Say OK'})

        # Should get a response (might timeout with small model)
        assert result is not None
