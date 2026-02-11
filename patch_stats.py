import argparse
import sys
from naheulbeuk_patch import NaheulbeukSave


STAT_FIELDS = {
    "agility": b"m_agility",
    "strength": b"m_strength",
    "constitution": b"m_constitution",
    "courage": b"m_courage",
    "charisma": b"m_charisma",
    "cleverness": b"m_cleverness",
}

DISCOVERY_ORDER = [
    "agility",
    "charisma",
    "cleverness",
    "constitution",
    "courage",
    "strength",
]

DISPLAY_ORDER = [
    "agility",
    "strength",
    "constitution",
    "cleverness",
    "courage",
    "charisma",
]

BASE_OVERRIDE_FIELD = b"m_baseValueOverride"
VALUE_FIELD = b"m_value"
STATS_MANAGER_FIELD = b"m_statsManager"
CURRENT_LEVEL_FIELD = b"m_currentLevel"


def find_all_offsets(data, marker):
    offsets = []
    start = 0
    while True:
        idx = data.find(marker, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def read_i32(data, offset):
    return int.from_bytes(data[offset:offset + 4], "little", signed=True)


def write_i32(data, offset, value):
    data[offset:offset + 4] = int(value).to_bytes(4, "little", signed=True)


def is_placeholder_slot(slot):
    for stat_name in DISPLAY_ORDER:
        stat = slot["stats"][stat_name]
        if stat["base_value"] != -1 or stat["value"] != -1:
            return False
    return True


def discover_stat_slots(data, include_placeholders=False):
    stats_manager_offsets = find_all_offsets(data, STATS_MANAGER_FIELD)
    slots = []

    for idx, sm_offset in enumerate(stats_manager_offsets):
        block_end = stats_manager_offsets[idx + 1] if idx + 1 < len(stats_manager_offsets) else len(data)
        block = data[sm_offset:block_end]
        slot_stats = {}

        complete = True
        for stat_name in DISCOVERY_ORDER:
            marker = STAT_FIELDS[stat_name]
            rel_stat_offset = block.find(marker)
            if rel_stat_offset == -1:
                complete = False
                break

            stat_offset = sm_offset + rel_stat_offset
            base_marker_offset = data.find(BASE_OVERRIDE_FIELD, stat_offset, min(stat_offset + 220, len(data)))
            if base_marker_offset == -1:
                complete = False
                break

            value_marker_offset = data.find(VALUE_FIELD, base_marker_offset + 1, min(stat_offset + 260, len(data)))
            if value_marker_offset == -1:
                complete = False
                break

            base_value_offset = base_marker_offset + len(BASE_OVERRIDE_FIELD)
            value_offset = value_marker_offset + len(VALUE_FIELD)

            if value_offset + 4 > len(data) or base_value_offset + 4 > len(data):
                complete = False
                break

            slot_stats[stat_name] = {
                "stat_marker_offset": stat_offset,
                "base_marker_offset": base_marker_offset,
                "value_marker_offset": value_marker_offset,
                "base_offset": base_value_offset,
                "value_offset": value_offset,
                "base_value": read_i32(data, base_value_offset),
                "value": read_i32(data, value_offset),
            }

        if not complete:
            continue

        level = None
        rel_level_offset = block.find(CURRENT_LEVEL_FIELD)
        if rel_level_offset != -1:
            level_offset = sm_offset + rel_level_offset + len(CURRENT_LEVEL_FIELD)
            if level_offset + 4 <= len(data):
                level = read_i32(data, level_offset)

        slot = {
            "stats_manager_offset": sm_offset,
            "current_level": level,
            "stats": slot_stats,
        }

        if not include_placeholders and is_placeholder_slot(slot):
            continue

        slots.append(slot)

    return slots


def parse_target_stats(args):
    requested = {}

    direct_fields = ["agility", "strength", "constitution", "courage", "charisma"]
    for field_name in direct_fields:
        val = getattr(args, field_name)
        if val is not None:
            requested[field_name] = val

    if args.intelligence is not None and args.cleverness is not None and args.intelligence != args.cleverness:
        raise ValueError("Conflict: --intelligence and --cleverness have different values.")

    if args.intelligence is not None:
        requested["cleverness"] = args.intelligence
    elif args.cleverness is not None:
        requested["cleverness"] = args.cleverness

    if not requested:
        raise ValueError(
            "At least one stat flag is required: --agility/--strength/--constitution/"
            "--courage/--charisma/--intelligence/--cleverness."
        )

    for field_name, val in requested.items():
        if val < 0 or val > 999:
            raise ValueError(f"Invalid value for '{field_name}': {val}. Allowed range is 0..999.")

    return requested


def parse_current_stats(args):
    current = {}

    direct_fields = ["agility", "strength", "constitution", "courage", "charisma"]
    for field_name in direct_fields:
        val = getattr(args, f"current_{field_name}")
        if val is not None:
            current[field_name] = val

    if (
        args.current_intelligence is not None
        and args.current_cleverness is not None
        and args.current_intelligence != args.current_cleverness
    ):
        raise ValueError("Conflict: --current-intelligence and --current-cleverness have different values.")

    if args.current_intelligence is not None:
        current["cleverness"] = args.current_intelligence
    elif args.current_cleverness is not None:
        current["cleverness"] = args.current_cleverness

    return current


def display_label(stat_name):
    return "intelligence" if stat_name == "cleverness" else stat_name


def required_current_flag_hint(stat_name):
    if stat_name == "cleverness":
        return "--current-intelligence or --current-cleverness"
    return f"--current-{stat_name}"


def print_slots(slots, include_placeholders=False):
    scope = "all" if include_placeholders else "non-placeholder"
    print(f"Discovered {len(slots)} complete stat slots ({scope}).")
    for idx, slot in enumerate(slots, start=1):
        level_txt = slot["current_level"] if slot["current_level"] is not None else "?"
        print(f"Slot {idx}: statsManager=0x{slot['stats_manager_offset']:X}, level={level_txt}")
        for stat_name in DISPLAY_ORDER:
            stat = slot["stats"][stat_name]
            label = display_label(stat_name)
            print(
                f"  {label:<12} base={stat['base_value']:>4} value={stat['value']:>4} "
                f"(base@0x{stat['base_offset']:X}, value@0x{stat['value_offset']:X})"
            )


def main():
    parser = argparse.ArgumentParser(description="Patch base character stats in Naheulbeuk save files.")
    parser.add_argument("save_file", help="Path to the .sav file")
    parser.add_argument("--mode", choices=["slot", "all"], default="slot",
                        help="slot (default) patches one slot, all patches every discovered slot.")
    parser.add_argument("--slot", type=int, help="Slot number (1..N), required in slot mode.")
    parser.add_argument("--list-slots", action="store_true", help="List discovered slots and exit.")
    parser.add_argument("--include-placeholders", action="store_true",
                        help="Include placeholder slots (all stats == -1). Advanced/debug option.")

    parser.add_argument("--agility", type=int, help="Target Agility (0..999)")
    parser.add_argument("--strength", type=int, help="Target Strength (0..999)")
    parser.add_argument("--constitution", type=int, help="Target Constitution (0..999)")
    parser.add_argument("--courage", type=int, help="Target Courage (0..999)")
    parser.add_argument("--charisma", type=int, help="Target Charisma (0..999)")
    parser.add_argument("--intelligence", type=int, help="Target Intelligence (alias of cleverness, 0..999)")
    parser.add_argument("--cleverness", type=int, help="Target Cleverness (0..999)")
    parser.add_argument("--current-agility", type=int, help="Current Agility value for safety check in slot mode.")
    parser.add_argument("--current-strength", type=int, help="Current Strength value for safety check in slot mode.")
    parser.add_argument("--current-constitution", type=int, help="Current Constitution value for safety check in slot mode.")
    parser.add_argument("--current-courage", type=int, help="Current Courage value for safety check in slot mode.")
    parser.add_argument("--current-charisma", type=int, help="Current Charisma value for safety check in slot mode.")
    parser.add_argument("--current-intelligence", type=int, help="Current Intelligence value for safety check in slot mode.")
    parser.add_argument("--current-cleverness", type=int, help="Current Cleverness value for safety check in slot mode.")

    parser.add_argument("--out", help="Output file path (default: <input>.stats.patched)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just show what would be done")
    args = parser.parse_args()

    try:
        save = NaheulbeukSave(args.save_file)
        save.load()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    slots = discover_stat_slots(save.decompressed_data, include_placeholders=args.include_placeholders)
    if not slots:
        print("Error: Could not discover any matching stat slots in this save.")
        if not args.include_placeholders:
            print("Tip: try --include-placeholders to inspect raw template-like slots.")
        sys.exit(1)

    if args.list_slots:
        print_slots(slots, include_placeholders=args.include_placeholders)
        return

    try:
        requested_stats = parse_target_stats(args)
        current_stats = parse_current_stats(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.mode == "slot":
        if args.slot is None:
            print("Error: --slot is required in 'slot' mode.")
            sys.exit(1)
        if args.slot < 1 or args.slot > len(slots):
            print(f"Error: --slot out of range. Valid range is 1..{len(slots)}.")
            sys.exit(1)
        selected_slots = [(args.slot, slots[args.slot - 1])]

        missing_current = [stat_name for stat_name in requested_stats if stat_name not in current_stats]
        if missing_current:
            hints = [required_current_flag_hint(stat_name) for stat_name in missing_current]
            print(
                "Error: Missing required current stat flags in 'slot' mode: "
                + ", ".join(hints)
            )
            print("Tip: run --list-slots and pass current values from the selected slot.")
            sys.exit(1)

        _, selected_slot = selected_slots[0]
        mismatches = []
        for stat_name in requested_stats:
            expected_current = current_stats[stat_name]
            actual_current = selected_slot["stats"][stat_name]["value"]
            if expected_current != actual_current:
                mismatches.append((display_label(stat_name), expected_current, actual_current))

        if mismatches:
            print("Error: Current stat mismatch for selected slot:")
            for label, expected_current, actual_current in mismatches:
                print(f"  {label}: expected {expected_current}, found {actual_current}")
            print("Tip: run --list-slots and use exact 'value' numbers as --current-* arguments.")
            sys.exit(1)
    else:
        selected_slots = [(idx + 1, slot) for idx, slot in enumerate(slots)]

    print(
        f"Plan: Patching {len(selected_slots)} slot(s), {len(requested_stats)} stat(s) each "
        "(m_value only; base unchanged)."
    )
    for slot_number, slot in selected_slots:
        level_txt = slot["current_level"] if slot["current_level"] is not None else "?"
        print(f"Slot {slot_number} @ 0x{slot['stats_manager_offset']:X} (level={level_txt})")
        for stat_name in DISPLAY_ORDER:
            if stat_name not in requested_stats:
                continue

            target_value = requested_stats[stat_name]
            stat = slot["stats"][stat_name]
            label = display_label(stat_name)
            print(
                f"  {label}: value {stat['value']} -> {target_value} "
                f"(base stays {stat['base_value']})"
            )

            if not args.dry_run:
                write_i32(save.decompressed_data, stat["value_offset"], target_value)

    if args.dry_run:
        print("Dry-run complete. No changes saved.")
        return

    out_path = args.out if args.out else args.save_file + ".stats.patched"
    save.save(out_path)
    print(f"Successfully saved to: {out_path}")


if __name__ == "__main__":
    main()
