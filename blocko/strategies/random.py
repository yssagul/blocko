"""
Random strategy — selects uniformly at random from all legal moves.

This is the simplest possible strategy.  It serves as the baseline for
evaluating all other strategies and as a component in :class:`MixedStrategy`.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class RandomStrategy(Strategy):
    """Uniformly random move selection.  O(1) per candidate (after move gen)."""

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None
        return random.choice(legal_moves)
