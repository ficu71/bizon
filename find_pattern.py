import sys
import struct

def find_pattern(filename, gold, weight, max_weight=350):
    with open(filename, 'rb') as f:
        data = f.read()

    print(f"Searching for pattern: Gold={gold}, Weight={weight}, MaxWeight={max_weight} in {filename}")
    
    # Try different widths and distances
    # Potential patterns:
    # [Gold (u16/u32)] ... [Weight (u16/u32)] ... [MaxWeight (u16/u32)]
    
    possible_offsets = []
    for i in range(len(data) - 12):
        # Let's try u16_le for all
        g = struct.unpack('<H', data[i:i+2])[0]
        if g == gold:
            # Look in a window of 256 bytes for weight
            for j in range(max(0, i - 128), min(len(data) - 2, i + 128)):
                w = struct.unpack('<H', data[j:j+2])[0]
                if w == weight:
                     # Also look for max_weight
                     for k in range(max(0, j - 128), min(len(data) - 2, j + 128)):
                         mw = struct.unpack('<H', data[k:k+2])[0]
                         if mw == max_weight:
                             print(f"Potential match at offset {i:X} (Gold={gold} at {i:X}, Weight={weight} at {j:X}, Max={max_weight} at {k:X})")
                             possible_offsets.append(i)
    return possible_offsets

def run():
    # Save with 539 gold, 19 weight
    # I don't know which file is which for sure, let's check all
    files = [
        "save do analizy/Game_fcu_AutoSave_1.sav",
        "save do analizy/Game_fcu_fcusav.sav",
        "save do analizy/Game_fcu_elo.sav",
        "save do analizy/Game_fcu_elo elo.sav"
    ]
    
    print("--- Checking for 539 / 19 / 350 ---")
    for f in files:
        find_pattern(f, 539, 19)

    print("\n--- Checking for 500 / 8 / 350 ---")
    for f in files:
        find_pattern(f, 500, 8)

if __name__ == "__main__":
    run()
