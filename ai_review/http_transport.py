"""Small standard-library JSON HTTP transport for AI provider adapters."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from .providers import AIReviewProviderError


class UrllibJsonTransport:
    """JSON transport with bounded timeout and diagnostic-free API-key handling."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise AIReviewProviderError(f"AI provider HTTP error: {exc.code}") from exc
        except OSError as exc:
            raise AIReviewProviderError("AI provider request failed") from exc
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AIReviewProviderError("AI provider returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise AIReviewProviderError("AI provider response must be an object")
        return decoded


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AIReviewProviderError("Local AI redirects are not permitted")


class LocalJsonTransport:
    """Loopback only, without environment proxies or HTTP redirects."""

    def post_json(self, url, *, headers, payload, timeout_seconds):
        if url != "http://127.0.0.1:11434/api/chat":
            raise AIReviewProviderError("Local AI must use the configured loopback endpoint")
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=dict(headers), method="POST"
        )
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _RejectRedirects()
        )
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                body = response.read(1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise AIReviewProviderError(
                    "Local model is missing; run the documented model pull"
                ) from exc
            raise AIReviewProviderError(f"Local AI HTTP error: {exc.code}") from exc
        except OSError as exc:
            raise AIReviewProviderError(
                "Local AI is unavailable; start the local review server and try again"
            ) from exc
        if len(body) > 1024 * 1024:
            raise AIReviewProviderError("Local AI response exceeds the size limit")
        try:
            decoded = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise AIReviewProviderError("Local AI returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise AIReviewProviderError("Local AI response must be an object")
        return decoded
