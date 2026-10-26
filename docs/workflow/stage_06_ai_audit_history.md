# Stage 6 — AI review, audit and history

## Purpose

Optional local Ollama and Gemini/Grok adapters review minimised deterministic evidence after the
workbook exists. The result is display-only and is stored with a local audit
sidecar; Streamlit history displays the workbook, metadata and review record.

## Inputs and outputs

- Input: completed `WorkpaperResult`, `DecisionTrace` records and an explicitly
  selected provider (API keys apply only to cloud providers).
- Output: schema-validated `AiReview` and `<workpaper>.ai_review_audit.json`.

## Issue/debugging log

| State | Issue | Diagnosis and safe resolution |
| --- | --- | --- |
| Resolved | The staged generator hardcoded AI review off and had no local provider. | Added an optional local Ollama checkbox, fixed-loopback transport, bounded schema-validated evidence batches and immediate model unloading. The result displays the existing audit/disposition controls. All 124 tests pass, including live-generator UI and workbook-hash failure-isolation regressions. Setup and shared-Mac resource limits are in [local review notes](../local_ai_review.md). |
| Validated | Live local review trial on Apple M5/16 GB, 27 October 2026. | Six synthetic decisions reviewed in 10.7 seconds of inference (11.6 seconds overall); two generic schema-valid reminders. Sampled model allocation about 1.78 GiB. Workbook hash unchanged, model unloaded, and temporary server stopped. This is integration evidence, not a tax-quality or shared-workload benchmark. |
| Resolved | Provider-specific logic could leak into business code. | Gemini and Grok implement one review interface and strict schema validation. |
| Resolved | AI findings lacked a reviewer outcome. | Audit sidecar stores provider/model, prompt/schema versions, input hash, response status and accountant disposition. |
| Guardrail | Invalid/malformed AI output. | Reject it; do not display or apply it. The workbook remains unchanged. |

## Debug procedure

1. Confirm the workpaper result is completed and has decision traces.
2. Inspect the audit sidecar, never an API key or raw workbook payload.
3. Run `python -m unittest tests.test_ai_review_contract tests.test_ai_review_providers tests.test_ai_review_audit -v`.
4. Read [AI review data handling](../ai_review_data_handling.md) before using a
   real client file with an external provider.
