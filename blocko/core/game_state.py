"""
Standard 4×4×4 game state for the Blocko engine.

Manages the fixed-boundary grid (coordinates 0–3 on every axis), block pool,
turn order, move generation, legality checking, scoring, and state copying.

The standard game state is the default mode: all coordinates are bounded to
[0, 3] and scoring uses the 5 exterior faces of the resulting 4×4×4 cube.
"""

import copy
import random
from typing import List, Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces


class GameState:
    """
    Complete state of a standard 4×4×4 Blocko game.

    Attributes:
        grid: Mapping of (x, y, z) → PlacedBlock for every occupied cell.
        remaining_blocks: Pool of unplayed blocks.
        current_player: Whose turn it is (WHITE goes first).
        move_history: Ordered list of (player, placed_block) tuples.
    """

    def __init__(self):
        self.grid: dict[tuple, PlacedBlock] = {}
        self.remaining_blocks: List[Block] = self._initialize_blocks()
        self.current_player: Player = Player.WHITE
        self.move_history: list = []

    # ── block pool ────────────────────────────────────────────────────────

    def _initialize_blocks(self) -> List[Block]:
        """Create the standard pool of 32 blocks."""
        blocks = []
        block_id = 0

        # 3 all-black (BB)
        for _ in range(3):
            blocks.append(Block(Color.BLACK, Color.BLACK, block_id))
            block_id += 1

        # 3 all-white (WW)
        for _ in range(3):
            blocks.append(Block(Color.WHITE, Color.WHITE, block_id))
            block_id += 1

        # 8 half-black/half-white (BW)
        for _ in range(8):
            blocks.append(Block(Color.BLACK, Color.WHITE, block_id))
            block_id += 1

        # 9 half-black/half-red (BR)
        for _ in range(9):
            blocks.append(Block(Color.BLACK, Color.RED, block_id))
            block_id += 1

        # 9 half-white/half-red (WR)
        for _ in range(9):
            blocks.append(Block(Color.WHITE, Color.RED, block_id))
            block_id += 1

        return blocks

    # ── helpers ────────────────────────────────────────────────────────────

    def _get_max_z(self) -> int:
        """Return the highest occupied z-level, or -1 if the grid is empty."""
        if not self.grid:
            return -1
        return max(z for _, _, z in self.grid)

    # ── move generation ───────────────────────────────────────────────────

    def get_legal_moves(self) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """
        Return all legal moves as (block, position, orientation, flip) tuples.

        Blocks with identical color pairs are deduplicated so that the
        expensive legality check runs only once per unique color pair.
        """
        legal_moves = []

        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        # Deduplicate blocks by color pair
        seen_color_pairs: set = set()
        unique_blocks: list = []
        duplicate_blocks: list = []
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key not in seen_color_pairs:
                seen_color_pairs.add(key)
                unique_blocks.append(block)
            else:
                duplicate_blocks.append(block)

        for block in unique_blocks:
            for x in range(4):
                for y in range(4):
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            for flip in [False, True]:
                                if self._is_legal_placement(block, (x, y, z), orientation, flip):
                                    legal_moves.append((block, (x, y, z), orientation, flip))

        # Copy legal placements for duplicate blocks
        for block in duplicate_blocks:
            key = (block.color1, block.color2)
            for rep_block in unique_blocks:
                if (rep_block.color1, rep_block.color2) == key:
                    for move in legal_moves:
                        if move[0] is rep_block:
                            legal_moves.append((block, move[1], move[2], move[3]))
                    break

        return legal_moves

    # ── legality ──────────────────────────────────────────────────────────

    def _is_legal_placement(self, block: Block, position: Tuple[int, int, int],
                            orientation: str, flip: bool) -> bool:
        """
        Check whether a placement is legal under all game rules:
          1. Both cells within bounds (0–3 on each axis).
          2. Neither cell already occupied.
          3. Both cells gravity-supported (z=0 or cell below occupied/self-support).
          4. No same non-red color stacking (white-on-white / black-on-black).
        """
        x, y, z = position

        temp_block = PlacedBlock(block, position, orientation, flip)
        occupied_positions = temp_block.get_occupied_positions()
        occupied_set = set(occupied_positions)

        # Rule 1 — bounds
        for px, py, pz in occupied_positions:
            if not (0 <= px < 4 and 0 <= py < 4 and 0 <= pz < 4):
                return False

        # Rule 2 — no overlap
        for pos in occupied_positions:
            if pos in self.grid:
                return False

        # Rule 3 — gravity support
        for px, py, pz in occupied_positions:
            if pz == 0:
                continue
            below = (px, py, pz - 1)
            if below not in self.grid and below not in occupied_set:
                return False

        # Rule 4 — color stacking constraint
        for px, py, pz in occupied_positions:
            if pz > 0:
                below_pos = (px, py, pz - 1)
                if below_pos in self.grid:
                    color_above = temp_block.get_color_at_position((px, py, pz))
                    color_below = self.grid[below_pos].get_color_at_position(below_pos)
                    if color_above == Color.RED:
                        continue
                    if color_above == color_below and color_above != Color.RED:
                        return False

        return True

    # ── move execution ────────────────────────────────────────────────────

    def make_move(self, block: Block, position: Tuple[int, int, int],
                  orientation: str, flip: bool) -> bool:
        """
        Execute a move. Returns True if successful, False if illegal.

        Side-effects on success:
          - Both cells added to ``self.grid``.
          - Block removed from ``self.remaining_blocks``.
          - Move appended to ``self.move_history``.
          - ``self.current_player`` toggled.
        """
        if not self._is_legal_placement(block, position, orientation, flip):
            return False

        placed_block = PlacedBlock(block, position, orientation, flip)
        for pos in placed_block.get_occupied_positions():
            self.grid[pos] = placed_block

        self.remaining_blocks.remove(block)
        self.move_history.append((self.current_player, placed_block))
        self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE

        return True

    # ── scoring ───────────────────────────────────────────────────────────

    def calculate_score(self) -> Tuple[int, int]:
        """
        Calculate final scores for both players.

        Returns:
            (white_score, black_score) — each cell on the 5 exterior faces
            (top, front, back, left, right) contributes 1 point to its
            color's player.  The bottom face is not scored.
        """
        white_score = 0
        black_score = 0

        # Top face (z=3)
        for x in range(4):
            for y in range(4):
                pos = (x, y, 3)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Front face (y=0)
        for x in range(4):
            for z in range(4):
                pos = (x, 0, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Back face (y=3)
        for x in range(4):
            for z in range(4):
                pos = (x, 3, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Left face (x=0)
        for y in range(4):
            for z in range(4):
                pos = (0, y, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Right face (x=3)
        for y in range(4):
            for z in range(4):
                pos = (3, y, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        return white_score, black_score

    # ── game-over detection ───────────────────────────────────────────────

    def is_game_over(self) -> bool:
        """Return True if no legal moves remain for any remaining block."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        seen_color_pairs: set = set()
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key in seen_color_pairs:
                continue
            seen_color_pairs.add(key)
            for x in range(4):
                for y in range(4):
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            if self._is_legal_placement(block, (x, y, z), orientation, False):
                                return False
                            if self._is_legal_placement(block, (x, y, z), orientation, True):
                                return False
        return True

    # ── bounds / exterior faces ───────────────────────────────────────────

    def get_bounds(self) -> Tuple[int, int, int, int, int, int]:
        """Return (x_min, x_max, y_min, y_max, z_min, z_max) of the play area."""
        return (0, 3, 0, 3, 0, 3)

    def exterior_faces(self, x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        return exterior_faces(x, y, z, self.get_bounds())

    # ── copying ───────────────────────────────────────────────────────────

    def copy(self) -> "GameState":
        """Create a deep copy of the game state."""
        new_state = GameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        return new_state
