"""
Mixed strategy — weighted random blend of other strategies.

On each turn a strategy is randomly selected (proportional to its weight)
and that strategy's :meth:`choose_move` is called.  This allows creating
ensembles that combine different play styles.
"""

import random
from typing import List, Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class MixedStrategy(Strategy):
    """
    Weighted random over a list of sub-strategies.

    Args:
        strategies: List of (strategy, weight) tuples.  Weights are
            automatically normalized so they need not sum to 1.
    """

    def __init__(self, strategies: List[Tuple[Strategy, float]]):
        self.strategies = strategies
        total_weight = sum(w for _, w in strategies)
        self.normalized_weights = [(s, w / total_weight) for s, w in strategies]

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        rand = random.random()
        cumulative = 0
        for strategy, weight in self.normalized_weights:
            cumulative += weight
            if rand < cumulative:
                return strategy.choose_move(game_state, player)

        # Fallback to last strategy
        return self.normalized_weights[-1][0].choose_move(game_state, player)
