#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
import zlib

GZIP_MAGIC = b"\x1f\x8b\x08"


@dataclass
class ExtractedGzipPayload:
    gzip_offset: int
    decompressed: bytearray
    trailing_bytes: bytes


@dataclass
class PatchHit:
    field_name: str
    field_offset: int
    value_offset: int
    old_value: int
    new_value: int
    slot: int
    field_slot: int


@dataclass
class FieldHit:
    field_name: str
    field_offset: int
    value_offset: int
    value: int
    slot: int
    field_slot: int
    context: str


def _extract_gzip_payload(container: bytes) -> tuple[int, bytearray, bytes]:
    offset = container.find(GZIP_MAGIC)
    if offset == -1:
        raise ValueError("Could not find GZIP payload in save file")

    stream = container[offset:]
    decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
    decompressed = decompressor.decompress(stream)
    decompressed += decompressor.flush()

    consumed = len(stream) - len(decompressor.unused_data)
    if consumed <= 0:
        raise ValueError("Failed to locate consumed GZIP stream length")

    trailing_bytes = stream[consumed:]
    return offset, bytearray(decompressed), trailing_bytes


def extract_gzip_payload(container: bytes) -> ExtractedGzipPayload:
    gzip_offset, decompressed, trailing_bytes = _extract_gzip_payload(container)
    return ExtractedGzipPayload(
        gzip_offset=gzip_offset,
        decompressed=decompressed,
        trailing_bytes=trailing_bytes,
    )


def rebuild_gzip_container(
    original_container: bytes,
    extracted: ExtractedGzipPayload,
    *,
    compress_level: int = 9,
) -> bytes:
    compressor = zlib.compressobj(compress_level, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    recompressed = compressor.compress(extracted.decompressed) + compressor.flush()
    return (
        original_container[: extracted.gzip_offset]
        + recompressed
        + extracted.trailing_bytes
    )


def _render_context(blob: bytes, offset: int, *, before: int = 48, after: int = 96) -> str:
    start = max(0, offset - before)
    end = min(len(blob), offset + after)
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in blob[start:end])
    return " ".join(text.split())


def _find_named_fields(
    decompressed: bytearray,
    field_names: list[bytes],
    width: int,
    *,
    with_context: bool = False,
) -> list[FieldHit]:
    hits: list[FieldHit] = []
    per_field_counter: dict[str, int] = {}

    for field_name in field_names:
        start = 0
        while True:
            field_offset = decompressed.find(field_name, start)
            if field_offset == -1:
                break

            value_offset = field_offset + len(field_name)
            if value_offset + width > len(decompressed):
                start = field_offset + 1
                continue

            field_key = field_name.decode("ascii", errors="replace")
            per_field_counter[field_key] = per_field_counter.get(field_key, 0) + 1
            current_value = int.from_bytes(
                decompressed[value_offset : value_offset + width],
                "little",
                signed=False,
            )
            hits.append(
                FieldHit(
                    field_name=field_key,
                    field_offset=field_offset,
                    value_offset=value_offset,
                    value=current_value,
                    slot=0,
                    field_slot=per_field_counter[field_key],
                    context=_render_context(decompressed, field_offset) if with_context else "",
                )
            )

            start = field_offset + 1

    hits.sort(key=lambda h: h.field_offset)
    for i, hit in enumerate(hits, 1):
        hit.slot = i
    return hits


def list_field_hits_in_gzip_container(
    container_path: Path,
    field_names: Iterable[bytes],
    *,
    width: int = 4,
) -> tuple[int, list[FieldHit]]:
    if width not in (2, 4):
        raise ValueError(f"Width must be 2 or 4, got {width}")

    field_list = list(field_names)
    if not field_list:
        raise ValueError("No field names provided")

    payload = container_path.read_bytes()
    gzip_offset, decompressed, _ = _extract_gzip_payload(payload)
    hits = _find_named_fields(decompressed, field_list, width, with_context=True)
    return gzip_offset, hits


def patch_fields_in_gzip_container(
    container_path: Path,
    field_names: Iterable[bytes],
    value: int,
    *,
    width: int = 4,
    output_path: Optional[Path] = None,
    max_hits: Optional[int] = None,
    slots: Optional[Iterable[int]] = None,
    field_slots: Optional[Iterable[int]] = None,
    compress_level: int = 9,
) -> tuple[Path, int, list[PatchHit]]:
    if width not in (2, 4):
        raise ValueError(f"Width must be 2 or 4, got {width}")
    if value < 0:
        raise ValueError("Value must be >= 0")

    max_value = 0xFFFF if width == 2 else 0xFFFFFFFF
    if value > max_value:
        raise ValueError(f"Value {value} out of range for width={width}")

    field_list = list(field_names)
    if not field_list:
        raise ValueError("No field names provided")

    payload = container_path.read_bytes()
    gzip_offset, decompressed, trailing = _extract_gzip_payload(payload)
    all_hits = _find_named_fields(decompressed, field_list, width, with_context=False)
    if not all_hits:
        raise ValueError("No matching fields found in decompressed payload")

    slot_set = set(slots or [])
    if any(s <= 0 for s in slot_set):
        raise ValueError("Slots must be positive integers (1..N)")

    field_slot_set = set(field_slots or [])
    if any(s <= 0 for s in field_slot_set):
        raise ValueError("Field slots must be positive integers (1..N)")

    selected_hits = [
        h
        for h in all_hits
        if (not slot_set or h.slot in slot_set) and (not field_slot_set or h.field_slot in field_slot_set)
    ]

    if not selected_hits:
        raise ValueError("No matching fields for selected slot(s) / field_slot(s)")

    if max_hits is not None:
        selected_hits = selected_hits[:max_hits]

    new_bytes = value.to_bytes(width, "little", signed=False)
    patched_hits: list[PatchHit] = []
    for hit in selected_hits:
        old_value = int.from_bytes(
            decompressed[hit.value_offset : hit.value_offset + width],
            "little",
            signed=False,
        )
        decompressed[hit.value_offset : hit.value_offset + width] = new_bytes
        patched_hits.append(
            PatchHit(
                field_name=hit.field_name,
                field_offset=hit.field_offset,
                value_offset=hit.value_offset,
                old_value=old_value,
                new_value=value,
                slot=hit.slot,
                field_slot=hit.field_slot,
            )
        )

    compressor = zlib.compressobj(compress_level, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    recompressed = compressor.compress(decompressed) + compressor.flush()
    patched_data = payload[:gzip_offset] + recompressed + trailing

    target = output_path or container_path.with_suffix(container_path.suffix + ".patched")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(patched_data)

    return target, gzip_offset, patched_hits
