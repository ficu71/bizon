from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SaveBlob:
    path: Path
    data: bytes


def load_three_saves(paths: list[str]) -> list[SaveBlob]:
    if len(paths) != 3:
        raise ValueError("Wymagane są dokładnie 3 pliki save.")
    blobs: list[SaveBlob] = []
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Brak pliku: {path}")
        blobs.append(SaveBlob(path=path, data=path.read_bytes()))
    return blobs
