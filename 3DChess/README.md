# ♔ 3D Chess

A fully playable 3D chess game built with Python, Pygame, and OpenGL. Features a rotating 3D board, animated piece movement, time controls, save/load, and a live HUD with move history, captured pieces, and player clocks.

---

## Requirements

### Python
Python 3.8 or higher.

### Dependencies
Install all required packages with:

```bash
pip install pygame PyOpenGL PyOpenGL_accelerate numpy pywavefront
```

| Package | Purpose |
|---|---|
| `pygame` | Window, input, 2D overlay rendering |
| `PyOpenGL` | 3D board and piece rendering |
| `numpy` | Shadow circle geometry |
| `pywavefront` | Loading `.obj` 3D piece models |

---

## Project Structure

```
project/
├── main.py          # Main game file
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

> **Note:** If a model file is missing, the piece falls back to a simple 3D box placeholder so the game still runs.

---

## Running the Game

```bash
python main.py
```

The game launches immediately with a **10-minute timer** per player (default). No setup screen — just start playing.

---

## Features

### 3D Board & Pieces
- Full 3D perspective view with dynamic lighting (two light sources).
- Pieces rendered from `.obj` models; auto-scaled and centred on squares.
- Smooth slide animation for every move.
- Circular drop shadows under each piece.
- Board coordinate labels (a–h, 1–8) projected onto the 3D view.
- Two board colour themes: **Classic** (wood tones) and **Dark Blue**.

### Chess Rules
- All standard moves: pawns, rooks, knights, bishops, queens, kings.
- Castling (kingside and queenside).
- En passant capture.
- Pawn promotion (choose queen, rook, bishop, or knight via popup menu).
- Full check and checkmate detection with flashing king highlight.
- Stalemate detection.
- Legal move validation — illegal moves that leave the king in check are blocked.

### HUD / Overlay
- **Move history panel** (top-left): White and Black moves shown side by side in algebraic notation, scrolling as the game progresses.
- **Turn indicator** (top-right): Shows whose turn it is with a colour-coded badge.
- **CHECK! banner**: Appears in the centre when the current player is in check.
- **Valid move highlights**: Green squares for legal destinations, red for captures, yellow for the selected piece.
- **Controls panel** (bottom-left): Quick reference for all keyboard and mouse controls.

### Captured Pieces Panel
Displayed on the right side of the screen, split into two strips:

| Panel | Background | Piece colour | Shows |
|---|---|---|---|
| **Captured by Black** (top) | Dark | White symbols | White pieces taken by Black |
| **Captured by White** (bottom) | Light/cream | Dark symbols | Black pieces taken by White |

A **material advantage badge** (`+N`) appears next to the leading player's captured strip — white badge on the dark panel, dark badge on the light panel, so it is always readable.

### Time Controls
- Default time is **10 minutes per player**, active from the very first move.
- When starting a **New Game**, a time-selection screen lets you pick **10 min**, **15 min**, **30 min**, or **No Timer**.
- Each player's clock is shown on the right panel — Black's clock at the top, White's at the bottom.
- The **active clock** glows green. Clocks turn **red** when under 30 seconds.
- If a player's time reaches zero, the game ends immediately with a "flag fallen" result.
- Time is **frozen while the game is paused**.

### Pause
- Click the **⏸ Pause** button (between the two clocks) or press **P** to pause.
- While paused, the board area dims and a "PAUSED" banner appears. All piece interaction and clock ticking is suspended.
- Click **▶ Resume** or press **P** / **Esc** to continue.

### Save & Load
- **Save** writes a JSON file to the `saves/` folder containing: board position, captured pieces, move history, whose turn it is, and the **remaining clock time for both players**.
- **Load** fully restores all of the above — including the exact seconds left on each clock at the time of saving.
- Up to 8 recent saves are shown in the load menu (most recent first).
- Older saves without time data load gracefully, giving each player the full `time_control` duration.

### Game Over Screen
Appears on checkmate, stalemate, or flag fall. Displays the result and reason, then offers:
- **New Game** — opens the time-selection screen.
- **Save & Quit** — saves the final position before returning to the menu.
- **Load Game** — open the load menu.
- **Quit App** — exits.

---

## Controls

### Mouse
| Action | Effect |
|---|---|
| Left-click a piece | Select it (highlights legal moves) |
| Left-click a highlighted square | Move the selected piece |
| Left-click the selected piece again | Deselect |
| Left-drag | Orbit / rotate the camera |
| Scroll wheel | Zoom in / out |

### Keyboard
| Key | Action |
|---|---|
| `←` / `→` | Rotate camera left / right |
| `↑` / `↓` | Tilt camera up / down |
| `Z` / `X` | Zoom in / out |
| `M` | Toggle board colour theme |
| `P` | Pause / Resume |
| `S` | Quick-save to slot 1 |
| `L` | Open load game menu |
| `N` | New game (opens time-selection screen) |
| `R` | Hard reset (same as New Game) |
| `Q` | Resign / quit to game-over screen |
| `Esc` | Deselect piece · Close load menu · Resume if paused |

---

## Configuration

A few constants at the top of `main3.py` can be tweaked without touching the rest of the code:

| Constant | Default | Description |
|---|---|---|
| `WIDTH, HEIGHT` | `900, 650` | Window size in pixels |
| `camera_angle_x` | `35.0` | Initial camera tilt |
| `camera_angle_y` | `-30.0` | Initial camera rotation |
| `camera_distance` | `28.0` | Initial zoom level |
| `animation_speed` | `0.18` | Piece slide speed (squares per frame) |
| `time_control` | `10*60` | Default game time in seconds per player |
| `board_color_theme` | `"black_white"` | Starting theme (`"black_white"` or `"dark_blue"`) |

---

## Save File Format

Saves are stored as human-readable JSON in `saves/`. Each file contains:

```json
{
  "current_turn": "white",
  "pieces": [ { "name": "king", "color": "white", "col": 3.0, "row": 0.0, "has_moved": false }, "..." ],
  "captured_by_white": ["pawn", "knight"],
  "captured_by_black": ["pawn"],
  "move_history": [ { "piece": "pawn", "color": "white", "from": [4, 1], "to": [4, 3], "label": "e2e4" }, "..." ],
  "last_pawn_double": null,
  "white_time": 534.2,
  "black_time": 489.7,
  "time_control": 600
}
```

---

## Known Limitations

- Two-player local only — no AI opponent or online play.
- The game window is a fixed size (900 × 650); resizing is not supported.
- `.obj` models must be named exactly `{color}_{piece}.obj` (e.g. `white_knight.obj`).
