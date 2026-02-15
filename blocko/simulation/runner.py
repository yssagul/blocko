"""
Game runner and Monte Carlo simulation harness.

Provides:
  - :func:`play_game` — play a single game between two strategies.
  - :func:`run_monte_carlo` — run many games and collect aggregate stats.
  - :func:`print_results` — pretty-print a Monte Carlo results dict.
"""

import numpy as np

from blocko.core.models import Player
from blocko.core.game_state import GameState
from blocko.core.open_grid import OpenGridGameState
from blocko.core.random_draw import RandomDrawGameState, RandomDrawOpenGridGameState
from blocko.strategies.base import Strategy
from blocko.simulation.game_record import GameRecord


def _create_game(open_grid: bool = False, random_draw: bool = False) -> GameState:
    """Create the appropriate game state for the requested mode."""
    if random_draw and open_grid:
        return RandomDrawOpenGridGameState()
    elif random_draw:
        return RandomDrawGameState()
    elif open_grid:
        return OpenGridGameState()
    else:
        return GameState()


def play_game(white_strategy: Strategy, black_strategy: Strategy,
              verbose: bool = False, detailed: bool = False,
              open_grid: bool = False,
              random_draw: bool = False) -> GameRecord:
    """
    Play a single game with given strategies.

    Args:
        white_strategy: Strategy instance for the White player.
        black_strategy: Strategy instance for the Black player.
        verbose: Print move-by-move output.
        detailed: Collect per-move block usage and score progression.
        open_grid: Use OpenGridGameState with dynamic X/Y boundaries.
        random_draw: Use RandomDraw variant (random piece selection).

    Returns:
        A :class:`GameRecord` with scores, move count, and optional detail.
    """
    game = _create_game(open_grid=open_grid, random_draw=random_draw)
    num_moves = 0
    opening_move = None
    white_blocks = []
    black_blocks = []
    score_progression = [] if detailed else None

    is_random_draw = random_draw

    while not game.is_game_over():
        current_strategy = white_strategy if game.current_player == Player.WHITE else black_strategy
        current_player = game.current_player

        # In RandomDraw mode, draw a piece before the strategy chooses
        if is_random_draw:
            drawn = game.draw_piece()
            if drawn is None:
                break

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
                    detailed: bool = False, open_grid: bool = False,
                    random_draw: bool = False) -> dict:
    """
    Run a Monte Carlo simulation with given strategies.

    Args:
        white_strategy: Strategy instance for the White player.
        black_strategy: Strategy instance for the Black player.
        num_games: Number of games to simulate.
        verbose: Print progress every 100 games.
        detailed: Collect per-game block usage and score progressions.
        open_grid: Use OpenGridGameState with dynamic X/Y boundaries.
        random_draw: Use RandomDraw variant (random piece selection).

    Returns:
        A statistics dictionary with win rates, average scores, score
        differences, and the full list of :class:`GameRecord` objects.
    """
    results = {
        'white_wins': 0,
        'black_wins': 0,
        'ties': 0,
        'white_scores': [],
        'black_scores': [],
        'num_moves': [],
        'score_differences': [],
        'records': [],
    }

    for i in range(num_games):
        if verbose and (i + 1) % 100 == 0:
            print(f"Completed {i+1}/{num_games} games...")

        record = play_game(white_strategy, black_strategy,
                           verbose=False, detailed=detailed,
                           open_grid=open_grid, random_draw=random_draw)

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


def print_results(results: dict, white_name: str, black_name: str) -> None:
    """Pretty-print Monte Carlo simulation results."""
    print("\n" + "=" * 60)
    print(f"Monte Carlo Simulation Results")
    print(f"White Strategy: {white_name}")
    print(f"Black Strategy: {black_name}")
    print("=" * 60)
    print(f"\nWin Rates:")
    print(f"  White: {results['white_win_rate']*100:.1f}% ({results['white_wins']} wins)")
    print(f"  Black: {results['black_win_rate']*100:.1f}% ({results['black_wins']} wins)")
    print(f"  Ties:  {results['tie_rate']*100:.1f}% ({results['ties']} ties)")
    print(f"\nAverage Scores:")
    print(f"  White: {results['avg_white_score']:.2f}")
    print(f"  Black: {results['avg_black_score']:.2f}")
    print(f"  Score Difference: {results['avg_score_diff']:.2f} ± {results['std_score_diff']:.2f}")
    print(f"\nAverage Game Length: {results['avg_moves']:.1f} moves")
    print("=" * 60 + "\n")
