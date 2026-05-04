import subprocess
from pathlib import Path


def validate_media_file(path, min_duration_seconds: float = 1.0) -> tuple[bool, float, str]:
    """Validate that ffprobe can read a media file and that it has real duration."""
    media_path = Path(path)
    if not media_path.exists():
        return False, 0.0, "file does not exist"
    if media_path.stat().st_size <= 0:
        return False, 0.0, "file is empty"
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode != 0:
            return False, 0.0, (out.stderr or "ffprobe failed")[-300:]
        duration = float((out.stdout or "0").strip() or 0)
        if duration < min_duration_seconds:
            return False, duration, f"duration {duration:.2f}s below minimum"
        return True, duration, ""
    except Exception as exc:
        return False, 0.0, str(exc)[:300]


def pick_valid_final_video(
    video_dir,
    prefer_subtitles: bool = True,
    min_duration_seconds: float = 30.0,
) -> tuple[Path | None, bool, list[dict]]:
    """Pick the newest playable FINAL_*.mp4, preferring subtitled versions."""
    folder = Path(video_dir)
    if not folder.is_dir():
        return None, False, [{"error": f"folder {folder} not found"}]

    subtitled = sorted(folder.glob("FINAL_SUB_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    regular = sorted(
        [p for p in folder.glob("FINAL_*.mp4") if "FINAL_SUB_" not in p.name],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    candidates = (subtitled + regular) if prefer_subtitles else (regular + subtitled)

    invalid = []
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        ok, duration, err = validate_media_file(
            candidate,
            min_duration_seconds=min_duration_seconds,
        )
        if ok:
            return candidate, "FINAL_SUB_" in candidate.name, invalid
        invalid.append({
            "name": candidate.name,
            "size_mb": round(candidate.stat().st_size / (1024 * 1024), 1) if candidate.exists() else 0,
            "duration": round(duration, 3),
            "error": err,
        })

    return None, False, invalid
