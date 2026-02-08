"""
Counter-Defensive strategy — sabotage-first, race-second warfare.

Specifically designed to beat :class:`~blocko.strategies.defensive.DefensiveStrategy`
by mirroring its burial doctrine from move 1 while opportunistically racing to
claim the permanent z=3 top layer positions that Defensive defers.

**Three pillars of counter-play:**

1. **Mirror sabotage from move 1** — Assume the opponent is Defensive until
   proven otherwise.  Bury opponent color in interior cells and poison their
   z=2 edge columns at the same rate Defensive does to you, starting
   immediately.  This eliminates the 3-move detection lag that previously let
   Defensive build an unrecoverable burial lead as White.

2. **z=3 racing (mid/late game)** — After matching the burial rate, pivot to
   claiming top-layer corner and edge positions (worth 1–3 permanent faces).
   The racing bonus scales up as blocks decrease, peaking in mid-game when
   z=2 foundations are in place.

3. **Block pool warfare** — Use pure own-color blocks (BB/WW, 3 each) on
   high-face exterior positions before Defensive can grab them for burial.
   Deny Defensive its primary weapon.

Adapts automatically to non-Defensive opponents via board-state detection
(C10): when sustained non-burial play is detected (>6 moves, zero burial
signals), shifts toward general scoring.  The default posture is always
sabotage-first, making Counter resilient from move 1 regardless of seat.

Complexity: O(1) per candidate with 4-tier biased sampling (MAX_CANDIDATES=200).
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class CounterDefensiveStrategy(Strategy):
    """
    10-component analytical evaluator with adaptive opponent detection.

    Designed to beat DefensiveStrategy while remaining competitive against
    all other strategies.
    """

    MAX_CANDIDATES = 200
    EARLY_GAME_THRESHOLD = 20   # blocks remaining
    MID_GAME_THRESHOLD = 14

    # ── helpers (bounds-aware for OpenGrid support) ────────────────────────

    def _exterior_faces(self, x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        return exterior_faces(x, y, z, self._bounds)

    def _is_interior(self, x: int, y: int, z: int) -> bool:
        """True if the cell touches zero scored exterior faces."""
        bx_min, bx_max, by_min, by_max, _, _ = self._bounds
        return (bx_min < x < bx_max) and (by_min < y < by_max) and (z < 3)

    def _is_edge_column(self, x: int, y: int) -> bool:
        """True if (x, y) is on the perimeter of the scoring box."""
        bx_min, bx_max, by_min, by_max, _, _ = self._bounds
        return x == bx_min or x == bx_max or y == by_min or y == by_max

    def _is_corner_column(self, x: int, y: int) -> bool:
        """True if (x, y) is a corner of the scoring box."""
        bx_min, bx_max, by_min, by_max, _, _ = self._bounds
        return (x in (bx_min, bx_max)) and (y in (by_min, by_max))

    # ── board-state scan (once per turn) ──────────────────────────────────

    def _scan_board_state(self, game_state: GameState,
                          my_color: Color, opp_color: Color) -> dict:
        """
        Pre-compute board-level signals for context-aware evaluation.
        Cost: O(64) cell lookups — runs once per choose_move() call.
        """
        bx_min, bx_max, by_min, by_max, _, _ = self._bounds

        opp_burial_count = 0    # how many of MY cells are buried interior
        my_burial_count = 0     # how many of OPP cells I have buried
        poisoned_columns = set()      # (x,y) where MY color is at z=2
        opp_poisoned_columns = set()  # (x,y) where OPP color is at z=2
        open_z3_edge_cells = set()    # (x,y) edge columns with z=3 open + z=2 supported
        available_z3_corners = set()  # (x,y) corner columns with z=3 open + z=2 supported

        for x in range(bx_min, bx_max + 1):
            for y in range(by_min, by_max + 1):
                for z in range(3):  # z=0,1,2
                    pos = (x, y, z)
                    if pos in game_state.grid:
                        color = game_state.grid[pos].get_color_at_position(pos)
                        if self._is_interior(x, y, z):
                            if color == my_color:
                                opp_burial_count += 1
                            elif color == opp_color:
                                my_burial_count += 1

                # Check z=2 poisoning
                z2_pos = (x, y, 2)
                z3_pos = (x, y, 3)
                if z2_pos in game_state.grid and self._is_edge_column(x, y):
                    color_at_z2 = game_state.grid[z2_pos].get_color_at_position(z2_pos)
                    if color_at_z2 == my_color:
                        poisoned_columns.add((x, y))
                    elif color_at_z2 == opp_color:
                        opp_poisoned_columns.add((x, y))

                # Check z=3 availability
                if z3_pos not in game_state.grid and z2_pos in game_state.grid:
                    if self._is_edge_column(x, y):
                        open_z3_edge_cells.add((x, y))
                    if self._is_corner_column(x, y):
                        available_z3_corners.add((x, y))

        # Count remaining block types
        remaining_bb = 0
        remaining_ww = 0
        remaining_bw = 0
        for b in game_state.remaining_blocks:
            c1, c2 = b.color1, b.color2
            if c1 == Color.BLACK and c2 == Color.BLACK:
                remaining_bb += 1
            elif c1 == Color.WHITE and c2 == Color.WHITE:
                remaining_ww += 1
            elif {c1, c2} == {Color.BLACK, Color.WHITE}:
                remaining_bw += 1

        # Face coverage counts
        face_counts = {
            'top': {'my': 0, 'opp': 0},
            'front': {'my': 0, 'opp': 0},
            'back': {'my': 0, 'opp': 0},
            'left': {'my': 0, 'opp': 0},
            'right': {'my': 0, 'opp': 0},
        }
        face_positions = {
            'top':   [(x, y, 3) for x in range(bx_min, bx_max + 1) for y in range(by_min, by_max + 1)],
            'front': [(x, by_min, z) for x in range(bx_min, bx_max + 1) for z in range(4)],
            'back':  [(x, by_max, z) for x in range(bx_min, bx_max + 1) for z in range(4)],
            'left':  [(bx_min, y, z) for y in range(by_min, by_max + 1) for z in range(4)],
            'right': [(bx_max, y, z) for y in range(by_min, by_max + 1) for z in range(4)],
        }
        for face_name, positions in face_positions.items():
            for pos in positions:
                if pos in game_state.grid:
                    color = game_state.grid[pos].get_color_at_position(pos)
                    if color == my_color:
                        face_counts[face_name]['my'] += 1
                    elif color == opp_color:
                        face_counts[face_name]['opp'] += 1

        # Approximate move count from blocks placed (32 total, each turn
        # places 1 block = occupies 2 cells).  Blocks remaining < 32 means
        # moves have been made.  Each player has made roughly (32 - remaining) / 2 moves.
        blocks_remaining = len(game_state.remaining_blocks)
        total_moves = 32 - blocks_remaining  # blocks placed so far
        filled_cells = len(game_state.grid)

        # ── C10 adaptive detection — "assume defensive until proven otherwise"
        # Early game (< 6 blocks placed): always assume defensive — we have
        # no information yet and Defensive is the meta threat.
        # Mid game (6-14 blocks placed): look for burial/poison signals.
        #   If signals detected → defensive confirmed, keep sabotage-first.
        #   If NO signals after 6+ blocks → likely non-defensive, shift to scoring.
        # Late game: re-evaluate based on cumulative signals.
        if total_moves < 6:
            # Too early to tell — default to sabotage-first posture
            is_defensive_opponent = True
        else:
            # After 6+ blocks placed, require EVIDENCE of non-defensive play
            # to drop the sabotage posture.  Defensive signals = burial or poison.
            defensive_signals = opp_burial_count + len(poisoned_columns)
            # Non-defensive = zero signals after many moves
            is_defensive_opponent = defensive_signals >= 1

        # Burial parity: how far behind we are on the burial race
        burial_deficit = opp_burial_count - my_burial_count  # positive = we're behind

        return {
            'opp_burial_count': opp_burial_count,
            'my_burial_count': my_burial_count,
            'burial_deficit': burial_deficit,
            'poisoned_columns': poisoned_columns,
            'opp_poisoned_columns': opp_poisoned_columns,
            'open_z3_edge_cells': open_z3_edge_cells,
            'available_z3_corners': available_z3_corners,
            'remaining_bb': remaining_bb,
            'remaining_ww': remaining_ww,
            'remaining_bw': remaining_bw,
            'face_counts': face_counts,
            'total_moves': total_moves,
            'filled_cells': filled_cells,
            'is_defensive_opponent': is_defensive_opponent,
        }

    # ── 4-tier smart sampling ─────────────────────────────────────────────

    def _smart_sample(self, legal_moves: list, my_color: Color,
                      opp_color: Color, scan: dict) -> list:
        """
        4-tier sampling biased toward counter-play.

        Tier 0 (always kept): Mirror burial, counter-poison, z=3 racing,
                              pure own-color on high faces.
        Tier 1: BW blocks on edge columns, own+RED on 2+ faces.
        Tier 2: Any move with own color on 1+ faces, opp+RED burial.
        Tier 3: Everything else.
        """
        tiers: list[list] = [[], [], [], []]

        for move in legal_moves:
            block = move[0]
            c1, c2 = block.color1, block.color2
            colors = {c1, c2}
            temp = PlacedBlock(block, move[1], move[2], move[3])
            positions = temp.get_occupied_positions()

            tier_assigned = False

            # Tier 0 checks
            for pos in positions:
                color = temp.get_color_at_position(pos)
                x, y, z = pos

                # Mirror burial: opponent color in interior
                if color == opp_color and self._is_interior(x, y, z):
                    tiers[0].append(move)
                    tier_assigned = True
                    break
                # Counter-poison: opponent color at z=2 on edge
                if (color == opp_color and z == 2
                        and self._is_edge_column(x, y)):
                    tiers[0].append(move)
                    tier_assigned = True
                    break
                # z=3 racing: own color at z=3 on edge/corner
                if (color == my_color and z == 3
                        and self._is_edge_column(x, y)):
                    tiers[0].append(move)
                    tier_assigned = True
                    break

            if tier_assigned:
                continue

            # Tier 0: pure own-color on 3+ faces
            if c1 == my_color and c2 == my_color:
                total_faces = sum(self._exterior_faces(*p) for p in positions)
                if total_faces >= 3:
                    tiers[0].append(move)
                    continue
                else:
                    tiers[1].append(move)
                    continue

            # Tier 1: BW on edge columns, own+RED on 2+ faces
            if colors == {Color.BLACK, Color.WHITE}:
                any_edge = any(self._is_edge_column(p[0], p[1])
                               for p in positions)
                if any_edge:
                    tiers[1].append(move)
                    continue

            if my_color in colors and Color.RED in colors:
                total_faces = sum(self._exterior_faces(*p) for p in positions)
                if total_faces >= 2:
                    tiers[1].append(move)
                    continue

            # Tier 2: any move with own color on exterior
            has_own_exterior = False
            for pos in positions:
                color = temp.get_color_at_position(pos)
                if color == my_color and self._exterior_faces(*pos) > 0:
                    has_own_exterior = True
                    break
            if has_own_exterior:
                tiers[2].append(move)
                continue

            # Tier 3: everything else
            tiers[3].append(move)

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

    # ── 10-component evaluator ────────────────────────────────────────────

    def _evaluate_move(self, move, game_state: GameState,
                       my_color: Color, opp_color: Color,
                       blocks_remaining: int, scan: dict) -> float:
        """
        Score a candidate move using 10 components.
        All O(1) per move — no state copying.
        """
        block, position, orientation, flip = move
        temp_block = PlacedBlock(block, position, orientation, flip)
        positions = temp_block.get_occupied_positions()

        score = 0.0
        is_early = blocks_remaining > self.EARLY_GAME_THRESHOLD
        is_late = blocks_remaining <= self.MID_GAME_THRESHOLD
        is_defensive = scan['is_defensive_opponent']
        burial_deficit = scan['burial_deficit']
        total_moves = scan['total_moves']

        # ── C10 adaptive multipliers ────────────────────────────────────
        # Default posture: sabotage-first.  Scoring is secondary until
        # mid-game or until the opponent is confirmed non-defensive.
        if is_early:
            # Early game: sabotage ALWAYS high regardless of detection.
            # This ensures White doesn't waste moves 1-3 on scoring while
            # Defensive buries our pieces.
            sabotage_mult = 1.4
            z3_race_mult = 0.8   # z=3 racing deferred to mid-game
            scoring_mult = 0.6   # pure scoring heavily discounted
            if not is_defensive:
                # Opponent confirmed non-defensive after 6+ moves:
                # moderate shift toward scoring, but still bury
                sabotage_mult = 1.0
                z3_race_mult = 1.0
                scoring_mult = 1.0
        else:
            # Mid/late game: z=3 racing becomes the primary win condition
            sabotage_mult = 1.2 if is_defensive else 0.7
            z3_race_mult = 1.4 if is_defensive else 1.1
            scoring_mult = 1.0 if is_defensive else 1.3

        # Burial catch-up urgency: if we're behind on burial, boost further
        if burial_deficit > 0:
            sabotage_mult += burial_deficit * 0.15  # +0.15 per burial behind

        # Pre-compute per-cell info
        cell_info = []
        for pos in positions:
            color = temp_block.get_color_at_position(pos)
            faces = self._exterior_faces(*pos)
            cell_info.append((pos, color, faces))

        c1, c2 = block.color1, block.color2
        block_colors = {c1, c2}

        # ── C1: Mirror Burial ─────────────────────────────────────────
        # Bury opponent color in zero-face interior to match Defensive's
        # burial rate from move 1.  This is the HIGHEST priority in early
        # game — it must outbid C4/C7 scoring to prevent the White-side
        # opening weakness where Counter chases scoring while Defensive
        # builds an unrecoverable burial lead.
        for pos, color, faces in cell_info:
            if color == opp_color and faces == 0 and self._is_interior(*pos):
                base = 18 if pos[2] == 0 else (15 if pos[2] == 1 else 11)
                # Early game burial is critical — bump further
                if is_early:
                    base += 4
                elif is_late:
                    base = int(base * 0.5)
                # Burial catch-up: extra reward when behind on burial race
                if burial_deficit > 0:
                    base += min(burial_deficit * 3, 12)
                score += base * sabotage_mult

            elif color == my_color and faces == 0:
                score -= 8  # own color wasted interior (slightly harsher)

        # ── C2: Counter-Poisoning ─────────────────────────────────────
        # Place opponent color at z=2 on edge/corner columns to deny
        # them z=3.  Symmetric exploit of the stacking rule.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == opp_color and z == 2 and self._is_edge_column(x, y):
                z3_pos = (x, y, 3)
                if z3_pos not in game_state.grid:
                    base = 14
                    if self._is_corner_column(x, y):
                        base += 8  # deny 3-face z=3 corner
                    # Catch-up bonus if we're behind on the poison race
                    if len(scan['opp_poisoned_columns']) < len(scan['poisoned_columns']):
                        base += 4
                    score += base * sabotage_mult

        # ── C3: Opponent z=3 Gift Avoidance ───────────────────────────
        # Catastrophic penalty for giving opponent permanent z=3 points.
        for pos, color, faces in cell_info:
            if color == opp_color and pos[2] == 3:
                score -= faces * 25  # never reduced by any modifier

        # ── C4: z=3 Racing ────────────────────────────────────────────
        # Claim own color at z=3 — the permanent layer that Defensive
        # defers.  This is the primary win condition in MID-GAME, not
        # early game.  Racing too early (moves 1-4) wastes tempo that
        # should go to burial.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == my_color and z == 3 and faces > 0:
                base = faces * 10
                if self._is_corner_column(x, y):
                    base += 6   # corner z=3 = 3 faces, supreme value
                elif self._is_edge_column(x, y):
                    base += 3   # edge z=3 = 2 faces, strong value
                # Mid-game is the sweet spot for z=3 racing — foundations
                # are built and burial rate can slow.
                if not is_early and not is_late:
                    base += 5   # mid-game racing bonus
                elif is_late:
                    base += 3   # late game — still valuable
                # Early game: NO bonus — burial takes priority.
                # z3_race_mult is already 0.8 in early game.
                score += base * z3_race_mult

        # ── C5: z=3 Foundation Building ───────────────────────────────
        # Reward placing RED or opponent color at z=2 on edge columns
        # to support future z=3 claims without self-poisoning.
        # Foundations are valuable in early game because they enable the
        # mid-game z=3 race.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if z == 2 and self._is_edge_column(x, y):
                z3_pos = (x, y, 3)
                if z3_pos not in game_state.grid:
                    if color == Color.RED:
                        base_found = 6  # RED at z=2: any color can go at z=3
                        if self._is_corner_column(x, y):
                            base_found += 4  # corner foundation is premium
                        score += base_found
                    elif color == opp_color:
                        pass  # handled by C2 (counter-poison)
                    elif color == my_color:
                        # Self-poisoning: we can't put our color at z=3 above
                        z3_faces = self._exterior_faces(x, y, 3)
                        if z3_faces >= 2:
                            score -= 7  # blocking a high-value z=3 claim

        # ── C6: Block Pool Warfare ────────────────────────────────────
        # Part A: Pure own-color block efficiency
        if c1 == my_color and c2 == my_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces >= 4:
                score += 8   # excellent use of rare block
            elif total_faces >= 3:
                score += 4
            elif total_faces <= 1:
                score -= 12  # terrible waste — save for exteriors

        # Part B: Pure opponent-color block denial
        if c1 == opp_color and c2 == opp_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces == 0:
                # Buried both halves: maximum sabotage + block denial
                denial_bonus = 10
                # Diminishing returns if opponent has few pure blocks left
                opp_pure_remaining = (scan['remaining_bb']
                                      if opp_color == Color.BLACK
                                      else scan['remaining_ww'])
                if opp_pure_remaining < 2:
                    denial_bonus = 4
                score += denial_bonus
            elif total_faces <= 1:
                score += 5
            elif total_faces >= 3:
                score -= 8  # giving opponent lots of face exposure

        # Part C: BW block offensive orientation
        if block_colors == {Color.BLACK, Color.WHITE}:
            if orientation == 'z':
                pos0, pos1 = positions[0], positions[1]
                color0 = cell_info[0][1]
                color1 = cell_info[1][1]
                z_low = pos0[2]
                # Ideal: own color at z=3 (permanent), opponent at z=2 (poison)
                if z_low == 2 and self._is_edge_column(pos0[0], pos0[1]):
                    if color1 == my_color and color0 == opp_color:
                        # Top half is ours (z=3), bottom is opponent (z=2 poison)
                        score += 7
                    elif color0 == my_color and color1 == opp_color:
                        # Top half is opponent at z=3 — catastrophic
                        score -= 5  # C3 handles the heavy penalty

            # General BW: prefer our half on exterior, opponent interior
            for pos, color, faces in cell_info:
                if color == my_color and faces > 0:
                    score += 2
                elif color == opp_color and faces == 0:
                    score += 2

        # Part D: Opponent+RED block orientation
        has_opp = (c1 == opp_color or c2 == opp_color)
        has_red = (c1 == Color.RED or c2 == Color.RED)
        if has_opp and has_red:
            for pos, color, faces in cell_info:
                if color == opp_color and faces == 0:
                    score += 6  # opponent buried, red takes face
                elif color == Color.RED and faces >= 2:
                    score += 3  # neutral on exterior
                elif color == opp_color and faces >= 2:
                    score -= 6  # opponent on multi-face exterior

        # ── C7: Net Score Delta ───────────────────────────────────────
        # General face-counting — keeps Counter competitive against
        # non-Defensive opponents.  In early game with scoring_mult=0.6,
        # this yields ~3.6/face, ensuring burial (18+4 base × 1.4 mult =
        # ~30) always outbids a 2-face claim (~7.2).
        my_face_gain = 0
        opp_face_gain = 0
        for _pos, color, faces in cell_info:
            if color == my_color:
                my_face_gain += faces
            elif color == opp_color:
                opp_face_gain += faces
        net_delta = my_face_gain - opp_face_gain
        # Base value per face: 6 (reduced from 8 to widen burial advantage)
        score += net_delta * 6 * scoring_mult

        # ── C8: Face Coverage Balance ─────────────────────────────────
        # Reward placing own color on underserved faces.
        _bx_min, _bx_max, _by_min, _by_max, _, _bz_max = self._bounds
        face_map = {
            'top':   lambda x, y, z, _bz=_bz_max: z == _bz,
            'front': lambda x, y, z, _by=_by_min: y == _by,
            'back':  lambda x, y, z, _by=_by_max: y == _by,
            'left':  lambda x, y, z, _bx=_bx_min: x == _bx,
            'right': lambda x, y, z, _bx=_bx_max: x == _bx,
        }
        fc = scan['face_counts']
        for pos, color, faces in cell_info:
            if color == my_color:
                x, y, z = pos
                for face_name, test in face_map.items():
                    if test(x, y, z):
                        if fc[face_name]['my'] < 4:
                            score += 3
                        elif fc[face_name]['my'] < 8:
                            score += 1

        # ── C9: RED Utilization ───────────────────────────────────────
        # RED scores for nobody — use it for positional control.
        for pos, color, faces in cell_info:
            x, y, z = pos
            if color == Color.RED:
                if z == 2 and self._is_edge_column(x, y):
                    score += 3  # keeps z=3 open for any color
                elif z == 3 and faces > 0:
                    # RED at z=3 wastes a permanent slot — but check if
                    # we could place our own color there instead.
                    # Since RED was part of a 2-cell block, the other half
                    # has value; this is just a mild penalty for the waste.
                    score -= 1
                elif faces == 0:
                    score -= 2  # RED interior is completely pointless

        # ── C10: Adaptive Detection (implicit via sabotage_mult etc.) ─
        # Already applied as multipliers above.  No additional score.

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
        self._bounds = game_state.scoring_bounds()

        # Pre-compute board state once per turn
        scan = self._scan_board_state(game_state, my_color, opp_color)

        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = self._smart_sample(legal_moves, my_color,
                                            opp_color, scan)

        best_score = float('-inf')
        best_moves: list = []

        for move in candidates:
            s = self._evaluate_move(move, game_state, my_color, opp_color,
                                    blocks_remaining, scan)
            if s > best_score:
                best_score = s
                best_moves = [move]
            elif s == best_score:
                best_moves.append(move)

        return random.choice(best_moves)
