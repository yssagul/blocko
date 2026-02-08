"""
Edge control strategy — prioritizes exterior-face visibility.

Scores each move by how many of the player's color cells land on scored
exterior faces (edges, corners, top).  No state copying; uses only the
block's occupied positions and a fast face count.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class EdgeControlStrategy(Strategy):
    """
    Prioritize placing own-color cells on edge and corner positions.

    Complexity: O(1) per candidate (no state copy).
    """

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
        bx_min, bx_max, by_min, by_max, _bz_min, bz_max = game_state.scoring_bounds()

        def score_position(pos):
            """Score based on how many exterior faces this position has."""
            x, y, z = pos
            score = 0
            if x == bx_min or x == bx_max: score += 1
            if y == by_min or y == by_max: score += 1
            if z == bz_max: score += 1  # Top (not bottom)
            return score

        best_score = float('-inf')
        best_moves = []

        for move in legal_moves:
            block, position, orientation, flip = move
            temp_block = PlacedBlock(block, position, orientation, flip)

            total_score = 0
            for pos in temp_block.get_occupied_positions():
                color = temp_block.get_color_at_position(pos)
                if color == my_color:
                    total_score += score_position(pos)

            if total_score > best_score:
                best_score = total_score
                best_moves = [move]
            elif total_score == best_score:
                best_moves.append(move)

        return random.choice(best_moves)
