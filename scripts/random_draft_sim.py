#!/usr/bin/env python3
"""
Random Draft Mode simulation.
Each turn, a random block is drawn from the pool. The player must use it
if any legal move exists for that block. If no legal move exists, the block
is returned and another is drawn until a playable block is found.
The strategy only controls WHERE to place the forced block, not WHICH block.
"""

import time
import random
import numpy as np
from collections import defaultdict

from blocko.core import GameState, OpenGridGameState, Player, Color, Block, PlacedBlock
from blocko.strategies import Strategy, StrategicAIStrategy, AntiRandomStrategy, RandomStrategy
from blocko.simulation import GameRecord, print_results


def _block_type_key(block: Block) -> str:
    return block.color1.name[0] + block.color2.name[0]


def play_random_draft_game(
    white_strategy: Strategy,
    black_strategy: Strategy,
    verbose: bool = False,
    detailed: bool = False,
    open_grid: bool = False,
) -> GameRecord:
    """
    Play a single game with random block drafting.
    Each turn a random block is drawn; the player must use it if legal.
    If not legal, it's returned and another block is drawn.
    """
    game = OpenGridGameState() if open_grid else GameState()
    num_moves = 0
    opening_move = None
    white_blocks = []
    black_blocks = []
    score_progression = [] if detailed else None
    draft_stats = {'draws': 0, 'redraws': 0}  # track draw efficiency

    while not game.is_game_over():
        current_strategy = (
            white_strategy if game.current_player == Player.WHITE
            else black_strategy
        )
        current_player = game.current_player

        # --- Random draft: draw a block, check if playable ---
        remaining = list(game.remaining_blocks)
        if not remaining:
            break

        # Get ALL legal moves once (expensive but needed for filtering)
        all_legal = game.get_legal_moves()
        if not all_legal:
            break

        # Build a set of playable block types
        playable_block_ids = set()
        for move in all_legal:
            playable_block_ids.add(id(move[0]))

        # Build pool of blocks that have at least one legal move
        playable_pool = [b for b in remaining if id(b) in playable_block_ids]
        if not playable_pool:
            break

        # Draw randomly from the full remaining pool, redraw if not playable
        pool = list(remaining)
        random.shuffle(pool)
        drawn_block = None
        draws = 0
        for candidate in pool:
            draws += 1
            if id(candidate) in playable_block_ids:
                drawn_block = candidate
                break

        draft_stats['draws'] += draws
        draft_stats['redraws'] += (draws - 1)

        if drawn_block is None:
            break

        # Filter legal moves to only those using the drawn block
        forced_moves = [m for m in all_legal if m[0] is drawn_block]

        if not forced_moves:
            # Shouldn't happen since we checked playability, but safety check
            # Try same block type (different instance)
            bt = _block_type_key(drawn_block)
            forced_moves = [m for m in all_legal
                            if _block_type_key(m[0]) == bt]
            if forced_moves:
                # Remap to use the drawn block instance
                forced_moves = [
                    (drawn_block, m[1], m[2], m[3]) for m in forced_moves
                ]

        if not forced_moves:
            break

        # --- Strategy picks the best placement for this forced block ---
        # Create a temporary filtered game state view for the strategy
        # We'll use a wrapper approach: override get_legal_moves on a copy
        best_move = _pick_best_move(current_strategy, game, current_player,
                                     forced_moves, drawn_block)

        if best_move is None:
            best_move = random.choice(forced_moves)

        block, position, orientation, flip = best_move

        # Track block usage
        if detailed:
            block_type = repr(block)
            if current_player == Player.WHITE:
                white_blocks.append(block_type)
            else:
                black_blocks.append(block_type)

        if num_moves == 0:
            opening_move = (repr(block), position, orientation, flip)

        game.make_move(block, position, orientation, flip)
        num_moves += 1

        if detailed:
            w, b = game.calculate_score()
            score_progression.append((w, b))

        if verbose:
            bt = _block_type_key(block)
            print(f"Move {num_moves}: {current_player.name} drew {bt} "
                  f"→ ({position[0]},{position[1]},{position[2]}) "
                  f"{orientation} {'flip' if flip else ''}"
                  f"  [drew {draws}x]")

    white_score, black_score = game.calculate_score()

    if white_score > black_score:
        winner = 'white'
    elif black_score > white_score:
        winner = 'black'
    else:
        winner = 'tie'

    if verbose:
        print(f"\nGame Over! White: {white_score}, Black: {black_score}")
        print(f"Winner: {winner.capitalize()}, Moves: {num_moves}")
        print(f"Draft stats: {draft_stats['draws']} total draws, "
              f"{draft_stats['redraws']} redraws")

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


def _pick_best_move(strategy, game_state, player, forced_moves, drawn_block):
    """
    Let the strategy evaluate the forced moves and pick the best one.
    For StrategicAIStrategy, we use its evaluation function directly.
    For simpler strategies, we fall back to random choice from forced moves.
    """
    if isinstance(strategy, StrategicAIStrategy):
        return _strategic_pick(strategy, game_state, player, forced_moves)
    elif isinstance(strategy, AntiRandomStrategy):
        return _anti_random_pick(strategy, game_state, player, forced_moves)
    else:
        # RandomStrategy or unknown — just pick randomly
        return random.choice(forced_moves) if forced_moves else None


def _strategic_pick(strategy, game_state, player, forced_moves):
    """Use StrategicAIStrategy's evaluation to rank forced moves."""
    my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
    opp_color = Color.BLACK if player == Player.WHITE else Color.WHITE

    # Use the analytical evaluator for all forced moves
    face_counts = strategy._compute_face_counts(game_state, my_color, opp_color)

    best_score = float('-inf')
    best_move = None

    for move in forced_moves:
        score = strategy._evaluate_move(move, game_state, my_color, opp_color)
        if score > best_score:
            best_score = score
            best_move = move

    return best_move


def _anti_random_pick(strategy, game_state, player, forced_moves):
    """Use AntiRandomStrategy's evaluation to rank forced moves."""
    my_color = Color.WHITE if player == Player.WHITE else Color.BLACK
    opp_color = Color.BLACK if player == Player.WHITE else Color.WHITE

    best_score = float('-inf')
    best_move = None

    for move in forced_moves:
        score = strategy._evaluate_move(move, game_state, my_color, opp_color)
        if score > best_score:
            best_score = score
            best_move = move

    return best_move


def run_random_draft_mc(
    white_strategy, black_strategy, num_games=500,
    verbose=False, detailed=False, open_grid=False,
):
    """Monte Carlo with random draft mode."""
    results = {
        'white_wins': 0, 'black_wins': 0, 'ties': 0,
        'white_scores': [], 'black_scores': [],
        'num_moves': [], 'score_differences': [],
        'records': [],
    }

    for i in range(num_games):
        if verbose and (i + 1) % 100 == 0:
            print(f"Completed {i+1}/{num_games} games...", flush=True)

        record = play_random_draft_game(
            white_strategy, black_strategy,
            verbose=False, detailed=detailed, open_grid=open_grid,
        )

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

    results['white_win_rate'] = results['white_wins'] / num_games
    results['black_win_rate'] = results['black_wins'] / num_games
    results['tie_rate'] = results['ties'] / num_games
    results['avg_white_score'] = np.mean(results['white_scores'])
    results['avg_black_score'] = np.mean(results['black_scores'])
    results['avg_moves'] = np.mean(results['num_moves'])
    results['avg_score_diff'] = np.mean(results['score_differences'])
    results['std_score_diff'] = np.std(results['score_differences'])

    return results


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    strategic = StrategicAIStrategy()
    N = 500

    print("=" * 64, flush=True)
    print("  RANDOM DRAFT: StrategicAI vs StrategicAI  (Standard Grid)", flush=True)
    print("=" * 64, flush=True)

    # First, play one verbose game to show what's happening
    print("\n--- Sample game (verbose) ---", flush=True)
    play_random_draft_game(strategic, strategic, verbose=True)

    # Run full benchmark
    print(f"\n--- Running {N}-game Monte Carlo ---", flush=True)
    t0 = time.time()
    results_draft = run_random_draft_mc(
        strategic, strategic, N, verbose=True, open_grid=False,
    )
    elapsed = time.time() - t0
    print_results(results_draft, "StrategicAI(W)", "StrategicAI(B)")
    print(f"  Time: {elapsed:.1f}s  ({elapsed/N*1000:.0f}ms/game)", flush=True)

    # Reference: normal mode (no draft) — use saved results or run small batch
    print(f"\n--- Reference: Normal mode (100 games) ---", flush=True)
    from blocko.simulation import run_monte_carlo
    t0 = time.time()
    results_normal = run_monte_carlo(
        strategic, strategic, 100, verbose=True, open_grid=False,
    )
    elapsed = time.time() - t0
    print_results(results_normal, "StrategicAI(W)", "StrategicAI(B)")
    print(f"  Time: {elapsed:.1f}s  ({elapsed/100*1000:.0f}ms/game)", flush=True)

    # Summary comparison
    print("\n" + "=" * 64, flush=True)
    print("  COMPARISON SUMMARY", flush=True)
    print("=" * 64, flush=True)
    print(f"{'Mode':<22} {'W Win':>7} {'B Win':>7} {'Tie':>7} {'Avg Margin':>12}", flush=True)
    print("-" * 64, flush=True)
    print(f"{'Random Draft (500g)':<22} "
          f"{results_draft['white_win_rate']*100:>6.1f}% "
          f"{results_draft['black_win_rate']*100:>6.1f}% "
          f"{results_draft['tie_rate']*100:>6.1f}% "
          f"{'B' if results_draft['avg_score_diff'] < 0 else 'W'}"
          f"+{abs(results_draft['avg_score_diff']):.1f} "
          f"±{results_draft['std_score_diff']:.1f}",
          flush=True)
    print(f"{'Normal (100g ref)':<22} "
          f"{results_normal['white_win_rate']*100:>6.1f}% "
          f"{results_normal['black_win_rate']*100:>6.1f}% "
          f"{results_normal['tie_rate']*100:>6.1f}% "
          f"{'B' if results_normal['avg_score_diff'] < 0 else 'W'}"
          f"+{abs(results_normal['avg_score_diff']):.1f} "
          f"±{results_normal['std_score_diff']:.1f}",
          flush=True)
    print(flush=True)
