import argparse
import sys
from naheulbeuk_patch import NaheulbeukSave

def main():
    parser = argparse.ArgumentParser(description="Patch perk points in Naheulbeuk save files with safety checks.")
    parser.add_argument("save_file", help="Path to the .sav file")
    parser.add_argument("new_amount", type=int, help="New points amount to set for all matched fields")
    parser.add_argument("--mode", choices=["player", "all"], default="player", 
                        help="DANGER: 'all' patches everything, 'player' (default) is safer.")
    parser.add_argument("--current-active", type=int, help="Current active skill points")
    parser.add_argument("--current-passive", type=int, help="Current passive skill points")
    parser.add_argument("--current-stats", type=int, help="Current stats points")
    parser.add_argument("--out", help="Output file path (default: <input>.perks.patched)")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes, just show what would be done")

    args = parser.parse_args()

    if args.mode == "player" and (args.current_active is None or args.current_passive is None or args.current_stats is None):
        print("Error: --current-active, --current-passive, and --current-stats are required in 'player' mode.")
        sys.exit(1)

    try:
        save = NaheulbeukSave(args.save_file)
        save.load()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    fields = [b'm_activeSkillPoints', b'm_passiveSkillPoints', b'm_statsPoints']
    field_results = {f: save.find_fields(f) for f in fields}

    to_patch = []
    if args.mode == "player":
        # Group candidates by "entity" (assuming they appear close together or in order)
        # For simplicity in Naheulbeuk, they usually belong to the same character record.
        # However, the safer way is to find a unique triplet that matches user input.
        
        # We'll just look for any index where these three values appear in sequence or close.
        # Actually, let's just find the character that matches ALL three current values.
        # This is tricky because we don't have a formal "entity" parser.
        # Simplified: find the first occurrence where current active matches, then check next fields.
        
        # Let's try a different approach: find all occurrences of m_activeSkillPoints that match current_active.
        active_matches = [c for c in field_results[b'm_activeSkillPoints'] if c['current_value'] == args.current_active]
        
        matched_entities = []
        for am in active_matches:
            # Look for passive and stats points around this offset (Unity serialized fields are close)
            # Find the closest passive points after this active points marker
            pm = min([c for c in field_results[b'm_passiveSkillPoints'] if c['marker_offset'] > am['marker_offset']], 
                     key=lambda x: x['marker_offset'] - am['marker_offset'], default=None)
            sm = min([c for c in field_results[b'm_statsPoints'] if c['marker_offset'] > am['marker_offset']], 
                     key=lambda x: x['marker_offset'] - am['marker_offset'], default=None)
            
            if pm and sm and pm['current_value'] == args.current_passive and sm['current_value'] == args.current_stats:
                # Basic distance check to ensure they are likely part of the same block
                if (pm['marker_offset'] - am['marker_offset']) < 1000 and (sm['marker_offset'] - am['marker_offset']) < 1000:
                    matched_entities.append((am, pm, sm))

        if len(matched_entities) == 0:
            print(f"Error: No character found with Active={args.current_active}, Passive={args.current_passive}, Stats={args.current_stats}.")
            sys.exit(1)
        if len(matched_entities) > 1:
            print(f"Error: Found {len(matched_entities)} characters with matching point values. Be more specific or use --mode all.")
            sys.exit(1)
            
        to_patch = list(matched_entities[0])
    else:
        for f in fields:
            to_patch.extend(field_results[f])

    print(f"Plan: Patching {len(to_patch)} fields -> {args.new_amount}")
    for c in to_patch:
        # We need to find which field this is for logging
        # (This is a bit hacky since we lost the field name in the candidate list if we just use core)
        # But we can look it up or just print offset
        print(f"  Offset 0x{c['marker_offset']:X}: {c['current_value']} -> {args.new_amount}")
        if not args.dry_run:
            save.patch_candidate(c, args.new_amount)

    if not args.dry_run:
        out_path = args.out if args.out else args.save_file + ".perks.patched"
        save.save(out_path)
        print(f"Successfully saved to: {out_path}")
    else:
        print("Dry-run complete. No changes saved.")

if __name__ == "__main__":
    main()
