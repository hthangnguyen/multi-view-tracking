import cv2
import numpy as np

from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

# ─────────────────────────────────────────────────────────────
# Saver
# ─────────────────────────────────────────────────────────────

class Saver:
    def __init__(self, output_dir: str, fps: float, save_combined: bool,
                 save_individual: bool, n_streams: int,
                 combined_size: Optional[Tuple[int, int]] = None,
                 individual_sizes: Optional[List[Tuple[int, int]]] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.save_combined = save_combined
        self.save_individual = save_individual
        self.n_streams = n_streams

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        self.combined_writer: Optional[cv2.VideoWriter] = None
        self.individual_writers: List[cv2.VideoWriter] = []

        if save_combined and combined_size:
            path = str(self.output_dir / f"combined_{ts}.mp4")
            self.combined_writer = cv2.VideoWriter(path, fourcc, fps, combined_size)
            print(f"[Saver] Combined → {path}")

        if save_individual and individual_sizes:
            for i, sz in enumerate(individual_sizes):
                path = str(self.output_dir / f"stream_{i+1}_{ts}.mp4")
                w = self.individual_writers.__len__()
                writer = cv2.VideoWriter(path, fourcc, fps, sz)
                self.individual_writers.append(writer)
                print(f"[Saver] Stream {i+1} → {path}")

    def write(self, combined: Optional[np.ndarray], individuals: List[np.ndarray]):
        if self.combined_writer and combined is not None:
            self.combined_writer.write(combined)
        for i, w in enumerate(self.individual_writers):
            if i < len(individuals):
                w.write(individuals[i])

    def release(self):
        if self.combined_writer:
            self.combined_writer.release()
        for w in self.individual_writers:
            w.release()
        print("[Saver] All writers closed.")

