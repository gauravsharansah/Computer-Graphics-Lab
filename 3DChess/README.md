# ♚ 3D Chess

A fully playable two-player 3D chess game built with Python, Pygame, and OpenGL. Features a rotating 3D board rendered in a garden-style scene, smooth piece animation, complete chess rules, time controls, pause, save/load, and a live HUD.

---

## Requirements

**Python 3.8+**

Install all dependencies with:

```bash
pip install pygame PyOpenGL PyOpenGL_accelerate numpy pywavefront
```

| Package | Purpose |
|---|---|
| `pygame` | Window management, input, 2D overlay rendering |
| `PyOpenGL` | 3D board and piece rendering |
| `numpy` | Shadow circle geometry |
| `pywavefront` | Loading `.obj` 3D piece models |

---

## Project Structure

```
3DChess/
├── main.py        # Main game file (run this)
├── README.md
├── models/           # 3D piece model files (.obj)
│   ├── white_pawn.obj
│   ├── white_rook.obj
│   ├── white_knight.obj
│   ├── white_bishop.obj
│   ├── white_queen.obj
│   ├── white_king.obj
│   ├── black_pawn.obj
│   ├── black_rook.obj
│   ├── black_knight.obj
│   ├── black_bishop.obj
│   ├── black_queen.obj
│   └── black_king.obj
└── saves/            # Auto-created; stores saved game JSON files
```

> If a model file is missing the piece renders as a simple 3D box so the game still runs.

---

## Running

```bash
python main.py
```

The game launches immediately with a **10-minute timer per player** (default). A time-selection screen appears — pick a time control or "No Timer" to begin.

---

## Features

### 3D Board & Scene
- Full 3D perspective view with dual-light Phong shading.
- Garden-style gradient background: sky blue at top fading to grass green at bottom.
- Pieces rendered from `.obj` models with automatic bounding-box scaling.
- Smooth linear-interpolation animation for every move.
- Circular drop shadows under each piece.
- Board coordinate labels (a–h files at bottom edge, 1–8 ranks at right edge) projected from 3D world positions into 2D screen space.
- Two board colour themes: **Classic** (wood tones) and **Red/White** — toggle with `M`.

### Chess Rules
- All standard moves: pawns, rooks, knights, bishops, queens, kings.
- Castling (kingside and queenside).
- En passant capture.
- Pawn promotion — popup shows large piece symbols; correct hollow/solid symbols per player colour.
- Full check and checkmate detection with blinking red king highlight (only the king actually in check flashes — the other king never incorrectly flashes).
- Stalemate detection.
- Full legal-move validation via board simulation — no move that leaves the king in check is allowed.

### HUD Panels

**Move History** (top-left): Shows White and Black moves paired row by row. Panel height grows from a minimum of 5 rows up to a fixed maximum of 15 rows. Once at 15 rows, the window slides forward one pair per new White move, always showing the most recent 15 pairs in chronological order top-to-bottom. Black's cell on the current bottom row is blank until Black responds.

**Turn Indicator** (top-right): Colour-coded badge showing whose turn it is.

**CHECK! Banner** (centre-top): Appears when the current player is in check.

**Captured Pieces Panel** (right side, two strips):
- Top strip (dark background, white symbols): pieces captured by Black.
- Bottom strip (light background, dark symbols): pieces captured by White.
- Material advantage badge (`+N`) shown in the correct contrasting colour.

**Clock Display** (right side): Black's clock at the top, White's at the bottom. Active player's clock glows green. Under 30 seconds turns red. Clocks freeze while paused or while a piece is animating.

**Pause / Resume Button**: Centred between the two player blocks on the right panel.

**Controls Panel** (bottom-left, 3 columns): Quick-reference for all mouse and keyboard controls.

### Time Controls
- Default: 10 minutes per player, active from the first move.
- New Game time-selection screen: 10 min / 15 min / 30 min / No Timer.
- Flag fall: if a player's clock reaches zero the game ends immediately.
- Clocks are saved and restored exactly when loading a saved game.

### Pause
- Press **P** or click the **Pause** button to pause. Press **P** / **Esc** or click **Resume** to continue.
- While paused: clocks freeze, board clicks are blocked, the board area dims with a "PAUSED" banner.

### Save & Load
- Games are saved to the `saves/` folder as `Game01.json`, `Game02.json`, in sequential order.
- **No save is created at the starting position** (zero moves played).
- **No duplicate saves**: pressing S twice at the same position only creates one file; a second save is only created after at least one new move is played.
- **Auto-save**: the game is automatically saved when it ends by checkmate, stalemate, or flag fall. A golden notification banner appears for 5 seconds confirming the filename.
- **Manual save** (`S` key): creates a new sequential file; a green notification banner appears for 5 seconds.
- **Save & Quit** button on the game-over screen: also saves sequentially.
- **Load** (`L` key or game-over button): shows the 8 most recent saves. A notification banner appears for 5 seconds on successful load.
- All notifications (save, load, auto-save) display for exactly **5 real seconds** using elapsed-millisecond timing — not frame counts.

### Game Over Screen
Appears on checkmate, stalemate, flag fall, or quit (`Q`). Shows result and reason, then offers New Game, Save & Quit, Load Game, Quit App.

---

## Controls

### Mouse
| Action | Effect |
|---|---|
| Left-click a piece | Select it (highlights legal moves) |
| Left-click a highlighted square | Move the selected piece |
| Left-click the selected piece again | Deselect |
| Left-drag (no piece selected) | Orbit / rotate the camera |
| Scroll wheel | Zoom in / out |

> The camera cannot be orbited while a piece is selected or while a piece is animating.

### Keyboard
| Key | Action |
|---|---|
| `←` / `→` | Rotate camera left / right |
| `↑` / `↓` | Tilt camera up / down |
| `Z` / `X` | Zoom in / out |
| `M` | Toggle board colour theme |
| `S` | Save current game |
| `L` | Open load game menu |
| `N` | New game (shows time-selection screen) |
| `P` | Pause / Resume |
| `Q` | Quit current game (shows game-over screen) |
| `R` | Hard reset — deletes all saved games and starts fresh |
| `Esc` | Deselect piece · Close load menu · Resume if paused |

---

## Save File Format

```json
{
  "current_turn": "white",
  "pieces": [{ "name": "king", "color": "white", "col": 3.0, "row": 0.0, "has_moved": false }],
  "captured_by_white": ["pawn"],
  "captured_by_black": [],
  "move_history": [{ "piece": "pawn", "color": "white", "from": [4,1], "to": [4,3], "label": "e2e4" }],
  "last_pawn_double": null,
  "white_time": 534.2,
  "black_time": 489.7,
  "time_control": 600
}
```

---

## Configuration

Constants at the top of `main_v6.py`:

| Constant | Default | Description |
|---|---|---|
| `WIDTH, HEIGHT` | `900, 650` | Window size in pixels |
| `camera_angle_x` | `47.0` | Initial camera tilt |
| `camera_angle_y` | `180.0` | Initial camera rotation |
| `camera_distance` | `28.0` | Initial zoom level |
| `animation_speed` | `0.36` | Piece slide speed (squares per frame) |
| `time_control` | `10*60` | Default game time in seconds per player |
| `board_color_theme` | `"black_white"` | Starting theme |

---

## Known Limitations

- Two-player local only — no AI opponent or network play.
- Fixed window size (900 × 650); resizing is not supported.
- Model files must be named exactly `{color}_{piece}.obj` (e.g. `white_knight.obj`).
