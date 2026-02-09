from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    reason: str


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def merge_regions(regions: list[Region]) -> list[Region]:
    if not regions:
        return []
    ordered = sorted(regions, key=lambda r: (r.start, r.end))
    merged: list[Region] = [ordered[0]]
    for item in ordered[1:]:
        last = merged[-1]
        if item.start <= last.end:
            merged[-1] = Region(
                start=last.start,
                end=max(last.end, item.end),
                reason=f"{last.reason}+{item.reason}",
            )
        else:
            merged.append(item)
    return merged


def is_offset_in_regions(offset: int, regions: list[Region]) -> bool:
    for region in regions:
        if region.start <= offset < region.end:
            return True
    return False


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    entropy = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def hexdump_context(blob: bytes, offset: int, before: int = 16, after: int = 48) -> str:
    start = clamp(offset - before, 0, len(blob))
    end = clamp(offset + after, 0, len(blob))
    chunk = blob[start:end]
    hex_part = " ".join(f"{b:02x}" for b in chunk)
    return f"{start:#x}..{end:#x} | {hex_part}"
