# ETCCNT301 – Nand to Tetris I: Capstone Project Report

**Project Title:** Make the Computer Draw a Box  
**Student Name:** Yuvraj Singh Soni  
**University Roll Number:** `2501010098`  
**Personal Number ($K$):** `98`  
**Institution:** K.R. Mangalam University  

---

## 1. Personalization & Box Geometry

From the university roll number `2501010098`, the personal parameter is $K = 98$ (the last two digits). All project-specific parameters are derived deterministically from $K$:

- **Starting Row:** $\text{BOX\_START\_ROW} = K = 98$
- **Box Height:** $\text{BOX\_HEIGHT} = 20$ pixels (rows `98` through `117` inclusive)
- **Box Width:** $\text{BOX\_WIDTH} = 16 \times ((98 \bmod 4) + 1) = 16 \times 3 = 48$ pixels ($3$ consecutive 16-bit words per row, aligned to the left edge)
- **Starting Screen Address:** $16384 + (32 \times 98) = 16384 + 3136 = 19520$
- **Assembler Feature ($K \bmod 3$):** $98 \bmod 3 = 2$ → **Case 2: Duplicate Label Warning**

---

## 2. Part A – Hack Computer Architecture (HDL)

The Hack computer was implemented across three hierarchical HDL modules:

1. **`CPU.hdl`**: Decodes 16-bit instructions using `instruction[15]` as the opcode (`0` for A-instruction, `1` for C-instruction). During a C-instruction, `instruction[12]` selects between `ARegister` and `inM`, `instruction[11..6]` drives the `ALU` (`zx, nx, zy, ny, f, no`), `instruction[5..3]` controls destination loading (`loadA`, `loadD`, `writeM`), and `instruction[2..0]` evaluates jump conditions against `ALU` status flags `ng` and `zr` to control the `PC`.
2. **`Memory.hdl`**: Maps the 15-bit address bus using `address[13..14]` via `DMux4Way` (write enable) and `Mux4Way16` (read selection) across `RAM16K` (`0x0000–0x3FFF`), `Screen` (`0x4000–0x5FFF`), and `Keyboard` (`0x6000`).
3. **`Computer.hdl`**: Integrates `ROM32K`, `CPU`, and `Memory`, wiring `pc` to `ROM32K`, `instruction` to `CPU`, and `outM`/`writeM`/`addressM`/`inM` between `CPU` and `Memory`, with `reset` propagated to `CPU`.

### Official Hardware Simulator Test Results
*(Insert genuine screenshots captured from `HardwareSimulator.bat` below after execution on the Nand2Tetris tools suite.)*

- `CPU.tst`: `evidence/CPU_test.png` *(Pending official Nand2Tetris tool execution)*
- `Memory.tst`: `evidence/Memory_test.png` *(Pending official Nand2Tetris tool execution)*
- `ComputerAdd.tst`: `evidence/ComputerAdd_test.png` *(Pending official Nand2Tetris tool execution)*
- `ComputerMax.tst`: `evidence/ComputerMax_test.png` *(Pending official Nand2Tetris tool execution)*
- `ComputerRect.tst`: `evidence/ComputerRect_test.png` *(Pending official Nand2Tetris tool execution)*

---

## 3. Part B – Two-Pass Hack Assembler (`assembler.py`)

A standalone two-pass Hack assembler was implemented in Python without `eval()`, using explicit parsing and validated lookup tables (`DEST_TABLE`, `COMP_TABLE`, `JUMP_TABLE`, `PREDEFINED_SYMBOLS`):

- **Pass 1 (`first_pass`)**: Strips `//` comments and whitespace, preserves 1-based source line numbers, records `(LABEL)` ROM addresses without consuming instruction addresses, and implements **Case 2 ($98 \bmod 3 = 2$)**: when a label is declared more than once (or collides with an existing symbol), it prints `Warning: duplicate label <LABEL> at line <LINE>` to `stderr` and preserves the original symbol address deterministically.
- **Pass 2 (`second_pass`)**: Translates A-instructions (`0` + 15-bit binary, allocating new variables sequentially from RAM address `16`) and C-instructions (`111` + 7-bit `comp` + 3-bit `dest` + 3-bit `jump`). Invalid mnemonics or out-of-range constants raise `AssemblerError` with the exact source line number and return exit code `1` without writing partial `.hack` output.

### Verification Results
- **Unit Tests (`tests/test_assembler.py`)**: All 5 tests passed (`test_a_instructions_and_predefined_symbols`, `test_c_instructions`, `test_labels_and_variables`, `test_case2_duplicate_label_warning`, `test_malformed_instruction_errors_cleanly`).
- **Official Assembler Comparison (`tests/compare_outputs.py`)**: Ready to compare `Add.asm`, `Max.asm`, `Rect.asm`, and `Pong.asm` line-by-line once the official `Assembler.bat` and `projects/06` files are available.

---

## 4. Part C – Interactive Box Program (`Box.asm` & `Box.hack`)

`Box.asm` continuously monitors `KBD` (`RAM[24576]`) in `MAIN_LOOP`:
- When `KBD != 0`, `DRAW_BOX` sets `fill_val = -1` (`0xFFFF`, 16 black pixels).
- When `KBD == 0`, `CLEAR_BOX` sets `fill_val = 0` (`0x0000`, 16 white pixels).
- `FILL_BOX` initializes `row_addr = 19520` and `row_count = 20`. `ROW_LOOP` iterates over the 20 rows, `COL_LOOP` writes `fill_val` to 3 consecutive words (`48` pixels), and `NEXT_ROW` advances `row_addr` by `32` words. Only the `60` words belonging to the rectangle are modified.

`Box.hack` was assembled directly using `python capstone/assembler.py capstone/Box.asm capstone/Box.hack` and verified programmatically with `tests/test_box_simulation.py` (`test_draw_and_clear_box`: passed).

### CPU Emulator Output Screenshot
- `Box.hack` running in `CPUEmulator.bat`: `evidence/Box_output.png` *(Pending official Nand2Tetris tool execution)*

---

## 5. Development Mistake & Fix

During the implementation of `Box.asm`, the row-advance step in `NEXT_ROW` initially used `M=M+D` to add `32` (`D`) to `row_addr` (`M`). When `assembler.py` was executed on `Box.asm`, it rejected the instruction with `Assembly error: Line 78: invalid comp 'M+D' in 'M=M+D'`. In the Hack ALU specification, addition between `D` and `M` is only encoded as `D+M` (`1000010`); `M+D` is not a valid mnemonic in the Hack C-instruction `comp` table. Replacing `M=M+D` with `M=D+M` resolved the assembly error immediately, and `Box.asm` assembled cleanly into `Box.hack` and passed the `test_box_simulation.py` verification.
