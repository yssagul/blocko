"""
Statistical meta-analysis suite for the Blocko game.

Provides 6 analysis functions and a master :func:`run_meta_analysis` that
executes them all and prints a final verdict:

1. :func:`analyze_first_player_advantage` — seat-swap + mirror matches.
2. :func:`analyze_block_usage` — block type drafting patterns.
3. :func:`analyze_opening_moves` — first-move dominance correlations.
4. :func:`analyze_score_distribution` — margin percentiles + text histogram.
5. :func:`analyze_game_length_correlation` — game length vs winner.
6. :func:`run_meta_analysis` — orchestrates all 5 above + final verdict.
"""

import time
from collections import defaultdict

import numpy as np

from blocko.strategies import RandomStrategy, StrategicAIStrategy
from blocko.simulation.runner import run_monte_carlo


# ──────────────────────────────────────────────────────────────────────────
# Analysis 1 & 2: First-player advantage
# ──────────────────────────────────────────────────────────────────────────

def analyze_first_player_advantage(strategies: dict, num_games: int = 500,
                                   verbose: bool = True) -> dict:
    """
    Mirror matches + seat-swapped matchups.

    Mirror matches reveal inherent first/second-player advantage.
    Seat swaps separate strategy strength from seat advantage.

    Returns:
        Dict with ``'mirror'`` and ``'seat_swap'`` result sub-dicts.
    """
    strat_names = list(strategies.keys())
    summary = {
        'seat_swap': {},
        'mirror': {},
    }

    # --- Mirror matches ---
    print("\n" + "=" * 60)
    print("MIRROR MATCH ANALYSIS (First-Player Advantage)")
    print("=" * 60)
    print("Each strategy plays against itself. In a balanced game,")
    print("White (first player) and Black should win ~50% each.\n")

    mirror_totals = {'white_wins': 0, 'black_wins': 0, 'ties': 0, 'games': 0}

    for name in strat_names:
        if verbose:
            print(f"  Running {name} vs {name} ({num_games} games)...", end=" ", flush=True)
        results = run_monte_carlo(strategies[name], strategies[name],
                                  num_games, verbose=False)
        summary['mirror'][name] = results
        mirror_totals['white_wins'] += results['white_wins']
        mirror_totals['black_wins'] += results['black_wins']
        mirror_totals['ties'] += results['ties']
        mirror_totals['games'] += num_games

        w_pct = results['white_win_rate'] * 100
        b_pct = results['black_win_rate'] * 100
        t_pct = results['tie_rate'] * 100
        if verbose:
            print(f"White {w_pct:.1f}% | Black {b_pct:.1f}% | Tie {t_pct:.1f}%")

    # Aggregate mirror result
    total = mirror_totals['games']
    agg_w = mirror_totals['white_wins'] / total * 100
    agg_b = mirror_totals['black_wins'] / total * 100
    agg_t = mirror_totals['ties'] / total * 100
    print(f"\n  AGGREGATE across all mirror matches ({total} games):")
    print(f"    White (1st): {agg_w:.1f}%  |  Black (2nd): {agg_b:.1f}%  |  Tie: {agg_t:.1f}%")

    if agg_w > 55:
        print("    ⚠  SIGNIFICANT first-player advantage detected!")
    elif agg_b > 55:
        print("    ⚠  SIGNIFICANT second-player advantage detected!")
    else:
        print("    ✓  No strong first-player advantage detected.")

    # --- Seat-swapped matchups ---
    print("\n" + "=" * 60)
    print("SEAT-SWAP ANALYSIS")
    print("=" * 60)
    print("Each pair is tested in both seat orders to separate")
    print("strategy strength from seat advantage.\n")

    for i, name_a in enumerate(strat_names):
        for name_b in strat_names[i + 1:]:
            if verbose:
                print(f"  {name_a} vs {name_b}:", flush=True)

            if verbose:
                print(f"    Seat 1: {name_a}(W) vs {name_b}(B)...", end=" ", flush=True)
            r_ab = run_monte_carlo(strategies[name_a], strategies[name_b],
                                   num_games, verbose=False)
            if verbose:
                print(f"W:{r_ab['white_win_rate']*100:.1f}% B:{r_ab['black_win_rate']*100:.1f}%")

            if verbose:
                print(f"    Seat 2: {name_b}(W) vs {name_a}(B)...", end=" ", flush=True)
            r_ba = run_monte_carlo(strategies[name_b], strategies[name_a],
                                   num_games, verbose=False)
            if verbose:
                print(f"W:{r_ba['white_win_rate']*100:.1f}% B:{r_ba['black_win_rate']*100:.1f}%")

            a_wins = r_ab['white_wins'] + r_ba['black_wins']
            b_wins = r_ab['black_wins'] + r_ba['white_wins']
            ties = r_ab['ties'] + r_ba['ties']
            total_pair = num_games * 2
            a_pct = a_wins / total_pair * 100
            b_pct = b_wins / total_pair * 100

            white_total = r_ab['white_wins'] + r_ba['white_wins']
            white_pct = white_total / total_pair * 100

            if verbose:
                print(f"    → {name_a} wins {a_pct:.1f}%, {name_b} wins {b_pct:.1f}%"
                      f" (seat-neutral)")
                print(f"    → White (1st player) won {white_pct:.1f}% across both orderings")

            summary['seat_swap'][(name_a, name_b)] = {
                'a_as_white': r_ab,
                'b_as_white': r_ba,
                'a_win_pct': a_pct,
                'b_win_pct': b_pct,
                'first_player_win_pct': white_pct,
            }

    return summary


# ──────────────────────────────────────────────────────────────────────────
# Analysis 3: Block usage
# ──────────────────────────────────────────────────────────────────────────

def analyze_block_usage(strategies: dict, num_games: int = 200,
                        verbose: bool = True) -> dict:
    """
    Track which block types winners vs losers draft.

    Returns:
        Dict keyed by matchup string, mapping block types to winner/loser
        usage percentages.
    """
    print("\n" + "=" * 60)
    print("BLOCK USAGE ANALYSIS")
    print("=" * 60)
    print("Tracks which block types winners vs losers draft.\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    if 'edge_control' in strategies and 'greedy' in strategies:
        test_pairs.append(('edge_control', 'greedy'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_usage = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games)...", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False, detailed=True)

        winner_blocks = defaultdict(int)
        loser_blocks = defaultdict(int)
        tie_blocks = defaultdict(int)

        for record in results['records']:
            w_blocks = record.white_blocks_used or []
            b_blocks = record.black_blocks_used or []

            if record.winner == 'white':
                for bt in w_blocks:
                    winner_blocks[bt] += 1
                for bt in b_blocks:
                    loser_blocks[bt] += 1
            elif record.winner == 'black':
                for bt in b_blocks:
                    winner_blocks[bt] += 1
                for bt in w_blocks:
                    loser_blocks[bt] += 1
            else:
                for bt in w_blocks + b_blocks:
                    tie_blocks[bt] += 1

        all_block_types = sorted(set(list(winner_blocks.keys()) +
                                     list(loser_blocks.keys()) +
                                     list(tie_blocks.keys())))

        total_winner = sum(winner_blocks.values()) or 1
        total_loser = sum(loser_blocks.values()) or 1

        key = f"{w_name}_vs_{b_name}"
        all_usage[key] = {}

        if verbose:
            print(f"    {'Block Type':<15} {'Winner %':>10} {'Loser %':>10} {'Diff':>10}")
            print(f"    {'-' * 45}")

        for bt in all_block_types:
            w_pct = winner_blocks[bt] / total_winner * 100
            l_pct = loser_blocks[bt] / total_loser * 100
            diff = w_pct - l_pct
            all_usage[key][bt] = {'winner_pct': w_pct, 'loser_pct': l_pct, 'diff': diff}
            if verbose:
                flag = " ◄" if abs(diff) > 3.0 else ""
                print(f"    {bt:<15} {w_pct:>9.1f}% {l_pct:>9.1f}% {diff:>+9.1f}%{flag}")

        if verbose:
            print()

    return all_usage


# ──────────────────────────────────────────────────────────────────────────
# Analysis 4: Opening moves
# ──────────────────────────────────────────────────────────────────────────

def analyze_opening_moves(strategies: dict, num_games: int = 500,
                          verbose: bool = True) -> dict:
    """
    Check whether certain first-move positions/blocks correlate with winning.

    Returns:
        Dict keyed by matchup string, each containing a sorted list of
        (opening_key, stats) tuples.
    """
    print("\n" + "=" * 60)
    print("OPENING MOVE DOMINANCE ANALYSIS")
    print("=" * 60)
    print("Do certain opening moves correlate with winning?\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_openings = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games)...", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False, detailed=True)

        opening_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0})

        for record in results['records']:
            if record.opening_move is None:
                continue
            block_repr, pos, orient, flip = record.opening_move
            key = (block_repr, pos, orient, flip)

            if record.winner == 'white':
                opening_stats[key]['wins'] += 1
            elif record.winner == 'black':
                opening_stats[key]['losses'] += 1
            else:
                opening_stats[key]['ties'] += 1

        sorted_openings = sorted(opening_stats.items(),
                                 key=lambda x: sum(x[1].values()), reverse=True)

        pair_key = f"{w_name}_vs_{b_name}"
        all_openings[pair_key] = sorted_openings

        if verbose:
            print(f"    {'Opening Move':<40} {'Count':>6} {'Win%':>7} {'Loss%':>7}")
            print(f"    {'-' * 60}")
            for opening, stats in sorted_openings[:10]:
                total = stats['wins'] + stats['losses'] + stats['ties']
                if total < 5:
                    continue
                w_pct = stats['wins'] / total * 100
                l_pct = stats['losses'] / total * 100
                block_repr, pos, orient, flip = opening
                label = f"{block_repr} @{pos} {orient} {'F' if flip else 'N'}"
                flag = " ◄ dominant" if w_pct > 70 and total > 20 else ""
                print(f"    {label:<40} {total:>6} {w_pct:>6.1f}% {l_pct:>6.1f}%{flag}")
            print()

    return all_openings


# ──────────────────────────────────────────────────────────────────────────
# Analysis 5: Score distribution
# ──────────────────────────────────────────────────────────────────────────

def analyze_score_distribution(strategies: dict, num_games: int = 500,
                               verbose: bool = True) -> dict:
    """
    Score margin distribution: percentiles and a text histogram.

    Returns:
        Dict keyed by matchup string with percentiles, mean, std, min, max.
    """
    print("\n" + "=" * 60)
    print("SCORE MARGIN DISTRIBUTION ANALYSIS")
    print("=" * 60)
    print("How are victory margins distributed? (positive = White wins)\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    if 'edge_control' in strategies and 'greedy' in strategies:
        test_pairs.append(('edge_control', 'greedy'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_distributions = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games):", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False)

        diffs = np.array(results['score_differences'])
        percentiles = {
            '5th': np.percentile(diffs, 5),
            '25th': np.percentile(diffs, 25),
            'median': np.median(diffs),
            '75th': np.percentile(diffs, 75),
            '95th': np.percentile(diffs, 95),
        }
        all_distributions[f"{w_name}_vs_{b_name}"] = {
            'percentiles': percentiles,
            'mean': float(np.mean(diffs)),
            'std': float(np.std(diffs)),
            'min': int(np.min(diffs)),
            'max': int(np.max(diffs)),
        }

        if verbose:
            print(f"    Mean: {np.mean(diffs):+.1f}  Std: {np.std(diffs):.1f}"
                  f"  Range: [{np.min(diffs)}, {np.max(diffs)}]")
            print(f"    Percentiles:  5th={percentiles['5th']:+.0f}"
                  f"  25th={percentiles['25th']:+.0f}"
                  f"  50th={percentiles['median']:+.0f}"
                  f"  75th={percentiles['75th']:+.0f}"
                  f"  95th={percentiles['95th']:+.0f}")

            # Text histogram
            bin_min = int(np.min(diffs)) - 1
            bin_max = int(np.max(diffs)) + 2
            hist, bin_edges = np.histogram(diffs, bins=range(bin_min, bin_max))
            max_count = max(hist) if max(hist) > 0 else 1
            bar_width = 40

            print(f"    Distribution:")
            for j, count in enumerate(hist):
                if count == 0:
                    continue
                bar_len = int(count / max_count * bar_width)
                margin = int(bin_edges[j])
                print(f"      {margin:>+4d} | {'█' * bar_len} {count}")
            print()

    return all_distributions


# ──────────────────────────────────────────────────────────────────────────
# Analysis 6: Game length correlation
# ──────────────────────────────────────────────────────────────────────────

def analyze_game_length_correlation(strategies: dict, num_games: int = 500,
                                    verbose: bool = True) -> dict:
    """
    Correlate game length with winner.

    Returns:
        Dict keyed by matchup string with correlation coefficient and
        average lengths per outcome.
    """
    print("\n" + "=" * 60)
    print("GAME LENGTH vs WINNER CORRELATION")
    print("=" * 60)
    print("Does game length predict who wins?\n")

    strat_names = list(strategies.keys())
    test_pairs = []
    for name in strat_names:
        test_pairs.append((name, name))
    if 'greedy' in strategies and 'random' in strategies:
        test_pairs.append(('greedy', 'random'))
    test_pairs = list(dict.fromkeys(test_pairs))

    all_correlations = {}

    for w_name, b_name in test_pairs:
        if verbose:
            print(f"  {w_name} vs {b_name} ({num_games} games):", flush=True)

        results = run_monte_carlo(strategies[w_name], strategies[b_name],
                                  num_games, verbose=False)

        records = results['records']

        length_bins = defaultdict(lambda: {'white': 0, 'black': 0, 'tie': 0})
        for record in records:
            length_bin = (record.num_moves // 3) * 3
            length_bins[length_bin][record.winner] += 1

        lengths = np.array([r.num_moves for r in records])
        diffs = np.array([r.score_diff for r in records])
        if np.std(lengths) > 0 and np.std(diffs) > 0:
            correlation = np.corrcoef(lengths, diffs)[0, 1]
        else:
            correlation = 0.0

        white_win_lengths = [r.num_moves for r in records if r.winner == 'white']
        black_win_lengths = [r.num_moves for r in records if r.winner == 'black']
        tie_lengths = [r.num_moves for r in records if r.winner == 'tie']

        pair_key = f"{w_name}_vs_{b_name}"
        all_correlations[pair_key] = {
            'correlation': correlation,
            'avg_length_white_wins': np.mean(white_win_lengths) if white_win_lengths else 0,
            'avg_length_black_wins': np.mean(black_win_lengths) if black_win_lengths else 0,
            'avg_length_ties': np.mean(tie_lengths) if tie_lengths else 0,
        }

        if verbose:
            print(f"    Length-ScoreDiff correlation: {correlation:+.3f}", end="")
            if abs(correlation) > 0.3:
                direction = "longer→White" if correlation > 0 else "longer→Black"
                print(f"  ⚠  ({direction})")
            else:
                print(f"  (weak)")

            if white_win_lengths:
                print(f"    Avg length when White wins: {np.mean(white_win_lengths):.1f}")
            if black_win_lengths:
                print(f"    Avg length when Black wins: {np.mean(black_win_lengths):.1f}")
            if tie_lengths:
                print(f"    Avg length when Tie:        {np.mean(tie_lengths):.1f}")

            print(f"    {'Moves':<8} {'White%':>8} {'Black%':>8} {'Tie%':>8} {'Count':>8}")
            print(f"    {'-' * 40}")
            for length_bin in sorted(length_bins.keys()):
                stats = length_bins[length_bin]
                total = stats['white'] + stats['black'] + stats['tie']
                if total < 5:
                    continue
                print(f"    {length_bin:>3}-{length_bin + 2:<3}"
                      f" {stats['white'] / total * 100:>7.1f}%"
                      f" {stats['black'] / total * 100:>7.1f}%"
                      f" {stats['tie'] / total * 100:>7.1f}%"
                      f" {total:>7}")
            print()

    return all_correlations


# ──────────────────────────────────────────────────────────────────────────
# Master orchestrator
# ──────────────────────────────────────────────────────────────────────────

def run_meta_analysis(num_games: int = 500) -> dict:
    """
    Run all 6 meta analyses and print a final verdict.

    Uses ``RandomStrategy`` and ``StrategicAIStrategy`` by default.

    Args:
        num_games: Number of games per test.

    Returns:
        Dict with all analysis results keyed by analysis name.
    """
    print("=" * 60)
    print("4x4x4 Block Stacking Game — FULL META ANALYSIS")
    print("=" * 60)
    print(f"Running {num_games} games per test.\n")

    strategies = {
        'random': RandomStrategy(),
        'strategic': StrategicAIStrategy(),
    }

    t0 = time.time()

    fpa_results = analyze_first_player_advantage(strategies, num_games)
    block_results = analyze_block_usage(strategies, num_games=min(num_games, 200))
    opening_results = analyze_opening_moves(strategies, num_games)
    dist_results = analyze_score_distribution(strategies, num_games)
    length_results = analyze_game_length_correlation(strategies, num_games)

    elapsed = time.time() - t0

    # === FINAL VERDICT ===
    print("\n" + "=" * 60)
    print("FINAL META ANALYSIS VERDICT")
    print("=" * 60)

    # Aggregate first-player advantage from mirror matches
    mirror = fpa_results['mirror']
    total_w = sum(r['white_wins'] for r in mirror.values())
    total_b = sum(r['black_wins'] for r in mirror.values())
    total_t = sum(r['ties'] for r in mirror.values())
    total_g = total_w + total_b + total_t
    w_rate = total_w / total_g * 100

    print(f"\n  1. FIRST-PLAYER ADVANTAGE (mirror matches):")
    print(f"     White (1st) wins: {w_rate:.1f}% across {total_g} mirror games")
    if w_rate > 55:
        print(f"     → BROKEN: Going first is a significant advantage.")
    elif w_rate < 45:
        print(f"     → BROKEN: Going second is a significant advantage.")
    else:
        print(f"     → BALANCED: No significant first-player advantage.")

    swap = fpa_results['seat_swap']
    if swap:
        avg_fp = np.mean([v['first_player_win_pct'] for v in swap.values()])
        print(f"\n  2. SEAT-SWAP CONSISTENCY:")
        print(f"     Average White (1st) win rate across swapped pairs: {avg_fp:.1f}%")
        if avg_fp > 55:
            print(f"     → First-mover advantage persists even when strategies swap seats.")
        elif avg_fp < 45:
            print(f"     → Second-mover advantage persists across strategy swaps.")
        else:
            print(f"     → Seat position does not dominate strategy skill.")

    print(f"\n  3. BLOCK POOL:")
    has_block_bias = False
    for matchup, usage in block_results.items():
        for bt, stats in usage.items():
            if abs(stats['diff']) > 5.0:
                if not has_block_bias:
                    print(f"     Significant block draft biases detected:")
                    has_block_bias = True
                print(f"       {bt} in {matchup}: winner uses {stats['diff']:+.1f}% more")
    if not has_block_bias:
        print(f"     No significant block draft advantage detected.")

    print(f"\n  4. OPENING MOVES:")
    has_dominant = False
    for matchup, openings in opening_results.items():
        for opening, stats in openings:
            total = stats['wins'] + stats['losses'] + stats['ties']
            if total >= 20 and stats['wins'] / total > 0.70:
                if not has_dominant:
                    print(f"     Dominant openings found:")
                    has_dominant = True
                block_repr, pos, orient, flip = opening
                wr = stats['wins'] / total * 100
                print(f"       {block_repr} @{pos} {orient} → {wr:.0f}% win rate"
                      f" ({total} games) in {matchup}")
    if not has_dominant:
        print(f"     No single opening move dominates.")

    print(f"\n  5. SCORE DISTRIBUTION:")
    for matchup, dist in dist_results.items():
        spread = dist['std']
        skew_dir = "White" if dist['mean'] > 1 else "Black" if dist['mean'] < -1 else "neutral"
        print(f"     {matchup}: mean {dist['mean']:+.1f}, std {spread:.1f}, "
              f"range [{dist['min']},{dist['max']}] → {skew_dir}")

    print(f"\n  6. GAME LENGTH CORRELATION:")
    for matchup, corr in length_results.items():
        r = corr['correlation']
        strength = "strong" if abs(r) > 0.3 else "moderate" if abs(r) > 0.15 else "weak"
        direction = "longer→White" if r > 0 else "longer→Black"
        print(f"     {matchup}: r={r:+.3f} ({strength}, {direction})")

    print(f"\n  Total analysis time: {elapsed:.1f}s")
    print("=" * 60)

    return {
        'first_player': fpa_results,
        'block_usage': block_results,
        'opening_moves': opening_results,
        'score_distribution': dist_results,
        'game_length': length_results,
    }
