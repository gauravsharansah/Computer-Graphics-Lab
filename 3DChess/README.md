# ♟️ 3D Chess

A fully playable 3D chess game built with Python, Pygame, and OpenGL. Pieces are rendered using `.obj` 3D models with smooth animation, lighting, and an interactive camera — all from a single script.

---

## Features

- **3D rendered board and pieces** using PyOpenGL with lighting and specular materials
- **Full chess rule enforcement** including castling, en passant, pawn promotion, check, checkmate, and stalemate detection
- **Smooth piece animations** as pieces glide to their destination squares
- **Move highlighting** to show legal squares for the selected piece
- **Check flash effect** — the king pulses red when in check
- **Pawn promotion menu** with interactive piece selection (Queen, Rook, Bishop, Knight)
- **Save / Load system** — save to a timestamped file or a quick slot, load from a scrollable menu
- **Move history** tracking in algebraic-style notation
- **Captured piece tracking** for both sides
- **Two board color themes** — Brown & White and Dark Blue
- **Fallback box rendering** if `.obj` model files are missing

---

## Requirements

- Python 3.8+
- [pygame](https://pypi.org/project/pygame/)
- [PyOpenGL](https://pypi.org/project/PyOpenGL/)
- [numpy](https://pypi.org/project/numpy/)
- [pywavefront](https://pypi.org/project/PyWavefront/)

Install all dependencies with:

```bash
pip install pygame PyOpenGL numpy PyWavefront
```

---

## Project Structure

```
project/
├── main.py          # Main game script
├── models/          # 3D .obj model files for pieces
│   ├── white_pawn.obj
│   ├── white_rook.obj
│   ├── white_knight.obj
│   ├── white_bishop.obj
│   ├── white_queen.obj
│   ├── white_king.obj
│   ├── black_pawn.obj
│   └── ...
└── saves/           # Auto-created; stores JSON save files
```

> If `models/` is absent or a model is missing, pieces will be rendered as simple 3D boxes automatically.

---

## Running the Game

```bash
python main.py
```

---

## Controls

### Mouse
| Action | Control |
|---|---|
| Select / move a piece | Left click |
| Rotate camera | Click and drag |
| Zoom in / out | Scroll wheel |

### Keyboard
| Key | Action |
|---|---|
| `R` or `N` | New game |
| `S` | Save game (slot 1) |
| `L` | Open load menu |
| `M` | Toggle board color theme |
| `Q` | Resign (ends game as draw) |
| `ESC` | Deselect piece / close menu |
| `←` / `→` | Rotate camera left / right |
| `↑` / `↓` | Tilt camera up / down |
| `Z` / `X` | Zoom in / out |

---

## Save System

Games are saved as JSON files in the `saves/` directory. Each save stores the full board state, captured pieces, move history, and whose turn it is. Up to 8 recent saves are shown in the load menu.

---

## Chess Rules Implemented

- Standard piece movement for all 6 piece types
- **Castling** (kingside and queenside) — only if neither piece has moved and the path is clear
- **En passant** capture
- **Pawn promotion** with a graphical selection menu
- **Check detection** with visual flash indicator
- **Checkmate and stalemate** detection ending the game
- Moves that would leave the player's own king in check are blocked

---

## License

This project is released for personal and educational use.
