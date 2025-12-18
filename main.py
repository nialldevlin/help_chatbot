# main.py - Entry point for the Help Chatbot CLI
import argparse
import os
import sys

# Enable agent_engine to use Anthropic/Haiku
os.environ['AGENT_ENGINE_USE_ANTHROPIC'] = '1'
# Default Ollama host if not provided
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")

from anthropic import Anthropic
from tools import search_codebase_tool, ensure_rag_index_built, _load_rag_settings

MODEL_PROFILES = {
    "haiku": {"backend": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "llama": {"backend": "ollama", "model": "llama3.2:1b"},
}
DEFAULT_MODEL = "haiku"


def handle_model_command(command: str, current_model: str) -> str:
    """Switch or report the current LLM profile."""
    parts = command.strip().split()
    available = ", ".join(sorted(MODEL_PROFILES.keys()))
    if len(parts) == 1:
        print(f"Current model: {current_model}")
        print(f"Available models: {available}")
        return current_model

    target = parts[1].lower()
    if target not in MODEL_PROFILES:
        print(f"Unknown model '{target}'. Valid options: {available}")
        return current_model

    if target == current_model:
        print(f"Already using '{target}'.")
        return current_model

    print(f"Switched model to '{target}'.")
    return target


def generate_with_model(prompt: str, model_choice: str) -> str:
    """Generate a response for the prompt using the selected model."""
    profile = MODEL_PROFILES.get(model_choice, MODEL_PROFILES[DEFAULT_MODEL])
    backend = profile["backend"]
    model_id = profile["model"]

    if backend == "anthropic":
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=model_id,
            max_tokens=1000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    elif backend == "ollama":
        try:
            from ollama_client import OllamaLLMClient
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Ollama model requested but `ollama_client` module is unavailable. "
                "Install the package (e.g., `pip install -e /home/ndev/help_chatbot`) "
                "or ensure the module is on PYTHONPATH."
            ) from exc

        client = OllamaLLMClient(model=model_id)
        result = client.generate({"prompt": prompt})
        if isinstance(result, dict):
            return result.get("response") or result.get("main_result") or str(result)
        return str(result)
    else:
        raise ValueError(f"Unsupported backend '{backend}' for model '{model_choice}'")


def infer_focus_from_question(question: str) -> list[str] | None:
    """Infer likely focus paths from the question (simple heuristics)."""
    tokens = question.replace(",", " ").replace(":", " ").split()
    focus = set()
    for tok in tokens:
        if "/" in tok or tok.endswith((".py", ".md", ".yaml", ".yml", ".json", ".txt")):
            # take directory or token itself
            if "/" in tok:
                path_part = tok.split("/")[0] if tok.startswith("/") else tok.split("/")[0]
                focus.add(path_part)
            else:
                focus.add(tok)
    if not focus:
        return ["src", "docs", "config", "tests"]
    return list(focus)

def get_config_dir():
    """
    Resolve the config directory.
    Tries local ./config first (for development), then installed location.
    """
    # First try: local config directory relative to this script (for development/editable install)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir, "config")

    if os.path.isdir(config_dir):
        return config_dir

    # Second try: installed data files location (for pip install)
    try:
        import sys
        # data_files installs to sys.prefix/ask_chatbot_config
        installed_config = os.path.join(sys.prefix, 'ask_chatbot_config')
        if os.path.isdir(installed_config):
            return installed_config
    except Exception:
        pass

    # Final fallback: return the local path even if it doesn't exist
    # (will error later with helpful message)
    return config_dir

def get_model_profile(model_id, profiles_config):
    """
    Find a profile by ID in the profiles config.
    Returns the profile dict or None if not found.
    """
    if 'profiles' not in profiles_config:
        return None

    for profile in profiles_config['profiles']:
        if profile.get('id') == model_id:
            return profile

    return None

def summarize_tool_results(user_question, tool_results, model_choice):
    """
    Summarize tool results through the selected LLM backend.

    Args:
        user_question: The original question asked by the user
        tool_results: The raw output from search_codebase tool (file listings + README)
        model_choice: Which backend/model to use for summarization

    Returns:
        Natural language summary as a string
    """

    prompt = f"""You are helping answer a question about a codebase.

User's question: {user_question}

Search results (structured):
{tool_results}

Ground rules:
- If Direct File Snippets exist, answer ONLY from those and cite their paths/line ranges exactly.
- Otherwise, use RAG Snippets; cite their paths/line ranges exactly.
- Otherwise, use Search Snippets; cite file paths/lines if present.
- If nothing usable is available, say so explicitly; do NOT invent details or rely on README.

Always include a short RAG status if present.
Every claim must include an inline citation of the form path:line-range taken from the provided snippets (e.g., src/agent_engine/runtime/context.py:56-67). If you cannot cite, say so and stop; do not guess or invent line numbers.
Output 1-2 short paragraphs."""

    try:
        return generate_with_model(prompt, model_choice)
    except Exception as e:
        return f"Error summarizing results: {e}\n\nRaw results:\n{tool_results}"

def answer_question(question: str, model_choice: str, focus_areas: list[str] | None = None) -> str:
    """
    Answer a question about the codebase by searching and summarizing.

    Args:
        question: The user's question

    Returns:
        Natural language answer
    """
    print(f"\nSearching codebase...")

    # Search the codebase directly
    search_results = search_codebase_tool(query=question, focus_areas=focus_areas)

    # Summarize the results using the selected LLM
    print("Analyzing results...")
    answer = summarize_tool_results(question, search_results, model_choice)

    return answer

def main():
    """
    Main entry point for the 'ask' CLI tool.
    Supports two modes:
    - Single-shot: ask "question" -> run query, print answer, exit
    - Interactive: ask -> start REPL
    """
    parser = argparse.ArgumentParser(
        prog='ask',
        description='Ask questions about your codebase using AI agents'
    )
    parser.add_argument(
        'question',
        nargs='?',
        default=None,
        help='The question to ask about the codebase. If not provided, starts interactive REPL mode.'
    )
    parser.add_argument(
        '--model', '-m',
        dest='model',
        choices=list(MODEL_PROFILES.keys()),
        help='Model profile to use (haiku or llama).'
    )
    parser.add_argument(
        '--skip-rag',
        action='store_true',
        help='Skip RAG indexing for this session'
    )

    args = parser.parse_args()

    try:
        initial_model = args.model or DEFAULT_MODEL

        # Build/update RAG index on startup (unless --skip-rag)
        if not args.skip_rag:
            ensure_rag_index_built(os.getcwd(), _load_rag_settings(os.getcwd()))

        if args.question:
            # Single-shot mode: run the query and exit
            focus = infer_focus_from_question(args.question)
            answer = answer_question(args.question, initial_model, focus_areas=focus)
            print("\n" + answer)
        else:
            # Interactive REPL mode
            print("Starting Help Chatbot...")
            print("Type '/quit' or '/exit' to quit, or type your question.")
            print()

            # Custom REPL loop
            current_model = initial_model
            current_focus = None
            while True:
                try:
                    # Get user input
                    user_input = input("\n> ").strip()

                    if not user_input:
                        continue

                    # Handle quit commands
                    if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                        print("Goodbye!")
                        break

                    if user_input.startswith("/model"):
                        current_model = handle_model_command(user_input, current_model)
                        continue
                    if user_input.startswith("/focus"):
                        parts = user_input.split()
                        current_focus = parts[1:] if len(parts) > 1 else None
                        if current_focus:
                            print(f"Focus set to: {', '.join(current_focus)}")
                        else:
                            print("Cleared focus (using auto-inferred/default).")
                        continue

                    # Answer the question
                    focus = current_focus or infer_focus_from_question(user_input)
                    answer = answer_question(user_input, current_model, focus_areas=focus)
                    print("\n" + answer)

                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except EOFError:
                    print("\nGoodbye!")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    import traceback
                    traceback.print_exc()

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please ensure your configuration files are correct and all dependencies are installed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
