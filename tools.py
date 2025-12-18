import os
import glob
import re
import shutil
import subprocess
import yaml
import random
from pathlib import Path
from typing import List, Tuple

from rag import OllamaEmbeddingProvider, Retriever, SimpleVectorStore, Chunk, get_rag_index_path


def _truncate_readme(readme_content: str, max_lines: int = 50) -> str:
    """Truncate README to first max_lines or until first H2 heading."""
    if not readme_content:
        return ""

    lines = readme_content.split('\n')
    truncated = []

    for i, line in enumerate(lines):
        if i >= max_lines:
            break
        # Stop at first H2 heading (## Something) after initial title
        if i > 0 and line.strip().startswith('## '):
            break
        truncated.append(line)

    result = '\n'.join(truncated)
    if len(lines) > len(truncated):
        result += f"\n\n... (README truncated, {len(lines) - len(truncated)} more lines)"

    return result


def _limit_search_results(search_output: str, max_results: int) -> str:
    """Limit ripgrep search results to top N file matches."""
    if not search_output or "No direct matches" in search_output:
        return search_output

    # Split by file (ripgrep separates files with blank lines typically)
    # This is a simple approach - just truncate the output
    lines = search_output.split('\n')
    if len(lines) <= max_results * 5:  # Rough estimate: 5 lines per match
        return search_output

    # Keep first max_results worth of content
    truncated = lines[:max_results * 5]
    return '\n'.join(truncated) + f"\n\n... (showing top {max_results} matches)"


def search_codebase_tool(query: str, focus_areas: List[str] = None, workspace_root: str = None, question_type: str = None) -> str:
    """
    Searches the codebase for relevant files and snippets based on a query.
    Searches the user's current working directory, not the script location.
    For a general query like "what is this codebase", it will provide a file listing and README content.

    Args:
        query: The search query string
        focus_areas: Optional list of directories to search within
        workspace_root: Optional workspace root path (defaults to cwd)
        question_type: Optional type hint to filter results - one of:
            - "overview": Include truncated README, limited search snippets (top 3)
            - "lookup": Skip README, limited search snippets (top 5)
            - "implementation": Skip README, limited search snippets (top 3)
            - "configuration": Skip README, focus on config files
            - None: Include all sections (default behavior)
    """
    cwd = workspace_root or os.getcwd()

    # For configuration questions, default focus_areas if not provided
    if question_type == "configuration" and not focus_areas:
        focus_areas = ["config", "docs"]

    print(f"DEBUG: Searching {cwd} for query: '{query}' with focus areas: {focus_areas or 'all'} (question_type: {question_type})")

    try:
        # List files and directories from cwd, ignoring .git, venv, and __pycache__
        all_files = glob.glob(os.path.join(cwd, "**/*"), recursive=True)
        files = [
            f for f in all_files
            if ".git" not in f and "venv" not in f and "__pycache__" not in f
        ]
        # Limit the listing so we don't overwhelm downstream prompts
        preview_files = files[:200]
        file_list = "\n".join(preview_files)
        if len(files) > len(preview_files):
            file_list += f"\n... and {len(files) - len(preview_files)} more files"

        readme_content = ""
        # Find and read README
        readme_files = [f for f in files if "readme" in f.lower()]
        if readme_files:
            try:
                with open(readme_files[0], 'r') as f:
                    readme_content = f.read()
            except Exception as e:
                readme_content = f"Error reading README: {e}"

        direct_file_snippets = _gather_direct_file_snippets(query, cwd)

        search_snippets = ""
        rag_snippets = ""
        rag_meta = _load_rag_settings(cwd)
        rag_error = None
        if rag_meta.get("enabled"):
            rag_snippets, rag_error = _run_rag(query, cwd, rag_meta)

        if query:
            rg_path = shutil.which("rg")
            if rg_path:
                search_dirs = focus_areas or [cwd]
                snippet_lines = []
                for area in search_dirs:
                    area_path = os.path.join(cwd, area) if not os.path.isabs(area) else area
                    if not os.path.exists(area_path):
                        continue
                    cmd = [
                        rg_path,
                        "--max-filesize", "1M",
                        "--max-count", "5",
                        "-n",
                        "--context", "1",
                        query,
                        area_path,
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                    )
                    if result.stdout.strip():
                        snippet_lines.append(result.stdout.strip())
                search_snippets = "\n\n".join(snippet_lines).strip()
            else:
                search_snippets = "ripgrep (`rg`) is not installed, so code search is unavailable."
        if not search_snippets:
            search_snippets = "No direct matches found for the query."

        # Apply question_type-specific filtering
        filtered_readme = readme_content
        filtered_search_snippets = search_snippets

        if question_type == "overview":
            # Truncate README to 50 lines or first H2, limit search to top 3
            filtered_readme = _truncate_readme(readme_content, max_lines=50)
            filtered_search_snippets = _limit_search_results(search_snippets, max_results=3)
        elif question_type == "lookup":
            # Skip README, limit search to top 5
            filtered_readme = None
            filtered_search_snippets = _limit_search_results(search_snippets, max_results=5)
        elif question_type == "implementation":
            # Skip README, limit search to top 3
            filtered_readme = None
            filtered_search_snippets = _limit_search_results(search_snippets, max_results=3)
        elif question_type == "configuration":
            # Skip README, limit search to top 3
            filtered_readme = None
            filtered_search_snippets = _limit_search_results(search_snippets, max_results=3)
        # else: question_type is None, keep all sections (current behavior)

        # Build sections conditionally based on filtered results
        sections = [
            f"## Query\n{query}",
            "## Search Snippets\n" + (filtered_search_snippets or "No direct matches found for the query."),
            "## RAG Snippets\n" + (rag_snippets or "RAG disabled or no matches found."),
            "## RAG Status\n" + (rag_error or "RAG retrieval attempted."),
            "## Direct File Snippets\n" + (direct_file_snippets or "No direct file references found in the query."),
        ]

        # Add README section only if not filtered out
        if filtered_readme is not None:
            sections.append("## README\n" + (filtered_readme or "No README file found."))

        sections.append("## Project File Listing (partial)\n" + (file_list or "No files were listed."))

        return "\n\n".join(sections)
    except Exception as e:
        return f"Error while analyzing codebase: {e}"


def _load_rag_settings(cwd: str) -> dict:
    """Load rag profile metadata from config/memory.yaml if present.

    Defaults to enabled with top_k=6 when no config exists so RAG still works in
    arbitrary workspaces.
    """
    cfg_path = os.path.join(cwd, "config", "memory.yaml")
    if not os.path.exists(cfg_path):
        return {"enabled": True, "top_k": 6}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        profiles = (data.get("memory") or {}).get("context_profiles") or []
        rag_profile = next((p for p in profiles if p.get("id") == "rag_profile"), None)
        if not rag_profile:
            return {"enabled": True, "top_k": 6}
        meta = rag_profile.get("metadata") or {}
        return {
            "enabled": meta.get("rag_enabled", True),
            "top_k": int(meta.get("rag_top_k", 6)),
        }
    except Exception:
        return {"enabled": True, "top_k": 6}


def _run_rag(query: str, workspace_root: str, rag_meta: dict) -> Tuple[str, str]:
    if not query:
        return "", "RAG skipped (empty query)."
    try:
        embedder = OllamaEmbeddingProvider()
        store_path = os.path.join(workspace_root, ".agent_engine", "rag_index.json")
        retriever = Retriever(
            workspace_root=workspace_root,
            embedder=embedder,
            store=SimpleVectorStore(store_path),
        )
        chunks = retriever.retrieve(query, top_k=rag_meta.get("top_k", 6))
        if not chunks:
            return "No RAG matches found.", "RAG completed (no matches)."
        lines = []
        for c in chunks:
            lines.append(f"{c.path}:{c.start_line}-{c.end_line} (score={c.score:.3f})\n{c.text.strip()}")
        return "\n\n".join(lines), "RAG completed."
    except Exception as exc:
        return "", f"RAG retrieval failed: {exc}"


def _gather_direct_file_snippets(query: str, workspace_root: str) -> str:
    """If the query names files/paths, read and return small snippets."""
    tokens = re.findall(r"[A-Za-z0-9_./:-]+", query)
    seen = set()
    snippets: List[str] = []
    default_roots = ["src", "docs", "config", "tests"]

    def candidate_paths(tok: str) -> List[str]:
        cands = []
        if os.path.isabs(tok):
            cands.append(tok)
        else:
            cands.append(os.path.join(workspace_root, tok))
            for root in default_roots:
                cands.append(os.path.join(workspace_root, root, tok.lstrip("/")))
        return cands

    # Also consider combined tokens like "src/agent_engine/" + "runtime/context.py"
    for i, tok in enumerate(tokens):
        if i + 1 < len(tokens) and tok.endswith("/"):
            combined = tok.rstrip("/") + "/" + tokens[i + 1].lstrip("/")
            tokens.append(combined)

    for tok in tokens:
        if "/" in tok or tok.endswith((".py", ".md", ".yaml", ".yml", ".json", ".txt")):
            for cand in candidate_paths(tok):
                if os.path.isdir(cand) or not os.path.exists(cand):
                    continue
                real = os.path.realpath(cand)
                if real in seen:
                    continue
                seen.add(real)
                try:
                    with open(real, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    numbered = [f"{idx+1}: {line.rstrip()}" for idx, line in enumerate(lines[:200])]
                    excerpt = "\n".join(numbered)
                    rel = os.path.relpath(real, workspace_root)
                    snippets.append(f"{rel}:1-{min(len(lines),200)}\n{excerpt}")
                    break
                except Exception:
                    continue
    # Heuristic fallback: if nothing found and query mentions context/RAG, pull the main context file
    if not snippets and any(k in query.lower() for k in ["context", "rag", "retrieval"]):
        fallback = os.path.join(workspace_root, "src", "agent_engine", "runtime", "context.py")
        if os.path.exists(fallback):
            try:
                with open(fallback, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                numbered = [f"{idx+1}: {line.rstrip()}" for idx, line in enumerate(lines[:200])]
                excerpt = "\n".join(numbered)
                rel = os.path.relpath(fallback, workspace_root)
                snippets.append(f"{rel}:1-{min(len(lines),200)}\n{excerpt}")
            except Exception:
                pass
    return "\n\n".join(snippets)

def format_response_tool(original_question: str, analysis: str, code_snippets: str, workspace_root: str = None) -> str:
    """
    Formats the analyzed question and code snippets into a coherent answer for the user.
    """
    print(f"DEBUG: Formatting response for question: '{original_question}' (workspace: {workspace_root or 'cwd'})")
    response = f"## Your Question:\n{original_question}\n\n"
    response += f"## Agent Analysis:\n{analysis}\n\n"
    response += f"## Relevant Code/Information:\n{code_snippets}\n\n"
    return response


def ensure_rag_index_built(workspace_root: str, rag_meta: dict) -> bool:
    """
    Ensure RAG index exists and is up-to-date.
    Called on app startup before first query.
    Returns True if RAG is ready, False if skipped.
    """
    if not rag_meta.get("enabled"):
        return False

    # Check file count
    file_count = len(list(Path(workspace_root).rglob("*.py")))
    if file_count > 1000:
        print(f"i  Codebase is large ({file_count} files). Skipping RAG indexing.")
        print(f"   RAG provides semantic search but isn't critical for basic queries.")
        return False

    store_path = get_rag_index_path(workspace_root)
    embedder = OllamaEmbeddingProvider()
    store = SimpleVectorStore(store_path)
    retriever = Retriever(workspace_root, embedder, store)

    # Check if index exists and is valid
    existing_chunks = store.load()
    if existing_chunks:
        # Index exists - check if it's stale
        if _is_index_stale(workspace_root, existing_chunks):
            print("(updating RAG index (files changed)...")
            _update_rag_index_incremental(retriever, existing_chunks)
        # else: index is current, skip rebuild
    else:
        # No index - build it
        print("Building RAG index (first run)...")
        print("   This may take a minute for large codebases.")
        try:
            chunks = retriever.build_index()
            print(f"Indexed {len(chunks)} chunks from {file_count} files")
        except Exception as e:
            print(f"RAG indexing failed: {e}")
            print("   Queries will still work using keyword search.")
            return False

    return True


def _is_index_stale(workspace_root: str, indexed_chunks: List[Chunk], max_samples: int = 50) -> bool:
    """Check if index is stale by sampling files (for performance)."""
    # Get unique file paths from chunks
    unique_files = {}
    for chunk in indexed_chunks:
        if chunk.path not in unique_files:
            unique_files[chunk.path] = chunk.modified_time

    # Sample at most max_samples files to check
    files_to_check = list(unique_files.items())
    if len(files_to_check) > max_samples:
        files_to_check = random.sample(files_to_check, max_samples)

    for file_path, indexed_mtime in files_to_check:
        full_path = os.path.join(workspace_root, file_path)
        if not os.path.exists(full_path):
            return True  # File was deleted
        if os.path.getmtime(full_path) > indexed_mtime:
            return True  # File was modified

    return False  # Sample looks good; assume index is current


def _update_rag_index_incremental(retriever, existing_chunks: List[Chunk]) -> None:
    """Update only new/modified files."""
    print("Updating RAG index (files changed)...")
    retriever.build_index_incremental()
