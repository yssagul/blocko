"""
blocko.analysis — Statistical meta-analysis suite.

::

    from blocko.analysis import run_meta_analysis
"""

from blocko.analysis.meta import (
    analyze_first_player_advantage,
    analyze_block_usage,
    analyze_opening_moves,
    analyze_score_distribution,
    analyze_game_length_correlation,
    run_meta_analysis,
)

__all__ = [
    "analyze_first_player_advantage",
    "analyze_block_usage",
    "analyze_opening_moves",
    "analyze_score_distribution",
    "analyze_game_length_correlation",
    "run_meta_analysis",
]
