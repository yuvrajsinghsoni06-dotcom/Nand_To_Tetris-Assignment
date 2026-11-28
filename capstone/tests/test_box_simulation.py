"""
Programmatic verification of capstone/Box.hack on a minimal Hack CPU simulator.
Verifies:
  1. When KBD (RAM[24576]) != 0, exact 20x3 words starting at 19520 become -1 (0xFFFF).
  2. When KBD (RAM[24576]) == 0, those exact 60 words become 0 (0x0000).
  3. No screen word outside that 20x3 rectangle is modified.
"""

import unittest
from pathlib import Path

CAPSTONE_DIR = Path(__file__).resolve().parent.parent
BOX_HACK = CAPSTONE_DIR / "Box.hack"

COMP_OPS = {
    "0101010": lambda d, am: 0,
    "0111111": lambda d, am: 1,
    "0111010": lambda d, am: -1,
    "0001100": lambda d, am: d,
    "0110000": lambda d, am: am,
    "0001101": lambda d, am: ~d,
    "0110001": lambda d, am: ~am,
    "0001111": lambda d, am: -d,
    "0110011": lambda d, am: -am,
    "0011111": lambda d, am: d + 1,
    "0110111": lambda d, am: am + 1,
    "0001110": lambda d, am: d - 1,
    "0110010": lambda d, am: am - 1,
    "0000010": lambda d, am: d + am,
    "0010011": lambda d, am: d - am,
    "0000111": lambda d, am: am - d,
    "0000000": lambda d, am: d & am,
    "0010101": lambda d, am: d | am,
}


def to_signed16(val: int) -> int:
    val &= 0xFFFF
    return val - 0x10000 if val & 0x8000 else val


class HackSim:
    def __init__(self, rom_lines):
        self.rom = rom_lines
        self.ram = [0] * 24577
        self.a = 0
        self.d = 0
        self.pc = 0

    def step(self):
        inst = self.rom[self.pc]
        if inst[0] == "0":
            self.a = int(inst[1:], 2)
            self.pc += 1
            return

        a_bit = inst[3]
        comp_bits = "0" + inst[4:10]
        dest_bits = inst[10:13]
        jump_bits = inst[13:16]

        am = self.ram[self.a] if a_bit == "1" else self.a
        out = to_signed16(COMP_OPS[comp_bits](self.d, am))

        if dest_bits[2] == "1":
            self.ram[self.a] = out
        if dest_bits[1] == "1":
            self.d = out
        if dest_bits[0] == "1":
            self.a = out & 0x7FFF

        jlt = jump_bits[0] == "1" and out < 0
        jeq = jump_bits[1] == "1" and out == 0
        jgt = jump_bits[2] == "1" and out > 0

        if jlt or jeq or jgt:
            self.pc = self.a
        else:
            self.pc += 1


class TestBoxProgram(unittest.TestCase):
    def test_draw_and_clear_box(self):
        rom = BOX_HACK.read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(rom), 0)
        for line in rom:
            self.assertEqual(len(line), 16)

        sim = HackSim(rom)
        expected_box_addrs = {
            19520 + 32 * r + c for r in range(20) for c in range(3)
        }
        self.assertEqual(len(expected_box_addrs), 60)

        # 1. Press key ('A' = 65) and run enough cycles for a full frame
        sim.ram[24576] = 65
        for _ in range(3000):
            sim.step()

        for addr in range(16384, 24576):
            if addr in expected_box_addrs:
                self.assertEqual(sim.ram[addr], -1, f"Expected black at {addr}")
            else:
                self.assertEqual(sim.ram[addr], 0, f"Unexpected write at {addr}")

        # 2. Release key (KBD = 0) and run enough cycles to clear
        sim.ram[24576] = 0
        for _ in range(3000):
            sim.step()

        for addr in range(16384, 24576):
            self.assertEqual(sim.ram[addr], 0, f"Expected white at {addr}")


if __name__ == "__main__":
    unittest.main()
