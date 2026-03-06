from __future__ import annotations

from argparse import Namespace
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from uese.cli.commands import (
    EXIT_BLOCKED,
    EXIT_OK,
    EXIT_VERIFY_FAILED,
    cmd_naheulbeuk_doctor,
    cmd_naheulbeuk_patch,
)
from uese.core.naheulbeuk_app import NaheulbeukBlockedError, NaheulbeukVerifyError


class NaheulbeukCliTests(unittest.TestCase):
    def test_doctor_command_supports_json_output(self) -> None:
        args = Namespace(save=None, json=True)
        stdout = io.StringIO()
        with patch("uese.cli.commands.get_naheulbeuk_doctor_report") as report_mock:
            report_mock.return_value = {
                "status": "degraded",
                "mode": "inspect_and_expert_mode_only",
                "checks": [],
                "warnings": [],
                "supported_character_fields": [],
                "probe_save": None,
            }
            with redirect_stdout(stdout):
                rc = cmd_naheulbeuk_doctor(args)

        self.assertEqual(rc, EXIT_OK)
        self.assertIn('"status": "degraded"', stdout.getvalue())

    def test_patch_command_returns_blocked_exit_code(self) -> None:
        args = Namespace(
            save="input.sav",
            character_id="character-032-509810ff4c19",
            record_id=None,
            field="stats_points",
            value=12.0,
            allow_ambiguous=False,
            allow_identity_ambiguous=False,
            out=None,
            no_backup=True,
        )
        stdout = io.StringIO()
        with patch("uese.cli.commands.apply_naheulbeuk_semantic_patches", side_effect=NaheulbeukBlockedError("blocked")):
            with redirect_stdout(stdout):
                rc = cmd_naheulbeuk_patch(args)

        self.assertEqual(rc, EXIT_BLOCKED)
        self.assertIn("blocked", stdout.getvalue())

    def test_patch_command_returns_verify_exit_code(self) -> None:
        args = Namespace(
            save="input.sav",
            character_id="character-001-13ec71f4576f",
            record_id=None,
            field="stats_points",
            value=12.0,
            allow_ambiguous=False,
            allow_identity_ambiguous=False,
            out=None,
            no_backup=True,
        )
        stdout = io.StringIO()
        with patch(
            "uese.cli.commands.apply_naheulbeuk_semantic_patches",
            side_effect=NaheulbeukVerifyError("verify mismatch", payload={"status": "partial_failed"}),
        ):
            with redirect_stdout(stdout):
                rc = cmd_naheulbeuk_patch(args)

        self.assertEqual(rc, EXIT_VERIFY_FAILED)
        self.assertIn('"status": "partial_failed"', stdout.getvalue())
