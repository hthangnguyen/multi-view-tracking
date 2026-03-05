import cv2
import numpy as np
from typing import Optional, List

# ─────────────────────────────────────────────────────────────
# Grid Builder
# ─────────────────────────────────────────────────────────────

def build_grid(frames: List[np.ndarray], n_cols: int,
               cell_w: int = 640, cell_h: int = 360,
               labels: Optional[List[str]] = None,
               border: int = 0) -> np.ndarray:
    """
    Arrange frames into a grid with n_cols columns.
    Blank cells are filled with black if total frames < grid slots.
    """
    n = len(frames)
    n_rows = (n + n_cols - 1) // n_cols  # ceiling division

    cells = []
    for i, frame in enumerate(frames):
        cell = cv2.resize(frame, (cell_w, cell_h))
        # Draw border
        if border > 0:
            cell = cv2.copyMakeBorder(cell, border, border, border, border,
                                      cv2.BORDER_CONSTANT, value=(50, 50, 50))
        # Label overlay
        lbl = labels[i] if labels else f"Stream {i+1}"
        # cv2.rectangle(cell, (0, 0), (len(lbl) * 10 + 10, 22), (0, 0, 0), -1)
        # cv2.putText(cell, lbl, (5, 16),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 1, cv2.LINE_AA)
        cells.append(cell)

    # Pad to fill grid
    blank_cell = np.zeros((cell_h + 2*border, cell_w + 2*border, 3), dtype=np.uint8)
    while len(cells) < n_rows * n_cols:
        cells.append(blank_cell)

    rows_img = []
    for r in range(n_rows):
        row_cells = cells[r * n_cols: (r + 1) * n_cols]
        rows_img.append(np.hstack(row_cells))

    return np.vstack(rows_img)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def load_sources(filepath: str) -> List[str]:
    """Read stream sources from a text file (one per line, # = comment)."""
    sources = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                sources.append(line)
    return sources


def draw_hud(frame: np.ndarray, fps: float, frame_idx: int,
             saving: bool, paused: bool) -> np.ndarray:
    """Overlay status info on top-right corner."""
    h, w = frame.shape[:2]
    status_parts = []
    if paused:
        status_parts.append("PAUSED")
    if saving:
        status_parts.append("● REC")
    status_parts.append(f"FPS:{fps:.1f}")
    status_parts.append(f"F:{frame_idx}")
    status = "  ".join(status_parts)

    (tw, th), _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    x, y = w - tw - 12, 20
    # cv2.rectangle(frame, (x - 4, y - th - 4), (x + tw + 4, y + 4),
    #               (0, 0, 0), -1)
    color = (0, 60, 220) if saving else (200, 200, 200)
    # show status
    cv2.putText(frame, status, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

    # Key hint bar at bottom
    # hint = "[SPACE] Pause  [S] Save  [Q/ESC] Quit  [+/-] Resize"
    # cv2.rectangle(frame, (0, h - 22), (w, h), (0, 0, 0), -1)
    # cv2.putText(frame, hint, (6, h - 6),
    #             cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1, cv2.LINE_AA)
    return frame
