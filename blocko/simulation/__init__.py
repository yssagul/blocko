"""
blocko.simulation — Game runner, Monte Carlo harness, and rule validator.

::

    from blocko.simulation import play_game, run_monte_carlo, validate_game
"""

from blocko.simulation.game_record import GameRecord
from blocko.simulation.runner import play_game, run_monte_carlo, print_results
from blocko.simulation.validator import validate_game

__all__ = [
    "GameRecord",
    "play_game",
    "run_monte_carlo",
    "print_results",
    "validate_game",
]
