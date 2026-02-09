#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class GameProfile:
    def __init__(self, data: Dict[str, Any]):
        self.game_id = data.get("game_id", "")
        self.name = data.get("name", "")
        self.engine = data.get("engine", "unknown")
        self.save_locations = data.get("save_locations", {})
        self.save_pattern = data.get("save_pattern", "*.sav")
        self.fields = data.get("fields", {})
        self.version = data.get("version", "1.0")
        self.author = data.get("author", "")

    def get_field(self, field_name: str) -> Optional[Dict[str, Any]]:
        return self.fields.get(field_name)

    def set_field_offset(self, field_name: str, offset: int) -> None:
        if field_name in self.fields:
            self.fields[field_name]["offset"] = offset


class ProfileManager:
    def __init__(self, profiles_dir: Optional[Path] = None):
        if profiles_dir:
            self.profiles_dir = profiles_dir
        else:
            self.profiles_dir = Path(__file__).parent.parent.parent / "profiles"

    def load_profile(self, game_id: str) -> Optional[GameProfile]:
        profile_path = self.profiles_dir / f"{game_id}.yaml"
        if not profile_path.exists():
            return None

        with open(profile_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return GameProfile(data)

    def save_profile(self, profile: GameProfile) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_path = self.profiles_dir / f"{profile.game_id}.yaml"

        data = {
            "game_id": profile.game_id,
            "name": profile.name,
            "engine": profile.engine,
            "save_locations": profile.save_locations,
            "save_pattern": profile.save_pattern,
            "fields": profile.fields,
            "version": profile.version,
            "author": profile.author,
        }

        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def list_profiles(self) -> list[str]:
        if not self.profiles_dir.exists():
            return []

        profiles = []
        for yaml_file in self.profiles_dir.glob("*.yaml"):
            if yaml_file.stem != "template":
                profiles.append(yaml_file.stem)

        return profiles
