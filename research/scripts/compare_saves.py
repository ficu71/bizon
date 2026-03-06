
import sys
from pathlib import Path

def compare_files(file_a, file_b):
    try:
        with open(file_a, 'rb') as f1, open(file_b, 'rb') as f2:
            data_a = f1.read()
            data_b = f2.read()
    except FileNotFoundError:
        print(f"Error: One of the files not found: {file_a}, {file_b}")
        return

    len_a = len(data_a)
    len_b = len(data_b)
    
    print(f"File A: {len_a} bytes")
    print(f"File B: {len_b} bytes")
    
    min_len = min(len_a, len_b)
    
    diff_count = 0
    print("\nDifferences (Offset: A -> B):")
    
    # Only show first 100 diffs to avoid spam
    max_diffs = 100
    
    for i in range(min_len):
        if data_a[i] != data_b[i]:
            diff_count += 1
            if diff_count <= max_diffs:
                # Show context
                start = max(0, i - 8)
                end = min(min_len, i + 8)
                context_a = data_a[start:end].hex()
                context_b = data_b[start:end].hex()
                print(f"0x{i:08X}: 0x{data_a[i]:02X} -> 0x{data_b[i]:02X}")

    print(f"\nTotal differences found: {diff_count}")
    if len_a != len_b:
        print(f"Length difference: {abs(len_a - len_b)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 compare_saves.py <file_a> <file_b>")
    else:
        compare_files(sys.argv[1], sys.argv[2])
