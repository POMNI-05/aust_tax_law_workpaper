"""Schema-constrained display-only AI review runner."""

from __future__ import annotations

import logging
from typing import Any

from ai_review import (
    GeminiShadowReviewProvider,
    GrokShadowReviewProvider,
    OllamaShadowReviewProvider,
    SHADOW_REVIEW_PROMPT_VERSION,
)
from ai_review.http_transport import LocalJsonTransport, UrllibJsonTransport
from ai_review.local_provider import LOCAL_PROVIDER_NAME, LOCAL_REVIEW_PROMPT_VERSION


logger = logging.getLogger(__name__)


def run_ai_shadow_review(
    *,
    workpaper_result: Any,
    ai_provider: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """Run minimised decision evidence through the selected AI adapter."""

    prompt_version = (
        LOCAL_REVIEW_PROMPT_VERSION if ai_provider == LOCAL_PROVIDER_NAME
        else SHADOW_REVIEW_PROMPT_VERSION
    )
    provider_kwargs = {
        "api_key": api_key,
        "model": model,
        "transport": UrllibJsonTransport(),
    }
    if ai_provider == "Gemini":
        provider = GeminiShadowReviewProvider(**provider_kwargs)
    elif ai_provider == "Grok":
        provider = GrokShadowReviewProvider(**provider_kwargs)
    elif ai_provider == LOCAL_PROVIDER_NAME:
        provider = OllamaShadowReviewProvider(model=model, transport=LocalJsonTransport())
    else:
        return {
            "status": "skipped",
            "summary": f"Unsupported AI review provider: {ai_provider}.",
            "findings": [],
        }

    try:
        review = provider.review(workpaper_result, workpaper_result.decision_traces)
    except Exception as exc:
        logger.exception("AI shadow review failed for provider=%s", ai_provider)
        return {
            "status": "error",
            "prompt_version": prompt_version,
            "summary": f"{ai_provider} shadow review failed: {type(exc).__name__}: {exc}",
            "findings": [],
        }

    findings = [
        {
            "severity": finding.severity.value,
            "decision_id": finding.decision_id,
            "evidence": list(finding.evidence),
            "missing_facts": list(finding.missing_facts),
            "recommended_review_action": finding.recommended_review_action,
        }
        for finding in review.findings
    ]
    return {
        "status": "success",
        "prompt_version": prompt_version,
        "summary": (
            f"{ai_provider} returned {len(findings)} display-only, schema-validated "
            "review finding(s)."
        ),
        "findings": findings,
        "limitations": list(review.limitations),
    }
