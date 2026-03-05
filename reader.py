from queue import Queue, Empty
import threading
from typing import Optional
import cv2
import os
import time
import numpy as np

# ─────────────────────────────────────────────────────────────
# Stream Reader (one per source)
# ─────────────────────────────────────────────────────────────

class StreamReader:
    def __init__(self, source: str, stream_id: int, buffer_size: int = 30):
        self.source = source
        self.stream_id = stream_id
        self.buffer_size = buffer_size

        self.cap = None
        self.fps = 30.0
        self.width = 0
        self.height = 0
        self.frame_count = 0
        self.is_file = False

        self.frame_queue: Queue = Queue(maxsize=buffer_size)
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.error: Optional[str] = None
        self._lock = threading.Lock()

    def open(self) -> bool:
        """Open the video source."""
        try:
            # Detect if source is a file or a live stream/camera
            if str(self.source).isdigit():
                self.cap = cv2.VideoCapture(int(self.source))
                self.is_file = False
            else:
                self.cap = cv2.VideoCapture(self.source)
                # Heuristic: local files exist on disk
                self.is_file = os.path.isfile(str(self.source))

            if not self.cap.isOpened():
                self.error = f"Cannot open source: {self.source}"
                return False

            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            return True
        except Exception as e:
            self.error = str(e)
            return False

    def _read_loop(self):
        """Background thread: continuously read frames into buffer."""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                break
            ret, frame = self.cap.read()
            if not ret:
                if self.is_file:
                    # Loop file streams
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    time.sleep(0.01)
                    continue
            try:
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                self.frame_queue.put_nowait(frame)
            except Exception:
                pass

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def get_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()

