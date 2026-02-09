import sys
import zlib
import os

def patch_naheulbeuk_perks(container_path, amount):
    with open(container_path, 'rb') as f:
        data = f.read()

    # Find GZIP header
    magic = b'\x1f\x8b\x08'
    offset = data.find(magic)
    if offset == -1:
        print("Error: Could not find GZIP payload.")
        return

    try:
        decompressed = bytearray(zlib.decompress(data[offset:], zlib.MAX_WBITS | 16))
    except Exception as e:
        print(f"Error decompressing: {e}")
        return

    fields = [b'm_activeSkillPoints', b'm_passiveSkillPoints', b'm_statsPoints']
    patch_count = 0
    
    for field in fields:
        start = 0
        while True:
            idx = decompressed.find(field, start)
            if idx == -1:
                break
            val_offset = idx + len(field)
            old_val = int.from_bytes(decompressed[val_offset:val_offset+4], 'little')
            decompressed[val_offset:val_offset+4] = int(amount).to_bytes(4, 'little')
            print(f"Patched '{field.decode()}' at 0x{idx:X} ({old_val} -> {amount})")
            patch_count += 1
            start = idx + 1

    if patch_count == 0:
        print("Error: No perk fields found.")
        return

    # Recompress
    compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
    new_compressed = compressor.compress(decompressed) + compressor.flush()
    new_data = data[:offset] + new_compressed
    
    output_path = container_path + ".perks.patched"
    with open(output_path, 'wb') as f:
        f.write(new_data)
    
    print(f"Successfully created patched save: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 patch_perks.py <save_file> <amount>")
    else:
        patch_naheulbeuk_perks(sys.argv[1], sys.argv[2])
