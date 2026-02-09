from __future__ import annotations

from pathlib import Path

from .exclude import build_excluded_regions
from .patch import patch_file
from .report import export_json, export_markdown
from .scan import scan_exact


def _make_blob(size: int, value: int, offset: int) -> bytes:
    blob = bytearray(b"Aube.SaveHeader|Assembly-CSharp|GameSave.GameFormatter+Format\x00")
    if len(blob) < size:
        blob.extend(b"\x11" * (size - len(blob)))
    blob[offset : offset + 4] = value.to_bytes(4, "little", signed=False)
    return bytes(blob)


def main() -> int:
    root = Path.cwd()
    examples = root / "examples"
    output = root / "output"
    examples.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    off = 0x80
    s1 = _make_blob(512, 111, off)
    s2 = _make_blob(512, 222, off)
    s3 = _make_blob(512, 333, off)

    p1 = examples / "save_111.sav"
    p2 = examples / "save_222.sav"
    p3 = examples / "save_333.sav"
    p1.write_bytes(s1)
    p2.write_bytes(s2)
    p3.write_bytes(s3)

    excluded = [build_excluded_regions(s1, ["png", "entropy"]), build_excluded_regions(s2, ["png", "entropy"]), build_excluded_regions(s3, ["png", "entropy"])]
    candidates = scan_exact([s1, s2, s3], (111, 222, 333), "4", "u32", excluded)
    if not candidates:
        raise RuntimeError("Self-test fail: brak kandydatów")
    best = candidates[0]
    if best.offset != off or best.dtype != "u32" or best.width != 4:
        raise RuntimeError(f"Self-test fail: top candidate unexpected: off={best.offset:#x} dtype={best.dtype}")

    export_json(candidates, str(output / "report_selftest.json"), top=50)
    export_markdown(candidates, str(output / "report_selftest.md"), top=20)

    patched = output / "test_999.sav"
    result = patch_file(str(p3), str(patched), off, "u32", 999)
    value_after = int.from_bytes(patched.read_bytes()[off : off + 4], "little", signed=False)
    if value_after != 999:
        raise RuntimeError("Self-test fail: patch nie zadziałał")

    print("[OK] Self-test przeszedł")
    print(f"[OK] Top candidate: off={best.offset:#x} dtype={best.dtype} score={best.score}")
    print(f"[OK] Backup: {result.backup_path}")
    print(f"[OK] Raporty: {output / 'report_selftest.json'} , {output / 'report_selftest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
