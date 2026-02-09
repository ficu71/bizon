#!/usr/bin/env python3
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass
class ScanCandidate:
    offset: int
    width: int
    dtype: str
    values: Tuple[int, int, int]
    score: int = 0
    diff_ab: int = 0
    diff_bc: int = 0
    context_hex: str = ""


class UniversalScanner:
    def __init__(self):
        self.excluded_regions: List[Tuple[int, int]] = []

    def scan_saves(
        self,
        save_a: Path,
        save_b: Path,
        save_c: Path,
        values: Tuple[int, int, int],
        width: int = 4,
        dtype: str = "auto",
        exclude: List[str] | None = None,
    ) -> List[ScanCandidate]:
        blobs = [p.read_bytes() for p in [save_a, save_b, save_c]]
        self.excluded_regions = self._find_excluded_regions(blobs, exclude or ["png", "entropy"])
        candidates = self._scan_candidates(blobs, values, width, dtype)
        for c in candidates:
            c.score, c.diff_ab, c.diff_bc = self._score(blobs, c)
            c.context_hex = self._hexdump_context(blobs[0], c.offset)
        return sorted(candidates, key=lambda c: (-c.score, c.offset, c.dtype))

    def scan_deltas(
        self,
        save_a: Path,
        save_b: Path,
        save_c: Path,
        deltas: Tuple[int, int],
        width: int = 4,
        dtype: str = "auto",
        exclude: List[str] | None = None,
    ) -> List[ScanCandidate]:
        blobs = [p.read_bytes() for p in [save_a, save_b, save_c]]
        self.excluded_regions = self._find_excluded_regions(blobs, exclude or ["png", "entropy"])

        n = min(len(b) for b in blobs)
        dtype_map = {"u16": 2, "s16": 2, "u32": 4, "s32": 4}
        dtypes = ["u16", "s16", "u32", "s32"] if dtype == "auto" else [dtype]
        candidates: List[ScanCandidate] = []

        for dt in dtypes:
            if dt not in dtype_map:
                continue
            w = dtype_map[dt]
            if width in (2, 4) and w != width:
                continue

            for i in range(0, n - w + 1):
                if self._in_excluded(i):
                    continue
                va = self._read_num(blobs[0], i, dt)
                vb = self._read_num(blobs[1], i, dt)
                vc = self._read_num(blobs[2], i, dt)
                if (vb - va) == deltas[0] and (vc - vb) == deltas[1]:
                    c = ScanCandidate(i, w, dt, (va, vb, vc))
                    c.score, c.diff_ab, c.diff_bc = self._score(blobs, c)
                    c.context_hex = self._hexdump_context(blobs[0], c.offset)
                    candidates.append(c)

        return sorted(candidates, key=lambda c: (-c.score, c.offset, c.dtype))

    def _scan_candidates(
        self,
        blobs: List[bytes],
        values: Tuple[int, int, int],
        width: int,
        dtype: str,
    ) -> List[ScanCandidate]:
        n = min(len(b) for b in blobs)
        candidates: List[ScanCandidate] = []

        dtype_map = {
            "u16": 2,
            "s16": 2,
            "u32": 4,
            "s32": 4,
        }
        if dtype == "auto":
            dtypes = ["u16", "s16", "u32", "s32"]
        else:
            if dtype not in dtype_map:
                raise ValueError(f"Unsupported dtype: {dtype}")
            dtypes = [dtype]

        for dt in dtypes:
            w = dtype_map[dt]
            if width in (2, 4) and w != width:
                continue
            for i in range(0, n - w + 1):
                if self._in_excluded(i):
                    continue
                va = self._read_num(blobs[0], i, dt)
                vb = self._read_num(blobs[1], i, dt)
                vc = self._read_num(blobs[2], i, dt)
                if (va, vb, vc) == values:
                    candidates.append(ScanCandidate(i, w, dt, values))
        return candidates

    def _read_num(self, blob: bytes, offset: int, dtype: str) -> int:
        width = 2 if dtype.endswith("16") else 4
        signed = dtype.startswith("s")
        return int.from_bytes(blob[offset : offset + width], "little", signed=signed)

    def _score(self, blobs: List[bytes], c: ScanCandidate) -> Tuple[int, int, int]:
        span = 64
        start = max(0, c.offset - span)
        end = min(len(blobs[0]), len(blobs[1]), len(blobs[2]), c.offset + c.width + span)
        diff_ab = sum(a != b for a, b in zip(blobs[0][start:end], blobs[1][start:end]))
        diff_bc = sum(a != b for a, b in zip(blobs[1][start:end], blobs[2][start:end]))
        noise = diff_ab + diff_bc

        score = 0
        local_a = blobs[0][c.offset : c.offset + c.width]
        local_b = blobs[1][c.offset : c.offset + c.width]
        local_c = blobs[2][c.offset : c.offset + c.width]
        if local_a != local_b and local_b != local_c:
            score += 300
        if c.offset % c.width == 0:
            score += 40
        score += max(0, 500 - noise)
        if noise > 420:
            score -= 250
        return score, diff_ab, diff_bc

    def _find_excluded_regions(self, blobs: List[bytes], exclude_kinds: List[str]) -> List[Tuple[int, int]]:
        regions: List[Tuple[int, int]] = []
        if "none" in exclude_kinds:
            return regions
        for blob in blobs:
            if "png" in exclude_kinds:
                regions.extend(self._find_png_regions(blob))
            if "entropy" in exclude_kinds:
                regions.extend(self._find_entropy_regions(blob))
        return self._merge_regions(regions)

    def _find_png_regions(self, blob: bytes) -> List[Tuple[int, int]]:
        regions: List[Tuple[int, int]] = []
        start = 0
        while True:
            idx = blob.find(PNG_MAGIC, start)
            if idx == -1:
                break
            cursor = idx + len(PNG_MAGIC)
            end = len(blob)
            while cursor + 8 <= len(blob):
                chunk_len = struct.unpack(">I", blob[cursor : cursor + 4])[0]
                chunk_type = blob[cursor + 4 : cursor + 8]
                cursor += 8 + chunk_len + 4
                if cursor > len(blob):
                    cursor = len(blob)
                    break
                if chunk_type == b"IEND":
                    break
            end = cursor
            regions.append((idx, end))
            start = max(end, idx + 1)
        return regions

    def _find_entropy_regions(
        self, blob: bytes, window: int = 4096, step: int = 2048, threshold: float = 7.7
    ) -> List[Tuple[int, int]]:
        regions: List[Tuple[int, int]] = []
        if len(blob) < window:
            return regions
        for i in range(0, len(blob) - window + 1, step):
            ent = self._entropy(blob[i : i + window])
            if ent >= threshold:
                regions.append((i, i + window))
        return self._merge_regions(regions)

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        freq = [0] * 256
        for b in data:
            freq[b] += 1
        n = len(data)
        h = 0.0
        for c in freq:
            if c == 0:
                continue
            p = c / n
            h -= p * math.log2(p)
        return h

    def _merge_regions(self, regions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        if not regions:
            return []
        regions = sorted(regions)
        merged: List[List[int]] = [[regions[0][0], regions[0][1]]]
        for s, e in regions[1:]:
            if s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [(s, e) for s, e in merged]

    def _in_excluded(self, offset: int) -> bool:
        return any(s <= offset < e for s, e in self.excluded_regions)

    def _hexdump_context(self, blob: bytes, offset: int, before: int = 16, after: int = 48) -> str:
        start = max(0, offset - before)
        end = min(len(blob), offset + after)
        return f"{start:#x}..{end:#x} | " + " ".join(f"{b:02x}" for b in blob[start:end])
