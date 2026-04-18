# Architecture Reference

## Services

| Service | Role |
|---------|------|
| `services/tts-server` | Minimal stateless TTS synthesis (GPU pod) |
| `services/creepy-brain` | Story generation, TTS orchestration, workflow engine |

## Project Structure

```
├── services/
│   ├── tts-server/
│   │   ├── minimal_server.py    # FastAPI: /synthesize, /health, /ready
│   │   └── Dockerfile
│   └── creepy-brain/
│       ├── app/
│       │   ├── text/            # Chunking, normalization (Claude API)
│       │   ├── audio/           # Validation
│       │   ├── workflows/       # Hatchet workflow steps
│       │   ├── gpu/             # RunPod GPU provider
│       │   └── services/        # Business logic
│       ├── alembic/
│       └── pyproject.toml
├── AGENTS.md / CLAUDE.md
└── docs/
```

## TTS Server API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/ready` | Model loaded? |
| POST | `/synthesize` | `{text, voice, seed}` → WAV bytes |

TTS server is stateless. All orchestration (chunking, normalization, validation, retry) lives in creepy-brain.

## creepy-brain Responsibility Map

| Task | Location |
|------|----------|
| Text normalization | `app/text/normalization.py` |
| Text chunking | `app/text/chunking.py` |
| Audio validation | `app/audio/validation.py` |
| Retry with seed increment | `app/workflows/steps/tts.py` |
| GPU pod lifecycle | `app/gpu/runpod.py` |

## GPU Rules

- **Always use CUDA directly** — never `device_map="auto"` or `accelerate`. Use `.to("cuda")`.
- Models cannot coexist in VRAM — unload one before loading another.

## Deploy

**Never build Docker images locally.** Push to GitHub — CI builds and pushes automatically.

| Image | Registry |
|-------|----------|
| tts-server | `ghcr.io/sgoel1220/tts-server:main` |
| image-server | `ghcr.io/sgoel1220/image-server:main` |
| creepy-brain | `ghcr.io/sgoel1220/creepy-brain:main` |

RunPod settings: community cloud, spot instances, no volume, 20-25 GB disk, ports 8005 (TTS) / 8006 (image-server).

## Dev Commands

```bash
cd services/tts-server && python3 minimal_server.py        # run TTS server
cd services/tts-server && python3 -m py_compile minimal_server.py && echo OK
cd services/creepy-brain && pip install -e .
```
