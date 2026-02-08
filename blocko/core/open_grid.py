"""
Open Grid game state variant for the Blocko engine.

In Open Grid mode the X and Y boundaries float dynamically: the first piece
is placed at (0, 0, 0) and subsequent pieces can extend in ±X / ±Y as long
as each axis span never exceeds 4 cells.  Z remains fixed at 0–3.  Each
axis locks independently once its span reaches 4.

This module subclasses :class:`~blocko.core.game_state.GameState` and
overrides move generation, legality, scoring, and bounds computation to
support the dynamic coordinate system.
"""

import copy
from typing import List, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player
from blocko.core.game_state import GameState


class OpenGridGameState(GameState):
    """
    Open Grid variant of the Blocko game state.

    Tracks per-axis occupied min/max and computes dynamic bounds.
    Scoring uses the tightest 4-wide bounding box that contains all pieces.
    """

    def __init__(self):
        super().__init__()
        self._x_min: int | None = None
        self._x_max: int | None = None
        self._y_min: int | None = None
        self._y_max: int | None = None

    # ── dynamic bounds ────────────────────────────────────────────────────

    def get_bounds(self) -> Tuple[int, int, int, int, int, int]:
        """
        Return the *possible* placement bounding box.

        If an axis is locked (span = 4 cells) the bounds are exact.
        If still floating, returns the widest range that keeps the axis
        within 4 cells.  For the scoring box see :meth:`_scoring_bounds`.
        """
        if self._x_min is None:
            return (0, 3, 0, 3, 0, 3)

        x_span = self._x_max - self._x_min
        if x_span >= 3:
            bx_min, bx_max = self._x_min, self._x_min + 3
        else:
            bx_min = self._x_max - 3
            bx_max = self._x_min + 3

        y_span = self._y_max - self._y_min
        if y_span >= 3:
            by_min, by_max = self._y_min, self._y_min + 3
        else:
            by_min = self._y_max - 3
            by_max = self._y_min + 3

        return (bx_min, bx_max, by_min, by_max, 0, 3)

    def _scoring_bounds(self) -> Tuple[int, int, int, int, int, int]:
        """
        Return the 4-wide bounding box used for scoring.

        If an axis is locked the scoring box equals the placement box.
        If floating, the occupied min anchors the box origin, extending +3.
        """
        if self._x_min is None:
            return (0, 3, 0, 3, 0, 3)
        return (self._x_min, self._x_min + 3,
                self._y_min, self._y_min + 3,
                0, 3)

    def scoring_bounds(self) -> Tuple[int, int, int, int, int, int]:
        """Return the scoring bounding box (tight 4-wide box at occupied min)."""
        return self._scoring_bounds()

    def _update_occupied_range(self, positions: list) -> None:
        """Update per-axis min/max tracking after placing cells."""
        for px, py, _pz in positions:
            if self._x_min is None:
                self._x_min = self._x_max = px
                self._y_min = self._y_max = py
            else:
                self._x_min = min(self._x_min, px)
                self._x_max = max(self._x_max, px)
                self._y_min = min(self._y_min, py)
                self._y_max = max(self._y_max, py)

    # ── legality ──────────────────────────────────────────────────────────

    def _is_legal_placement(self, block: Block, position: Tuple[int, int, int],
                            orientation: str, flip: bool) -> bool:
        """
        Check if a placement is legal in Open Grid mode.

        Differs from standard mode:
          - X/Y are not bounded to [0, 3]; instead each axis span must stay ≤ 4.
          - Z is still fixed to [0, 3].
        """
        x, y, z = position

        temp_block = PlacedBlock(block, position, orientation, flip)
        occupied_positions = temp_block.get_occupied_positions()
        occupied_set = set(occupied_positions)

        # Z bounds (always fixed 0–3)
        for px, py, pz in occupied_positions:
            if not (0 <= pz < 4):
                return False

        # X/Y span constraint
        if self._x_min is not None:
            for px, py, pz in occupied_positions:
                new_x_min = min(self._x_min, px)
                new_x_max = max(self._x_max, px)
                if new_x_max - new_x_min > 3:
                    return False
                new_y_min = min(self._y_min, py)
                new_y_max = max(self._y_max, py)
                if new_y_max - new_y_min > 3:
                    return False

        # No overlap
        for pos in occupied_positions:
            if pos in self.grid:
                return False

        # Gravity support
        for px, py, pz in occupied_positions:
            if pz == 0:
                continue
            below = (px, py, pz - 1)
            if below not in self.grid and below not in occupied_set:
                return False

        # Color stacking constraint
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
        """Execute a move and update the occupied range."""
        if not self._is_legal_placement(block, position, orientation, flip):
            return False

        placed_block = PlacedBlock(block, position, orientation, flip)
        positions = placed_block.get_occupied_positions()
        for pos in positions:
            self.grid[pos] = placed_block

        self.remaining_blocks.remove(block)
        self.move_history.append((self.current_player, placed_block))
        self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE

        self._update_occupied_range(positions)
        return True

    # ── move generation ───────────────────────────────────────────────────

    def get_legal_moves(self) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Legal moves with dynamic X/Y coordinate ranges."""
        legal_moves = []
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        # Determine X/Y scan range
        if self._x_min is None:
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            x_lo = self._x_max - 3
            x_hi = self._x_min + 3
            x_range = range(x_lo, x_hi + 1)
            y_lo = self._y_max - 3
            y_hi = self._y_min + 3
            y_range = range(y_lo, y_hi + 1)

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
            for x in x_range:
                for y in y_range:
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

    # ── game-over detection ───────────────────────────────────────────────

    def is_game_over(self) -> bool:
        """Check if the game is over with dynamic coordinate ranges."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        if self._x_min is None:
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            x_range = range(self._x_max - 3, self._x_min + 4)
            y_range = range(self._y_max - 3, self._y_min + 4)

        seen_color_pairs: set = set()
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key in seen_color_pairs:
                continue
            seen_color_pairs.add(key)
            for x in x_range:
                for y in y_range:
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            if self._is_legal_placement(block, (x, y, z), orientation, False):
                                return False
                            if self._is_legal_placement(block, (x, y, z), orientation, True):
                                return False
        return True

    # ── scoring ───────────────────────────────────────────────────────────

    def calculate_score(self) -> Tuple[int, int]:
        """
        Calculate scores using the scoring bounding box.

        The scoring box is the tightest 4-wide box anchored at the occupied
        min on each axis.
        """
        white_score = 0
        black_score = 0

        bx_min, bx_max, by_min, by_max, bz_min, bz_max = self._scoring_bounds()

        def _count(pos):
            nonlocal white_score, black_score
            if pos in self.grid:
                color = self.grid[pos].get_color_at_position(pos)
                if color == Color.WHITE:
                    white_score += 1
                elif color == Color.BLACK:
                    black_score += 1

        # Top face (z = bz_max = 3)
        for x in range(bx_min, bx_max + 1):
            for y in range(by_min, by_max + 1):
                _count((x, y, bz_max))

        # Front face (y = by_min)
        for x in range(bx_min, bx_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((x, by_min, z))

        # Back face (y = by_max)
        for x in range(bx_min, bx_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((x, by_max, z))

        # Left face (x = bx_min)
        for y in range(by_min, by_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((bx_min, y, z))

        # Right face (x = bx_max)
        for y in range(by_min, by_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((bx_max, y, z))

        return white_score, black_score

    # ── copying ───────────────────────────────────────────────────────────

    def copy(self) -> "OpenGridGameState":
        """Create a deep copy of the open grid game state."""
        new_state = OpenGridGameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        new_state._x_min = self._x_min
        new_state._x_max = self._x_max
        new_state._y_min = self._y_min
        new_state._y_max = self._y_max
        return new_state
