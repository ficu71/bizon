#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from uese.core.patch_engine import PatchEngine
from uese.core.universal_scanner import UniversalScanner


def _parse_offset(value: str) -> int:
    return int(value, 16) if value.lower().startswith("0x") else int(value)


def _print_candidates(candidates, top: int) -> None:
    print(f"Found {len(candidates)} candidates")
    for i, c in enumerate(candidates[:top], 1):
        print(f"{i:02d}. offset={c.offset:#x} width={c.width} dtype={c.dtype}")
        print(f"    score={c.score} diffs(ab={c.diff_ab}, bc={c.diff_bc}) values={c.values}")
        print(f"    ctx: {c.context_hex}")


def _write_json(candidates, path: Path, top: int = 500) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "rank": i + 1,
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
        for i, c in enumerate(candidates[:top])
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_md(candidates, path: Path, top: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# UESE Report\n\n",
        f"Candidates: **{len(candidates)}**\n\n",
        "| # | score | offset | width | dtype | values | diff_ab | diff_bc |\n",
        "|---:|---:|---|---:|---|---|---:|---:|\n",
    ]
    for i, c in enumerate(candidates[:top], 1):
        lines.append(
            f"| {i} | {c.score} | `{hex(c.offset)}` | {c.width} | `{c.dtype}` | `{c.values}` | {c.diff_ab} | {c.diff_bc} |\n"
        )
        lines.append(f"\n> ctx: `{c.context_hex}`\n\n")
    path.write_text("".join(lines), encoding="utf-8")


def cmd_scan(args) -> int:
    saves = [Path(s) for s in args.saves]
    for s in saves:
        if not s.exists():
            print(f"Error: {s} not found")
            return 1

    scanner = UniversalScanner()
    candidates = scanner.scan_saves(
        saves[0],
        saves[1],
        saves[2],
        values=tuple(args.values),
        width=args.width,
        dtype=args.dtype,
        exclude=args.exclude,
    )

    if not candidates:
        print("No candidates found")
        return 1

    _print_candidates(candidates, args.top)
    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "\n".join(
                f"{c.offset:#x},{c.score},{c.width},{c.dtype},{c.values[0]},{c.values[1]},{c.values[2]},{c.diff_ab},{c.diff_bc}"
                for c in candidates
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"CSV saved: {out}")
    if args.json:
        _write_json(candidates, Path(args.json))
        print(f"JSON saved: {args.json}")
    if args.md:
        _write_md(candidates, Path(args.md))
        print(f"MD saved: {args.md}")
    return 0


def cmd_delta(args) -> int:
    saves = [Path(s) for s in args.saves]
    for s in saves:
        if not s.exists():
            print(f"Error: {s} not found")
            return 1

    scanner = UniversalScanner()
    candidates = scanner.scan_deltas(
        saves[0],
        saves[1],
        saves[2],
        deltas=tuple(args.deltas),
        width=args.width,
        dtype=args.dtype,
        exclude=args.exclude,
    )
    if not candidates:
        print("No delta candidates found")
        return 1

    _print_candidates(candidates, args.top)
    if args.json:
        _write_json(candidates, Path(args.json))
        print(f"JSON saved: {args.json}")
    if args.md:
        _write_md(candidates, Path(args.md))
        print(f"MD saved: {args.md}")
    return 0


def cmd_patch(args) -> int:
    save_path = Path(args.save)
    if not save_path.exists():
        print(f"Error: {save_path} not found")
        return 1

    engine = PatchEngine()
    offset = _parse_offset(args.offset)
    out_path = Path(args.out) if args.out else None

    try:
        engine.patch_value(
            filepath=save_path,
            offset=offset,
            width=args.width,
            value=args.value,
            backup=not args.no_backup,
            output_path=out_path,
        )
        verify_file = out_path or save_path
        if engine.verify_patch(verify_file, offset, args.value, args.width):
            print("✅ Patch verified successfully")
            return 0
        print("⚠️ Warning: patch verification failed")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UESE - Universal Epic Save Editor")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan exact values across 3 saves")
    scan.add_argument("-s", "--saves", nargs=3, required=True)
    scan.add_argument("-v", "--values", nargs=3, type=int, required=True)
    scan.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    scan.add_argument("--dtype", choices=["auto", "u16", "u32", "s16", "s32"], default="auto")
    scan.add_argument("--exclude", nargs="*", choices=["png", "entropy", "none"], default=["png", "entropy"])
    scan.add_argument("-t", "--top", type=int, default=10)
    scan.add_argument("--csv")
    scan.add_argument("--json")
    scan.add_argument("--md")

    delta = sub.add_parser("delta", help="Scan by delta pattern")
    delta.add_argument("-s", "--saves", nargs=3, required=True)
    delta.add_argument("-d", "--deltas", nargs=2, type=int, required=True)
    delta.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    delta.add_argument("--dtype", choices=["auto", "u16", "u32", "s16", "s32"], default="auto")
    delta.add_argument("--exclude", nargs="*", choices=["png", "entropy", "none"], default=["png", "entropy"])
    delta.add_argument("-t", "--top", type=int, default=10)
    delta.add_argument("--json")
    delta.add_argument("--md")

    patch = sub.add_parser("patch", help="Patch value at offset")
    patch.add_argument("-s", "--save", required=True)
    patch.add_argument("-o", "--offset", required=True)
    patch.add_argument("-v", "--value", type=int, required=True)
    patch.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    patch.add_argument("--out")
    patch.add_argument("--no-backup", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "delta":
        return cmd_delta(args)
    if args.command == "patch":
        return cmd_patch(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
