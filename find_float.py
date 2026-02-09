import sys
import struct

def find_float(filename, value):
    val = float(value)
    # Check 4-byte float LE and BE
    target_le = struct.pack('<f', val)
    target_be = struct.pack('>f', val)
    
    with open(filename, 'rb') as f:
        data = f.read()
    
    found = False
    idx = data.find(target_le)
    while idx != -1:
        print(f"File {filename}: Found float LE {val} at {idx:X}")
        idx = data.find(target_le, idx + 1)
        found = True
        
    idx = data.find(target_be)
    while idx != -1:
        print(f"File {filename}: Found float BE {val} at {idx:X}")
        idx = data.find(target_be, idx + 1)
        found = True
    return found

def run():
    files = [
        "save do analizy/Game_fcu_AutoSave_1.sav",
        "save do analizy/Game_fcu_fcusav.sav",
        "save do analizy/Game_fcu_elo.sav",
        "save do analizy/Game_fcu_elo elo.sav"
    ]
    for f in files:
        find_float(f, 500.0)
        find_float(f, 539.0)

if __name__ == "__main__":
    run()
