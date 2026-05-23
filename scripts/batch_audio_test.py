#!/usr/bin/env python3
"""Batch test: audio on/off x with/without reference images."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from generate_video import create_task, get_task_status, download_file

API_KEY = os.environ.get("GPT_IMAGE_API_KEY")
PROMPT = "两个角色在阳光明媚的森林里漫步，树叶在风中轻轻摇曳"
REF_IMAGES = [
    "https://oss.talesofai.cn/picture/262d416d-e55e-43b8-8738-02eecf48ebca.jpeg",
    "https://oss.talesofai.cn/picture_s/4f24925e-6ff2-40e2-a2b6-a0e881ed2634_0.jpeg",
]
OUTPUT_DIR = "/tmp/audio_test"

configs = [
    {"name": "01_text_audio", "generate_audio": True, "reference_images": None},
    {"name": "02_text_no_audio", "generate_audio": False, "reference_images": None},
    {"name": "03_ref_audio", "generate_audio": True, "reference_images": REF_IMAGES},
    {"name": "04_ref_no_audio", "generate_audio": False, "reference_images": REF_IMAGES},
]

def submit(cfg):
    task = create_task(
        prompt=PROMPT,
        api_key=API_KEY,
        model="seedance-2-0-fast",
        duration=5,
        resolution="720p",
        aspect_ratio="16:9",
        generate_audio=cfg["generate_audio"],
        reference_images=cfg.get("reference_images"),
    )
    return task.get("task_id")

# 1. Submit all
print("Submitting 4 tasks...")
tasks = {}
for cfg in configs:
    tid = submit(cfg)
    tasks[tid] = cfg
    print(f"  {cfg['name']}: {tid}")

# 2. Poll
print("\nPolling...")
pending = set(tasks.keys())
elapsed = 0
results = {}

while pending:
    for tid in list(pending):
        try:
            status, video_url, last_frame_url, metadata = get_task_status(tid, API_KEY)
            progress = metadata.get("progress", "")
            progress_str = f" ({progress})" if progress else ""

            if status in ("succeeded", "failed", "expired", "cancelled"):
                pending.discard(tid)
                results[tid] = {
                    "status": status,
                    "url": video_url,
                    "metadata": metadata,
                }
                print(f"  {tasks[tid]['name']}: {status}{progress_str}")

                if status == "succeeded" and video_url:
                    ext = ".mp4"
                    path = os.path.join(OUTPUT_DIR, f"{tasks[tid]['name']}{ext}")
                    download_file(video_url, path)
                    results[tid]["file_path"] = path
                    print(f"    -> saved: {path}")
        except Exception as e:
            print(f"  {tasks[tid]['name']}: error - {e}")
            pending.discard(tid)

    if pending:
        time.sleep(5)
        elapsed += 5
        if elapsed % 30 == 0:
            print(f"  ... {elapsed}s elapsed, {len(pending)} pending")

# 3. Summary
print("\n=== Summary ===")
for tid, cfg in tasks.items():
    r = results.get(tid, {})
    print(f"{cfg['name']}: {r.get('status')} | audio={cfg['generate_audio']} | ref={'yes' if cfg['reference_images'] else 'no'}")
    if r.get("file_path"):
        print(f"  -> {r['file_path']}")
