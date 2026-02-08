"""
Game rule validator for the Blocko engine.

Plays random games and validates every move and the final board state
against all game rules.  Useful for regression testing and verifying
engine correctness after refactoring.
"""

from blocko.core.models import Color, PlacedBlock
from blocko.core.game_state import GameState
from blocko.strategies.random import RandomStrategy


def validate_game(num_games: int = 100, verbose: bool = True) -> bool:
    """
    Play *num_games* random games, validating every move and final state.

    Checks:
      1. Both cells within bounds.
      2. No cell overlap.
      3. Gravity support (z=0 or cell below occupied).
      4. Color stacking constraint (no same non-red on top).
      5. Each block occupies exactly 2 cells.
      6. Orientation is one of 'x', 'y', 'z'.
      7. Post-game: no duplicate grid positions, no support gaps.

    Args:
        num_games: Number of games to play.
        verbose: Print per-game results and a final summary.

    Returns:
        True if all games pass validation.
    """
    all_passed = True

    for game_num in range(num_games):
        game = GameState()
        strat = RandomStrategy()
        move_num = 0
        errors = []

        while not game.is_game_over():
            move = strat.choose_move(game, game.current_player)
            if move is None:
                break

            block, position, orientation, flip = move
            placed = PlacedBlock(block, position, orientation, flip)
            occupied = placed.get_occupied_positions()
            occupied_set = set(occupied)
            move_num += 1

            # --- Rule 1: Within bounds ---
            for px, py, pz in occupied:
                if not (0 <= px < 4 and 0 <= py < 4 and 0 <= pz < 4):
                    errors.append(f"Move {move_num}: Out of bounds at {(px, py, pz)}")

            # --- Rule 2: Not overlapping ---
            for pos in occupied:
                if pos in game.grid:
                    errors.append(f"Move {move_num}: Overlap at {pos}")

            # --- Rule 3: Support (no cantilevering) ---
            for px, py, pz in occupied:
                if pz == 0:
                    continue
                below = (px, py, pz - 1)
                if below not in game.grid and below not in occupied_set:
                    errors.append(f"Move {move_num}: No support at {(px, py, pz)}"
                                  f" (below {below} not in grid or block)")

            # --- Rule 4: Color stacking ---
            for px, py, pz in occupied:
                if pz > 0:
                    below_pos = (px, py, pz - 1)
                    if below_pos in game.grid:
                        color_above = placed.get_color_at_position((px, py, pz))
                        color_below = game.grid[below_pos].get_color_at_position(below_pos)
                        if color_above != Color.RED and color_above == color_below:
                            errors.append(
                                f"Move {move_num}: Same-color stack at {(px, py, pz)}"
                                f" ({color_above.name} on {color_below.name})")

            # --- Rule 5: Orientation produces exactly 2 positions ---
            if len(occupied) != 2:
                errors.append(f"Move {move_num}: Block occupies {len(occupied)} cells"
                              f" (expected 2)")

            # --- Rule 6: Valid orientation ---
            if orientation not in ('x', 'y', 'z'):
                errors.append(f"Move {move_num}: Invalid orientation '{orientation}'")

            game.make_move(*move)

        # --- Post-game validation ---
        positions_seen = set()
        for pos in game.grid:
            if pos in positions_seen:
                errors.append(f"Final state: Duplicate position {pos} in grid")
            positions_seen.add(pos)

        for pos in game.grid:
            px, py, pz = pos
            for z_check in range(1, pz + 1):
                if (px, py, z_check - 1) not in game.grid:
                    errors.append(f"Final state: {pos} has gap in support at z={z_check - 1}")
                    break

        # Count orientation usage
        orientations_used = set()
        for _, placed_block in game.move_history:
            orientations_used.add(placed_block.orientation)

        if errors:
            all_passed = False
            if verbose:
                print(f"Game {game_num + 1}: FAILED ({len(errors)} errors)")
                for e in errors[:10]:
                    print(f"  ✗ {e}")
        elif verbose and game_num < 3:
            print(f"Game {game_num + 1}: PASSED — {move_num} moves, "
                  f"orientations used: {orientations_used}, "
                  f"score: {game.calculate_score()}")

    if verbose:
        print(f"\nValidation: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'}"
              f" ({num_games} games)")

    return all_passed
