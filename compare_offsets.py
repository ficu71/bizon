import sys
import struct

def compare_offsets(file1, file2, offsets):
    with open(file1, 'rb') as f:
        data1 = f.read()
    with open(file2, 'rb') as f:
        data2 = f.read()
    
    print(f"Comparing {file1} vs {file2}")
    print("Offset   | File1 (u16_le) | File2 (u16_le) | Same?")
    print("-" * 60)
    
    for offset in offsets:
        if offset + 2 <= len(data1) and offset + 2 <= len(data2):
            val1 = struct.unpack('<H', data1[offset:offset+2])[0]
            val2 = struct.unpack('<H', data2[offset:offset+2])[0]
            same = "✓" if val1 == val2 else "✗"
            print(f"0x{offset:06X} | {val1:5d}          | {val2:5d}          | {same}")
        else:
            print(f"0x{offset:06X} | OUT OF BOUNDS")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 compare_offsets.py <file1> <file2> <offset1> [offset2] ...")
    else:
        offsets = [int(x, 16) if x.startswith('0x') else int(x) for x in sys.argv[3:]]
        compare_offsets(sys.argv[1], sys.argv[2], offsets)
