
import sys

def find_compression(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    patterns = {
        'gzip': b'\x1f\x8b',
        'zlib_def': b'\x78\x9c',
        'zlib_max': b'\x78\xda',
        'zlib_low': b'\x78\x01',
        'zip': b'\x50\x4b\x03\x04',
        'unity_fs': b'UnityFS',
        'unity_raw': b'UnityRaw'
    }

    for name, magic in patterns.items():
        # Start search after potential PNG (approx 0x13000) or check all
        offset = data.find(magic, 0x13000)
        while offset != -1:
            print(f"Found {name} header at offset {offset} (0x{offset:X})")
            # Only report first few
            break 
        if offset == -1:
            pass # Be silent if not found in this region

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 find_compression.py <filename>")
    else:
        find_compression(sys.argv[1])
