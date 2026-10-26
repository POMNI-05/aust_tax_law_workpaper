from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from ai_review import AIReviewProviderError, read_ai_review_audit
from ai_review.http_transport import LocalJsonTransport, _RejectRedirects
from ai_review.local_provider import (
    DEFAULT_LOCAL_MODEL,
    LOCAL_CHAT_URL,
    LOCAL_PROVIDER_NAME,
    LOCAL_REVIEW_PROMPT_VERSION,
    MAX_PROMPT_BYTES,
    OllamaShadowReviewProvider,
    _REVIEW_LOCK,
    _review_batches,
)
from ai_review.providers import build_shadow_review_input
from frontend import job_runner
from frontend.ai_shadow_review import run_ai_shadow_review
from tests import test_ai_review_providers as provider_fixtures
from tests.test_ai_review_providers import FakeTransport
from tests.test_end_to_end import _combined_workbook


def _response(payload):
    return {"done": True, "done_reason": "stop", "message": {"content": json.dumps(payload)}}


class LocalAiReviewTests(unittest.TestCase):
    def setUp(self):
        fixture = provider_fixtures.AiReviewProviderTests()
        fixture.setUp()
        self.trace = fixture.trace
        self.result = replace(fixture.result, decision_traces=(self.trace,))
        self.payload = fixture.review_payload

    def test_local_review_uses_bounded_schema_without_credentials_or_paths(self):
        transport = FakeTransport(_response(self.payload))
        review = OllamaShadowReviewProvider(transport).review(self.result, [self.trace])
        self.assertEqual(review.findings[0].decision_id, self.trace.decision_id)
        call = transport.calls[0]
        self.assertEqual(call["url"], LOCAL_CHAT_URL)
        self.assertEqual(call["payload"]["keep_alive"], 0)
        self.assertFalse(call["payload"]["think"])
        self.assertFalse(call["payload"]["stream"])
        self.assertEqual(call["payload"]["options"]["num_thread"], 2)
        self.assertLessEqual(call["timeout_seconds"], 60)
        self.assertNotIn("Authorization", call["headers"])
        self.assertNotIn("tools", call["payload"])
        self.assertNotIn("output_path", str(call["payload"]))

    def test_unknown_ids_and_incomplete_output_are_rejected(self):
        unknown = {**self.payload, "findings": [{**self.payload["findings"][0], "decision_id": "other-job"}]}
        for response in (
            _response(unknown),
            {**_response(self.payload), "done_reason": "length"},
            {"done": True, "done_reason": "stop", "message": {"content": "not JSON"}},
        ):
            with self.subTest(response=response):
                with self.assertRaises(AIReviewProviderError):
                    OllamaShadowReviewProvider(FakeTransport(response)).review(self.result, [self.trace])

    def test_cloud_model_and_simultaneous_local_review_are_rejected(self):
        transport = FakeTransport(_response(self.payload))
        with self.assertRaisesRegex(AIReviewProviderError, "supports only"):
            OllamaShadowReviewProvider(transport, model="some-cloud-model").review(self.result, [self.trace])
        with _REVIEW_LOCK:
            with self.assertRaisesRegex(AIReviewProviderError, "already running"):
                OllamaShadowReviewProvider(transport).review(self.result, [self.trace])
        self.assertEqual(transport.calls, [])

    def test_batching_preserves_all_decisions_and_review_items_within_limit(self):
        traces = tuple(replace(self.trace, decision_id=f"decision-{i}") for i in range(30))
        items = tuple(replace(self.result.review_items[0], decision_id=t.decision_id) for t in traces)
        batches = _review_batches(build_shadow_review_input(replace(self.result, review_items=items), traces))
        self.assertGreater(len(batches), 1)
        self.assertEqual([i for _, ids in batches for i in ids], [t.decision_id for t in traces])
        for prompt, ids in batches:
            self.assertLessEqual(len(prompt.encode("utf-8")), MAX_PROMPT_BYTES)
            evidence = json.loads(prompt.split("Deterministic evidence:\n")[1].split("\n\nReturn")[0])
            self.assertEqual({item["decision_id"] for item in evidence["deterministic_review_items"]}, set(ids))

    def test_oversized_evidence_and_timeout_do_not_return_partial_findings(self):
        huge = replace(self.trace, account_name="x" * MAX_PROMPT_BYTES)
        transport = FakeTransport(_response(self.payload))
        with self.assertRaisesRegex(AIReviewProviderError, "exceeds"):
            OllamaShadowReviewProvider(transport).review(self.result, [huge])
        with self.assertRaisesRegex(AIReviewProviderError, "timed out"):
            OllamaShadowReviewProvider(transport, timeout_seconds=0).review(self.result, [self.trace])
        self.assertEqual(transport.calls, [])

    def test_local_transport_rejects_remote_urls_and_redirects(self):
        for url in ("https://ollama.com/api/chat", "http://localhost.example.com:11434/api/chat"):
            with self.assertRaises(AIReviewProviderError):
                LocalJsonTransport().post_json(url, headers={}, payload={}, timeout_seconds=1)
        with self.assertRaisesRegex(AIReviewProviderError, "redirect"):
            _RejectRedirects().redirect_request(None, None, 302, "", {}, "https://example.com")

    def test_local_transport_bypasses_environment_proxies(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{}'
        with patch("ai_review.http_transport.urllib.request.build_opener", return_value=opener) as build:
            LocalJsonTransport().post_json(LOCAL_CHAT_URL, headers={}, payload={}, timeout_seconds=1)
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], _RejectRedirects)

    def test_frontend_local_review_needs_no_key_and_records_prompt_version(self):
        with patch("frontend.ai_shadow_review.LocalJsonTransport", return_value=FakeTransport(_response(self.payload))):
            response = run_ai_shadow_review(
                workpaper_result=self.result, ai_provider=LOCAL_PROVIDER_NAME,
                api_key="", model=DEFAULT_LOCAL_MODEL,
            )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["prompt_version"], LOCAL_REVIEW_PROMPT_VERSION)

    def test_review_failure_preserves_generated_workbook_and_audit(self):
        before = []

        def unavailable(provider, result, traces):
            before.append(hashlib.sha256(Path(result.output_path).read_bytes()).hexdigest())
            raise AIReviewProviderError("Synthetic unavailable server")

        with TemporaryDirectory() as folder:
            root = Path(folder)
            with (
                patch.object(job_runner, "JOBS_DIR", root / "jobs"),
                patch.object(job_runner, "DOWNLOADS_DIR", root / "downloads"),
                patch.object(OllamaShadowReviewProvider, "review", unavailable),
            ):
                result = job_runner.run_workpaper_job(
                    extra_files=[_combined_workbook()], ato_policy_year="2026",
                    run_ai_face_check=True, ai_provider=LOCAL_PROVIDER_NAME,
                    ai_model=DEFAULT_LOCAL_MODEL,
                )
            self.assertEqual(result["status"], "success", result.get("error_message"))
            self.assertEqual(result["ai_face_check"]["status"], "error")
            self.assertEqual(hashlib.sha256(Path(result["output_path"]).read_bytes()).hexdigest(), before[0])
            audit = read_ai_review_audit(result["ai_review_audit_path"])
            self.assertEqual(audit["provider"]["name"], LOCAL_PROVIDER_NAME)
            self.assertEqual(audit["response"]["status"], "error")
            self.assertEqual(audit["review_contract"]["prompt_version"], LOCAL_REVIEW_PROMPT_VERSION)

    def test_generator_offers_local_review_without_an_api_key(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "frontend/app.py"))
        app.session_state["generator_stage"] = "review"
        app.session_state["scan_result"] = {"profile": {"ato_policy_year": "2026"}}
        app.run(timeout=15)
        self.assertFalse(app.exception)
        checkbox = app.checkbox(key="stage2_local_ai_review")
        self.assertFalse(checkbox.value)
        checkbox.check().run(timeout=15)
        self.assertFalse(app.exception)
        self.assertTrue(app.checkbox(key="stage2_local_ai_review").value)
        self.assertTrue(any(DEFAULT_LOCAL_MODEL in caption.value for caption in app.caption))


if __name__ == "__main__":
    unittest.main()
