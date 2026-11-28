// Box.asm - Interactive Box Drawing Program
// Course: ETCCNT301 - Nand to Tetris I (Capstone Project)
// Student: Yuvraj Singh Soni | Roll No: 2501010098 | K = 98
//
// Personalized Box Geometry:
//   Starting Row   = K = 98
//   Height         = 20 pixels (rows 98..117)
//   Width          = 16 * ((98 % 4) + 1) = 48 pixels (3 words/row)
//   Start Address  = SCREEN (16384) + 32 * 98 = 19520

(MAIN_LOOP)
    @KBD
    D=M
    @CLEAR_BOX
    D;JEQ           // If KBD == 0 (no key pressed), clear the box

(DRAW_BOX)
    @fill_val
    M=-1            // -1 (0xFFFF) sets 16 consecutive pixels to black
    @FILL_BOX
    0;JMP

(CLEAR_BOX)
    @fill_val
    M=0             // 0 (0x0000) sets 16 consecutive pixels to white

(FILL_BOX)
    @19520          // Row 98 start address: 16384 + 32 * 98 = 19520
    D=A
    @row_addr
    M=D

    @20             // BOX_HEIGHT = 20 rows
    D=A
    @row_count
    M=D

(ROW_LOOP)
    @row_count
    D=M
    @MAIN_LOOP
    D;JEQ           // All 20 rows processed -> return to keyboard monitor

    @row_addr
    D=M
    @col_addr
    M=D             // Start at left edge of current row

    @3              // Words per row = (98 % 4) + 1 = 3 (48 pixels)
    D=A
    @col_count
    M=D

(COL_LOOP)
    @col_count
    D=M
    @NEXT_ROW
    D;JEQ           // All 3 words in current row written -> advance row

    @fill_val
    D=M
    @col_addr
    A=M
    M=D             // Write -1 (black) or 0 (white) to screen word

    @col_addr
    M=M+1           // Move to next 16-pixel word in row

    @col_count
    M=M-1
    @COL_LOOP
    0;JMP

(NEXT_ROW)
    @32
    D=A
    @row_addr
    M=D+M           // Next row is +32 words away in Hack screen memory

    @row_count
    M=M-1
    @ROW_LOOP
    0;JMP
