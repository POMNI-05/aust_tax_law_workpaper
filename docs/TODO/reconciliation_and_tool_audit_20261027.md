# Reconciliation safety and tool-integration audit — 27 October 2026

## Task plan

### Git checkpoint preparation — complete

- Reviewed the current draft-reconciliation, annotation, financial-year and
  regression changes as one checkpoint before starting evidence-review work.
- Pre-commit validation: 138 tests and 27 subtests passed; `git diff --check`
  passed. Commit identity is `ICGTAX Intern`; destination is `origin/main`.
- Scope is source, synthetic tests and project documentation. Evidence
  Register, cross-document tie-outs, new Skills and MCP integration remain
  proposed future work. The publication result is recorded by Git history and
  the user-facing push confirmation.

### Draft workflow follow-up — complete

1. **Inspect current diff — complete.** Retain the single draft calculation,
   explicit rule eligibility, preliminary result labels, year propagation and
   depreciation precedence. Current review items are a section on Checks;
   a dedicated consolidated worksheet and complete cell Notes remain needed.
2. **Close annotation/integrity gaps — complete.** Create the Review Items
   worksheet, include source account and cell amount in saved Notes, describe
   actual depreciation precedence, and preserve rule eligibility only for its
   configured adjustment route. Reject invalid parsed amounts rather than
   representing them as zero.
3. **Validate generated output — complete.** Extend synthetic regressions for
   Notes/review consolidation, unsupported amounts, depreciation precedence,
   no repeated source postings, and real selected-year Scan → Generation.
   Run focused and full suites and inspect generated XLSX formulas and Notes.

**Stage outcome:** the dedicated Review Items worksheet now consolidates account,
adjustment, depreciation and reconciliation-completeness reviews. Saved cell
Notes identify source account/adjustment, period, amount, rule, assumption and
review steps. Rule eligibility does not survive a route-changing override;
invalid amounts fail validation and missing amounts remain blank. Identical
source-row copies calculate once, conflicting copies stop, and depreciation
review notes describe the entered amount's precedence over detected evidence.
The focused reconciliation/Scan/workbook suite passed 38 tests, including actual
FY2025 Scan → Generation with comparative FY2026 data and a matching schedule.
Full suite: **138 tests and 27 subtests passed**. `git diff --check` passed.
Reloaded XLSX assertions confirm the `$100` Entertainment proposal participates
in its SUM/7T formula and its full Note is saved. The comparative case confirms
FY2025 base `$880` plus Entertainment `$80` less schedule `$25`; Donations `$40`
is displayed after the result and excluded from both subtotal formula ranges.
No Excel calculation engine was invoked; tests validate persisted formulas,
inputs and Python reconciliation values, with recalculation requested on open.
Next: review remaining integration risks before MCP development.
Takeaway: review annotations must describe the amount actually selected by
the calculation, including override precedence and explicit zero.

1. **Read-only audit and execution trace — complete.** Inspect the scanner,
   generator, calculators, workbook writer, approval inputs, AI adapters and
   tests. Execute synthetic Scan → Generation → mocked AI review and focused
   existing tests. Record verified behavior separately from code inference.
2. **Reconciliation/year safety patch — superseded.** The initial approved-only
   policy was replaced on 27 October 2026 by the draft-workpaper policy below.
   The financial-year propagation repair remains current.
3. **Draft-workpaper reconciliation policy — complete.** Include only
   explicitly draft-eligible, source-traceable proposals in preliminary Item
   7T; keep unresolved proposals visible and excluded. Annotate calculations
   and review requirements in Excel and retain the depreciation de-duplication
   guard.
4. **Regression/release checks — complete.** Cover the $100 Entertainment
   draft formula, eligible/unresolved boundaries, cell Notes, no double count,
   source/year propagation and scan-to-generation execution.

## Stage 1 result — read-only audit

- Synthetic Scan → Generation → mocked local AI succeeded; source hash matched,
  six decision traces were returned, and an AI audit sidecar was written. No
  model or external AI service was called.
- Focused existing suite: 41 tests passed.
- Synthetic FY2025 depreciation evidence produced a false selected-year warning
  during Scan when the profile selected 2025; Generation used FY2025 correctly.
- The current Entertainment `$100` proposal is included in preliminary Item 7T.
  The standalone Decimal calculator is not called by the workbook path.
- MCP tools are not implemented. Repeat-generation idempotency, durable
  adjustment approval records, and workbook/reconciliation binding are absent.
- **Takeaway:** verify the function call chain and generated formulas, not just
  the existence or isolated tests of a calculator.

## Stage 2 result — initial safety/year fix (proposal policy superseded)

- **Status:** complete.
- **Outcome:** The first patch excluded proposals from the calculation. The
  user later clarified that the product generates drafts and superseded this
  approved-only policy. The Scan selected-year propagation fix remains current.
- **Validation:** The existing accountant-approved depreciation override still
  suppresses a duplicate detected-schedule proposal; a regression confirms one
  7F row. Source rule notes and schedule source references are retained.
- **Next:** Finish release checks and record unresolved audit backlog.
- **Takeaway:** Approval status and calculation membership must be represented
  separately in both workbook rows and formula ranges.

## Stage 3 result — initial approved-only regressions (policy superseded)

- **Status:** complete.
- **Outcome:** Added regression coverage for unapproved Entertainment amounts,
  approved-only Excel formulas, visible excluded proposals, depreciation
  override/schedule de-duplication, selected-year Scan propagation, and
  comparative-period amount selection. Synthetic end-to-end execution used
  FY2025 and FY2026 columns, validated source hashes, produced the workbook,
  and exercised the local-review adapter with a mocked transport.
- **Validation:** Focused suite: 44 tests passed before the final selected-period
  case; final full suite: 128 tests passed. `git diff --check` passed. The final
  synthetic FY2025 Scan had no depreciation-period warning, showed the FY2025
  Entertainment amount, and Generation reported FY2025. The AI mock completed;
  no LLM or external service was called.
- **Next:** Prioritise remaining MCP/security and approval-lineage backlog before
  implementing MCP tools.
- **Takeaway:** A regression should verify values and formula boundaries across
  the complete invocation path, not just a helper's return value.

## Stage 4 result — draft reconciliation policy, 27 October 2026

- **Status:** complete.
- **Outcome:** Draft Item 7T includes source-row-traceable adjustments only when
  the matching rule explicitly sets `Draft Eligible`; Entertainment is the
  configured synthetic example. Matching-year depreciation schedules and
  reviewer-entered depreciation amounts remain preliminary draft proposals,
  with an entered amount suppressing the detected schedule to avoid duplicate
  7F. Other account-name proposals stay visible as unresolved and outside the
  formula. Every generated Item 7T is labelled preliminary/unverified. Source,
  rule, amount assumptions and review requirements appear in Excel Notes,
  Inputs & Overrides and Checks → Review Items.
- **Validation:** focused reconciliation/Scan/end-to-end tests passed. Full
  suite: 131 tests passed. The end-to-end XLSX regression reloads the generated
  workbook and asserts the formula range, `$100` proposal inclusion, and cell
  Note content. `git diff --check` passed. Financial-year propagation and the
  depreciation de-duplication regression remain intact.
- **Next:** prioritize remaining integration and approval-lineage risks before
  implementing MCP tools.
- **Takeaway:** draft eligibility controls whether a traceable amount appears
  in a preliminary formula; it does not establish tax deductibility or the
  correct tax amount.

## Remaining verified/inferred risks

- Draft eligibility means only “include the traceable source amount in a
  preliminary workpaper calculation”; it does not prove deductibility or the
  correct adjustment amount. An accountant must review these assumptions.

- The known depreciation override/schedule duplicate is guarded, but no
  semantic de-duplication exists between a manually configured `TAX_ADJUSTMENTS`
  row and a separately approved source-account adjustment.
- Adjustment approval is not stored as a durable, identity-bound record keyed
  to source hashes, income year, amount and rule version. Free-text labels or
  `Auto Post` values alone are not a suitable MCP approval credential.
- Generation has no idempotency key. Repeated same-client generation within the
  same second can produce the same download name and overwrite the prior file.
- Manual workbook editing creates a new file and cell audit but does not rerun
  deterministic reconciliation. The AI audit binds to minimised decision
  evidence, not the workbook hash.
- The standalone Decimal reconciliation and most calculator functions are not
  connected to `build_workpaper`; see the chat audit for the complete call map
  and proposed MCP rules.
