
import sys

def dump_context(filename, search_string):
    with open(filename, 'rb') as f:
        data = f.read()

    search_bytes = search_string.encode('utf-8')
    offset = data.find(search_bytes)

    if offset == -1:
        print(f"String '{search_string}' not found.")
        return

    print(f"Found '{search_string}' at offset {offset} (0x{offset:X})")
    
    start = offset
    end = min(len(data), offset + len(search_bytes) + 64)
    
    context = data[start:end]
    
    print("Hex dump:")
    print("Offset   | Hex                                             | ASCII")
    print("-" * 75)
    
    for i in range(0, len(context), 16):
        chunk = context[i:i+16]
        hex_str = ' '.join(f"{b:02X}" for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{offset+i:08X} | {hex_str:<47} | {ascii_str}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 dump_context.py <filename> <search_string>")
    else:
        dump_context(sys.argv[1], sys.argv[2])
