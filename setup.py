from setuptools import setup
import os

# Get the directory where setup.py is located
here = os.path.abspath(os.path.dirname(__file__))

setup(
    name="ask-chatbot",
    version="0.1.0",
    description="A CLI tool to ask questions about codebases using AI agents",
    author="Help Chatbot",
    py_modules=['main', 'tools', 'ollama_client', 'rag'],
    data_files=[
        ('ask_chatbot_config', [
            os.path.join(here, 'config', 'agents.yaml'),
            os.path.join(here, 'config', 'workflow.yaml'),
            os.path.join(here, 'config', 'tools.yaml'),
            os.path.join(here, 'config', 'cli_profiles.yaml'),
            os.path.join(here, 'config', 'memory.yaml'),
            os.path.join(here, 'config', 'provider_credentials.yaml'),
        ]),
        ('ask_chatbot_config/schemas', [
            os.path.join(here, 'config', 'schemas', 'workflow_schemas.yaml'),
        ]),
    ],
    install_requires=[
        "agent_engine @ file:///home/ndev/agent_engine",
        "anthropic>=0.39.0",
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'pytest-mock>=3.11.1',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'ask=main:main',
        ],
    },
    python_requires='>=3.8',
)
