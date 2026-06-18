import json
import math
import os
import random
import re
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


VIDEO_SIZE = (1920, 1080)
THUMB_SIZE = (1280, 720)
COVER_SIZE = (1080, 1080)
FPS = 30
DEFAULT_VISUAL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_VISUAL_BEATS = 120
DEFAULT_MAX_COMFY_IMAGES = 120
_VIGNETTE_CACHE = {}


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _env_float(name, default):
    try:
        return max(1.0, float(os.getenv(name, default)))
    except Exception:
        return default


def _env_int(name, default):
    try:
        return max(1, int(float(os.getenv(name, default))))
    except Exception:
        return default


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

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for i in range(12):
        alpha = max(0, 62 - i * 5)
        gdraw.ellipse((w * 0.5 - 80 - i * 20, h * 0.5 - 80 - i * 20, w * 0.5 + 80 + i * 20, h * 0.5 + 80 + i * 20), outline=(*palette[1], alpha), width=3)
    img = Image.alpha_composite(img, glow)
    return img.convert("RGB")


def _resize_cover(img, size):
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / max(1, src_w), target_h / max(1, src_h))
    new_size = (int(src_w * scale), int(src_h * scale))
    img = img.resize(new_size, Image.LANCZOS)
    left = max(0, (new_size[0] - target_w) // 2)
    top = max(0, (new_size[1] - target_h) // 2)
    return img.crop((left, top, left + target_w, top + target_h))


def _add_vignette(img, palette):
    w, h = img.size
    cache_key = (w, h)
    overlay = _VIGNETTE_CACHE.get(cache_key)
    if overlay is None:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        px = overlay.load()
        for y in range(h):
            for x in range(w):
                dx = abs((x / max(1, w - 1)) - 0.5) * 2
                dy = abs((y / max(1, h - 1)) - 0.5) * 2
                distance = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.05)
                alpha = int(max(0, distance - 0.24) * 118)
                px[x, y] = (0, 0, 0, alpha)
        _VIGNETTE_CACHE[cache_key] = overlay
    accent = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(accent)
    draw.rectangle((0, 0, w, int(h * 0.16)), fill=(0, 0, 0, 70))
    draw.rectangle((0, int(h * 0.78), w, h), fill=(0, 0, 0, 82))
    draw.line((0, h - 3, w, h - 3), fill=(*palette[2], 150), width=4)
    return Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), overlay), accent)


def _compose_generated_frame(source_path, output_path, palette, beat):
    """Post-process a generated image into the final music-video frame.

    Comfy/Flux is asked to generate clean, text-free imagery. This layer adds
    only lightweight branding and the current lyric as a small cinematic cue,
    never the raw prompt.
    """
    try:
        img = Image.open(source_path).convert("RGB")
        img = _resize_cover(img, VIDEO_SIZE).convert("RGBA")
    except Exception:
        return False

    img = _add_vignette(img, palette)
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = VIDEO_SIZE
    paper = (246, 242, 232, 248)
    dim = (215, 208, 194, 218)
    ember = (*palette[2], 245)
    small_font = load_font(28, bold=False)
    lyric_font = load_font(44, bold=True)
    section_font = load_font(24, bold=False)
    margin = 74

    draw.text((margin, 48), "POWER MUSIC", font=small_font, fill=paper)
    section = compact_text(beat.get("section"), 36).upper()
    if section:
        draw.rounded_rectangle((margin, h - 145, margin + 220, h - 104), radius=20, fill=(0, 0, 0, 120), outline=ember, width=1)
        draw.text((margin + 24, h - 136), section, font=section_font, fill=dim)

    lyric = compact_text(beat.get("lyric") or beat.get("overlay"), 96)
    if lyric:
        lines = _wrap_text(draw, lyric, lyric_font, w - margin * 2 - 40)[:2]
        total_h = len(lines) * 52
        y = h - 92 - total_h
        for line in lines:
            draw.text((margin, y), line, font=lyric_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 180))
            y += 52

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=93)
    return output_path.exists() and output_path.stat().st_size > 5000


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


def _srt_timestamp(seconds):
    safe_seconds = max(0.0, float(seconds or 0))
    hours = int(safe_seconds // 3600)
    minutes = int((safe_seconds % 3600) // 60)
    secs = int(safe_seconds % 60)
    millis = int(round((safe_seconds - int(safe_seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _write_subtitle_file(beats, output_path):
    lines = []
    count = 0
    for beat in beats:
        subtitle = compact_text(beat.get("subtitle") or beat.get("lyric") or beat.get("overlay"), 150)
        if not subtitle:
            continue
        start = float(beat.get("start") or 0)
        end = max(start + 0.5, float(beat.get("end") or (start + float(beat.get("duration") or 0.5))))
        count += 1
        lines.extend(
            [
                str(count),
                f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}",
                subtitle,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return count


def _write_subtitle_segments(segments, output_path):
    lines = []
    count = 0
    for segment in segments:
        subtitle = compact_text(segment.get("text") or segment.get("line"), 180)
        if not subtitle:
            continue
        start = float(segment.get("start") or 0)
        end = max(start + 0.45, float(segment.get("end") or (start + 1.2)))
        count += 1
        lines.extend(
            [
                str(count),
                f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}",
                subtitle,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return count


def _music_whisper_enabled():
    default = bool(os.getenv("OPENAI_API_KEY"))
    return _env_bool("CONTENT_FACTORY_MUSIC_WHISPER_SUBTITLES_ENABLED", default=default) and bool(os.getenv("OPENAI_API_KEY"))


def _normalize_token_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9áéíóúñü]+", text, flags=re.I)


def _word_token(value):
    tokens = _normalize_token_text(value)
    return tokens[0] if tokens else ""


def _clean_transcribed_words(words, duration):
    clean = []
    for item in words or []:
        raw = item if isinstance(item, dict) else {}
        token = _word_token(raw.get("word"))
        if not token:
            continue
        try:
            start = max(0.0, float(raw.get("start") or 0))
            end = max(start + 0.05, float(raw.get("end") or (start + 0.3)))
        except Exception:
            continue
        if duration and start > duration + 5:
            continue
        if duration:
            end = min(end, max(start + 0.05, float(duration)))
        clean.append(
            {
                "word": compact_text(raw.get("word"), 40),
                "token": token,
                "start": start,
                "end": max(end, start + 0.05),
            }
        )
    return clean


def _token_overlap_score(window_tokens, target_tokens):
    if not window_tokens or not target_tokens:
        return 0.0
    target_counts = {}
    for token in target_tokens:
        target_counts[token] = target_counts.get(token, 0) + 1
    hits = 0
    for token in window_tokens:
        remaining = target_counts.get(token, 0)
        if remaining > 0:
            hits += 1
            target_counts[token] = remaining - 1
    coverage = hits / max(1, len(target_tokens))
    density = hits / max(1, len(window_tokens))
    return coverage * 0.72 + density * 0.28


def _find_line_window(words, target_tokens, cursor):
    if not words or not target_tokens:
        return None
    target_len = len(target_tokens)
    search_start = max(0, int(cursor) - 6)
    search_end = min(len(words), int(cursor) + max(42, target_len * 9))
    min_size = max(1, int(target_len * 0.6))
    max_size = max(min_size, min(len(words), int(target_len * 1.7) + 3))
    best = None
    best_score = 0.0
    for start in range(search_start, search_end):
        for size in range(min_size, max_size + 1):
            end = start + size
            if end > len(words):
                break
            window_tokens = [word["token"] for word in words[start:end]]
            score = _token_overlap_score(window_tokens, target_tokens)
            distance_penalty = min(0.22, abs(start - cursor) * 0.006)
            adjusted = score - distance_penalty
            if adjusted > best_score:
                best_score = adjusted
                best = (start, end, max(0.0, score))
    if best and best[2] >= 0.56:
        return best
    return None


def _align_lyrics_to_transcribed_words(units, words, duration):
    if not units or not words:
        return []
    tokenized_units = []
    total_tokens = 0
    for index, unit in enumerate(units):
        tokens = _normalize_token_text(unit.get("line"))
        if not tokens:
            continue
        total_tokens += len(tokens)
        tokenized_units.append({**unit, "index": index, "tokens": tokens})
    if not tokenized_units:
        return []

    cursor = 0
    segments = []
    total_tokens = max(1, total_tokens)
    for unit in tokenized_units:
        tokens = unit["tokens"]
        found = _find_line_window(words, tokens, cursor)
        if found:
            start_index, end_index, score = found
            mode = "phrase_match"
        else:
            estimated_size = max(1, round(len(words) * (len(tokens) / total_tokens)))
            start_index = min(cursor, max(0, len(words) - 1))
            end_index = min(len(words), max(start_index + 1, start_index + estimated_size))
            score = 0.0
            mode = "proportional"

        start_word = words[start_index]
        end_word = words[max(start_index, end_index - 1)]
        start = float(start_word.get("start") or 0)
        end = max(start + 0.55, float(end_word.get("end") or (start + 1.2)))
        if duration:
            end = min(end, max(start + 0.55, float(duration)))
        segments.append(
            {
                "index": len(segments),
                "unitIndex": unit.get("index"),
                "section": compact_text(unit.get("section"), 60),
                "line": compact_text(unit.get("line"), 180),
                "text": compact_text(unit.get("line"), 180),
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(max(0.45, end - start), 3),
                "alignmentScore": round(score, 3),
                "alignmentMode": mode,
            }
        )
        cursor = max(cursor + 1, end_index)
        if cursor >= len(words):
            break

    for index, segment in enumerate(segments):
        if index > 0:
            previous = segments[index - 1]
            if segment["start"] < previous["end"]:
                midpoint = (segment["start"] + previous["end"]) / 2
                previous["end"] = round(max(previous["start"] + 0.45, midpoint - 0.02), 3)
                previous["duration"] = round(max(0.45, previous["end"] - previous["start"]), 3)
                segment["start"] = round(min(segment["end"] - 0.45, midpoint + 0.02), 3)
                segment["duration"] = round(max(0.45, segment["end"] - segment["start"]), 3)
    return segments


def _build_whisper_subtitle_segments(package, audio_path, duration):
    diagnostics = {
        "enabled": bool(_music_whisper_enabled()),
        "model": "whisper-1",
        "words": 0,
        "segments": 0,
        "mode": "disabled",
        "error": "",
    }
    if not diagnostics["enabled"]:
        diagnostics["mode"] = "disabled"
        diagnostics["error"] = "OPENAI_API_KEY not configured or CONTENT_FACTORY_MUSIC_WHISPER_SUBTITLES_ENABLED=false"
        return [], diagnostics
    units = _lyric_units(package.get("lyrics"))
    if not units:
        diagnostics["mode"] = "no_lyrics"
        diagnostics["error"] = "lyrics not available"
        return [], diagnostics
    try:
        from scripts.generate_subtitles import transcribe_with_whisper

        transcription = transcribe_with_whisper(Path(audio_path))
    except Exception as exc:
        diagnostics["mode"] = "transcription_failed"
        diagnostics["error"] = str(exc)[:500]
        return [], diagnostics
    if not isinstance(transcription, dict):
        diagnostics["mode"] = "transcription_empty"
        diagnostics["error"] = "OpenAI transcription did not return words"
        return [], diagnostics
    words = _clean_transcribed_words(transcription.get("words") or [], duration)
    diagnostics["words"] = len(words)
    if not words:
        diagnostics["mode"] = "transcription_no_words"
        diagnostics["error"] = "Whisper returned no word timestamps"
        return [], diagnostics
    segments = _align_lyrics_to_transcribed_words(units, words, duration)
    diagnostics["segments"] = len(segments)
    diagnostics["mode"] = "whisper_word_aligned" if segments else "alignment_empty"
    if not segments:
        diagnostics["error"] = "lyrics could not be aligned to transcription"
    return segments, diagnostics


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


def _clean_lyric_line(value):
    text = compact_text(value, 180)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _lyric_units(lyrics):
    """Extract singable lyric lines with their current song section."""
    units = []
    current_section = "Intro"
    for raw_line in str(lyrics or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        section_match = re.fullmatch(r"\[([^\]]{1,80})\]", line)
        if section_match:
            current_section = compact_text(section_match.group(1), 60) or current_section
            continue
        clean = _clean_lyric_line(line)
        if clean:
            units.append({"section": current_section, "line": clean})
    return units


def _match_scene_for_section(scenes, section, index):
    normalized = compact_text(section, 80).lower()
    for scene in scenes:
        scene_section = compact_text(scene.get("section"), 80).lower()
        if scene_section and (scene_section in normalized or normalized in scene_section):
            return scene
    if not scenes:
        return {"section": section or "Scene", "visualPrompt": "", "textOverlay": ""}
    return scenes[index % len(scenes)]


def _visual_mood_from_line(line):
    text = str(line or "").lower()
    signals = []
    if any(word in text for word in ["miedo", "excusa", "duda", "tiembla", "cans", "caer"]):
        signals.append("inner resistance turning into controlled strength")
    if any(word in text for word in ["cumplo", "promesa", "disciplina", "plan", "paso"]):
        signals.append("discipline, commitment, forward motion")
    if any(word in text for word in ["fuego", "hierro", "sudor", "entreno", "levanto"]):
        signals.append("physical power, gym energy, sweat, metal, sunrise")
    if any(word in text for word in ["niño", "futuro", "historia", "version"]):
        signals.append("identity transformation, memory and future self")
    if any(word in text for word in ["respiro", "calma", "silencio", "mente"]):
        signals.append("breath, focus, quiet confidence")
    if any(word in text for word in ["no negocio", "decido", "elijo", "hoy", "nunca mas"]):
        signals.append("decisive boundary, self-command, internal leadership")
    if any(word in text for word in ["cama", "amanece", "despierto", "mañana", "dia"]):
        signals.append("morning transition, leaving comfort, first disciplined action")
    if any(word in text for word in ["corro", "calle", "ruta", "camino", "cima"]):
        signals.append("forward movement, road, sunrise, endurance")
    if any(word in text for word in ["mi palabra", "promesa", "contrato", "firma"]):
        signals.append("oath, signature, contract with the stronger self")
    return ", ".join(signals) or "premium emotional motivation, identity, momentum"


def _build_music_visual_prompt(package, beat, scene, palette):
    video = _video_concept(package)
    title = compact_text(package.get("title"), 120)
    identity = compact_text(video.get("visualIdentity"), 260) or "premium cinematic motivational music-video identity"
    style = compact_text(package.get("style"), 80) or "motivational anthem"
    intention = compact_text(package.get("intention"), 90) or "discipline and identity"
    lyric = compact_text(beat.get("line") or beat.get("lyric"), 180)
    previous_lyric = compact_text(beat.get("previousLine"), 140)
    next_lyric = compact_text(beat.get("nextLine"), 140)
    section = compact_text(beat.get("section"), 60)
    scene_prompt = compact_text(scene.get("visualPrompt"), 520)
    mood = _visual_mood_from_line(lyric)
    colors = ", ".join(str(c) for c in (video.get("palette") or [])[:4]) or f"deep black, gold, ember red, {palette[0]}"

    return compact_text(
        (
            "PROMPT CONTRACT: generate ONE clean, text-free, 16:9 cinematic still for a music video. "
            "Do not draw typography; subtitles will be added later by the renderer. "
            "Interpret the lyric semantically and emotionally, not as random decoration. "
            "Flux Krea photoreal editorial quality, premium composition, clear subject, cinematic lighting, high emotional clarity. "
            f"Song: {title}. Section: {section}. Style: {style}. Intention: {intention}. "
            f"Previous lyric context: {previous_lyric}. Current lyric to visualize: {lyric}. Next lyric context: {next_lyric}. "
            f"Meaning map: {mood}. Visual identity to keep consistent: {identity}. Palette: {colors}. "
            f"Base scene direction: {scene_prompt}. "
            "Choose a concrete, relevant image: a disciplined person in motion, gym iron, sunrise road, mirror transformation, breath in cold air, "
            "a signed oath, focused eyes, shoes leaving the bedroom, city at dawn, or symbolic strength only when the lyric is abstract. "
            "The image must make sense even if the subtitle is hidden. Avoid generic waveform backgrounds, empty graphic templates, random neon circles, stock-photo smiles, "
            "fake text, logos, watermarks, UI, frame borders, captions, readable letters, misspelled typography, extra limbs, distorted hands."
        ),
        1600,
    )


def _timed_segment_for_window(segments, start, end):
    if not segments:
        return 0, {}
    best_index = 0
    best_score = -1.0
    midpoint = (float(start or 0) + float(end or 0)) / 2
    for index, segment in enumerate(segments):
        seg_start = float(segment.get("start") or 0)
        seg_end = float(segment.get("end") or seg_start)
        overlap = max(0.0, min(end, seg_end) - max(start, seg_start))
        distance = abs(((seg_start + seg_end) / 2) - midpoint)
        score = overlap * 10 - distance * 0.04
        if score > best_score:
            best_score = score
            best_index = index
    return best_index, segments[best_index]


def _build_visual_beats(package, duration, interval_seconds, max_beats, timed_segments=None):
    scenes = _scene_list(package)
    units = _lyric_units(package.get("lyrics"))
    if not units:
        units = [
            {"section": "Hook", "line": compact_text(package.get("mainHook") or package.get("mantra") or package.get("title"), 140) or "I choose my strongest self"}
        ]
    timed_segments = [segment for segment in (timed_segments or []) if isinstance(segment, dict)]

    target_count = max(1, int(math.ceil(max(1.0, duration) / max(1.0, interval_seconds))))
    beat_count = min(max_beats, target_count)
    actual_interval = duration / max(1, beat_count)
    palette = _palette(package)
    beats = []
    for index in range(beat_count):
        start = index * actual_interval
        end = duration if index == beat_count - 1 else min(duration, (index + 1) * actual_interval)
        if timed_segments:
            segment_index, segment = _timed_segment_for_window(timed_segments, start, end)
            unit = {"section": segment.get("section"), "line": segment.get("line") or segment.get("text")}
            previous_segment = timed_segments[max(0, segment_index - 1)] if timed_segments else {}
            next_segment = timed_segments[min(len(timed_segments) - 1, segment_index + 1)] if timed_segments else {}
            previous_unit = {"line": previous_segment.get("line") or previous_segment.get("text")}
            next_unit = {"line": next_segment.get("line") or next_segment.get("text")}
            alignment_mode = segment.get("alignmentMode") or "timed"
            alignment_score = segment.get("alignmentScore")
        else:
            unit_index = min(len(units) - 1, int((index / max(1, beat_count)) * len(units)))
            unit = units[unit_index]
            previous_unit = units[max(0, unit_index - 1)] if units else {}
            next_unit = units[min(len(units) - 1, unit_index + 1)] if units else {}
            alignment_mode = "estimated"
            alignment_score = None
        scene = _match_scene_for_section(scenes, unit.get("section"), index)
        text_overlay = compact_text(unit.get("line"), 60) or compact_text(scene.get("textOverlay"), 60)
        prompt_context = {
            **unit,
            "previousLine": previous_unit.get("line") if isinstance(previous_unit, dict) else "",
            "nextLine": next_unit.get("line") if isinstance(next_unit, dict) else "",
        }
        prompt = _build_music_visual_prompt(package, prompt_context, scene, palette)
        beats.append(
            {
                "scene_number": index + 1,
                "section": compact_text(unit.get("section"), 60),
                "lyric": compact_text(unit.get("line"), 180),
                "subtitle": compact_text(unit.get("line"), 150),
                "overlay": text_overlay,
                "prompt": prompt,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": max(0.5, end - start),
                "sourceScene": scene.get("section"),
                "alignmentMode": alignment_mode,
                "alignmentScore": alignment_score,
            }
        )
    return beats, actual_interval


def _comfy_music_enabled():
    default = bool(os.getenv("COMFYUI_API_KEY"))
    return _env_bool("CONTENT_FACTORY_MUSIC_COMFY_ENABLED", default=default) and bool(os.getenv("COMFYUI_API_KEY"))


def _generate_comfy_beat_images(beats, images_dir):
    """Generate beat-aligned images with the existing Comfy/Flux pipeline.

    The function is deliberately optional and fault-tolerant. A failed Comfy
    batch never breaks the final render; local premium fallback frames fill any
    missing beat.
    """
    stats = {
        "enabled": False,
        "requested": 0,
        "generated": 0,
        "skipped": 0,
        "failed": 0,
        "missing": [],
        "invalid": [],
        "error": "",
    }
    if not _comfy_music_enabled():
        stats["error"] = "COMFYUI_API_KEY not configured or CONTENT_FACTORY_MUSIC_COMFY_ENABLED=false"
        return stats

    max_images = _env_int("CONTENT_FACTORY_MUSIC_MAX_COMFY_IMAGES", DEFAULT_MAX_COMFY_IMAGES)
    comfy_scenes = [{"scene_number": beat["scene_number"], "prompt": beat["prompt"]} for beat in beats[:max_images]]
    if not comfy_scenes:
        return stats

    stats["enabled"] = True
    stats["requested"] = len(comfy_scenes)
    try:
        from scripts.factory import generate_comfy_images, _select_image_workflow

        workflow = _select_image_workflow("narrativa")
        workflow["label"] = "FLUX/Krea Power Music"
        result = generate_comfy_images(comfy_scenes, images_dir, workflow, pipeline_format="narrativa")
        stats.update(
            {
                "generated": int(result.get("generated") or 0),
                "skipped": int(result.get("skipped") or 0),
                "failed": int(result.get("failed") or 0),
                "missing": result.get("missing") or [],
                "invalid": result.get("invalid") or [],
            }
        )
    except Exception as exc:
        stats["error"] = str(exc)[:500]
    return stats


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
    duration = probe_audio_duration(audio_path)
    requested_interval = _env_float("CONTENT_FACTORY_MUSIC_VISUAL_INTERVAL_SECONDS", DEFAULT_VISUAL_INTERVAL_SECONDS)
    max_visual_beats = _env_int("CONTENT_FACTORY_MUSIC_MAX_VISUAL_BEATS", DEFAULT_MAX_VISUAL_BEATS)
    subtitle_segments, subtitle_diagnostics = _build_whisper_subtitle_segments(package, audio_path, duration)
    subtitle_mode = "whisper_word_aligned" if subtitle_segments else "lyric_blocks_estimated"
    beats, visual_interval = _build_visual_beats(package, duration, requested_interval, max_visual_beats, timed_segments=subtitle_segments)

    cover_path = output_dir / "cover.jpg"
    thumbnail_path = output_dir / "thumbnail.jpg"
    metadata_path = output_dir / "metadata.json"
    lyrics_path = output_dir / "lyrics.txt"
    suno_path = output_dir / "suno_prompt.txt"
    subtitles_path = output_dir / "subtitles.srt"
    final_path = output_dir / "FINAL_MUSIC.mp4"

    cover = _draw_frame(COVER_SIZE, palette, title, subtitle, package.get("mainHook") or title, package.get("coverPrompt"), 11, square=True)
    cover.save(cover_path, quality=94)
    thumb_text = ((package.get("youtube") or {}).get("thumbnailText") if isinstance(package.get("youtube"), dict) else "") or package.get("mainHook") or title
    thumb = _draw_frame(THUMB_SIZE, palette, title, subtitle, thumb_text, package.get("coverPrompt"), 17)
    thumb.save(thumbnail_path, quality=94)

    comfy_dir = output_dir / "comfy"
    comfy_stats = _generate_comfy_beat_images(beats, comfy_dir)
    segment_paths = []
    generated_frames = 0
    fallback_frames = 0
    for index, beat in enumerate(beats, start=1):
        image_path = assets_dir / f"beat_{index:03d}.jpg"
        segment_path = segments_dir / f"segment_{index:03d}.mp4"
        comfy_path = comfy_dir / f"scene_{index:04d}.png"
        if comfy_path.exists() and comfy_path.stat().st_size > 5000 and _compose_generated_frame(comfy_path, image_path, palette, beat):
            generated_frames += 1
        else:
            frame = _draw_frame(
                VIDEO_SIZE,
                palette,
                title,
                beat.get("section"),
                beat.get("overlay") or package.get("mainHook") or title,
                beat.get("prompt"),
                100 + index,
            )
            frame.save(image_path, quality=92)
            fallback_frames += 1

        segment_duration = max(0.5, float(beat.get("duration") or visual_interval))
        frames = max(1, int(math.ceil(segment_duration * FPS)))
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
                f"{segment_duration:.3f}",
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
            timeout=max(120, int(segment_duration * 20)),
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
    if subtitle_segments:
        subtitle_count = _write_subtitle_segments(subtitle_segments, subtitles_path)
    else:
        subtitle_count = _write_subtitle_file(beats, subtitles_path)
    metadata = {
        "trackId": track_id,
        "title": title,
        "durationSeconds": duration,
        "sceneCount": len(beats),
        "visualBeatCount": len(beats),
        "visualIntervalSeconds": round(visual_interval, 3),
        "requestedVisualIntervalSeconds": round(requested_interval, 3),
        "visualProvider": "comfy_flux" if generated_frames else "local_fallback",
        "comfy": comfy_stats,
        "generatedFrames": generated_frames,
        "fallbackFrames": fallback_frames,
        "renderer": "power_music_video_v2_lyric_beats",
        "subtitleMode": subtitle_mode,
        "subtitleCount": subtitle_count,
        "subtitleDiagnostics": subtitle_diagnostics,
        "visualBeats": [
            {
                "index": beat["scene_number"],
                "section": beat.get("section"),
                "lyric": beat.get("lyric"),
                "subtitle": beat.get("subtitle"),
                "start": beat.get("start"),
                "end": beat.get("end"),
                "duration": round(float(beat.get("duration") or 0), 3),
                "sourceScene": beat.get("sourceScene"),
                "alignmentMode": beat.get("alignmentMode"),
                "alignmentScore": beat.get("alignmentScore"),
                "prompt": beat.get("prompt"),
            }
            for beat in beats
        ],
        "files": {
            "video": final_path.name,
            "thumbnail": thumbnail_path.name,
            "cover": cover_path.name,
            "lyrics": lyrics_path.name,
            "sunoPrompt": suno_path.name,
            "subtitles": subtitles_path.name,
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
        "subtitles": subtitles_path,
        "durationSeconds": duration,
        "sceneCount": len(beats),
        "visualBeatCount": len(beats),
        "visualIntervalSeconds": round(visual_interval, 3),
        "visualProvider": metadata["visualProvider"],
        "generatedFrames": generated_frames,
        "fallbackFrames": fallback_frames,
        "comfy": comfy_stats,
        "renderer": metadata["renderer"],
        "subtitleMode": metadata["subtitleMode"],
        "subtitleCount": metadata["subtitleCount"],
        "subtitleDiagnostics": metadata["subtitleDiagnostics"],
    }
