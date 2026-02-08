"""
Defensive strategy — sabotage-oriented positional warfare.

Redesigned around four core principles:

**D1 — Interior burial (early game):**
Bury opponent-color cells in the 12 zero-face interior positions
(x∈{1,2}, y∈{1,2}, z∈{0,1,2}) where they score nothing.  The ideal
early-game move places opponent color at (1,1,0) or (2,2,0) — permanently
wasted.

**D2 — BW net-zero face neutralization:**
Use BW blocks to achieve ±0 score change on exterior faces: orient so the
opponent half lands on an exterior face and the own half lands interior,
effectively "spending" a face slot on a cancel.  Particularly strong when
placing BW vertically at z=2–3 edge columns (opponent at z=2 face, own
at z=3 face = net zero but opponent's z=2 face can be covered later).

**D3 — Opponent z=2 poisoning:**
Place opponent-color cells at z=2 on edge/corner columns.  The stacking
rule then *forbids* the opponent from placing their own color at z=3
directly above — denying them permanent top-layer points.  Meanwhile the
opponent's z=2 face can be covered by our own z=3 placement later.

**D4 — Constraint forcing (late game):**
When few blocks remain, evaluate whether a placement forces the opponent
into bad orientations on their next turn — e.g., their only remaining
blocks are BW and all good spots require same-color stacking, leaving
them with interior-only legal moves.

All evaluation is O(1) per candidate (no state copies).

Complexity: O(1) per candidate with biased sampling (MAX_CANDIDATES=150).
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class DefensiveStrategy(Strategy):
    """
    Sabotage-oriented strategy: bury, neutralize, poison, and constrain.

    Uses a multi-component O(1) analytical evaluator with phase-aware
    weighting (early game emphasizes burial; late game emphasizes
    constraint forcing).
    """

    MAX_CANDIDATES = 150
    LATE_GAME_THRESHOLD = 18  # blocks remaining

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        return exterior_faces(x, y, z)

    @staticmethod
    def _is_interior(x: int, y: int, z: int) -> bool:
        """True if the cell touches zero scored exterior faces."""
        return (1 <= x <= 2) and (1 <= y <= 2) and (z < 3)

    @staticmethod
    def _is_edge_column(x: int, y: int) -> bool:
        """True if (x,y) is on the perimeter of the 4×4 grid."""
        return x == 0 or x == 3 or y == 0 or y == 3

    @staticmethod
    def _is_corner_column(x: int, y: int) -> bool:
        """True if (x,y) is a corner of the 4×4 grid."""
        return (x in (0, 3)) and (y in (0, 3))

    # ── biased sampling ───────────────────────────────────────────────────

    def _smart_sample(self, legal_moves: list, my_color: Color,
                      opp_color: Color) -> list:
        """
        3-tier sampling biased toward the strategy's goals.

        Tier 0 (always kept): Moves that bury opponent color in interior
                              positions, or use BW blocks on edges.
        Tier 1: Moves using opponent-color blocks (BR/WR containing opp).
        Tier 2: Everything else.
        """
        tiers: list[list] = [[], [], []]

        for move in legal_moves:
            block = move[0]
            c1, c2 = block.color1, block.color2
            colors = {c1, c2}

            # Tier 0: high-value sabotage moves
            if opp_color in colors:
                # Check if any occupied cell buries opponent color interior
                temp = PlacedBlock(block, move[1], move[2], move[3])
                dominated = False
                for pos in temp.get_occupied_positions():
                    color = temp.get_color_at_position(pos)
                    if color == opp_color and self._is_interior(*pos):
                        dominated = True
                        break
                    # Also prioritize opponent color at z=2 on edge columns
                    if (color == opp_color and pos[2] == 2
                            and self._is_edge_column(pos[0], pos[1])):
                        dominated = True
                        break
                if dominated:
                    tiers[0].append(move)
                    continue

            # Tier 0 also: BW blocks on edge/corner columns (net-zero weapons)
            if colors == {Color.BLACK, Color.WHITE}:
                temp = PlacedBlock(block, move[1], move[2], move[3])
                positions = temp.get_occupied_positions()
                any_edge = any(self._is_edge_column(p[0], p[1])
                               for p in positions)
                if any_edge:
                    tiers[0].append(move)
                    continue

            # Tier 1: blocks containing opponent color (general sabotage)
            if opp_color in colors:
                tiers[1].append(move)
            else:
                tiers[2].append(move)

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

    # ── constraint scan ───────────────────────────────────────────────────

    def _count_opponent_forced_interior(self, game_state: GameState,
                                        opp_color: Color) -> int:
        """
        Count z=3 edge/corner cells where the opponent is *blocked* from
        placing their own color due to the stacking rule (their color is
        already at z=2 below).  Higher = more damage done.
        """
        count = 0
        for x in range(4):
            for y in range(4):
                if not self._is_edge_column(x, y):
                    continue
                z2_pos = (x, y, 2)
                z3_pos = (x, y, 3)
                if z2_pos in game_state.grid and z3_pos not in game_state.grid:
                    color_at_z2 = game_state.grid[z2_pos].get_color_at_position(z2_pos)
                    if color_at_z2 == opp_color:
                        count += 1
        return count

    # ── main evaluator ────────────────────────────────────────────────────

    def _evaluate_move(self, move, game_state: GameState,
                       my_color: Color, opp_color: Color,
                       blocks_remaining: int) -> float:
        """
        Score a candidate move using 8 sabotage-oriented components.
        All O(1) — no state copying.

        Components:
          D1  Interior burial bonus        — bury opponent color inside
          D2  BW net-zero face play        — cancel opponent faces with own
          D3  Opponent z=2 poisoning       — deny opponent z=3 above
          D4  Constraint forcing           — opponent color at z=2 edge blocks z=3
          D5  Own-color protection         — avoid wasting own color interior
          D6  Top-layer denial             — penalize gifting opponent z=3
          D7  Stacking trap setup          — own color at z=2 prevents opponent cover
          D8  Block-type efficiency        — save pure own-color for exteriors
        """
        block, position, orientation, flip = move
        temp_block = PlacedBlock(block, position, orientation, flip)
        positions = temp_block.get_occupied_positions()

        score = 0.0
        is_early = blocks_remaining > self.LATE_GAME_THRESHOLD

        # Pre-compute per-cell info
        cell_info = []
        for pos in positions:
            color = temp_block.get_color_at_position(pos)
            faces = self._exterior_faces(*pos)
            cell_info.append((pos, color, faces))

        c1, c2 = block.color1, block.color2

        # ── D1: Interior burial bonus ─────────────────────────────────
        # Bury opponent color in zero-face interior cells.  Huge reward
        # early game when interior ground-floor spots are available.
        for pos, color, faces in cell_info:
            if color == opp_color and faces == 0:
                # Interior burial — opponent point permanently wasted
                burial_bonus = 15 if is_early else 8
                # Ground floor interior is best (hardest to ever matter)
                if pos[2] == 0:
                    burial_bonus += 5
                elif pos[2] == 1:
                    burial_bonus += 2
                score += burial_bonus

            elif color == my_color and faces == 0:
                # Own color buried interior — bad, avoid this
                score -= 8

        # ── D2: BW net-zero face neutralization ───────────────────────
        # BW blocks on exterior: one half scores for us, one for opponent.
        # Net zero is *good* defensively — it wastes a face slot.
        # Especially valuable when opponent half is on a coverable face
        # (z<3) and own half is on z=3 (permanent).
        block_colors = {c1, c2}
        if block_colors == {Color.BLACK, Color.WHITE}:
            my_faces = 0
            opp_faces = 0
            my_on_top = False
            opp_on_coverable = False

            for pos, color, faces in cell_info:
                if color == my_color:
                    my_faces += faces
                    if pos[2] == 3 and faces > 0:
                        my_on_top = True
                elif color == opp_color:
                    opp_faces += faces
                    if pos[2] < 3 and faces > 0:
                        opp_on_coverable = True

            # Reward near net-zero face outcomes
            net = my_faces - opp_faces
            if net == 0 and (my_faces + opp_faces) > 0:
                score += 8  # perfect cancel
                if my_on_top and opp_on_coverable:
                    score += 6  # ideal: our point permanent, theirs temporary
            elif abs(net) <= 1:
                score += 4  # close to net-zero, still decent

            # Vertical BW at z=2-3 on edge column — top-tier sabotage
            if orientation == 'z':
                pos0, pos1 = positions[0], positions[1]
                if pos0[2] == 2 and self._is_edge_column(pos0[0], pos0[1]):
                    score += 5

        # ── D3: Opponent z=2 edge/corner poisoning ────────────────────
        # Opponent color at z=2 on an edge/corner column poisons that
        # column: the stacking rule forbids opponent from claiming z=3
        # above with their own color.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == opp_color and z == 2 and self._is_edge_column(x, y):
                z3_pos = (x, y, 3)
                if z3_pos not in game_state.grid:
                    poison_bonus = 12
                    if self._is_corner_column(x, y):
                        poison_bonus += 6  # corner z=3 is 3 faces — huge denial
                    score += poison_bonus

        # ── D4: Opponent z=3 avoidance ────────────────────────────────
        # Placing opponent color at z=3 on edges/corners is a disaster —
        # it gives them permanent uncoverable points.  Avoid at all costs.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == opp_color and z == 3:
                penalty = faces * 20  # catastrophic — permanent opponent points
                score -= penalty

        # ── D5: Own-color face scoring (secondary objective) ──────────
        # We still want our own points, just less aggressively than an
        # offensive strategy.  Weight is moderate — sabotage comes first.
        for pos, color, faces in cell_info:
            if color == my_color and faces > 0:
                bonus = faces * 4
                if pos[2] == 3:
                    bonus += faces * 3  # permanent own points, good
                score += bonus

        # ── D6: Stacking trap setup ───────────────────────────────────
        # Place our own color at z=2 on edge columns.  This prevents the
        # opponent from placing OUR color at z=3 above (stacking rule),
        # which might seem bad — but we can place opp-color or RED there
        # later to deny the opponent.  Also, if we later get to place our
        # own color at z=3 on a *different* face of the same cell, the
        # stacking rule only applies vertically.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == my_color and z == 2 and self._is_edge_column(x, y):
                z3_pos = (x, y, 3)
                if z3_pos not in game_state.grid:
                    # Our color at z=2: opponent can't stack their color
                    # above either (wait, the constraint says same-color —
                    # opponent CAN place their color above ours).
                    # But: WE can't stack our own color at z=3.
                    # This is a COST.  Penalize lightly if the z=3 cell
                    # is high-value (multi-face).
                    z3_faces = self._exterior_faces(x, y, 3)
                    if z3_faces >= 2:
                        score -= 4  # we're giving up a premium z=3 spot

        # ── D7: Opponent forced into bad orientations ─────────────────
        # In late game, reward moves that leave the opponent with blocks
        # that can only be placed in low-value (interior) positions.
        # Approximate by checking if this placement covers ground-floor
        # edge cells (reducing future high-value real estate).
        if not is_early:
            for pos, color, faces in cell_info:
                x, y, z = pos
                # Filling in edge column cells reduces options
                if z == 0 and self._is_edge_column(x, y):
                    # Ground floor edge now occupied — opponent can't use it
                    if (x, y, 0) not in game_state.grid:
                        score += 2
                # Filling z=1 on edge columns further constrains
                if z == 1 and self._is_edge_column(x, y):
                    below = (x, y, 0)
                    if below in game_state.grid:
                        score += 1

        # ── D8: Block-type efficiency ─────────────────────────────────
        # Pure own-color blocks (BB/WW) are rare (3 each).  Don't waste
        # them on interior or low-face positions.  Save for z=3 exteriors.
        if c1 == my_color and c2 == my_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces >= 4:
                score += 6   # excellent use
            elif total_faces >= 2:
                score += 2
            elif total_faces <= 1:
                score -= 10  # terrible waste of a rare block

        # Pure opponent-color blocks (BB/WW for them) — bury interior
        if c1 == opp_color and c2 == opp_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces == 0:
                score += 12  # perfect: both halves buried with zero faces
            elif total_faces <= 1:
                score += 5
            elif total_faces >= 3:
                score -= 8   # giving them lots of face exposure

        # Opponent+RED blocks — orient so opponent is interior, red exterior
        has_opp = (c1 == opp_color or c2 == opp_color)
        has_red = (c1 == Color.RED or c2 == Color.RED)
        if has_opp and has_red:
            for pos, color, faces in cell_info:
                if color == opp_color and faces == 0:
                    score += 6  # opponent buried, red takes the face
                elif color == Color.RED and faces >= 2:
                    score += 3  # red on exterior is neutral (not opponent)
                elif color == opp_color and faces >= 2:
                    score -= 6  # opponent on multi-face exterior — bad

        return score

    # ── main entry point ──────────────────────────────────────────────────

    def choose_move(self, game_state: GameState,
                    player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
        opp_color = Color.BLACK if player == Player.WHITE else Color.WHITE
        blocks_remaining = len(game_state.remaining_blocks)

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = self._smart_sample(legal_moves, my_color, opp_color)

        best_score = float('-inf')
        best_moves: list = []

        for move in candidates:
            s = self._evaluate_move(move, game_state, my_color, opp_color,
                                    blocks_remaining)
            if s > best_score:
                best_score = s
                best_moves = [move]
            elif s == best_score:
                best_moves.append(move)

        return random.choice(best_moves)
