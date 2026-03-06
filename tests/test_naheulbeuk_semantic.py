from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uese.core.naheulbeuk_semantic import (
    CharacterAssetIdentity,
    SemanticPatchInput,
    _apply_character_asset_resolution,
    _apply_scene_asset_hints,
    apply_semantic_patches,
    inspect_naheulbeuk_save,
    plan_semantic_patches,
    SceneAssetHint,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SAVE = REPO_ROOT / "save do analizy" / "Game_fcu_elo.sav"
FIRST_RECORD_ID = "character-001-13ec71f4576f"
DISABLE_GAME_ASSET_ENV = {
    "UESE_NAHEULBEUK_DISABLE_GAME_ASSET_RESOLVER": "1",
    "UESE_NAHEULBEUK_DISABLE_SCENE_HINT_RESOLVER": "1",
}


class NaheulbeukSemanticTests(unittest.TestCase):
    def inspect_sample(self):
        with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
            return inspect_naheulbeuk_save(SAMPLE_SAVE)

    def test_inspect_returns_typed_character_records(self) -> None:
        model = self.inspect_sample()

        self.assertGreaterEqual(model.character_count, 50)
        self.assertGreaterEqual(model.economy_count, 20)
        self.assertEqual(sum(1 for record in model.characters if record.edit_status == "safe"), 28)
        self.assertEqual(sum(1 for record in model.characters if record.edit_status == "risky"), 26)
        self.assertEqual(sum(1 for record in model.characters if record.edit_status == "unresolved"), 1)
        self.assertEqual(model.characters[0].record_id, FIRST_RECORD_ID)
        self.assertEqual(model.characters[0].template_id, 100)
        self.assertEqual(model.characters[0].template_name, "AS_L_PitDoorman_M01")
        self.assertEqual(model.characters[0].classification, "npc")
        self.assertEqual(model.characters[0].template_status, "resolved")
        self.assertEqual(model.characters[0].edit_status, "safe")
        self.assertEqual(model.characters[0].structure_signature, "combat_entity")
        self.assertEqual(model.characters[0].group_kind, "asset_guid")
        self.assertEqual(model.characters[0].group_size, 1)

        field_map = {field.field_id: field for field in model.characters[0].fields}
        self.assertEqual(field_map["energy"].value, 70)
        self.assertEqual(field_map["level"].value, 2)
        self.assertEqual(field_map["stats_points"].value, 0)
        self.assertIsNone(field_map["agility"].value)
        self.assertEqual(field_map["agility"].status, "ambiguous")

    def test_unmatched_blocks_remain_risky_without_character_asset_lookup(self) -> None:
        model = self.inspect_sample()
        block_map = {record.block_index: record for record in model.characters}

        witness = block_map[37]
        sleepy_guard = block_map[38]
        unresolved = block_map[29]

        self.assertIsNone(witness.template_name)
        self.assertEqual(witness.template_resolution_source, "unresolved")
        self.assertEqual(witness.template_status, "unresolved")
        self.assertEqual(witness.classification, "unknown")
        self.assertEqual(witness.edit_status, "risky")
        self.assertEqual(witness.structure_signature, "combat_entity")
        self.assertEqual(witness.group_kind, "asset_guid")
        self.assertEqual(witness.group_size, 1)

        self.assertIsNone(sleepy_guard.template_name)
        self.assertEqual(sleepy_guard.template_resolution_source, "unresolved")
        self.assertEqual(sleepy_guard.template_status, "unresolved")
        self.assertEqual(sleepy_guard.edit_status, "risky")

        self.assertIsNone(unresolved.template_name)
        self.assertEqual(unresolved.identity_status, "ambiguous")
        self.assertEqual(unresolved.template_resolution_source, "unresolved")
        self.assertEqual(unresolved.template_status, "unresolved")
        self.assertEqual(unresolved.edit_status, "risky")
        self.assertEqual(unresolved.structure_signature, "combat_entity")
        self.assertEqual(unresolved.group_kind, "asset_guid")

        partial = block_map[55]
        self.assertIsNone(partial.template_name)
        self.assertEqual(partial.identity_status, "unresolved")
        self.assertEqual(partial.edit_status, "unresolved")
        self.assertEqual(partial.structure_signature, "partial_stats_block")
        self.assertEqual(partial.group_kind, "template_id")

    def test_character_asset_resolution_prefers_asset_guid_identity(self) -> None:
        model = self.inspect_sample()
        record = next(item for item in model.characters if item.block_index == 29)
        changed = _apply_character_asset_resolution(
            [record],
            {
                record.asset_guid: CharacterAssetIdentity(
                    template_name="AS_XL_OrcTutorial_M01",
                    bundle_name="npc",
                    bundle_path="/tmp/npc",
                    script_name="CharacterAsset",
                )
            },
        )

        self.assertEqual(changed, 1)
        self.assertEqual(record.template_name, "AS_XL_OrcTutorial_M01")
        self.assertEqual(record.template_status, "resolved")
        self.assertEqual(record.template_resolution_source, "game_character_asset")
        self.assertEqual(record.template_source_detail, "CharacterAsset:npc")
        self.assertEqual(record.classification, "npc")
        self.assertEqual(record.identity_status, "resolved")
        self.assertEqual(record.edit_status, "safe")

    def test_scene_hint_reclassifies_environment_record(self) -> None:
        model = self.inspect_sample()
        record = next(item for item in model.characters if item.block_index == 32)
        changed = _apply_scene_asset_hints(
            [record],
            {
                record.asset_guid: SceneAssetHint(
                    class_name="BreakableSpawner",
                    scene_path="floors/floor00/scene",
                    game_object_name="SP_1x1x1_Breakable_Common",
                    asset_file_name="BuildPlayer-Floor00_LD",
                    hit_count=147,
                    dominant_actor_guid=record.actor_guid,
                )
            },
        )

        self.assertEqual(changed, 1)
        self.assertEqual(record.classification, "environment")
        self.assertEqual(record.identity_status, "resolved")
        self.assertEqual(record.edit_status, "unresolved")
        self.assertIsNotNone(record.scene_hint)
        self.assertEqual(record.scene_hint.class_name, "BreakableSpawner")
        self.assertEqual(record.scene_hint.game_object_name, "SP_1x1x1_Breakable_Common")
        self.assertEqual(record.label, "Breakable Spawner · Character 32 · 509810ff")
        self.assertTrue(any("environment/spawner data" in note for note in record.notes))

    def test_environment_records_are_blocked_from_semantic_patch_flow(self) -> None:
        model = self.inspect_sample()
        record = next(item for item in model.characters if item.block_index == 32)
        _apply_scene_asset_hints(
            [record],
            {
                record.asset_guid: SceneAssetHint(
                    class_name="BreakableSpawner",
                    scene_path="floors/floor00/scene",
                    game_object_name="SP_1x1x1_Breakable_Common",
                    asset_file_name="BuildPlayer-Floor00_LD",
                    hit_count=147,
                    dominant_actor_guid=record.actor_guid,
                )
            },
        )

        with self.assertRaisesRegex(ValueError, "environment data rather than a character"):
            plan_semantic_patches(
                model,
                [
                    SemanticPatchInput(
                        record_id=record.record_id,
                        field_id="stats_points",
                        value=12,
                        allow_identity_ambiguous=True,
                    )
                ],
            )

    def test_apply_semantic_patch_updates_direct_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            working_copy = Path(temp_dir) / SAMPLE_SAVE.name
            shutil.copy2(SAMPLE_SAVE, working_copy)

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                result = apply_semantic_patches(
                    working_copy,
                    [
                        SemanticPatchInput(
                            record_id=FIRST_RECORD_ID,
                            field_id="stats_points",
                            value=77,
                        )
                    ],
                    backup=False,
                )

            self.assertEqual(result["status"], "success")
            self.assertTrue(result["results"][0]["verified"])

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                reparsed = inspect_naheulbeuk_save(working_copy)
            field_map = {field.field_id: field for field in reparsed.characters[0].fields}
            self.assertEqual(field_map["stats_points"].value, 77)

    def test_apply_semantic_patch_rejects_inferred_identity_without_opt_in(self) -> None:
        model = self.inspect_sample()
        record = next(item for item in model.characters if item.block_index == 37)

        with tempfile.TemporaryDirectory() as temp_dir:
            working_copy = Path(temp_dir) / SAMPLE_SAVE.name
            shutil.copy2(SAMPLE_SAVE, working_copy)

            with self.assertRaisesRegex(ValueError, "allow_identity_ambiguous=true"):
                with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                    apply_semantic_patches(
                        working_copy,
                        [
                            SemanticPatchInput(
                                record_id=record.record_id,
                                field_id="stats_points",
                                value=12,
                            )
                        ],
                        backup=False,
                    )

    def test_apply_semantic_patch_allows_inferred_identity_with_opt_in(self) -> None:
        model = self.inspect_sample()
        record = next(item for item in model.characters if item.block_index == 37)

        with tempfile.TemporaryDirectory() as temp_dir:
            working_copy = Path(temp_dir) / SAMPLE_SAVE.name
            shutil.copy2(SAMPLE_SAVE, working_copy)

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                result = apply_semantic_patches(
                    working_copy,
                    [
                        SemanticPatchInput(
                            record_id=record.record_id,
                            field_id="stats_points",
                            value=12,
                            allow_identity_ambiguous=True,
                        )
                    ],
                    backup=False,
                )

            self.assertEqual(result["status"], "success")
            self.assertTrue(result["results"][0]["verified"])

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                reparsed = inspect_naheulbeuk_save(working_copy)
            updated = next(item for item in reparsed.characters if item.record_id == record.record_id)
            field_map = {field.field_id: field for field in updated.fields}
            self.assertEqual(field_map["stats_points"].value, 12)

    def test_apply_semantic_patch_updates_override_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            working_copy = Path(temp_dir) / SAMPLE_SAVE.name
            shutil.copy2(SAMPLE_SAVE, working_copy)

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                result = apply_semantic_patches(
                    working_copy,
                    [
                        SemanticPatchInput(
                            record_id=FIRST_RECORD_ID,
                            field_id="agility",
                            value=14,
                            allow_ambiguous=True,
                        )
                    ],
                    backup=False,
                )

            self.assertEqual(result["status"], "success")
            self.assertTrue(result["results"][0]["verified"])

            with patch.dict(os.environ, DISABLE_GAME_ASSET_ENV, clear=False):
                reparsed = inspect_naheulbeuk_save(working_copy)
            field_map = {field.field_id: field for field in reparsed.characters[0].fields}
            self.assertEqual(field_map["agility"].value, 14)
            self.assertEqual(field_map["agility"].current_mode, "override")


if __name__ == "__main__":
    unittest.main()
