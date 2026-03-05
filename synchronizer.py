import cv2
import numpy as np

from typing import Optional, List
from reader import StreamReader

# ─────────────────────────────────────────────────────────────
# Synchronizer
# ─────────────────────────────────────────────────────────────

class Synchronizer:
    """
    Pulls one frame from every stream, targeting a common FPS.
    Fills with the last good frame if a stream stalls.
    """
    def __init__(self, readers: List[StreamReader], target_fps: float = 30.0):
        self.readers = readers
        self.target_fps = target_fps
        self.last_frames: List[Optional[np.ndarray]] = [None] * len(readers)

    def get_sync_frames(self) -> List[np.ndarray]:
        frames = []
        for i, reader in enumerate(self.readers):
            frame = reader.get_frame(timeout=1.0 / self.target_fps)
            if frame is not None:
                self.last_frames[i] = frame
            elif self.last_frames[i] is not None:
                frame = self.last_frames[i]  # reuse last good frame
            else:
                # Placeholder: black frame
                h = reader.height or 360
                w = reader.width or 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                cv2.putText(frame, "No Signal", (w//2 - 60, h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 200), 2)
                self.last_frames[i] = frame
            frames.append(frame)
        return frames
