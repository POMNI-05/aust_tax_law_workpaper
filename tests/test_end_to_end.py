from __future__ import annotations

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

from frontend import job_runner, scan_runner
from ai_review import read_ai_review_audit


def _combined_workbook() -> io.BytesIO:
    workbook = Workbook()
    pl = workbook.active
    pl.title = "Profit and Loss"
    pl.append(["Profit and Loss"])
    pl.append([])
    pl.append(["Account", "30 Jun 2026"])
    pl.append(["Trading Income", None])
    pl.append(["Sales", 1000])
    pl.append(["Total Income", 1000])
    pl.append(["Operating Expenses", None])
    pl.append(["Entertainment", 100])
    pl.append(["Total Operating Expenses", 100])
    pl.append(["Net Profit", 900])

    bs = workbook.create_sheet("Balance Sheet")
    bs.append(["Balance Sheet"])
    bs.append([])
    bs.append(["Account", "30 Jun 2026"])
    bs.append(["Current Assets", None])
    bs.append(["Cash", 1000])
    bs.append(["Total Assets", 1000])
    bs.append(["Current Liabilities", None])
    bs.append(["Loan", 400])
    bs.append(["Total Liabilities", 400])
    bs.append(["Equity", None])
    bs.append(["Retained Earnings", 600])
    bs.append(["Total Equity", 600])
    bs.append(["Net Assets", 600])

    stream = io.BytesIO()
    stream.name = "combined.xlsx"
    workbook.save(stream)
    stream.seek(0)
    return stream


def _comparative_draft_workbook() -> io.BytesIO:
    """Synthetic eligible, review-only and schedule evidence in two years."""
    workbook = load_workbook(_combined_workbook())
    for sheet in workbook:
        sheet.cell(3, 3, "30 Jun 2025")
        for row in sheet.iter_rows(min_row=4):
            if isinstance(row[1].value, (int, float)):
                sheet.cell(row[1].row, 3, row[1].value)
    pl = workbook["Profit and Loss"]
    pl.cell(8, 3, 80)
    pl.insert_rows(9)
    for col, value in enumerate(["Donations", 40, 40], start=1):
        pl.cell(9, col, value)
    pl.cell(10, 2, 140)
    pl.cell(10, 3, 120)
    pl.cell(11, 2, 860)
    pl.cell(11, 3, 880)
    dep = workbook.create_sheet("Tax Depreciation")
    dep.append(["Tax Depreciation Schedule for year ended 30 June 2025"])
    dep.append(["Name", "Cost", "Tax Depreciation", "Closing Value"])
    dep.append(["Synthetic asset", 100, 25, 75])
    dep.append(["Total", 100, 25, 75])
    stream = io.BytesIO()
    stream.name = "comparative-synthetic.xlsx"
    workbook.save(stream)
    stream.seek(0)
    return stream


class EndToEndTests(unittest.TestCase):
    def test_isolated_job_generates_workbook_and_cleans_working_files(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with (
                patch.object(job_runner, "JOBS_DIR", root / "jobs"),
                patch.object(job_runner, "DOWNLOADS_DIR", root / "downloads"),
            ):
                result = job_runner.run_workpaper_job(
                    extra_files=[_combined_workbook()],
                    client_name="Synthetic",
                    ato_policy_year="2026",
                    company_tax_rate_category="general",
                    history_owner_id="test-session",
                    requested_tables={"fbt_entertainment": True},
                )

            self.assertEqual(result["status"], "success", result.get("error_message"))
            self.assertTrue(result["job_cleaned_up"])
            self.assertFalse((root / "jobs" / result["job_id"]).exists())
            self.assertEqual(result["workpaper_result"]["status"], "completed")
            self.assertGreater(result["workpaper_result"]["decision_trace_count"], 0)

            output = Path(result["output_path"])
            self.assertTrue(output.exists())
            self.assertEqual(output.parent.name, "test-session")
            audit = read_ai_review_audit(result["ai_review_audit_path"])
            self.assertEqual(audit["response"]["status"], "skipped")
            self.assertEqual(audit["provider"]["name"], "None")
            self.assertEqual(audit["accountant_disposition"]["status"], "pending")

            workbook = load_workbook(output, data_only=False)
            self.assertIn("Tax Reconciliation", workbook.sheetnames)
            self.assertNotIn("Tax Calculation", workbook.sheetnames)
            self.assertIn("Inputs & Overrides", workbook.sheetnames)
            recon_values = [
                cell.value for row in workbook["Tax Reconciliation"] for cell in row
            ]
            checks_values = [
                cell.value for row in workbook["Checks"] for cell in row
            ]
            self.assertIn("Review Items", workbook.sheetnames)
            review_values = [cell.value for row in workbook["Review Items"] for cell in row]
            input_values = [
                cell.value for row in workbook["Inputs & Overrides"] for cell in row
            ]
            self.assertIn(
                "Draft Tax Adjustment Proposals — Review Required",
                input_values,
            )
            self.assertIn("FBT / Entertainment Review", input_values)
            self.assertIn(
                "Preliminary draft taxable income/(loss) — Item 7T (unverified)",
                recon_values,
            )
            # Net profit is 900. The configured Entertainment proposal is
            # included in draft 7T, but is clearly unverified and annotated.
            recon_sheet = workbook["Tax Reconciliation"]
            base_row = next(
                row[0].row for row in recon_sheet.iter_rows()
                if row[0].value == "Accounting profit/(loss) — Item 6T"
            )
            result_row = next(
                row[0].row for row in recon_sheet.iter_rows()
                if row[0].value == "Preliminary draft taxable income/(loss) — Item 7T (unverified)"
            )
            proposal_row = next(
                row[0].row for row in recon_sheet.iter_rows()
                if row[0].value == "Entertainment"
            )
            self.assertEqual(recon_sheet.cell(proposal_row, 2).value, 100)
            add_total_row = next(
                row[0].row for row in recon_sheet.iter_rows()
                if row[0].value == "Total ADD"
            )
            self.assertEqual(recon_sheet.cell(add_total_row, 2).value, f"=SUM(B5:B{add_total_row - 1})")
            self.assertEqual(
                recon_sheet.cell(result_row, 2).value,
                f"=B{base_row}+B{add_total_row}-0",
            )
            self.assertLess(proposal_row, add_total_row)
            self.assertIsNotNone(recon_sheet.cell(proposal_row, 2).comment)
            self.assertIn("NOT VERIFIED", recon_sheet.cell(proposal_row, 2).comment.text)
            for evidence in ("Entertainment", "100.00", "01_combined.xlsx", "Source row 8", "itr-rule-", "full source account balance", "FBT"):
                self.assertIn(evidence, recon_sheet.cell(proposal_row, 2).comment.text)
            self.assertEqual(recon_sheet.cell(proposal_row, 2).fill.fill_type, "solid")
            self.assertNotIn(300, recon_values)
            self.assertNotIn("Completeness checks — not tax adjustments", recon_values)
            self.assertNotIn("Review Items", checks_values)
            self.assertIn("Completeness checks", review_values)
            self.assertIn("Draft Status", review_values)
            self.assertIn("Proposed — included in draft", review_values)
            self.assertEqual(workbook.calculation.calcMode, "auto")

            balance_sheet = workbook["Balance Sheet"]
            self.assertNotIn(
                "Tab 3 decision",
                [cell.value for row in balance_sheet.iter_rows() for cell in row],
            )

    def test_real_scan_to_annotated_draft_uses_selected_year_and_supported_amounts(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with (
                patch.object(scan_runner, "SCAN_JOBS_DIR", root / "scans"),
                patch.object(job_runner, "JOBS_DIR", root / "jobs"),
                patch.object(job_runner, "DOWNLOADS_DIR", root / "downloads"),
            ):
                scan = scan_runner.run_scan_job(
                    uploaded_files=[_comparative_draft_workbook()],
                    profile={"ato_policy_year": "2025"},
                )
                self.assertEqual(scan["status"], "success", scan.get("error_message"))
                self.assertEqual(scan["selected_income_year"], "2025")
                self.assertEqual(scan_runner.verify_scan_sources(scan), (True, []))
                entertainment = next(item for item in scan["observations"] if item["account"] == "Entertainment")
                self.assertEqual(entertainment["amount"], 80)
                self.assertFalse(scan["warnings"], scan["warnings"])

                sources = scan_runner.open_scan_source_files(scan)
                try:
                    result = job_runner.run_workpaper_job(
                        extra_files=sources,
                        client_name="Synthetic Draft 2025",
                        ato_policy_year="2025",
                        requested_tables={"depreciation": True, "fbt_entertainment": True},
                        history_owner_id="test-session",
                    )
                finally:
                    for source in sources:
                        source.close()
                    scan_runner.cleanup_scan(scan)

            self.assertEqual(result["status"], "success", result.get("error_message"))
            self.assertEqual(result["workpaper_result"]["income_year"], "2025")
            workbook = load_workbook(result["output_path"], data_only=False)
            recon = workbook["Tax Reconciliation"]
            headers = {cell.value: cell.column for cell in recon[2]}
            period_col = headers["Year Ended 30 June 2025"]
            rows = {row[0].value: row[0].row for row in recon.iter_rows(min_row=3)}
            letter = recon.cell(2, period_col).column_letter
            self.assertEqual(recon.cell(rows["Accounting profit/(loss) — Item 6T"], period_col).value, 880)
            self.assertEqual(recon.cell(rows["Entertainment"], period_col).value, 80)
            self.assertEqual(recon.cell(rows["Tax depreciation / decline in value"], period_col).value, 25)
            self.assertEqual(recon.cell(rows["Donations"], period_col).value, 40)
            result_row = rows["Preliminary draft taxable income/(loss) — Item 7T (unverified)"]
            self.assertGreater(rows["Donations"], result_row)
            self.assertEqual(
                recon.cell(rows["Total ADD"], period_col).value,
                f"=SUM({letter}{rows['ADD'] + 1}:{letter}{rows['Total ADD'] - 1})",
            )
            self.assertEqual(
                recon.cell(rows["Total SUBTRACT"], period_col).value,
                f"=SUM({letter}{rows['SUBTRACT'] + 1}:{letter}{rows['Total SUBTRACT'] - 1})",
            )
            self.assertEqual(
                recon.cell(result_row, period_col).value,
                f"={letter}{rows['Accounting profit/(loss) — Item 6T']}+{letter}{rows['Total ADD']}-{letter}{rows['Total SUBTRACT']}",
            )
            for account in ("Entertainment", "Tax depreciation / decline in value", "Donations"):
                self.assertIsNotNone(recon.cell(rows[account], period_col).comment)
            self.assertIn("EXCLUDED", recon.cell(rows["Donations"], period_col).comment.text)
            self.assertIn("draft-tax-depreciation-schedule-v1", recon.cell(rows["Tax depreciation / decline in value"], period_col).comment.text)
            reviews = [cell.value for row in workbook["Review Items"] for cell in row]
            for finding in ("Proposed — included in draft", "Unresolved — excluded", "Donations", "draft-tax-depreciation-schedule-v1", "2025: 25.00"):
                self.assertIn(finding, reviews)


if __name__ == "__main__":
    unittest.main()
