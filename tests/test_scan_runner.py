from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from backend import cleaner, scan_workbooks
from frontend import scan_runner


class ScanRunnerTests(unittest.TestCase):
    def test_scan_observation_amount_uses_selected_period_not_first_numeric_column(self):
        frame = pd.DataFrame({
            "Account Label": ["Entertainment"],
            "30 Jun 2026": [100.0],
            "30 Jun 2025": [80.0],
            "Row Type": ["account"],
            "Report Section": ["Operating Expenses"],
            "Source Row": [8],
        })

        with patch.object(cleaner, "SELECTED_INCOME_YEAR", "2025"):
            self.assertEqual(scan_workbooks._amount_column(frame), "30 Jun 2025")

        frame = frame.drop(columns=["30 Jun 2025"])
        with patch.object(cleaner, "SELECTED_INCOME_YEAR", "2024"):
            self.assertIsNone(scan_workbooks._amount_column(frame))

        generic = frame.rename(columns={"30 Jun 2026": "Amount"})
        with patch.object(cleaner, "SELECTED_INCOME_YEAR", "2024"):
            self.assertEqual(scan_workbooks._amount_column(generic), "Amount")

    def test_scan_passes_selected_income_year_to_backend_subprocess(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            captured: dict[str, str] = {}

            def fake_run(_args, **kwargs):
                captured.update(
                    {
                        key: kwargs["env"][key]
                        for key in (
                            "SELECTED_INCOME_YEAR",
                            "ATO_POLICY_YEAR",
                            "ITR_POLICY_YEAR",
                        )
                    }
                )
                result_path = Path(kwargs["env"]["TAX_SCAN_RESULT_PATH"])
                result_path.write_text(
                    json.dumps({
                        "status": "success",
                        "scan_id": kwargs["env"]["TAX_SCAN_ID"],
                        "source_file_hashes": json.loads(
                            kwargs["env"]["TAX_SCAN_SOURCE_HASHES"]
                        ),
                    }),
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            upload = io.BytesIO(b"synthetic workbook bytes")
            upload.name = "synthetic.xlsx"
            with (
                patch.object(scan_runner, "SCAN_JOBS_DIR", root / "scans"),
                patch.object(scan_runner.subprocess, "run", side_effect=fake_run),
            ):
                result = scan_runner.run_scan_job(
                    uploaded_files=[upload],
                    profile={"ato_policy_year": "2025"},
                )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["selected_income_year"], "2025")
            self.assertEqual(
                captured,
                {
                    "SELECTED_INCOME_YEAR": "2025",
                    "ATO_POLICY_YEAR": "2025",
                    "ITR_POLICY_YEAR": "2025",
                },
            )
            scan_runner.cleanup_scan(result)

    def test_unsupported_scan_year_fails_before_subprocess_or_file_write(self):
        upload = io.BytesIO(b"synthetic workbook bytes")
        with patch.object(scan_runner.subprocess, "run") as run:
            result = scan_runner.run_scan_job(
                uploaded_files=[upload],
                profile={"ato_policy_year": "2027"},
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["selected_income_year"], "2027")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
