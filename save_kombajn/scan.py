from __future__ import annotations

from .score import Candidate, compute_score
from .util import hexdump_context, is_offset_in_regions

DTYPE_WIDTH = {
    "u16": 2,
    "s16": 2,
    "u32": 4,
    "s32": 4,
}


def _resolve_dtypes(width_mode: str, dtype_mode: str) -> list[tuple[str, int]]:
    if dtype_mode == "auto":
        candidates = [(dt, w) for dt, w in DTYPE_WIDTH.items()]
    else:
        candidates = [(dtype_mode, DTYPE_WIDTH[dtype_mode])]

    if width_mode == "auto":
        return candidates
    width = int(width_mode)
    return [(dt, w) for dt, w in candidates if w == width]


def _read_num(blob: bytes, offset: int, dtype: str) -> int | None:
    width = DTYPE_WIDTH[dtype]
    end = offset + width
    if end > len(blob):
        return None
    signed = dtype.startswith("s")
    return int.from_bytes(blob[offset:end], "little", signed=signed)


def scan_exact(
    blobs: list[bytes],
    values: tuple[int, int, int],
    width_mode: str,
    dtype_mode: str,
    excluded_by_file: list[list],
) -> list[Candidate]:
    a, b, c = blobs
    max_len = min(len(a), len(b), len(c))
    candidates: list[Candidate] = []

    for dtype, width in _resolve_dtypes(width_mode, dtype_mode):
        for off in range(0, max_len - width + 1):
            ex = (
                is_offset_in_regions(off, excluded_by_file[0])
                or is_offset_in_regions(off, excluded_by_file[1])
                or is_offset_in_regions(off, excluded_by_file[2])
            )
            if ex:
                continue

            va = _read_num(a, off, dtype)
            vb = _read_num(b, off, dtype)
            vc = _read_num(c, off, dtype)
            if va is None or vb is None or vc is None:
                continue
            if (va, vb, vc) != values:
                continue

            score, diff_ab, diff_bc = compute_score(a, b, c, off, width, ex)
            candidates.append(
                Candidate(
                    offset=off,
                    width=width,
                    dtype=dtype,
                    values=(va, vb, vc),
                    score=score,
                    diff_ab=diff_ab,
                    diff_bc=diff_bc,
                    context_hex=hexdump_context(a, off, before=16, after=48),
                )
            )

    candidates.sort(key=lambda x: (-x.score, x.offset, x.dtype))
    return candidates


def scan_delta(
    blobs: list[bytes],
    deltas: tuple[int, int],
    width_mode: str,
    dtype_mode: str,
    excluded_by_file: list[list],
) -> list[Candidate]:
    a, b, c = blobs
    max_len = min(len(a), len(b), len(c))
    candidates: list[Candidate] = []

    for dtype, width in _resolve_dtypes(width_mode, dtype_mode):
        for off in range(0, max_len - width + 1):
            ex = (
                is_offset_in_regions(off, excluded_by_file[0])
                or is_offset_in_regions(off, excluded_by_file[1])
                or is_offset_in_regions(off, excluded_by_file[2])
            )
            if ex:
                continue

            va = _read_num(a, off, dtype)
            vb = _read_num(b, off, dtype)
            vc = _read_num(c, off, dtype)
            if va is None or vb is None or vc is None:
                continue
            if (vb - va) != deltas[0] or (vc - vb) != deltas[1]:
                continue

            score, diff_ab, diff_bc = compute_score(a, b, c, off, width, ex)
            candidates.append(
                Candidate(
                    offset=off,
                    width=width,
                    dtype=dtype,
                    values=(va, vb, vc),
                    score=score,
                    diff_ab=diff_ab,
                    diff_bc=diff_bc,
                    context_hex=hexdump_context(a, off, before=16, after=48),
                )
            )

    candidates.sort(key=lambda x: (-x.score, x.offset, x.dtype))
    return candidates
