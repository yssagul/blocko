"""
Game record dataclass for storing simulation results.

Each :class:`GameRecord` captures the outcome and (optionally) detailed
per-move tracking for a single completed game.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class GameRecord:
    """
    Detailed record of a single completed game.

    Attributes:
        white_score: Final white point total.
        black_score: Final black point total.
        num_moves: Total number of moves played.
        winner: ``'white'``, ``'black'``, or ``'tie'``.
        score_diff: ``white_score - black_score``.
        opening_move: Tuple (block_repr, position, orientation, flip) of the
            first move, or None.
        white_blocks_used: List of block type strings used by White
            (only when ``detailed=True``).
        black_blocks_used: List of block type strings used by Black
            (only when ``detailed=True``).
        score_progression: List of (white, black) score snapshots after each
            move (only when ``detailed=True``).
    """
    white_score: int
    black_score: int
    num_moves: int
    winner: str  # 'white', 'black', or 'tie'
    score_diff: int  # white_score - black_score
    opening_move: Optional[Tuple] = None
    white_blocks_used: Optional[List[str]] = None
    black_blocks_used: Optional[List[str]] = None
    score_progression: Optional[List[Tuple[int, int]]] = None
