#!/usr/bin/env python3
"""
Deeper analysis: incremental scoring, turning points, and tactical patterns.
"""

def get_block_colors(block_type, flip):
    c1, c2 = block_type[0], block_type[1]
    if flip:
        return c2, c1
    return c1, c2

def compute_score(board):
    white_score = 0
    black_score = 0
    for x in range(4):
        for y in range(4):
            cell = board[x][y][3]
            if cell == 'W': white_score += 1
            elif cell == 'B': black_score += 1
    for x in range(4):
        for z in range(4):
            cell = board[x][0][z]
            if cell == 'W': white_score += 1
            elif cell == 'B': black_score += 1
    for x in range(4):
        for z in range(4):
            cell = board[x][3][z]
            if cell == 'W': white_score += 1
            elif cell == 'B': black_score += 1
    for y in range(4):
        for z in range(4):
            cell = board[0][y][z]
            if cell == 'W': white_score += 1
            elif cell == 'B': black_score += 1
    for y in range(4):
        for z in range(4):
            cell = board[3][y][z]
            if cell == 'W': white_score += 1
            elif cell == 'B': black_score += 1
    return white_score, black_score

def place_block(board, block_type, pos, orient, flip):
    x, y, z = pos
    c1, c2 = get_block_colors(block_type, flip)

    if orient == 'Z':
        col_height = 0
        for zz in range(4):
            if board[x][y][zz] is not None:
                col_height = zz + 1
            else:
                break
        board[x][y][col_height] = c1
        board[x][y][col_height + 1] = c2
        return [(x,y,col_height,c1), (x,y,col_height+1,c2)]
    elif orient == 'X':
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
        board[x][y][actual_z] = c1
        board[x+1][y][actual_z] = c2
        return [(x,y,actual_z,c1), (x+1,y,actual_z,c2)]
    elif orient == 'Y':
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
        board[x][y][actual_z] = c1
        board[x][y+1][actual_z] = c2
        return [(x,y,actual_z,c1), (x,y+1,actual_z,c2)]

import copy

def incremental_analysis(moves, game_name):
    print(f"\n{'='*70}")
    print(f"INCREMENTAL SCORING: {game_name}")
    print(f"{'='*70}")

    board = [[[None for z in range(4)] for y in range(4)] for x in range(4)]

    prev_w, prev_b = 0, 0

    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        placed = place_block(board, block_type, pos, orient, flip)
        w, b = compute_score(board)
        dw = w - prev_w
        db = b - prev_b
        net_change = (dw - db) if player == 'White' else (db - dw)

        cells_str = ", ".join([f"{c}@({x},{y},{z})" for x,y,z,c in placed])

        margin = w - b
        print(f"  M{move_num:2d} {player:5s} {block_type} {orient}: {cells_str}")
        print(f"       Score: W={w} B={b} (margin W+{margin if margin >= 0 else margin}) | Delta: W+{dw} B+{db} | {'GOOD' if net_change > 0 else 'BAD' if net_change < 0 else 'NEUTRAL'} move (net {'+' if net_change >= 0 else ''}{net_change} for {player})")

        prev_w, prev_b = w, b

    print(f"\n  FINAL: White={prev_w}, Black={prev_b}, Margin={prev_w - prev_b}")

# Game 1 moves
game1_moves = [
    ('White', 'BW', (1,2,0), 'X', False),
    ('Black', 'BB', (0,0,0), 'Z', False),
    ('White', 'WW', (0,0,2), 'Z', False),
    ('Black', 'BB', (3,3,0), 'Z', False),
    ('White', 'WW', (3,3,2), 'Z', False),
    ('Black', 'BB', (3,0,0), 'Z', True),
    ('White', 'WW', (3,0,2), 'Z', False),
    ('Black', 'BR', (0,3,0), 'Z', True),
    ('White', 'WR', (0,3,2), 'Z', True),
    ('Black', 'BR', (1,0,0), 'Z', True),
    ('White', 'WR', (1,0,2), 'Z', True),
    ('Black', 'BR', (0,1,0), 'Y', True),
    ('White', 'BR', (1,1,0), 'X', True),
    ('Black', 'BR', (0,1,1), 'Z', False),
    ('White', 'BR', (2,2,1), 'Z', True),
    ('Black', 'BR', (0,2,1), 'Z', True),
    ('White', 'WR', (0,1,3), 'Y', True),
    ('Black', 'BR', (2,0,0), 'Z', False),
    ('White', 'BR', (1,2,1), 'Z', True),
    ('Black', 'BW', (2,0,2), 'Z', True),
    ('White', 'BW', (3,2,0), 'Z', False),
    ('Black', 'WR', (1,1,1), 'Z', True),
    ('White', 'BW', (3,1,0), 'Z', False),
    ('Black', 'WR', (2,1,1), 'Z', True),
    ('White', 'BW', (1,3,0), 'Z', False),
    ('Black', 'BW', (1,1,3), 'Y', False),
    ('White', 'BW', (2,3,0), 'Z', False),
    ('Black', 'BW', (2,1,3), 'Y', False),
    ('White', 'WR', (1,3,2), 'Z', True),
    ('Black', 'WR', (3,1,2), 'Z', True),
    ('White', 'WR', (2,3,2), 'Z', True),
    ('Black', 'WR', (3,2,2), 'Z', True),
]

# Game 2 moves
game2_moves = [
    ('White', 'BB', (1,1,0), 'Z', False),
    ('Black', 'BB', (0,0,0), 'Z', True),
    ('White', 'BB', (2,1,0), 'Z', False),
    ('Black', 'BR', (0,0,2), 'Z', True),
    ('White', 'WW', (0,3,0), 'Z', False),
    ('Black', 'BR', (0,3,2), 'Z', True),
    ('White', 'WW', (3,3,0), 'Z', False),
    ('Black', 'BR', (3,3,2), 'Z', True),
    ('White', 'WW', (3,0,0), 'Z', False),
    ('Black', 'BR', (3,0,2), 'Z', True),
    ('White', 'BW', (2,2,0), 'Y', False),
    ('Black', 'BR', (1,1,2), 'Z', True),
    ('White', 'BW', (1,2,0), 'Y', False),
    ('Black', 'BW', (2,1,2), 'Z', True),
    ('White', 'BR', (1,2,1), 'Z', True),
    ('Black', 'BR', (1,3,1), 'Z', True),
    ('White', 'BR', (2,2,1), 'Z', True),
    ('Black', 'BR', (2,3,1), 'Z', False),
    ('White', 'BW', (3,1,0), 'Z', False),
    ('Black', 'BW', (2,2,3), 'Y', True),
    ('White', 'BW', (3,2,0), 'Z', False),
    ('Black', 'BW', (1,0,0), 'Z', True),
    ('White', 'BW', (2,0,0), 'Z', False),
    ('Black', 'WR', (1,0,2), 'X', False),
    ('White', 'WR', (3,2,2), 'Z', True),
    ('Black', 'WR', (0,1,0), 'Z', True),
    ('White', 'WR', (3,1,2), 'Z', True),
    ('Black', 'WR', (0,2,0), 'Z', True),
    ('White', 'WR', (1,2,3), 'Y', True),
    ('Black', 'WR', (0,1,2), 'Z', True),
    ('White', 'WR', (0,2,2), 'Z', True),
    ('Black', 'WR', (1,0,3), 'X', True),
]

incremental_analysis(game1_moves, "GAME 1")
incremental_analysis(game2_moves, "GAME 2")

# Analyze which cells are on side faces at z=0 and z=1 (buried but scoring)
print("\n" + "=" * 70)
print("BURIED SIDE-FACE SCORING ANALYSIS")
print("=" * 70)

def side_face_by_layer(board, game_name):
    print(f"\n{game_name}:")
    for z in range(4):
        w_side = 0
        b_side = 0
        r_side = 0
        # Front y=0
        for x in range(4):
            c = board[x][0][z]
            if c == 'W': w_side += 1
            elif c == 'B': b_side += 1
            elif c == 'R': r_side += 1
        # Back y=3
        for x in range(4):
            c = board[x][3][z]
            if c == 'W': w_side += 1
            elif c == 'B': b_side += 1
            elif c == 'R': r_side += 1
        # Left x=0
        for y in range(4):
            c = board[0][y][z]
            if c == 'W': w_side += 1
            elif c == 'B': b_side += 1
            elif c == 'R': r_side += 1
        # Right x=3
        for y in range(4):
            c = board[3][y][z]
            if c == 'W': w_side += 1
            elif c == 'B': b_side += 1
            elif c == 'R': r_side += 1
        print(f"  z={z}: W={w_side} B={b_side} R={r_side} (total side cells: {w_side+b_side+r_side})")

# Reconstruct final boards
board1 = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
for m in game1_moves:
    place_block(board1, m[1], m[2], m[3], m[4])

board2 = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
for m in game2_moves:
    place_block(board2, m[1], m[2], m[3], m[4])

side_face_by_layer(board1, "Game 1")
side_face_by_layer(board2, "Game 2")

# Analyze the "White played opponent's blocks" strategy
print("\n" + "=" * 70)
print("OPPONENT-COLOR BLOCK USAGE ANALYSIS")
print("=" * 70)

def opponent_block_analysis(moves, game_name):
    print(f"\n{game_name}:")
    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        c1, c2 = get_block_colors(block_type, flip)

        if player == 'White':
            # White wants W cells on exterior, B cells buried
            if 'B' in block_type:
                if block_type == 'BB':
                    print(f"  M{move_num}: White plays BB -- placing BLACK blocks (sacrifice/denial)")
                elif block_type == 'BW' or block_type == 'BR':
                    # Check where each cell lands
                    pass
        else:
            if 'W' in block_type and block_type != 'WW':
                if block_type == 'WR' or block_type == 'BW':
                    pass

# Phase analysis
print("\n" + "=" * 70)
print("GAME PHASE ANALYSIS")
print("=" * 70)

def phase_analysis(moves, game_name):
    print(f"\n{game_name}:")
    board = [[[None for z in range(4)] for y in range(4)] for x in range(4)]

    # Track which columns are being filled
    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        placed = place_block(board, block_type, pos, orient, flip)

        # Count filled columns
        cols_full = 0
        cols_partial = 0
        cols_empty = 0
        for x in range(4):
            for y in range(4):
                height = 0
                for z in range(4):
                    if board[x][y][z] is not None:
                        height = z + 1
                if height == 0:
                    cols_empty += 1
                elif height == 4:
                    cols_full += 1
                else:
                    cols_partial += 1

        if move_num <= 4 or move_num in [8, 12, 16, 20, 24, 28, 32]:
            print(f"  After M{move_num:2d}: full={cols_full:2d} partial={cols_partial:2d} empty={cols_empty:2d}")

phase_analysis(game1_moves, "Game 1")
phase_analysis(game2_moves, "Game 2")

# Z-orientation vs horizontal analysis
print("\n" + "=" * 70)
print("ORIENTATION USAGE BY PLAYER")
print("=" * 70)

def orient_analysis(moves, game_name):
    print(f"\n{game_name}:")
    w_orient = {'X': 0, 'Y': 0, 'Z': 0}
    b_orient = {'X': 0, 'Y': 0, 'Z': 0}
    for _, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        if player == 'White':
            w_orient[orient] += 1
        else:
            b_orient[orient] += 1
    print(f"  White: X={w_orient['X']} Y={w_orient['Y']} Z={w_orient['Z']}")
    print(f"  Black: X={b_orient['X']} Y={b_orient['Y']} Z={b_orient['Z']}")

orient_analysis(game1_moves, "Game 1")
orient_analysis(game2_moves, "Game 2")

# Count exterior vs interior cells per player
print("\n" + "=" * 70)
print("EXTERIOR vs INTERIOR CELL PLACEMENT")
print("=" * 70)

def exterior_interior(board, game_name):
    w_ext = 0
    w_int = 0
    b_ext = 0
    b_int = 0
    r_ext = 0
    r_int = 0

    for x in range(4):
        for y in range(4):
            for z in range(4):
                c = board[x][y][z]
                if c is None:
                    continue
                is_ext = (z == 3 or y == 0 or y == 3 or x == 0 or x == 3)
                if c == 'W':
                    if is_ext: w_ext += 1
                    else: w_int += 1
                elif c == 'B':
                    if is_ext: b_ext += 1
                    else: b_int += 1
                elif c == 'R':
                    if is_ext: r_ext += 1
                    else: r_int += 1

    print(f"\n{game_name}:")
    print(f"  White cells: {w_ext} exterior, {w_int} interior (total {w_ext+w_int})")
    print(f"  Black cells: {b_ext} exterior, {b_int} interior (total {b_ext+b_int})")
    print(f"  Red cells:   {r_ext} exterior, {r_int} interior (total {r_ext+r_int})")

    # Note: a cell can be on multiple faces
    # Let's also count total scoring points per cell color
    w_pts = 0
    b_pts = 0
    for x in range(4):
        for y in range(4):
            for z in range(4):
                c = board[x][y][z]
                if c is None: continue
                faces = 0
                if z == 3: faces += 1
                if y == 0: faces += 1
                if y == 3: faces += 1
                if x == 0: faces += 1
                if x == 3: faces += 1
                if c == 'W': w_pts += faces
                elif c == 'B': b_pts += faces
    print(f"  White scoring points: {w_pts}")
    print(f"  Black scoring points: {b_pts}")

exterior_interior(board1, "Game 1")
exterior_interior(board2, "Game 2")

# Total cells by color
print("\n" + "=" * 70)
print("TOTAL CELLS BY COLOR")
print("=" * 70)

for board, name in [(board1, "Game 1"), (board2, "Game 2")]:
    w = b = r = 0
    for x in range(4):
        for y in range(4):
            for z in range(4):
                c = board[x][y][z]
                if c == 'W': w += 1
                elif c == 'B': b += 1
                elif c == 'R': r += 1
    print(f"  {name}: W={w} B={b} R={r} total={w+b+r}")
