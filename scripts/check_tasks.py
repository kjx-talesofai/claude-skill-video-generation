#!/usr/bin/env python3
"""Query status of one or more video generation tasks."""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error


BASE_URL = "https://new-api.talesofai.com"


def _api_request(path: str, api_key: str, retries: int = 3) -> dict:
    """Make a GET request and return parsed JSON."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")

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


def get_task_status(task_id: str, api_key: str) -> dict:
    """Get status of a single task."""
    response = _api_request(f"/v1/video/generations/{task_id}", api_key)

    if "code" in response and "data" in response:
        wrapper = response.get("data", {})
        native = wrapper.get("data", {})

        status = native.get("status", wrapper.get("status", "unknown")).lower()
        video_url = wrapper.get("result_url") or ""
        if not video_url and "content" in native:
            video_url = native["content"].get("video_url", "")
        last_frame_url = native.get("content", {}).get("last_frame_url", "") if "content" in native else ""

        return {
            "task_id": task_id,
            "status": status,
            "url": video_url or None,
            "last_frame_url": last_frame_url or None,
            "progress": wrapper.get("progress"),
            "resolution": native.get("resolution"),
            "ratio": native.get("ratio"),
            "duration": native.get("duration"),
            "seed": native.get("seed"),
            "model": native.get("model"),
        }

    return {
        "task_id": task_id,
        "status": response.get("status", "unknown").lower(),
        "url": response.get("url"),
        "raw": response,
    }


def download_file(url: str, output_path: str) -> str:
    """Download a file from URL."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Query video generation task status")
    parser.add_argument("task_ids", nargs="+", help="One or more task IDs to query")
    parser.add_argument("--api-key", help="API key (or set GPT_IMAGE_API_KEY env var)")
    parser.add_argument("--poll", action="store_true", help="Keep polling until all tasks complete or fail")
    parser.add_argument("--poll-interval", type=int, default=5, help="Seconds between polls (default: 5)")
    parser.add_argument("--max-wait", type=int, default=600, help="Max seconds to wait for completion (default: 600)")
    parser.add_argument("--download", action="store_true", help="Download completed videos")
    parser.add_argument("--output-dir", default=".", help="Directory for downloads (default: current dir)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GPT_IMAGE_API_KEY")
    if not api_key:
        print("Error: API key must be provided via --api-key or GPT_IMAGE_API_KEY env var", file=sys.stderr)
        return 1

    pending = set(args.task_ids)
    results = {}
    elapsed = 0

    while pending:
        for task_id in list(pending):
            try:
                info = get_task_status(task_id, api_key)
                results[task_id] = info

                status = info["status"]
                progress = info.get("progress", "")
                progress_str = f" ({progress})" if progress else ""

                if not args.json:
                    print(f"{task_id}: {status}{progress_str}")

                if status in ("succeeded", "failed", "expired", "cancelled"):
                    pending.discard(task_id)

                    if status == "succeeded" and args.download and info.get("url"):
                        os.makedirs(args.output_dir, exist_ok=True)
                        filename = f"video_{task_id}.mp4"
                        output_path = os.path.join(args.output_dir, filename)
                        download_file(info["url"], output_path)
                        info["file_path"] = output_path
                        if not args.json:
                            print(f"  -> Downloaded: {output_path}")

                        if info.get("last_frame_url"):
                            frame_filename = f"video_{task_id}_last_frame.png"
                            frame_path = os.path.join(args.output_dir, frame_filename)
                            download_file(info["last_frame_url"], frame_path)
                            info["last_frame_path"] = frame_path
                            if not args.json:
                                print(f"  -> Last frame: {frame_path}")

            except RuntimeError as e:
                results[task_id] = {"task_id": task_id, "status": "error", "error": str(e)}
                pending.discard(task_id)
                if not args.json:
                    print(f"{task_id}: error - {e}")

        if pending and args.poll:
            if elapsed >= args.max_wait:
                if not args.json:
                    print(f"Timed out after {args.max_wait}s waiting for {len(pending)} task(s)")
                break
            time.sleep(args.poll_interval)
            elapsed += args.poll_interval
        elif pending and not args.poll:
            break

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
