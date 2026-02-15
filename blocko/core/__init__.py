"""
blocko.core — Game engine fundamentals.

Re-exports the core types and game states so that downstream code can write::

    from blocko.core import GameState, Color, Player, Block
"""

from blocko.core.models import Color, Player, Block, PlacedBlock, exterior_faces
from blocko.core.game_state import GameState
from blocko.core.open_grid import OpenGridGameState
from blocko.core.random_draw import RandomDrawGameState, RandomDrawOpenGridGameState

__all__ = [
    "Color",
    "Player",
    "Block",
    "PlacedBlock",
    "exterior_faces",
    "GameState",
    "OpenGridGameState",
    "RandomDrawGameState",
    "RandomDrawOpenGridGameState",
]
