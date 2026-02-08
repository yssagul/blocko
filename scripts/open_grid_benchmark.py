#!/usr/bin/env python3
"""
Open Grid vs Standard mode balance comparison.
"""

import time

from blocko.strategies import RandomStrategy, StrategicAIStrategy, AntiRandomStrategy
from blocko.simulation import run_monte_carlo, print_results


def run_benchmark(label, white_strat, black_strat, n_games, open_grid):
    print(f"\n{'='*60}", flush=True)
    print(f"  {label}  (open_grid={open_grid})", flush=True)
    print(f"{'='*60}", flush=True)
    t0 = time.time()
    results = run_monte_carlo(white_strat, black_strat, n_games,
                              verbose=True, open_grid=open_grid)
    elapsed = time.time() - t0
    print_results(results, "White", "Black")
    print(f"  Time: {elapsed:.1f}s  ({elapsed/n_games*1000:.0f}ms/game)", flush=True)
    return results


if __name__ == "__main__":
    random_s = RandomStrategy()

    # 1. Random vs Random — Open Grid (500 games, fast)
    run_benchmark("Random vs Random — OPEN GRID",
                  random_s, random_s, 500, open_grid=True)

    # 2. Random vs Random — Standard (500 games, reference)
    run_benchmark("Random vs Random — STANDARD",
                  random_s, random_s, 500, open_grid=False)

    # 3. StrategicAI vs StrategicAI — shorter runs
    strategic = StrategicAIStrategy()

    # Check timing first
    print("\nTiming a single StrategicAI open grid game...", flush=True)
    t0 = time.time()
    from blocko.simulation import play_game
    rec = play_game(strategic, strategic, open_grid=True)
    t1 = time.time()
    print(f"  Single game: {(t1-t0)*1000:.0f}ms  Score: {rec.white_score}-{rec.black_score}", flush=True)

    # If a single game takes <5s, run 100; otherwise run 20
    per_game_ms = (t1 - t0) * 1000
    if per_game_ms < 5000:
        n_strat = 100
    elif per_game_ms < 20000:
        n_strat = 50
    else:
        n_strat = 20
    print(f"  Will run {n_strat} StrategicAI games", flush=True)

    run_benchmark("StrategicAI vs StrategicAI — OPEN GRID",
                  strategic, strategic, n_strat, open_grid=True)

    run_benchmark("StrategicAI vs StrategicAI — STANDARD",
                  strategic, strategic, n_strat, open_grid=False)

    print("\n\nDone! All benchmarks complete.", flush=True)
