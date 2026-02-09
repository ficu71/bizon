
import sys
from pathlib import Path

# Add project root to path
sys.path.append('/Users/f1cu_71/Desktop/biz/bizon')

from uese.core.universal_scanner import UniversalScanner

def scan_file(filename):
    scanner = UniversalScanner()
    path = Path(filename)
    blob = path.read_bytes()
    
    # scan for PNGs
    pngs = scanner._find_png_regions(blob)
    print(f"Found {len(pngs)} PNG regions:")
    for s, e in pngs:
        print(f"  PNG: {s:X} - {e:X} (Length: {e-s})")
        
    # scan for entropy
    entropy_regions = scanner._find_entropy_regions(blob)
    print(f"Found {len(entropy_regions)} high entropy regions:")
    for s, e in entropy_regions:
        print(f"  Entropy: {s:X} - {e:X} (Length: {e-s})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scan_with_uese.py <filename>")
    else:
        scan_file(sys.argv[1])
