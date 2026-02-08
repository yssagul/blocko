#!/usr/bin/env python3
"""
Backward-compatibility shim for the original monolithic module.

All game engine code now lives in the ``blocko`` package::

    blocko.core          — models, GameState, OpenGridGameState
    blocko.strategies    — 8 AI strategies
    blocko.simulation    — play_game, run_monte_carlo, validate_game
    blocko.analysis      — meta-analysis suite

This file re-exports every public name so that existing scripts such as
``server.py`` and ``random_draft_sim.py`` continue to work unmodified via::

    from block_game_simulation import GameState, StrategicAIStrategy, ...

New code should import directly from ``blocko.*`` instead.
"""

# ── Core ──────────────────────────────────────────────────────────────────
from blocko.core.models import Color, Player, Block, PlacedBlock, exterior_faces
from blocko.core.game_state import GameState
from blocko.core.open_grid import OpenGridGameState

# ── Strategies ────────────────────────────────────────────────────────────
from blocko.strategies.base import Strategy
from blocko.strategies.random import RandomStrategy
from blocko.strategies.greedy import GreedyStrategy
from blocko.strategies.defensive import DefensiveStrategy
from blocko.strategies.edge_control import EdgeControlStrategy
from blocko.strategies.blocking import BlockOpponentStrategy
from blocko.strategies.analytical import AntiRandomStrategy
from blocko.strategies.strategic import StrategicAIStrategy
from blocko.strategies.mixed import MixedStrategy

# ── Simulation ────────────────────────────────────────────────────────────
from blocko.simulation.game_record import GameRecord
from blocko.simulation.runner import play_game, run_monte_carlo, print_results
from blocko.simulation.validator import validate_game

# ── Analysis ──────────────────────────────────────────────────────────────
from blocko.analysis.meta import (
    analyze_first_player_advantage,
    analyze_block_usage,
    analyze_opening_moves,
    analyze_score_distribution,
    analyze_game_length_correlation,
    run_meta_analysis,
)


def main():
    """Main function — runs the full meta analysis suite."""
    run_meta_analysis(num_games=500)


if __name__ == "__main__":
    main()
