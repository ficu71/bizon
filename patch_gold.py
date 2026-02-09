import argparse
import sys
from naheulbeuk_patch import NaheulbeukSave

def main():
    parser = argparse.ArgumentParser(description="Patch gold in Naheulbeuk save files with safety checks.")
    parser.add_argument("save_file", help="Path to the .sav file")
    parser.add_argument("new_gold", type=int, help="New gold amount to set")
    parser.add_argument("--mode", choices=["player", "all"], default="player", 
                        help="DANGER: 'all' patches everything, 'player' (default) is safer.")
    parser.add_argument("--current", type=int, help="Current gold amount (required for 'player' mode)")
    parser.add_argument("--out", help="Output file path (default: <input>.patched)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just show what would be done")

    args = parser.parse_args()

    if args.mode == "player" and args.current is None:
        print("Error: --current is required in 'player' mode to ensure safety.")
        sys.exit(1)

    try:
        save = NaheulbeukSave(args.save_file)
        save.load()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    candidates = save.find_fields(b'm_gold')
    
    if not candidates:
        print("Error: Could not find any 'm_gold' fields in the save.")
        sys.exit(1)

    to_patch = []
    if args.mode == "player":
        # Find matches for current gold
        matches = [c for c in candidates if c['current_value'] == args.current]
        if len(matches) == 0:
            print(f"Error: No 'm_gold' fields found with current value {args.current}.")
            print("Found values: " + ", ".join(str(c['current_value']) for c in candidates))
            sys.exit(1)
        if len(matches) > 1:
            print(f"Error: Multiple 'm_gold' fields found with value {args.current}. Cannot be sure which is the player.")
            print("Try use --mode all if you are sure, or check values in game.")
            sys.exit(1)
        to_patch = matches
    else:
        to_patch = candidates

    print(f"Plan: Patching {len(to_patch)} occurrences of 'm_gold' -> {args.new_gold}")
    for c in to_patch:
        print(f"  Offset 0x{c['marker_offset']:X}: {c['current_value']} -> {args.new_gold}")
        if not args.dry_run:
            save.patch_candidate(c, args.new_gold)

    if not args.dry_run:
        out_path = args.out if args.out else args.save_file + ".patched"
        save.save(out_path)
        print(f"Successfully saved to: {out_path}")
    else:
        print("Dry-run complete. No changes saved.")

if __name__ == "__main__":
    main()
