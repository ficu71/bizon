# Core modules
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
    "ProfileManager",
    "GameProfile",
]
