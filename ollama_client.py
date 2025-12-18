"""Ollama LLM client aligned with Agent Engine expectations."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, Optional
from urllib import request as urlrequest
from urllib.error import URLError

logger = logging.getLogger(__name__)


class OllamaLLMClient:
    """Ollama client compatible with Agent Engine's llm_client contract."""

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        transport: Optional[Callable[[str, Dict[str, str], Dict[str, Any]], Any]] = None,
        timeout: int = 30,
        auto_pull: bool = True,
        auto_select_llama_size: bool = False,
        llama_size_thresholds_gb: Optional[Dict[str, int]] = None,
        min_llama_size: Optional[str] = None,
        max_llama_size: Optional[str] = None,
    ) -> None:
        self.model = model or "llama3"
        normalized_base = base_url.rstrip("/")
        if normalized_base.endswith("/api/generate"):
            normalized_base = normalized_base[: -len("/api/generate")]
        elif normalized_base.endswith("/api"):
            normalized_base = normalized_base[: -len("/api")]
        self.base_url = normalized_base or "http://localhost:11434"
        self.generate_url = f"{self.base_url}/api/generate"
        self.tags_url = f"{self.base_url}/api/tags"
        self.pull_url = f"{self.base_url}/api/pull"
        self.timeout = timeout
        self.auto_pull = auto_pull
        self.auto_select_llama_size = auto_select_llama_size
        self.llama_size_thresholds_gb = llama_size_thresholds_gb or {"70b": 48, "8b": 8}
        self.min_llama_size = min_llama_size
        self.max_llama_size = max_llama_size
        self._model_cache: set[str] = set()
        self.transport = transport or self._urllib_transport

    def generate(self, request: Dict[str, Any] | str) -> Any:
        prompt = request.get("prompt") if isinstance(request, dict) else str(request)
        model_name = self._resolve_model_name(request)
        payload = {"model": model_name, "prompt": prompt, "stream": False}
        self._ensure_model_available(model_name)
        response = self.transport(self.generate_url, {"Content-Type": "application/json"}, payload)
        return _parse_response(response, content_key="response")

    def stream_generate(self, request: Dict[str, Any]):
        # No streaming in this client; yield single response for compatibility.
        yield self.generate(request)

    def _resolve_model_name(self, request: Dict[str, Any] | str) -> str:
        requested_model = self.model
        if isinstance(request, dict) and request.get("model"):
            requested_model = request["model"]
        if self.auto_select_llama_size and self._looks_like_llama_base(requested_model):
            return self._select_llama_variant(requested_model)
        return requested_model

    def _looks_like_llama_base(self, model_name: str) -> bool:
        base, _, size = model_name.partition(":")
        return base.startswith("llama") and not size

    def _select_llama_variant(self, base_model: str) -> str:
        available_gb = _get_system_memory_gb()
        candidates = sorted(self.llama_size_thresholds_gb.items(), key=lambda kv: kv[1], reverse=True)
        candidates = self._filter_llama_candidates(candidates)
        for size, min_gb in candidates:
            if available_gb >= min_gb:
                return f"{base_model}:{size}"
        if candidates:
            return f"{base_model}:{candidates[-1][0]}"
        return base_model

    def _filter_llama_candidates(self, candidates: list[tuple[str, int]]) -> list[tuple[str, int]]:
        if not self.min_llama_size and not self.max_llama_size:
            return candidates

        min_threshold = self.llama_size_thresholds_gb.get(self.min_llama_size) if self.min_llama_size else None
        max_threshold = self.llama_size_thresholds_gb.get(self.max_llama_size) if self.max_llama_size else None

        if self.min_llama_size and min_threshold is None:
            logger.warning("min_llama_size '%s' not found; ignoring.", self.min_llama_size)
        if self.max_llama_size and max_threshold is None:
            logger.warning("max_llama_size '%s' not found; ignoring.", self.max_llama_size)

        filtered = [
            (size, min_gb)
            for size, min_gb in candidates
            if (min_threshold is None or min_gb >= min_threshold)
            and (max_threshold is None or min_gb <= max_threshold)
        ]
        if not filtered:
            logger.warning("No llama variants satisfied min/max filters; falling back to unfiltered list.")
            return candidates
        return filtered

    def _ensure_model_available(self, model: str) -> None:
        if not self.auto_pull or model in self._model_cache:
            return

        # Check installed models
        try:
            resp = self.transport(self.tags_url, {}, {})
            data = _parse_response(resp, content_key="models")
            if isinstance(data, list):
                installed = {m.get("model") for m in data if isinstance(m, dict)}
                if model in installed:
                    self._model_cache.add(model)
                    return
        except Exception as exc:
            logger.warning("Could not verify Ollama models: %s", exc)

        # Pull the model if missing
        try:
            pull_payload = {"model": model}
            _ = self.transport(self.pull_url, {"Content-Type": "application/json"}, pull_payload)
            self._model_cache.add(model)
        except Exception as exc:
            logger.warning("Failed to pull Ollama model %s: %s", model, exc)

    def _urllib_transport(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Any:
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(url, data=data, headers=headers, method="POST")
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc


def _get_system_memory_gb() -> int:
    try:
        import psutil  # type: ignore

        mem = getattr(psutil, "virtual_memory", lambda: None)()
        if mem:
            return int(mem.total / (1024 ** 3))
    except Exception:
        pass

    try:
        if hasattr(os, "sysconf"):
            pagesize = os.sysconf("SC_PAGE_SIZE")
            num_pages = os.sysconf("SC_PHYS_PAGES")
            total = pagesize * num_pages
            return int(total / (1024 ** 3))
    except Exception:
        pass
    return 0


def _parse_response(response: Any, content_key: str) -> Any:
    if hasattr(response, "json"):
        try:
            data = response.json()
        except Exception:
            text = getattr(response, "text", None)
            data = json.loads(text) if text else {}
    else:
        data = response

    if isinstance(data, dict) and content_key in data:
        return data[content_key]
    return data
