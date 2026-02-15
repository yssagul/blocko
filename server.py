#!/usr/bin/env python3
"""
Flask backend for the 4x4x4 Block Stacking Game.
Supports single-player vs AI (REST) and online multiplayer (SocketIO).
"""

import eventlet
eventlet.monkey_patch()

import os
import random
import string
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from blocko.core import (GameState, OpenGridGameState, Player, Color, Block,
                         PlacedBlock, RandomDrawGameState,
                         RandomDrawOpenGridGameState)
from blocko.strategies import StrategicAIStrategy

HERE = Path(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ---------------------------------------------------------------------------
# Global game state  (single-player vs AI)
# ---------------------------------------------------------------------------
game_state: GameState | None = None
ai_strategy = StrategicAIStrategy()
move_log: list[dict] = []
game_mode: str = "standard"
human_player: Player = Player.WHITE   # randomised each game

# ---------------------------------------------------------------------------
# Multiplayer room management
# ---------------------------------------------------------------------------
VALID_MODES = ("standard", "open_grid", "random_draw", "random_draw_open_grid")

rooms_store: dict[str, dict] = {}   # room_code → room dict
sid_to_room: dict[str, str] = {}    # socket session id → room_code


# ---------------------------------------------------------------------------
# Shared helpers
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


def _is_random_draw() -> bool:
    """Return True if the current game mode uses random draw."""
    return game_mode in ("random_draw", "random_draw_open_grid")


def _is_random_draw_mode(mode: str) -> bool:
    """Return True if the given mode string uses random draw."""
    return mode in ("random_draw", "random_draw_open_grid")


def _human_color() -> str:
    """Return the human player's color name (lowercase)."""
    return human_player.name.lower()


def _ai_player() -> Player:
    """Return the AI's Player enum."""
    return Player.BLACK if human_player == Player.WHITE else Player.WHITE


def _placed_cells(block: Block, position: tuple, orientation: str, flip: bool):
    """Return the two [x,y,z] cells a placement occupies."""
    pb = PlacedBlock(block, position, orientation, flip)
    return [list(p) for p in pb.get_occupied_positions()]


def _create_game_state(mode: str) -> GameState:
    """Create a fresh GameState for the given mode (does NOT touch globals)."""
    if mode == "random_draw_open_grid":
        return RandomDrawOpenGridGameState()
    elif mode == "random_draw":
        return RandomDrawGameState()
    elif mode == "open_grid":
        return OpenGridGameState()
    else:
        return GameState()


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialize_state(game: GameState) -> dict:
    """Serialize the full game state into a JSON-safe dict (single-player)."""
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

    state = {
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
        "human_player": _human_color(),
    }

    if _is_random_draw() and hasattr(game, 'drawn_block') and game.drawn_block is not None:
        state["drawn_block"] = _block_type_key(game.drawn_block)
    else:
        state["drawn_block"] = None

    return state


def _serialize_room_state(game: GameState, room: dict, for_player: str) -> dict:
    """Serialize game state for a multiplayer room."""
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
    mode = room["game_mode"]

    state = {
        "grid": grid,
        "white_score": white_score,
        "black_score": black_score,
        "current_player": game.current_player.name.lower(),
        "game_over": game.is_game_over(),
        "remaining_blocks": remaining,
        "move_count": len(game.move_history),
        "move_log": room["move_log"],
        "bounds": {
            "x_min": bounds[0], "x_max": bounds[1],
            "y_min": bounds[2], "y_max": bounds[3],
            "z_min": bounds[4], "z_max": bounds[5],
        },
        "mode": mode,
        "human_player": for_player,
        "drawn_block": None,
    }

    is_rd = _is_random_draw_mode(mode)
    if is_rd and hasattr(game, 'drawn_block') and game.drawn_block is not None:
        state["drawn_block"] = _block_type_key(game.drawn_block)

    return state


def _serialize_legal_moves(game: GameState) -> dict:
    """
    Return legal moves in a compact lookup structure:
      { block_type: { orientation: { "true"/"false": [[x,y,z], ...] } } }
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


# ---------------------------------------------------------------------------
# Single-player helpers
# ---------------------------------------------------------------------------

def _init_game(mode: str = "standard"):
    """Create a fresh game and clear the log.  Randomly pick who goes first."""
    global game_state, move_log, game_mode, human_player
    game_mode = mode
    human_player = random.choice([Player.WHITE, Player.BLACK])
    game_state = _create_game_state(mode)
    move_log = []


# ---------------------------------------------------------------------------
# REST Routes  (single-player vs AI)
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
    _init_game(mode=mode)

    ai_color = _ai_player()
    ai_first_move = None

    # If AI goes first (human is BLACK, so AI is WHITE which always starts)
    if human_player == Player.BLACK:
        if _is_random_draw():
            drawn = game_state.draw_piece()
            if drawn is not None:
                ai_move = ai_strategy.choose_move(game_state, ai_color)
                if ai_move is not None:
                    ai_block, ai_pos, ai_orient, ai_flip = ai_move
                    game_state.make_move(*ai_move)
                    ai_cells = _placed_cells(ai_block, ai_pos, ai_orient, ai_flip)
                    ai_first_move = {
                        "player": ai_color.name.lower(),
                        "block_type": _block_type_key(ai_block),
                        "position": list(ai_pos),
                        "orientation": ai_orient,
                        "flip": ai_flip,
                        "cells": ai_cells,
                    }
                    move_log.append(ai_first_move)
        else:
            ai_move = ai_strategy.choose_move(game_state, ai_color)
            if ai_move is not None:
                ai_block, ai_pos, ai_orient, ai_flip = ai_move
                game_state.make_move(*ai_move)
                ai_cells = _placed_cells(ai_block, ai_pos, ai_orient, ai_flip)
                ai_first_move = {
                    "player": ai_color.name.lower(),
                    "block_type": _block_type_key(ai_block),
                    "position": list(ai_pos),
                    "orientation": ai_orient,
                    "flip": ai_flip,
                    "cells": ai_cells,
                }
                move_log.append(ai_first_move)

    # In RandomDraw modes, draw a piece for the current player (human)
    if _is_random_draw() and not game_state.is_game_over():
        game_state.draw_piece()

    resp = {
        "state": _serialize_state(game_state),
        "legal_moves": _serialize_legal_moves(game_state),
        "ai_move": ai_first_move,
    }
    return jsonify(resp)


@app.route("/api/move", methods=["POST"])
def api_move():
    if game_state is None:
        _init_game()

    data = request.get_json(force=True)
    block_type: str = data.get("block_type", "")
    position: list = data.get("position", [])
    orientation: str = data.get("orientation", "")
    flip: bool = data.get("flip", False)

    ai_color = _ai_player()

    # --- validate inputs ---
    if not block_type or len(position) != 3 or orientation not in ("x", "y", "z"):
        return jsonify({"error": "Invalid move parameters"}), 400

    if game_state.current_player != human_player:
        return jsonify({"error": "Not your turn"}), 400

    # In RandomDraw mode, the player must use the drawn block
    if _is_random_draw():
        if game_state.drawn_block is None:
            return jsonify({"error": "No piece drawn"}), 400
        drawn_type = _block_type_key(game_state.drawn_block)
        if block_type != drawn_type:
            return jsonify({"error": f"You must play the drawn piece ({drawn_type})"}), 400
        block = game_state.drawn_block
    else:
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
        "player": _human_color(),
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
        if _is_random_draw():
            drawn = game_state.draw_piece()
            if drawn is None:
                pass
            else:
                ai_move = ai_strategy.choose_move(game_state, ai_color)
                if ai_move is not None:
                    ai_block, ai_pos, ai_orient, ai_flip = ai_move
                    game_state.make_move(*ai_move)
                    ai_cells = _placed_cells(ai_block, ai_pos, ai_orient, ai_flip)
                    ai_move_info = {
                        "player": ai_color.name.lower(),
                        "block_type": _block_type_key(ai_block),
                        "position": list(ai_pos),
                        "orientation": ai_orient,
                        "flip": ai_flip,
                        "cells": ai_cells,
                    }
                    move_log.append(ai_move_info)
        else:
            ai_move = ai_strategy.choose_move(game_state, ai_color)
            if ai_move is not None:
                ai_block, ai_pos, ai_orient, ai_flip = ai_move
                game_state.make_move(*ai_move)
                ai_cells = _placed_cells(ai_block, ai_pos, ai_orient, ai_flip)
                ai_move_info = {
                    "player": ai_color.name.lower(),
                    "block_type": _block_type_key(ai_block),
                    "position": list(ai_pos),
                    "orientation": ai_orient,
                    "flip": ai_flip,
                    "cells": ai_cells,
                }
                move_log.append(ai_move_info)

    # In RandomDraw mode, draw the next piece for the human player
    if _is_random_draw() and not game_state.is_game_over():
        game_state.draw_piece()

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
# Multiplayer room helpers
# ---------------------------------------------------------------------------

def _generate_room_code() -> str:
    """Generate a unique 4-digit room code."""
    while True:
        code = ''.join(random.choices(string.digits, k=4))
        if code not in rooms_store:
            return code


def _leave_current_room(sid: str):
    """Remove a player from their current room and notify the opponent."""
    if sid not in sid_to_room:
        return

    code = sid_to_room.pop(sid)
    if code not in rooms_store:
        return

    room = rooms_store[code]
    leave_room(code)

    left_color = None
    if room["players"]["white"] == sid:
        room["players"]["white"] = None
        left_color = "white"
    elif room["players"]["black"] == sid:
        room["players"]["black"] = None
        left_color = "black"

    remaining_sid = room["players"]["white"] or room["players"]["black"]
    if remaining_sid and left_color:
        socketio.emit("opponent_disconnected", {
            "message": f"Your opponent ({left_color}) has left the game.",
        }, to=remaining_sid)

    # If both players gone, delete the room
    if room["players"]["white"] is None and room["players"]["black"] is None:
        del rooms_store[code]
    elif room["status"] == "playing":
        room["status"] = "finished"


def _cleanup_stale_rooms():
    """Remove rooms that have been waiting >30 min or finished >5 min."""
    now = time.time()
    to_delete = []
    for code, room in rooms_store.items():
        age = now - room.get("created_at", now)
        if room["status"] == "waiting" and age > 1800:
            to_delete.append(code)
        elif room["status"] == "finished" and age > 300:
            to_delete.append(code)
    for code in to_delete:
        for color in ("white", "black"):
            sid = rooms_store[code]["players"].get(color)
            if sid and sid in sid_to_room:
                del sid_to_room[sid]
        del rooms_store[code]


# ---------------------------------------------------------------------------
# SocketIO event handlers  (multiplayer)
# ---------------------------------------------------------------------------

@socketio.on("create_room")
def handle_create_room(data):
    sid = request.sid

    # Leave any existing room first
    if sid in sid_to_room:
        _leave_current_room(sid)

    # Periodic cleanup
    _cleanup_stale_rooms()

    mode = data.get("mode", "standard")
    if mode not in VALID_MODES:
        mode = "standard"

    code = _generate_room_code()
    game = _create_game_state(mode)

    rooms_store[code] = {
        "game_state": game,
        "move_log": [],
        "game_mode": mode,
        "players": {"white": sid, "black": None},
        "status": "waiting",
        "creator_sid": sid,
        "created_at": time.time(),
    }
    sid_to_room[sid] = code
    join_room(code)

    emit("room_created", {
        "room_code": code,
        "your_color": "white",
        "mode": mode,
    })


@socketio.on("join_room")
def handle_join_room(data):
    sid = request.sid
    code = data.get("room_code", "").strip()

    if not code or code not in rooms_store:
        emit("join_error", {"error": "Room not found. Check your code and try again."})
        return

    room = rooms_store[code]

    if room["status"] != "waiting":
        emit("join_error", {"error": "Game already in progress or room is full."})
        return

    if room["players"]["white"] == sid:
        emit("join_error", {"error": "You are already in this room."})
        return

    # Leave any existing room first
    if sid in sid_to_room:
        _leave_current_room(sid)

    room["players"]["black"] = sid
    room["status"] = "playing"
    sid_to_room[sid] = code
    join_room(code)

    # Notify joiner
    emit("room_joined", {
        "room_code": code,
        "your_color": "black",
        "mode": room["game_mode"],
    })

    # Notify creator
    emit("opponent_joined", {
        "opponent_color": "black",
    }, to=room["players"]["white"])

    # In RandomDraw modes, draw the first piece for White
    game = room["game_state"]
    is_rd = _is_random_draw_mode(room["game_mode"])
    if is_rd:
        game.draw_piece()

    # Send game_start to both players
    white_sid = room["players"]["white"]
    black_sid = room["players"]["black"]
    legal = _serialize_legal_moves(game) if not game.is_game_over() else {}

    emit("game_start", {
        "state": _serialize_room_state(game, room, "white"),
        "legal_moves": legal,
        "your_color": "white",
    }, to=white_sid)

    emit("game_start", {
        "state": _serialize_room_state(game, room, "black"),
        "legal_moves": {},
        "your_color": "black",
    }, to=black_sid)


@socketio.on("game_move")
def handle_game_move(data):
    sid = request.sid

    if sid not in sid_to_room:
        emit("move_error", {"error": "You are not in a room."})
        return

    code = sid_to_room[sid]
    room = rooms_store.get(code)
    if not room:
        emit("move_error", {"error": "Room not found."})
        return

    game = room["game_state"]

    if room["status"] != "playing":
        emit("move_error", {"error": "Game is not in progress."})
        return

    # Determine which player this socket is
    if room["players"]["white"] == sid:
        player_color = "white"
        player_enum = Player.WHITE
    elif room["players"]["black"] == sid:
        player_color = "black"
        player_enum = Player.BLACK
    else:
        emit("move_error", {"error": "You are not a player in this room."})
        return

    # Turn validation
    if game.current_player != player_enum:
        emit("move_error", {"error": "It's not your turn."})
        return

    # Parse move data
    block_type = data.get("block_type", "")
    position = data.get("position", [])
    orientation = data.get("orientation", "")
    flip = data.get("flip", False)

    if not block_type or len(position) != 3 or orientation not in ("x", "y", "z"):
        emit("move_error", {"error": "Invalid move parameters."})
        return

    is_rd = _is_random_draw_mode(room["game_mode"])

    # Find the block
    if is_rd:
        if game.drawn_block is None:
            emit("move_error", {"error": "No piece drawn."})
            return
        drawn_type = _block_type_key(game.drawn_block)
        if block_type != drawn_type:
            emit("move_error", {"error": f"You must play the drawn piece ({drawn_type})."})
            return
        block = game.drawn_block
    else:
        block = _find_block_by_type(game, block_type)
        if block is None:
            emit("move_error", {"error": f"No remaining {block_type} blocks."})
            return

    pos_tuple = tuple(position)

    # Execute the move
    success = game.make_move(block, pos_tuple, orientation, flip)
    if not success:
        emit("move_error", {"error": "Illegal move."})
        return

    # Record the move
    cells = _placed_cells(block, pos_tuple, orientation, flip)
    move_info = {
        "player": player_color,
        "block_type": block_type,
        "position": list(pos_tuple),
        "orientation": orientation,
        "flip": flip,
        "cells": cells,
    }
    room["move_log"].append(move_info)

    # In RandomDraw mode, draw piece for the next player
    if is_rd and not game.is_game_over():
        game.draw_piece()

    # Check game over
    if game.is_game_over():
        room["status"] = "finished"

    # Build legal moves (only for the player whose turn it is)
    legal = {}
    if not game.is_game_over():
        legal = _serialize_legal_moves(game)

    # Emit to White
    white_sid = room["players"]["white"]
    black_sid = room["players"]["black"]

    if white_sid:
        emit("move_made", {
            "state": _serialize_room_state(game, room, "white"),
            "move": move_info,
            "legal_moves": legal if game.current_player == Player.WHITE else {},
        }, to=white_sid)

    if black_sid:
        emit("move_made", {
            "state": _serialize_room_state(game, room, "black"),
            "move": move_info,
            "legal_moves": legal if game.current_player == Player.BLACK else {},
        }, to=black_sid)


@socketio.on("leave_room")
def handle_leave_room(data=None):
    _leave_current_room(request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    _leave_current_room(request.sid)


@socketio.on("request_rematch")
def handle_request_rematch(data=None):
    sid = request.sid
    if sid not in sid_to_room:
        return

    code = sid_to_room[sid]
    room = rooms_store.get(code)
    if not room or room["status"] != "finished":
        return

    # Track rematch readiness
    if "rematch_ready" not in room:
        room["rematch_ready"] = set()
    room["rematch_ready"].add(sid)

    white_sid = room["players"]["white"]
    black_sid = room["players"]["black"]

    # Notify opponent
    opponent_sid = black_sid if sid == white_sid else white_sid
    if opponent_sid:
        emit("rematch_requested", {}, to=opponent_sid)

    # If both ready, start new game with swapped colours
    if (white_sid and black_sid and
            white_sid in room.get("rematch_ready", set()) and
            black_sid in room.get("rematch_ready", set())):

        # Swap colours
        room["players"]["white"], room["players"]["black"] = black_sid, white_sid
        white_sid, black_sid = room["players"]["white"], room["players"]["black"]

        # Reset game
        game = _create_game_state(room["game_mode"])
        room["game_state"] = game
        room["move_log"] = []
        room["status"] = "playing"
        room.pop("rematch_ready", None)

        # Handle RandomDraw: draw first piece for White
        is_rd = _is_random_draw_mode(room["game_mode"])
        if is_rd:
            game.draw_piece()

        legal = _serialize_legal_moves(game) if not game.is_game_over() else {}

        emit("game_start", {
            "state": _serialize_room_state(game, room, "white"),
            "legal_moves": legal,
            "your_color": "white",
        }, to=white_sid)

        emit("game_start", {
            "state": _serialize_room_state(game, room, "black"),
            "legal_moves": {},
            "your_color": "black",
        }, to=black_sid)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _init_game()
    print("Starting Block Stacking Game server at http://localhost:8080")
    socketio.run(app, debug=True, port=8080)
