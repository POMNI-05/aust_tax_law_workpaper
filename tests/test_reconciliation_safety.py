from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from backend.workpaper_builder import (
    _auto_reconciliation_rows_from_labelled_pl,
    _build_proposed_adjustments,
    _build_tax_reconciliation,
    _build_tax_reconciliation_review_checks,
    _build_tax_depreciation_review_item,
    _tax_depreciation_reconciliation_rows,
    _unapproved_reconciliation_rows_from_labelled_pl,
)
from backend.labeller import label_report


class ReconciliationSafetyTests(unittest.TestCase):
    def _labelled_row(self, **updates):
        row = {
            "Account Label": "Entertainment",
            "Row Type": "account",
            "2026": 120.0,
            "ITR Ref": "Exp - 6S",
            "Recon ITR Ref": "7W",
            "Recon Display Ref": "7W",
            "Recon Direction": "add",
            "Treatment": "review_only",
            "Confidence": "medium",
            "Review Note": "Confirm deductibility and FBT treatment.",
            "Auto Post": "",
            "Draft Eligible": True,
            "Source Row": 12,
            "Rule ID": "synthetic-entertainment-rule",
            "Matched Pattern": r"\bentertainment\b",
        }
        row.update(updates)
        return pd.DataFrame([row])

    def test_review_only_rule_is_proposed_but_not_posted(self):
        labelled = self._labelled_row()

        add_rows, subtract_rows, add_totals, subtract_totals = (
            _auto_reconciliation_rows_from_labelled_pl(labelled, ["2026"])
        )
        proposals = _build_proposed_adjustments(labelled, ["2026"])

        self.assertEqual(add_rows, [])
        self.assertEqual(subtract_rows, [])
        self.assertEqual(add_totals["2026"], 0.0)
        self.assertEqual(subtract_totals["2026"], 0.0)
        self.assertEqual(proposals.loc[0, "Draft Status"], "Proposed — included in preliminary draft")
        self.assertTrue(proposals.loc[0, "Draft Eligible"])

    def test_explicit_approval_posts_and_preserves_negative_sign(self):
        labelled = self._labelled_row(**{"2026": -35.0, "Auto Post": "Approved"})

        add_rows, _, add_totals, _ = _auto_reconciliation_rows_from_labelled_pl(
            labelled,
            ["2026"],
        )

        self.assertEqual(add_rows[0]["2026"], -35.0)
        self.assertEqual(add_totals["2026"], -35.0)

    def test_account_override_cannot_enable_draft_eligibility(self):
        source = pd.DataFrame({
            "Account": ["Donation"],
            "2026": [40.0],
            "Row Type": ["account"],
            "Report Section": ["Expenses"],
        })
        override = {
            "enabled": True,
            "name": "synthetic override",
            "account_pattern": "Donation",
            "match_type": "contains",
            "report_type": "profit_and_loss",
            "set": {"Draft Eligible": True},
        }

        with patch("backend.labeller.load_overrides", return_value=[override]):
            labelled = label_report(source, "profit_and_loss")

        self.assertFalse(bool(labelled.loc[0, "Draft Eligible"]))

    def test_override_cannot_reuse_entertainment_eligibility_for_another_route(self):
        source = pd.DataFrame({
            "Account": ["Entertainment"], "2026": [100.0],
            "Row Type": ["account"], "Report Section": ["Expenses"], "Source Row": [8],
        })
        override = {
            "enabled": True, "account_pattern": "Entertainment", "match_type": "exact",
            "set": {"Recon ITR Ref": "7X", "Recon Display Ref": "7X", "Recon Direction": "subtract"},
        }
        with patch("backend.labeller.load_overrides", return_value=[override]):
            labelled = label_report(source, "profit_and_loss")
        self.assertEqual(labelled.loc[0, "Recon ITR Ref"], "7X")
        self.assertFalse(bool(labelled.loc[0, "Draft Eligible"]))

    def test_invalid_parse_status_is_not_substituted_with_zero(self):
        labelled = self._labelled_row(**{"2026": 100.0, "2026 Parse Status": "invalid"})
        with self.assertRaisesRegex(ValueError, "CELL-002"):
            _unapproved_reconciliation_rows_from_labelled_pl(labelled, ["2026"])

    def test_missing_amount_or_rule_evidence_does_not_create_a_draft_adjustment(self):
        missing_amount = self._labelled_row(**{"2026": None})
        self.assertEqual(_unapproved_reconciliation_rows_from_labelled_pl(missing_amount, ["2026"]), [])
        self.assertFalse(bool(_build_proposed_adjustments(missing_amount, ["2026"]).iloc[0]["Draft Eligible"]))
        self.assertTrue(pd.isna(_build_proposed_adjustments(missing_amount, ["2026"]).iloc[0]["2026"]))
        missing_rule = self._labelled_row(**{"Rule ID": ""})
        candidate = _unapproved_reconciliation_rows_from_labelled_pl(missing_rule, ["2026"])[0]
        self.assertFalse(candidate["_Draft eligible"])
        self.assertEqual(candidate["2026"], 120)

    def test_information_only_build_to_rent_label_never_posts(self):
        labelled = self._labelled_row(
            **{
                "Account Label": "Build to rent capital works",
                "Recon ITR Ref": "7Y",
                "Recon Display Ref": "7Y",
                "Recon Direction": "information_only",
                "Auto Post": "Approved",
            }
        )

        add_rows, subtract_rows, add_totals, subtract_totals = (
            _auto_reconciliation_rows_from_labelled_pl(labelled, ["2026"])
        )

        self.assertEqual(add_rows, [])
        self.assertEqual(subtract_rows, [])
        self.assertEqual(add_totals["2026"], 0.0)
        self.assertEqual(subtract_totals["2026"], 0.0)

    def test_rd_offset_is_absent_without_a_reviewed_rd_claim(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Net Profit"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )
        reconciliation = _build_tax_reconciliation(clean_pl, pd.DataFrame())

        self.assertNotIn("R&D offset", reconciliation["Description"].tolist())
        self.assertNotIn("No add-back entries identified", reconciliation["Description"].tolist())
        self.assertNotIn("No subtraction entries identified", reconciliation["Description"].tolist())
        self.assertEqual(
            reconciliation["Description"].tolist(),
            [
                "Accounting profit/(loss) — Item 6T",
                "Preliminary draft taxable income/(loss) — Item 7T (unverified)",
            ],
        )

    def test_depreciation_number_is_a_draft_proposal_without_approval(self):
        not_posted, _ = _tax_depreciation_reconciliation_rows(
            ["2026"],
            reviewed_tax_depreciation_total=125.0,
            approved_for_posting=False,
        )
        posted, totals = _tax_depreciation_reconciliation_rows(
            ["2026"],
            reviewed_tax_depreciation_total=125.0,
            approved_for_posting=True,
        )

        self.assertEqual(not_posted[0]["Line Type"], "proposal")
        self.assertEqual(not_posted[0]["2026"], 125.0)
        self.assertEqual(posted[0]["ITR Ref"], "7F")
        self.assertEqual(posted[0]["2026"], 125.0)
        self.assertEqual(totals["2026"], 125.0)

    def test_matching_tax_law_depreciation_schedule_is_in_preliminary_draft(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Profit Before Tax"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )

        reconciliation = _build_tax_reconciliation(
            clean_pl,
            pd.DataFrame(),
            tax_depreciation_total=25.0,
            tax_depreciation_source="tax-depreciation.xlsx :: Schedule",
            tax_depreciation_matches_selected_period=True,
        )

        schedule_row = reconciliation[
            reconciliation["Description"].eq("Tax depreciation / decline in value")
        ].iloc[0]
        self.assertEqual(schedule_row["ITR Ref"], "7F")
        self.assertEqual(schedule_row["2026"], 25.0)
        self.assertEqual(schedule_row["Line Type"], "proposal")
        self.assertIn("verify asset eligibility", schedule_row["Review note"])
        self.assertEqual(
            reconciliation[reconciliation["Description"].eq("Total SUBTRACT")].iloc[0]["2026"],
            25.0,
        )
        result = reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]
        self.assertEqual(result["2026"], 75.0)

    def test_wrong_year_or_zero_tax_depreciation_schedule_is_not_used(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Profit Before Tax"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )

        for amount, matches, source in (
            (25.0, False, "schedule.xlsx :: FY2025"),
            (0.0, True, "schedule.xlsx :: FY2026"),
            (None, True, "schedule.xlsx :: FY2026"),
            (25.0, True, None),
        ):
            with self.subTest(amount=amount, matches=matches, source=source):
                reconciliation = _build_tax_reconciliation(
                    clean_pl, pd.DataFrame(), tax_depreciation_total=amount,
                    tax_depreciation_source=source,
                    tax_depreciation_matches_selected_period=matches,
                )
                self.assertNotIn("SUBTRACT", reconciliation["Description"].tolist())
                self.assertEqual(reconciliation.iloc[-1]["2026"], 100.0)

    def test_unapproved_entertainment_add_back_is_in_unverified_draft_7t(self):
        labelled = self._labelled_row(**{"2026": 277.20})
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Net Profit"],
                "2026": [-8134.45],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )

        candidates = _unapproved_reconciliation_rows_from_labelled_pl(labelled, ["2026"])
        reconciliation = _build_tax_reconciliation(clean_pl, labelled)

        self.assertEqual(candidates[0]["2026"], 277.20)
        self.assertEqual(candidates[0]["Description"], "Entertainment")
        self.assertIn("full source account balance", candidates[0]["_Draft assumption"])
        self.assertIn("Total ADD", reconciliation["Description"].tolist())
        self.assertIn("PRELIMINARY DRAFT", reconciliation.iloc[-1]["Description"].upper())
        taxable_row = reconciliation[
            reconciliation["Description"].eq("Preliminary draft taxable income/(loss) — Item 7T (unverified)")
        ].iloc[0]
        self.assertEqual(taxable_row["2026"], -7857.25)
        self.assertEqual(taxable_row["ITR Ref"], "7T (preliminary)")
        proposal = reconciliation[reconciliation["Description"].eq("Entertainment")].iloc[0]
        self.assertEqual(proposal["Line Type"], "proposal")
        self.assertEqual(proposal["2026"], 277.20)

    def test_unconfigured_rule_is_visible_but_excluded_from_draft_total(self):
        labelled = self._labelled_row(**{"Draft Eligible": False, "2026": 50.0})
        clean_pl = pd.DataFrame({
            "Account Label": ["Profit Before Tax"],
            "2026": [100.0],
            "Row Type": ["total"],
            "Report Section": [""],
        })

        reconciliation = _build_tax_reconciliation(clean_pl, labelled)
        result = reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]

        self.assertEqual(result["2026"], 100.0)
        self.assertIn("UNRESOLVED ADJUSTMENTS — EXCLUDED FROM DRAFT ITEM 7T", reconciliation["Description"].tolist())
        self.assertEqual(reconciliation[reconciliation["Description"].eq("Entertainment")].iloc[0]["2026"], 50.0)

    def test_draft_eligible_rule_without_source_row_is_not_calculated(self):
        labelled = self._labelled_row(**{"Source Row": "", "2026": 50.0})
        clean_pl = pd.DataFrame({
            "Account Label": ["Profit Before Tax"],
            "2026": [100.0],
            "Row Type": ["total"],
            "Report Section": [""],
        })

        reconciliation = _build_tax_reconciliation(clean_pl, labelled)
        result = reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]

        self.assertEqual(result["2026"], 100.0)
        self.assertIn("UNRESOLVED ADJUSTMENTS — EXCLUDED FROM DRAFT ITEM 7T", reconciliation["Description"].tolist())

    def test_pending_adjustments_are_grouped_by_direction(self):
        add_back = self._labelled_row(**{"2026": 20.0})
        deduction = self._labelled_row(**{
            "Account Label": "Tax depreciation",
            "2026": 25.0,
            "Recon ITR Ref": "7F",
            "Recon Display Ref": "7F",
            "Recon Direction": "subtract",
            "Draft Eligible": False,
            "Source Row": 13,
        })
        clean_pl = pd.DataFrame({
            "Account Label": ["Net Profit"],
            "2026": [100.0],
            "Row Type": ["total"],
            "Report Section": [""],
        })

        reconciliation = _build_tax_reconciliation(
            clean_pl,
            pd.concat([add_back, deduction], ignore_index=True),
        )

        self.assertIn("ADD", reconciliation["Description"].tolist())
        self.assertNotIn("SUBTRACT", reconciliation["Description"].tolist())
        self.assertEqual(reconciliation[reconciliation["Description"].eq("Total ADD")].iloc[0]["2026"], 20.0)
        preliminary = reconciliation[
            reconciliation["ITR Ref"].eq("7T (preliminary)")
        ].iloc[0]
        self.assertEqual(preliminary["2026"], 120.0)

    def test_explicit_profit_before_tax_can_produce_item_7t_and_loss_code(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Profit Before Tax"],
                "2026": [-50.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )

        reconciliation = _build_tax_reconciliation(clean_pl, pd.DataFrame())
        result_row = reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]

        self.assertEqual(
            result_row["Description"],
            "Preliminary draft taxable income/(loss) — Item 7T (unverified)",
        )
        self.assertEqual(result_row["Tax return code"], "L (preliminary)")
        self.assertNotIn("No add-back entries identified", reconciliation["Description"].tolist())

    def test_approved_adjustment_remains_in_preliminary_workpaper(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Profit Before Tax"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )
        labelled = self._labelled_row(**{"2026": 20.0, "Auto Post": "Approved"})

        reconciliation = _build_tax_reconciliation(clean_pl, labelled)
        result_row = reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]

        self.assertEqual(result_row["Description"], "Preliminary draft taxable income/(loss) — Item 7T (unverified)")
        self.assertEqual(result_row["2026"], 120.0)

    def test_approved_depreciation_override_does_not_duplicate_detected_schedule(self):
        clean_pl = pd.DataFrame({
            "Account Label": ["Profit Before Tax"],
            "2026": [100.0],
            "Row Type": ["total"],
            "Report Section": [""],
        })
        reconciliation = _build_tax_reconciliation(
            clean_pl,
            pd.DataFrame(),
            tax_depreciation_total=25.0,
            tax_depreciation_source="synthetic-schedule.xlsx :: Schedule",
            tax_depreciation_matches_selected_period=True,
            reviewed_tax_depreciation_total=25.0,
            tax_depreciation_approved_for_posting=True,
        )

        posted = reconciliation[
            reconciliation["Description"].eq("Tax depreciation / decline in value")
        ]
        self.assertEqual(len(posted), 1)
        self.assertEqual(posted.iloc[0]["2026"], 25.0)
        self.assertNotIn(
            "PROPOSED ADJUSTMENTS — EXCLUDED FROM APPROVED-ONLY ITEM 7T",
            reconciliation["Description"].tolist(),
        )

    def test_entered_depreciation_replaces_schedule_without_approval_including_zero(self):
        clean_pl = pd.DataFrame({
            "Account Label": ["Profit Before Tax"], "2026": [100.0],
            "Row Type": ["total"], "Report Section": [""],
        })
        for amount in (30.0, 0.0):
            for approved in (False, True):
                with self.subTest(amount=amount, approved=approved):
                    reconciliation = _build_tax_reconciliation(
                        clean_pl, pd.DataFrame(), tax_depreciation_total=25.0,
                        tax_depreciation_source="schedule.xlsx :: Schedule",
                        tax_depreciation_matches_selected_period=True,
                        reviewed_tax_depreciation_total=amount,
                        tax_depreciation_approved_for_posting=approved,
                    )
                    rows = reconciliation[reconciliation["ITR Ref"].eq("7F")]
                    self.assertEqual(len(rows), 1 if amount else 0)
                    self.assertEqual(reconciliation.iloc[-1]["2026"], 100 - amount)

    def test_depreciation_review_uses_actual_entered_amount_and_explains_precedence(self):
        reports = SimpleNamespace(
            tax_depreciation_total=25.0,
            tax_depreciation_matches_selected_period=True,
            tax_depreciation_source="schedule.xlsx :: Schedule",
        )
        for amount in (30.0, 0.0):
            row = _build_tax_depreciation_review_item(reports, amount).iloc[0]
            self.assertIn(f"{amount:,.2f}", row["Draft Amount"])
            self.assertIn("replaces", row["Review Note"])
            self.assertEqual(row["Rule ID"], "draft-tax-depreciation-input-v1")
            self.assertIn("25.0", row["Reason"])
            if not amount:
                self.assertEqual(row["Draft Status"], "Review-only — excluded")

    def test_repeated_source_rows_and_repeated_calculation_do_not_duplicate_adjustments(self):
        clean_pl = pd.DataFrame({
            "Account Label": ["Profit Before Tax"], "2026": [100.0],
            "Row Type": ["total"], "Report Section": [""],
        })
        for approved in ("", "Approved"):
            source = self._labelled_row(**{"Auto Post": approved})
            duplicate = pd.concat([source, source], ignore_index=True)
            first = _build_tax_reconciliation(clean_pl, duplicate)
            second = _build_tax_reconciliation(clean_pl, duplicate)
            pd.testing.assert_frame_equal(first, second)
            self.assertEqual(first["Description"].eq("Entertainment").sum(), 1)
            self.assertEqual(first.iloc[-1]["2026"], 220)

        conflicting = pd.concat([source, self._labelled_row(**{"2026": 200.0})], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "RECON-001"):
            _build_tax_reconciliation(clean_pl, conflicting)

    def test_company_tax_precalculation_is_not_shown_on_minimal_tab_3(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Profit Before Tax"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )
        reconciliation = _build_tax_reconciliation(clean_pl, pd.DataFrame())

        with (
            patch("backend.workpaper_builder.TAX_RATE", 0.30),
            patch("backend.workpaper_builder.COMPANY_TAX_RATE_CATEGORY", "general"),
        ):
            reconciliation = _build_tax_reconciliation(clean_pl, pd.DataFrame())

        self.assertNotIn(
            "Indicative company tax before offsets — rate 30%",
            reconciliation["Description"].tolist(),
        )

    def test_plain_net_profit_keeps_item_7t_preliminary_until_base_is_confirmed(self):
        clean_pl = pd.DataFrame(
            {
                "Account Label": ["Net Profit"],
                "2026": [100.0],
                "Row Type": ["total"],
                "Report Section": [""],
            }
        )

        reconciliation = _build_tax_reconciliation(clean_pl, pd.DataFrame())
        review_checks = _build_tax_reconciliation_review_checks(
            clean_pl,
            pd.DataFrame(),
        )

        self.assertNotIn(
            "Item 6T base: confirm Net Profit excludes income tax expense",
            reconciliation["Description"].tolist(),
        )
        self.assertIn(
            "Item 6T base: confirm Net Profit excludes income tax expense",
            review_checks["Check"].tolist(),
        )
        self.assertEqual(
            reconciliation[reconciliation["ITR Ref"].eq("7T (preliminary)")].iloc[0]["Description"],
            "Preliminary draft taxable income/(loss) — Item 7T (unverified)",
        )


if __name__ == "__main__":
    unittest.main()
