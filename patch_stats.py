#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from uese.core.gzip_field_patcher import (
    list_field_hits_in_gzip_container,
    patch_fields_in_gzip_container,
)

FIELD_NAMES = [b"m_statsPoints"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Naheulbeuk stat points in GZIP payload")
    parser.add_argument("save_file", help="Path to input save file")
    parser.add_argument("amount", nargs="?", type=int, help="New stat points value (uint32)")
    parser.add_argument("--output", help="Output file path (default: <save>.stats.patched)")
    parser.add_argument(
        "--max-hits",
        type=int,
        help="Patch at most N field occurrences (default: all)",
    )
    parser.add_argument(
        "--slot",
        action="append",
        type=int,
        help="Patch only selected slot from --list output (can be repeated)",
    )
    parser.add_argument(
        "--character-slot",
        action="append",
        type=int,
        help="Alias for --slot (target selected field_slot/character index)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available stat slots with current values and exit",
    )
    args = parser.parse_args()
    print(
        "Deprecated expert helper: use `python3 -m uese naheulbeuk show-stats/patch` for semantic record editing; "
        "`patch_stats.py` remains raw slot-based tooling only."
    )

    save_path = Path(args.save_file)
    output_path = Path(args.output) if args.output else save_path.with_suffix(save_path.suffix + ".stats.patched")

    if args.list:
        try:
            gzip_offset, hits = list_field_hits_in_gzip_container(
                container_path=save_path,
                field_names=FIELD_NAMES,
                width=4,
            )
        except Exception as exc:
            print(f"Error: {exc}")
            return 1

        print(f"Found compressed payload at offset 0x{gzip_offset:X}")
        if not hits:
            print("No stat slots found.")
            return 0

        for hit in hits:
            ctx = hit.context[:110]
            print(
                f"[slot={hit.slot:03d}] value={hit.value} "
                f"offset=0x{hit.field_offset:X} field_slot={hit.field_slot} ctx={ctx}"
            )
        return 0

    if args.amount is None:
        parser.error("amount is required unless --list is used")

    try:
        selected_slots = (args.slot or []) + (args.character_slot or [])
        patched_file, gzip_offset, hits = patch_fields_in_gzip_container(
            container_path=save_path,
            field_names=FIELD_NAMES,
            value=args.amount,
            width=4,
            output_path=output_path,
            max_hits=args.max_hits,
            slots=selected_slots or None,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Found compressed payload at offset 0x{gzip_offset:X}")
    for hit in hits:
        print(
            f"Patched '{hit.field_name}' at 0x{hit.field_offset:X} "
            f"[slot={hit.slot}, field_slot={hit.field_slot}] ({hit.old_value} -> {hit.new_value})"
        )
    print(f"Patched {len(hits)} stat field(s).")
    print(f"Created patched save: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
