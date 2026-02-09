import zlib
import os

class NaheulbeukSave:
    def __init__(self, path):
        self.path = path
        self.header = b''
        self.compressed_payload = b''
        self.trailing_data = b''
        self.decompressed_data = bytearray()
        self.gzip_offset = -1

    def load(self):
        with open(self.path, 'rb') as f:
            full_data = f.read()

        # Find GZIP header magic
        magic = b'\x1f\x8b\x08'
        self.gzip_offset = full_data.find(magic)
        if self.gzip_offset == -1:
            raise ValueError("Could not find GZIP payload in save file.")

        self.header = full_data[:self.gzip_offset]
        
        # Use decompressobj to handle trailing data correctly
        d = zlib.decompressobj(zlib.MAX_WBITS | 16)
        try:
            self.decompressed_data = bytearray(d.decompress(full_data[self.gzip_offset:]))
            self.trailing_data = d.unused_data
        except Exception as e:
            raise ValueError(f"Decompression failed: {e}")

        return self.decompressed_data

    def find_fields(self, field_name):
        """
        Finds all occurrences of a field and returns a list of dictionaries:
        {'offset': int, 'value': int}
        """
        results = []
        start = 0
        while True:
            idx = self.decompressed_data.find(field_name, start)
            if idx == -1:
                break
            val_offset = idx + len(field_name)
            # Assuming 4-byte little endian integers for gold/perks
            current_val = int.from_bytes(self.decompressed_data[val_offset:val_offset+4], 'little')
            results.append({
                'marker_offset': idx,
                'value_offset': val_offset,
                'current_value': current_val
            })
            start = idx + 1
        return results

    def patch_candidate(self, candidate, new_value):
        offset = candidate['value_offset']
        self.decompressed_data[offset:offset+4] = int(new_value).to_bytes(4, 'little')

    def save(self, output_path):
        # Recompress
        compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        new_compressed = compressor.compress(self.decompressed_data) + compressor.flush()
        
        # Construct final file
        final_data = self.header + new_compressed + self.trailing_data
        
        with open(output_path, 'wb') as f:
            f.write(final_data)
        
        return output_path
