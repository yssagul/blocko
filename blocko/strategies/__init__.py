"""
blocko.strategies — AI strategies for the Blocko game.

Provides 8 strategies ranging from uniform random to a 12-component
analytical evaluator with minimax endgame search::

    from blocko.strategies import StrategicAIStrategy, RandomStrategy
"""

from blocko.strategies.base import Strategy
from blocko.strategies.random import RandomStrategy
from blocko.strategies.greedy import GreedyStrategy
from blocko.strategies.defensive import DefensiveStrategy
from blocko.strategies.edge_control import EdgeControlStrategy
from blocko.strategies.blocking import BlockOpponentStrategy
from blocko.strategies.analytical import AntiRandomStrategy
from blocko.strategies.strategic import StrategicAIStrategy
from blocko.strategies.mixed import MixedStrategy

__all__ = [
    "Strategy",
    "RandomStrategy",
    "GreedyStrategy",
    "DefensiveStrategy",
    "EdgeControlStrategy",
    "BlockOpponentStrategy",
    "AntiRandomStrategy",
    "StrategicAIStrategy",
    "MixedStrategy",
]
