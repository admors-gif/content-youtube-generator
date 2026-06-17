import json
import math
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


VIDEO_SIZE = (1920, 1080)
THUMB_SIZE = (1280, 720)
COVER_SIZE = (1080, 1080)
FPS = 30


def compact_text(value, limit=240):
    text = " ".join(str(value or "").replace("\x00", " ").split()).strip()
    return text[:limit]


def safe_slug(value, fallback="music"):
    text = compact_text(value, 90).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text, flags=re.I).strip("_")
    return text or fallback


def _font_candidates():
    return [
        "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]


def load_font(size, bold=True):
    candidates = _font_candidates()
    if not bold:
        candidates = candidates[1:] + candidates[:1]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(value, fallback):
    text = str(value or "").strip()
    match = re.search(r"#?([0-9a-fA-F]{6})", text)
    if not match:
        return fallback
    raw = match.group(1)
    return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))


def _palette(package):
    video = _video_concept(package)
    raw = video.get("palette") if isinstance(video.get("palette"), list) else []
    colors = [
        _hex_to_rgb(raw[0] if len(raw) > 0 else "", (6, 11, 22)),
        _hex_to_rgb(raw[1] if len(raw) > 1 else "", (212, 162, 76)),
        _hex_to_rgb(raw[2] if len(raw) > 2 else "", (224, 83, 61)),
    ]
    if colors[0] == colors[1]:
        colors[1] = (212, 162, 76)
    if colors[1] == colors[2]:
        colors[2] = (224, 83, 61)
    return colors


def _blend(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _background(size, palette, seed=0):
    random.seed(seed)
    w, h = size
    base, gold, ember = palette
    img = Image.new("RGB", size, base)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        row = _blend(base, tuple(max(0, c - 6) for c in base), t)
        for x in range(w):
            radial = math.sqrt(((x - w * 0.72) / w) ** 2 + ((y - h * 0.3) / h) ** 2)
            glow = max(0, 1 - radial * 2.9)
            color = _blend(row, gold, glow * 0.28)
            px[x, y] = color

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(90):
        x = random.randint(-w // 6, w)
        y = random.randint(-h // 6, h)
        r = random.randint(1, 5)
        color = gold if random.random() > 0.35 else ember
        alpha = random.randint(18, 72)
        draw.ellipse((x, y, x + r, y + r), fill=(*color, alpha))
    for _ in range(7):
        x1 = random.randint(-w // 4, w)
        y1 = random.randint(0, h)
        x2 = x1 + random.randint(w // 3, w)
        y2 = y1 + random.randint(-90, 90)
        draw.line((x1, y1, x2, y2), fill=(*ember, random.randint(28, 58)), width=random.randint(2, 5))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    return img.filter(ImageFilter.GaussianBlur(0.25))


def _wrap_text(draw, text, font, max_width):
    words = compact_text(text, 500).split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_centered_text(draw, text, box, font, fill, spacing=12, stroke=0):
    x1, y1, x2, y2 = box
    lines = _wrap_text(draw, text, font, max(10, x2 - x1))
    line_h = font.size + spacing
    total_h = line_h * len(lines)
    y = y1 + max(0, ((y2 - y1) - total_h) / 2)
    for line in lines:
        width = draw.textlength(line, font=font)
        x = x1 + ((x2 - x1) - width) / 2
        draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        y += line_h


def _draw_frame(size, palette, title, subtitle, overlay, prompt, seed, square=False):
    img = _background(size, palette, seed=seed)
    w, h = size
    draw = ImageDraw.Draw(img)
    gold = (*palette[1], 255)
    ember = (*palette[2], 255)
    paper = (246, 242, 232, 255)
    dim = (190, 184, 172, 255)

    title_font = load_font(92 if not square else 82)
    subtitle_font = load_font(38 if not square else 34, bold=False)
    overlay_font = load_font(62 if not square else 52)
    small_font = load_font(28 if not square else 24, bold=False)

    margin = int(w * 0.07)
    draw.rounded_rectangle((margin, margin, w - margin, h - margin), radius=28, outline=(*palette[2], 180), width=3)
    draw.text((margin + 44, margin + 34), "POWER MUSIC", font=small_font, fill=ember)

    _draw_centered_text(
        draw,
        overlay or title,
        (margin + 70, int(h * 0.28), w - margin - 70, int(h * 0.59)),
        overlay_font,
        paper,
        spacing=14,
        stroke=2,
    )
    _draw_centered_text(
        draw,
        title,
        (margin + 80, int(h * 0.62), w - margin - 80, int(h * 0.75)),
        title_font if square else load_font(70),
        paper,
        spacing=10,
        stroke=1,
    )
    if subtitle:
        _draw_centered_text(draw, subtitle, (margin + 90, int(h * 0.76), w - margin - 90, int(h * 0.84)), subtitle_font, dim, spacing=8)

    if prompt and not square:
        caption = compact_text(prompt, 110)
        _draw_centered_text(draw, caption, (margin + 120, int(h * 0.86), w - margin - 120, int(h * 0.93)), small_font, dim, spacing=6)

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for i in range(12):
        alpha = max(0, 62 - i * 5)
        gdraw.ellipse((w * 0.5 - 80 - i * 20, h * 0.5 - 80 - i * 20, w * 0.5 + 80 + i * 20, h * 0.5 + 80 + i * 20), outline=(*palette[1], alpha), width=3)
    img = Image.alpha_composite(img, glow)
    return img.convert("RGB")


def _run(cmd, timeout=900):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg failed")[-1200:])
    return result


def probe_audio_duration(audio_path):
    try:
        result = _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            timeout=60,
        )
        return max(1.0, float(str(result.stdout).strip()))
    except Exception:
        return 180.0


def _video_concept(package):
    if isinstance(package.get("videoConcept"), dict):
        return package.get("videoConcept") or {}
    if isinstance(package.get("visualDirection"), dict):
        return package.get("visualDirection") or {}
    return {}


def _scene_list(package):
    video = _video_concept(package)
    scenes = video.get("scenes") if isinstance(video.get("scenes"), list) else []
    clean = []
    for scene in scenes[:8]:
        if not isinstance(scene, dict):
            continue
        clean.append(
            {
                "section": compact_text(scene.get("section"), 60) or "Scene",
                "visualPrompt": compact_text(scene.get("visualPrompt"), 360),
                "textOverlay": compact_text(scene.get("textOverlay"), 64),
            }
        )
    if not clean:
        clean = [
            {"section": "Intro", "visualPrompt": "premium dark cinematic motivational opening", "textOverlay": "HOY EMPIEZA"},
            {"section": "Hook", "visualPrompt": "gold energy waveform and disciplined silhouette", "textOverlay": compact_text(package.get("mainHook"), 42) or "NO NEGOCIO"},
            {"section": "Final", "visualPrompt": "sunrise victory road, cinematic triumph", "textOverlay": compact_text(package.get("mantra"), 42) or "CUMPLO"},
        ]
    return clean


def render_power_music_video(track_id, package, audio_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    segments_dir = output_dir / "segments"
    assets_dir.mkdir(exist_ok=True)
    segments_dir.mkdir(exist_ok=True)

    package = package if isinstance(package, dict) else {}
    title = compact_text(package.get("title"), 100) or "Power Music"
    subtitle = compact_text(package.get("subtitle") or package.get("mainHook"), 160)
    palette = _palette(package)
    scenes = _scene_list(package)
    duration = probe_audio_duration(audio_path)

    cover_path = output_dir / "cover.jpg"
    thumbnail_path = output_dir / "thumbnail.jpg"
    metadata_path = output_dir / "metadata.json"
    lyrics_path = output_dir / "lyrics.txt"
    suno_path = output_dir / "suno_prompt.txt"
    final_path = output_dir / "FINAL_MUSIC.mp4"

    cover = _draw_frame(COVER_SIZE, palette, title, subtitle, package.get("mainHook") or title, package.get("coverPrompt"), 11, square=True)
    cover.save(cover_path, quality=94)
    thumb_text = ((package.get("youtube") or {}).get("thumbnailText") if isinstance(package.get("youtube"), dict) else "") or package.get("mainHook") or title
    thumb = _draw_frame(THUMB_SIZE, palette, title, subtitle, thumb_text, package.get("coverPrompt"), 17)
    thumb.save(thumbnail_path, quality=94)

    scene_duration = max(5.0, duration / max(1, len(scenes)))
    segment_paths = []
    for index, scene in enumerate(scenes, start=1):
        image_path = assets_dir / f"scene_{index:02d}.jpg"
        segment_path = segments_dir / f"segment_{index:02d}.mp4"
        frame = _draw_frame(
            VIDEO_SIZE,
            palette,
            title,
            scene["section"],
            scene["textOverlay"] or package.get("mainHook") or title,
            scene["visualPrompt"],
            100 + index,
        )
        frame.save(image_path, quality=92)
        frames = max(1, int(math.ceil(scene_duration * FPS)))
        zoom = "zoompan=z='min(zoom+0.00085,1.09)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        vf = f"scale={VIDEO_SIZE[0]}:{VIDEO_SIZE[1]},{zoom}:d={frames}:s={VIDEO_SIZE[0]}x{VIDEO_SIZE[1]}:fps={FPS},format=yuv420p"
        _run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_path),
                "-vf",
                vf,
                "-t",
                f"{scene_duration:.3f}",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(segment_path),
            ],
            timeout=max(120, int(scene_duration * 20)),
        )
        segment_paths.append(segment_path)

    concat_path = output_dir / "concat.txt"
    concat_path.write_text("".join(f"file '{path.resolve().as_posix()}'\n" for path in segment_paths), encoding="utf-8")
    silent_video = output_dir / "visual_track.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(silent_video)], timeout=600)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(final_path),
        ],
        timeout=max(600, int(duration * 12)),
    )

    lyrics_path.write_text(str(package.get("lyrics") or ""), encoding="utf-8")
    suno_path.write_text(str(package.get("sunoPrompt") or ""), encoding="utf-8")
    metadata = {
        "trackId": track_id,
        "title": title,
        "durationSeconds": duration,
        "sceneCount": len(scenes),
        "renderer": "power_music_video_v1",
        "files": {
            "video": final_path.name,
            "thumbnail": thumbnail_path.name,
            "cover": cover_path.name,
            "lyrics": lyrics_path.name,
            "sunoPrompt": suno_path.name,
        },
        "youtube": package.get("youtube") or {},
        "safetyNotes": package.get("safetyNotes") or [],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "video": final_path,
        "thumbnail": thumbnail_path,
        "cover": cover_path,
        "metadata": metadata_path,
        "lyrics": lyrics_path,
        "sunoPrompt": suno_path,
        "durationSeconds": duration,
        "sceneCount": len(scenes),
    }
