<p align="center">
  <img src="https://assets.hypersampling.com/hyper-sampling-2.jpg" alt="hyper-sampling" height="50"/>
  &nbsp;&nbsp;&nbsp;
  <img src="https://raw.githubusercontent.com/kjx-talesofai/claude-skill-hypersampling/master/neta_logo.png" alt="neta.art" height="50"/>
</p>

<p align="center">
  <strong><a href="https://hypersampling.com">Jiaxin Kou 寇佳新</a></strong>
  &nbsp;·&nbsp;
  <strong><a href="https://www.neta.art">Neta Art 捏Ta</a></strong>
  &nbsp;·&nbsp;
  <a href="https://github.com/kjx-talesofai">GitHub @kjx-talesofai</a>
</p>

# Video Generation Skill

Generate videos using Seedance 2.0 via proxy API endpoints.

## Setup

```bash
export GPT_IMAGE_API_KEY="your-key-here"
```

## Usage

```bash
# Text-to-video
python scripts/generate_video.py \
  "a cat playing piano in a cozy jazz club"

# Image-to-video
python scripts/generate_video.py \
  "slow zoom out, cinematic" \
  --image https://example.com/photo.jpg

# High quality, longer duration
python scripts/generate_video.py \
  "a serene mountain lake at dawn" \
  --model seedance-2-0 \
  --duration 10 \
  --resolution 1080p \
  --aspect-ratio 16:9

# Just get the URL without downloading
python scripts/generate_video.py \
  "a cyberpunk city" \
  --no-download
```

## Files

- `scripts/generate_video.py` — Main video generation script
- `scripts/check_tasks.py` — Batch task query
- `SKILL.md` — Skill entrypoint for Claude Code
- `references/seedance-2-0.md` — Full API reference
