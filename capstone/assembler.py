"""
Two-Pass Hack Assembler
Capstone Project - ETCCNT301 (Nand to Tetris I)
Student: Yuvraj Singh Soni | Roll No: 2501010098 | K = 98
K-dependent feature (K % 3 == 2): Case 2 - Duplicate label warning without overwriting.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PREDEFINED_SYMBOLS: Dict[str, int] = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "SCREEN": 16384,
    "KBD": 24576,
    **{f"R{i}": i for i in range(16)},
}

DEST_TABLE: Dict[str, str] = {
    "": "000",
    "M": "001",
    "D": "010",
    "MD": "011",
    "A": "100",
    "AM": "101",
    "AD": "110",
    "AMD": "111",
}

JUMP_TABLE: Dict[str, str] = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

COMP_TABLE: Dict[str, str] = {
    # a = 0
    "0": "0101010",
    "1": "0111111",
    "-1": "0111010",
    "D": "0001100",
    "A": "0110000",
    "!D": "0001101",
    "!A": "0110001",
    "-D": "0001111",
    "-A": "0110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "D|A": "0010101",
    # a = 1
    "M": "1110000",
    "!M": "1110001",
    "-M": "1110011",
    "M+1": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "D|M": "1010101",
}

# Valid Hack symbol characters: letters, digits, _, ., $, : (cannot start with digit)
SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


class AssemblerError(Exception):
    """Raised when an invalid Hack assembly instruction or syntax is encountered."""

    def __init__(self, line_number: int, message: str) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {line_number}: {message}")


def clean_line(raw_line: str) -> str:
    """Strip inline comments and all whitespace from an assembly line."""
    no_comment = raw_line.split("//", 1)[0]
    return "".join(no_comment.split())


def first_pass(
    lines: List[str], warn_stream=None
) -> Tuple[Dict[str, int], List[Tuple[int, str]], List[str]]:
    """
    Pass 1: Collect label declarations and build the initial symbol table.

    Returns:
        symbol_table: Predefined symbols + label ROM addresses.
        instructions: List of (original_line_number, cleaned_instruction).
        warnings: List of warning messages generated (e.g., duplicate labels).
    """
    if warn_stream is None:
        warn_stream = sys.stderr

    symbol_table: Dict[str, int] = dict(PREDEFINED_SYMBOLS)
    instructions: List[Tuple[int, str]] = []
    warnings: List[str] = []
    rom_address = 0

    for line_num, raw_line in enumerate(lines, start=1):
        cleaned = clean_line(raw_line)
        if not cleaned:
            continue

        if cleaned.startswith("(") and cleaned.endswith(")"):
            label = cleaned[1:-1]
            if not label or not SYMBOL_RE.match(label):
                raise AssemblerError(line_num, f"invalid label declaration '{cleaned}'")

            # K % 3 == 2 (Case 2): Warn on duplicate label without overwriting
            if label in symbol_table:
                warning_msg = f"Warning: duplicate label {label} at line {line_num}"
                warnings.append(warning_msg)
                print(warning_msg, file=warn_stream)
            else:
                symbol_table[label] = rom_address
        else:
            instructions.append((line_num, cleaned))
            rom_address += 1

    return symbol_table, instructions, warnings


def encode_a_instruction(
    operand: str,
    line_num: int,
    symbol_table: Dict[str, int],
    next_ram_address: int,
) -> Tuple[str, int]:
    """Encode an A-instruction (@value or @symbol) into a 16-bit binary string."""
    if not operand:
        raise AssemblerError(line_num, "empty A-instruction '@'")

    if operand.isdigit():
        value = int(operand)
        if value < 0 or value > 32767:
            raise AssemblerError(
                line_num, f"A-instruction constant {value} out of range (0..32767)"
            )
    else:
        if not SYMBOL_RE.match(operand):
            raise AssemblerError(line_num, f"invalid A-instruction operand '@{operand}'")
        if operand not in symbol_table:
            symbol_table[operand] = next_ram_address
            next_ram_address += 1
        value = symbol_table[operand]

    return f"0{value:015b}", next_ram_address


def encode_c_instruction(instruction: str, line_num: int) -> str:
    """Encode a C-instruction (dest=comp;jump) into a 16-bit binary string."""
    dest = ""
    jump = ""
    rest = instruction

    if "=" in rest:
        parts = rest.split("=")
        if len(parts) != 2:
            raise AssemblerError(line_num, f"invalid C-instruction '{instruction}'")
        dest, rest = parts

    if ";" in rest:
        parts = rest.split(";")
        if len(parts) != 2:
            raise AssemblerError(line_num, f"invalid C-instruction '{instruction}'")
        comp, jump = parts
    else:
        comp = rest

    if dest not in DEST_TABLE:
        raise AssemblerError(line_num, f"invalid dest '{dest}' in '{instruction}'")
    if comp not in COMP_TABLE:
        raise AssemblerError(line_num, f"invalid comp '{comp}' in '{instruction}'")
    if jump not in JUMP_TABLE:
        raise AssemblerError(line_num, f"invalid jump '{jump}' in '{instruction}'")

    return f"111{COMP_TABLE[comp]}{DEST_TABLE[dest]}{JUMP_TABLE[jump]}"


def second_pass(
    instructions: List[Tuple[int, str]],
    symbol_table: Dict[str, int],
) -> List[str]:
    """Pass 2: Translate instructions into 16-bit Hack machine code strings."""
    machine_code: List[str] = []
    next_ram_address = 16

    for line_num, inst in instructions:
        if inst.startswith("@"):
            binary, next_ram_address = encode_a_instruction(
                inst[1:], line_num, symbol_table, next_ram_address
            )
        else:
            binary = encode_c_instruction(inst, line_num)

        if len(binary) != 16:
            raise AssemblerError(line_num, f"internal error: encoded length {len(binary)} != 16")
        machine_code.append(binary)

    return machine_code


def assemble_lines(
    lines: List[str], warn_stream=None
) -> Tuple[List[str], Dict[str, int], List[str]]:
    """Assemble Hack assembly source lines into 16-bit binary strings."""
    symbol_table, instructions, warnings = first_pass(lines, warn_stream=warn_stream)
    machine_code = second_pass(instructions, symbol_table)
    return machine_code, symbol_table, warnings


def assemble_file(
    input_path: Path, output_path: Optional[Path] = None, warn_stream=None
) -> Path:
    """Assemble a .asm file and write the resulting .hack file."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".hack")

    source_lines = input_path.read_text(encoding="utf-8").splitlines()
    machine_code, _, _ = assemble_lines(source_lines, warn_stream=warn_stream)

    output_content = "\n".join(machine_code) + ("\n" if machine_code else "")
    output_path.write_text(output_content, encoding="utf-8")
    return output_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Two-Pass Hack Assembler (Yuvraj Singh Soni | K=98, Case 2)"
    )
    parser.add_argument("input_asm", type=Path, help="Path to input .asm file")
    parser.add_argument(
        "output_hack",
        type=Path,
        nargs="?",
        default=None,
        help="Optional path to output .hack file",
    )
    args = parser.parse_args(argv)

    try:
        out_path = assemble_file(args.input_asm, args.output_hack)
        print(f"Assembled '{args.input_asm}' -> '{out_path}'")
        return 0
    except (AssemblerError, FileNotFoundError, OSError) as exc:
        print(f"Assembly error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
