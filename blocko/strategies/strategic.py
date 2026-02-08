"""
Strategic AI strategy — 12-component evaluator + minimax endgame.

**Phase 1 (early/mid game, >12 blocks remaining):**
Enhanced O(1) analytical evaluation with 12 weighted components and
6-tier smart sampling.  No state copies.

**Phase 2 (endgame, ≤12 blocks remaining):**
Alpha-beta minimax at adaptive depth (2–4 plies), using the analytical
evaluator for move ordering and leaf scoring.  This detects forced
WR-flood sequences that skilled players exploit.

Weaknesses addressed:
  W1  No endgame lookahead          → minimax search
  W2  BR addiction / safe-move bias  → aggression bonus, 6-tier sampling
  W3  Failure to contest z=3         → doubled top-layer weights
  W4  No stacking-constraint weapon  → constraint propagation component
  W5  Corner fixation vs face breadth→ reduced corner premium, face coverage
  W6  No counter to BW burial        → burial detection + edge disruption
  W7  WR allocation backwards        → opponent-block orientation component
"""

import random
from typing import Optional, Tuple

from blocko.core.models import Block, Color, PlacedBlock, Player, exterior_faces
from blocko.core.game_state import GameState
from blocko.strategies.base import Strategy


class StrategicAIStrategy(Strategy):
    """
    12-component analytical evaluator + alpha-beta minimax hybrid.

    Complexity: O(1) per candidate in early/mid game; depth 2–4 minimax
    in endgame (≤12 blocks).
    """

    ENDGAME_THRESHOLD = 12
    MAX_CANDIDATES = 150

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        return exterior_faces(x, y, z)

    # ── face-count cache (per turn) ───────────────────────────────────────

    def _compute_face_counts(self, game_state: GameState,
                             my_color: Color, opp_color: Color) -> dict:
        """
        Count cells of each colour on each of the 5 scored faces.
        O(80) — runs once per choose_move() call, not per candidate.
        """
        faces = {
            'top':   {'my': 0, 'opp': 0},
            'front': {'my': 0, 'opp': 0},
            'back':  {'my': 0, 'opp': 0},
            'left':  {'my': 0, 'opp': 0},
            'right': {'my': 0, 'opp': 0},
        }
        face_positions = {
            'top':   [(x, y, 3) for x in range(4) for y in range(4)],
            'front': [(x, 0, z) for x in range(4) for z in range(4)],
            'back':  [(x, 3, z) for x in range(4) for z in range(4)],
            'left':  [(0, y, z) for y in range(4) for z in range(4)],
            'right': [(3, y, z) for y in range(4) for z in range(4)],
        }
        for face_name, positions in face_positions.items():
            for pos in positions:
                if pos in game_state.grid:
                    color = game_state.grid[pos].get_color_at_position(pos)
                    if color == my_color:
                        faces[face_name]['my'] += 1
                    elif color == opp_color:
                        faces[face_name]['opp'] += 1
        return faces

    # ── 6-tier smart sampling ─────────────────────────────────────────────

    def _smart_sample(self, legal_moves: list, my_color: Color) -> list:
        """
        6-tier sampling.  Tier 0 ensures pure own-colour blocks on
        high-exterior-face positions are always evaluated (combats W2).
        """
        tiers: list[list] = [[] for _ in range(6)]

        for move in legal_moves:
            block = move[0]
            c1, c2 = block.color1, block.color2
            colors = {c1, c2}

            # Tier 0: pure own-colour on edge positions (≥3 exterior faces)
            if c1 == my_color and c2 == my_color:
                temp = PlacedBlock(block, move[1], move[2], move[3])
                total_faces = sum(self._exterior_faces(*p)
                                  for p in temp.get_occupied_positions())
                if total_faces >= 3:
                    tiers[0].append(move)
                    continue
                else:
                    tiers[1].append(move)
                    continue

            if my_color in colors and Color.RED in colors:
                tiers[2].append(move)
            elif Color.BLACK in colors and Color.WHITE in colors:
                tiers[3].append(move)
            elif my_color not in colors and Color.RED in colors:
                tiers[4].append(move)
            else:
                tiers[5].append(move)

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

    # ── 12-component analytical evaluator ─────────────────────────────────

    def _evaluate_move(self, move, game_state: GameState,
                       my_color: Color, opp_color: Color) -> float:
        """
        Compute a composite score for *move* using 12 weighted components.
        All components are O(1) per move (no state copying).
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

        c1, c2 = block.color1, block.color2

        # --- C1: Net score delta (weight ×12) ---  [W7]
        my_face_gain = 0
        opp_face_gain = 0
        for _pos, color, faces in cell_info:
            if color == my_color:
                my_face_gain += faces
            elif color == opp_color:
                opp_face_gain += faces
        score += (my_face_gain - opp_face_gain) * 12

        # --- C2: Top-layer permanence bonus (weight ×6/face) ---  [W3]
        for pos, color, faces in cell_info:
            if color == my_color and pos[2] == 3:
                score += faces * 6

        # --- C3: Corner premium (weight +3) ---  [W5 rebalanced]
        for _pos, color, faces in cell_info:
            if color == my_color and faces == 3:
                score += 3

        # --- C4: Interior waste penalty (-3/+1) ---
        for _pos, color, faces in cell_info:
            if faces == 0:
                if color == my_color:
                    score -= 3
                elif color == opp_color:
                    score += 1

        # --- C5: Future enablement bonus (+2) ---
        for pos, _color, _faces in cell_info:
            x, y, z = pos
            if z == 2:
                above = (x, y, 3)
                if above not in game_state.grid:
                    above_faces = self._exterior_faces(x, y, 3)
                    if above_faces >= 2:
                        score += 2

        # --- C6: Opponent top-layer penalty (×4/face) ---  [W3]
        for pos, color, faces in cell_info:
            if color == opp_color and pos[2] == 3:
                score -= faces * 4

        # --- C7: Block-type efficiency + aggression ---  [W2]
        if c1 == my_color and c2 == my_color:
            total_faces = sum(f for _, _, f in cell_info)
            if total_faces >= 4:
                score += 6
            elif total_faces <= 1:
                score -= 7
            if total_faces >= 3:
                score += 4

        has_opp = (c1 == opp_color or c2 == opp_color)
        if has_opp:
            for _pos, color, faces in cell_info:
                if color == opp_color and faces > 0:
                    score -= faces * 3

        # --- C8: Face coverage bonus (+2/underserved face) ---  [W5]
        if hasattr(self, '_face_counts'):
            face_map = {
                'top':   lambda x, y, z: z == 3,
                'front': lambda x, y, z: y == 0,
                'back':  lambda x, y, z: y == 3,
                'left':  lambda x, y, z: x == 0,
                'right': lambda x, y, z: x == 3,
            }
            for pos, color, faces in cell_info:
                if color == my_color:
                    x, y, z = pos
                    for face_name, test in face_map.items():
                        if test(x, y, z):
                            if self._face_counts[face_name]['my'] < 4:
                                score += 2

        # --- C9: Constraint propagation (z=2 → z=3 forcing) ---  [W4]
        for pos, color, faces in cell_info:
            x, y, z = pos
            is_edge = (x == 0 or x == 3 or y == 0 or y == 3)
            if z == 2 and is_edge:
                above_faces = self._exterior_faces(x, y, 3)
                if above_faces >= 2:
                    if color == my_color:
                        score -= 8
                    elif color == opp_color:
                        score += 4
                    elif color == Color.RED:
                        score += 1
            if z == 1 and is_edge:
                if color == my_color:
                    above_faces_z2 = self._exterior_faces(x, y, 2)
                    if above_faces_z2 >= 1:
                        above = (x, y, 2)
                        if above not in game_state.grid:
                            score -= 3

        # --- C10: BW burial detection ---  [W6]
        block_colors = {c1, c2}
        if block_colors == {Color.BLACK, Color.WHITE} and orientation == 'z':
            pos0, pos1 = positions[0], positions[1]
            color0 = cell_info[0][1]
            color1 = cell_info[1][1]
            z_low = pos0[2]
            if z_low == 0 and color0 == opp_color and color1 == my_color:
                faces_at_z1 = cell_info[1][2]
                if faces_at_z1 >= 1:
                    score += 6

        # Edge column ground-floor contestation
        for pos, color, faces in cell_info:
            x, y, z = pos
            if z == 0 and (x == 0 or x == 3 or y == 0 or y == 3):
                if (x, y, 0) not in game_state.grid:
                    score += 2

        # --- C11: Opponent block orientation optimisation ---  [W7]
        has_red = (c1 == Color.RED or c2 == Color.RED)
        if has_opp and has_red:
            for _pos, color, faces in cell_info:
                if color == opp_color and faces == 0:
                    score += 5
                elif color == Color.RED and faces >= 2:
                    score += 3
                elif color == opp_color and faces >= 2:
                    score -= 5

        # --- C12: Edge column race priority ---  [W3, W5, W6]
        for pos, color, faces in cell_info:
            x, y, z = pos
            is_edge = (x == 0 or x == 3 or y == 0 or y == 3)
            is_corner = (x in {0, 3}) and (y in {0, 3})
            if z == 0 and is_edge and color == my_color:
                score += 2
                if is_corner:
                    score += 1

        return score

    # ── minimax with alpha-beta pruning ───────────────────────────────────

    def _minimax(self, game_state: GameState, depth: int,
                 alpha: float, beta: float, maximizing: bool,
                 my_color: Color, opp_color: Color,
                 ai_player: Player) -> Tuple[float, Optional[tuple]]:
        """
        Alpha-beta minimax.  *maximizing* is True when it is the AI's turn.
        Returns (evaluation, best_move_or_None).
        """
        if depth == 0 or game_state.is_game_over():
            w, b = game_state.calculate_score()
            my_score = b if ai_player == Player.BLACK else w
            opp_score = w if ai_player == Player.BLACK else b
            return float(my_score - opp_score), None

        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            w, b = game_state.calculate_score()
            my_score = b if ai_player == Player.BLACK else w
            opp_score = w if ai_player == Player.BLACK else b
            return float(my_score - opp_score), None

        # Move ordering: analytical pre-sort for better pruning
        eval_color = my_color if maximizing else opp_color
        eval_opp   = opp_color if maximizing else my_color
        scored = [(self._evaluate_move(m, game_state, eval_color, eval_opp), m)
                  for m in legal_moves]
        scored.sort(key=lambda x: x[0], reverse=maximizing)

        top_k = 25 if depth >= 2 else 15
        candidates = [m for _, m in scored[:top_k]]

        if maximizing:
            max_eval = float('-inf')
            best_move = candidates[0]
            for move in candidates:
                child = game_state.copy()
                child.make_move(*move)
                ev, _ = self._minimax(child, depth - 1, alpha, beta,
                                      False, my_color, opp_color, ai_player)
                if ev > max_eval:
                    max_eval = ev
                    best_move = move
                alpha = max(alpha, ev)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = float('inf')
            best_move = candidates[0]
            for move in candidates:
                child = game_state.copy()
                child.make_move(*move)
                ev, _ = self._minimax(child, depth - 1, alpha, beta,
                                      True, my_color, opp_color, ai_player)
                if ev < min_eval:
                    min_eval = ev
                    best_move = move
                beta = min(beta, ev)
                if beta <= alpha:
                    break
            return min_eval, best_move

    # ── main entry point ──────────────────────────────────────────────────

    def choose_move(self, game_state: GameState,
                    player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color  = Color.WHITE if player == Player.WHITE else Color.BLACK
        opp_color = Color.BLACK if player == Player.WHITE else Color.WHITE

        remaining = len(game_state.remaining_blocks)

        # --- ENDGAME: minimax search ---
        if remaining <= self.ENDGAME_THRESHOLD:
            if remaining <= 4:
                depth = 4
            elif remaining <= 8:
                depth = 3
            else:
                depth = 2
            _, best_move = self._minimax(
                game_state, depth,
                float('-inf'), float('inf'),
                True, my_color, opp_color, player,
            )
            if best_move is not None:
                return best_move

        # --- EARLY/MID GAME: analytical evaluation ---
        self._face_counts = self._compute_face_counts(
            game_state, my_color, opp_color
        )

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
