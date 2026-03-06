import sys
import struct

def get_offsets(filename, value):
    offsets = set()
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Check u16_le and u32_le
    for i in range(len(data) - 1):
        if struct.unpack('<H', data[i:i+2])[0] == value:
            offsets.add(i)
    return offsets

def find_intersection():
    save_500 = "save do analizy/Game_fcu_fcusav.sav"
    save_539_1 = "save do analizy/Game_fcu_AutoSave_1.sav"
    save_539_2 = "save do analizy/Game_fcu_RestartFight.sav" # Guessing
    
    # Try all .sav files to see which one has 539
    files = [
        "save do analizy/Game_fcu_fcusav.sav",
        "save do analizy/Game_fcu_AutoSave_1.sav",
        "save do analizy/Game_fcu_RestartFight.sav",
        "save do analizy/Game_fcu_elo elo.sav",
        "save do analizy/Game_fcu_elo.sav"
    ]
    
    val_data = {}
    for f in files:
        offsets_500 = get_offsets(f, 500)
        offsets_539 = get_offsets(f, 539)
        val_data[f] = {500: offsets_500, 539: offsets_539}
        print(f"File {f}: {len(offsets_500)} at 500, {len(offsets_539)} at 539")

    # Now look for an offset that switches from 500 to 539
    # between any two files
    for f1 in files:
        for f2 in files:
            if f1 == f2: continue
            common_offsets = val_data[f1][500].intersection(val_data[f2][539])
            if common_offsets:
                print(f"\nPotential Gold Field! Offset switches 500 -> 539 between {f1} and {f2}:")
                for off in common_offsets:
                    print(f"  Offset: 0x{off:X} ({off})")

if __name__ == "__main__":
    find_intersection()
