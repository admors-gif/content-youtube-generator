"""
Create short playback-speed auditions from an existing audio file.

This is intentionally local and cheap: it does not call ElevenLabs, does not
regenerate images and does not touch Firestore. Use it to compare 1.0x, 1.12x
and 1.2x before making a podcast speed the production default.
"""
import argparse
import subprocess
from pathlib import Path


def _atempo_filter(speed: float) -> str:
    parts = []
    remaining = float(speed)
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def render_speed(input_path: Path, output_path: Path, speed: float, seconds: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-t",
        str(seconds),
    ]
    if abs(speed - 1.0) >= 0.01:
        cmd.extend(["-filter:a", _atempo_filter(speed)])
    cmd.extend(["-vn", "-c:a", "libmp3lame", "-b:a", "192k", str(output_path)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size <= 1000:
        raise RuntimeError(result.stderr[-500:])


def main() -> None:
    parser = argparse.ArgumentParser(description="Create podcast audio speed auditions.")
    parser.add_argument("audio", type=Path, help="Input MP3/WAV audio file")
    parser.add_argument("--seconds", type=int, default=90, help="Audition length in seconds")
    parser.add_argument("--out-dir", type=Path, default=Path("output/audio_speed_auditions"))
    parser.add_argument("--speeds", nargs="+", type=float, default=[1.0, 1.12, 1.2])
    args = parser.parse_args()

    if not args.audio.is_file():
        raise SystemExit(f"Audio not found: {args.audio}")

    stem = args.audio.stem
    for speed in args.speeds:
        out = args.out_dir / f"{stem}_{speed:.2f}x.mp3"
        render_speed(args.audio, out, speed, args.seconds)
        print(f"{speed:.2f}x -> {out}")


if __name__ == "__main__":
    main()
