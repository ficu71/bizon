#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Iterable, Literal
import re
import struct

from uese.core.gzip_field_patcher import (
    extract_gzip_payload,
    rebuild_gzip_container,
)
from uese.core.patch_engine import PatchEngine

try:
    import UnityPy
except Exception:  # pragma: no cover - optional reverse-engineering dependency.
    UnityPy = None

IdentifierStatus = Literal["resolved", "ambiguous", "unresolved"]
RecordKind = Literal["character", "economy"]
ValueKind = Literal["u32", "s32", "f32"]
RecordEditStatus = Literal["safe", "risky", "unresolved", "economy"]
StructureSignature = Literal[
    "combat_entity",
    "camera_bound_combat_entity",
    "partial_stats_block",
    "unknown",
]
TemplateResolutionSource = Literal[
    "game_character_asset",
    "indexed_table",
    "actor_guid_propagation",
    "asset_guid_propagation",
    "character_ref_propagation",
    "unresolved",
]
FieldValue = int | float | None


class SemanticPatchError(ValueError):
    """Base error for semantic patch planning/apply flows."""


class SemanticPatchValidationError(SemanticPatchError):
    """Patch request is malformed or missing an explicit opt-in."""


class SemanticPatchBlockedError(SemanticPatchError):
    """Patch request targets a record/field that semantic mode should not touch."""

GUID_RE = re.compile(rb"[0-9a-f]{32}")
TOP_LEVEL_TOKENS = [
    b"m_baseStatsModifiersValues",
    b"m_energy",
    b"m_health",
    b"m_agility",
    b"m_charisma",
    b"m_cleverness",
    b"m_constitution",
    b"m_courage",
    b"m_inflictedDamagePercentage",
    b"m_criticalFailure",
    b"m_strength",
    b"m_level",
    b"m_currentXp",
    b"m_statsPoints",
    b"m_activeSkillPoints",
    b"m_passiveSkillPoints",
    b"m_dodge",
    b"m_parry",
    b"m_tags",
]
BLOCK_START = b"m_statsManager"
GOLD_TOKEN = b"m_gold"
STRING_ENTRY_MARKER = 0x06
MAX_STRING_ENTRY_LEN = 96
MIN_STRING_RUN_SIZE = 32
MAX_STRING_RUN_GAP = 140

PARTY_ASSET_NAMES = {
    "AS_L_Ranger",
    "AS_L_Rogue",
    "AS_M_Elf",
    "AS_M_Priestess",
    "AS_M_Wizard",
    "AS_S_Dwarf",
    "AS_XL_Barbarian",
    "AS_XXL_Ogre",
}

NAHEULBEUK_GAME_DIR_ENV = "UESE_NAHEULBEUK_GAME_DIR"
NAHEULBEUK_DISABLE_GAME_ASSET_ENV = "UESE_NAHEULBEUK_DISABLE_GAME_ASSET_RESOLVER"
NAHEULBEUK_DISABLE_SCENE_HINT_ENV = "UESE_NAHEULBEUK_DISABLE_SCENE_HINT_RESOLVER"
NAHEULBEUK_DEFAULT_DATA_ROOTS = (
    Path("/Users/Shared/Epic Games/DungeonOfNaheulbeuk/Naheulbeuk.app/Contents/Resources/Data"),
    Path("/Users/Shared/Epic Games/DungeonOfNaheulbeuk/Naheulbeuk.app"),
    Path("/Users/Shared/Epic Games/DungeonOfNaheulbeuk"),
)
SAFE_CHARACTER_CLASSIFICATIONS = {"party", "companion", "npc"}
ENVIRONMENT_SCENE_CLASSES = {
    "BreakableSpawner",
}
INSTANCE_SUFFIX_RE = re.compile(r" \(\d+\)$")
CAMELCASE_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _normalize_naheulbeuk_data_root(candidate: Path) -> Path | None:
    candidate = candidate.expanduser()
    if not candidate.exists():
        return None
    if candidate.name == "Data" and candidate.is_dir():
        return candidate
    if candidate.suffix == ".app":
        data_root = candidate / "Contents" / "Resources" / "Data"
        return data_root if data_root.exists() else None
    app_root = candidate / "Naheulbeuk.app"
    if app_root.exists():
        data_root = app_root / "Contents" / "Resources" / "Data"
        return data_root if data_root.exists() else None
    return None


def _candidate_naheulbeuk_data_roots() -> list[Path]:
    roots: list[Path] = []
    explicit = os.environ.get(NAHEULBEUK_GAME_DIR_ENV)
    if explicit:
        roots.append(Path(explicit))
    roots.extend(NAHEULBEUK_DEFAULT_DATA_ROOTS)
    return roots


def _build_env_object_lookup(env: Any) -> dict[tuple[str, int], Any]:
    return {
        (obj.assets_file.name, obj.path_id): obj
        for obj in env.objects
    }


def _resolve_unity_reference(
    owner_obj: Any,
    reference: Any,
    object_lookup: dict[tuple[str, int], Any],
) -> Any | None:
    if not isinstance(reference, dict):
        return None

    path_id = reference.get("m_PathID")
    if not path_id:
        return None

    file_id = reference.get("m_FileID", 0)
    asset_file_name = owner_obj.assets_file.name
    if file_id:
        try:
            asset_file_name = owner_obj.assets_file.externals[file_id - 1].name
        except Exception:
            return None
    return object_lookup.get((asset_file_name, path_id))


def _unity_monobehaviour_class_name(
    tree: dict[str, Any],
    owner_obj: Any,
    object_lookup: dict[tuple[str, int], Any],
) -> str | None:
    script_obj = _resolve_unity_reference(owner_obj, tree.get("m_Script"), object_lookup)
    if script_obj is None:
        return None
    try:
        script_data = script_obj.read()
    except Exception:
        return None
    return (
        getattr(script_data, "m_ClassName", None)
        or getattr(script_data, "m_Name", None)
        or getattr(script_data, "name", None)
    )


def _unity_game_object_name(
    tree: dict[str, Any],
    owner_obj: Any,
    object_lookup: dict[tuple[str, int], Any],
) -> str | None:
    game_object = _resolve_unity_reference(owner_obj, tree.get("m_GameObject"), object_lookup)
    if game_object is None:
        return None
    try:
        game_object_tree = game_object.read_typetree()
    except Exception:
        return None
    name = game_object_tree.get("m_Name")
    return str(name) if name else None


def _normalize_scene_object_name(name: str | None) -> str | None:
    if not name:
        return None
    return INSTANCE_SUFFIX_RE.sub("", name.strip())


def _humanize_scene_class_name(class_name: str | None) -> str:
    if not class_name:
        return "Scene Entity"
    return CAMELCASE_BOUNDARY_RE.sub(" ", class_name.replace("_", " ")).strip()


@lru_cache(maxsize=4)
def _load_character_asset_index(bundle_root_str: str) -> dict[str, CharacterAssetIdentity]:
    if UnityPy is None:
        return {}

    bundle_root = Path(bundle_root_str)
    if not bundle_root.exists():
        return {}

    index: dict[str, CharacterAssetIdentity] = {}
    ambiguous_guids: set[str] = set()

    for bundle in sorted(path for path in bundle_root.rglob("*") if path.is_file()):
        try:
            env = UnityPy.load(str(bundle))
        except Exception:
            continue
        object_lookup = _build_env_object_lookup(env)
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            class_name = _unity_monobehaviour_class_name(tree, obj, object_lookup)
            if class_name not in {"CharacterAsset", "SellerCharacterAsset"}:
                continue
            reference = tree.get("m_reference")
            if not isinstance(reference, dict):
                continue
            guid = reference.get("m_guid")
            name = tree.get("m_Name")
            if not guid or not name:
                continue
            candidate = CharacterAssetIdentity(
                template_name=name,
                bundle_name=bundle.name,
                bundle_path=str(bundle),
                script_name=class_name,
            )
            existing = index.get(guid)
            if existing is not None and existing.template_name != candidate.template_name:
                ambiguous_guids.add(guid)
                index.pop(guid, None)
                continue
            if guid not in ambiguous_guids:
                index[guid] = candidate

    return index


def _discover_character_asset_index() -> tuple[dict[str, CharacterAssetIdentity], Path | None]:
    disabled = os.environ.get(NAHEULBEUK_DISABLE_GAME_ASSET_ENV, "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return {}, None

    for candidate in _candidate_naheulbeuk_data_roots():
        data_root = _normalize_naheulbeuk_data_root(candidate)
        if data_root is None:
            continue
        bundle_root = data_root / "StreamingAssets" / "OSX" / "as" / "ch"
        if not bundle_root.exists():
            continue
        index = _load_character_asset_index(str(bundle_root))
        if index:
            return index, bundle_root

    return {}, None


@dataclass(frozen=True)
class SceneAssetObservation:
    class_name: str
    scene_path: str
    game_object_name: str | None
    asset_file_name: str
    actor_guid: str | None


@dataclass(frozen=True)
class SceneAssetHint:
    class_name: str
    scene_path: str
    game_object_name: str | None
    asset_file_name: str
    hit_count: int
    dominant_actor_guid: str | None = None

    @property
    def display_label(self) -> str:
        return _humanize_scene_class_name(self.class_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_name": self.class_name,
            "display_label": self.display_label,
            "scene_path": self.scene_path,
            "game_object_name": self.game_object_name,
            "asset_file_name": self.asset_file_name,
            "hit_count": self.hit_count,
            "dominant_actor_guid": self.dominant_actor_guid,
        }


def _scene_bundle_inputs(scene_bundle: Path) -> tuple[str, ...]:
    inputs = [str(scene_bundle)]
    data_bundle = scene_bundle.with_name("data")
    if data_bundle.exists() and data_bundle.is_file():
        inputs.append(str(data_bundle))
    return tuple(inputs)


def _load_scene_candidate_files(
    scene_root: Path,
    wanted_guids: tuple[str, ...],
) -> dict[Path, set[str]]:
    guid_bytes = {guid: guid.encode("ascii") for guid in wanted_guids}
    candidates: dict[Path, set[str]] = {}
    for scene_bundle in sorted(path for path in scene_root.rglob("scene") if path.is_file()):
        found: set[str] = set()
        for bundle_path in [scene_bundle, scene_bundle.with_name("data")]:
            if not bundle_path.exists() or not bundle_path.is_file():
                continue
            try:
                blob = bundle_path.read_bytes()
            except Exception:
                continue
            for guid, probe in guid_bytes.items():
                if guid in found:
                    continue
                if probe in blob:
                    found.add(guid)
            if len(found) == len(guid_bytes):
                break
        if found:
            candidates[scene_bundle] = found
    return candidates


@lru_cache(maxsize=4)
def _load_scene_asset_hints(
    scene_root_str: str,
    wanted_guids: tuple[str, ...],
) -> dict[str, SceneAssetHint]:
    if UnityPy is None or not wanted_guids:
        return {}

    scene_root = Path(scene_root_str)
    if not scene_root.exists():
        return {}

    observations: dict[str, list[SceneAssetObservation]] = defaultdict(list)
    candidate_files = _load_scene_candidate_files(scene_root, wanted_guids)
    for scene_bundle, scene_guids in candidate_files.items():
        try:
            env = UnityPy.load(*_scene_bundle_inputs(scene_bundle))
        except Exception:
            continue

        object_lookup = _build_env_object_lookup(env)
        scene_path = scene_bundle.relative_to(scene_root).as_posix()
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree = obj.read_typetree()
            except Exception:
                continue
            asset_ref = tree.get("m_asset")
            if not isinstance(asset_ref, dict):
                continue
            guid = asset_ref.get("m_guid")
            if guid not in scene_guids:
                continue

            class_name = _unity_monobehaviour_class_name(tree, obj, object_lookup)
            if not class_name:
                continue
            observations[guid].append(
                SceneAssetObservation(
                    class_name=class_name,
                    scene_path=scene_path,
                    game_object_name=_normalize_scene_object_name(
                        _unity_game_object_name(tree, obj, object_lookup)
                    ),
                    asset_file_name=obj.assets_file.name,
                    actor_guid=tree.get("m_actor", {}).get("m_guid")
                    if isinstance(tree.get("m_actor"), dict)
                    else None,
                )
            )

    hints: dict[str, SceneAssetHint] = {}
    for guid, items in observations.items():
        class_counts = Counter(item.class_name for item in items if item.class_name)
        if len(class_counts) != 1:
            continue

        class_name = next(iter(class_counts))
        scene_counts = Counter(item.scene_path for item in items if item.scene_path)
        object_counts = Counter(item.game_object_name for item in items if item.game_object_name)
        asset_counts = Counter(item.asset_file_name for item in items if item.asset_file_name)
        actor_counts = Counter(item.actor_guid for item in items if item.actor_guid)

        hints[guid] = SceneAssetHint(
            class_name=class_name,
            scene_path=scene_counts.most_common(1)[0][0],
            game_object_name=object_counts.most_common(1)[0][0] if object_counts else None,
            asset_file_name=asset_counts.most_common(1)[0][0],
            hit_count=len(items),
            dominant_actor_guid=actor_counts.most_common(1)[0][0] if actor_counts else None,
        )

    return hints


def _discover_scene_asset_hints(asset_guids: Iterable[str]) -> tuple[dict[str, SceneAssetHint], Path | None]:
    disabled = os.environ.get(NAHEULBEUK_DISABLE_SCENE_HINT_ENV, "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return {}, None

    wanted_guids = tuple(sorted({guid for guid in asset_guids if guid}))
    if not wanted_guids:
        return {}, None

    for candidate in _candidate_naheulbeuk_data_roots():
        data_root = _normalize_naheulbeuk_data_root(candidate)
        if data_root is None:
            continue
        scene_root = data_root / "StreamingAssets" / "OSX" / "scenes"
        if not scene_root.exists():
            continue
        return _load_scene_asset_hints(str(scene_root), wanted_guids), scene_root

    return {}, None


def _find_exact_token(blob: bytes, token: bytes, start: int = 0, end: int | None = None) -> int:
    bound = len(blob) if end is None else end
    cursor = start
    prefix = len(token).to_bytes(4, "little", signed=False)
    while cursor < bound:
        pos = blob.find(token, cursor, bound)
        if pos == -1:
            return -1
        if pos >= 4 and blob[pos - 4 : pos] == prefix:
            return pos
        cursor = pos + 1
    return -1


def _find_all_exact_tokens(blob: bytes, token: bytes) -> list[int]:
    positions: list[int] = []
    cursor = 0
    while True:
        pos = _find_exact_token(blob, token, cursor)
        if pos == -1:
            break
        positions.append(pos)
        cursor = pos + 1
    return positions


def _rfind_exact_token(blob: bytes, token: bytes, start: int = 0, end: int | None = None) -> int:
    positions = _find_all_exact_tokens(blob[start:end], token)
    if not positions:
        return -1
    return start + positions[-1]


def _collect_indexed_strings(payload: bytes) -> list[tuple[int, int, str]]:
    entries: list[tuple[int, int, str]] = []
    cursor = 0
    while cursor < len(payload):
        marker_pos = payload.find(bytes([STRING_ENTRY_MARKER]), cursor)
        if marker_pos == -1:
            break
        cursor = marker_pos + 1

        if marker_pos + 6 >= len(payload):
            continue
        string_id = int.from_bytes(payload[marker_pos + 1 : marker_pos + 5], "little", signed=False)
        string_len = payload[marker_pos + 5]
        if string_len <= 0 or string_len > MAX_STRING_ENTRY_LEN:
            continue

        end = marker_pos + 6 + string_len
        if end > len(payload):
            continue
        data = payload[marker_pos + 6 : end]
        if not data:
            continue
        if not all(32 <= byte < 127 for byte in data):
            continue

        entries.append((marker_pos, string_id, data.decode("ascii", errors="ignore")))
    return entries


def _pick_best_string_run(entries: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    if not entries:
        return []

    runs: list[list[tuple[int, int, str]]] = []
    start = 0
    for index in range(1, len(entries)):
        prev = entries[index - 1]
        current = entries[index]
        breaks_run = (
            current[0] - prev[0] > MAX_STRING_RUN_GAP
            or current[1] != prev[1] + 1
        )
        if breaks_run:
            segment = entries[start:index]
            if len(segment) >= MIN_STRING_RUN_SIZE:
                runs.append(segment)
            start = index

    final_segment = entries[start:]
    if len(final_segment) >= MIN_STRING_RUN_SIZE:
        runs.append(final_segment)

    if not runs:
        return []

    def run_score(run: list[tuple[int, int, str]]) -> tuple[int, int]:
        asset_like = sum(1 for _, _, text in run if text.startswith("AS_"))
        return (len(run), asset_like)

    return max(runs, key=run_score)


def _build_template_string_map(payload: bytes) -> tuple[dict[int, str], int]:
    entries = _collect_indexed_strings(payload)
    run = _pick_best_string_run(entries)
    mapping = {string_id: text for _, string_id, text in run}
    max_id = max(mapping) if mapping else -1
    return mapping, max_id


def _decode_value(codec: ValueKind, raw: bytes) -> int | float:
    if codec == "u32":
        return int.from_bytes(raw, "little", signed=False)
    if codec == "s32":
        return int.from_bytes(raw, "little", signed=True)
    if codec == "f32":
        return struct.unpack("<f", raw)[0]
    raise ValueError(f"Unsupported codec: {codec}")


def _encode_value(codec: ValueKind, value: int | float) -> bytes:
    if codec == "u32":
        if int(value) < 0 or int(value) > 0xFFFFFFFF:
            raise ValueError(f"Value {value} out of range for uint32")
        return int(value).to_bytes(4, "little", signed=False)
    if codec == "s32":
        if int(value) < -0x80000000 or int(value) > 0x7FFFFFFF:
            raise ValueError(f"Value {value} out of range for int32")
        return int(value).to_bytes(4, "little", signed=True)
    if codec == "f32":
        return struct.pack("<f", float(value))
    raise ValueError(f"Unsupported codec: {codec}")


def _maybe_round_float(value: float) -> float:
    rounded = round(value, 4)
    if abs(rounded - int(rounded)) < 1e-6:
        return float(int(rounded))
    return rounded


@dataclass(frozen=True)
class ValueSpan:
    payload_offset: int
    width: int
    codec: ValueKind
    label: str
    source_path: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["payload_offset_hex"] = hex(self.payload_offset)
        return data


@dataclass
class SemanticField:
    field_id: str
    label: str
    category: str
    value_type: str
    value: FieldValue
    editable: bool
    status: IdentifierStatus
    confidence: float
    source_path: str
    spans: list[ValueSpan] = field(default_factory=list)
    min_value: int | float | None = None
    max_value: int | float | None = None
    notes: list[str] = field(default_factory=list)
    current_mode: str | None = None
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "label": self.label,
            "category": self.category,
            "value_type": self.value_type,
            "value": self.value,
            "editable": self.editable,
            "status": self.status,
            "confidence": self.confidence,
            "source_path": self.source_path,
            "spans": [span.to_dict() for span in self.spans],
            "min_value": self.min_value,
            "max_value": self.max_value,
            "notes": list(self.notes),
            "current_mode": self.current_mode,
            "aliases": list(self.aliases),
        }


@dataclass
class SemanticRecord:
    record_id: str
    kind: RecordKind
    label: str
    block_index: int | None
    classification: str
    confidence: float
    identity_status: IdentifierStatus
    actor_guid: str | None = None
    asset_guid: str | None = None
    character_ref_guid: str | None = None
    template_id: int | None = None
    template_name: str | None = None
    template_status: IdentifierStatus = "unresolved"
    template_resolution_source: TemplateResolutionSource = "unresolved"
    template_source_detail: str | None = None
    edit_status: RecordEditStatus = "risky"
    structure_signature: StructureSignature = "unknown"
    group_id: str | None = None
    group_kind: str | None = None
    group_size: int = 1
    scene_hint: SceneAssetHint | None = None
    fields: list[SemanticField] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def get_field(self, field_id: str) -> SemanticField | None:
        for item in self.fields:
            if item.field_id == field_id or field_id in item.aliases:
                return item
        return None

    def to_summary(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind,
            "label": self.label,
            "block_index": self.block_index,
            "classification": self.classification,
            "confidence": self.confidence,
            "identity_status": self.identity_status,
            "actor_guid": self.actor_guid,
            "asset_guid": self.asset_guid,
            "character_ref_guid": self.character_ref_guid,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "template_status": self.template_status,
            "template_resolution_source": self.template_resolution_source,
            "template_source_detail": self.template_source_detail,
            "edit_status": self.edit_status,
            "structure_signature": self.structure_signature,
            "group_id": self.group_id,
            "group_kind": self.group_kind,
            "group_size": self.group_size,
            "scene_hint": self.scene_hint.to_dict() if self.scene_hint else None,
            "field_count": len(self.fields),
            "notes": list(self.notes),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.to_summary()
        payload["fields"] = [field.to_dict() for field in self.fields]
        return payload


@dataclass
class NaheulbeukSaveModel:
    game_id: str
    filepath: str
    gzip_offset: int
    character_count: int
    economy_count: int
    warnings: list[str]
    characters: list[SemanticRecord]
    economy: list[SemanticRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "filepath": self.filepath,
            "gzip_offset": self.gzip_offset,
            "gzip_offset_hex": hex(self.gzip_offset),
            "character_count": self.character_count,
            "economy_count": self.economy_count,
            "warnings": list(self.warnings),
            "characters": [character.to_dict() for character in self.characters],
            "economy": [record.to_dict() for record in self.economy],
        }


@dataclass(frozen=True)
class SemanticPatchInput:
    record_id: str
    field_id: str
    value: int | float
    allow_ambiguous: bool = False
    allow_identity_ambiguous: bool = False


@dataclass
class PlannedPatch:
    record_id: str
    record_label: str
    field_id: str
    field_label: str
    old_value: FieldValue
    new_value: int | float
    value_type: str
    spans: list[ValueSpan]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_label": self.record_label,
            "field_id": self.field_id,
            "field_label": self.field_label,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "value_type": self.value_type,
            "spans": [span.to_dict() for span in self.spans],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CharacterAssetIdentity:
    template_name: str
    bundle_name: str
    bundle_path: str
    script_name: str


def _record_identity_requires_opt_in(record: SemanticRecord) -> bool:
    if record.kind != "character":
        return False
    return (
        record.identity_status != "resolved"
        or record.template_status != "resolved"
        or record.classification not in SAFE_CHARACTER_CLASSIFICATIONS
    )


def _record_edit_status(record: SemanticRecord) -> RecordEditStatus:
    if record.kind == "economy":
        return "economy"
    if record.classification == "environment":
        return "unresolved"
    if not _record_identity_requires_opt_in(record):
        return "safe"
    if record.structure_signature in {"combat_entity", "camera_bound_combat_entity"}:
        return "risky"
    return "unresolved"


def record_matches_filters(
    record: SemanticRecord,
    *,
    edit_status: str = "all",
    classification: str = "all",
) -> bool:
    if edit_status != "all" and record.edit_status != edit_status:
        return False
    if classification != "all":
        if record.kind != "character":
            return False
        if record.classification != classification:
            return False
    return True


def _infer_structure_signature(
    block: bytes,
    *,
    actor_guid: str | None,
    asset_guid: str | None,
) -> tuple[StructureSignature, list[str]]:
    has_objective = _find_exact_token(block, b"m_objectiveMarker") != -1
    has_faction = _find_exact_token(block, b"m_faction") != -1
    has_squad = _find_exact_token(block, b"m_squad") != -1
    has_skills = _find_exact_token(block, b"m_skills") != -1
    has_states = _find_exact_token(block, b"m_states") != -1
    has_item_ref = _find_exact_token(block, b"m_itemRef") != -1
    has_camera = _find_exact_token(block, b"m_camera") != -1
    has_follow = _find_exact_token(block, b"m_follow") != -1

    combat_markers = sum(
        1 for flag in (has_objective, has_faction, has_squad, has_skills, has_states, has_item_ref) if flag
    )

    if actor_guid and combat_markers >= 4:
        if has_camera or has_follow:
            return (
                "camera_bound_combat_entity",
                ["Record matches combat-entity signature and also carries camera/follow references."],
            )
        return (
            "combat_entity",
            ["Record matches combat-entity signature (actor/faction/objective/skills/item refs)."],
        )

    if asset_guid and combat_markers >= 3:
        return (
            "combat_entity",
            ["Record matches combat-entity signature through asset-linked combat fields."],
        )

    if actor_guid or asset_guid:
        return ("unknown", [])

    if has_skills or has_states or has_item_ref:
        return (
            "partial_stats_block",
            ["Stats block was parsed, but no stable actor/asset identity could be resolved."],
        )
    return ("unknown", [])


def _cluster_key(record: SemanticRecord) -> tuple[str, str]:
    if record.kind == "economy":
        return ("economy", record.record_id)
    if record.asset_guid:
        return ("asset_guid", record.asset_guid)
    if record.actor_guid:
        return ("actor_guid", record.actor_guid)
    if record.template_id is not None:
        return ("template_id", str(record.template_id))
    return ("record_id", record.record_id)


def _apply_record_clusters(records: list[SemanticRecord]) -> None:
    buckets: dict[tuple[str, str], list[SemanticRecord]] = {}
    for record in records:
        key = _cluster_key(record)
        buckets.setdefault(key, []).append(record)

    for (group_kind, raw_value), items in buckets.items():
        if group_kind == "record_id":
            group_id = raw_value
        elif group_kind == "template_id":
            group_id = f"template:{raw_value}"
        else:
            group_id = f"{group_kind}:{raw_value[:12]}"
        for item in items:
            item.group_kind = group_kind
            item.group_id = group_id
            item.group_size = len(items)


def _extract_guid_from_window(blob: bytes, start: int, end: int) -> str | None:
    match = GUID_RE.search(blob[start:end])
    if not match:
        return None
    return match.group().decode("ascii")


def _direct_field(
    block: bytes,
    block_start: int,
    token: bytes,
    *,
    field_id: str,
    label: str,
    category: str,
    codec: ValueKind,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
) -> SemanticField:
    pos = _find_exact_token(block, token)
    if pos == -1 or pos + len(token) + 4 > len(block):
        return SemanticField(
            field_id=field_id,
            label=label,
            category=category,
            value_type=codec,
            value=None,
            editable=False,
            status="unresolved",
            confidence=0.0,
            source_path=token.decode("ascii"),
            min_value=min_value,
            max_value=max_value,
            notes=["Field token not found in this character block."],
        )

    payload_offset = block_start + pos + len(token)
    value = _decode_value(codec, block[pos + len(token) : pos + len(token) + 4])
    if codec == "f32":
        value = _maybe_round_float(float(value))

    return SemanticField(
        field_id=field_id,
        label=label,
        category=category,
        value_type=codec,
        value=value,
        editable=True,
        status="resolved",
        confidence=0.98,
        source_path=token.decode("ascii"),
        spans=[
            ValueSpan(
                payload_offset=payload_offset,
                width=4,
                codec=codec,
                label=label,
                source_path=token.decode("ascii"),
            )
        ],
        min_value=min_value,
        max_value=max_value,
    )


def _nested_field(
    block: bytes,
    block_start: int,
    token: bytes,
    *,
    field_id: str,
    label: str,
    category: str,
    codec: ValueKind,
    child_token: bytes,
    next_tokens: Iterable[bytes],
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    notes: list[str] | None = None,
) -> SemanticField:
    pos = _find_exact_token(block, token)
    if pos == -1:
        return SemanticField(
            field_id=field_id,
            label=label,
            category=category,
            value_type=codec,
            value=None,
            editable=False,
            status="unresolved",
            confidence=0.0,
            source_path=f"{token.decode('ascii')}.{child_token.decode('ascii')}",
            min_value=min_value,
            max_value=max_value,
            notes=["Parent object token not found in this character block."],
        )

    end = len(block)
    for candidate in next_tokens:
        next_pos = _find_exact_token(block, candidate, pos + len(token))
        if next_pos != -1:
            end = min(end, next_pos)

    child_pos = _find_exact_token(block, child_token, pos, end)
    if child_pos == -1 or child_pos + len(child_token) + 4 > end:
        return SemanticField(
            field_id=field_id,
            label=label,
            category=category,
            value_type=codec,
            value=None,
            editable=False,
            status="unresolved",
            confidence=0.0,
            source_path=f"{token.decode('ascii')}.{child_token.decode('ascii')}",
            min_value=min_value,
            max_value=max_value,
            notes=["Nested value token not found inside the expected object window."],
        )

    payload_offset = block_start + child_pos + len(child_token)
    value = _decode_value(codec, block[child_pos + len(child_token) : child_pos + len(child_token) + 4])
    if codec == "f32":
        value = _maybe_round_float(float(value))

    field_notes = list(notes or [])
    return SemanticField(
        field_id=field_id,
        label=label,
        category=category,
        value_type=codec,
        value=value,
        editable=True,
        status="resolved",
        confidence=0.94,
        source_path=f"{token.decode('ascii')}.{child_token.decode('ascii')}",
        spans=[
            ValueSpan(
                payload_offset=payload_offset,
                width=4,
                codec=codec,
                label=label,
                source_path=f"{token.decode('ascii')}.{child_token.decode('ascii')}",
            )
        ],
        min_value=min_value,
        max_value=max_value,
        notes=field_notes,
    )


def _override_field(
    block: bytes,
    block_start: int,
    token: bytes,
    *,
    field_id: str,
    label: str,
    category: str,
    next_tokens: Iterable[bytes],
) -> SemanticField:
    pos = _find_exact_token(block, token)
    source_path = f"{token.decode('ascii')}.m_baseValueOverride"
    if pos == -1:
        return SemanticField(
            field_id=field_id,
            label=label,
            category=category,
            value_type="s32",
            value=None,
            editable=False,
            status="unresolved",
            confidence=0.0,
            source_path=source_path,
            notes=["CharacterStatistic block not found."],
        )

    end = len(block)
    for candidate in next_tokens:
        next_pos = _find_exact_token(block, candidate, pos + len(token))
        if next_pos != -1:
            end = min(end, next_pos)

    base_pos = _find_exact_token(block, b"m_baseValueOverride", pos, end)
    value_pos = _find_exact_token(block, b"m_value", pos, end)
    spans: list[ValueSpan] = []

    base_value: int | None = None
    cache_value: int | None = None
    if base_pos != -1 and base_pos + len(b"m_baseValueOverride") + 4 <= end:
        offset = block_start + base_pos + len(b"m_baseValueOverride")
        base_value = int.from_bytes(
            block[base_pos + len(b"m_baseValueOverride") : base_pos + len(b"m_baseValueOverride") + 4],
            "little",
            signed=True,
        )
        spans.append(
            ValueSpan(
                payload_offset=offset,
                width=4,
                codec="s32",
                label=f"{label} base override",
                source_path=f"{token.decode('ascii')}.m_baseValueOverride",
            )
        )

    if value_pos != -1 and value_pos + len(b"m_value") + 4 <= end:
        offset = block_start + value_pos + len(b"m_value")
        cache_value = int.from_bytes(
            block[value_pos + len(b"m_value") : value_pos + len(b"m_value") + 4],
            "little",
            signed=True,
        )
        spans.append(
            ValueSpan(
                payload_offset=offset,
                width=4,
                codec="s32",
                label=f"{label} cached value",
                source_path=f"{token.decode('ascii')}.m_value",
            )
        )

    if not spans:
        return SemanticField(
            field_id=field_id,
            label=label,
            category=category,
            value_type="s32",
            value=None,
            editable=False,
            status="unresolved",
            confidence=0.0,
            source_path=source_path,
            notes=["Override and cached value slots were not found."],
        )

    current_mode = "auto"
    current_value: FieldValue = None
    confidence = 0.62
    status: IdentifierStatus = "ambiguous"
    notes = [
        "This field is stored as CharacterStatistic override/cached value.",
        "When the override is -1, the save falls back to class-derived runtime logic.",
        "Setting a value writes both m_baseValueOverride and m_value for deterministic replay.",
    ]

    if base_value is not None and base_value >= 0:
        current_mode = "override"
        current_value = base_value
        confidence = 0.88
        status = "resolved"
    elif cache_value is not None and cache_value >= 0:
        current_mode = "cached"
        current_value = cache_value
        confidence = 0.74

    return SemanticField(
        field_id=field_id,
        label=label,
        category=category,
        value_type="s32",
        value=current_value,
        editable=True,
        status=status,
        confidence=confidence,
        source_path=source_path,
        spans=spans,
        min_value=-1,
        max_value=9999,
        notes=notes,
        current_mode=current_mode,
    )


def _build_character_fields(block: bytes, block_start: int) -> list[SemanticField]:
    specs: list[SemanticField] = [
        _nested_field(
            block,
            block_start,
            b"m_health",
            field_id="health",
            label="Health",
            category="resources",
            codec="s32",
            child_token=b"m_value",
            next_tokens=[b"m_agility"],
            min_value=0,
            max_value=999999,
        ),
        _nested_field(
            block,
            block_start,
            b"m_energy",
            field_id="energy",
            label="Energy",
            category="resources",
            codec="s32",
            child_token=b"m_value",
            next_tokens=[b"m_health"],
            min_value=0,
            max_value=999999,
        ),
        _override_field(
            block,
            block_start,
            b"m_agility",
            field_id="agility",
            label="Agility",
            category="base_attributes",
            next_tokens=[b"m_charisma"],
        ),
        _override_field(
            block,
            block_start,
            b"m_charisma",
            field_id="charisma",
            label="Charisma",
            category="base_attributes",
            next_tokens=[b"m_cleverness"],
        ),
        _override_field(
            block,
            block_start,
            b"m_cleverness",
            field_id="cleverness",
            label="Cleverness",
            category="base_attributes",
            next_tokens=[b"m_constitution"],
        ),
        _override_field(
            block,
            block_start,
            b"m_constitution",
            field_id="constitution",
            label="Constitution",
            category="base_attributes",
            next_tokens=[b"m_courage"],
        ),
        _override_field(
            block,
            block_start,
            b"m_courage",
            field_id="courage",
            label="Courage",
            category="base_attributes",
            next_tokens=[b"m_inflictedDamagePercentage"],
        ),
        _override_field(
            block,
            block_start,
            b"m_strength",
            field_id="strength",
            label="Strength",
            category="base_attributes",
            next_tokens=[b"m_level"],
        ),
        _nested_field(
            block,
            block_start,
            b"m_level",
            field_id="level",
            label="Level",
            category="progression",
            codec="u32",
            child_token=b"m_currentLevel",
            next_tokens=[b"m_currentXp"],
            min_value=0,
            max_value=999,
        ),
        _direct_field(
            block,
            block_start,
            b"m_currentXp",
            field_id="current_xp",
            label="Current XP",
            category="progression",
            codec="u32",
            min_value=0,
            max_value=999999999,
        ),
        _direct_field(
            block,
            block_start,
            b"m_statsPoints",
            field_id="stats_points",
            label="Stats Points",
            category="progression_points",
            codec="u32",
            min_value=0,
            max_value=99999,
        ),
        _direct_field(
            block,
            block_start,
            b"m_activeSkillPoints",
            field_id="active_skill_points",
            label="Active Skill Points",
            category="progression_points",
            codec="u32",
            min_value=0,
            max_value=99999,
        ),
        _direct_field(
            block,
            block_start,
            b"m_passiveSkillPoints",
            field_id="passive_skill_points",
            label="Passive Skill Points",
            category="progression_points",
            codec="u32",
            min_value=0,
            max_value=99999,
        ),
        _nested_field(
            block,
            block_start,
            b"m_dodge",
            field_id="dodge",
            label="Dodge",
            category="combat",
            codec="f32",
            child_token=b"m_dividerMalus",
            next_tokens=[b"m_parry"],
            min_value=0.0,
            max_value=1000.0,
            notes=["Stored as CharacterDodge.m_dividerMalus, not a plain integer stat."],
        ),
        _nested_field(
            block,
            block_start,
            b"m_parry",
            field_id="parry",
            label="Parry",
            category="combat",
            codec="f32",
            child_token=b"m_dividerMalus",
            next_tokens=[b"m_tags"],
            min_value=0.0,
            max_value=1000.0,
            notes=["Stored as CharacterParry.m_dividerMalus, not a plain integer stat."],
        ),
    ]
    return specs


def _extract_actor_guid(block: bytes) -> str | None:
    actor_pos = _rfind_exact_token(block, b"m_actor")
    if actor_pos == -1:
        return None
    return _extract_guid_from_window(block, actor_pos, min(len(block), actor_pos + 128))


def _extract_asset_guid(block: bytes) -> str | None:
    actor_pos = _rfind_exact_token(block, b"m_actor")
    if actor_pos == -1:
        return None
    asset_pos = _rfind_exact_token(block, b"m_asset", 0, actor_pos)
    if asset_pos == -1:
        return None
    return _extract_guid_from_window(block, asset_pos, min(len(block), asset_pos + 128))


def _extract_character_ref_guid(block: bytes) -> str | None:
    pos = _find_exact_token(block, b"m_characterRef")
    if pos == -1:
        return None
    return _extract_guid_from_window(block, pos, min(len(block), pos + 160))


def _extract_template_id(block: bytes) -> int | None:
    risk_pos = _rfind_exact_token(block, b"m_riskLevel")
    search_start = risk_pos if risk_pos != -1 else 0
    unique_pos = _find_exact_token(block, b"m_uniqueInt", search_start)
    if unique_pos == -1:
        unique_pos = _rfind_exact_token(block, b"m_uniqueInt")
        if unique_pos == -1:
            return None

    value_start = unique_pos + len(b"m_uniqueInt")
    value_end = value_start + 4
    if value_end > len(block):
        return None
    return int.from_bytes(block[value_start:value_end], "little", signed=False)


def _classify_character(template_name: str | None) -> tuple[str, IdentifierStatus, float]:
    if not template_name:
        return "unknown", "ambiguous", 0.55
    if template_name in PARTY_ASSET_NAMES:
        return "party", "resolved", 0.95
    if "Adventurer_" in template_name or "Companion" in template_name:
        return "companion", "resolved", 0.84
    if template_name.startswith("AS_"):
        return "npc", "resolved", 0.9
    return "unknown", "ambiguous", 0.6


def _record_label(
    block_index: int,
    actor_guid: str | None,
    asset_guid: str | None,
    template_name: str | None,
    structure_signature: StructureSignature = "unknown",
    template_id: int | None = None,
    scene_hint: SceneAssetHint | None = None,
) -> str:
    if template_name:
        head = template_name
    elif scene_hint is not None:
        head = scene_hint.display_label
    elif structure_signature == "camera_bound_combat_entity":
        head = f"Combat Camera Entity T{template_id}" if template_id is not None else "Combat Camera Entity"
    elif structure_signature == "combat_entity":
        head = f"Combat Entity T{template_id}" if template_id is not None else "Combat Entity"
    elif structure_signature == "partial_stats_block":
        head = f"Partial Stats Block T{template_id}" if template_id is not None else "Partial Stats Block"
    else:
        head = f"Character {block_index:02d}"

    parts = [head]
    if head != f"Character {block_index:02d}":
        parts.append(f"Character {block_index:02d}")
    if actor_guid:
        parts.append(actor_guid[:8])
    elif asset_guid:
        parts.append(asset_guid[:8])
    return " · ".join(parts)


def _build_character_record(
    block: bytes,
    block_start: int,
    block_index: int,
    template_map: dict[int, str],
    max_template_id: int,
) -> SemanticRecord | None:
    fields = _build_character_fields(block, block_start)
    resolved_fields = [item for item in fields if item.status != "unresolved"]
    actor_guid = _extract_actor_guid(block)
    if not actor_guid and len(resolved_fields) < 4:
        return None

    asset_guid = _extract_asset_guid(block)
    character_ref_guid = _extract_character_ref_guid(block)
    template_id = _extract_template_id(block)
    structure_signature, signature_notes = _infer_structure_signature(
        block,
        actor_guid=actor_guid,
        asset_guid=asset_guid,
    )
    template_name = template_map.get(template_id) if template_id is not None else None
    template_status: IdentifierStatus = "unresolved"
    template_resolution_source: TemplateResolutionSource = "unresolved"
    template_source_detail: str | None = None
    if template_name is not None:
        template_status = "resolved"
        template_resolution_source = "indexed_table"
        template_source_detail = "save:indexed_string_table"
    elif template_id is not None and template_id <= max_template_id:
        template_status = "ambiguous"
    classification, _, template_confidence = _classify_character(template_name)

    record_id = (
        f"character-{block_index:03d}-{actor_guid[:12]}"
        if actor_guid
        else f"stats-block-{block_index:03d}"
    )
    notes: list[str] = []
    if all(field.current_mode != "override" for field in fields if field.category == "base_attributes"):
        notes.append("Base attributes are currently in auto mode until an override is written.")
    notes.extend(signature_notes)
    if not asset_guid:
        notes.append("Asset guid could not be resolved from the local weak-reference window.")
    if template_id is None:
        notes.append("Template id (m_uniqueInt) could not be resolved from the actor section.")
    elif template_name is None and template_id > max_template_id:
        notes.append(
            f"Template id {template_id} is outside the indexed string table range "
            f"(max known id {max_template_id})."
        )
    elif template_name is not None:
        notes.append(f"Resolved template name from indexed table: {template_name}.")

    identity_status: IdentifierStatus
    if template_status == "resolved":
        identity_status = "resolved"
    elif structure_signature == "partial_stats_block" and not actor_guid and not asset_guid:
        identity_status = "unresolved"
    elif actor_guid or asset_guid or character_ref_guid or template_id is not None:
        identity_status = "ambiguous"
    else:
        identity_status = "unresolved"
    base_confidence = 0.92 if actor_guid else 0.46
    confidence = max(base_confidence, template_confidence)

    record = SemanticRecord(
        record_id=record_id,
        kind="character",
        label=_record_label(
            block_index,
            actor_guid,
            asset_guid,
            template_name,
            structure_signature,
            template_id,
            None,
        ),
        block_index=block_index,
        classification=classification,
        confidence=confidence,
        identity_status=identity_status,
        actor_guid=actor_guid,
        asset_guid=asset_guid,
        character_ref_guid=character_ref_guid,
        template_id=template_id,
        template_name=template_name,
        template_status=template_status,
        template_resolution_source=template_resolution_source,
        template_source_detail=template_source_detail,
        structure_signature=structure_signature,
        fields=fields,
        notes=notes,
    )
    record.edit_status = _record_edit_status(record)
    return record


def _apply_character_asset_resolution(
    records: list[SemanticRecord],
    asset_index: dict[str, CharacterAssetIdentity],
) -> int:
    resolved = 0
    for record in records:
        if not record.asset_guid:
            continue
        identity = asset_index.get(record.asset_guid)
        if identity is None:
            continue

        previous_name = record.template_name
        previous_source = record.template_resolution_source
        if previous_name == identity.template_name and previous_source == "game_character_asset":
            continue

        if previous_name and previous_name != identity.template_name:
            record.notes.append(
                "Indexed-table identity hint "
                f"{previous_name} conflicted with CharacterAsset {identity.template_name}; "
                "using asset-bundle identity."
            )
        else:
            record.notes.append(
                f"Resolved identity from {identity.script_name} in bundle {identity.bundle_name}: "
                f"{identity.template_name}."
            )

        classification, _, template_confidence = _classify_character(identity.template_name)
        record.template_name = identity.template_name
        record.template_status = "resolved"
        record.template_resolution_source = "game_character_asset"
        record.template_source_detail = f"{identity.script_name}:{identity.bundle_name}"
        record.classification = classification
        record.identity_status = "resolved"
        record.confidence = max(record.confidence, template_confidence, 0.97)
        record.label = _record_label(
            record.block_index or 0,
            record.actor_guid,
            record.asset_guid,
            record.template_name,
            record.structure_signature,
            record.template_id,
            record.scene_hint,
        )
        record.edit_status = _record_edit_status(record)
        resolved += 1

    return resolved


def _apply_scene_asset_hints(
    records: list[SemanticRecord],
    scene_hints: dict[str, SceneAssetHint],
) -> int:
    applied = 0
    for record in records:
        if record.template_name is not None or not record.asset_guid:
            continue
        hint = scene_hints.get(record.asset_guid)
        if hint is None:
            continue
        if record.scene_hint == hint:
            continue

        record.scene_hint = hint
        if hint.class_name in ENVIRONMENT_SCENE_CLASSES or hint.class_name.endswith("Spawner"):
            record.classification = "environment"
            record.identity_status = "resolved"
            record.confidence = max(record.confidence, 0.9)
            record.notes.append(
                "Scene bundles identify this asset as "
                f"{hint.class_name} on {hint.game_object_name or 'an unnamed object'} "
                f"({hint.scene_path}); this is treated as environment/spawner data, not a safe character target."
            )
        else:
            record.notes.append(
                "Scene bundles expose a stable non-template owner "
                f"{hint.class_name} ({hint.scene_path}), but no CharacterAsset identity was found."
            )
            record.confidence = max(record.confidence, 0.76)
        record.label = _record_label(
            record.block_index or 0,
            record.actor_guid,
            record.asset_guid,
            record.template_name,
            record.structure_signature,
            record.template_id,
            hint,
        )
        record.edit_status = _record_edit_status(record)
        applied += 1

    return applied


def _annotate_missing_character_asset_resolution(
    records: list[SemanticRecord],
    asset_index: dict[str, CharacterAssetIdentity],
) -> int:
    annotated = 0
    if not asset_index:
        return annotated

    for record in records:
        if not record.asset_guid:
            continue
        if record.asset_guid in asset_index:
            continue
        note = (
            "Installed game assets did not expose a CharacterAsset entry for "
            f"asset_guid={record.asset_guid}."
        )
        if note not in record.notes:
            record.notes.append(note)
            annotated += 1
    return annotated


def _annotate_missing_scene_hint_resolution(
    records: list[SemanticRecord],
    scene_hints: dict[str, SceneAssetHint],
    *,
    resolver_available: bool,
) -> int:
    annotated = 0
    if not resolver_available:
        return annotated

    for record in records:
        if not record.asset_guid:
            continue
        if record.template_name is not None or record.scene_hint is not None:
            continue
        if record.asset_guid in scene_hints:
            continue
        note = (
            "Installed scene bundles did not expose a stable scene owner for "
            f"asset_guid={record.asset_guid}."
        )
        if note not in record.notes:
            record.notes.append(note)
            annotated += 1
    return annotated


def _guid_index(
    records: list[SemanticRecord],
    attribute: str,
) -> dict[str, SemanticRecord]:
    index: dict[str, SemanticRecord] = {}
    ambiguous: set[str] = set()
    for record in records:
        guid = getattr(record, attribute)
        if not guid:
            continue
        if guid in ambiguous:
            continue
        if guid in index:
            # Ambiguous source guid - do not trust it for propagation.
            index.pop(guid, None)
            ambiguous.add(guid)
            continue
        index[guid] = record
    return index


def _can_propagate_identity(target: SemanticRecord, source: SemanticRecord) -> bool:
    if target.scene_hint is not None:
        return False
    if target.asset_guid and source.asset_guid and target.asset_guid != source.asset_guid:
        return False
    return True


def _apply_template_fallbacks(records: list[SemanticRecord]) -> int:
    resolved_sources = [
        record
        for record in records
        if record.template_name and record.template_status == "resolved"
    ]
    if not resolved_sources:
        return 0

    actor_index = _guid_index(resolved_sources, "actor_guid")
    asset_index = _guid_index(resolved_sources, "asset_guid")
    character_ref_index = _guid_index(resolved_sources, "character_ref_guid")
    propagated = 0

    def _propagate_from(
        target: SemanticRecord,
        source: SemanticRecord,
        source_label: TemplateResolutionSource,
        key_name: str,
    ) -> None:
        nonlocal propagated
        if source.template_name is None:
            return
        if target.template_name is not None:
            return

        target.template_name = source.template_name
        if target.template_id is None:
            target.template_id = source.template_id
        target.template_status = "ambiguous"
        target.template_resolution_source = source_label
        target.template_source_detail = source.template_source_detail
        target.classification = source.classification
        target.identity_status = "ambiguous"
        target.confidence = max(target.confidence, 0.78 if source_label == "actor_guid_propagation" else 0.68)
        target.label = _record_label(
            target.block_index or 0,
            target.actor_guid,
            target.asset_guid,
            target.template_name,
            target.structure_signature,
            target.template_id,
        )
        target.notes.append(
            "Template name inferred via "
            f"{key_name} from {source.record_id} ({source.template_name})."
        )
        target.edit_status = _record_edit_status(target)
        propagated += 1

    for record in records:
        if record.template_name is not None or record.scene_hint is not None:
            continue
        if record.actor_guid and record.actor_guid in actor_index:
            source = actor_index[record.actor_guid]
            if _can_propagate_identity(record, source):
                _propagate_from(record, source, "actor_guid_propagation", "actor_guid")
                continue
        if record.character_ref_guid and record.character_ref_guid in character_ref_index:
            source = character_ref_index[record.character_ref_guid]
            if _can_propagate_identity(record, source):
                _propagate_from(
                    record,
                    source,
                    "character_ref_propagation",
                    "character_ref_guid",
                )
                continue
        if record.asset_guid and record.asset_guid in asset_index:
            source = asset_index[record.asset_guid]
            if _can_propagate_identity(record, source):
                _propagate_from(record, source, "asset_guid_propagation", "asset_guid")
            continue

    return propagated


def _build_economy_records(payload: bytes) -> list[SemanticRecord]:
    records: list[SemanticRecord] = []
    for index, field_offset in enumerate(_find_all_exact_tokens(payload, GOLD_TOKEN), start=1):
        value_offset = field_offset + len(GOLD_TOKEN)
        if value_offset + 4 > len(payload):
            continue
        value = int.from_bytes(payload[value_offset : value_offset + 4], "little", signed=False)
        field = SemanticField(
            field_id="gold",
            label="Gold",
            category="economy",
            value_type="u32",
            value=value,
            editable=True,
            status="ambiguous",
            confidence=0.3,
            source_path="m_gold",
            spans=[
                ValueSpan(
                    payload_offset=value_offset,
                    width=4,
                    codec="u32",
                    label="Gold",
                    source_path="m_gold",
                )
            ],
            min_value=0,
            max_value=0xFFFFFFFF,
            notes=["Owner mapping is unresolved. This is exposed as an economy slot, not a character field."],
        )
        records.append(
            SemanticRecord(
                record_id=f"gold-slot-{index:03d}",
                kind="economy",
                label=f"Gold Slot {index:02d}",
                block_index=None,
                classification="unresolved_owner",
                confidence=0.3,
                identity_status="ambiguous",
                edit_status="economy",
                structure_signature="unknown",
                group_id=f"economy:{index:03d}",
                group_kind="economy",
                group_size=1,
                fields=[field],
                notes=["Gold slot order is not stable enough to claim ownership automatically."],
            )
        )
    return records


def inspect_naheulbeuk_save(filepath: Path | str) -> NaheulbeukSaveModel:
    path = Path(filepath)
    container = path.read_bytes()
    extracted = extract_gzip_payload(container)
    payload = bytes(extracted.decompressed)
    template_map, max_template_id = _build_template_string_map(payload)
    character_asset_index, character_asset_bundle_root = _discover_character_asset_index()

    starts = _find_all_exact_tokens(payload, BLOCK_START)
    characters: list[SemanticRecord] = []
    for index, start in enumerate(starts, start=1):
        end = starts[index] if index < len(starts) else len(payload)
        record = _build_character_record(
            payload[start:end],
            start,
            index,
            template_map,
            max_template_id,
        )
        if record is not None:
            characters.append(record)

    character_asset_resolved_count = _apply_character_asset_resolution(characters, character_asset_index)
    unresolved_asset_guids = sorted(
        {
            record.asset_guid
            for record in characters
            if record.asset_guid and record.template_name is None
        }
    )
    scene_hint_index, scene_hint_root = _discover_scene_asset_hints(unresolved_asset_guids)
    scene_hint_applied_count = _apply_scene_asset_hints(characters, scene_hint_index)
    scene_hint_missing_count = _annotate_missing_scene_hint_resolution(
        characters,
        scene_hint_index,
        resolver_available=scene_hint_root is not None,
    )
    character_asset_missing_count = _annotate_missing_character_asset_resolution(characters, character_asset_index)
    fallback_resolved_count = _apply_template_fallbacks(characters)
    _apply_record_clusters(characters)
    template_resolved_count = sum(1 for item in characters if item.template_status == "resolved")
    template_inferred_count = sum(
        1
        for item in characters
        if item.template_name is not None and item.template_status == "ambiguous"
    )
    template_unresolved_count = sum(1 for item in characters if item.template_name is None)
    safe_count = sum(1 for item in characters if item.edit_status == "safe")
    risky_count = sum(1 for item in characters if item.edit_status == "risky")
    unresolved_count = sum(1 for item in characters if item.edit_status == "unresolved")
    party_count = sum(1 for item in characters if item.classification == "party")
    companion_count = sum(1 for item in characters if item.classification == "companion")
    npc_count = sum(1 for item in characters if item.classification == "npc")
    environment_count = sum(1 for item in characters if item.classification == "environment")

    warnings = [
        "Naheulbeuk base attributes are written through CharacterStatistic override pairs. "
        "When a field is in auto mode, the save does not expose a trusted absolute stat value.",
        "Dodge and parry are stored as divider malus floats inside their objects, not as plain integers.",
        "Gold ownership is unresolved and remains exposed as standalone economy slots.",
        "Template resolver prefers CharacterAsset guid lookups from the installed game. "
        "Without those assets, indexed string tables remain a weaker fallback hint only.",
        "Scene-hint resolver inspects installed scene bundles for unresolved asset_guid values and demotes "
        "non-character world entities out of the normal semantic character flow.",
        "Fallback resolver may infer template names via guid links and marks these records as ambiguous.",
        "Classification is semantic-best-effort: party detection only auto-resolves known playable AS_* templates.",
        (
            "Template resolver summary: "
            f"resolved={template_resolved_count}, inferred={template_inferred_count}, "
            f"unresolved={template_unresolved_count}, fallback_hits={fallback_resolved_count}, "
            f"character_asset_hits={character_asset_resolved_count}, "
            f"character_asset_misses={character_asset_missing_count}, "
            f"scene_hint_hits={scene_hint_applied_count}, "
            f"scene_hint_misses={scene_hint_missing_count}, "
            f"safe={safe_count}, risky={risky_count}, unresolved_records={unresolved_count}, "
            f"party={party_count}, companion={companion_count}, npc={npc_count}, "
            f"environment={environment_count}."
        ),
    ]
    if character_asset_bundle_root is not None:
        warnings.insert(
            3,
            "CharacterAsset resolver loaded from "
            f"{character_asset_bundle_root}; asset_guid is preferred over indexed-table hints.",
        )
    else:
        warnings.insert(
            3,
            "CharacterAsset resolver is unavailable; installed game assets were not discovered, "
            "so exact identity may be weaker.",
        )
    if scene_hint_root is not None:
        warnings.insert(
            4,
            "Scene-hint resolver loaded from "
            f"{scene_hint_root}; unresolved asset_guid values can be classified as scene-bound entities.",
        )
    else:
        warnings.insert(
            4,
            "Scene-hint resolver is unavailable; unresolved asset_guid values remain generic until a stronger source appears.",
        )
    economy = _build_economy_records(payload)
    return NaheulbeukSaveModel(
        game_id="naheulbeuk",
        filepath=str(path),
        gzip_offset=extracted.gzip_offset,
        character_count=len(characters),
        economy_count=len(economy),
        warnings=warnings,
        characters=characters,
        economy=economy,
    )


def _record_lookup(model: NaheulbeukSaveModel) -> dict[str, SemanticRecord]:
    lookup: dict[str, SemanticRecord] = {}
    for record in [*model.characters, *model.economy]:
        lookup[record.record_id] = record
    return lookup


def plan_semantic_patches(
    model: NaheulbeukSaveModel,
    patch_inputs: Iterable[SemanticPatchInput],
) -> list[PlannedPatch]:
    lookup = _record_lookup(model)
    plans: list[PlannedPatch] = []
    touched_offsets: dict[int, str] = {}

    for patch in patch_inputs:
        record = lookup.get(patch.record_id)
        if record is None:
            raise SemanticPatchValidationError(f"Unknown record_id: {patch.record_id}")
        if record.classification == "environment":
            raise SemanticPatchBlockedError(
                "Record is classified as scene/environment data rather than a character: "
                f"record_id={record.record_id}, scene_hint="
                f"{record.scene_hint.class_name if record.scene_hint else 'n/a'}. "
                "Use Expert Mode / raw patching if you intentionally want to touch this block."
            )
        if _record_identity_requires_opt_in(record) and not patch.allow_identity_ambiguous:
            raise SemanticPatchValidationError(
                "Record identity is not fully resolved for semantic patching: "
                f"record_id={record.record_id}, classification={record.classification}, "
                f"identity_status={record.identity_status}, template_status={record.template_status}, "
                f"template_source={record.template_resolution_source}. "
                "Pass allow_identity_ambiguous=true to patch this record explicitly."
            )

        field = record.get_field(patch.field_id)
        if field is None:
            raise SemanticPatchValidationError(f"Unknown field '{patch.field_id}' for record {patch.record_id}")
        if not field.editable:
            raise SemanticPatchValidationError(f"Field '{patch.field_id}' is not editable")
        if field.status == "unresolved":
            raise SemanticPatchBlockedError(f"Field '{patch.field_id}' is unresolved and cannot be patched")
        if field.status == "ambiguous" and not patch.allow_ambiguous:
            raise SemanticPatchValidationError(
                f"Field '{patch.field_id}' is ambiguous; pass allow_ambiguous=true to patch it"
            )
        if not field.spans:
            raise SemanticPatchValidationError(f"Field '{patch.field_id}' has no patch spans")

        numeric_value = float(patch.value) if field.value_type == "f32" else int(patch.value)
        if field.min_value is not None and numeric_value < field.min_value:
            raise SemanticPatchValidationError(
                f"Value {numeric_value} below minimum {field.min_value} for field '{patch.field_id}'"
            )
        if field.max_value is not None and numeric_value > field.max_value:
            raise SemanticPatchValidationError(
                f"Value {numeric_value} above maximum {field.max_value} for field '{patch.field_id}'"
            )

        for span in field.spans:
            owner = touched_offsets.get(span.payload_offset)
            if owner is not None:
                raise SemanticPatchValidationError(
                    f"Offset conflict at {hex(span.payload_offset)} between {owner} and {patch.record_id}:{field.field_id}"
                )
            touched_offsets[span.payload_offset] = f"{patch.record_id}:{field.field_id}"

        plan_notes = list(field.notes)
        if patch.allow_identity_ambiguous:
            plan_notes.append(
                "Patch allowed with explicit identity opt-in for a non-fully-resolved record."
            )
        if patch.allow_ambiguous:
            plan_notes.append(
                "Patch allowed with explicit field ambiguity opt-in."
            )

        plans.append(
            PlannedPatch(
                record_id=record.record_id,
                record_label=record.label,
                field_id=field.field_id,
                field_label=field.label,
                old_value=field.value,
                new_value=numeric_value,
                value_type=field.value_type,
                spans=list(field.spans),
                notes=plan_notes,
            )
        )

    return plans


def _verify_expected_value(field: SemanticField, expected: int | float) -> bool:
    if field.value_type == "f32":
        if field.value is None:
            return False
        return abs(float(field.value) - float(expected)) < 1e-5
    return field.value == int(expected)


def apply_semantic_patches(
    filepath: Path | str,
    patch_inputs: Iterable[SemanticPatchInput],
    *,
    backup: bool = True,
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    path = Path(filepath)
    container = path.read_bytes()
    extracted = extract_gzip_payload(container)
    model = inspect_naheulbeuk_save(path)
    plans = plan_semantic_patches(model, list(patch_inputs))

    for plan in plans:
        for span in plan.spans:
            start = span.payload_offset
            end = start + span.width
            extracted.decompressed[start:end] = _encode_value(span.codec, plan.new_value)

    target = Path(output_path) if output_path else path
    if backup:
        PatchEngine()._create_backup(path)

    rebuilt = rebuild_gzip_container(container, extracted)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(rebuilt)

    reparsed = inspect_naheulbeuk_save(target)
    reparsed_lookup = _record_lookup(reparsed)
    results: list[dict[str, Any]] = []
    for plan in plans:
        record = reparsed_lookup.get(plan.record_id)
        field = record.get_field(plan.field_id) if record else None
        verified = bool(record and field and _verify_expected_value(field, plan.new_value))
        results.append(
            {
                "record_id": plan.record_id,
                "field_id": plan.field_id,
                "requested_value": plan.new_value,
                "verified": verified,
                "record_label": plan.record_label,
            }
        )

    return {
        "status": "success" if all(item["verified"] for item in results) else "partial_failed",
        "filepath": str(target),
        "planned_changes": [plan.to_dict() for plan in plans],
        "results": results,
        "model": reparsed.to_dict(),
    }
