
import sys
import zlib

def decompress_at(filename, offset):
    try:
        offset = int(offset)
    except ValueError:
        offset = int(offset, 16) # Handle hex

    with open(filename, 'rb') as f:
        f.seek(offset)
        data = f.read()

    modes = [
        ("zlib", lambda d: zlib.decompress(d)),
        ("gzip", lambda d: zlib.decompress(d, zlib.MAX_WBITS | 16)),
        ("raw", lambda d: zlib.decompress(d, -zlib.MAX_WBITS)),
    ]

    for name, func in modes:
        try:
            decompressed = func(data)
            print(f"Successfully decompressed {len(decompressed)} bytes from offset {offset} using {name}")
            output_filename = filename + f".decompressed_{offset}_{name}.bin"
            with open(output_filename, 'wb') as out:
                out.write(decompressed)
            print(f"Saved to {output_filename}")
            return # Stop after first success? OR continue to see if others work (unlikely multiple work on same byte)
        except Exception as e:
            print(f"Decompression failed at offset {offset} using {name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 decompress_save.py <filename> <offset>")
    else:
        decompress_at(sys.argv[1], sys.argv[2])
