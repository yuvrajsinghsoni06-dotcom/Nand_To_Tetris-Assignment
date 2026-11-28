"""
Compare capstone/assembler.py output against the official Nand2Tetris Assembler
for Add.asm, Max.asm, Rect.asm, and Pong.asm.

Usage:
    python compare_outputs.py --asm-dir <dir_with_official_asm> [--official-assembler <path_to_Assembler.bat>]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAPSTONE_DIR))

import assembler  # noqa: E402

PROGRAMS = ["Add", "Max", "Rect", "Pong"]


def compare_program(
    asm_path: Path, official_assembler: Path | None
) -> Tuple[bool, int, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        my_hack = tmp / f"{asm_path.stem}_mine.hack"
        assembler.assemble_file(asm_path, my_hack)
        my_lines = my_hack.read_text(encoding="utf-8").splitlines()

        for idx, line in enumerate(my_lines, start=1):
            if len(line) != 16 or not set(line).issubset({"0", "1"}):
                return False, len(my_lines), f"Invalid 16-bit line at {idx}: {line}"

        if official_assembler is None:
            return True, len(my_lines), "Assembled cleanly (no official assembler provided)"

        # Copy .asm to temp dir so official Assembler.bat writes <name>.hack there
        tmp_asm = tmp / asm_path.name
        tmp_asm.write_text(asm_path.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(
            [str(official_assembler), str(tmp_asm)],
            check=True,
            capture_output=True,
            text=True,
        )
        official_hack = tmp_asm.with_suffix(".hack")
        if not official_hack.exists():
            return False, len(my_lines), "Official assembler did not produce .hack output"

        official_lines = official_hack.read_text(encoding="utf-8").splitlines()
        if len(my_lines) != len(official_lines):
            return (
                False,
                len(my_lines),
                f"Line count mismatch: mine={len(my_lines)} vs official={len(official_lines)}",
            )

        for idx, (m_line, o_line) in enumerate(zip(my_lines, official_lines), start=1):
            if m_line != o_line:
                return (
                    False,
                    len(my_lines),
                    f"Mismatch at instruction {idx}: mine={m_line} vs official={o_line}",
                )

        return True, len(my_lines), "EXACT MATCH"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare assembler.py with official Hack Assembler")
    parser.add_argument(
        "--asm-dir",
        type=Path,
        required=True,
        help="Directory containing Add.asm, Max.asm, Rect.asm, Pong.asm (or subdirs add/, max/, rect/, pong/)",
    )
    parser.add_argument(
        "--official-assembler",
        type=Path,
        default=None,
        help="Path to official Nand2Tetris Assembler.bat / Assembler.sh",
    )
    args = parser.parse_args()

    all_passed = True
    for prog in PROGRAMS:
        candidates = [
            args.asm_dir / f"{prog}.asm",
            args.asm_dir / prog.lower() / f"{prog}.asm",
        ]
        asm_path = next((p for p in candidates if p.exists()), None)
        if asm_path is None:
            print(f"[MISSING] {prog}.asm not found under {args.asm_dir}")
            all_passed = False
            continue

        ok, count, msg = compare_program(asm_path, args.official_assembler)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {prog}.asm ({count} instructions): {msg}")
        if not ok:
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
