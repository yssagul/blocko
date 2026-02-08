"""
Core data models for the Blocko game engine.

Defines the fundamental types used throughout the game:
- Color: The three cell colors (BLACK, WHITE, RED)
- Player: The two players (BLACK, WHITE)
- Block: A 1×1×2 game piece with two colored halves
- PlacedBlock: A block placed at a specific position and orientation

Also provides the shared ``exterior_faces()`` utility, which counts how
many of the 5 scored exterior faces (top + 4 walls) a cell touches.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class Color(Enum):
    """Represents the three cell colors in the game."""
    BLACK = 0
    WHITE = 1
    RED = 2


class Player(Enum):
    """Represents the two players."""
    BLACK = 0
    WHITE = 1


@dataclass
class Block:
    """
    A 1×1×2 game piece with two colored halves.

    Attributes:
        color1: Color of the first (lower/negative-axis) half.
        color2: Color of the second (upper/positive-axis) half.
        block_id: Unique identifier within the block pool.
    """
    color1: Color
    color2: Color
    block_id: int

    def is_uniform(self) -> bool:
        """Check if both halves are the same color."""
        return self.color1 == self.color2

    def __repr__(self):
        return f"Block({self.color1.name[0]}{self.color2.name[0]})"


@dataclass
class PlacedBlock:
    """
    A block placed in the 3-D game space.

    Attributes:
        block: The underlying Block piece.
        position: (x, y, z) coordinates of the first cell.
        orientation: Axis the block extends along ('x', 'y', or 'z').
        flip: If True, color1 and color2 are swapped relative to position.
    """
    block: Block
    position: Tuple[int, int, int]
    orientation: str  # 'x', 'y', or 'z'
    flip: bool

    def get_occupied_positions(self) -> List[Tuple[int, int, int]]:
        """Return the two (x, y, z) cells this block occupies."""
        x, y, z = self.position
        if self.orientation == 'x':
            return [(x, y, z), (x+1, y, z)]
        elif self.orientation == 'y':
            return [(x, y, z), (x, y+1, z)]
        else:  # z
            return [(x, y, z), (x, y, z+1)]

    def get_color_at_position(self, pos: Tuple[int, int, int]) -> Color:
        """Return the color at the given cell position."""
        positions = self.get_occupied_positions()
        if pos == positions[0]:
            return self.block.color1 if not self.flip else self.block.color2
        elif pos == positions[1]:
            return self.block.color2 if not self.flip else self.block.color1
        else:
            raise ValueError("Position not in this block")


def exterior_faces(x: int, y: int, z: int,
                   bounds: Tuple[int, int, int, int, int, int] = (0, 3, 0, 3, 0, 3)) -> int:
    """
    Count how many of the 5 scored exterior faces a cell touches.

    The 5 scored faces are the top face and 4 walls (left, right, front, back).
    The bottom face is never scored.  A corner cell can touch up to 3 faces;
    an edge cell up to 2; an interior-face cell exactly 1; a fully interior
    cell touches 0.

    Args:
        x, y, z: Cell coordinates.
        bounds: (x_min, x_max, y_min, y_max, z_min, z_max) of the play area.

    Returns:
        Number of scored exterior faces (0–3).
    """
    bx_min, bx_max, by_min, by_max, _bz_min, bz_max = bounds
    faces = 0
    if x == bx_min or x == bx_max:
        faces += 1
    if y == by_min or y == by_max:
        faces += 1
    if z == bz_max:
        faces += 1
    return faces
