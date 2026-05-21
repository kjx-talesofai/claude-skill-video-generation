# Seedance 2.0 Reference

## Table of Contents

- [Models](#models)
- [Parameters](#parameters)
  - [Core](#core-new-api-openai-compatible-format)
  - [Passthrough via `metadata`](#passthrough-via-metadata-recommended)
  - [Content Array Roles](#content-array-roles)
  - [Convenience Flags](#convenience-flags-script-only)
  - [Parameter Passthrough](#parameter-passthrough)
- [Sequential Video Generation](#sequential-video-generation-return_last_frame)
- [API Endpoints](#api-endpoints)
  - [Create Task](#create-task)
  - [Get Task Status](#get-task-status)
  - [Async Workflow](#async-workflow)
- [Limits](#limits)
- [Important Notes](#important-notes)
- [Prompt Tips](#prompt-tips)

## Models

| Model | Description |
|---|---|
| `seedance-2-0-fast` | Faster generation, slightly lower quality. Good for drafts and rapid iteration. |
| `seedance-2-0` | Higher quality generation. Use for final production output. |

## Parameters

### Core (new-api OpenAI-compatible format)

| Parameter | Type | Required | Description |
|---|---|---|---|
| `model` | string | Yes | Model ID: `seedance-2-0-fast` or `seedance-2-0` |
| `prompt` | string | Yes | Text description of the desired video. |
| `image` | string | No | URL or base64 of a reference image for image-to-video. |
| `width` | integer | No | Video width in pixels. |
| `height` | integer | No | Video height in pixels. |
| `seed` | integer | No | Random seed for reproducibility. |
| `n` | integer | No | Number of videos to generate. Default: 1 |
| `user` | string | No | User identifier for tracking. |
| `metadata` | object | No | Extended parameters — **this is how we passthrough BytePlus native features**. |

### Passthrough via `metadata` (Recommended)

The new-api router forwards the entire `metadata` object to BytePlus ModelArk. This enables all native features:

| Parameter | Values | Description |
|---|---|---|
| `metadata.duration` | integer | Video length in seconds. Seedance 2.0 series: [4, 15]. Default: 5 |
| `metadata.fps` | integer | Frames per second. Default: 30 |
| `metadata.content` | array | Full `content` array with text, images, videos, audio |
| `metadata.resolution` | `480p`, `720p`, `1080p`, `2K` | Output resolution |
| `metadata.ratio` | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, `adaptive` | Aspect ratio |
| `metadata.generate_audio` | `true` (default) or `false` | Include synchronized audio |
| `metadata.watermark` | `true` or `false` (default) | Add `AI Generated` watermark |
| `metadata.camera_fixed` | `true` or `false` (default) | Fix camera position |
| `metadata.return_last_frame` | `true` or `false` (default) | Return last frame PNG for sequential generation |

### Content Array Roles

```json
[
  {"type": "text", "text": "prompt here"},
  {"type": "image_url", "image_url": {"url": "..."}, "role": "first_frame"},
  {"type": "image_url", "image_url": {"url": "..."}, "role": "last_frame"},
  {"type": "image_url", "image_url": {"url": "..."}, "role": "reference_image"},
  {"type": "video_url", "video_url": {"url": "..."}, "role": "reference_video"},
  {"type": "audio_url", "audio_url": {"url": "..."}, "role": "reference_audio"}
]
```

**Important:** The three image modes are mutually exclusive — cannot mix `first_frame`/`last_frame` with `reference_image`.

### Convenience Flags (Script Only)

The Python script maps these convenience flags to `width`/`height`:

| Resolution | Pixels (16:9) | Pixels (9:16) | Pixels (1:1) |
|---|---|---|---|
| 480p | 854x480 | 480x854 | 480x480 |
| 720p | 1280x720 | 720x1280 | 720x720 |
| 1080p | 1920x1080 | 1080x1920 | 1080x1080 |
| 2K | 2560x1440 | 1440x2560 | 1440x1440 |

Supported aspect ratios: `16:9`, `9:16`, `1:1`, `4:3`, `3:2`, `2:3`, `adaptive`.

`adaptive` lets the model automatically select the most appropriate aspect ratio based on the input prompt or reference images. When using `adaptive`, the script does not send computed `width`/`height` — the native API handles sizing internally.

### Parameter Passthrough

The new-api router supports two ways to pass images:

1. **Native `image` param** — simple single-image first-frame mode. Used when `--image` is provided.
2. **`metadata.content` passthrough** — full BytePlus native `content` array. Used when `--first-frame`, `--last-frame`, or `--reference-image` are provided. This enables first+last frame and multimodal reference modes.

**Do not mix modes.** The BytePlus API rejects requests that mix `first_frame`/`last_frame` with `reference_image` roles.

## Sequential Video Generation (`return_last_frame`)

Set `return_last_frame: true` to get the last frame of the generated video as a PNG. Use this frame as the `first_frame` of the next video to create seamless continuous sequences.

**Example workflow:**
```bash
# Generate first segment
python scripts/generate_video.py "a warrior walking through a forest" \
  --reference-image char1.jpg --return-last-frame --duration 5
# -> Gets video_xxx.mp4 + video_xxx_last_frame.png

# Generate second segment using the last frame
python scripts/generate_video.py "the warrior continues into a clearing" \
  --first-frame video_xxx_last_frame.png --duration 5
```

## API Endpoints

### Create Task

```
POST https://new-api.talesofai.com/v1/video/generations
```

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request body:**
```json
{
  "model": "seedance-2-0-fast",
  "prompt": "a cat playing piano in a cozy jazz club",
  "width": 1280,
  "height": 720,
  "metadata": {
    "duration": 5,
    "fps": 30
  }
}
```

**Response (flat):**
```json
{
  "id": "task_xxx",
  "task_id": "task_xxx",
  "object": "video",
  "model": "seedance-2-0-fast",
  "status": "queued",
  "progress": 0,
  "created_at": 1779207614
}
```

### Get Task Status

```
GET https://new-api.talesofai.com/v1/video/generations/{task_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Response (wrapped — actual format from router):**
```json
{
  "code": "success",
  "message": "",
  "data": {
    "id": 63,
    "task_id": "task_xxx",
    "status": "SUCCESS",
    "result_url": "https://...",
    "progress": "100%",
    "data": {
      "status": "succeeded",
      "content": {
        "video_url": "https://...",
        "last_frame_url": "https://..."
      },
      "resolution": "720p",
      "ratio": "16:9",
      "duration": 5,
      "framespersecond": 24,
      "seed": 19566,
      "generate_audio": true,
      "model": "doubao-seedance-2-0-fast-260128",
      "usage": {
        "completion_tokens": 109431,
        "total_tokens": 109431
      }
    }
  }
}
```

**Status values (from native BytePlus API, found at `data.data.status`):**
- `queued` — waiting to start
- `running` — generating (may also see `not_start` briefly)
- `succeeded` — done, video URL available
- `failed` — error occurred
- `expired` — task timed out
- `cancelled` — task was cancelled

### Async Workflow

1. Script POSTs the request and receives a `task_id` immediately.
2. Script polls the GET endpoint every `--poll-interval` seconds (default 5s).
3. When `status` becomes `"succeeded"`, the script downloads the video from `url`.
4. If `status` becomes `"failed"`, the script exits with the error message.
5. Use `--submit-only` to skip polling and return immediately.

## Limits

| Limit | Value |
|---|---|
| Max duration | 15 seconds (Seedance 2.0 series) |
| Max resolution | 2K (2560x1440) |
| Reference images | Up to 9 |
| Reference videos | Up to 3 (Seedance 2.0 only) |
| Reference audio | Up to 3 (Seedance 2.0 only, cannot input audio alone) |
| Max concurrent tasks | 3 per account |
| Rate limit | 2 QPS per account |
| Video URL lifetime | 24 hours (save promptly) |
| Task data retention | 7 days |

## Important Notes

- **Resolution behavior:** The native BytePlus API uses preset `resolution` + `ratio` values. Passing arbitrary `width`/`height` through the router may be mapped to the nearest supported preset.
- **FPS:** The native API returns `framespersecond` (commonly 24), which may differ from the `fps` value passed in the request.
- **Generate audio:** Seedance 2.0 defaults to generating synchronized audio. Set `generate_audio: false` for silent videos.
- **Face policy:** Seedance 2.0 does not support direct upload of reference images/videos containing real human faces. Use trusted outputs, preset digital characters, or authorized assets.
- **Sequential generation:** Use `return_last_frame: true` to chain multiple video segments together.
- **Async by design:** Video generation takes time. The script blocks and polls by default. Use `--submit-only` to just get the `task_id` and query later with `check_tasks.py`.
- **Output naming:** Downloaded files are named `video_{task_id}.mp4`. Last frames (when `--return-last-frame`) are named `video_{task_id}_last_frame.png`.
- **No build/test/lint tooling** exists — changes are verified by running the scripts directly.
- **Max wait:** Default 600 seconds (10 minutes). Increase with `--max-wait` if needed.

## Prompt Tips

- Be specific about camera movement: "slow pan right", "tracking shot", "static camera"
- Describe lighting and atmosphere: "golden hour", "neon lighting", "soft ambient light"
- Include motion details: "walking slowly", "water rippling gently"
- For dialogue/audio generation, put spoken text in double quotes
- For image-to-video, describe the desired motion relative to the still image
- Recommended prompt length: under 1000 words
