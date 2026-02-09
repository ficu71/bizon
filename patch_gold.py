import sys
import zlib
import os

def patch_naheulbeuk_gold(container_path, new_gold):
    with open(container_path, 'rb') as f:
        data = f.read()

    # Find GZIP header
    magic = b'\x1f\x8b\x08'
    offset = data.find(magic)
    if offset == -1:
        print("Error: Could not find GZIP payload in save file.")
        return

    print(f"Found compressed payload at offset 0x{offset:X}")
    
    # Decompress
    try:
        decompressed = bytearray(zlib.decompress(data[offset:], zlib.MAX_WBITS | 16))
        print(f"Decompressed {len(decompressed)} bytes.")
    except Exception as e:
        print(f"Error decompressing: {e}")
        return

    # Find all m_gold in decompressed data
    field_name = b'm_gold'
    start = 0
    count = 0
    while True:
        idx = decompressed.find(field_name, start)
        if idx == -1:
            break
        val_offset = idx + len(field_name)
        old_val = int.from_bytes(decompressed[val_offset:val_offset+4], 'little')
        decompressed[val_offset:val_offset+4] = int(new_gold).to_bytes(4, 'little')
        print(f"Patched 'm_gold' at 0x{idx:X} (Old value: {old_val})")
        count += 1
        start = idx + 1

    if count == 0:
        print("Error: Could not find 'm_gold' in decompressed data.")
        return
    
    print(f"Patched {count} instances of 'm_gold' in decompressed data.")
    
    # Recompress
    # Note: We use compresslevel=9 and default settings. 
    # Unity/GZIP might use slightly different settings, but zlib usually works.
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    new_compressed = compressor.compress(decompressed) + compressor.flush()
    
    # Construct new file: Header + New Compressed Payload
    new_data = data[:offset] + new_compressed
    
    output_path = container_path + ".patched"
    with open(output_path, 'wb') as f:
        f.write(new_data)
    
    print(f"Successfully created patched save: {output_path}")
    print("Replace your original save with this file (make a backup first!).")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 patch_gold.py <save_file> <gold_amount>")
    else:
        patch_naheulbeuk_gold(sys.argv[1], sys.argv[2])
