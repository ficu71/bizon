from __future__ import annotations

import struct

from .util import Region, merge_regions, shannon_entropy

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def find_png_regions(blob: bytes) -> list[Region]:
    regions: list[Region] = []
    start = 0
    while True:
        idx = blob.find(PNG_MAGIC, start)
        if idx == -1:
            break
        cursor = idx + len(PNG_MAGIC)
        end = len(blob)
        try:
            while cursor + 8 <= len(blob):
                chunk_len = struct.unpack(">I", blob[cursor : cursor + 4])[0]
                chunk_type = blob[cursor + 4 : cursor + 8]
                cursor += 8
                data_end = cursor + chunk_len
                crc_end = data_end + 4
                if crc_end > len(blob):
                    end = len(blob)
                    break
                cursor = crc_end
                if chunk_type == b"IEND":
                    end = cursor
                    break
        except Exception:
            end = len(blob)
        regions.append(Region(start=idx, end=end, reason="png"))
        start = max(idx + 1, end)
    return regions


def find_entropy_regions(
    blob: bytes, window: int = 4096, step: int = 2048, threshold: float = 7.7
) -> list[Region]:
    regions: list[Region] = []
    if window <= 0 or step <= 0 or len(blob) < window:
        return regions
    for off in range(0, len(blob) - window + 1, step):
        ent = shannon_entropy(blob[off : off + window])
        if ent >= threshold:
            regions.append(Region(start=off, end=off + window, reason="entropy"))
    return merge_regions(regions)


def build_excluded_regions(blob: bytes, exclude_kinds: list[str]) -> list[Region]:
    if "none" in exclude_kinds:
        return []
    regions: list[Region] = []
    if "png" in exclude_kinds:
        regions.extend(find_png_regions(blob))
    if "entropy" in exclude_kinds:
        regions.extend(find_entropy_regions(blob))
    return merge_regions(regions)
