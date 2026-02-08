"""
Analytical strategy (AntiRandomStrategy) — 7-component O(1) evaluator.

Designed to crush :class:`~blocko.strategies.random.RandomStrategy`.
Every move is scored analytically without copying the game state, using
only the two cells the block would occupy and their exterior-face counts.

The 7 evaluation components:
  1. **Net score delta** — own exterior faces minus opponent exterior faces.
  2. **Top-layer permanence** — z=3 cells can never be covered.
  3. **Three-face corner premium** — the 4 most valuable cells on the board.
  4. **Interior waste penalty** — don't bury own color inside the cube.
  5. **Future enablement** — z=2 cells that support high-value z=3 placements.
  6. **Opponent top-layer penalty** — avoid gifting permanent opponent points.
  7. **Block-type efficiency** — save rare pure-color blocks for exteriors.

Uses biased 5-tier sampling so high-value block types are always evaluated.
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class AntiRandomStrategy(Strategy):
    """
    7-component analytical evaluator with biased sampling.

    Complexity: O(1) per candidate (no state copy).
    """

    MAX_CANDIDATES = 150

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        return exterior_faces(x, y, z)

    # ── 5-tier smart sampling ─────────────────────────────────────────────

    def _smart_sample(self, legal_moves: list, my_color: Color) -> list:
        """
        Biased sample that always includes every move using pure own-colour
        blocks and fills the remaining budget from lower tiers.

        Tier order (best → worst for the current player):
          1. Pure own colour  (WW for White, BB for Black)
          2. Own colour + red (WR / BR)
          3. Mixed BW
          4. Opponent + red   (BR / WR)
          5. Pure opponent    (BB for White, WW for Black)
        """
        tiers: list[list] = [[] for _ in range(5)]

        for move in legal_moves:
            block = move[0]
            c1, c2 = block.color1, block.color2
            colors = {c1, c2}

            if c1 == my_color and c2 == my_color:
                tiers[0].append(move)
            elif my_color in colors and Color.RED in colors:
                tiers[1].append(move)
            elif Color.BLACK in colors and Color.WHITE in colors:
                tiers[2].append(move)
            elif my_color not in colors and Color.RED in colors:
                tiers[3].append(move)
            else:
                tiers[4].append(move)

        result = list(tiers[0])
        remaining = self.MAX_CANDIDATES - len(result)

        for tier in tiers[1:]:
            if remaining <= 0:
                break
            if len(tier) <= remaining:
                result.extend(tier)
                remaining -= len(tier)
            else:
                result.extend(random.sample(tier, remaining))
                remaining = 0

        return result

    # ── 7-component evaluation ────────────────────────────────────────────

    def _evaluate_move(self, move, game_state: GameState,
                       my_color: Color, opp_color: Color) -> float:
        """
        Compute a composite score for *move* without copying or simulating
        the game state.  All 7 components are derived from the two cells
        that the block will occupy and their exterior-face counts.
        """
        block, position, orientation, flip = move
        temp_block = PlacedBlock(block, position, orientation, flip)
        positions = temp_block.get_occupied_positions()

        score = 0.0

        # Pre-compute per-cell info
        cell_info = []
        for pos in positions:
            color = temp_block.get_color_at_position(pos)
            faces = self._exterior_faces(*pos)
            cell_info.append((pos, color, faces))

        # --- Component 1: net score delta (weight 10) --------------------
        my_face_gain = 0
        opp_face_gain = 0
        for _pos, color, faces in cell_info:
            if color == my_color:
                my_face_gain += faces
            elif color == opp_color:
                opp_face_gain += faces
        score += (my_face_gain - opp_face_gain) * 10

        # --- Component 2: top-layer permanence bonus (weight 3/face) -----
        for pos, color, faces in cell_info:
            if color == my_color and pos[2] == 3:
                score += faces * 3

        # --- Component 3: three-face corner premium (weight 5) -----------
        for _pos, color, faces in cell_info:
            if color == my_color and faces == 3:
                score += 5

        # --- Component 4: interior waste penalty -------------------------
        for _pos, color, faces in cell_info:
            if faces == 0:
                if color == my_color:
                    score -= 3
                elif color == opp_color:
                    score += 1

        # --- Component 5: future enablement bonus (weight 2) -------------
        for pos, _color, _faces in cell_info:
            x, y, z = pos
            if z == 2:
                above = (x, y, 3)
                if above not in game_state.grid:
                    above_faces = self._exterior_faces(x, y, 3)
                    if above_faces >= 2:
                        score += 2

        # --- Component 6: opponent top-layer penalty (weight −2/face) ----
        for pos, color, faces in cell_info:
            if color == opp_color and pos[2] == 3:
                score -= faces * 2

        # --- Component 7: block-type efficiency --------------------------
        c1, c2 = block.color1, block.color2
        if c1 == my_color and c2 == my_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces >= 4:
                score += 4
            elif total_faces <= 1:
                score -= 5

        return score

    # ── main entry point ──────────────────────────────────────────────────

    def choose_move(self, game_state: GameState,
                    player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
        opp_color = Color.BLACK if player == Player.WHITE else Color.WHITE

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = self._smart_sample(legal_moves, my_color)

        best_score = float('-inf')
        best_moves: list = []

        for move in candidates:
            s = self._evaluate_move(move, game_state, my_color, opp_color)
            if s > best_score:
                best_score = s
                best_moves = [move]
            elif s == best_score:
                best_moves.append(move)

        return random.choice(best_moves)
