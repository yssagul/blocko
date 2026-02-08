"""
Blocko — 4×4×4 Block Stacking Strategy Game Engine
===================================================

A turn-based strategy game where two players compete to show the most of
their colour on the 5 scored exterior faces (top + 4 walls) of a 4×4×4 cube.

Quick start::

    from blocko.core import GameState, Color, Player
    from blocko.strategies import StrategicAIStrategy, RandomStrategy
    from blocko.simulation import play_game, run_monte_carlo

    result = play_game(RandomStrategy(), StrategicAIStrategy())
    print(f"Winner: {result.winner}")

Subpackages
-----------
- ``blocko.core``         — Game state, models, Open Grid variant.
- ``blocko.strategies``   — 8 AI strategies from random to minimax.
- ``blocko.simulation``   — Game runner, Monte Carlo harness, validator.
- ``blocko.analysis``     — Statistical meta-analysis suite.
"""

__version__ = "0.1.0"
