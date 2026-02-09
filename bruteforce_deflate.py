
import sys
import zlib

def bruteforce_deflate(filename, start_offset, end_offset):
    with open(filename, 'rb') as f:
        f.seek(start_offset)
        data = f.read(end_offset - start_offset + 1024) # Read enough context

    print(f"Bruteforcing deflate from {start_offset} to {end_offset}...")
    
    for i in range(end_offset - start_offset):
        # file offset
        current_offset = start_offset + i
        chunk = data[i:]
        
        try:
            # Try raw deflate (-15)
            decompressed = zlib.decompress(chunk, -zlib.MAX_WBITS)
            if len(decompressed) > 100: # Filter out trivial successes
                print(f"SUCCESS at offset {current_offset} (0x{current_offset:X})")
                print(f"Size: {len(decompressed)}")
                # Save it
                out_name = f"{filename}.brute_{current_offset}.bin"
                with open(out_name, 'wb') as out:
                    out.write(decompressed)
                print(f"Saved to {out_name}")
                # Optional: peek at content
                print(f"Head: {decompressed[:50]}")
                break
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 bruteforce_deflate.py <filename> <start_offset> <end_offset>")
    else:
        start = sys.argv[2]
        end = sys.argv[3]
        try:
            s = int(start)
        except:
            try:
                s = int(start, 16)
            except:
                print("Invalid start")
                sys.exit(1)
        try:
            e = int(end)
        except:
            try:
                e = int(end, 16)
            except:
                print("Invalid end")
                sys.exit(1)
            
        bruteforce_deflate(sys.argv[1], s, e)
