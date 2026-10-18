"""Read-only Music diagnostics; public logs contain aggregate operational data only."""

import collections
import json
import re
import subprocess
import time


CONTAINER_SCRIPT = r'''
import collections
import json
import os
from pathlib import Path
import re
import time

now = time.time()
result = {"activeMusicJobs": [], "queuedMusicJobs": 0, "celeryProbe": "ok", "recentRenders": []}
try:
    from worker_app import celery_app
    inspector = celery_app.control.inspect(timeout=3)
    active = inspector.active() or {}
    reserved = inspector.reserved() or {}
    for tasks in active.values():
        for task in tasks:
            if str(task.get("name", "")).endswith(("produce_music_video", "produce_music_shorts")):
                started = task.get("time_start")
                result["activeMusicJobs"].append({
                    "type": "shorts" if task["name"].endswith("produce_music_shorts") else "video",
                    "elapsedSeconds": round(max(0, now - started)) if isinstance(started, (int, float)) else None,
                })
    result["queuedMusicJobs"] = sum(
        1 for tasks in reserved.values() for task in tasks
        if str(task.get("name", "")).endswith(("produce_music_video", "produce_music_shorts"))
    )
except Exception as exc:
    result["celeryProbe"] = type(exc).__name__

base = Path(os.getenv("MUSIC_RENDER_DIR", "/app/output/music_renders"))
for folder in base.glob("*/*/render/*"):
    if not folder.is_dir():
        continue
    row = {}
    latest = 0
    for label, pattern in (
        ("openaiImages", "openai_images/scene_*.jpg"),
        ("imageSignatures", "openai_images/scene_*.json"),
        ("sceneFrames", "assets/beat_*.jpg"),
        ("videoSegments", "segments/segment_*.mp4"),
        ("shortVideos", "shorts/*/*.mp4"),
    ):
        files = [path for path in folder.glob(pattern) if path.is_file()]
        row[label] = len(files)
        latest = max([latest] + [path.stat().st_mtime for path in files])
    for label, name in (
        ("storyboardReady", "storyboard.json"), ("thumbnailReady", "thumbnail.jpg"),
        ("rawThumbnailReady", "thumbnail_raw.jpg"), ("finalVideoReady", "FINAL_MUSIC.mp4"),
        ("metadataReady", "metadata.json"),
    ):
        path = folder / name
        row[label] = path.is_file() and path.stat().st_size > 0
        if row[label]:
            latest = max(latest, path.stat().st_mtime)
    if latest and now - latest < 6 * 3600:
        row["lastFileUpdateAgeSeconds"] = round(max(0, now - latest))
        model_counts = collections.Counter()
        for path in (folder / "openai_images").glob("scene_*.json"):
            try:
                model_counts[json.loads(path.read_text(encoding="utf-8")).get("model", "unknown")] += 1
            except (OSError, ValueError, AttributeError):
                pass  # A sidecar may still be in the middle of being written.
        row["requestedModelsUsed"] = dict(model_counts)
        result["recentRenders"].append(row)
result["recentRenders"].sort(key=lambda row: row["lastFileUpdateAgeSeconds"])
result["recentRenders"] = result["recentRenders"][:4]
print(json.dumps(result, sort_keys=True))
'''


def command(args, *, input_text=None, timeout=25):
    return subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=timeout)


def container_names():
    result = command(["docker", "ps", "--filter", "name=content", "--format", "{{.Names}}"])
    return [line.strip() for line in result.stdout.splitlines()
            if line.strip() in {"content-factory", "content-redis"}
            or re.fullmatch(r"content-factory[-_]content-worker[-_]\d+", line.strip())]


def error_summary(containers):
    counts = collections.Counter()
    markers = {
        "quota_or_billing": ("insufficient_quota", "billing_hard_limit", "billing_not_active", "exceeded your current quota"),
        "rate_limit": ("rate_limit_exceeded", "too many requests", "429 too many"),
        "model_unavailable": ("model_not_found", "model does not exist", "do not have access to model", "do not have access to the model"),
        "timeout": ("timed out", "timeouterror", "request timeout", "apitimeouterror"),
        "worker_lost_or_limit": ("workerlosterror", "softtimelimitexceeded", "hard time limit"),
        "invalid_image_parameters": ("unknown parameter", "unsupported parameter", "invalid size", "invalid quality"),
        "image_generation_error": ("[music-openai-images]",),
        "thumbnail_error": ("[music-thumbnail]",),
    }
    for container in containers:
        logs = command(["docker", "logs", "--since", "90m", "--tail", "2000", container])
        for line in (logs.stdout + logs.stderr).splitlines():
            lower = line.lower()
            for category, patterns in markers.items():
                if any(pattern in lower for pattern in patterns):
                    counts[category] += 1
    return dict(counts)


def snapshot(index):
    names = container_names()
    probe = command(["docker", "exec", "-i", "content-factory", "python", "-"], input_text=CONTAINER_SCRIPT, timeout=35)
    try:
        music = json.loads(probe.stdout.splitlines()[-1])
    except (ValueError, IndexError):
        music = {"probe": "failed", "returnCode": probe.returncode}
    states = []
    for container in names:
        state = command(["docker", "inspect", "--format", "{{.State.Status}} {{.State.OOMKilled}} {{.RestartCount}}", container])
        states.append({"service": "worker" if "worker" in container else "api" if container == "content-factory" else "redis", "state": state.stdout.strip()})
    print(json.dumps({"snapshot": index, "containers": states, "music": music, "recentErrorCounts": error_summary(names)}, sort_keys=True), flush=True)


if __name__ == "__main__":
    snapshot(1)
    time.sleep(25)
    snapshot(2)
