#!/usr/bin/env python3
"""
Multi-Stream Video Viewer
- Reads multiple video streams from a text file
- Synchronizes all streams by timestamp/frame rate
- Displays streams in a configurable grid layout (n_cols)
- Saves combined frame or individual streams
"""

import cv2

import time
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List

from saver import Saver
from synchronizer import Synchronizer, StreamReader
from utils import build_grid, load_sources, draw_hud

# ─────────────────────────────────────────────────────────────
# Main Viewer
# ─────────────────────────────────────────────────────────────

def run_viewer(args):
    # ── 1. Load sources
    sources = load_sources(args.src)
    if not sources:
        print("[ERROR] No sources found in file.")
        sys.exit(1)
    print(f"[INFO] Loaded {len(sources)} source(s).")

    n_cols = max(1, args.n_cols)
    cell_w = args.cell_width
    cell_h = args.cell_height

    # ── 2. Open streams
    readers: List[StreamReader] = []
    labels: List[str] = []
    for i, src in enumerate(sources):
        r = StreamReader(src, i, buffer_size=args.buffer)
        if not r.open():
            print(f"[WARNING] Stream {i+1} failed to open ({src}): {r.error}")
            # Still add a dummy placeholder
        readers.append(r)
        labels.append(Path(str(src)).name if os.path.isfile(str(src)) else str(src))

    if not any(r.cap and r.cap.isOpened() for r in readers):
        print("[ERROR] No streams could be opened.")
        sys.exit(1)

    # ── 3. Determine target FPS (use min across opened streams)
    opened_fps = [r.fps for r in readers if r.cap and r.cap.isOpened()]
    target_fps = min(opened_fps) if opened_fps else 30.0
    if args.fps:
        target_fps = args.fps
    frame_delay = 1.0 / target_fps
    print(f"[INFO] Target FPS: {target_fps:.2f}")

    # ── 4. Start reading threads
    for r in readers:
        if r.cap and r.cap.isOpened():
            r.start()

    sync = Synchronizer(readers, target_fps)

    # ── 5. Warm-up: grab first sync set to know sizes
    print("[INFO] Warming up streams...")
    time.sleep(0.5)
    init_frames = sync.get_sync_frames()

    # Compute combined grid size
    border = 2
    grid_cell_w = cell_w + 2 * border
    grid_cell_h = cell_h + 2 * border
    n_rows = (len(readers) + n_cols - 1) // n_cols
    combined_w = n_cols * grid_cell_w
    combined_h = n_rows * grid_cell_h

    # ── 6. Saver setup (lazy — only created when user presses S)
    saver: Optional[Saver] = None
    saving = False

    def start_saving():
        nonlocal saver, saving
        ind_sizes = [(r.width, r.height) if (r.width and r.height) else (cell_w, cell_h)
                     for r in readers]
        saver = Saver(
            output_dir=args.output_dir,
            fps=target_fps,
            save_combined=args.save_combined or (not args.save_individual),
            save_individual=args.save_individual,
            n_streams=len(readers),
            combined_size=(combined_w, combined_h) if (args.save_combined or not args.save_individual) else None,
            individual_sizes=ind_sizes if args.save_individual else None,
        )
        saving = True
        print("[INFO] Recording started.")

    def stop_saving():
        nonlocal saver, saving
        if saver:
            saver.release()
            saver = None
        saving = False
        print("[INFO] Recording stopped.")

    if args.auto_save:
        start_saving()

    # ── 7. Display loop
    window = "Multi-Stream Viewer  (Q=Quit  SPACE=Pause  S=Toggle Save)"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, min(combined_w, 1280), min(combined_h, 720))

    paused = False
    frame_idx = 0
    fps_counter = 0
    fps_display = target_fps
    t_fps = time.time()
    last_frames = init_frames

    print("[INFO] Display started. Press Q or ESC to quit.")

    try:
        while True:
            t_start = time.time()

            if not paused:
                frames = sync.get_sync_frames()
                last_frames = frames
            else:
                frames = last_frames

            # Build grid
            grid = build_grid(frames, n_cols, cell_w, cell_h, labels, border)

            # HUD overlay
            grid = draw_hud(grid, fps_display, frame_idx, saving, paused)

            cv2.imshow(window, grid)

            # Write to disk if saving
            if saving and saver and not paused:
                saver.write(grid, frames)

            frame_idx += 1
            fps_counter += 1
            elapsed_fps = time.time() - t_fps
            if elapsed_fps >= 1.0:
                fps_display = fps_counter / elapsed_fps
                fps_counter = 0
                t_fps = time.time()

            # Key handling
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):  # Q or ESC
                break
            elif key == ord(' '):
                paused = not paused
                print(f"[INFO] {'Paused' if paused else 'Resumed'}")
            elif key in (ord('s'), ord('S')):
                if saving:
                    stop_saving()
                else:
                    start_saving()
            elif key in (ord('+'), ord('=')):
                cell_w = int(cell_w * 1.1)
                cell_h = int(cell_h * 1.1)
            elif key in (ord('-'), ord('_')):
                cell_w = max(160, int(cell_w * 0.9))
                cell_h = max(90, int(cell_h * 0.9))

            # Pace loop to target FPS
            elapsed = time.time() - t_start
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    finally:
        if saving:
            stop_saving()
        for r in readers:
            r.stop()
        cv2.destroyAllWindows()
        print("[INFO] All streams closed.")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Multi-Stream Video Viewer — synchronized grid display with optional recording",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "--src",
        type=str, default="sources.txt",
        help="Path to a .txt file listing one video source per line.\n"
             "Sources can be: file paths, RTSP/HTTP URLs, or camera indices (0, 1, …)",
    )
    p.add_argument(
        "--n-cols", type=int, default=2, dest="n_cols",
        help="Number of columns in the display grid (default: 2)",
    )
    p.add_argument(
        "--cell-width", type=int, default=640, dest="cell_width",
        help="Width of each cell in pixels (default: 640)",
    )
    p.add_argument(
        "--cell-height", type=int, default=360, dest="cell_height",
        help="Height of each cell in pixels (default: 360)",
    )
    p.add_argument(
        "--fps", type=float, default=None,
        help="Override target FPS (default: auto-detect from streams)",
    )
    p.add_argument(
        "--buffer", type=int, default=30,
        help="Per-stream frame buffer size (default: 30)",
    )
    p.add_argument(
        "--output-dir", type=str, default="output", dest="output_dir",
        help="Directory for saved recordings (default: ./output)",
    )
    p.add_argument(
        "--save-combined", action="store_true", dest="save_combined",
        help="Save the combined grid frame as a video file",
    )
    p.add_argument(
        "--save-individual", action="store_true", dest="save_individual",
        help="Save each stream as a separate video file",
    )
    p.add_argument(
        "--auto-save", action="store_true", dest="auto_save",
        help="Start recording immediately on launch",
    )
    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    run_viewer(args)