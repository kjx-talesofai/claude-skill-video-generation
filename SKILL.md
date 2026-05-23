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

# Image-to-video with a local file (auto-converted to data URI)
python scripts/generate_video.py "camera slowly pans right, warm lighting" \
  --image ./local/photo.jpg --model seedance-2-0 --timeout 300

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
| **First frame** | `--image <url/path/uri>` | Single image as the first frame. Accepts URL, local file path, or data URI. |
| **First + last frame** | `--first-frame <url>` `--last-frame <url>` | Start and end with specific frames. URLs only. |
| **Reference images** | `--reference-image <url>` (repeatable) | 1-9 images for character/style consistency. URLs only. |

## Common Parameters

| Flag | Description | Default |
|---|---|---|
| `--model` | `seedance-2-0-fast` or `seedance-2-0` | `seedance-2-0-fast` |
| `--duration` | Video length in seconds (4–15) | `5` |
| `--aspect-ratio` | `16:9`, `9:16`, `1:1`, `4:3`, `3:2`, `2:3`, `3:4`, `21:9`, `adaptive` | `16:9` |
| `--resolution` | `480p`, `720p`, `1080p`, `2K` | `720p` |
| `--fps` | Frames per second | `30` |
| `--seed` | Random seed for reproducibility | auto |
| `--image` | Reference image for first frame mode (URL, local path, or data URI) | none |
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
| `--timeout` | HTTP request timeout in seconds | `60` |

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

## Limitations & Best Practices

### Face and Privacy Content
Seedance 2.0 does not support reference images containing real human faces. AI-generated character images may also be incorrectly flagged as real persons, returning `InputImageSensitiveContentDetected.PrivacyInformation`. If this occurs, use text-to-video mode (omit `--image`) or try a different reference image.

### Aspect Ratio
- **`adaptive`** lets the model automatically select a ratio based on the input prompt or reference images. **Different inputs may produce different output ratios.** When stitching multiple segments together, use a fixed ratio (e.g., `16:9`) instead of `adaptive` to ensure consistent dimensions.
- Supported ratios: `16:9`, `9:16`, `1:1`, `4:3`, `3:2`, `2:3`, `3:4`, `21:9`, `adaptive`.

### Concurrency
Submit no more than **3 tasks simultaneously** per account. Additional tasks will queue or fail.

### Large Image Uploads
When passing local images with `--image`, the file is base64-encoded into the request payload. For files larger than ~1 MB, increase `--timeout` (e.g., `--timeout 300`) to avoid `The read operation timed out`.

### Segment Chaining Best Practice
Seedance supports up to 15 seconds per segment. For a 30-second video, prefer **2 segments of 15 seconds** chained with `--return-last-frame` over many short segments. Fewer segments reduce overhead and improve consistency.

## Cross-Skill Workflow: Image Generation → Video Generation

When the workflow involves generating a reference image first (via the **image-generation** skill) and then animating it:

1. **Generate the image** with Gemini Image: outputs a local file.
2. **Pass the local file directly** to `generate_video.py --image`. The script auto-converts it to a data URI.

```bash
# Step 1: Generate image (image-generation skill)
python image-generation/scripts/generate_gemini_image.py "a warrior standing in a dark forest" \
  --aspect-ratio 16:9 --output warrior.png

# Step 2: Animate it (video-generation skill)
python video-generation/scripts/generate_video.py "slow camera pan across the warrior" \
  --image ./warrior.png --model seedance-2-0 --duration 10
```

**Note:** `--first-frame`, `--last-frame`, and `--reference-image` only accept URLs. For those modes, upload the image to a publicly accessible URL first.

For full parameter details, resolution mappings, and advanced usage, see [`references/seedance-2-0.md`](references/seedance-2-0.md).
