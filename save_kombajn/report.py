from __future__ import annotations

from pathlib import Path
import json

from .score import Candidate


def print_candidates(candidates: list[Candidate], top: int = 30) -> None:
    print(f"Znaleziono kandydatów: {len(candidates)}")
    print(f"Top {top}:")
    for i, c in enumerate(candidates[:top], start=1):
        print(
            f"{i:02d}. score={c.score:4d} off={c.offset:#x} width={c.width} "
            f"dtype={c.dtype} values={c.values} diff_ab={c.diff_ab} diff_bc={c.diff_bc}"
        )
        print(f"    ctx: {c.context_hex}")


def export_json(candidates: list[Candidate], out_path: str, top: int = 500) -> None:
    path = Path(out_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for idx, c in enumerate(candidates[:top], start=1):
        payload.append(
            {
                "rank": idx,
                "offset": c.offset,
                "offset_hex": hex(c.offset),
                "width": c.width,
                "dtype": c.dtype,
                "values": list(c.values),
                "score": c.score,
                "diff_ab": c.diff_ab,
                "diff_bc": c.diff_bc,
                "context_hex": c.context_hex,
            }
        )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_markdown(candidates: list[Candidate], out_path: str, top: int = 80) -> None:
    path = Path(out_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Save Kombajn Report\n\n")
    lines.append(f"Liczba kandydatów: **{len(candidates)}**\n\n")
    lines.append("| # | score | offset | width | dtype | values | diff_ab | diff_bc |\n")
    lines.append("|---:|---:|---|---:|---|---|---:|---:|\n")
    for idx, c in enumerate(candidates[:top], start=1):
        lines.append(
            f"| {idx} | {c.score} | `{hex(c.offset)}` | {c.width} | `{c.dtype}` | "
            f"`{c.values}` | {c.diff_ab} | {c.diff_bc} |\n"
        )
        lines.append(f"\n> ctx: `{c.context_hex}`\n\n")
    path.write_text("".join(lines), encoding="utf-8")
