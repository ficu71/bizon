
import sys

def search_gold(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Search for "gold" case insensitive
    target = b"gold"
    
    # Simple search
    for i in range(len(data) - 4):
        chunk = data[i:i+4]
        if chunk.lower() == target:
            print(f"Found 'gold' at offset {i} (0x{i:X})")
            # Show context
            ctx_start = max(0, i - 16)
            ctx_end = min(len(data), i + 32)
            print(f"Context: {data[ctx_start:ctx_end]}")
            
    # Also search for UTF-16 LE "g\x00o\x00l\x00d\x00"
    target_utf16 = b"g\x00o\x00l\x00d\x00"
    for i in range(len(data) - 8):
        chunk = data[i:i+8]
        if chunk.lower() == target_utf16:
             print(f"Found UTF-16 'gold' at offset {i} (0x{i:X})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 search_gold.py <filename>")
    else:
        search_gold(sys.argv[1])
