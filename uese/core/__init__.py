# Core modules
from .naheulbeuk_semantic import (
    SemanticPatchInput,
    apply_semantic_patches,
    inspect_naheulbeuk_save,
    record_matches_filters,
)
from .naheulbeuk_app import (
    NaheulbeukAppError,
    NaheulbeukBlockedError,
    NaheulbeukInputError,
    NaheulbeukVerifyError,
    apply_naheulbeuk_semantic_patches,
    get_naheulbeuk_doctor_report,
    get_naheulbeuk_record,
    inspect_naheulbeuk,
    list_naheulbeuk_records,
    plan_naheulbeuk_semantic_patches,
)
from .patch_engine import PatchEngine
from .universal_scanner import ScanCandidate, UniversalScanner

try:
    from .profile_manager import GameProfile, ProfileManager
except Exception:  # optional dependency (pyyaml)
    GameProfile = None
    ProfileManager = None

__all__ = [
    "UniversalScanner",
    "ScanCandidate",
    "PatchEngine",
    "inspect_naheulbeuk_save",
    "apply_semantic_patches",
    "SemanticPatchInput",
    "record_matches_filters",
    "inspect_naheulbeuk",
    "list_naheulbeuk_records",
    "get_naheulbeuk_record",
    "plan_naheulbeuk_semantic_patches",
    "apply_naheulbeuk_semantic_patches",
    "get_naheulbeuk_doctor_report",
    "NaheulbeukAppError",
    "NaheulbeukInputError",
    "NaheulbeukVerifyError",
    "NaheulbeukBlockedError",
    "ProfileManager",
    "GameProfile",
]
