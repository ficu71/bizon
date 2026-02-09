from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    # Umożliwia uruchamianie: python3 save_kombajn/cli.py ...
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from save_kombajn.exclude import build_excluded_regions
    from save_kombajn.io import load_three_saves
    from save_kombajn.patch import patch_file
    from save_kombajn.report import export_json, export_markdown, print_candidates
    from save_kombajn.scan import scan_delta, scan_exact
else:
    from .exclude import build_excluded_regions
    from .io import load_three_saves
    from .patch import patch_file
    from .report import export_json, export_markdown, print_candidates
    from .scan import scan_delta, scan_exact


def _parse_offset(value: str) -> int:
    return int(value, 16) if value.lower().startswith("0x") else int(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="save-kombajn",
        description="Diff-based skaner i patcher binarnych save'ów Unity/C#",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan", help="Skan exact po 3 save'ach")
    scan_cmd.add_argument("files", nargs=3, help="Dokładnie 3 pliki save")
    scan_cmd.add_argument("--values", nargs=3, type=int, required=True, metavar=("V1", "V2", "V3"))
    scan_cmd.add_argument("--width", default="auto", choices=["auto", "2", "4"])
    scan_cmd.add_argument("--dtype", default="auto", choices=["auto", "u16", "u32", "s16", "s32"])
    scan_cmd.add_argument(
        "--exclude",
        nargs="*",
        default=["png", "entropy"],
        choices=["png", "entropy", "none"],
        help="Domyślnie: png entropy",
    )
    scan_cmd.add_argument("--top", type=int, default=30)
    scan_cmd.add_argument("--json", default="")
    scan_cmd.add_argument("--md", default="")

    delta_cmd = sub.add_parser("delta", help="Skan po stałych deltach")
    delta_cmd.add_argument("files", nargs=3, help="Dokładnie 3 pliki save")
    delta_cmd.add_argument("--deltas", nargs=2, type=int, required=True, metavar=("D1", "D2"))
    delta_cmd.add_argument("--width", default="auto", choices=["auto", "2", "4"])
    delta_cmd.add_argument("--dtype", default="auto", choices=["auto", "u16", "u32", "s16", "s32"])
    delta_cmd.add_argument(
        "--exclude",
        nargs="*",
        default=["png", "entropy"],
        choices=["png", "entropy", "none"],
        help="Domyślnie: png entropy",
    )
    delta_cmd.add_argument("--top", type=int, default=30)
    delta_cmd.add_argument("--json", default="")
    delta_cmd.add_argument("--md", default="")

    patch_cmd = sub.add_parser("patch", help="Patchuje wartość na podanym offsecie")
    patch_cmd.add_argument("input_file")
    patch_cmd.add_argument("output_file")
    patch_cmd.add_argument("--offset", required=True, type=_parse_offset)
    patch_cmd.add_argument("--dtype", required=True, choices=["u16", "u32", "s16", "s32"])
    patch_cmd.add_argument("--value", required=True, type=int)

    return parser


def _run_scan(args: argparse.Namespace) -> int:
    saves = load_three_saves(args.files)
    blobs = [s.data for s in saves]
    excluded = [build_excluded_regions(blob, args.exclude) for blob in blobs]
    candidates = scan_exact(
        blobs=blobs,
        values=(args.values[0], args.values[1], args.values[2]),
        width_mode=args.width,
        dtype_mode=args.dtype,
        excluded_by_file=excluded,
    )
    print_candidates(candidates, top=args.top)
    if args.json:
        export_json(candidates, args.json)
        print(f"[+] Zapisano JSON: {args.json}")
    if args.md:
        export_markdown(candidates, args.md)
        print(f"[+] Zapisano Markdown: {args.md}")
    return 0


def _run_delta(args: argparse.Namespace) -> int:
    saves = load_three_saves(args.files)
    blobs = [s.data for s in saves]
    excluded = [build_excluded_regions(blob, args.exclude) for blob in blobs]
    candidates = scan_delta(
        blobs=blobs,
        deltas=(args.deltas[0], args.deltas[1]),
        width_mode=args.width,
        dtype_mode=args.dtype,
        excluded_by_file=excluded,
    )
    print_candidates(candidates, top=args.top)
    if args.json:
        export_json(candidates, args.json)
        print(f"[+] Zapisano JSON: {args.json}")
    if args.md:
        export_markdown(candidates, args.md)
        print(f"[+] Zapisano Markdown: {args.md}")
    return 0


def _run_patch(args: argparse.Namespace) -> int:
    result = patch_file(
        input_file=args.input_file,
        output_file=args.output_file,
        offset=args.offset,
        dtype=args.dtype,
        value=args.value,
    )
    print(f"[+] Input:  {result.input_path}")
    print(f"[+] Output: {result.output_path}")
    print(f"[+] Backup: {result.backup_path}")
    print(
        f"[+] Patch @ {result.offset:#x}: "
        f"{result.old_bytes.hex(' ')} -> {result.new_bytes.hex(' ')}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scan":
        return _run_scan(args)
    if args.command == "delta":
        return _run_delta(args)
    if args.command == "patch":
        return _run_patch(args)
    parser.error("Nieznana komenda")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
