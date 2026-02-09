from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchResult:
    input_path: Path
    output_path: Path
    backup_path: Path
    offset: int
    old_bytes: bytes
    new_bytes: bytes


def encode_value(dtype: str, value: int) -> bytes:
    if dtype == "u16":
        return value.to_bytes(2, "little", signed=False)
    if dtype == "s16":
        return value.to_bytes(2, "little", signed=True)
    if dtype == "u32":
        return value.to_bytes(4, "little", signed=False)
    if dtype == "s32":
        return value.to_bytes(4, "little", signed=True)
    raise ValueError(f"Nieobsługiwany dtype: {dtype}")


def patch_file(input_file: str, output_file: str, offset: int, dtype: str, value: int) -> PatchResult:
    in_path = Path(input_file).expanduser().resolve()
    out_path = Path(output_file).expanduser().resolve()
    if not in_path.exists() or not in_path.is_file():
        raise FileNotFoundError(f"Brak pliku wejściowego: {in_path}")

    blob = in_path.read_bytes()
    new_bytes = encode_value(dtype, value)
    width = len(new_bytes)

    if offset < 0 or offset + width > len(blob):
        raise ValueError("Offset poza zakresem pliku")

    backup_path = in_path.with_name(in_path.name + ".bak")
    if not backup_path.exists():
        backup_path.write_bytes(blob)

    before = blob[offset : offset + width]
    out_blob = bytearray(blob)
    out_blob[offset : offset + width] = new_bytes

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(bytes(out_blob))

    return PatchResult(
        input_path=in_path,
        output_path=out_path,
        backup_path=backup_path,
        offset=offset,
        old_bytes=before,
        new_bytes=new_bytes,
    )
