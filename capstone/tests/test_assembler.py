"""Unit tests for the two-pass Hack assembler (capstone/assembler.py)."""

import io
import sys
import tempfile
import unittest
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAPSTONE_DIR))

import assembler  # noqa: E402


class TestHackAssembler(unittest.TestCase):
    def test_a_instructions_and_predefined_symbols(self):
        src = [
            "// Predefined symbols test",
            "@0",
            "@21",
            "@32767",
            "@SP",
            "@R15",
            "@SCREEN",
            "@KBD",
        ]
        code, _, warnings = assembler.assemble_lines(src, warn_stream=io.StringIO())
        self.assertEqual(warnings, [])
        self.assertEqual(
            code,
            [
                "0000000000000000",  # @0
                "0000000000010101",  # @21
                "0111111111111111",  # @32767
                "0000000000000000",  # @SP (0)
                "0000000000001111",  # @R15 (15)
                "0100000000000000",  # @SCREEN (16384)
                "0110000000000000",  # @KBD (24576)
            ],
        )

    def test_c_instructions(self):
        src = [
            "D=A",
            "M=D+1;JGT",
            "0;JMP",
            "AMD=D-M;JNE",
        ]
        code, _, _ = assembler.assemble_lines(src, warn_stream=io.StringIO())
        self.assertEqual(
            code,
            [
                "1110110000010000",  # D=A
                "1110011111001001",  # M=D+1;JGT
                "1110101010000111",  # 0;JMP
                "1111010011111101",  # AMD=D-M;JNE
            ],
        )

    def test_labels_and_variables(self):
        src = [
            "   // Forward jump",
            "   @END",
            "   0;JMP",
            "(LOOP)",
            "   @count   // First variable -> RAM[16]",
            "   M=M+1",
            "   @total   // Second variable -> RAM[17]",
            "   M=D",
            "   @count   // Reuses RAM[16]",
            "   D=M",
            "   @LOOP    // Backward jump -> ROM[2]",
            "   0;JMP",
            "(END)",
            "   @END",
            "   0;JMP",
        ]
        code, symtab, _ = assembler.assemble_lines(src, warn_stream=io.StringIO())
        self.assertEqual(symtab["LOOP"], 2)
        self.assertEqual(symtab["END"], 10)
        self.assertEqual(symtab["count"], 16)
        self.assertEqual(symtab["total"], 17)
        self.assertEqual(len(code), 12)
        for line in code:
            self.assertEqual(len(line), 16)
            self.assertTrue(set(line).issubset({"0", "1"}))

    def test_case2_duplicate_label_warning(self):
        src = [
            "@1",
            "(LOOP)",
            "D=A",
            "(LOOP)",
            "@LOOP",
            "0;JMP",
        ]
        warn_buf = io.StringIO()
        code, symtab, warnings = assembler.assemble_lines(src, warn_stream=warn_buf)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0], "Warning: duplicate label LOOP at line 4")
        self.assertIn("Warning: duplicate label LOOP at line 4", warn_buf.getvalue())
        # Must keep the first definition (ROM address 1), not overwrite with 2
        self.assertEqual(symtab["LOOP"], 1)
        self.assertEqual(code[2], "0000000000000001")

    def test_malformed_instruction_errors_cleanly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            asm_path = Path(tmpdir) / "bad.asm"
            hack_path = Path(tmpdir) / "bad.hack"
            asm_path.write_text("@1\nD=INVALID\n", encoding="utf-8")
            rc = assembler.main([str(asm_path), str(hack_path)])
            self.assertNotEqual(rc, 0)
            self.assertFalse(hack_path.exists())


if __name__ == "__main__":
    unittest.main()
