#!/usr/bin/env python3
"""Generate videos using Seedance 2.0 via proxy API endpoint.

Supports:
- Text-to-video
- Image-to-video (first frame)
- First frame + last frame
- Multimodal reference images (1-9 images)
- Return last frame for sequential video generation
- Adaptive aspect ratio
- Watermark
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error


BASE_URL = "https://new-api.talesofai.com"

_RESOLUTION_MAP = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
    "2K": 1440,
}

_ASPECT_RATIOS = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "1:1": (1, 1),
    "4:3": (4, 3),
    "3:2": (3, 2),
    "2:3": (2, 3),
    "adaptive": (0, 0),
}


def _resolve_size(resolution: str, aspect_ratio: str) -> tuple[int, int] | None:
    """Map resolution + aspect ratio to width x height.

    Returns None for adaptive aspect ratio (native API handles sizing).
    """
    if aspect_ratio == "adaptive":
        return None

    short_edge = _RESOLUTION_MAP.get(resolution)
    if short_edge is None:
        raise ValueError(f"Unknown resolution: {resolution}. Choose from {list(_RESOLUTION_MAP)}")

    w_ratio, h_ratio = _ASPECT_RATIOS.get(aspect_ratio, (16, 9))

    if w_ratio >= h_ratio:
        height = short_edge
        width = int(height * w_ratio / h_ratio)
    else:
        width = short_edge
        height = int(width * h_ratio / w_ratio)

    # Make dimensions even (common video encoding requirement)
    width = width if width % 2 == 0 else width + 1
    height = height if height % 2 == 0 else height + 1

    return width, height


def _api_request(method: str, path: str, api_key: str, payload: dict | None = None, retries: int = 3) -> dict:
    """Make an API request and return parsed JSON. Retries on transient SSL/network errors."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            raise RuntimeError(f"HTTP {e.code}: {body}") from e
        except (urllib.error.URLError, ssl.SSLError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1)
            continue

    raise RuntimeError(f"Request failed after {retries} attempts: {last_err}") from last_err


def _extract_task_status(response: dict) -> tuple[str, str | None, str | None, dict]:
    """Extract (status, video_url, last_frame_url, metadata) from a GET task status response.

    The new-api router wraps the native BytePlus response.
    Status values: queued, running, succeeded, failed, expired, cancelled.
    """
    if "code" in response and "data" in response:
        wrapper = response.get("data", {})
        native = wrapper.get("data", {})

        status = native.get("status", wrapper.get("status", "unknown")).lower()

        # Video URL may be in result_url (top-level wrapper) or content.video_url (native)
        video_url = wrapper.get("result_url") or ""
        if not video_url and "content" in native:
            video_url = native["content"].get("video_url", "")

        # Last frame URL (when return_last_frame is set)
        last_frame_url = native.get("content", {}).get("last_frame_url", "") if "content" in native else ""

        metadata = {
            "resolution": native.get("resolution"),
            "ratio": native.get("ratio"),
            "duration": native.get("duration"),
            "framespersecond": native.get("framespersecond"),
            "seed": native.get("seed"),
            "generate_audio": native.get("generate_audio"),
            "model": native.get("model"),
            "usage": native.get("usage"),
            "progress": wrapper.get("progress"),
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return status, video_url or None, last_frame_url or None, metadata

    # Fallback to documented flat format
    status = response.get("status", "unknown").lower()
    video_url = response.get("url")
    last_frame_url = response.get("last_frame_url")
    metadata = response.get("metadata", {})
    return status, video_url, last_frame_url, metadata


def _build_content(
    prompt: str,
    image: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
) -> tuple[list[dict], bool]:
    """Build BytePlus content array. Returns (content, use_metadata).

    If first_frame, last_frame, or reference_images are used, all content goes
    through metadata passthrough. Otherwise, use new-api native image param.
    """
    use_metadata = bool(first_frame or last_frame or reference_images)

    if not use_metadata:
        return [], False

    content: list[dict] = []
    content.append({"type": "text", "text": prompt})

    if first_frame:
        content.append({
            "type": "image_url",
            "image_url": {"url": first_frame},
            "role": "first_frame",
        })

    if last_frame:
        content.append({
            "type": "image_url",
            "image_url": {"url": last_frame},
            "role": "last_frame",
        })

    if reference_images:
        for img_url in reference_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url},
                "role": "reference_image",
            })

    return content, True


def create_task(
    prompt: str,
    api_key: str,
    model: str = "seedance-2-0-fast",
    image: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    duration: int = 5,
    width: int | None = None,
    height: int | None = None,
    fps: int = 30,
    seed: int | None = None,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    generate_audio: bool = True,
    return_last_frame: bool = False,
    camera_fixed: bool = False,
    watermark: bool = False,
) -> dict:
    """Submit a video generation task and return the task info."""
    content, use_metadata = _build_content(prompt, image, first_frame, last_frame, reference_images)

    payload: dict = {
        "model": model,
        "prompt": prompt,
    }

    # Only send width/height for non-adaptive, non-metadata paths.
    # When use_metadata=True, native API uses resolution + ratio instead.
    if width is not None and height is not None:
        payload["width"] = width
        payload["height"] = height

    if use_metadata:
        payload["metadata"] = {
            "content": content,
            "resolution": resolution,
            "ratio": aspect_ratio,
            "generate_audio": generate_audio,
            "duration": duration,
            "fps": fps,
        }
        if seed is not None:
            payload["metadata"]["seed"] = seed
        if return_last_frame:
            payload["metadata"]["return_last_frame"] = True
        if camera_fixed:
            payload["metadata"]["camera_fixed"] = True
        if watermark:
            payload["metadata"]["watermark"] = True
        if "image" in payload:
            del payload["image"]
    else:
        if image:
            payload["image"] = image
        if seed is not None:
            payload["seed"] = seed
        # Pass duration/fps through metadata for all requests
        payload["metadata"] = {
            "duration": duration,
            "fps": fps,
        }
        if not generate_audio:
            payload["metadata"]["generate_audio"] = False
        if return_last_frame:
            payload["metadata"]["return_last_frame"] = True
        if camera_fixed:
            payload["metadata"]["camera_fixed"] = True
        if watermark:
            payload["metadata"]["watermark"] = True

    return _api_request("POST", "/v1/video/generations", api_key, payload)


def get_task_status(task_id: str, api_key: str) -> tuple[str, str | None, str | None, dict]:
    """Poll the status of a video generation task.

    Returns (status, video_url, last_frame_url, metadata).
    """
    response = _api_request("GET", f"/v1/video/generations/{task_id}", api_key)
    return _extract_task_status(response)


def download_file(url: str, output_path: str) -> str:
    """Download a file from URL to a local file."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return output_path


def generate_video(
    prompt: str,
    api_key: str | None = None,
    model: str = "seedance-2-0-fast",
    image: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: list[str] | None = None,
    duration: int = 5,
    resolution: str = "720p",
    aspect_ratio: str = "16:9",
    fps: int = 30,
    seed: int | None = None,
    generate_audio: bool = True,
    return_last_frame: bool = False,
    camera_fixed: bool = False,
    watermark: bool = False,
    output_dir: str = ".",
    download: bool = True,
    poll_interval: int = 5,
    max_wait: int = 600,
    submit_only: bool = False,
) -> dict:
    """Generate a video: submit task, poll for completion, optionally download."""
    if api_key is None:
        api_key = os.environ.get("GPT_IMAGE_API_KEY")
    if not api_key:
        raise ValueError("API key must be provided via --api-key or GPT_IMAGE_API_KEY env var")

    size = _resolve_size(resolution, aspect_ratio)
    width, height = size if size else (None, None)

    task = create_task(
        prompt, api_key, model, image, first_frame, last_frame,
        reference_images, duration, width, height, fps, seed,
        resolution, aspect_ratio, generate_audio, return_last_frame, camera_fixed, watermark,
    )
    task_id = task.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {task}")

    print(f"Task submitted: {task_id}", file=sys.stderr)

    if submit_only:
        return {
            "task_id": task_id,
            "status": "submitted",
            "note": "Use check_tasks.py to query status",
        }

    elapsed = 0
    while elapsed < max_wait:
        status, video_url, last_frame_url, metadata = get_task_status(task_id, api_key)
        progress = metadata.get("progress", "")
        progress_str = f" ({progress})" if progress else ""
        print(f"  [{elapsed}s] status: {status}{progress_str}", file=sys.stderr)

        if status == "succeeded":
            if not video_url:
                raise RuntimeError("Task succeeded but no video URL returned")

            result = {
                "task_id": task_id,
                "status": status,
                "url": video_url,
                "format": "mp4",
                "metadata": metadata,
            }

            if last_frame_url:
                result["last_frame_url"] = last_frame_url

            if download:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"video_{task_id}.mp4"
                output_path = os.path.join(output_dir, filename)
                download_file(video_url, output_path)
                result["file_path"] = output_path
                print(f"Downloaded to: {output_path}", file=sys.stderr)

                if last_frame_url:
                    frame_filename = f"video_{task_id}_last_frame.png"
                    frame_path = os.path.join(output_dir, frame_filename)
                    download_file(last_frame_url, frame_path)
                    result["last_frame_path"] = frame_path
                    print(f"Last frame saved to: {frame_path}", file=sys.stderr)

            return result

        if status in ("failed", "expired", "cancelled"):
            raise RuntimeError(f"Video generation {status}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timed out after {max_wait}s waiting for task {task_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate videos via Seedance 2.0 proxy")
    parser.add_argument("prompt", help="Video generation prompt")
    parser.add_argument("--api-key", help="API key (or set GPT_IMAGE_API_KEY env var)")
    parser.add_argument(
        "--model",
        default="seedance-2-0-fast",
        choices=["seedance-2-0-fast", "seedance-2-0"],
        help="Model to use (default: seedance-2-0-fast)",
    )

    # Image modes
    parser.add_argument("--image", help="Reference image URL for image-to-video (first frame, backward compatible)")
    parser.add_argument("--first-frame", help="First frame image URL")
    parser.add_argument("--last-frame", help="Last frame image URL")
    parser.add_argument("--reference-image", action="append", dest="reference_images", help="Reference image URL for multimodal reference mode (can be used multiple times)")

    # Video params
    parser.add_argument("--duration", type=int, default=5, help="Video duration in seconds (default: 5)")
    parser.add_argument(
        "--resolution",
        default="720p",
        choices=["480p", "720p", "1080p", "2K"],
        help="Output resolution (default: 720p)",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=list(_ASPECT_RATIOS),
        help="Aspect ratio (default: 16:9). Use 'adaptive' to let the model select based on input.",
    )
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    # Advanced params
    parser.add_argument("--generate-audio", action="store_true", default=True, help="Generate synchronized audio (default: true)")
    parser.add_argument("--no-generate-audio", action="store_false", dest="generate_audio", help="Generate silent video")
    parser.add_argument("--return-last-frame", action="store_true", help="Return the last frame image for sequential video generation")
    parser.add_argument("--camera-fixed", action="store_true", help="Fix camera position (not supported by Seedance 2.0)")
    parser.add_argument("--watermark", action="store_true", help="Add AI Generated watermark to the video")

    # Output / workflow
    parser.add_argument("--output-dir", default=".", help="Directory to save downloaded video (default: current dir)")
    parser.add_argument("--no-download", action="store_true", help="Only return URL, do not download the video")
    parser.add_argument("--submit-only", action="store_true", help="Submit task and return immediately without polling")
    parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between status checks (default: 5)")
    parser.add_argument("--max-wait", type=int, default=600, help="Max seconds to wait for completion (default: 600)")
    args = parser.parse_args()

    # Validate: cannot mix image modes
    modes = []
    if args.image:
        modes.append("image")
    if args.first_frame or args.last_frame:
        modes.append("first/last_frame")
    if args.reference_images:
        modes.append("reference_image")
    if len(modes) > 1:
        print(f"Error: Cannot mix image modes: {modes}. Use only one of --image, --first-frame/--last-frame, or --reference-image.", file=sys.stderr)
        return 1

    try:
        result = generate_video(
            prompt=args.prompt,
            api_key=args.api_key,
            model=args.model,
            image=args.image,
            first_frame=args.first_frame,
            last_frame=args.last_frame,
            reference_images=args.reference_images,
            duration=args.duration,
            resolution=args.resolution,
            aspect_ratio=args.aspect_ratio,
            fps=args.fps,
            seed=args.seed,
            generate_audio=args.generate_audio,
            return_last_frame=args.return_last_frame,
            camera_fixed=args.camera_fixed,
            watermark=args.watermark,
            output_dir=args.output_dir,
            download=not args.no_download,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait,
            submit_only=args.submit_only,
        )
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
