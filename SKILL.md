---
name: video-generation
description: Generate videos using Seedance 2.0 via proxy API endpoints. Trigger when the user says "seedance", "generate video", "create video", "make a video", "video generation", or any request to generate, create, or make videos.
---

# Video Generation

Generate videos using Seedance 2.0 through proxy endpoints.

## Configuration

Set the `GPT_IMAGE_API_KEY` environment variable with your API key.

> **Security note:** Prefer the environment variable over `--api-key`. CLI arguments are visible in shell history and process listings (`ps`, `top`). Never commit your key to version control.

## Quick Start

```bash
# Text-to-video (fast model, default 5s, 720p)
python scripts/generate_video.py "a cat playing piano in a cozy jazz club"

# Image-to-video (single image as first frame)
python scripts/generate_video.py "camera slowly pans right, warm lighting" \
  --image https://example.com/photo.jpg --model seedance-2-0

# First frame + last frame
python scripts/generate_video.py "a dramatic scene transition" \
  --first-frame https://example.com/start.jpg \
  --last-frame https://example.com/end.jpg

# Multimodal reference images (character consistency)
python scripts/generate_video.py "two warriors exploring a mystical forest" \
  --reference-image https://example.com/char1.jpg \
  --reference-image https://example.com/char2.jpg

# Sequential video generation (return last frame for next segment)
python scripts/generate_video.py "a warrior walking through a dark forest" \
  --reference-image https://example.com/char1.jpg \
  --return-last-frame --duration 5
# Use video_xxx_last_frame.png as --first-frame for the next segment

# Submit without waiting (fire and forget)
python scripts/generate_video.py "a cyberpunk city" --submit-only
# Then query later: python scripts/check_tasks.py task_xxx --poll --download

# Longer duration, custom resolution
python scripts/generate_video.py "a sports car driving along a coastal highway at sunset" \
  --model seedance-2-0 --duration 10 --resolution 1080p --aspect-ratio 16:9
```

## Model Selection

| Model | Best For | Speed |
|---|---|---|
| **seedance-2-0-fast** (default) | Quick drafts, rapid iteration | Fast |
| **seedance-2-0** | Final production quality | Slower, higher quality |

## Image Modes

Three image modes are supported. **They cannot be mixed.**

| Mode | Flags | Description |
|---|---|---|
| **First frame** | `--image <url>` | Single image as the first frame of the video |
| **First + last frame** | `--first-frame <url>` `--last-frame <url>` | Start and end with specific frames |
| **Reference images** | `--reference-image <url>` (repeatable) | 1-9 images for character/style consistency |

## Common Parameters

| Flag | Description | Default |
|---|---|---|
| `--model` | `seedance-2-0-fast` or `seedance-2-0` | `seedance-2-0-fast` |
| `--duration` | Video length in seconds (4–15) | `5` |
| `--aspect-ratio` | `16:9`, `9:16`, `1:1`, `4:3`, `3:2`, `2:3`, `adaptive` | `16:9` |
| `--resolution` | `480p`, `720p`, `1080p`, `2K` | `720p` |
| `--fps` | Frames per second | `30` |
| `--seed` | Random seed for reproducibility | auto |
| `--image` | Reference image URL (first frame mode) | none |
| `--first-frame` | First frame image URL | none |
| `--last-frame` | Last frame image URL | none |
| `--reference-image` | Reference image URL (repeatable) | none |
| `--generate-audio` | Generate synchronized audio | `true` |
| `--no-generate-audio` | Generate silent video | — |
| `--return-last-frame` | Return last frame PNG for chaining videos | `false` |
| `--camera-fixed` | Fix camera position | `false` |
| `--watermark` | Add AI Generated watermark | `false` |
| `--submit-only` | Submit task and return immediately | `false` |
| `--output-dir` | Directory to save the downloaded video | current dir |
| `--no-download` | Only return URL, do not download | `false` |
| `--poll-interval` | Seconds between status checks | `5` |
| `--max-wait` | Maximum seconds to wait for completion | `600` |

## Batch Task Query

Query one or more tasks, optionally poll until completion and auto-download:

```bash
# Query single task
python scripts/check_tasks.py task_xxx

# Query multiple tasks
python scripts/check_tasks.py task_xxx task_yyy task_zzz

# Poll until all complete, then download
python scripts/check_tasks.py task_xxx task_yyy --poll --download --output-dir ./videos
```

For full parameter details, resolution mappings, and advanced usage, see [`references/seedance-2-0.md`](references/seedance-2-0.md).
