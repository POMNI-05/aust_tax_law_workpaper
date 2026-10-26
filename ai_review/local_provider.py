"""Small, on-demand Ollama reviewer for a shared Mac."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from .models import AiReview, DecisionTrace, WorkpaperResult, WorkpaperStatus
from .providers import (
    AIReviewProviderError,
    JsonTransport,
    ShadowReviewInput,
    build_shadow_review_input,
    build_shadow_review_prompt,
)
from .validation import AI_REVIEW_RESPONSE_SCHEMA, parse_ai_review

LOCAL_PROVIDER_NAME = "Local (Ollama)"
DEFAULT_LOCAL_MODEL = "qwen3:1.7b"
LOCAL_REVIEW_PROMPT_VERSION = "1.0-local.1"
LOCAL_CHAT_URL = "http://127.0.0.1:11434/api/chat"
LOCAL_CONTEXT_TOKENS = 8192
LOCAL_OUTPUT_TOKENS = 1024
MAX_PROMPT_BYTES = 6144
MAX_BATCHES = 16
_REVIEW_LOCK = threading.Lock()


def _prompt(review_input: ShadowReviewInput) -> str:
    schema = json.dumps(AI_REVIEW_RESPONSE_SCHEMA["schema"], separators=(",", ":"))
    return f"{build_shadow_review_prompt(review_input)}\n\nReturn this JSON schema:\n{schema}"


def _review_batches(review_input: ShadowReviewInput) -> list[tuple[str, list[str]]]:
    """Partition all evidence rather than silently truncate a small context."""

    batches: list[tuple[str, list[str]]] = []
    pending: list[dict] = []
    known_ids = {trace["decision_id"] for trace in review_input.decision_traces}
    if any(
        item["decision_id"] is not None and item["decision_id"] not in known_ids
        for item in review_input.review_items
    ):
        raise AIReviewProviderError("Review evidence references a missing decision")

    def candidate(traces):
        ids = [trace["decision_id"] for trace in traces]
        items = tuple(
            item for item in review_input.review_items
            if item["decision_id"] in ids
            or (item["decision_id"] is None and not batches)
        )
        return _prompt(ShadowReviewInput(review_input.income_year, items, tuple(traces))), ids

    for trace in review_input.decision_traces:
        prompt, ids = candidate([*pending, trace])
        if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES and pending:
            batches.append(candidate(pending))
            pending = []
            prompt, ids = candidate([trace])
        if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise AIReviewProviderError("A decision exceeds the lightweight local review limit")
        pending.append(trace)
    if pending:
        batches.append(candidate(pending))
    if len(batches) > MAX_BATCHES:
        raise AIReviewProviderError("Workpaper exceeds the lightweight local review batch limit")
    return batches


@dataclass(slots=True)
class OllamaShadowReviewProvider:
    """Local-only schema-constrained review; no keys, tools or cloud fallback."""

    transport: JsonTransport
    model: str = DEFAULT_LOCAL_MODEL
    timeout_seconds: float = 120.0
    provider_name: str = field(init=False, default=LOCAL_PROVIDER_NAME)

    def review(
        self,
        workpaper_result: WorkpaperResult,
        decision_traces: Sequence[DecisionTrace],
    ) -> AiReview:
        if self.model != DEFAULT_LOCAL_MODEL:
            raise AIReviewProviderError(f"This local trial supports only {DEFAULT_LOCAL_MODEL}")
        if workpaper_result.status != WorkpaperStatus.COMPLETED:
            raise AIReviewProviderError("Only completed workpapers can be sent for AI review")
        if not decision_traces:
            raise AIReviewProviderError(
                "No deterministic decision traces are available for review"
            )
        batches = _review_batches(build_shadow_review_input(workpaper_result, decision_traces))
        if not _REVIEW_LOCK.acquire(blocking=False):
            raise AIReviewProviderError("A local review is already running; try again when it finishes")
        try:
            deadline = time.monotonic() + self.timeout_seconds
            findings = []
            limitations = []
            for prompt, decision_ids in batches:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AIReviewProviderError(
                        "Local review timed out; no partial findings were accepted"
                    )
                response = self.transport.post_json(
                    LOCAL_CHAT_URL,
                    headers={"Content-Type": "application/json"},
                    payload={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "format": AI_REVIEW_RESPONSE_SCHEMA["schema"],
                        "stream": False,
                        "think": False,
                        "keep_alive": 0,
                        "options": {
                            "temperature": 0,
                            "num_ctx": LOCAL_CONTEXT_TOKENS,
                            "num_predict": LOCAL_OUTPUT_TOKENS,
                            "num_thread": 2,
                            "num_batch": 128,
                        },
                    },
                    timeout_seconds=min(60.0, remaining),
                )
                if response.get("done") is not True or response.get("done_reason") != "stop":
                    raise AIReviewProviderError("Local model returned an incomplete review")
                try:
                    payload = json.loads(response["message"]["content"])
                    review = parse_ai_review(payload, decision_ids=decision_ids)
                except (KeyError, TypeError, ValueError) as exc:
                    raise AIReviewProviderError(
                        "Local model returned an invalid structured review"
                    ) from exc
                findings.extend(review.findings)
                limitations.extend(review.limitations)
            limitations.append(
                "Experimental small local model; findings require independent accountant review."
            )
            if len(batches) > 1:
                limitations.append(
                    "Evidence was reviewed in separate batches; cross-batch issues may be missed."
                )
            return AiReview("completed", tuple(findings), tuple(dict.fromkeys(limitations)))
        finally:
            _REVIEW_LOCK.release()
