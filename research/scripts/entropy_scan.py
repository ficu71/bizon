
import sys
import math

def calculate_entropy(data):
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(x))/len(data)
        if p_x > 0:
            entropy += - p_x*math.log(p_x, 2)
    return entropy

def scan_entropy(filename, block_size=1024):
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"Scanning {filename} ({len(data)} bytes) for entropy...")
    print(f"Block size: {block_size}")
    print("Offset   | Entropy")
    print("-" * 20)
    
    high_entropy_start = -1
    
    for i in range(0, len(data), block_size):
        chunk = data[i:i+block_size]
        e = calculate_entropy(chunk)
        
        # formatting output to not be too verbose, show changes or high values
        if e > 7.5:
             if high_entropy_start == -1:
                 high_entropy_start = i
                 print(f"{i:08X} | {e:.4f} (High entropy start)")
        else:
            if high_entropy_start != -1:
                print(f"{i:08X} | {e:.4f} (High entropy end, length: {i - high_entropy_start})")
                high_entropy_start = -1
            
            # Print low entropy points occasionally or if very low
            if e < 1.0 or i % (block_size * 20) == 0:
                 print(f"{i:08X} | {e:.4f}")

    if high_entropy_start != -1:
        print(f"{len(data):08X} | End (High entropy region continued until EOF)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 entropy_scan.py <filename>")
    else:
        scan_entropy(sys.argv[1])
