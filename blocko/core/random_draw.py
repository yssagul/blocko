"""
Random Draw game state variants for the Blocko engine.

In Random Draw mode each player must play a randomly drawn piece from the
pool.  If the drawn piece has no legal placement it is set aside and
another is drawn, repeating until a playable piece is found.  All
discarded pieces return to the draw pile before the next player's turn.

Two concrete classes are provided:

- :class:`RandomDrawGameState` — Standard 4×4×4 fixed-boundary grid.
- :class:`RandomDrawOpenGridGameState` — Open Grid with dynamic X/Y.

The game ends when no remaining piece has any legal move, or when all
pieces have been used — identical to the other modes.
"""

import random
from typing import List, Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState
from blocko.core.open_grid import OpenGridGameState


class RandomDrawMixin:
    """
    Mixin that adds random-draw piece selection to a GameState subclass.

    Manages a ``drawn_block`` that the current player must use, and a
    ``discarded`` pile of pieces that had no legal move this turn.

    Subclasses must call ``super().__init__()`` and provide the standard
    GameState interface (``remaining_blocks``, ``_has_legal_move_for_block``,
    ``make_move``, ``current_player``, etc.).
    """

    def _init_random_draw(self):
        self.drawn_block: Optional[Block] = None
        self.discarded: List[Block] = []

    # ── drawing ────────────────────────────────────────────────────────────

    def draw_piece(self) -> Optional[Block]:
        """
        Draw a random playable piece for the current player.

        Pieces that have no legal move are moved to ``self.discarded``.
        If no piece in the pool is playable, returns None (game over).
        Discarded pieces are NOT returned to the pool until the *next*
        call to :meth:`_return_discarded`.
        """
        self._return_discarded()

        while self.remaining_blocks:
            idx = random.randrange(len(self.remaining_blocks))
            block = self.remaining_blocks[idx]
            if self._has_legal_move_for_block(block):
                self.drawn_block = block
                return block
            # No legal move — discard
            self.remaining_blocks.pop(idx)
            self.discarded.append(block)

        # Nothing playable
        self.drawn_block = None
        return None

    def _return_discarded(self):
        """Return all discarded pieces back into the remaining pool."""
        if self.discarded:
            self.remaining_blocks.extend(self.discarded)
            self.discarded.clear()

    # ── move generation (only the drawn piece) ─────────────────────────────

    def get_legal_moves(self) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Return legal moves for only the currently drawn block."""
        if self.drawn_block is None:
            return []
        return self._legal_moves_for_block(self.drawn_block)

    # ── move execution ────────────────────────────────────────────────────

    def make_move(self, block: Block, position: Tuple[int, int, int],
                  orientation: str, flip: bool) -> bool:
        """Execute a move and clear the drawn block."""
        success = super().make_move(block, position, orientation, flip)
        if success:
            self.drawn_block = None
            # Return any discards so next player has the full pool
            self._return_discarded()
        return success

    # ── game-over detection ────────────────────────────────────────────────

    def is_game_over(self) -> bool:
        """
        The game is over when no remaining piece (including discarded
        ones) has any legal move, or when all pieces have been used.

        This checks the full pool (remaining + discarded) since discards
        are returned before each draw.
        """
        # Temporarily reunite discarded with remaining for the check
        full_pool = self.remaining_blocks + self.discarded
        if not full_pool:
            return True
        return self._no_legal_moves_for_pool(full_pool)


class RandomDrawGameState(RandomDrawMixin, GameState):
    """
    Random Draw variant on the standard 4×4×4 grid.

    Each turn, a piece is randomly drawn and the player must place it.
    Unplayable draws are discarded and redrawn until a playable piece
    is found or the game ends.
    """

    def __init__(self):
        super().__init__()
        self._init_random_draw()

    def _has_legal_move_for_block(self, block: Block) -> bool:
        """Check if *block* has at least one legal placement."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
        for x in range(4):
            for y in range(4):
                for z in range(z_limit):
                    for orientation in ['x', 'y', 'z']:
                        if self._is_legal_placement(block, (x, y, z), orientation, False):
                            return True
                        if self._is_legal_placement(block, (x, y, z), orientation, True):
                            return True
        return False

    def _legal_moves_for_block(self, block: Block
                               ) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Return all legal placements for a single block."""
        moves = []
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
        for x in range(4):
            for y in range(4):
                for z in range(z_limit):
                    for orientation in ['x', 'y', 'z']:
                        for flip in [False, True]:
                            if self._is_legal_placement(block, (x, y, z), orientation, flip):
                                moves.append((block, (x, y, z), orientation, flip))
        return moves

    def _no_legal_moves_for_pool(self, pool: List[Block]) -> bool:
        """Return True if no block in *pool* has a legal move."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
        seen_color_pairs: set = set()
        for block in pool:
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

    def copy(self) -> "RandomDrawGameState":
        """Create a deep copy of the random draw game state."""
        import copy
        new_state = RandomDrawGameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        new_state.drawn_block = self.drawn_block
        new_state.discarded = self.discarded.copy()
        return new_state


class RandomDrawOpenGridGameState(RandomDrawMixin, OpenGridGameState):
    """
    Random Draw variant on the Open Grid (dynamic X/Y boundaries).

    Combines RandomDraw piece selection with OpenGrid's floating
    coordinate system.
    """

    def __init__(self):
        super().__init__()
        self._init_random_draw()

    def _has_legal_move_for_block(self, block: Block) -> bool:
        """Check if *block* has at least one legal placement (Open Grid)."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
        if self._x_min is None:
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            x_range = range(self._x_max - 3, self._x_min + 4)
            y_range = range(self._y_max - 3, self._y_min + 4)
        for x in x_range:
            for y in y_range:
                for z in range(z_limit):
                    for orientation in ['x', 'y', 'z']:
                        if self._is_legal_placement(block, (x, y, z), orientation, False):
                            return True
                        if self._is_legal_placement(block, (x, y, z), orientation, True):
                            return True
        return False

    def _legal_moves_for_block(self, block: Block
                               ) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Return all legal placements for a single block (Open Grid)."""
        moves = []
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
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
        for x in x_range:
            for y in y_range:
                for z in range(z_limit):
                    for orientation in ['x', 'y', 'z']:
                        for flip in [False, True]:
                            if self._is_legal_placement(block, (x, y, z), orientation, flip):
                                moves.append((block, (x, y, z), orientation, flip))
        return moves

    def _no_legal_moves_for_pool(self, pool: List[Block]) -> bool:
        """Return True if no block in *pool* has a legal move (Open Grid)."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)
        if self._x_min is None:
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            x_range = range(self._x_max - 3, self._x_min + 4)
            y_range = range(self._y_max - 3, self._y_min + 4)
        seen_color_pairs: set = set()
        for block in pool:
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

    def copy(self) -> "RandomDrawOpenGridGameState":
        """Create a deep copy of the random draw open grid game state."""
        import copy
        new_state = RandomDrawOpenGridGameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        new_state._x_min = self._x_min
        new_state._x_max = self._x_max
        new_state._y_min = self._y_min
        new_state._y_max = self._y_max
        new_state.drawn_block = self.drawn_block
        new_state.discarded = self.discarded.copy()
        return new_state
