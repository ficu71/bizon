from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    offset: int
    width: int
    dtype: str
    values: tuple[int, int, int]
    score: int
    diff_ab: int
    diff_bc: int
    context_hex: str


def _window_diff_count(a: bytes, b: bytes, start: int, end: int) -> int:
    return sum(x != y for x, y in zip(a[start:end], b[start:end]))


def compute_score(
    a: bytes,
    b: bytes,
    c: bytes,
    offset: int,
    width: int,
    is_excluded: bool,
) -> tuple[int, int, int]:
    """
    Deterministyczny scoring:
    - +300 jeśli same bajty pola zmieniają się między A->B i B->C
    - +max(0, 500 - noise) gdzie noise = diff_ab + diff_bc w oknie +/-64
    - -250 jeśli noise > 420 (chaotyczna okolica)
    - -500 jeśli offset leży w regionie wykluczonym
    """
    window = 64
    start = max(0, offset - window)
    end = min(len(a), len(b), len(c), offset + width + window)
    diff_ab = _window_diff_count(a, b, start, end)
    diff_bc = _window_diff_count(b, c, start, end)
    noise = diff_ab + diff_bc

    score = 0
    local_a = a[offset : offset + width]
    local_b = b[offset : offset + width]
    local_c = c[offset : offset + width]

    if local_a != local_b and local_b != local_c:
        score += 300

    score += max(0, 500 - noise)

    if noise > 420:
        score -= 250
    if is_excluded:
        score -= 500

    return score, diff_ab, diff_bc
