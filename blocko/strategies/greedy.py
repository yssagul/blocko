"""
Greedy strategy — maximizes immediate score delta.

Simulates each candidate move on a state copy and picks the one that
produces the largest score improvement for the current player.  Uses
move sampling (MAX_CANDIDATES) to keep evaluation tractable.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Player
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class GreedyStrategy(Strategy):
    """
    Choose the move that maximizes immediate point gain.

    Complexity: O(n) with full state copy per candidate.
    """

    MAX_CANDIDATES = 100

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        best_score_diff = float('-inf')
        best_moves = []

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = random.sample(legal_moves, self.MAX_CANDIDATES)

        for move in candidates:
            sim_state = game_state.copy()
            sim_state.make_move(*move)

            white_score, black_score = sim_state.calculate_score()
            score_diff = white_score - black_score if player == Player.WHITE else black_score - white_score

            if score_diff > best_score_diff:
                best_score_diff = score_diff
                best_moves = [move]
            elif score_diff == best_score_diff:
                best_moves.append(move)

        return random.choice(best_moves)
