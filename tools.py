import os
import glob
import re
import shutil
import subprocess
import yaml
from typing import List, Tuple

from rag import OllamaEmbeddingProvider, Retriever, SimpleVectorStore

def search_codebase_tool(query: str, focus_areas: List[str] = None, workspace_root: str = None) -> str:
    """
    Searches the codebase for relevant files and snippets based on a query.
    Searches the user's current working directory, not the script location.
    For a general query like "what is this codebase", it will provide a file listing and README content.
    """
    cwd = workspace_root or os.getcwd()
    print(f"DEBUG: Searching {cwd} for query: '{query}' with focus areas: {focus_areas or 'all'}")

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

        sections = [
            f"## Query\n{query}",
            "## Search Snippets\n" + (search_snippets or "No direct matches found for the query."),
            "## RAG Snippets\n" + (rag_snippets or "RAG disabled or no matches found."),
            "## RAG Status\n" + (rag_error or "RAG retrieval attempted."),
            "## Direct File Snippets\n" + (direct_file_snippets or "No direct file references found in the query."),
            "## README\n" + (readme_content or "No README file found."),
            "## Project File Listing (partial)\n" + (file_list or "No files were listed."),
        ]
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
