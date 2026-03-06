from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any, Iterable

from .naheulbeuk_semantic import (
    NAHEULBEUK_GAME_DIR_ENV,
    SemanticPatchBlockedError,
    SemanticPatchInput,
    SemanticPatchValidationError,
    UnityPy,
    _candidate_naheulbeuk_data_roots,
    _discover_character_asset_index,
    _normalize_naheulbeuk_data_root,
    apply_semantic_patches,
    inspect_naheulbeuk_save,
    plan_semantic_patches,
    record_matches_filters,
)

SUPPORTED_CHARACTER_FIELDS: tuple[dict[str, Any], ...] = (
    {"field_id": "health", "label": "Health", "category": "resources", "value_type": "s32", "min_value": 0, "max_value": 999999},
    {"field_id": "energy", "label": "Energy", "category": "resources", "value_type": "s32", "min_value": 0, "max_value": 999999},
    {"field_id": "agility", "label": "Agility", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "charisma", "label": "Charisma", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "cleverness", "label": "Cleverness", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "constitution", "label": "Constitution", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "courage", "label": "Courage", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "strength", "label": "Strength", "category": "base_attributes", "value_type": "s32", "min_value": -1, "max_value": 9999},
    {"field_id": "level", "label": "Level", "category": "progression", "value_type": "u32", "min_value": 0, "max_value": 999},
    {"field_id": "current_xp", "label": "Current XP", "category": "progression", "value_type": "u32", "min_value": 0, "max_value": 999999999},
    {"field_id": "stats_points", "label": "Stats Points", "category": "progression_points", "value_type": "u32", "min_value": 0, "max_value": 99999},
    {"field_id": "active_skill_points", "label": "Active Skill Points", "category": "progression_points", "value_type": "u32", "min_value": 0, "max_value": 99999},
    {"field_id": "passive_skill_points", "label": "Passive Skill Points", "category": "progression_points", "value_type": "u32", "min_value": 0, "max_value": 99999},
    {"field_id": "dodge", "label": "Dodge", "category": "combat", "value_type": "f32", "min_value": 0.0, "max_value": 1000.0},
    {"field_id": "parry", "label": "Parry", "category": "combat", "value_type": "f32", "min_value": 0.0, "max_value": 1000.0},
)


class NaheulbeukAppError(RuntimeError):
    exit_code = 1
    status_code = 400
    error_code = "naheulbeuk_error"

    def __init__(self, message: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload


class NaheulbeukInputError(NaheulbeukAppError):
    error_code = "naheulbeuk_input_error"


class NaheulbeukVerifyError(NaheulbeukAppError):
    exit_code = 2
    status_code = 409
    error_code = "naheulbeuk_verify_failed"


class NaheulbeukBlockedError(NaheulbeukAppError):
    exit_code = 3
    status_code = 409
    error_code = "naheulbeuk_semantic_blocked"


class NaheulbeukInternalError(NaheulbeukAppError):
    status_code = 500
    error_code = "naheulbeuk_internal_error"


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    summary: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail,
        }


def _repo_default_probe_save() -> Path | None:
    sample = Path(__file__).resolve().parents[2] / "save do analizy" / "Game_fcu_elo.sav"
    return sample if sample.exists() else None


def _discover_data_root() -> tuple[Path | None, str | None]:
    explicit = os.environ.get(NAHEULBEUK_GAME_DIR_ENV)
    explicit_path = Path(explicit).expanduser() if explicit else None
    for candidate in _candidate_naheulbeuk_data_roots():
        data_root = _normalize_naheulbeuk_data_root(candidate)
        if data_root is None:
            continue
        source = "env" if explicit_path and candidate.expanduser() == explicit_path else "default"
        return data_root, source
    return None, None


def _ensure_existing_file(filepath: Path | str) -> Path:
    path = Path(filepath).expanduser()
    if not path.exists():
        raise NaheulbeukInputError(f"File not found: {path}")
    if not path.is_file():
        raise NaheulbeukInputError(f"Expected a file path, got: {path}")
    return path


def _coerce_app_error(exc: Exception) -> NaheulbeukAppError:
    if isinstance(exc, NaheulbeukAppError):
        return exc
    if isinstance(exc, SemanticPatchBlockedError):
        return NaheulbeukBlockedError(str(exc))
    if isinstance(exc, SemanticPatchValidationError):
        return NaheulbeukInputError(str(exc))
    if isinstance(exc, FileNotFoundError):
        return NaheulbeukInputError(str(exc))
    return NaheulbeukInternalError(str(exc))


def get_naheulbeuk_doctor_report(filepath: Path | str | None = None) -> dict[str, Any]:
    data_root, data_root_source = _discover_data_root()
    unitypy_installed = UnityPy is not None
    unitypy_version = getattr(UnityPy, "__version__", None) if UnityPy is not None else None

    character_asset_root = data_root / "StreamingAssets" / "OSX" / "as" / "ch" if data_root else None
    scene_root = data_root / "StreamingAssets" / "OSX" / "scenes" if data_root else None

    character_asset_index: dict[str, Any] = {}
    discovered_asset_root: Path | None = None
    if data_root and unitypy_installed:
        character_asset_index, discovered_asset_root = _discover_character_asset_index()

    checks = [
        DoctorCheck(
            name="python",
            status="ok",
            summary=f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            detail=sys.executable,
        ),
        DoctorCheck(
            name="unitypy",
            status="ok" if unitypy_installed else "warn",
            summary="UnityPy installed" if unitypy_installed else "UnityPy missing",
            detail=unitypy_version,
        ),
        DoctorCheck(
            name="game_data_root",
            status="ok" if data_root else "warn",
            summary="Naheulbeuk data root discovered" if data_root else "Naheulbeuk data root not found",
            detail=f"{data_root} ({data_root_source})" if data_root else os.environ.get(NAHEULBEUK_GAME_DIR_ENV),
        ),
        DoctorCheck(
            name="character_asset_resolver",
            status="ok" if character_asset_index else "warn",
            summary=(
                f"CharacterAsset resolver ready ({len(character_asset_index)} templates)"
                if character_asset_index
                else "CharacterAsset resolver unavailable"
            ),
            detail=str(discovered_asset_root or character_asset_root) if (discovered_asset_root or character_asset_root) else None,
        ),
        DoctorCheck(
            name="scene_hint_resolver",
            status="ok" if (unitypy_installed and scene_root and scene_root.exists()) else "warn",
            summary="Scene-hint resolver ready" if (unitypy_installed and scene_root and scene_root.exists()) else "Scene-hint resolver unavailable",
            detail=str(scene_root) if scene_root else None,
        ),
    ]

    warnings: list[str] = []
    if not unitypy_installed:
        warnings.append("UnityPy is missing; semantic inspect still works, but CharacterAsset and scene-hint identity resolution will be degraded.")
    if data_root is None:
        warnings.append("Installed Naheulbeuk assets were not discovered; semantic editing falls back to weaker save-only identity hints.")
    if data_root is not None and not character_asset_index:
        warnings.append("Game data root exists, but CharacterAsset bundle indexing found no usable template map.")

    probe_payload: dict[str, Any] | None = None
    probe_candidate = Path(filepath).expanduser() if filepath else _repo_default_probe_save()
    if probe_candidate is not None:
        if probe_candidate.exists():
            try:
                model = inspect_naheulbeuk_save(probe_candidate)
                probe_payload = {
                    "filepath": str(probe_candidate),
                    "status": "ok",
                    "character_count": model.character_count,
                    "economy_count": model.economy_count,
                    "safe_count": sum(1 for record in model.characters if record.edit_status == "safe"),
                    "risky_count": sum(1 for record in model.characters if record.edit_status == "risky"),
                    "unresolved_count": sum(1 for record in model.characters if record.edit_status == "unresolved"),
                }
            except Exception as exc:  # pragma: no cover - safety net for doctor mode
                probe_payload = {
                    "filepath": str(probe_candidate),
                    "status": "error",
                    "error": str(exc),
                }
                warnings.append(f"Probe save inspect failed: {exc}")
        else:
            probe_payload = {
                "filepath": str(probe_candidate),
                "status": "missing",
            }

    ready = unitypy_installed and data_root is not None and bool(character_asset_index)
    return {
        "status": "ready" if ready else "degraded",
        "mode": "semantic_ready" if ready else "inspect_and_expert_mode_only",
        "game_dir_env": NAHEULBEUK_GAME_DIR_ENV,
        "data_root": str(data_root) if data_root else None,
        "data_root_source": data_root_source,
        "checks": [check.to_dict() for check in checks],
        "warnings": warnings,
        "supported_character_fields": list(SUPPORTED_CHARACTER_FIELDS),
        "probe_save": probe_payload,
    }


def inspect_naheulbeuk(filepath: Path | str) -> dict[str, Any]:
    try:
        return inspect_naheulbeuk_save(_ensure_existing_file(filepath)).to_dict()
    except Exception as exc:
        raise _coerce_app_error(exc) from exc


def list_naheulbeuk_records(
    filepath: Path | str,
    *,
    risk: str = "all",
    classification: str = "all",
) -> dict[str, Any]:
    try:
        path = _ensure_existing_file(filepath)
        model = inspect_naheulbeuk_save(path)
        filtered_characters = [
            record
            for record in model.characters
            if record_matches_filters(record, edit_status=risk, classification=classification)
        ]
        return {
            "filepath": str(path),
            "character_count": len(filtered_characters),
            "total_character_count": model.character_count,
            "economy_count": model.economy_count,
            "filters": {"risk": risk, "classification": classification},
            "warnings": model.warnings,
            "characters": [record.to_summary() for record in filtered_characters],
            "economy": [record.to_summary() for record in model.economy],
        }
    except Exception as exc:
        raise _coerce_app_error(exc) from exc


def get_naheulbeuk_record(filepath: Path | str, record_id: str) -> dict[str, Any]:
    try:
        path = _ensure_existing_file(filepath)
        model = inspect_naheulbeuk_save(path)
        for record in [*model.characters, *model.economy]:
            if record.record_id == record_id:
                return record.to_dict()
        raise NaheulbeukInputError(f"Character/record not found: {record_id}")
    except Exception as exc:
        raise _coerce_app_error(exc) from exc


def plan_naheulbeuk_semantic_patches(
    filepath: Path | str,
    patch_inputs: Iterable[SemanticPatchInput],
) -> dict[str, Any]:
    try:
        path = _ensure_existing_file(filepath)
        model = inspect_naheulbeuk_save(path)
        plans = plan_semantic_patches(model, list(patch_inputs))
        return {
            "filepath": str(path),
            "warnings": model.warnings,
            "planned_changes": [plan.to_dict() for plan in plans],
        }
    except Exception as exc:
        raise _coerce_app_error(exc) from exc


def apply_naheulbeuk_semantic_patches(
    filepath: Path | str,
    patch_inputs: Iterable[SemanticPatchInput],
    *,
    backup: bool = True,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    try:
        result = apply_semantic_patches(
            _ensure_existing_file(filepath),
            list(patch_inputs),
            backup=backup,
            output_path=output_path,
        )
        if result.get("status") != "success":
            raise NaheulbeukVerifyError(
                "Semantic patch write completed, but verify/reparse did not confirm every requested value.",
                payload=result,
            )
        return result
    except Exception as exc:
        raise _coerce_app_error(exc) from exc
