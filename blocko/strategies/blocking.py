"""
Block-opponent strategy — 3-component evaluator with stacking awareness.

Combines three signals:
  1. **Actual score change** — simulates the move and measures real delta.
  2. **Blocking bonus** — rewards placements that prevent the opponent from
     stacking their own color above via the color-stacking rule.
  3. **Coverage penalty** — penalizes exposing own high-value cells for the
     opponent to cover.

Uses move sampling (MAX_CANDIDATES) and the shared ``exterior_faces()``
utility.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class BlockOpponentStrategy(Strategy):
    """
    3-component evaluator: score + stacking + coverage.

    Complexity: O(1) per candidate for components 2–3, but component 1
    requires a full state copy.
    """

    MAX_CANDIDATES = 100

    def choose_move(self, game_state: GameState, player: Player
                    ) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
        opponent_color = Color.BLACK if player == Player.WHITE else Color.WHITE

        # Current score before any move
        w_before, b_before = game_state.calculate_score()
        my_score_before = w_before if player == Player.WHITE else b_before
        opp_score_before = b_before if player == Player.WHITE else w_before

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = random.sample(legal_moves, self.MAX_CANDIDATES)

        best_score = float('-inf')
        best_moves = []

        for move in candidates:
            block, position, orientation, flip = move

            # === Component 1: Actual score change ===
            sim_state = game_state.copy()
            sim_state.make_move(*move)
            w_after, b_after = sim_state.calculate_score()
            my_score_after = w_after if player == Player.WHITE else b_after
            opp_score_after = b_after if player == Player.WHITE else w_after

            my_gain = my_score_after - my_score_before
            opp_gain = opp_score_after - opp_score_before
            score = (my_gain - opp_gain) * 3

            # === Component 2: Blocking bonus via stacking rule ===
            temp_block = PlacedBlock(block, position, orientation, flip)
            for pos in temp_block.get_occupied_positions():
                x, y, z = pos
                color = temp_block.get_color_at_position(pos)

                if color == opponent_color and z < 3:
                    above = (x, y, z + 1)
                    if above not in game_state.grid and above not in set(temp_block.get_occupied_positions()):
                        above_vis = exterior_faces(x, y, z + 1)
                        score += above_vis * 2

                elif color == my_color and z < 3:
                    above = (x, y, z + 1)
                    if above not in game_state.grid and above not in set(temp_block.get_occupied_positions()):
                        above_vis = exterior_faces(x, y, z + 1)
                        score -= above_vis * 1

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves)
