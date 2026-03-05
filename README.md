# Multi-Stream Video Viewer

Synchronized multi-source video viewer with grid display and recording.

## Requirements

```bash
pip install opencv-python numpy
```

---

## Quick Start

1. **Edit `sources.txt`** — add your video sources (files, cameras, RTSP URLs):
   ```
   /videos/cam1.mp4
   /videos/cam2.mp4
   0
   rtsp://192.168.1.10:554/stream
   ```

2. **Run the viewer:**
   ```bash
   python multi_stream_viewer.py sources.txt
   ```

---

## Usage

```
python multi_stream_viewer.py <sources_file> [options]
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--n-cols N` | `2` | Columns in the display grid |
| `--cell-width W` | `640` | Width of each stream cell (px) |
| `--cell-height H` | `360` | Height of each stream cell (px) |
| `--fps F` | auto | Override target FPS |
| `--buffer N` | `30` | Per-stream frame buffer size |
| `--output-dir DIR` | `./output` | Directory for recordings |
| `--save-combined` | off | Save the full grid as one video |
| `--save-individual` | off | Save each stream separately |
| `--auto-save` | off | Start recording on launch |

---

## Examples

**4 streams in a 2×2 grid:**
```bash
python multi_stream_viewer.py sources.txt --n-cols 2
```

**6 streams in a 3×2 grid, small cells:**
```bash
python multi_stream_viewer.py sources.txt --n-cols 3 --cell-width 480 --cell-height 270
```

**Save combined grid video automatically:**
```bash
python multi_stream_viewer.py sources.txt --n-cols 2 --save-combined --auto-save
```

**Save each stream as a separate file:**
```bash
python multi_stream_viewer.py sources.txt --save-individual --output-dir my_recordings
```

**Save both combined and individual:**
```bash
python multi_stream_viewer.py sources.txt --save-combined --save-individual --auto-save
```

---

## Keyboard Controls (in viewer window)

| Key | Action |
|-----|--------|
| `Q` / `ESC` | Quit |
| `SPACE` | Pause / Resume |
| `S` | Toggle recording on/off |
| `+` / `=` | Increase cell size |
| `-` | Decrease cell size |

---

## Grid Layout

Given N streams and `--n-cols C`, the grid is:
- **Rows** = ⌈N / C⌉
- Empty slots are filled with black

Examples:
- 4 streams, `--n-cols 2` → **2×2** grid
- 3 streams, `--n-cols 2` → **2×2** (last cell black)

---

## Source File Format (`sources.txt`)

```
# Lines starting with # are comments and ignored
# One source per line

0                                        # webcam index
/path/to/video.mp4                       # local file (loops)
rtsp://user:pass@192.168.1.10:554/live   # RTSP stream
http://example.com/live/stream.m3u8      # HTTP stream
```

---

## Synchronization

All streams are synchronized to a common FPS (minimum of all stream FPS, or `--fps` override).  
Each stream runs in its own background thread with a ring buffer.  
If a stream lags, the last received frame is reused to keep the grid in sync.  
File streams loop automatically.
