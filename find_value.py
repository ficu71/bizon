
import sys
import struct

def find_value(filename, value):
    try:
        val = int(value)
    except ValueError:
        print(f"Invalid value: {value}")
        return

    print(f"Searching for value: {val}")
    
    with open(filename, 'rb') as f:
        data = f.read()

    patterns = [
        ('u8', struct.pack('<B', val) if val < 256 else None),
        ('u16_le', struct.pack('<H', val) if val < 65536 else None),
        ('u32_le', struct.pack('<I', val)),
        ('u16_be', struct.pack('>H', val) if val < 65536 else None),
        ('u32_be', struct.pack('>I', val))
    ]

    found = False
    for name, pattern in patterns:
        if pattern is None:
            continue
            
        offset = data.find(pattern)
        while offset != -1:
            found = True
            print(f"Found {name} value {val} at offset {offset} (0x{offset:X})")
            
            # Show context
            start = max(0, offset - 16)
            end = min(len(data), offset + 16)
            msg = data[start:end].hex(' ')
            print(f"  Context: {msg}")
            
            offset = data.find(pattern, offset + 1)
            
    if not found:
        print(f"Value {val} not found in {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 find_value.py <filename> <value>")
    else:
        find_value(sys.argv[1], sys.argv[2])
