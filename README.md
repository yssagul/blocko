# Blocko

A Monte Carlo simulation framework for the 4x4x4 Block Stacking Strategy Game.

## Game Overview

Two players (White and Black) take turns placing 1x1x2 blocks into a 4x4x4 cube. Each block has two colored halves (black, white, or red). Score is determined by exterior face visibility on 5 sides (top + 4 walls; bottom is not scored).

### Rules

- **32 blocks**: 3 BB, 3 WW, 8 BW, 9 BR, 9 WR
- Same non-red color cannot stack on itself (white-on-white and black-on-black are illegal)
- Red is wild (can go on anything, anything can go on red)
- All cells must be gravity-supported (no cantilevering)
- Game ends when no legal moves remain

### Scoring

Each cell on the 5 exterior faces (top, front, back, left, right) scores 1 point for its color's player. The bottom face is not scored. Corner cells can score on up to 3 faces; edge cells on 2; interior face cells on 1.

## Quick Start

### Installation

```bash
pip install -e .
```

### Run a simulation

```python
from blocko.strategies import StrategicAIStrategy, RandomStrategy
from blocko.simulation import play_game, run_monte_carlo

record = play_game(StrategicAIStrategy(), RandomStrategy())
print(f"White: {record.white_score}, Black: {record.black_score}")
```

### Play in the browser

```bash
pip install -e ".[server]"
python server.py
# Open http://localhost:8080
```

### Run meta analysis

```bash
python block_game_simulation.py
```

Or from Python:

```python
from blocko.analysis import run_meta_analysis
run_meta_analysis(num_games=500)
```

## Project Structure

```
blocko/                          # Main package
├── __init__.py
├── core/                        # Game engine fundamentals
│   ├── models.py                #   Color, Player, Block, PlacedBlock, exterior_faces()
│   ├── game_state.py            #   GameState (standard 4x4x4)
│   └── open_grid.py             #   OpenGridGameState (dynamic boundaries)
├── strategies/                  # AI strategies
│   ├── base.py                  #   Strategy ABC
│   ├── random.py                #   RandomStrategy
│   ├── greedy.py                #   GreedyStrategy
│   ├── defensive.py             #   DefensiveStrategy
│   ├── edge_control.py          #   EdgeControlStrategy
│   ├── blocking.py              #   BlockOpponentStrategy
│   ├── analytical.py            #   AntiRandomStrategy (7-component)
│   ├── strategic.py             #   StrategicAIStrategy (12-component + minimax)
│   └── mixed.py                 #   MixedStrategy (weighted ensemble)
├── simulation/                  # Game runner and tools
│   ├── game_record.py           #   GameRecord dataclass
│   ├── runner.py                #   play_game(), run_monte_carlo(), print_results()
│   └── validator.py             #   validate_game() — rule verification
└── analysis/                    # Statistical analysis
    └── meta.py                  #   6 meta-analyses + run_meta_analysis()

scripts/                         # Standalone benchmark scripts
├── random_draft_sim.py          #   Random block drafting variant
└── open_grid_benchmark.py       #   Standard vs Open Grid comparison

server.py                        # Flask backend (port 8080)
index.html                       # Three.js 3D browser frontend
block_game_simulation.py         # Backward-compat shim (re-exports from blocko.*)

archive/                         # Historical files
├── game_prototype_8.html        #   Earlier standalone HTML prototype
└── game_analysis/               #   One-off analysis notebooks
```

## Strategies

| Strategy | Approach | Complexity |
|---|---|---|
| `RandomStrategy` | Uniform random from legal moves | O(1) per candidate |
| `GreedyStrategy` | Maximize immediate score delta | O(n) with state copy |
| `DefensiveStrategy` | Minimize opponent scoring opportunities | O(n) with state copy |
| `EdgeControlStrategy` | Prioritize edge/corner exterior faces | O(1) per candidate |
| `BlockOpponentStrategy` | 3-component: score + stacking + coverage | O(1) per candidate |
| `AntiRandomStrategy` | 7-component analytical evaluator | O(1) per candidate |
| `StrategicAIStrategy` | 12-component analytical + minimax endgame | Hybrid: O(1) early, depth 2-4 late |
| `MixedStrategy` | Weighted random over other strategies | Depends on components |

### StrategicAIStrategy Details

Two-phase hybrid that addresses 7 identified weaknesses of simpler strategies:

- **Early/mid game** (>12 blocks remaining): 12-component analytical evaluation with 6-tier smart sampling
- **Endgame** (<=12 blocks): Alpha-beta minimax at adaptive depth (2-4 plies)

The 12 components evaluate: net score delta, top-layer permanence, corner premium, interior waste, future enablement, opponent top penalty, block efficiency, face coverage, constraint propagation, BW burial patterns, opponent block orientation, and edge column racing.

## Game Modes

- **Standard**: Fixed 4x4x4 grid at coordinates (0-3, 0-3, 0-3)
- **Open Grid**: Dynamic X/Y boundaries that float until each axis spans 4 cells, then lock. Z is always fixed (0-3). Enables negative coordinates and asymmetric board shapes.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/open_grid_benchmark.py` | Standard vs Open Grid mode balance comparison |
| `scripts/random_draft_sim.py` | Random block drafting variant simulation |

## Development

```bash
pip install -e ".[dev]"
```

### Adding a New Strategy

1. Create a new file in `blocko/strategies/` (e.g., `my_strategy.py`)
2. Subclass `Strategy` from `blocko.strategies.base` and implement `choose_move()`
3. Add the import to `blocko/strategies/__init__.py`
4. Test with: `play_game(MyStrategy(), RandomStrategy())`

### Adding a New Game Mode

1. Subclass `GameState` in `blocko/core/` (see `open_grid.py` as an example)
2. Override the relevant methods (move generation, legality, scoring, bounds)
3. Add `open_grid=` style parameter to `play_game()` in `blocko/simulation/runner.py`
4. Export from `blocko/core/__init__.py`
