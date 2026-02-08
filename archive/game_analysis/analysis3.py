#!/usr/bin/env python3
"""
Endgame analysis: the WR endgame trap and stacking constraint analysis.
"""

def get_block_colors(block_type, flip):
    c1, c2 = block_type[0], block_type[1]
    if flip:
        return c2, c1
    return c1, c2

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

# GAME 1 - Analyze the endgame (moves 25-32)
# After move 24, what does the board look like?
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
]

board1_m24 = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
for m in game1_moves[:24]:
    place_block(board1_m24, m[1], m[2], m[3], m[4])

print("GAME 1 - Board after move 24 (before endgame):")
for z in range(3, -1, -1):
    print(f"\n  Layer z={z}:")
    print(f"       x=0  x=1  x=2  x=3")
    for y in range(4):
        row = f"  y={y}  "
        for x in range(4):
            cell = board1_m24[x][y][z]
            if cell is None:
                row += " .   "
            else:
                row += f" {cell}   "
        print(row)

# Show column heights and top colors
print("\n  Column status after M24:")
for y in range(4):
    for x in range(4):
        height = 0
        top_color = None
        for z in range(4):
            if board1_m24[x][y][z] is not None:
                height = z + 1
                top_color = board1_m24[x][y][z]
        print(f"    ({x},{y}): height={height}, top={top_color}")

# Remaining empty columns after M24
print("\n  Empty/unfilled columns after M24:")
for y in range(4):
    for x in range(4):
        height = 0
        top_color = None
        for z in range(4):
            if board1_m24[x][y][z] is not None:
                height = z + 1
                top_color = board1_m24[x][y][z]
        if height < 4:
            print(f"    ({x},{y}): height={height}, top={top_color}, needs {4-height} more")

# Now analyze the stacking constraint for remaining columns
print("\n\n  STACKING CONSTRAINT ANALYSIS (Game 1 after M24):")
print("  What can go on top of each unfilled column?")
for y in range(4):
    for x in range(4):
        height = 0
        top_color = None
        for z in range(4):
            if board1_m24[x][y][z] is not None:
                height = z + 1
                top_color = board1_m24[x][y][z]
        if height < 4:
            if top_color is None:
                can_stack = "anything"
            elif top_color == 'R':
                can_stack = "anything (R is wild)"
            elif top_color == 'W':
                can_stack = "B or R only (not W)"
            elif top_color == 'B':
                can_stack = "W or R only (not B)"
            print(f"    ({x},{y}): top={top_color}, {can_stack}")

# Same for Game 2
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
]

board2_m24 = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
for m in game2_moves[:24]:
    place_block(board2_m24, m[1], m[2], m[3], m[4])

print("\n\nGAME 2 - Board after move 24:")
for z in range(3, -1, -1):
    print(f"\n  Layer z={z}:")
    print(f"       x=0  x=1  x=2  x=3")
    for y in range(4):
        row = f"  y={y}  "
        for x in range(4):
            cell = board2_m24[x][y][z]
            if cell is None:
                row += " .   "
            else:
                row += f" {cell}   "
        print(row)

print("\n  STACKING CONSTRAINT ANALYSIS (Game 2 after M24):")
for y in range(4):
    for x in range(4):
        height = 0
        top_color = None
        for z in range(4):
            if board2_m24[x][y][z] is not None:
                height = z + 1
                top_color = board2_m24[x][y][z]
        if height < 4:
            if top_color is None:
                can_stack = "anything"
            elif top_color == 'R':
                can_stack = "anything (R is wild)"
            elif top_color == 'W':
                can_stack = "B or R only (not W)"
            elif top_color == 'B':
                can_stack = "W or R only (not B)"
            print(f"    ({x},{y}): height={height}, top={top_color}, {can_stack}, is_edge={x==0 or x==3 or y==0 or y==3}")

# Analyze the "force WR" endgame
print("\n\n" + "=" * 70)
print("WR ENDGAME TRAP ANALYSIS")
print("=" * 70)

print("""
GAME 1 Endgame (M25-32):
  After M24, the remaining unfilled columns need blocks to reach z=3.
  Key insight: When columns have W on top at z=1, they need 2 more cells.
  BW with B on bottom, W on top works. But what about edge columns?

  M25: White BW Z at (1,3) -> B@z0, W@z1 (new column, back face)
  M26: Black BW Y at (1,1)/(1,2) z=3 -> B@(1,1,3), W@(1,2,3) (top face)
  M27: White BW Z at (2,3) -> B@z0, W@z1 (new column, back face)
  M28: Black BW Y at (2,1)/(2,2) z=3 -> B@(2,1,3), W@(2,2,3) (top face)
  M29: White WR Z at (1,3) -> R@z2, W@z3 (CLAIMING BACK EDGE + TOP!)
  M30: Black WR Z at (3,1) -> R@z2, W@z3 (forced to score White!)
  M31: White WR Z at (2,3) -> R@z2, W@z3 (CLAIMING ANOTHER EDGE!)
  M32: Black WR Z at (3,2) -> R@z2, W@z3 (forced to score White again!)

  The AI was FORCED to play WR blocks that scored for White because
  the remaining columns had top colors that constrained what could be placed.
""")

print("""
GAME 2 Endgame (M25-32):
  Similar pattern emerges. After M24:
  M25: White WR Z at (3,2) -> R@z2, W@z3 (right edge + top)
  M26: Black WR Z at (0,1) -> R@z0, W@z1 (left edge, low placement)
  M27: White WR Z at (3,1) -> R@z2, W@z3 (right edge + top)
  M28: Black WR Z at (0,2) -> R@z0, W@z1 (left edge, low placement)
  M29: White WR Y at (1,2)/(1,3) z=3 -> R@(1,2,3), W@(1,3,3) (top + back)
  M30: Black WR Z at (0,1) -> R@z2, W@z3 (LEFT EDGE - scoring White!)
  M31: White WR Z at (0,2) -> R@z2, W@z3 (left edge + top)
  M32: Black WR X at (1,0)/(2,0) z=3 -> R@(1,0,3), W@(2,0,3) (scoring White!)

  Again the AI is forced into WR plays that score for White.
""")

# Analyze how the human set up the BW buried-B strategy
print("=" * 70)
print("BURIED-B STRATEGY ANALYSIS")
print("=" * 70)

print("""
In both games, the human plays BW blocks vertically (Z orient, no flip):
  B goes to the lower z, W goes to the upper z.

Game 1 BW vertical plays by White:
  M21: BW Z no-flip at (3,2) -> B@z0, W@z1  (right+back edge!)
  M23: BW Z no-flip at (3,1) -> B@z0, W@z1  (right edge!)
  M25: BW Z no-flip at (1,3) -> B@z0, W@z1  (back edge)
  M27: BW Z no-flip at (2,3) -> B@z0, W@z1  (back edge)

  In every case, B is at z=0 (not scored, bottom is never a face!)
  and W is at z=1. The z=1 cell IS on side faces if at edge positions.
  Then later, WR with flip (R@z2, W@z3) goes on top, giving W at z=3 (top face).

  Net result: White gets z=1 AND z=3 in edge columns, Black gets nothing.
  The B at z=0 costs White nothing because bottom face is never scored.

Game 2 BW vertical plays by White:
  M19: BW Z no-flip at (3,1) -> B@z0, W@z1  (right edge)
  M21: BW Z no-flip at (3,2) -> B@z0, W@z1  (right edge)
  M23: BW Z no-flip at (2,0) -> B@z0, W@z1  (front edge)

  Same pattern: B buried at z=0 (unscored bottom), W at z=1 (side-face scoring).
""")

# Compute how many points the AI GAVE to White in each game
print("=" * 70)
print("AI SELF-DAMAGE ANALYSIS: Points scored FOR the opponent")
print("=" * 70)

def ai_self_damage(moves, game_name):
    print(f"\n{game_name}:")
    board = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
    prev_w, prev_b = 0, 0

    w_from_black_moves = 0  # White points gained when Black plays
    b_from_white_moves = 0  # Black points gained when White plays

    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        place_block(board, block_type, pos, orient, flip)
        w, b = 0, 0
        # recompute
        for x in range(4):
            for y in range(4):
                cell = board[x][y][3]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for x in range(4):
            for z in range(4):
                cell = board[x][0][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for x in range(4):
            for z in range(4):
                cell = board[x][3][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for yy in range(4):
            for z in range(4):
                cell = board[0][yy][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for yy in range(4):
            for z in range(4):
                cell = board[3][yy][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1

        dw = w - prev_w
        db = b - prev_b

        if player == 'Black' and dw > 0:
            w_from_black_moves += dw
            print(f"  M{move_num}: Black's {block_type} gave White +{dw} points")
        if player == 'White' and db > 0:
            b_from_white_moves += db
            print(f"  M{move_num}: White's {block_type} gave Black +{db} points")

        prev_w, prev_b = w, b

    print(f"\n  TOTALS:")
    print(f"    White points from Black's moves: {w_from_black_moves}")
    print(f"    Black points from White's moves: {b_from_white_moves}")
    print(f"    Net self-damage by Black: {w_from_black_moves - b_from_white_moves}")

ai_self_damage(game1_moves, "Game 1")
ai_self_damage(game2_moves, "Game 2")

# Game 1 margin progression
print("\n" + "=" * 70)
print("MARGIN PROGRESSION (White - Black)")
print("=" * 70)

def margin_progression(moves, game_name):
    print(f"\n{game_name}:")
    board = [[[None for z in range(4)] for y in range(4)] for x in range(4)]
    margins = []
    for move_num, (player, block_type, pos, orient, flip) in enumerate(moves, 1):
        place_block(board, block_type, pos, orient, flip)
        w, b = 0, 0
        for x in range(4):
            for y in range(4):
                cell = board[x][y][3]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for x in range(4):
            for z in range(4):
                cell = board[x][0][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for x in range(4):
            for z in range(4):
                cell = board[x][3][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for yy in range(4):
            for z in range(4):
                cell = board[0][yy][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        for yy in range(4):
            for z in range(4):
                cell = board[3][yy][z]
                if cell == 'W': w += 1
                elif cell == 'B': b += 1
        margins.append(w - b)

    # Print as a chart
    for i, m in enumerate(margins):
        bar = ""
        if m > 0:
            bar = " " * 15 + "|" + "#" * m
        elif m < 0:
            bar = " " * (15 + m) + "#" * (-m) + "|"
        else:
            bar = " " * 15 + "|"

        player = moves[i][0]
        print(f"  M{i+1:2d} {player[0]}: {bar} ({'+' if m >= 0 else ''}{m})")

margin_progression(game1_moves, "Game 1")
margin_progression(game2_moves, "Game 2")
