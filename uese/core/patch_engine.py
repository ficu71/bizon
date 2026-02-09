#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional


class PatchEngine:
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or Path.home() / '.uese_backups'
        self.backup_dir.mkdir(exist_ok=True)

    def patch_value(
        self,
        filepath: Path,
        offset: int,
        width: int,
        value: int,
        backup: bool = True,
        output_path: Optional[Path] = None,
    ) -> bool:
        if not filepath.exists():
            raise FileNotFoundError(f'Save file not found: {filepath}')

        if width not in [2, 4]:
            raise ValueError(f'Width must be 2 or 4, got {width}')

        if width == 2 and not (0 <= value <= 0xFFFF):
            raise ValueError(f'Value {value} out of range for uint16')
        if width == 4 and not (0 <= value <= 0xFFFFFFFF):
            raise ValueError(f'Value {value} out of range for uint32')

        blob = bytearray(filepath.read_bytes())

        if offset < 0 or offset + width > len(blob):
            raise ValueError(f'Offset {offset:#x} out of bounds')

        if backup:
            self._create_backup(filepath)

        old_value = blob[offset:offset+width]
        new_bytes = value.to_bytes(width, 'little', signed=False)
        blob[offset:offset+width] = new_bytes

        target = output_path or filepath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)

        print(f'✅ Patched {filepath.name}')
        if output_path is not None:
            print(f'   Output: {target}')
        print(f'   Offset: {offset:#x}')
        print(f'   Old bytes: {old_value.hex(" ")}')
        print(f'   New bytes: {new_bytes.hex(" ")}')
        print(f'   New: {value}')
        return True

    def _create_backup(self, filepath: Path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'{filepath.stem}_{timestamp}{filepath.suffix}.bak'
        backup_path = self.backup_dir / backup_name
        backup_path.write_bytes(filepath.read_bytes())
        print(f'📦 Backup: {backup_path}')
        return backup_path

    def verify_patch(self, filepath: Path, offset: int, expected_value: int, width: int) -> bool:
        blob = filepath.read_bytes()
        actual = int.from_bytes(blob[offset:offset+width], 'little')
        return actual == expected_value
