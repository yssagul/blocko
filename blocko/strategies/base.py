"""
Abstract base class for all Blocko AI strategies.

Every strategy must implement :meth:`choose_move`, which receives the
current game state and the player to move, and returns a legal move tuple
or ``None`` if no move is possible.
"""

from typing import Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState


class Strategy:
    """
    Base class for AI strategies.

    Subclasses must override :meth:`choose_move` to implement their
    move-selection logic.
    """

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """
        Choose a move given the current game state.

        Args:
            game_state: The current board state.
            player: The player whose turn it is.

        Returns:
            A (block, position, orientation, flip) tuple, or None if no
            legal move exists.
        """
        raise NotImplementedError
