from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from uese.core.naheulbeuk_app import (
    NaheulbeukVerifyError,
    apply_naheulbeuk_semantic_patches,
    get_naheulbeuk_doctor_report,
    plan_naheulbeuk_semantic_patches,
)
from uese.core.naheulbeuk_semantic import SemanticPatchInput


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SAVE = REPO_ROOT / "save do analizy" / "Game_fcu_elo.sav"
FIRST_RECORD_ID = "character-001-13ec71f4576f"


class NaheulbeukAppTests(unittest.TestCase):
    def test_doctor_report_exposes_product_contract(self) -> None:
        report = get_naheulbeuk_doctor_report(SAMPLE_SAVE)

        self.assertIn(report["status"], {"ready", "degraded"})
        self.assertIn(report["mode"], {"semantic_ready", "inspect_and_expert_mode_only"})
        self.assertTrue(report["checks"])
        self.assertGreaterEqual(len(report["supported_character_fields"]), 15)
        self.assertEqual(report["probe_save"]["status"], "ok")
        self.assertEqual(report["probe_save"]["filepath"], str(SAMPLE_SAVE))

    def test_plan_patch_exposes_preview_spans(self) -> None:
        preview = plan_naheulbeuk_semantic_patches(
            SAMPLE_SAVE,
            [
                SemanticPatchInput(
                    record_id=FIRST_RECORD_ID,
                    field_id="stats_points",
                    value=77,
                )
            ],
        )

        self.assertEqual(preview["filepath"], str(SAMPLE_SAVE))
        self.assertEqual(len(preview["planned_changes"]), 1)
        self.assertEqual(preview["planned_changes"][0]["field_id"], "stats_points")
        self.assertTrue(preview["planned_changes"][0]["spans"])

    def test_apply_service_raises_verify_error_for_partial_failed_result(self) -> None:
        with patch("uese.core.naheulbeuk_app.apply_semantic_patches") as apply_mock:
            apply_mock.return_value = {
                "status": "partial_failed",
                "results": [{"record_id": FIRST_RECORD_ID, "field_id": "stats_points", "verified": False}],
            }

            with self.assertRaises(NaheulbeukVerifyError):
                apply_naheulbeuk_semantic_patches(
                    SAMPLE_SAVE,
                    [
                        SemanticPatchInput(
                            record_id=FIRST_RECORD_ID,
                            field_id="stats_points",
                            value=77,
                        )
                    ],
                    backup=False,
                )
