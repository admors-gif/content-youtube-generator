import json
import subprocess
from pathlib import Path


def _has_audio_stream(path: Path) -> tuple[bool, str]:
    """Return whether ffprobe can see at least one audio stream."""
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if out.returncode != 0:
        return False, (out.stderr or "ffprobe audio stream check failed")[-300:]
    try:
        streams = json.loads(out.stdout or "{}").get("streams") or []
    except json.JSONDecodeError:
        return False, "ffprobe audio stream output was not valid JSON"
    if not streams:
        return False, "missing audio stream"
    return True, ""


def validate_media_file(
    path,
    min_duration_seconds: float = 1.0,
    require_audio: bool = False,
) -> tuple[bool, float, str]:
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
        if require_audio:
            has_audio, audio_error = _has_audio_stream(media_path)
            if not has_audio:
                return False, duration, audio_error
        return True, duration, ""
    except Exception as exc:
        return False, 0.0, str(exc)[:300]


def pick_valid_final_video(
    video_dir,
    prefer_subtitles: bool = True,
    min_duration_seconds: float = 30.0,
    require_audio: bool = True,
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
            require_audio=require_audio,
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
