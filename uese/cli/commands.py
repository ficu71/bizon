#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from uese.core.naheulbeuk_app import (
    NaheulbeukAppError,
    apply_naheulbeuk_semantic_patches,
    get_naheulbeuk_doctor_report,
    get_naheulbeuk_record,
    inspect_naheulbeuk,
    list_naheulbeuk_records,
)
from uese.core.naheulbeuk_semantic import (
    SemanticPatchInput,
    inspect_naheulbeuk_save,
)
from uese.core.patch_engine import PatchEngine
from uese.core.universal_scanner import UniversalScanner

EXIT_OK = 0
EXIT_INPUT_ERROR = 1
EXIT_VERIFY_FAILED = 2
EXIT_BLOCKED = 3


def _parse_offset(value: str) -> int:
    return int(value, 16) if value.lower().startswith("0x") else int(value)


def _exit_code_from_app_error(exc: NaheulbeukAppError) -> int:
    return getattr(exc, "exit_code", EXIT_INPUT_ERROR)


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


def _print_doctor_report(report: dict[str, object]) -> None:
    print(f"Naheulbeuk doctor: {report['status']} ({report['mode']})")
    if report.get("data_root"):
        print(f"data_root={report['data_root']} source={report.get('data_root_source') or 'unknown'}")
    else:
        print("data_root=unresolved")

    for check in report.get("checks", []):
        print(
            f"- {check['name']}: {check['status']} | {check['summary']}"
            + (f" | {check['detail']}" if check.get("detail") else "")
        )

    probe = report.get("probe_save")
    if probe:
        if probe.get("status") == "ok":
            print(
                "probe_save="
                f"{probe['filepath']} | characters={probe['character_count']} | "
                f"economy={probe['economy_count']} | safe={probe['safe_count']} | "
                f"risky={probe['risky_count']} | unresolved={probe['unresolved_count']}"
            )
        elif probe.get("status") == "missing":
            print(f"probe_save={probe['filepath']} | missing")
        else:
            print(f"probe_save={probe['filepath']} | error={probe.get('error')}")

    if report.get("warnings"):
        print("warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")


def _print_naheulbeuk_inspect_summary(model) -> None:
    safe_count = sum(1 for record in model.characters if record.edit_status == "safe")
    risky_count = sum(1 for record in model.characters if record.edit_status == "risky")
    unresolved_count = sum(1 for record in model.characters if record.edit_status == "unresolved")
    class_counts: dict[str, int] = {}
    for record in model.characters:
        class_counts[record.classification] = class_counts.get(record.classification, 0) + 1

    print(f"Naheulbeuk inspect: {model.filepath}")
    print(f"gzip_offset={hex(model.gzip_offset)}")
    print(
        f"characters={model.character_count} economy={model.economy_count} "
        f"safe={safe_count} risky={risky_count} unresolved={unresolved_count}"
    )
    print(
        "classifications="
        + ", ".join(f"{name}={count}" for name, count in sorted(class_counts.items()))
    )
    if model.warnings:
        print("warnings:")
        for warning in model.warnings:
            print(f"  - {warning}")


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


def _print_naheulbeuk_character_summaries(model) -> None:
    print(f"Characters: {model.character_count}")
    for record in model.characters:
        print(
            f"- {record.record_id} | block={record.block_index} | {record.label} | "
            f"{record.identity_status} | class={record.classification} | "
            f"edit={record.edit_status} | role={record.structure_signature} | "
            f"group={record.group_id} x{record.group_size} | "
            f"template={record.template_name or 'unresolved'} ({record.template_status}/{record.template_resolution_source}) | "
            f"scene_hint={record.scene_hint.class_name if record.scene_hint else 'n/a'} | "
            f"fields={len(record.fields)}"
        )
    if model.economy:
        print(f"Economy slots: {model.economy_count}")


def _resolve_record(model, record_id: str):
    for record in [*model.characters, *model.economy]:
        if record.record_id == record_id:
            return record
    return None


def cmd_naheulbeuk_inspect(args) -> int:
    try:
        payload = inspect_naheulbeuk(args.save)
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        return _exit_code_from_app_error(exc)

    if args.json:
        print(json.dumps(payload, indent=2))
        return EXIT_OK

    model = inspect_naheulbeuk_save(Path(args.save))
    _print_naheulbeuk_inspect_summary(model)
    return EXIT_OK


def cmd_naheulbeuk_doctor(args) -> int:
    try:
        report = get_naheulbeuk_doctor_report(args.save)
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        return _exit_code_from_app_error(exc)

    if args.json:
        print(json.dumps(report, indent=2))
        return EXIT_OK

    _print_doctor_report(report)
    return EXIT_OK


def cmd_naheulbeuk_list_characters(args) -> int:
    try:
        payload = list_naheulbeuk_records(
            args.save,
            risk=args.risk,
            classification=args.classification,
        )
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        return _exit_code_from_app_error(exc)

    if args.json:
        print(json.dumps(payload, indent=2))
        return EXIT_OK

    model = inspect_naheulbeuk_save(Path(args.save))
    filtered_ids = {record["record_id"] for record in payload["characters"]}
    model.characters = [record for record in model.characters if record.record_id in filtered_ids]
    model.character_count = len(model.characters)
    _print_naheulbeuk_character_summaries(model)
    return EXIT_OK


def cmd_naheulbeuk_show_stats(args) -> int:
    record_id = args.character_id or args.record_id
    if not record_id:
        print("Error: --character-id or --record-id is required")
        return EXIT_INPUT_ERROR

    try:
        payload = get_naheulbeuk_record(args.save, record_id)
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        return _exit_code_from_app_error(exc)

    if args.json:
        print(json.dumps(payload, indent=2))
        return EXIT_OK

    model = inspect_naheulbeuk_save(Path(args.save))
    record = _resolve_record(model, record_id)
    if record is None:
        print(f"Error: record not found after inspect: {record_id}")
        return EXIT_INPUT_ERROR

    print(f"{record.label} ({record.record_id})")
    print(
        f"kind={record.kind} status={record.identity_status} class={record.classification} "
        f"confidence={record.confidence}"
    )
    print(
        f"template_id={record.template_id} template_name={record.template_name} "
        f"template_status={record.template_status} template_source={record.template_resolution_source} "
        f"template_detail={record.template_source_detail or 'n/a'}"
    )
    print(
        f"edit_status={record.edit_status} structure_signature={record.structure_signature} "
        f"group={record.group_id} size={record.group_size}"
    )
    if record.scene_hint is not None:
        print(
            f"scene_hint={record.scene_hint.class_name} "
            f"object={record.scene_hint.game_object_name or 'n/a'} "
            f"scene={record.scene_hint.scene_path} hits={record.scene_hint.hit_count}"
        )
    for field in record.fields:
        print(
            f"- {field.field_id}: value={field.value} status={field.status} editable={field.editable} "
            f"source={field.source_path}"
        )
    return EXIT_OK


def cmd_naheulbeuk_patch(args) -> int:
    record_id = args.character_id or args.record_id
    if not record_id:
        print("Error: --character-id or --record-id is required")
        return EXIT_INPUT_ERROR

    output_path = Path(args.out) if args.out else None
    try:
        result = apply_naheulbeuk_semantic_patches(
            args.save,
            [
                SemanticPatchInput(
                    record_id=record_id,
                    field_id=args.field,
                    value=args.value,
                    allow_ambiguous=args.allow_ambiguous,
                    allow_identity_ambiguous=args.allow_identity_ambiguous,
                )
            ],
            backup=not args.no_backup,
            output_path=output_path,
        )
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        if exc.payload:
            print(json.dumps(exc.payload, indent=2))
        return _exit_code_from_app_error(exc)

    print(json.dumps(result, indent=2))
    return EXIT_OK


def cmd_naheulbeuk_patch_batch(args) -> int:
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Error: spec not found: {spec_path}")
        return EXIT_INPUT_ERROR

    try:
        raw = json.loads(spec_path.read_text(encoding="utf-8"))
        items = raw["patches"] if isinstance(raw, dict) and "patches" in raw else raw
        patch_inputs = [
            SemanticPatchInput(
                record_id=item.get("record_id") or item.get("character_id"),
                field_id=item["field_id"],
                value=item["value"],
                allow_ambiguous=bool(item.get("allow_ambiguous", False)),
                allow_identity_ambiguous=bool(item.get("allow_identity_ambiguous", False)),
                )
            for item in items
        ]
        if any(not item.record_id for item in patch_inputs):
            raise NaheulbeukInputError("Each patch item must include record_id or character_id")
        result = apply_naheulbeuk_semantic_patches(
            args.save,
            patch_inputs,
            backup=not args.no_backup,
            output_path=Path(args.out) if args.out else None,
        )
    except NaheulbeukAppError as exc:
        print(f"Error: {exc}")
        if exc.payload:
            print(json.dumps(exc.payload, indent=2))
        return _exit_code_from_app_error(exc)
    except Exception as exc:
        print(f"Error: {exc}")
        return EXIT_INPUT_ERROR

    print(json.dumps(result, indent=2))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UESE - Universal Epic Save Editor")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Expert Mode: scan exact values across 3 saves")
    scan.add_argument("-s", "--saves", nargs=3, required=True)
    scan.add_argument("-v", "--values", nargs=3, type=int, required=True)
    scan.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    scan.add_argument("--dtype", choices=["auto", "u16", "u32", "s16", "s32"], default="auto")
    scan.add_argument("--exclude", nargs="*", choices=["png", "entropy", "none"], default=["png", "entropy"])
    scan.add_argument("-t", "--top", type=int, default=10)
    scan.add_argument("--csv")
    scan.add_argument("--json")
    scan.add_argument("--md")

    delta = sub.add_parser("delta", help="Expert Mode: scan by delta pattern")
    delta.add_argument("-s", "--saves", nargs=3, required=True)
    delta.add_argument("-d", "--deltas", nargs=2, type=int, required=True)
    delta.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    delta.add_argument("--dtype", choices=["auto", "u16", "u32", "s16", "s32"], default="auto")
    delta.add_argument("--exclude", nargs="*", choices=["png", "entropy", "none"], default=["png", "entropy"])
    delta.add_argument("-t", "--top", type=int, default=10)
    delta.add_argument("--json")
    delta.add_argument("--md")

    patch = sub.add_parser("patch", help="Expert Mode: patch value at offset")
    patch.add_argument("-s", "--save", required=True)
    patch.add_argument("-o", "--offset", required=True)
    patch.add_argument("-v", "--value", type=int, required=True)
    patch.add_argument("-w", "--width", type=int, choices=[2, 4], default=4)
    patch.add_argument("--out")
    patch.add_argument("--no-backup", action="store_true")

    naheulbeuk = sub.add_parser("naheulbeuk", help="Typed semantic tools for The Dungeon of Naheulbeuk")
    naheulbeuk_sub = naheulbeuk.add_subparsers(dest="naheulbeuk_command", required=True)

    naheulbeuk_doctor = naheulbeuk_sub.add_parser("doctor", help="Check whether semantic editing is ready or degraded")
    naheulbeuk_doctor.add_argument("--save", help="Optional save file to probe with inspect")
    naheulbeuk_doctor.add_argument("--json", action="store_true")

    naheulbeuk_inspect = naheulbeuk_sub.add_parser("inspect", help="Inspect a Naheulbeuk save semantically")
    naheulbeuk_inspect.add_argument("save")
    naheulbeuk_inspect.add_argument("--json", action="store_true")

    naheulbeuk_list = naheulbeuk_sub.add_parser("list-characters", help="List typed character records")
    naheulbeuk_list.add_argument("save")
    naheulbeuk_list.add_argument("--json", action="store_true")
    naheulbeuk_list.add_argument("--risk", choices=["all", "safe", "risky", "unresolved"], default="all")
    naheulbeuk_list.add_argument(
        "--classification",
        choices=["all", "party", "companion", "npc", "unknown", "environment"],
        default="all",
    )

    naheulbeuk_show = naheulbeuk_sub.add_parser("show-stats", help="Show semantic fields for one character/record")
    naheulbeuk_show.add_argument("save")
    naheulbeuk_show.add_argument("--character-id")
    naheulbeuk_show.add_argument("--record-id")
    naheulbeuk_show.add_argument("--json", action="store_true")

    naheulbeuk_patch = naheulbeuk_sub.add_parser("patch", help="Patch one semantic field")
    naheulbeuk_patch.add_argument("save")
    naheulbeuk_patch.add_argument("--character-id")
    naheulbeuk_patch.add_argument("--record-id")
    naheulbeuk_patch.add_argument("--field", required=True)
    naheulbeuk_patch.add_argument("--value", required=True, type=float)
    naheulbeuk_patch.add_argument("--allow-ambiguous", action="store_true")
    naheulbeuk_patch.add_argument("--allow-identity-ambiguous", action="store_true")
    naheulbeuk_patch.add_argument("--out")
    naheulbeuk_patch.add_argument("--no-backup", action="store_true")

    naheulbeuk_patch_batch = naheulbeuk_sub.add_parser("patch-batch", help="Patch a JSON batch spec")
    naheulbeuk_patch_batch.add_argument("save")
    naheulbeuk_patch_batch.add_argument("--spec", required=True)
    naheulbeuk_patch_batch.add_argument("--out")
    naheulbeuk_patch_batch.add_argument("--no-backup", action="store_true")
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
    if args.command == "naheulbeuk":
        if args.naheulbeuk_command == "doctor":
            return cmd_naheulbeuk_doctor(args)
        if args.naheulbeuk_command == "inspect":
            return cmd_naheulbeuk_inspect(args)
        if args.naheulbeuk_command == "list-characters":
            return cmd_naheulbeuk_list_characters(args)
        if args.naheulbeuk_command == "show-stats":
            return cmd_naheulbeuk_show_stats(args)
        if args.naheulbeuk_command == "patch":
            return cmd_naheulbeuk_patch(args)
        if args.naheulbeuk_command == "patch-batch":
            return cmd_naheulbeuk_patch_batch(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
