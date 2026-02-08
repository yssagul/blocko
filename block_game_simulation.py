#!/usr/bin/env python3
"""
Monte Carlo Simulation for 4x4x4 Block Stacking Strategy Game

This script simulates a turn-based strategy game where players compete to have
the most of their color (black or white) showing on the exterior of a 4x4x4 cube.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from enum import Enum
import random
from collections import defaultdict
import copy


class Color(Enum):
    """Represents the three colors in the game"""
    BLACK = 0
    WHITE = 1
    RED = 2


class Player(Enum):
    """Represents the two players"""
    BLACK = 0
    WHITE = 1


@dataclass
class Block:
    """Represents a 1x1x2 block with colors on each half"""
    color1: Color  # Color of first half
    color2: Color  # Color of second half
    block_id: int  # Unique identifier

    def is_uniform(self) -> bool:
        """Check if block is all one color"""
        return self.color1 == self.color2

    def __repr__(self):
        return f"Block({self.color1.name[0]}{self.color2.name[0]})"


@dataclass
class PlacedBlock:
    """Represents a block placed in the game space"""
    block: Block
    position: Tuple[int, int, int]  # (x, y, z) coordinates
    orientation: str  # 'x', 'y', or 'z' - which axis the block extends along
    flip: bool  # Whether color1 or color2 is at the lower/negative end

    def get_occupied_positions(self) -> List[Tuple[int, int, int]]:
        """Returns the two 1x1x1 positions this block occupies"""
        x, y, z = self.position
        if self.orientation == 'x':
            return [(x, y, z), (x+1, y, z)]
        elif self.orientation == 'y':
            return [(x, y, z), (x, y+1, z)]
        else:  # z
            return [(x, y, z), (x, y, z+1)]

    def get_color_at_position(self, pos: Tuple[int, int, int]) -> Color:
        """Returns the color at a specific position"""
        positions = self.get_occupied_positions()
        if pos == positions[0]:
            return self.block.color1 if not self.flip else self.block.color2
        elif pos == positions[1]:
            return self.block.color2 if not self.flip else self.block.color1
        else:
            raise ValueError("Position not in this block")


class GameState:
    """Represents the current state of the game"""

    def __init__(self):
        self.grid = {}  # (x,y,z) -> PlacedBlock mapping
        self.remaining_blocks = self._initialize_blocks()
        self.current_player = Player.WHITE  # White goes first
        self.move_history = []

    def _initialize_blocks(self) -> List[Block]:
        """Creates the initial pool of 32 blocks"""
        blocks = []
        block_id = 0

        # 3 all-black
        for _ in range(3):
            blocks.append(Block(Color.BLACK, Color.BLACK, block_id))
            block_id += 1

        # 3 all-white
        for _ in range(3):
            blocks.append(Block(Color.WHITE, Color.WHITE, block_id))
            block_id += 1

        # 8 half-black/half-white
        for _ in range(8):
            blocks.append(Block(Color.BLACK, Color.WHITE, block_id))
            block_id += 1

        # 9 half-black/half-red
        for _ in range(9):
            blocks.append(Block(Color.BLACK, Color.RED, block_id))
            block_id += 1

        # 9 half-white/half-red
        for _ in range(9):
            blocks.append(Block(Color.WHITE, Color.RED, block_id))
            block_id += 1

        return blocks

    def _get_max_z(self) -> int:
        """Returns the highest occupied z-level, or -1 if grid is empty"""
        if not self.grid:
            return -1
        return max(z for _, _, z in self.grid)

    def get_legal_moves(self) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """
        Returns all legal moves as (block, position, orientation, flip) tuples
        """
        legal_moves = []

        # Only need to check z up to one above the current max occupied level
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)  # +2 because z-oriented blocks start one below their top

        # Deduplicate blocks by color pair to avoid redundant checks
        seen_color_pairs = set()
        unique_blocks = []
        duplicate_blocks = []
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key not in seen_color_pairs:
                seen_color_pairs.add(key)
                unique_blocks.append(block)
            else:
                duplicate_blocks.append(block)

        for block in unique_blocks:
            for x in range(4):
                for y in range(4):
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            for flip in [False, True]:
                                if self._is_legal_placement(block, (x, y, z), orientation, flip):
                                    legal_moves.append((block, (x, y, z), orientation, flip))

        # For duplicate blocks, copy legal placements from their unique representative
        for block in duplicate_blocks:
            key = (block.color1, block.color2)
            # Find the representative block's moves and replicate with this block
            for rep_block in unique_blocks:
                if (rep_block.color1, rep_block.color2) == key:
                    for move in legal_moves:
                        if move[0] is rep_block:
                            legal_moves.append((block, move[1], move[2], move[3]))
                    break

        return legal_moves

    def _is_legal_placement(self, block: Block, position: Tuple[int, int, int],
                           orientation: str, flip: bool) -> bool:
        """Check if a placement is legal according to game rules"""
        x, y, z = position

        # Create temporary placed block to check
        temp_block = PlacedBlock(block, position, orientation, flip)
        occupied_positions = temp_block.get_occupied_positions()
        occupied_set = set(occupied_positions)

        # Check all positions are within bounds
        for px, py, pz in occupied_positions:
            if not (0 <= px < 4 and 0 <= py < 4 and 0 <= pz < 4):
                return False

        # Check positions aren't already occupied
        for pos in occupied_positions:
            if pos in self.grid:
                return False

        # Check for support (no cantilevering)
        # A cell is supported if it's on the ground (z=0), OR the cell below
        # is already in the grid, OR the cell below is part of this same block
        # (self-support for vertical blocks)
        for px, py, pz in occupied_positions:
            if pz == 0:  # On the ground, always supported
                continue
            below = (px, py, pz-1)
            if below not in self.grid and below not in occupied_set:
                return False

        # Check stacking rules (can't stack same color on top of same color)
        # Only check against blocks already in the grid (not self-stacking within
        # the same block, since a vertical block's two halves are part of one piece)
        for px, py, pz in occupied_positions:
            if pz > 0:  # Not on ground level
                below_pos = (px, py, pz-1)
                if below_pos in self.grid:
                    color_above = temp_block.get_color_at_position((px, py, pz))
                    color_below = self.grid[below_pos].get_color_at_position(below_pos)

                    # Red can go on anything
                    if color_above == Color.RED:
                        continue

                    # Can't stack white on white or black on black
                    if color_above == color_below and color_above != Color.RED:
                        return False

        return True

    def make_move(self, block: Block, position: Tuple[int, int, int],
                  orientation: str, flip: bool) -> bool:
        """
        Execute a move. Returns True if successful, False otherwise.
        """
        if not self._is_legal_placement(block, position, orientation, flip):
            return False

        # Place the block
        placed_block = PlacedBlock(block, position, orientation, flip)
        for pos in placed_block.get_occupied_positions():
            self.grid[pos] = placed_block

        # Remove from remaining blocks
        self.remaining_blocks.remove(block)

        # Record move
        self.move_history.append((self.current_player, placed_block))

        # Switch player
        self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE

        return True

    def calculate_score(self) -> Tuple[int, int]:
        """
        Calculate final scores for both players.
        Returns (white_score, black_score)
        Only counts exterior faces (5 sides, not bottom)
        """
        white_score = 0
        black_score = 0

        # Check all exterior faces
        # Top face (z=3)
        for x in range(4):
            for y in range(4):
                pos = (x, y, 3)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Front face (y=0)
        for x in range(4):
            for z in range(4):
                pos = (x, 0, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Back face (y=3)
        for x in range(4):
            for z in range(4):
                pos = (x, 3, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Left face (x=0)
        for y in range(4):
            for z in range(4):
                pos = (0, y, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        # Right face (x=3)
        for y in range(4):
            for z in range(4):
                pos = (3, y, z)
                if pos in self.grid:
                    color = self.grid[pos].get_color_at_position(pos)
                    if color == Color.WHITE:
                        white_score += 1
                    elif color == Color.BLACK:
                        black_score += 1

        return white_score, black_score

    def is_game_over(self) -> bool:
        """Check if the game is over (no legal moves remain)"""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        seen_color_pairs = set()
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key in seen_color_pairs:
                continue
            seen_color_pairs.add(key)
            for x in range(4):
                for y in range(4):
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            if self._is_legal_placement(block, (x, y, z), orientation, False):
                                return False
                            if self._is_legal_placement(block, (x, y, z), orientation, True):
                                return False
        return True

    def get_bounds(self):
        """Return (x_min, x_max, y_min, y_max, z_min, z_max) of the play area."""
        return (0, 3, 0, 3, 0, 3)

    def exterior_faces(self, x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        bx_min, bx_max, by_min, by_max, bz_min, bz_max = self.get_bounds()
        faces = 0
        if x == bx_min or x == bx_max:
            faces += 1
        if y == by_min or y == by_max:
            faces += 1
        if z == bz_max:
            faces += 1
        return faces

    def copy(self):
        """Create a deep copy of the game state"""
        new_state = GameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        return new_state


class OpenGridGameState(GameState):
    """
    Open Grid variant: X and Y boundaries float dynamically.
    The first piece is placed at (0,0,0) and subsequent pieces can extend
    in ±X/±Y as long as each axis span never exceeds 4 (i.e. fits in 4 cells).
    Z remains fixed at 0-3. Each axis locks independently once its span = 4.
    """

    def __init__(self):
        super().__init__()
        self._x_min: int | None = None
        self._x_max: int | None = None
        self._y_min: int | None = None
        self._y_max: int | None = None

    def get_bounds(self):
        """
        Dynamic bounds based on occupied cells.
        Returns the *possible* bounding box (may be wider than occupied if axes float).
        For scoring, use _scoring_bounds() which returns the tightest valid 4-wide bbox.
        """
        if self._x_min is None:
            # No pieces placed yet — default to standard grid
            return (0, 3, 0, 3, 0, 3)
        # Per-axis: if locked (span=3 means 4 cells), return exact.
        # If floating, return the widest possible range.
        x_span = self._x_max - self._x_min
        if x_span >= 3:
            bx_min, bx_max = self._x_min, self._x_min + 3
        else:
            bx_min = self._x_max - 3
            bx_max = self._x_min + 3

        y_span = self._y_max - self._y_min
        if y_span >= 3:
            by_min, by_max = self._y_min, self._y_min + 3
        else:
            by_min = self._y_max - 3
            by_max = self._y_min + 3

        return (bx_min, bx_max, by_min, by_max, 0, 3)

    def _scoring_bounds(self):
        """
        Return the 4-wide bounding box used for scoring.
        If an axis is locked (span=3), that's the bbox.
        If floating, use the occupied min as the bbox origin.
        """
        if self._x_min is None:
            return (0, 3, 0, 3, 0, 3)
        return (self._x_min, self._x_min + 3,
                self._y_min, self._y_min + 3,
                0, 3)

    def _update_occupied_range(self, positions):
        """Update min/max tracking after placing cells."""
        for px, py, pz in positions:
            if self._x_min is None:
                self._x_min = self._x_max = px
                self._y_min = self._y_max = py
            else:
                self._x_min = min(self._x_min, px)
                self._x_max = max(self._x_max, px)
                self._y_min = min(self._y_min, py)
                self._y_max = max(self._y_max, py)

    def _is_legal_placement(self, block: Block, position: Tuple[int, int, int],
                           orientation: str, flip: bool) -> bool:
        """Check if a placement is legal in open grid mode."""
        x, y, z = position

        temp_block = PlacedBlock(block, position, orientation, flip)
        occupied_positions = temp_block.get_occupied_positions()
        occupied_set = set(occupied_positions)

        # Check Z bounds (always fixed 0-3)
        for px, py, pz in occupied_positions:
            if not (0 <= pz < 4):
                return False

        # Check X/Y span constraint: adding these cells must keep each axis ≤ 4 wide
        if self._x_min is not None:
            for px, py, pz in occupied_positions:
                new_x_min = min(self._x_min, px)
                new_x_max = max(self._x_max, px)
                if new_x_max - new_x_min > 3:
                    return False
                new_y_min = min(self._y_min, py)
                new_y_max = max(self._y_max, py)
                if new_y_max - new_y_min > 3:
                    return False

        # Check positions aren't already occupied
        for pos in occupied_positions:
            if pos in self.grid:
                return False

        # Check for support (gravity — same as base)
        for px, py, pz in occupied_positions:
            if pz == 0:
                continue
            below = (px, py, pz - 1)
            if below not in self.grid and below not in occupied_set:
                return False

        # Check stacking color rules (same as base)
        for px, py, pz in occupied_positions:
            if pz > 0:
                below_pos = (px, py, pz - 1)
                if below_pos in self.grid:
                    color_above = temp_block.get_color_at_position((px, py, pz))
                    color_below = self.grid[below_pos].get_color_at_position(below_pos)
                    if color_above == Color.RED:
                        continue
                    if color_above == color_below and color_above != Color.RED:
                        return False

        return True

    def make_move(self, block: Block, position: Tuple[int, int, int],
                  orientation: str, flip: bool) -> bool:
        """Execute a move and update the occupied range."""
        if not self._is_legal_placement(block, position, orientation, flip):
            return False

        placed_block = PlacedBlock(block, position, orientation, flip)
        positions = placed_block.get_occupied_positions()
        for pos in positions:
            self.grid[pos] = placed_block

        self.remaining_blocks.remove(block)
        self.move_history.append((self.current_player, placed_block))
        self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE

        # Update occupied range
        self._update_occupied_range(positions)

        return True

    def get_legal_moves(self) -> List[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Legal moves with dynamic X/Y coordinate ranges."""
        legal_moves = []
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        # Determine X/Y scan range
        if self._x_min is None:
            # No pieces yet — first piece can go anywhere in a reasonable range
            # Since blocks are 1x1x2, scanning [-1, 4] covers all sensible starts
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            # Scan range: positions that would keep axis span ≤ 4
            x_lo = self._x_max - 3  # leftmost x that keeps span ≤ 4
            x_hi = self._x_min + 3  # rightmost x that keeps span ≤ 4
            # +1 for orientation that extends +1 in x
            x_range = range(x_lo, x_hi + 1)
            y_lo = self._y_max - 3
            y_hi = self._y_min + 3
            y_range = range(y_lo, y_hi + 1)

        # Deduplicate blocks by color pair
        seen_color_pairs = set()
        unique_blocks = []
        duplicate_blocks = []
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key not in seen_color_pairs:
                seen_color_pairs.add(key)
                unique_blocks.append(block)
            else:
                duplicate_blocks.append(block)

        for block in unique_blocks:
            for x in x_range:
                for y in y_range:
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            for flip in [False, True]:
                                if self._is_legal_placement(block, (x, y, z), orientation, flip):
                                    legal_moves.append((block, (x, y, z), orientation, flip))

        # Copy legal placements for duplicate blocks
        for block in duplicate_blocks:
            key = (block.color1, block.color2)
            for rep_block in unique_blocks:
                if (rep_block.color1, rep_block.color2) == key:
                    for move in legal_moves:
                        if move[0] is rep_block:
                            legal_moves.append((block, move[1], move[2], move[3]))
                    break

        return legal_moves

    def is_game_over(self) -> bool:
        """Check if the game is over with dynamic coordinate ranges."""
        max_z = self._get_max_z()
        z_limit = min(max_z + 2, 4)

        if self._x_min is None:
            x_range = range(-1, 5)
            y_range = range(-1, 5)
        else:
            x_range = range(self._x_max - 3, self._x_min + 4)
            y_range = range(self._y_max - 3, self._y_min + 4)

        seen_color_pairs = set()
        for block in self.remaining_blocks:
            key = (block.color1, block.color2)
            if key in seen_color_pairs:
                continue
            seen_color_pairs.add(key)
            for x in x_range:
                for y in y_range:
                    for z in range(z_limit):
                        for orientation in ['x', 'y', 'z']:
                            if self._is_legal_placement(block, (x, y, z), orientation, False):
                                return False
                            if self._is_legal_placement(block, (x, y, z), orientation, True):
                                return False
        return True

    def calculate_score(self) -> Tuple[int, int]:
        """
        Calculate scores using the scoring bounding box.
        The scoring box is the tightest 4-wide box that contains all occupied cells.
        """
        white_score = 0
        black_score = 0

        bx_min, bx_max, by_min, by_max, bz_min, bz_max = self._scoring_bounds()

        def _count(pos):
            nonlocal white_score, black_score
            if pos in self.grid:
                color = self.grid[pos].get_color_at_position(pos)
                if color == Color.WHITE:
                    white_score += 1
                elif color == Color.BLACK:
                    black_score += 1

        # Top face (z = bz_max = 3)
        for x in range(bx_min, bx_max + 1):
            for y in range(by_min, by_max + 1):
                _count((x, y, bz_max))

        # Front face (y = by_min)
        for x in range(bx_min, bx_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((x, by_min, z))

        # Back face (y = by_max)
        for x in range(bx_min, bx_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((x, by_max, z))

        # Left face (x = bx_min)
        for y in range(by_min, by_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((bx_min, y, z))

        # Right face (x = bx_max)
        for y in range(by_min, by_max + 1):
            for z in range(bz_min, bz_max + 1):
                _count((bx_max, y, z))

        return white_score, black_score

    def copy(self):
        """Create a deep copy of the open grid game state."""
        new_state = OpenGridGameState()
        new_state.grid = copy.deepcopy(self.grid)
        new_state.remaining_blocks = self.remaining_blocks.copy()
        new_state.current_player = self.current_player
        new_state.move_history = self.move_history.copy()
        new_state._x_min = self._x_min
        new_state._x_max = self._x_max
        new_state._y_min = self._y_min
        new_state._y_max = self._y_max
        return new_state


class Strategy:
    """Base class for AI strategies"""

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        """Choose a move given the current game state"""
        raise NotImplementedError


class RandomStrategy(Strategy):
    """Randomly choose from available legal moves"""

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None
        return random.choice(legal_moves)


class GreedyStrategy(Strategy):
    """Choose the move that maximizes immediate point gain"""

    MAX_CANDIDATES = 100  # Evaluate at most this many moves per turn

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        best_score_diff = float('-inf')
        best_moves = []

        # Sample a subset when there are too many moves to evaluate
        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = random.sample(legal_moves, self.MAX_CANDIDATES)

        for move in candidates:
            # Simulate the move
            sim_state = game_state.copy()
            sim_state.make_move(*move)

            # Calculate score difference
            white_score, black_score = sim_state.calculate_score()
            score_diff = white_score - black_score if player == Player.WHITE else black_score - white_score

            if score_diff > best_score_diff:
                best_score_diff = score_diff
                best_moves = [move]
            elif score_diff == best_score_diff:
                best_moves.append(move)

        return random.choice(best_moves)


class DefensiveStrategy(Strategy):
    """Choose moves that minimize opponent's scoring opportunities"""

    MAX_CANDIDATES = 50  # Evaluate at most this many moves per turn

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        best_opponent_reduction = float('-inf')
        best_moves = []

        # Cache this outside the loop - it's the same for every candidate move
        opponent_moves_before = len(legal_moves)

        # Sample a subset when there are too many moves to evaluate
        candidates = legal_moves
        if len(legal_moves) > self.MAX_CANDIDATES:
            candidates = random.sample(legal_moves, self.MAX_CANDIDATES)

        for move in candidates:
            # Simulate the move
            sim_state = game_state.copy()
            sim_state.make_move(*move)

            # Count how many fewer moves opponent has
            opponent_moves_after = len(sim_state.get_legal_moves())
            reduction = opponent_moves_before - opponent_moves_after

            if reduction > best_opponent_reduction:
                best_opponent_reduction = reduction
                best_moves = [move]
            elif reduction == best_opponent_reduction:
                best_moves.append(move)

        return random.choice(best_moves)


class EdgeControlStrategy(Strategy):
    """Prioritize placing blocks on edges and corners for maximum visibility"""

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK

        def score_position(pos):
            """Score based on how many exterior faces this position has"""
            x, y, z = pos
            score = 0
            if x == 0 or x == 3: score += 1
            if y == 0 or y == 3: score += 1
            if z == 3: score += 1  # Top (not bottom)
            return score

        best_score = float('-inf')
        best_moves = []

        for move in legal_moves:
            block, position, orientation, flip = move
            temp_block = PlacedBlock(block, position, orientation, flip)

            # Calculate how many of MY color faces will be on exterior
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


class BlockOpponentStrategy(Strategy):
    """
    Game-state-aware blocking strategy that combines:
      1. Actual score improvement (simulate the move, measure real score change)
      2. Blocking bonus for denying opponent high-value future placements via
         the color-stacking rule
      3. Coverage awareness — penalizes leaving own high-value cells exposed
         for the opponent to stack on top of

    Uses move sampling to keep performance reasonable.
    """

    MAX_CANDIDATES = 100  # Evaluate at most this many moves per turn

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this position touches"""
        faces = 0
        if x == 0 or x == 3: faces += 1
        if y == 0 or y == 3: faces += 1
        if z == 3: faces += 1  # top face (bottom not scored)
        return faces

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        legal_moves = game_state.get_legal_moves()
        if not legal_moves:
            return None

        my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
        opponent_color = Color.BLACK if player == Player.WHITE else Color.WHITE

        # Current score before any move
        w_before, b_before = game_state.calculate_score()
        my_score_before = w_before if player == Player.WHITE else b_before
        opp_score_before = b_before if player == Player.WHITE else w_before

        # Sample moves if there are too many
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

            # Net score improvement (my gain minus opponent's gain)
            my_gain = my_score_after - my_score_before
            opp_gain = opp_score_after - opp_score_before
            score = (my_gain - opp_gain) * 3

            # === Component 2: Blocking bonus via stacking rule ===
            temp_block = PlacedBlock(block, position, orientation, flip)
            for pos in temp_block.get_occupied_positions():
                x, y, z = pos
                color = temp_block.get_color_at_position(pos)

                if color == opponent_color and z < 3:
                    # Placing opponent's color here prevents them from stacking
                    # their own color at (x, y, z+1). Score the value of that
                    # blocked position.
                    above = (x, y, z + 1)
                    if above not in game_state.grid and above not in set(temp_block.get_occupied_positions()):
                        above_vis = self._exterior_faces(x, y, z + 1)
                        score += above_vis * 2

                elif color == my_color and z < 3:
                    # Placing my color here prevents opponent from stacking
                    # my color above (since same-color stacking is illegal).
                    # But it also means I can't stack my own color above either.
                    # Penalize slightly if the position above is high-value
                    # and empty — opponent could cover us with THEIR color.
                    above = (x, y, z + 1)
                    if above not in game_state.grid and above not in set(temp_block.get_occupied_positions()):
                        above_vis = self._exterior_faces(x, y, z + 1)
                        # Small penalty: we're exposed and opponent can cover us
                        score -= above_vis * 1

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves)


class AntiRandomStrategy(Strategy):
    """
    Analytically-optimised strategy designed to crush RandomStrategy.

    Key insight: the score delta of any move can be computed in O(1) without
    simulating the game state, because scoring is purely positional (exterior
    face count) and blocks are never removed.

    Evaluation combines 7 weighted components:
      1. Net score delta  (my exterior faces − opponent exterior faces)
      2. Top-layer permanence bonus  (z=3 can never be covered)
      3. Three-face corner premium   (4 most valuable cells)
      4. Interior-waste penalty       (don't bury own colour inside)
      5. Future-enablement bonus      (z=2 supporting a good z=3)
      6. Opponent top-layer penalty   (avoid gifting permanent opp points)
      7. Block-type efficiency        (save rare pure-colour blocks for exteriors)

    Uses biased sampling so that moves using high-value block types are
    always evaluated first.
    """

    MAX_CANDIDATES = 150

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        faces = 0
        if x == 0 or x == 3:
            faces += 1
        if y == 0 or y == 3:
            faces += 1
        if z == 3:
            faces += 1          # top face (bottom is not scored)
        return faces

    # ---- smart sampling -------------------------------------------------

    def _smart_sample(self, legal_moves: list, my_color: Color) -> list:
        """
        When there are more legal moves than MAX_CANDIDATES, return a biased
        sample that always includes every move using pure own-colour blocks
        and fills the remaining budget from lower tiers.

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

        result = list(tiers[0])                       # always keep tier-1
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

    # ---- evaluation -----------------------------------------------------

    def _evaluate_move(self, move, game_state: 'GameState',
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
                    score -= 3          # wasting own colour
                elif color == opp_color:
                    score += 1          # burying opponent colour

        # --- Component 5: future enablement bonus (weight 2) -------------
        for pos, _color, _faces in cell_info:
            x, y, z = pos
            if z == 2:                  # directly below z=3
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
                score += 4              # excellent use of rare pure block
            elif total_faces <= 1:
                score -= 5              # terrible — save it for later

        return score

    # ---- main entry point -----------------------------------------------

    def choose_move(self, game_state: 'GameState',
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


class StrategicAIStrategy(Strategy):
    """
    Advanced strategy that addresses 7 identified weaknesses from human game
    analysis.  Uses a two-phase hybrid approach:

    Phase 1 (early/mid game) — Enhanced O(1) analytical evaluation with 12
    components (up from AntiRandomStrategy's 7), covering stacking-constraint
    awareness, BW burial, face-coverage breadth, opponent-block orientation,
    and edge-column racing.

    Phase 2 (endgame, ≤12 blocks remaining) — Alpha-beta minimax at adaptive
    depth 2-4, using the analytical evaluator for move ordering and leaf
    scoring.  This detects forced WR-flood sequences that skilled players
    exploit.

    Weaknesses addressed:
      W1  No endgame lookahead          → minimax search
      W2  BR addiction / safe-move bias  → aggression bonus, 6-tier sampling
      W3  Failure to contest z=3         → doubled top-layer weights
      W4  No stacking-constraint weapon  → constraint propagation component
      W5  Corner fixation vs face breadth→ reduced corner premium, face coverage
      W6  No counter to BW burial        → burial detection + edge disruption
      W7  WR allocation backwards        → opponent-block orientation component
    """

    ENDGAME_THRESHOLD = 12
    MAX_CANDIDATES = 150

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _exterior_faces(x: int, y: int, z: int) -> int:
        """Count how many of the 5 scored exterior faces this cell touches."""
        faces = 0
        if x == 0 or x == 3:
            faces += 1
        if y == 0 or y == 3:
            faces += 1
        if z == 3:
            faces += 1
        return faces

    # ---- face-count cache (per turn) ------------------------------------

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

    # ---- 6-tier smart sampling ------------------------------------------

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

    # ---- 12-component analytical evaluator ------------------------------

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
            # Aggression bonus: pure own-colour on good exterior positions
            if total_faces >= 3:
                score += 4

        # Extra opp-colour penalty on opponent-benefiting blocks
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
                        # My colour at z=2 → z=3 CANNOT be my colour → terrible
                        score -= 8
                    elif color == opp_color:
                        # Opp at z=2 → z=3 cannot be opp → good for me
                        score += 4
                    elif color == Color.RED:
                        score += 1
            # Milder check for z=1 cascade
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
                    score += 5      # opp colour buried interior
                elif color == Color.RED and faces >= 2:
                    score += 3      # red on exterior (neutral)
                elif color == opp_color and faces >= 2:
                    score -= 5      # opp colour on multi-face exterior

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

    # ---- minimax with alpha-beta pruning --------------------------------

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

    # ---- main entry point -----------------------------------------------

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


class MixedStrategy(Strategy):
    """Combines multiple strategies with weighted probabilities"""

    def __init__(self, strategies: List[Tuple[Strategy, float]]):
        """
        strategies: List of (strategy, weight) tuples
        Weights don't need to sum to 1, they'll be normalized
        """
        self.strategies = strategies
        total_weight = sum(w for _, w in strategies)
        self.normalized_weights = [(s, w/total_weight) for s, w in strategies]

    def choose_move(self, game_state: GameState, player: Player) -> Optional[Tuple[Block, Tuple[int, int, int], str, bool]]:
        # Choose a strategy based on weights
        rand = random.random()
        cumulative = 0
        for strategy, weight in self.normalized_weights:
            cumulative += weight
            if rand < cumulative:
                return strategy.choose_move(game_state, player)

        # Fallback to last strategy
        return self.normalized_weights[-1][0].choose_move(game_state, player)


def validate_game(num_games: int = 100, verbose: bool = True) -> bool:
    """
    Plays random games and validates every move and final state against
    all game rules. Use this to verify the simulation is correct.
    Returns True if all games pass validation.
    """
    all_passed = True

    for game_num in range(num_games):
        game = GameState()
        strat = RandomStrategy()
        move_num = 0
        errors = []

        while not game.is_game_over():
            move = strat.choose_move(game, game.current_player)
            if move is None:
                break

            block, position, orientation, flip = move
            placed = PlacedBlock(block, position, orientation, flip)
            occupied = placed.get_occupied_positions()
            occupied_set = set(occupied)
            move_num += 1

            # --- Rule 1: Within bounds ---
            for px, py, pz in occupied:
                if not (0 <= px < 4 and 0 <= py < 4 and 0 <= pz < 4):
                    errors.append(f"Move {move_num}: Out of bounds at {(px,py,pz)}")

            # --- Rule 2: Not overlapping ---
            for pos in occupied:
                if pos in game.grid:
                    errors.append(f"Move {move_num}: Overlap at {pos}")

            # --- Rule 3: Support (no cantilevering) ---
            for px, py, pz in occupied:
                if pz == 0:
                    continue
                below = (px, py, pz - 1)
                if below not in game.grid and below not in occupied_set:
                    errors.append(f"Move {move_num}: No support at {(px,py,pz)}"
                                  f" (below {below} not in grid or block)")

            # --- Rule 4: Color stacking ---
            for px, py, pz in occupied:
                if pz > 0:
                    below_pos = (px, py, pz - 1)
                    if below_pos in game.grid:
                        color_above = placed.get_color_at_position((px, py, pz))
                        color_below = game.grid[below_pos].get_color_at_position(below_pos)
                        if color_above != Color.RED and color_above == color_below:
                            errors.append(
                                f"Move {move_num}: Same-color stack at {(px,py,pz)}"
                                f" ({color_above.name} on {color_below.name})")

            # --- Rule 5: Orientation produces exactly 2 positions ---
            if len(occupied) != 2:
                errors.append(f"Move {move_num}: Block occupies {len(occupied)} cells"
                              f" (expected 2)")

            # --- Rule 6: Orientations cover all 3 axes ---
            # (checked implicitly by move generation, but verify)
            if orientation not in ('x', 'y', 'z'):
                errors.append(f"Move {move_num}: Invalid orientation '{orientation}'")

            game.make_move(*move)

        # --- Post-game validation ---
        # Check no two blocks overlap in final grid
        positions_seen = set()
        for pos in game.grid:
            if pos in positions_seen:
                errors.append(f"Final state: Duplicate position {pos} in grid")
            positions_seen.add(pos)

        # Check all occupied positions have valid z-support chain
        for pos in game.grid:
            px, py, pz = pos
            for z_check in range(1, pz + 1):
                if (px, py, z_check - 1) not in game.grid:
                    errors.append(f"Final state: {pos} has gap in support at z={z_check-1}")
                    break

        # Count orientation usage
        orientations_used = set()
        for _, placed_block in game.move_history:
            orientations_used.add(placed_block.orientation)

        if errors:
            all_passed = False
            if verbose:
                print(f"Game {game_num + 1}: FAILED ({len(errors)} errors)")
                for e in errors[:10]:
                    print(f"  ✗ {e}")
        elif verbose and game_num < 3:
            # Show details for first few passing games
            print(f"Game {game_num + 1}: PASSED — {move_num} moves, "
                  f"orientations used: {orientations_used}, "
                  f"score: {game.calculate_score()}")

    if verbose:
        print(f"\nValidation: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}"
              f" ({num_games} games)")

    return all_passed


@dataclass
class GameRecord:
    """Detailed record of a single game for meta analysis"""
    white_score: int
    black_score: int
    num_moves: int
    winner: str  # 'white', 'black', or 'tie'
    score_diff: int  # white_score - black_score
    opening_move: Optional[Tuple] = None  # (block_repr, position, orientation, flip)
    white_blocks_used: Optional[List[str]] = None  # block type strings
    black_blocks_used: Optional[List[str]] = None
    score_progression: Optional[List[Tuple[int, int]]] = None  # (white, black) after each move


def play_game(white_strategy: Strategy, black_strategy: Strategy,
              verbose: bool = False, detailed: bool = False,
              open_grid: bool = False) -> GameRecord:
    """
    Play a single game with given strategies.
    Returns a GameRecord with scores, move count, and optionally detailed tracking.
    When open_grid=True, uses OpenGridGameState with dynamic X/Y boundaries.
    """
    game = OpenGridGameState() if open_grid else GameState()
    num_moves = 0
    opening_move = None
    white_blocks = []
    black_blocks = []
    score_progression = [] if detailed else None

    while not game.is_game_over():
        current_strategy = white_strategy if game.current_player == Player.WHITE else black_strategy
        current_player = game.current_player
        move = current_strategy.choose_move(game, current_player)

        if move is None:
            break

        block, position, orientation, flip = move

        # Track block usage per player
        if detailed:
            block_type = repr(block)
            if current_player == Player.WHITE:
                white_blocks.append(block_type)
            else:
                black_blocks.append(block_type)

        # Track opening move
        if num_moves == 0:
            opening_move = (repr(block), position, orientation, flip)

        game.make_move(*move)
        num_moves += 1

        # Track score after each move
        if detailed:
            w, b = game.calculate_score()
            score_progression.append((w, b))

        if verbose:
            print(f"Move {num_moves}: {game.current_player.name} placed {move[0]}")

    white_score, black_score = game.calculate_score()

    if white_score > black_score:
        winner = 'white'
    elif black_score > white_score:
        winner = 'black'
    else:
        winner = 'tie'

    if verbose:
        print(f"\nGame Over!")
        print(f"White: {white_score}, Black: {black_score}")
        print(f"Winner: {winner.capitalize()}")
        print(f"Total moves: {num_moves}")

    return GameRecord(
        white_score=white_score,
        black_score=black_score,
        num_moves=num_moves,
        winner=winner,
        score_diff=white_score - black_score,
        opening_move=opening_move,
        white_blocks_used=white_blocks if detailed else None,
        black_blocks_used=black_blocks if detailed else None,
        score_progression=score_progression,
    )


def run_monte_carlo(white_strategy: Strategy, black_strategy: Strategy,
                    num_games: int = 1000, verbose: bool = False,
                    detailed: bool = False, open_grid: bool = False) -> dict:
    """
    Run Monte Carlo simulation with given strategies.
    Returns statistics dictionary. When detailed=True, also collects
    block usage, opening moves, score progressions, and per-game records.
    When open_grid=True, uses OpenGridGameState with dynamic X/Y boundaries.
    """
    results = {
        'white_wins': 0,
        'black_wins': 0,
        'ties': 0,
        'white_scores': [],
        'black_scores': [],
        'num_moves': [],
        'score_differences': [],
        'records': [],  # full GameRecord list for deep analysis
    }

    for i in range(num_games):
        if verbose and (i+1) % 100 == 0:
            print(f"Completed {i+1}/{num_games} games...")

        record = play_game(white_strategy, black_strategy,
                           verbose=False, detailed=detailed,
                           open_grid=open_grid)

        results['white_scores'].append(record.white_score)
        results['black_scores'].append(record.black_score)
        results['num_moves'].append(record.num_moves)
        results['score_differences'].append(record.score_diff)
        results['records'].append(record)

        if record.winner == 'white':
            results['white_wins'] += 1
        elif record.winner == 'black':
            results['black_wins'] += 1
        else:
            results['ties'] += 1

    # Calculate statistics
    results['white_win_rate'] = results['white_wins'] / num_games
    results['black_win_rate'] = results['black_wins'] / num_games
    results['tie_rate'] = results['ties'] / num_games
    results['avg_white_score'] = np.mean(results['white_scores'])
    results['avg_black_score'] = np.mean(results['black_scores'])
    results['avg_moves'] = np.mean(results['num_moves'])
    results['avg_score_diff'] = np.mean(results['score_differences'])
    results['std_score_diff'] = np.std(results['score_differences'])

    return results


def print_results(results: dict, white_name: str, black_name: str):
    """Pretty print Monte Carlo results"""
    print("\n" + "="*60)
    print(f"Monte Carlo Simulation Results")
    print(f"White Strategy: {white_name}")
    print(f"Black Strategy: {black_name}")
    print("="*60)
    print(f"\nWin Rates:")
    print(f"  White: {results['white_win_rate']*100:.1f}% ({results['white_wins']} wins)")
    print(f"  Black: {results['black_win_rate']*100:.1f}% ({results['black_wins']} wins)")
    print(f"  Ties:  {results['tie_rate']*100:.1f}% ({results['ties']} ties)")
    print(f"\nAverage Scores:")
    print(f"  White: {results['avg_white_score']:.2f}")
    print(f"  Black: {results['avg_black_score']:.2f}")
    print(f"  Score Difference: {results['avg_score_diff']:.2f} ± {results['std_score_diff']:.2f}")
    print(f"\nAverage Game Length: {results['avg_moves']:.1f} moves")
    print("="*60 + "\n")


# ============================================================
# META ANALYSIS FUNCTIONS
# ============================================================

def analyze_first_player_advantage(strategies: dict, num_games: int = 500,
                                   verbose: bool = True) -> dict:
    """
    Analysis 1: Seat-swapped matchups.
    Runs every strategy pair as both (A vs B) and (B vs A) to isolate
    first-player advantage from strategy strength.

    Analysis 2: Mirror matches.
    Runs every strategy against itself. In a balanced game, mirror matches
    should converge toward 50/50. Consistent White wins = first-player advantage.

    Returns a summary dict with all results.
    """
    strat_names = list(strategies.keys())
    summary = {
        'seat_swap': {},
        'mirror': {},
    }

    # --- Mirror matches ---
    print("\n" + "="*60)
    print("MIRROR MATCH ANALYSIS (First-Player Advantage)")
    print("="*60)
    print("Each strategy plays against itself. In a balanced game,")
    print("White (first player) and Black should win ~50% each.\n")

    mirror_totals = {'white_wins': 0, 'black_wins': 0, 'ties': 0, 'games': 0}

    for name in strat_names:
        if verbose:
            print(f"  Running {name} vs {name} ({num_games} games)...", end=" ", flush=True)
        results = run_monte_carlo(strategies[name], strategies[name],
                                  num_games, verbose=False)
        summary['mirror'][name] = results
        mirror_totals['white_wins'] += results['white_wins']
        mirror_totals['black_wins'] += results['black_wins']
        mirror_totals['ties'] += results['ties']
        mirror_totals['games'] += num_games

        w_pct = results['white_win_rate'] * 100
        b_pct = results['black_win_rate'] * 100
        t_pct = results['tie_rate'] * 100
        if verbose:
            print(f"White {w_pct:.1f}% | Black {b_pct:.1f}% | Tie {t_pct:.1f}%")

    # Aggregate mirror result
    total = mirror_totals['games']
    agg_w = mirror_totals['white_wins'] / total * 100
    agg_b = mirror_totals['black_wins'] / total * 100
    agg_t = mirror_totals['ties'] / total * 100
    print(f"\n  AGGREGATE across all mirror matches ({total} games):")
    print(f"    White (1st): {agg_w:.1f}%  |  Black (2nd): {agg_b:.1f}%  |  Tie: {agg_t:.1f}%")

    if agg_w > 55:
        print("    ⚠  SIGNIFICANT first-player advantage detected!")
    elif agg_b > 55:
        print("    ⚠  SIGNIFICANT second-player advantage detected!")
    else:
        print("    ✓  No strong first-player advantage detected.")

    # --- Seat-swapped matchups ---
    print("\n" + "="*60)
    print("SEAT-SWAP ANALYSIS")
    print("="*60)
    print("Each pair is tested in both seat orders to separate")
    print("strategy strength from seat advantage.\n")

    for i, name_a in enumerate(strat_names):
        for name_b in strat_names[i+1:]:
            if verbose:
                print(f"  {name_a} vs {name_b}:", flush=True)

            # A as White, B as Black
            if verbose:
                print(f"    Seat 1: {name_a}(W) vs {name_b}(B)...", end=" ", flush=True)
            r_ab = run_monte_carlo(strategies[name_a], strategies[name_b],
                                   num_games, verbose=False)
            if verbose:
                print(f"W:{r_ab['white_win_rate']*100:.1f}% B:{r_ab['black_win_rate']*100:.1f}%")

            # B as White, A as Black
            if verbose:
                print(f"    Seat 2: {name_b}(W) vs {name_a}(B)...", end=" ", flush=True)
            r_ba = run_monte_carlo(strategies[name_b], strategies[name_a],
                                   num_games, verbose=False)
            if verbose:
                print(f"W:{r_ba['white_win_rate']*100:.1f}% B:{r_ba['black_win_rate']*100:.1f}%")

            # Combine: how often does strategy A win regardless of seat?
            a_wins = r_ab['white_wins'] + r_ba['black_wins']
            b_wins = r_ab['black_wins'] + r_ba['white_wins']
            ties = r_ab['ties'] + r_ba['ties']
            total_pair = num_games * 2
            a_pct = a_wins / total_pair * 100
            b_pct = b_wins / total_pair * 100

            # Seat advantage: how much did White win across both orderings?
            white_total = r_ab['white_wins'] + r_ba['white_wins']
            white_pct = white_total / total_pair * 100

            if verbose:
                print(f"    → {name_a} wins {a_pct:.1f}%, {name_b} wins {b_pct:.1f}%"
                      f" (seat-neutral)")
                print(f"    → White (1st player) won {white_pct:.1f}% across both orderings")

            summary['seat_swap'][(name_a, name_b)] = {
                'a_as_white': r_ab,
                'b_as_white': r_ba,
                'a_win_pct': a_pct,
                'b_win_pct': b_pct,
                'first_player_win_pct': white_pct,
            }

    return summary


def analyze_block_usage(strategies: dict, num_games: int = 200,
                        verbose: bool = True) -> dict:
    """
    Analysis 3: Block pool composition.
    Tracks which block types each player uses and whether winners
    disproportionately claim certain block types.
    """
    print("\n" + "="*60)
    print("BLOCK USAGE ANALYSIS")
    print("="*60)
    print("Tracks which block types winners vs losers draft.\n")

    strat_names = list(strategies.keys())
    # Mirror matches (equal skill isolates block effects) + cross-skill pairs
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))  # mirror matches
    # Add a few cross-skill pairs if they exist
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    if 'edge_control' in strategies and 'greedy' in strategies:
        test_pairs.append(('edge_control', 'greedy'))
    # Deduplicate
    test_pairs = list(dict.fromkeys(test_pairs))

    all_usage = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games)...", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False, detailed=True)

        winner_blocks = defaultdict(int)
        loser_blocks = defaultdict(int)
        tie_blocks = defaultdict(int)

        for record in results['records']:
            w_blocks = record.white_blocks_used or []
            b_blocks = record.black_blocks_used or []

            if record.winner == 'white':
                for bt in w_blocks:
                    winner_blocks[bt] += 1
                for bt in b_blocks:
                    loser_blocks[bt] += 1
            elif record.winner == 'black':
                for bt in b_blocks:
                    winner_blocks[bt] += 1
                for bt in w_blocks:
                    loser_blocks[bt] += 1
            else:
                for bt in w_blocks + b_blocks:
                    tie_blocks[bt] += 1

        # Compute usage rates
        all_block_types = sorted(set(list(winner_blocks.keys()) +
                                     list(loser_blocks.keys()) +
                                     list(tie_blocks.keys())))

        total_winner = sum(winner_blocks.values()) or 1
        total_loser = sum(loser_blocks.values()) or 1

        key = f"{w_name}_vs_{b_name}"
        all_usage[key] = {}

        if verbose:
            print(f"    {'Block Type':<15} {'Winner %':>10} {'Loser %':>10} {'Diff':>10}")
            print(f"    {'-'*45}")

        for bt in all_block_types:
            w_pct = winner_blocks[bt] / total_winner * 100
            l_pct = loser_blocks[bt] / total_loser * 100
            diff = w_pct - l_pct
            all_usage[key][bt] = {'winner_pct': w_pct, 'loser_pct': l_pct, 'diff': diff}
            if verbose:
                flag = " ◄" if abs(diff) > 3.0 else ""
                print(f"    {bt:<15} {w_pct:>9.1f}% {l_pct:>9.1f}% {diff:>+9.1f}%{flag}")

        if verbose:
            print()

    return all_usage


def analyze_opening_moves(strategies: dict, num_games: int = 500,
                          verbose: bool = True) -> dict:
    """
    Analysis 4: Opening move dominance.
    Checks whether certain first-move positions/blocks correlate with winning.
    """
    print("\n" + "="*60)
    print("OPENING MOVE DOMINANCE ANALYSIS")
    print("="*60)
    print("Do certain opening moves correlate with winning?\n")

    strat_names = list(strategies.keys())
    # Mirror matches to isolate opening effects, plus cross-skill pairs
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_openings = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games)...", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False, detailed=True)

        # Group by opening move
        opening_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0})

        for record in results['records']:
            if record.opening_move is None:
                continue
            # Key by position + orientation (block type varies)
            block_repr, pos, orient, flip = record.opening_move
            key = (block_repr, pos, orient, flip)

            if record.winner == 'white':
                opening_stats[key]['wins'] += 1
            elif record.winner == 'black':
                opening_stats[key]['losses'] += 1
            else:
                opening_stats[key]['ties'] += 1

        # Sort by frequency
        sorted_openings = sorted(opening_stats.items(),
                                 key=lambda x: sum(x[1].values()), reverse=True)

        pair_key = f"{w_name}_vs_{b_name}"
        all_openings[pair_key] = sorted_openings

        if verbose:
            print(f"    {'Opening Move':<40} {'Count':>6} {'Win%':>7} {'Loss%':>7}")
            print(f"    {'-'*60}")
            for opening, stats in sorted_openings[:10]:  # Top 10
                total = stats['wins'] + stats['losses'] + stats['ties']
                if total < 5:
                    continue  # Skip rare openings
                w_pct = stats['wins'] / total * 100
                l_pct = stats['losses'] / total * 100
                block_repr, pos, orient, flip = opening
                label = f"{block_repr} @{pos} {orient} {'F' if flip else 'N'}"
                flag = " ◄ dominant" if w_pct > 70 and total > 20 else ""
                print(f"    {label:<40} {total:>6} {w_pct:>6.1f}% {l_pct:>6.1f}%{flag}")
            print()

    return all_openings


def analyze_score_distribution(strategies: dict, num_games: int = 500,
                               verbose: bool = True) -> dict:
    """
    Analysis 5: Score margin distribution.
    Shows percentiles and a text histogram of score differences.
    """
    print("\n" + "="*60)
    print("SCORE MARGIN DISTRIBUTION ANALYSIS")
    print("="*60)
    print("How are victory margins distributed? (positive = White wins)\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    # Cross-skill pairs
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    if 'edge_control' in strategies and 'greedy' in strategies:
        test_pairs.append(('edge_control', 'greedy'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_distributions = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games):", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False)

        diffs = np.array(results['score_differences'])
        percentiles = {
            '5th': np.percentile(diffs, 5),
            '25th': np.percentile(diffs, 25),
            'median': np.median(diffs),
            '75th': np.percentile(diffs, 75),
            '95th': np.percentile(diffs, 95),
        }
        all_distributions[f"{w_name}_vs_{b_name}"] = {
            'percentiles': percentiles,
            'mean': float(np.mean(diffs)),
            'std': float(np.std(diffs)),
            'min': int(np.min(diffs)),
            'max': int(np.max(diffs)),
        }

        if verbose:
            print(f"    Mean: {np.mean(diffs):+.1f}  Std: {np.std(diffs):.1f}"
                  f"  Range: [{np.min(diffs)}, {np.max(diffs)}]")
            print(f"    Percentiles:  5th={percentiles['5th']:+.0f}"
                  f"  25th={percentiles['25th']:+.0f}"
                  f"  50th={percentiles['median']:+.0f}"
                  f"  75th={percentiles['75th']:+.0f}"
                  f"  95th={percentiles['95th']:+.0f}")

            # Text histogram
            bin_min = int(np.min(diffs)) - 1
            bin_max = int(np.max(diffs)) + 2
            hist, bin_edges = np.histogram(diffs, bins=range(bin_min, bin_max))
            max_count = max(hist) if max(hist) > 0 else 1
            bar_width = 40

            print(f"    Distribution:")
            for j, count in enumerate(hist):
                if count == 0:
                    continue
                bar_len = int(count / max_count * bar_width)
                margin = int(bin_edges[j])
                print(f"      {margin:>+4d} | {'█' * bar_len} {count}")
            print()

    return all_distributions


def analyze_game_length_correlation(strategies: dict, num_games: int = 500,
                                    verbose: bool = True) -> dict:
    """
    Analysis 6: Game-length vs winner correlation.
    Do shorter or longer games systematically favor one side?
    """
    print("\n" + "="*60)
    print("GAME LENGTH vs WINNER CORRELATION")
    print("="*60)
    print("Does game length predict who wins?\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_correlations = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games):", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False)

        records = results['records']

        # Bin games by length
        length_bins = defaultdict(lambda: {'white': 0, 'black': 0, 'tie': 0})
        for record in records:
            # Bin into groups of 3 moves
            length_bin = (record.num_moves // 3) * 3
            length_bins[length_bin][record.winner] += 1

        # Compute correlation between game length and score diff
        lengths = np.array([r.num_moves for r in records])
        diffs = np.array([r.score_diff for r in records])
        if np.std(lengths) > 0 and np.std(diffs) > 0:
            correlation = np.corrcoef(lengths, diffs)[0, 1]
        else:
            correlation = 0.0

        # Average lengths for each outcome
        white_win_lengths = [r.num_moves for r in records if r.winner == 'white']
        black_win_lengths = [r.num_moves for r in records if r.winner == 'black']
        tie_lengths = [r.num_moves for r in records if r.winner == 'tie']

        pair_key = f"{w_name}_vs_{b_name}"
        all_correlations[pair_key] = {
            'correlation': correlation,
            'avg_length_white_wins': np.mean(white_win_lengths) if white_win_lengths else 0,
            'avg_length_black_wins': np.mean(black_win_lengths) if black_win_lengths else 0,
            'avg_length_ties': np.mean(tie_lengths) if tie_lengths else 0,
        }

        if verbose:
            print(f"    Length-ScoreDiff correlation: {correlation:+.3f}", end="")
            if abs(correlation) > 0.3:
                direction = "longer→White" if correlation > 0 else "longer→Black"
                print(f"  ⚠  ({direction})")
            else:
                print(f"  (weak)")

            if white_win_lengths:
                print(f"    Avg length when White wins: {np.mean(white_win_lengths):.1f}")
            if black_win_lengths:
                print(f"    Avg length when Black wins: {np.mean(black_win_lengths):.1f}")
            if tie_lengths:
                print(f"    Avg length when Tie:        {np.mean(tie_lengths):.1f}")

            # Show binned breakdown
            print(f"    {'Moves':<8} {'White%':>8} {'Black%':>8} {'Tie%':>8} {'Count':>8}")
            print(f"    {'-'*40}")
            for length_bin in sorted(length_bins.keys()):
                stats = length_bins[length_bin]
                total = stats['white'] + stats['black'] + stats['tie']
                if total < 5:
                    continue
                print(f"    {length_bin:>3}-{length_bin+2:<3}"
                      f" {stats['white']/total*100:>7.1f}%"
                      f" {stats['black']/total*100:>7.1f}%"
                      f" {stats['tie']/total*100:>7.1f}%"
                      f" {total:>7}")
            print()

    return all_correlations


def run_meta_analysis(num_games: int = 500):
    """
    Master function that runs all 6 meta analyses and prints a final verdict.
    """
    print("="*60)
    print("4x4x4 Block Stacking Game — FULL META ANALYSIS")
    print("="*60)
    print(f"Running {num_games} games per test.\n")

    strategies = {
        'random': RandomStrategy(),
        'strategic': StrategicAIStrategy(),
        #'greedy': GreedyStrategy(),
        # 'defensive': DefensiveStrategy(),       # slow — calls get_legal_moves() per candidate
        # 'edge_control': EdgeControlStrategy(),   # slow — evaluates ALL legal moves (no sampling cap)
        # 'block_opponent': BlockOpponentStrategy(),  # slow — multi-component eval with state copies
    }

    import time
    t0 = time.time()

    # Analysis 1 & 2: First-player advantage (seat-swap + mirror)
    fpa_results = analyze_first_player_advantage(strategies, num_games)

    # Analysis 3: Block pool composition
    block_results = analyze_block_usage(strategies, num_games=min(num_games, 200))

    # Analysis 4: Opening move dominance
    opening_results = analyze_opening_moves(strategies, num_games)

    # Analysis 5: Score margin distribution
    dist_results = analyze_score_distribution(strategies, num_games)

    # Analysis 6: Game-length correlation
    length_results = analyze_game_length_correlation(strategies, num_games)

    elapsed = time.time() - t0

    # === FINAL VERDICT ===
    print("\n" + "="*60)
    print("FINAL META ANALYSIS VERDICT")
    print("="*60)

    # Aggregate first-player advantage from mirror matches
    mirror = fpa_results['mirror']
    total_w = sum(r['white_wins'] for r in mirror.values())
    total_b = sum(r['black_wins'] for r in mirror.values())
    total_t = sum(r['ties'] for r in mirror.values())
    total_g = total_w + total_b + total_t
    w_rate = total_w / total_g * 100

    print(f"\n  1. FIRST-PLAYER ADVANTAGE (mirror matches):")
    print(f"     White (1st) wins: {w_rate:.1f}% across {total_g} mirror games")
    if w_rate > 55:
        print(f"     → BROKEN: Going first is a significant advantage.")
    elif w_rate < 45:
        print(f"     → BROKEN: Going second is a significant advantage.")
    else:
        print(f"     → BALANCED: No significant first-player advantage.")

    # Aggregate seat-swap: average first-player win %
    swap = fpa_results['seat_swap']
    if swap:
        avg_fp = np.mean([v['first_player_win_pct'] for v in swap.values()])
        print(f"\n  2. SEAT-SWAP CONSISTENCY:")
        print(f"     Average White (1st) win rate across swapped pairs: {avg_fp:.1f}%")
        if avg_fp > 55:
            print(f"     → First-mover advantage persists even when strategies swap seats.")
        elif avg_fp < 45:
            print(f"     → Second-mover advantage persists across strategy swaps.")
        else:
            print(f"     → Seat position does not dominate strategy skill.")

    # Block pool
    print(f"\n  3. BLOCK POOL:")
    has_block_bias = False
    for matchup, usage in block_results.items():
        for bt, stats in usage.items():
            if abs(stats['diff']) > 5.0:
                if not has_block_bias:
                    print(f"     Significant block draft biases detected:")
                    has_block_bias = True
                print(f"       {bt} in {matchup}: winner uses {stats['diff']:+.1f}% more")
    if not has_block_bias:
        print(f"     No significant block draft advantage detected.")

    # Opening moves
    print(f"\n  4. OPENING MOVES:")
    has_dominant = False
    for matchup, openings in opening_results.items():
        for opening, stats in openings:
            total = stats['wins'] + stats['losses'] + stats['ties']
            if total >= 20 and stats['wins'] / total > 0.70:
                if not has_dominant:
                    print(f"     Dominant openings found:")
                    has_dominant = True
                block_repr, pos, orient, flip = opening
                wr = stats['wins'] / total * 100
                print(f"       {block_repr} @{pos} {orient} → {wr:.0f}% win rate"
                      f" ({total} games) in {matchup}")
    if not has_dominant:
        print(f"     No single opening move dominates.")

    # Score distribution
    print(f"\n  5. SCORE DISTRIBUTION:")
    for matchup, dist in dist_results.items():
        spread = dist['std']
        skew_dir = "White" if dist['mean'] > 1 else "Black" if dist['mean'] < -1 else "neutral"
        print(f"     {matchup}: mean {dist['mean']:+.1f}, std {spread:.1f}, "
              f"range [{dist['min']},{dist['max']}] → {skew_dir}")

    # Game length correlation
    print(f"\n  6. GAME LENGTH CORRELATION:")
    for matchup, corr in length_results.items():
        r = corr['correlation']
        strength = "strong" if abs(r) > 0.3 else "moderate" if abs(r) > 0.15 else "weak"
        direction = "longer→White" if r > 0 else "longer→Black"
        print(f"     {matchup}: r={r:+.3f} ({strength}, {direction})")

    print(f"\n  Total analysis time: {elapsed:.1f}s")
    print("="*60)

    return {
        'first_player': fpa_results,
        'block_usage': block_results,
        'opening_moves': opening_results,
        'score_distribution': dist_results,
        'game_length': length_results,
    }


def main():
    """Main function — runs the full meta analysis suite"""
    run_meta_analysis(num_games=500)


if __name__ == "__main__":
    main()
