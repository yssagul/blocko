#!/usr/bin/env python3
"""
Flask backend for the 4x4x4 Block Stacking Game.
Human plays White (1st), AntiRandomStrategy AI plays Black (2nd).
"""

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from blocko.core import GameState, OpenGridGameState, Player, Color, Block, PlacedBlock
from blocko.strategies import StrategicAIStrategy

HERE = Path(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Global game state
# ---------------------------------------------------------------------------
game_state: GameState | None = None
ai_strategy = StrategicAIStrategy()
move_log: list[dict] = []
game_mode: str = "standard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _block_type_key(block: Block) -> str:
    """Return a two-letter type key like 'BW', 'WR', etc."""
    return block.color1.name[0] + block.color2.name[0]


def _find_block_by_type(game: GameState, type_key: str) -> Block | None:
    """Find the first remaining block matching *type_key*."""
    for b in game.remaining_blocks:
        if _block_type_key(b) == type_key:
            return b
    return None


def _serialize_state(game: GameState) -> dict:
    """Serialize the full game state into a JSON-safe dict."""
    # Grid: {\"x,y,z\": \"white\"/\"black\"/\"red\"}
    grid: dict[str, str] = {}
    for (x, y, z), placed_block in game.grid.items():
        color = placed_block.get_color_at_position((x, y, z))
        grid[f"{x},{y},{z}"] = color.name.lower()

    white_score, black_score = game.calculate_score()

    remaining: dict[str, int] = {}
    for b in game.remaining_blocks:
        key = _block_type_key(b)
        remaining[key] = remaining.get(key, 0) + 1

    bounds = game.get_bounds()

    return {
        "grid": grid,
        "white_score": white_score,
        "black_score": black_score,
        "current_player": game.current_player.name.lower(),
        "game_over": game.is_game_over(),
        "remaining_blocks": remaining,
        "move_count": len(game.move_history),
        "move_log": move_log,
        "bounds": {
            "x_min": bounds[0], "x_max": bounds[1],
            "y_min": bounds[2], "y_max": bounds[3],
            "z_min": bounds[4], "z_max": bounds[5],
        },
        "mode": game_mode,
    }


def _serialize_legal_moves(game: GameState) -> dict:
    """
    Return legal moves in a compact lookup structure:
      { block_type: { orientation: { "true"/"false": [[x,y,z], …] } } }
    Deduplicated by (block_type, position, orientation, flip).
    """
    moves = game.get_legal_moves()
    lookup: dict[str, dict[str, dict[str, list]]] = {}
    seen: set[tuple] = set()

    for block, pos, orient, flip in moves:
        bt = _block_type_key(block)
        dedup_key = (bt, pos, orient, flip)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        if bt not in lookup:
            lookup[bt] = {}
        if orient not in lookup[bt]:
            lookup[bt][orient] = {"true": [], "false": []}
        flip_key = "true" if flip else "false"
        lookup[bt][orient][flip_key].append(list(pos))

    return lookup


def _placed_cells(block: Block, position: tuple, orientation: str, flip: bool):
    """Return the two [x,y,z] cells a placement occupies."""
    pb = PlacedBlock(block, position, orientation, flip)
    return [list(p) for p in pb.get_occupied_positions()]


def _init_game(open_grid: bool = False):
    """Create a fresh game and clear the log."""
    global game_state, move_log, game_mode
    game_state = OpenGridGameState() if open_grid else GameState()
    game_mode = "open_grid" if open_grid else "standard"
    move_log = []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_file(HERE / "index.html")


@app.route("/api/state")
def api_state():
    if game_state is None:
        _init_game()
    return jsonify(_serialize_state(game_state))


@app.route("/api/legal")
def api_legal():
    if game_state is None:
        _init_game()
    return jsonify(_serialize_legal_moves(game_state))


@app.route("/api/reset", methods=["POST"])
def api_reset():
    data = request.get_json(force=True) if request.is_json else {}
    mode = data.get("mode", "standard")
    _init_game(open_grid=(mode == "open_grid"))
    return jsonify({
        "state": _serialize_state(game_state),
        "legal_moves": _serialize_legal_moves(game_state),
    })


@app.route("/api/move", methods=["POST"])
def api_move():
    if game_state is None:
        _init_game()

    data = request.get_json(force=True)
    block_type: str = data.get("block_type", "")
    position: list = data.get("position", [])
    orientation: str = data.get("orientation", "")
    flip: bool = data.get("flip", False)

    # --- validate inputs ---
    if not block_type or len(position) != 3 or orientation not in ("x", "y", "z"):
        return jsonify({"error": "Invalid move parameters"}), 400

    if game_state.current_player != Player.WHITE:
        return jsonify({"error": "Not your turn"}), 400

    block = _find_block_by_type(game_state, block_type)
    if block is None:
        return jsonify({"error": f"No remaining {block_type} blocks"}), 400

    pos_tuple = tuple(position)

    # --- execute human move ---
    success = game_state.make_move(block, pos_tuple, orientation, flip)
    if not success:
        return jsonify({"error": "Illegal move"}), 400

    human_cells = _placed_cells(block, pos_tuple, orientation, flip)
    human_move_info = {
        "player": "white",
        "block_type": block_type,
        "position": list(pos_tuple),
        "orientation": orientation,
        "flip": flip,
        "cells": human_cells,
    }
    move_log.append(human_move_info)

    # --- AI responds ---
    ai_move_info = None
    if not game_state.is_game_over():
        ai_move = ai_strategy.choose_move(game_state, Player.BLACK)
        if ai_move is not None:
            ai_block, ai_pos, ai_orient, ai_flip = ai_move
            game_state.make_move(*ai_move)
            ai_cells = _placed_cells(ai_block, ai_pos, ai_orient, ai_flip)
            ai_move_info = {
                "player": "black",
                "block_type": _block_type_key(ai_block),
                "position": list(ai_pos),
                "orientation": ai_orient,
                "flip": ai_flip,
                "cells": ai_cells,
            }
            move_log.append(ai_move_info)

    # --- build response ---
    legal = {}
    if not game_state.is_game_over():
        legal = _serialize_legal_moves(game_state)

    return jsonify({
        "state": _serialize_state(game_state),
        "human_move": human_move_info,
        "ai_move": ai_move_info,
        "legal_moves": legal,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _init_game()
    print("Starting Block Stacking Game server at http://localhost:8080")
    app.run(debug=True, port=8080)
