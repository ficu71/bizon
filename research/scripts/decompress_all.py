import sys
import zlib

def decompress_all(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    magic = b'\x1f\x8b\x08'
    offset = data.find(magic)
    count = 0
    while offset != -1:
        print(f"Trying decompression at offset {offset:X}")
        try:
            # Try gzip
            decompressed = zlib.decompress(data[offset:], zlib.MAX_WBITS | 16)
            print(f"  SUCCESS! Decompressed {len(decompressed)} bytes")
            with open(f"{filename}.{offset:X}.bin", 'wb') as out:
                out.write(decompressed)
            count += 1
        except Exception:
            pass
        offset = data.find(magic, offset + 1)
    print(f"Found and decompressed {count} blobs.")

if __name__ == "__main__":
    decompress_all(sys.argv[1])
