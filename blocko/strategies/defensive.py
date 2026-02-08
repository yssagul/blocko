"""
Defensive strategy — minimizes opponent scoring opportunities.

Simulates each candidate move and measures how many fewer legal moves the
opponent has afterward.  Picks the move that reduces opponent options the
most.  Uses move sampling (MAX_CANDIDATES) for performance.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class DefensiveStrategy(Strategy):
    """
    Choose the move that most reduces opponent move count.

    Complexity: O(n) with full state copy + move gen per candidate — slow.
    """

    MAX_CANDIDATES = 50

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        best_opponent_reduction = float('-inf')
        best_moves = []

        opponent_moves_before = len(legal_moves)

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = random.sample(legal_moves, self.MAX_CANDIDATES)

        for move in candidates:
            sim_state = game_state.copy()
            sim_state.make_move(*move)

            opponent_moves_after = len(sim_state.get_legal_moves())
            reduction = opponent_moves_before - opponent_moves_after

            if reduction > best_opponent_reduction:
                best_opponent_reduction = reduction
                best_moves = [move]
            elif reduction == best_opponent_reduction:
                best_moves.append(move)

        return random.choice(best_moves)
