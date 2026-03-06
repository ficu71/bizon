from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from uese.core.naheulbeuk_app import NaheulbeukBlockedError


class NaheulbeukApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_doctor_endpoint_returns_service_payload(self) -> None:
        payload = {
            "status": "degraded",
            "mode": "inspect_and_expert_mode_only",
            "checks": [],
            "warnings": [],
            "supported_character_fields": [],
            "probe_save": None,
        }
        with patch("backend.main.get_naheulbeuk_doctor_report", return_value=payload):
            response = self.client.get("/naheulbeuk/doctor")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)

    def test_semantic_patch_endpoint_maps_blocked_error_to_409(self) -> None:
        with patch(
            "backend.main.apply_naheulbeuk_semantic_patches",
            side_effect=NaheulbeukBlockedError("blocked by semantic guard"),
        ):
            response = self.client.post(
                "/naheulbeuk/patch-semantic",
                json={
                    "filepath": "input.sav",
                    "record_id": "character-032-509810ff4c19",
                    "field_id": "stats_points",
                    "value": 12,
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "blocked by semantic guard")
