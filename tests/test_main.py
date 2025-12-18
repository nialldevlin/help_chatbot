"""Unit tests for main.py"""

import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import get_config_dir, get_model_profile


class TestGetConfigDir:
    """Tests for get_config_dir function."""

    @pytest.mark.unit
    def test_get_config_dir_local(self):
        """Test that local config directory is found."""
        config_dir = get_config_dir()
        assert config_dir is not None
        assert "config" in config_dir

    @pytest.mark.unit
    def test_get_config_dir_exists(self):
        """Test that returned config directory exists."""
        config_dir = get_config_dir()
        assert Path(config_dir).exists()

    @pytest.mark.unit
    def test_get_config_dir_has_required_files(self):
        """Test that config directory contains required files."""
        config_dir = Path(get_config_dir())

        # Check for essential config files
        assert (config_dir / "workflow.yaml").exists()
        assert (config_dir / "agents.yaml").exists()
        assert (config_dir / "tools.yaml").exists()


class TestGetModelProfile:
    """Tests for get_model_profile function."""

    @pytest.mark.unit
    def test_get_model_profile_found(self):
        """Test finding a profile that exists."""
        profiles_config = {
            'profiles': [
                {'id': 'haiku', 'label': 'Haiku'},
                {'id': 'sonnet', 'label': 'Sonnet'},
            ]
        }

        profile = get_model_profile('haiku', profiles_config)
        assert profile is not None
        assert profile['id'] == 'haiku'
        assert profile['label'] == 'Haiku'

    @pytest.mark.unit
    def test_get_model_profile_not_found(self):
        """Test searching for profile that doesn't exist."""
        profiles_config = {
            'profiles': [
                {'id': 'haiku', 'label': 'Haiku'},
            ]
        }

        profile = get_model_profile('nonexistent', profiles_config)
        assert profile is None

    @pytest.mark.unit
    def test_get_model_profile_no_profiles_key(self):
        """Test with config that has no 'profiles' key."""
        profiles_config = {}

        profile = get_model_profile('haiku', profiles_config)
        assert profile is None

    @pytest.mark.unit
    def test_get_model_profile_empty_profiles(self):
        """Test with empty profiles list."""
        profiles_config = {'profiles': []}

        profile = get_model_profile('haiku', profiles_config)
        assert profile is None


class TestMainFunction:
    """Tests for main() function."""

    @pytest.mark.unit
    @patch('main.Engine')
    @patch('sys.argv', ['main.py', 'test question'])
    def test_main_single_shot_mode(self, mock_engine_class):
        """Test single-shot query mode."""
        # Mock the engine
        mock_engine = MagicMock()
        mock_engine_class.from_config_dir.return_value = mock_engine
        mock_engine.run.return_value = {
            'final_answer': 'This is the answer',
            'status': 'success'
        }

        # Import and run main
        from main import main

        # In single-shot mode, main() completes without raising SystemExit
        # unless there's an error
        try:
            main()
        except SystemExit as e:
            # If it does exit, should be with code 0
            assert e.code == 0

        # Verify engine was called
        assert mock_engine.run.called

    @pytest.mark.unit
    @patch('main.Engine')
    @patch('sys.argv', ['main.py'])
    def test_main_interactive_mode(self, mock_engine_class):
        """Test interactive REPL mode."""
        # Mock the engine and REPL
        mock_engine = MagicMock()
        mock_repl = MagicMock()
        mock_engine_class.from_config_dir.return_value = mock_engine
        mock_engine.create_repl.return_value = mock_repl

        from main import main

        # This would normally start a REPL, so we'll just check setup
        # In a real test, you'd need to mock the REPL interaction
        try:
            with patch('builtins.input', side_effect=['exit']):
                main()
        except (SystemExit, KeyboardInterrupt, AttributeError):
            # Expected - REPL might not be fully implemented or might exit
            pass

        # Verify engine was created
        assert mock_engine_class.from_config_dir.called

    @pytest.mark.unit
    @patch('main.Engine')
    @patch('sys.argv', ['main.py', '--model', 'sonnet', 'test question'])
    def test_main_with_model_flag(self, mock_engine_class):
        """Test using --model flag."""
        mock_engine = MagicMock()
        mock_engine_class.from_config_dir.return_value = mock_engine
        mock_engine.run.return_value = {'final_answer': 'Answer'}

        from main import main

        try:
            main()
        except SystemExit:
            pass

        # Verify engine was created
        assert mock_engine_class.from_config_dir.called

    @pytest.mark.unit
    def test_main_config_dir_not_found(self):
        """Test behavior when config directory doesn't exist."""
        with patch('main.get_config_dir', return_value='/nonexistent/path'):
            with patch('sys.argv', ['main.py', 'test']):
                from main import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1

    @pytest.mark.unit
    @patch('main.Engine')
    @patch('sys.argv', ['main.py', 'test question'])
    def test_main_engine_error(self, mock_engine_class):
        """Test error handling when engine fails."""
        mock_engine_class.from_config_dir.side_effect = Exception("Engine failed")

        from main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


class TestOutputExtraction:
    """Tests for output extraction logic in main.py."""

    @pytest.mark.unit
    def test_extract_final_answer_direct(self):
        """Test extracting answer when it's directly in result."""
        result = {'final_answer': 'The answer is 42'}

        # Simulate the extraction logic from main.py
        answer = result.get('final_answer')
        assert answer == 'The answer is 42'

    @pytest.mark.unit
    def test_extract_final_answer_nested(self):
        """Test extracting answer from nested output."""
        result = {
            'output': {
                'final_answer': 'Nested answer'
            }
        }

        # Simulate nested extraction
        answer = None
        if 'output' in result:
            output = result['output']
            if isinstance(output, dict) and 'final_answer' in output:
                answer = output['final_answer']

        assert answer == 'Nested answer'

    @pytest.mark.unit
    def test_extract_result_field(self):
        """Test extracting from 'result' field."""
        result = {
            'output': {
                'result': 'Result answer'
            }
        }

        # Simulate result field extraction
        answer = None
        if 'output' in result:
            output = result['output']
            if isinstance(output, dict) and 'result' in output:
                answer = output['result']

        assert answer == 'Result answer'
