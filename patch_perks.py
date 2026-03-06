#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from uese.core.gzip_field_patcher import (
    list_field_hits_in_gzip_container,
    patch_fields_in_gzip_container,
)

FIELD_MAP = {
    "active": [b"m_activeSkillPoints"],
    "passive": [b"m_passiveSkillPoints"],
    "stats": [b"m_statsPoints"],
    "all": [b"m_activeSkillPoints", b"m_passiveSkillPoints", b"m_statsPoints"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch Naheulbeuk perk/stat points in GZIP payload")
    parser.add_argument("save_file", help="Path to input save file")
    parser.add_argument("amount", nargs="?", type=int, help="New perk/stat value (uint32)")
    parser.add_argument(
        "--stat",
        choices=["all", "active", "passive", "stats"],
        default="all",
        help="Which stat group to patch",
    )
    parser.add_argument("--output", help="Output file path (default: <save>.perks.patched)")
    parser.add_argument(
        "--max-hits",
        type=int,
        help="Patch at most N field occurrences total (default: all)",
    )
    parser.add_argument(
        "--slot",
        action="append",
        type=int,
        help="Patch only selected slot(s) from --list output (can be repeated)",
    )
    parser.add_argument(
        "--character-slot",
        action="append",
        type=int,
        help="Patch selected field_slot index (useful to target one character across fields)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available slots for selected --stat and exit",
    )
    args = parser.parse_args()
    print(
        "Deprecated expert helper: use `python3 -m uese naheulbeuk show-stats/patch` for semantic record editing; "
        "`patch_perks.py` remains raw slot-based tooling only."
    )

    save_path = Path(args.save_file)
    output_path = Path(args.output) if args.output else save_path.with_suffix(save_path.suffix + ".perks.patched")
    field_names = FIELD_MAP[args.stat]

    if args.list:
        try:
            gzip_offset, hits = list_field_hits_in_gzip_container(
                container_path=save_path,
                field_names=field_names,
                width=4,
            )
        except Exception as exc:
            print(f"Error: {exc}")
            return 1

        print(f"Found compressed payload at offset 0x{gzip_offset:X}")
        if not hits:
            print("No matching perk/stat slots found.")
            return 0

        for hit in hits:
            ctx = hit.context[:110]
            print(
                f"[slot={hit.slot:03d}] field={hit.field_name} value={hit.value} "
                f"offset=0x{hit.field_offset:X} field_slot={hit.field_slot} ctx={ctx}"
            )
        return 0

    if args.amount is None:
        parser.error("amount is required unless --list is used")

    try:
        patched_file, gzip_offset, hits = patch_fields_in_gzip_container(
            container_path=save_path,
            field_names=field_names,
            value=args.amount,
            width=4,
            output_path=output_path,
            max_hits=args.max_hits,
            slots=args.slot,
            field_slots=args.character_slot,
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
    print(f"Patched {len(hits)} perk/stat field(s).")
    print(f"Created patched save: {patched_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
