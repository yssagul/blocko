#!/usr/bin/env python3
"""
Reconstruct and analyze two 4x4x4 block stacking games.
"""

# Block placement rules:
# - Position (x, y, z) is the "first" cell of the block
# - Orientation X: second cell at (x+1, y, z)
# - Orientation Y: second cell at (x, y+1, z)
# - Orientation Z: second cell at (x, y, z+1)
# - Block type "BW" no flip: first=B, second=W; flip: first=W, second=B
# - Block type "BR" no flip: first=B, second=R; flip: first=R, second=B
# - Block type "WR" no flip: first=W, second=R; flip: first=R, second=W
# - Block type "BB" no flip: first=B, second=B (flip irrelevant)
# - Block type "WW" no flip: first=W, second=W (flip irrelevant)
# - Gravity: blocks drop to lowest available z

# Stacking rules:
# - Same non-red color cannot stack on itself (white on white = illegal, black on black = illegal)
# - Red is wild (can go on anything, anything can go on red)
# - Ground (z=0) can accept anything

def get_block_colors(block_type, flip):
    """Return (color1, color2) for the block."""
    c1, c2 = block_type[0], block_type[1]
    if flip:
        return c2, c1
    return c1, c2

def get_second_cell(x, y, z, orient):
    """Return the second cell position based on orientation."""
    if orient == 'X':
        return (x+1, y, z)
    elif orient == 'Y':
        return (x, y+1, z)
    elif orient == 'Z':
        return (x, y, z+1)

def reconstruct_game(moves):
    """
    Reconstruct the board state from a list of moves.
    Board is a 4x4x4 grid, indexed [x][y][z].
    Returns the final board state.
    """
    # Initialize empty board
    board = [[[None for z in range(4)] for y in range(4)] for x in range(4)]

    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        x, y, z = pos
        c1, c2 = get_block_colors(block_type, flip)

        if orient == 'Z':
            # Vertical block: both cells in same column (x,y)
            # The block occupies z and z+1 at position (x,y)
            # With gravity, it drops to the lowest available position
            # Find the current height of column (x,y)
            col_height = 0
            for zz in range(4):
                if board[x][y][zz] is not None:
                    col_height = zz + 1
                else:
                    break
            # Place at col_height and col_height+1
            actual_z = col_height
            if actual_z + 1 >= 4 and actual_z >= 4:
                print(f"  ERROR Move {move_num}: Column ({x},{y}) overflow!")
                continue
            if actual_z + 1 > 3:
                print(f"  ERROR Move {move_num}: Column ({x},{y}) would exceed z=3!")
                continue
            board[x][y][actual_z] = c1
            board[x][y][actual_z + 1] = c2
            if actual_z != z:
                pass  # gravity adjusted
        elif orient == 'X':
            # Horizontal along x-axis: (x,y,z) and (x+1,y,z)
            # Both cells need to settle with gravity independently?
            # No - a horizontal block placed at height z means both cells
            # are at the same z level. With gravity, the block drops until
            # BOTH cells are supported.
            # The effective z is max of the heights of columns (x,y) and (x+1,y)
            h1 = 0
            for zz in range(4):
                if board[x][y][zz] is not None:
                    h1 = zz + 1
                else:
                    break
            h2 = 0
            for zz in range(4):
                if board[x+1][y][zz] is not None:
                    h2 = zz + 1
                else:
                    break
            actual_z = max(h1, h2)
            if actual_z > 3:
                print(f"  ERROR Move {move_num}: Horizontal X block at ({x},{y}) would exceed z=3!")
                continue
            board[x][y][actual_z] = c1
            board[x+1][y][actual_z] = c2
        elif orient == 'Y':
            # Horizontal along y-axis: (x,y,z) and (x,y+1,z)
            h1 = 0
            for zz in range(4):
                if board[x][y][zz] is not None:
                    h1 = zz + 1
                else:
                    break
            h2 = 0
            for zz in range(4):
                if board[x][y+1][zz] is not None:
                    h2 = zz + 1
                else:
                    break
            actual_z = max(h1, h2)
            if actual_z > 3:
                print(f"  ERROR Move {move_num}: Horizontal Y block at ({x},{y}) would exceed z=3!")
                continue
            board[x][y][actual_z] = c1
            board[x][y+1][actual_z] = c2

    return board

def print_board(board):
    """Print the board layer by layer from top (z=3) to bottom (z=0)."""
    for z in range(3, -1, -1):
        print(f"\n  Layer z={z}:")
        print(f"       x=0  x=1  x=2  x=3")
        for y in range(4):
            row = f"  y={y}  "
            for x in range(4):
                cell = board[x][y][z]
                if cell is None:
                    row += " .   "
                else:
                    row += f" {cell}   "
            print(row)

def compute_score(board):
    """
    Compute scores for White and Black.
    Exterior faces: top (z=3), front (y=0), back (y=3), left (x=0), right (x=3)
    Bottom (z=0) is NOT scored.
    """
    white_score = 0
    black_score = 0

    face_details = {
        'top': {'W': 0, 'B': 0, 'R': 0, 'empty': 0},
        'front': {'W': 0, 'B': 0, 'R': 0, 'empty': 0},
        'back': {'W': 0, 'B': 0, 'R': 0, 'empty': 0},
        'left': {'W': 0, 'B': 0, 'R': 0, 'empty': 0},
        'right': {'W': 0, 'B': 0, 'R': 0, 'empty': 0},
    }

    # Top face: z=3, all x,y
    for x in range(4):
        for y in range(4):
            cell = board[x][y][3]
            if cell == 'W':
                white_score += 1
                face_details['top']['W'] += 1
            elif cell == 'B':
                black_score += 1
                face_details['top']['B'] += 1
            elif cell == 'R':
                face_details['top']['R'] += 1
            else:
                face_details['top']['empty'] += 1

    # Front face: y=0, all x, all z
    for x in range(4):
        for z in range(4):
            cell = board[x][0][z]
            if cell == 'W':
                white_score += 1
                face_details['front']['W'] += 1
            elif cell == 'B':
                black_score += 1
                face_details['front']['B'] += 1
            elif cell == 'R':
                face_details['front']['R'] += 1
            else:
                face_details['front']['empty'] += 1

    # Back face: y=3, all x, all z
    for x in range(4):
        for z in range(4):
            cell = board[x][3][z]
            if cell == 'W':
                white_score += 1
                face_details['back']['W'] += 1
            elif cell == 'B':
                black_score += 1
                face_details['back']['B'] += 1
            elif cell == 'R':
                face_details['back']['R'] += 1
            else:
                face_details['back']['empty'] += 1

    # Left face: x=0, all y, all z
    for y in range(4):
        for z in range(4):
            cell = board[0][y][z]
            if cell == 'W':
                white_score += 1
                face_details['left']['W'] += 1
            elif cell == 'B':
                black_score += 1
                face_details['left']['B'] += 1
            elif cell == 'R':
                face_details['left']['R'] += 1
            else:
                face_details['left']['empty'] += 1

    # Right face: x=3, all y, all z
    for y in range(4):
        for z in range(4):
            cell = board[3][y][z]
            if cell == 'W':
                white_score += 1
                face_details['right']['W'] += 1
            elif cell == 'B':
                black_score += 1
                face_details['right']['B'] += 1
            elif cell == 'R':
                face_details['right']['R'] += 1
            else:
                face_details['right']['empty'] += 1

    return white_score, black_score, face_details

def analyze_column_control(board):
    """For each column (x,y), find the topmost occupied cell and its color."""
    control = [[None for y in range(4)] for x in range(4)]
    for x in range(4):
        for y in range(4):
            for z in range(3, -1, -1):
                if board[x][y][z] is not None:
                    control[x][y] = (board[x][y][z], z)
                    break
    return control

def print_column_control(control):
    """Print the column control grid."""
    print(f"       x=0    x=1    x=2    x=3")
    for y in range(4):
        row = f"  y={y}  "
        for x in range(4):
            if control[x][y] is None:
                row += " .     "
            else:
                color, z = control[x][y]
                row += f" {color}(z{z}) "
        print(row)

def print_top_layer(board):
    """Print what's at z=3 for each column."""
    print(f"       x=0  x=1  x=2  x=3")
    for y in range(4):
        row = f"  y={y}  "
        for x in range(4):
            cell = board[x][y][3]
            if cell is None:
                row += " .   "
            else:
                row += f" {cell}   "
        print(row)

def analyze_corners(board):
    """Analyze the 8 corners at z=3 (most valuable positions)."""
    corners = [(0,0,3), (0,3,3), (3,0,3), (3,3,3)]
    print("  Top corners (z=3, 3 exterior faces each):")
    for x, y, z in corners:
        cell = board[x][y][z]
        print(f"    ({x},{y},{z}): {cell if cell else 'empty'}")

    # Also check z=0 corners (2 faces each, since bottom not scored)
    # Actually at z=0, corners touch 2 side faces but bottom not scored
    # At z=3, corners touch top + 2 side faces = 3 faces

def count_blocks_by_player(moves):
    """Count block types used by each player."""
    white_blocks = {}
    black_blocks = {}
    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        if player == 'White':
            white_blocks[block_type] = white_blocks.get(block_type, 0) + 1
        else:
            black_blocks[block_type] = black_blocks.get(block_type, 0) + 1
    return white_blocks, black_blocks


# ============================================================
# GAME 1 MOVES
# ============================================================
game1_moves = [
    ('White', 'BW', (1,2,0), 'X', False),   # Move 1
    ('Black', 'BB', (0,0,0), 'Z', False),    # Move 2
    ('White', 'WW', (0,0,2), 'Z', False),    # Move 3
    ('Black', 'BB', (3,3,0), 'Z', False),    # Move 4
    ('White', 'WW', (3,3,2), 'Z', False),    # Move 5
    ('Black', 'BB', (3,0,0), 'Z', True),     # Move 6  (flip: B->B, no change for BB)
    ('White', 'WW', (3,0,2), 'Z', False),    # Move 7
    ('Black', 'BR', (0,3,0), 'Z', True),     # Move 8  (flip: R at z=0, B at z=1)
    ('White', 'WR', (0,3,2), 'Z', True),     # Move 9  (flip: R at z=2, W at z=3)
    ('Black', 'BR', (1,0,0), 'Z', True),     # Move 10 (flip: R at z=0, B at z=1)
    ('White', 'WR', (1,0,2), 'Z', True),     # Move 11 (flip: R at z=2, W at z=3)
    ('Black', 'BR', (0,1,0), 'Y', True),     # Move 12 (flip: R,B -> Y: R@(0,1,z), B@(0,2,z))
    ('White', 'BR', (1,1,0), 'X', True),     # Move 13 (flip: R,B -> X: R@(1,1,z), B@(2,1,z))
    ('Black', 'BR', (0,1,1), 'Z', False),    # Move 14 (no flip: B@z=1, R@z=2)
    ('White', 'BR', (2,2,1), 'Z', True),     # Move 15 (flip: R@z_low, B@z_high)
    ('Black', 'BR', (0,2,1), 'Z', True),     # Move 16 (flip: R@z_low, B@z_high)
    ('White', 'WR', (0,1,3), 'Y', True),     # Move 17 (flip: R,W -> Y: R@(0,1,z), W@(0,2,z))
    ('Black', 'BR', (2,0,0), 'Z', False),    # Move 18 (no flip: B@z_low, R@z_high)
    ('White', 'BR', (1,2,1), 'Z', True),     # Move 19 (flip: R@z_low, B@z_high)
    ('Black', 'BW', (2,0,2), 'Z', True),     # Move 20 (flip: W@z_low, B@z_high)
    ('White', 'BW', (3,2,0), 'Z', False),    # Move 21 (no flip: B@z_low, W@z_high)
    ('Black', 'WR', (1,1,1), 'Z', True),     # Move 22 (flip: R@z_low, W@z_high)
    ('White', 'BW', (3,1,0), 'Z', False),    # Move 23 (no flip: B@z_low, W@z_high)
    ('Black', 'WR', (2,1,1), 'Z', True),     # Move 24 (flip: R@z_low, W@z_high)
    ('White', 'BW', (1,3,0), 'Z', False),    # Move 25 (no flip: B@z_low, W@z_high)
    ('Black', 'BW', (1,1,3), 'Y', False),    # Move 26 (no flip: B@(1,1,3), W@(1,2,3))
    ('White', 'BW', (2,3,0), 'Z', False),    # Move 27 (no flip: B@z_low, W@z_high)
    ('Black', 'BW', (2,1,3), 'Y', False),    # Move 28 (no flip: B@(2,1,3), W@(2,2,3))
    ('White', 'WR', (1,3,2), 'Z', True),     # Move 29 (flip: R@z_low, W@z_high)
    ('Black', 'WR', (3,1,2), 'Z', True),     # Move 30 (flip: R@z_low, W@z_high)
    ('White', 'WR', (2,3,2), 'Z', True),     # Move 31 (flip: R@z_low, W@z_high)
    ('Black', 'WR', (3,2,2), 'Z', True),     # Move 32 (flip: R@z_low, W@z_high)
]

# ============================================================
# GAME 2 MOVES
# ============================================================
game2_moves = [
    ('White', 'BB', (1,1,0), 'Z', False),    # Move 1
    ('Black', 'BB', (0,0,0), 'Z', True),     # Move 2
    ('White', 'BB', (2,1,0), 'Z', False),    # Move 3
    ('Black', 'BR', (0,0,2), 'Z', True),     # Move 4
    ('White', 'WW', (0,3,0), 'Z', False),    # Move 5
    ('Black', 'BR', (0,3,2), 'Z', True),     # Move 6
    ('White', 'WW', (3,3,0), 'Z', False),    # Move 7
    ('Black', 'BR', (3,3,2), 'Z', True),     # Move 8
    ('White', 'WW', (3,0,0), 'Z', False),    # Move 9
    ('Black', 'BR', (3,0,2), 'Z', True),     # Move 10
    ('White', 'BW', (2,2,0), 'Y', False),    # Move 11  BW Y no flip: B@(2,2,z) W@(2,3,z)
    ('Black', 'BR', (1,1,2), 'Z', True),     # Move 12
    ('White', 'BW', (1,2,0), 'Y', False),    # Move 13  BW Y no flip: B@(1,2,z) W@(1,3,z)
    ('Black', 'BW', (2,1,2), 'Z', True),     # Move 14  flip: W@z_low, B@z_high
    ('White', 'BR', (1,2,1), 'Z', True),     # Move 15
    ('Black', 'BR', (1,3,1), 'Z', True),     # Move 16
    ('White', 'BR', (2,2,1), 'Z', True),     # Move 17
    ('Black', 'BR', (2,3,1), 'Z', False),    # Move 18  no flip: B@z_low, R@z_high
    ('White', 'BW', (3,1,0), 'Z', False),    # Move 19  no flip: B@z_low, W@z_high
    ('Black', 'BW', (2,2,3), 'Y', True),     # Move 20  flip: W@(2,2,3), B@(2,3,3)
    ('White', 'BW', (3,2,0), 'Z', False),    # Move 21  no flip: B@z_low, W@z_high
    ('Black', 'BW', (1,0,0), 'Z', True),     # Move 22  flip: W@z_low, B@z_high
    ('White', 'BW', (2,0,0), 'Z', False),    # Move 23  no flip: B@z_low, W@z_high
    ('Black', 'WR', (1,0,2), 'X', False),    # Move 24  no flip: W@(1,0,z), R@(2,0,z)
    ('White', 'WR', (3,2,2), 'Z', True),     # Move 25  flip: R@z_low, W@z_high
    ('Black', 'WR', (0,1,0), 'Z', True),     # Move 26  flip: R@z_low, W@z_high
    ('White', 'WR', (3,1,2), 'Z', True),     # Move 27  flip: R@z_low, W@z_high
    ('Black', 'WR', (0,2,0), 'Z', True),     # Move 28  flip: R@z_low, W@z_high
    ('White', 'WR', (1,2,3), 'Y', True),     # Move 29  flip: R@(1,2,3), W@(1,3,3)
    ('Black', 'WR', (0,1,2), 'Z', True),     # Move 30  flip: R@z_low, W@z_high
    ('White', 'WR', (0,2,2), 'Z', True),     # Move 31  flip: R@z_low, W@z_high
    ('Black', 'WR', (1,0,3), 'X', True),     # Move 32  flip: R@(1,0,3), W@(2,0,3) -- wait
    # Actually flip for WR: no flip = W,R; flip = R,W
    # So move 32 flip: R@(1,0,3), W@(2,0,3)... but wait, X orient means (x,y,z) and (x+1,y,z)
    # WR flipped: first=R, second=W -> R@(1,0,3), W@(2,0,3)
]

print("=" * 70)
print("GAME 1 RECONSTRUCTION")
print("=" * 70)

board1 = reconstruct_game(game1_moves)
print("\nFinal Board State:")
print_board(board1)

print("\n\nColumn Control (topmost color and z-level):")
control1 = analyze_column_control(board1)
print_column_control(control1)

print("\nTop Layer (z=3):")
print_top_layer(board1)

print("\nCorner Analysis:")
analyze_corners(board1)

w1, b1, details1 = compute_score(board1)
print(f"\nSCORE: White={w1}, Black={b1}")
print("\nFace breakdown:")
for face, counts in details1.items():
    print(f"  {face}: W={counts['W']}, B={counts['B']}, R={counts['R']}, empty={counts['empty']}")

print("\nBlock usage:")
wb1, bb1 = count_blocks_by_player(game1_moves)
print(f"  White: {wb1}")
print(f"  Black: {bb1}")

print("\n" + "=" * 70)
print("GAME 2 RECONSTRUCTION")
print("=" * 70)

board2 = reconstruct_game(game2_moves)
print("\nFinal Board State:")
print_board(board2)

print("\n\nColumn Control (topmost color and z-level):")
control2 = analyze_column_control(board2)
print_column_control(control2)

print("\nTop Layer (z=3):")
print_top_layer(board2)

print("\nCorner Analysis:")
analyze_corners(board2)

w2, b2, details2 = compute_score(board2)
print(f"\nSCORE: White={w2}, Black={b2}")
print("\nFace breakdown:")
for face, counts in details2.items():
    print(f"  {face}: W={counts['W']}, B={counts['B']}, R={counts['R']}, empty={counts['empty']}")

print("\nBlock usage:")
wb2, bb2 = count_blocks_by_player(game2_moves)
print(f"  White: {wb2}")
print(f"  Black: {bb2}")

# Now let's trace move-by-move for Game 1 to check gravity/stacking
print("\n" + "=" * 70)
print("GAME 1 MOVE-BY-MOVE TRACE")
print("=" * 70)

board_trace = [[[None for z in range(4)] for y in range(4)] for x in range(4)]

for move_num, (player, block_type, pos, orient, flip) in enumerate(game1_moves, 1):
    x, y, z = pos
    c1, c2 = get_block_colors(block_type, flip)

    if orient == 'Z':
        col_height = 0
        for zz in range(4):
            if board_trace[x][y][zz] is not None:
                col_height = zz + 1
            else:
                break
        actual_z = col_height
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x},{y},{actual_z+1})")
        board_trace[x][y][actual_z] = c1
        board_trace[x][y][actual_z + 1] = c2
    elif orient == 'X':
        h1 = 0
        for zz in range(4):
            if board_trace[x][y][zz] is not None:
                h1 = zz + 1
            else:
                break
        h2 = 0
        for zz in range(4):
            if board_trace[x+1][y][zz] is not None:
                h2 = zz + 1
            else:
                break
        actual_z = max(h1, h2)
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x+1},{y},{actual_z})")
        board_trace[x][y][actual_z] = c1
        board_trace[x+1][y][actual_z] = c2
    elif orient == 'Y':
        h1 = 0
        for zz in range(4):
            if board_trace[x][y][zz] is not None:
                h1 = zz + 1
            else:
                break
        h2 = 0
        for zz in range(4):
            if board_trace[x][y+1][zz] is not None:
                h2 = zz + 1
            else:
                break
        actual_z = max(h1, h2)
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x},{y+1},{actual_z})")
        board_trace[x][y][actual_z] = c1
        board_trace[x][y+1][actual_z] = c2


print("\n" + "=" * 70)
print("GAME 2 MOVE-BY-MOVE TRACE")
print("=" * 70)

board_trace2 = [[[None for z in range(4)] for y in range(4)] for x in range(4)]

for move_num, (player, block_type, pos, orient, flip) in enumerate(game2_moves, 1):
    x, y, z = pos
    c1, c2 = get_block_colors(block_type, flip)

    if orient == 'Z':
        col_height = 0
        for zz in range(4):
            if board_trace2[x][y][zz] is not None:
                col_height = zz + 1
            else:
                break
        actual_z = col_height
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x},{y},{actual_z+1})")
        board_trace2[x][y][actual_z] = c1
        board_trace2[x][y][actual_z + 1] = c2
    elif orient == 'X':
        h1 = 0
        for zz in range(4):
            if board_trace2[x][y][zz] is not None:
                h1 = zz + 1
            else:
                break
        h2 = 0
        for zz in range(4):
            if board_trace2[x+1][y][zz] is not None:
                h2 = zz + 1
            else:
                break
        actual_z = max(h1, h2)
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x+1},{y},{actual_z})")
        board_trace2[x][y][actual_z] = c1
        board_trace2[x+1][y][actual_z] = c2
    elif orient == 'Y':
        h1 = 0
        for zz in range(4):
            if board_trace2[x][y][zz] is not None:
                h1 = zz + 1
            else:
                break
        h2 = 0
        for zz in range(4):
            if board_trace2[x][y+1][zz] is not None:
                h2 = zz + 1
            else:
                break
        actual_z = max(h1, h2)
        print(f"  Move {move_num:2d}: {player:5s} {block_type} ({x},{y},{z}) {orient} flip={flip} -> {c1}@({x},{y},{actual_z}) {c2}@({x},{y+1},{actual_z})")
        board_trace2[x][y][actual_z] = c1
        board_trace2[x][y+1][actual_z] = c2

# Multi-face analysis
print("\n" + "=" * 70)
print("MULTI-FACE CELL ANALYSIS (cells appearing on multiple faces)")
print("=" * 70)

def analyze_multi_face_cells(board, game_name):
    """Identify cells that appear on multiple scoring faces."""
    print(f"\n{game_name}:")

    for x in range(4):
        for y in range(4):
            for z in range(4):
                faces = []
                if z == 3: faces.append('top')
                if y == 0: faces.append('front')
                if y == 3: faces.append('back')
                if x == 0: faces.append('left')
                if x == 3: faces.append('right')

                if len(faces) >= 2 and board[x][y][z] is not None:
                    color = board[x][y][z]
                    pts = len(faces)
                    if color in ('W', 'B'):
                        print(f"  ({x},{y},{z}): {color} on {len(faces)} faces ({', '.join(faces)}) = {pts} pts for {'White' if color == 'W' else 'Black'}")

analyze_multi_face_cells(board1, "Game 1")
analyze_multi_face_cells(board2, "Game 2")

# Edge scoring summary
print("\n" + "=" * 70)
print("EDGE/CORNER SCORING SUMMARY")
print("=" * 70)

def edge_corner_summary(board, game_name):
    w_multi = 0
    b_multi = 0
    w_corner3 = 0
    b_corner3 = 0
    for x in range(4):
        for y in range(4):
            for z in range(4):
                faces = 0
                if z == 3: faces += 1
                if y == 0: faces += 1
                if y == 3: faces += 1
                if x == 0: faces += 1
                if x == 3: faces += 1

                if faces >= 2 and board[x][y][z] is not None:
                    color = board[x][y][z]
                    if color == 'W':
                        w_multi += faces
                        if faces == 3:
                            w_corner3 += 1
                    elif color == 'B':
                        b_multi += faces
                        if faces == 3:
                            b_corner3 += 1

    print(f"\n{game_name}:")
    print(f"  White multi-face points: {w_multi} (3-face corners: {w_corner3})")
    print(f"  Black multi-face points: {b_multi} (3-face corners: {b_corner3})")

edge_corner_summary(board1, "Game 1")
edge_corner_summary(board2, "Game 2")
