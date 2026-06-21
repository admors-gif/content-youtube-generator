import base64
import json
import math
import os
import random
import re
import subprocess
import unicodedata
import urllib.request
import mimetypes
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from scripts.power_music_director import (
        DIRECTOR_VERSION,
        build_beat_shot_recipe,
        enrich_package_with_director_plan,
        lyric_visual_metaphor,
        prompt_gate_for_recipe,
    )
except Exception:  # pragma: no cover - keeps standalone script execution safe
    try:
        from power_music_director import DIRECTOR_VERSION, build_beat_shot_recipe, enrich_package_with_director_plan, lyric_visual_metaphor, prompt_gate_for_recipe
    except Exception:  # pragma: no cover
        DIRECTOR_VERSION = "power_music_director_unavailable"

        def build_beat_shot_recipe(section, line, index, plan):
            return {}

        def enrich_package_with_director_plan(package, payload=None):
            return package

        def lyric_visual_metaphor(section, line, index, plan=None):
            return ""

        def prompt_gate_for_recipe(prompt, shot_recipe=None):
            return {"passed": True, "hits": [], "goodSignals": 0, "physicsSignals": 0, "recipeId": ""}


VIDEO_SIZE = (1920, 1080)
SHORT_SIZE = (1080, 1920)
THUMB_SIZE = (1280, 720)
COVER_SIZE = (1080, 1080)
FPS = 30
DEFAULT_VISUAL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_VISUAL_BEATS = 120
DEFAULT_MAX_COMFY_IMAGES = 120
DEFAULT_SUBTITLE_MIN_ALIGNMENT_SCORE = 0.62
DEFAULT_SUBTITLE_MIN_PHRASE_RATIO = 0.55
DEFAULT_MUSIC_VISION_QA_MAX_FRAMES = 60
DEFAULT_MUSIC_VISION_QA_MIN_SCORE = 82
DEFAULT_MUSIC_VISION_QA_SOFT_MIN_SCORE = 70
DEFAULT_MUSIC_VISION_QA_REGEN_ATTEMPTS = 2
DEFAULT_MUSIC_INSTRUMENTAL_GAP_SECONDS = 2.8
DEFAULT_MUSIC_SHORTS_DURATION_SECONDS = 72.0
DEFAULT_MUSIC_SHORTS_CTA_SECONDS = 5.0
TEXT_FREE_NEGATIVE_PROMPT = (
    "No readable text, no letters, no typography, no captions, no lyrics, "
    "no logo, no watermark, no UI, no signs, no book pages, no posters, "
    "no screens with writing, no gibberish text, no pseudo-words, "
    "no household appliances, no clothes iron, no ironing board, no random domestic objects."
)
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


def _env_ratio(name, default):
    try:
        return min(1.0, max(0.0, float(os.getenv(name, default))))
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


def _music_thumbnail_model():
    return os.getenv("CONTENT_FACTORY_MUSIC_THUMBNAIL_MODEL", "gpt-image-2").strip() or "gpt-image-2"


def _music_thumbnail_model_candidates():
    configured = [
        item.strip()
        for item in os.getenv("CONTENT_FACTORY_MUSIC_THUMBNAIL_MODELS", "").split(",")
        if item.strip()
    ]
    if configured:
        return configured
    primary = _music_thumbnail_model()
    candidates = [primary]
    for fallback in ["gpt-image-1.5", "gpt-image-1"]:
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def _music_thumbnail_quality():
    return os.getenv("CONTENT_FACTORY_MUSIC_THUMBNAIL_QUALITY", "high").strip() or "high"


def _music_thumbnail_size(model):
    configured = os.getenv("CONTENT_FACTORY_MUSIC_THUMBNAIL_SIZE", "").strip()
    if configured:
        return configured
    if str(model).startswith("gpt-image"):
        return "1536x1024"
    return "1792x1024"


def _music_premium_thumbnail_enabled():
    default = bool(os.getenv("OPENAI_API_KEY"))
    return _env_bool("CONTENT_FACTORY_MUSIC_PREMIUM_THUMBNAIL_ENABLED", default=default) and bool(os.getenv("OPENAI_API_KEY"))


def _music_vision_qa_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_ENABLED", default=bool(os.getenv("OPENAI_API_KEY"))) and bool(os.getenv("OPENAI_API_KEY"))


def _music_vision_qa_model():
    return os.getenv("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _music_vision_qa_max_frames():
    return _env_int("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MAX_FRAMES", DEFAULT_MUSIC_VISION_QA_MAX_FRAMES)


def _music_vision_qa_min_score():
    return _env_int("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MIN_SCORE", DEFAULT_MUSIC_VISION_QA_MIN_SCORE)


def _music_vision_qa_soft_min_score():
    return _env_int("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_SOFT_MIN_SCORE", DEFAULT_MUSIC_VISION_QA_SOFT_MIN_SCORE)


def _music_vision_qa_regen_attempts():
    return _env_int("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_REGEN_ATTEMPTS", DEFAULT_MUSIC_VISION_QA_REGEN_ATTEMPTS)


def _music_instrumental_gap_seconds():
    return _env_float("CONTENT_FACTORY_MUSIC_INSTRUMENTAL_GAP_SECONDS", DEFAULT_MUSIC_INSTRUMENTAL_GAP_SECONDS)


def _music_fallback_quotes_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_FALLBACK_QUOTES_ENABLED", default=True)


def _music_fallback_lyrics_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_FALLBACK_LYRICS_ENABLED", default=True)


def _music_shorts_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_SHORTS_ENABLED", default=True)


def _music_shorts_duration_seconds():
    return _env_float("CONTENT_FACTORY_MUSIC_SHORTS_DURATION_SECONDS", DEFAULT_MUSIC_SHORTS_DURATION_SECONDS)


def _music_shorts_cta_seconds():
    return _env_float("CONTENT_FACTORY_MUSIC_SHORTS_CTA_SECONDS", DEFAULT_MUSIC_SHORTS_CTA_SECONDS)


def _music_shorts_elevenlabs_cta_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_SHORTS_ELEVENLABS_CTA_ENABLED", default=True) and bool(_provider_api_key("elevenlabs"))


def _music_shorts_channel_name():
    return os.getenv("CONTENT_FACTORY_MUSIC_CHANNEL_NAME", "Power Music").strip() or "Power Music"


def _music_shorts_cta_text():
    return compact_text(
        os.getenv(
            "CONTENT_FACTORY_MUSIC_SHORTS_CTA_TEXT",
            "Si esta energia te movio, suscribete a Power Music. Musica con proposito para evolucionar la mente.",
        ),
        220,
    )


def _music_fallback_frame_mode():
    value = os.getenv("CONTENT_FACTORY_MUSIC_FALLBACK_FRAME_MODE", "thumbnail").strip().lower()
    if value in {"local", "abstract", "off"}:
        return "local"
    return "thumbnail"


def _parse_json_object(text):
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _evaluate_music_frame_with_openai_vision(image_path, beat):
    if not _music_vision_qa_enabled():
        return {"enabled": False}
    try:
        from openai import OpenAI

        image_path = Path(image_path)
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
        prompt = (
            "You are a strict visual QA critic for a premium motivational music visualizer. "
            "Return only JSON with keys: passed boolean, score 0-100, issues array, hasReadableText boolean, "
            "hasRandomDomesticObject boolean, brandFit 0-100. Reject if the image has readable text, fake letters, "
            "logos, screens with writing, clothes iron, ironing board, random household objects, cheap stock-photo look, "
            "floating weights, physically impossible props, a dumbbell/barbell between legs, running in office clothes, "
            "deformed anatomy, mismatched human scale, or anything that does not fit a premium symbolic music video. "
            f"Beat context: section={compact_text(beat.get('section'), 60)}, storyMoment={compact_text(beat.get('storyMoment'), 240)}, "
            f"shotRecipe={json.dumps(beat.get('shotRecipe') or {}, ensure_ascii=False)[:1200]}."
        )
        response = client.chat.completions.create(
            model=_music_vision_qa_model(),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{encoded}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=260,
        )
        text = response.choices[0].message.content if response.choices else ""
        data = _parse_json_object(text)
        if not data:
            data = {"passed": False, "score": 0, "issues": ["vision_qa_returned_non_json"], "raw": compact_text(text, 300)}
        data["enabled"] = True
        data["model"] = _music_vision_qa_model()
        return data
    except Exception as exc:
        return {"enabled": True, "passed": None, "score": None, "issues": ["vision_qa_failed"], "error": str(exc)[:300]}


def _vision_qa_failed(qa_result):
    if not isinstance(qa_result, dict) or not qa_result.get("enabled"):
        return False
    issue_text = " ".join(str(item).lower() for item in (qa_result.get("issues") or []))
    hard_markers = [
        "readable text",
        "fake letters",
        "pseudo",
        "logo",
        "watermark",
        "household",
        "domestic",
        "iron",
        "ironing",
        "floating",
        "weight",
        "dumbbell",
        "barbell",
        "between legs",
        "anatomy",
        "deformed",
        "mismatched",
        "scale",
        "office clothes",
        "stock-photo",
        "stock photo",
    ]
    if qa_result.get("hasReadableText") is True or qa_result.get("hasRandomDomesticObject") is True:
        qa_result["hardRejected"] = True
        return True
    if any(marker in issue_text for marker in hard_markers):
        qa_result["hardRejected"] = True
        return True
    try:
        score = float(qa_result.get("score"))
    except Exception:
        score = None
    soft_min = _music_vision_qa_soft_min_score()
    if score is not None and score < soft_min:
        return True
    try:
        brand_fit = float(qa_result.get("brandFit"))
    except Exception:
        brand_fit = None
    if brand_fit is not None and brand_fit < soft_min:
        return True
    min_score = _music_vision_qa_min_score()
    if qa_result.get("passed") is False or (score is not None and score < min_score) or (brand_fit is not None and brand_fit < min_score):
        qa_result["softAccepted"] = True
        return False
    return False


def _qa_repair_prompt(prompt, qa_result, beat, attempt):
    issues = ", ".join(str(item) for item in (qa_result.get("issues") or [])[:8]) if isinstance(qa_result, dict) else ""
    recipe = beat.get("shotRecipe") if isinstance(beat.get("shotRecipe"), dict) else {}
    return compact_text(
        (
            f"{prompt}\n\n"
            f"STRICT REPAIR PASS {attempt}: previous frame failed QA issues: {issues}. "
            "Regenerate with simpler, safer composition. One subject only. Objects must be physically grounded with clear contact shadows. "
            "No floating weights, no object between legs, no deformed human body, no mismatched human scale, no random domestic objects, no text, no logos. "
            f"Follow locked shot recipe exactly: subject={recipe.get('subject')}; wardrobe={recipe.get('wardrobe')}; "
            f"action={recipe.get('action')}; propRules={recipe.get('propRules')}; composition={recipe.get('composition')}."
        ),
        2600,
    )


def _write_openai_image_data(image_data, output_path):
    b64_value = getattr(image_data, "b64_json", None)
    if b64_value is None and isinstance(image_data, dict):
        b64_value = image_data.get("b64_json")
    if b64_value:
        output_path.write_bytes(base64.b64decode(b64_value))
        return output_path.exists() and output_path.stat().st_size > 0

    image_url = getattr(image_data, "url", None)
    if image_url is None and isinstance(image_data, dict):
        image_url = image_data.get("url")
    if image_url:
        with urllib.request.urlopen(image_url, timeout=120) as resp:
            output_path.write_bytes(resp.read())
        return output_path.exists() and output_path.stat().st_size > 0
    return False


def _thumbnail_hook_text(package, title):
    youtube = package.get("youtube") if isinstance(package.get("youtube"), dict) else {}
    candidates = [
        youtube.get("thumbnailText"),
        package.get("mainHook"),
        package.get("mantra"),
        title,
    ]
    for candidate in candidates:
        text = compact_text(candidate, 70)
        if text:
            return text
    return title or "POWER MUSIC"


def _build_music_thumbnail_prompt(package, title, subtitle, hook_text):
    video = _video_concept(package)
    visual_identity = compact_text(video.get("visualIdentity"), 360) or (
        "premium cinematic music-video identity, emotional, bold, high contrast, creator-grade"
    )
    lyrics = compact_text(package.get("lyrics"), 700)
    cover_prompt = compact_text(package.get("coverPrompt"), 700)
    palette = ", ".join(str(c) for c in (video.get("palette") or [])[:4]) or "deep black, gold, ember red"
    return (
        "Create a text-free YouTube music thumbnail background, 16:9 landscape.\n"
        f"Song title metadata, do not render as text: {title}.\n"
        f"Clickable hook phrase metadata, added later by backend overlay only: {hook_text}.\n"
        f"Subtitle/emotional promise: {subtitle}.\n"
        f"Visual identity: {visual_identity}.\n"
        f"Palette: {palette}.\n"
        f"Lyric excerpt for meaning: {lyrics}.\n"
        f"Cover direction: {cover_prompt}.\n"
        "Make the image visually tied to the song's emotional conflict, power, ambition, desire, or victory, not a generic gym poster. "
        "Use one iconic cinematic metaphor, strong human emotion, luxury architecture, confident silhouette, or symbolic object, dramatic depth, premium lighting, "
        "clear subject, high click appeal, polished music-video poster quality. Leave clean negative space on the left "
        "for exact title overlay by the backend. "
        f"{TEXT_FREE_NEGATIVE_PROMPT} No PowerPoint card layout, no flat template, no poster text, no title text, no fake letters anywhere."
    )


def _generate_music_thumbnail_background(package, title, subtitle, hook_text, output_path):
    if not _music_premium_thumbnail_enabled():
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "").strip())
        prompt = _build_music_thumbnail_prompt(package, title, subtitle, hook_text)
        last_error = ""
        for model in _music_thumbnail_model_candidates():
            params = {
                "model": model,
                "prompt": prompt,
                "size": _music_thumbnail_size(model),
                "quality": _music_thumbnail_quality(),
                "n": 1,
            }
            if str(model).startswith("gpt-image"):
                params["output_format"] = "jpeg"
                params["output_compression"] = 92
            try:
                response = client.images.generate(**params)
            except Exception as exc:
                last_error = str(exc)[:300]
                if "output_format" in last_error or "output_compression" in last_error:
                    params.pop("output_format", None)
                    params.pop("output_compression", None)
                    try:
                        response = client.images.generate(**params)
                    except Exception as retry_exc:
                        last_error = str(retry_exc)[:300]
                        print(f"   [music-thumbnail] {model} retry failed: {last_error}", flush=True)
                        continue
                else:
                    print(f"   [music-thumbnail] {model} failed: {last_error}", flush=True)
                    continue
            data = getattr(response, "data", None) or []
            if not data:
                last_error = "Image API returned no data"
                continue
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if _write_openai_image_data(data[0], output_path):
                return model
        if last_error:
            print(f"   [music-thumbnail] OpenAI thumbnail unavailable: {last_error}", flush=True)
        return ""
    except Exception as exc:
        print(f"   [music-thumbnail] OpenAI thumbnail failed: {exc}", flush=True)
        return ""


def _draw_music_thumbnail_overlay(base_image_path, output_path, palette, title, hook_text, subtitle):
    try:
        img = Image.open(base_image_path).convert("RGB")
    except Exception:
        return False
    img = _resize_cover(img, THUMB_SIZE).convert("RGBA")
    w, h = THUMB_SIZE
    shade = Image.new("RGBA", THUMB_SIZE, (0, 0, 0, 0))
    px = shade.load()
    for y in range(h):
        for x in range(w):
            left = max(0.0, 1.0 - (x / max(1, w * 0.72)))
            bottom = max(0.0, (y - h * 0.55) / max(1, h * 0.45))
            alpha = int(min(210, 52 + left * 168 + bottom * 58))
            px[x, y] = (0, 0, 0, alpha)
    img = Image.alpha_composite(img, shade)
    draw = ImageDraw.Draw(img, "RGBA")

    paper = (250, 246, 236, 255)
    dim = (225, 215, 197, 230)
    ember = (*palette[2], 255)
    gold = (*palette[1], 250)
    margin = 68
    badge_font = load_font(26, bold=False)
    hook_font = load_font(74, bold=True)
    title_font = load_font(34, bold=False)

    draw.text((margin, 46), "POWER MUSIC", font=badge_font, fill=gold)
    draw.rounded_rectangle((margin, 90, margin + 250, 96), radius=3, fill=ember)

    hook_lines = _wrap_text(draw, compact_text(hook_text, 58).upper(), hook_font, 660)[:3]
    while len(hook_lines) > 2 and hook_font.size > 54:
        hook_font = load_font(hook_font.size - 4, bold=True)
        hook_lines = _wrap_text(draw, compact_text(hook_text, 58).upper(), hook_font, 690)[:3]
    y = 220
    for line in hook_lines:
        draw.text((margin, y), line, font=hook_font, fill=paper, stroke_width=4, stroke_fill=(0, 0, 0, 210))
        y += hook_font.size + 8

    title_clean = compact_text(title, 90)
    if title_clean and title_clean.lower() != compact_text(hook_text, 90).lower():
        for line in _wrap_text(draw, title_clean, title_font, 620)[:2]:
            draw.text((margin, y + 18), line, font=title_font, fill=dim, stroke_width=2, stroke_fill=(0, 0, 0, 180))
            y += title_font.size + 4

    if subtitle:
        sub_font = load_font(26, bold=False)
        sub = compact_text(subtitle, 110)
        for line in _wrap_text(draw, sub, sub_font, 640)[:2]:
            draw.text((margin, h - 110), line, font=sub_font, fill=dim)
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=94)
    return output_path.exists() and output_path.stat().st_size > 5000


def _build_music_thumbnail(package, palette, title, subtitle, output_path):
    hook_text = _thumbnail_hook_text(package, title)
    raw_path = output_path.with_name("thumbnail_openai_raw.jpg")
    thumbnail_model = _generate_music_thumbnail_background(package, title, subtitle, hook_text, raw_path)
    if thumbnail_model:
        if _draw_music_thumbnail_overlay(raw_path, output_path, palette, title, hook_text, subtitle):
            return f"openai_{thumbnail_model}_exact_overlay"

    fallback = _draw_frame(THUMB_SIZE, palette, title, subtitle, hook_text, package.get("coverPrompt"), 17)
    fallback.save(output_path, quality=94)
    return "local_exact_overlay_fallback"


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
    only a cinematic grade. Lyric text is intentionally disabled by default;
    titles and hooks belong in the thumbnail/cover, not inside every frame.
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
    lyric_font = load_font(44, bold=True)
    margin = 74

    lyric = compact_text(beat.get("lyric") or beat.get("overlay"), 96)
    if lyric and beat.get("showLyricOverlay"):
        lines = _wrap_text(draw, lyric, lyric_font, w - margin * 2 - 40)[:2]
        total_h = len(lines) * 52
        y = h - 92 - total_h
        for line in lines:
            draw.text((margin, y), line, font=lyric_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 180))
            y += 52

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=93)
    return output_path.exists() and output_path.stat().st_size > 5000


def _draw_fallback_quote(draw, quote, box, palette):
    if not _music_fallback_quotes_enabled():
        return False
    quote = compact_text(quote, 92)
    if not quote:
        return False
    x1, y1, x2, y2 = box
    max_width = max(240, x2 - x1)
    font = load_font(56, bold=True)
    lines = _wrap_text(draw, quote, font, max_width)[:2]
    while len(lines) > 2 and font.size > 34:
        font = load_font(font.size - 4, bold=True)
        lines = _wrap_text(draw, quote, font, max_width)[:2]
    line_h = font.size + 10
    total_h = line_h * len(lines)
    y = min(y2 - total_h, max(y1, y2 - total_h))
    paper = (246, 242, 232, 248)
    accent = (*palette[1], 230)
    draw.rounded_rectangle(
        (x1 - 22, y - 20, x2 + 22, y + total_h + 22),
        radius=24,
        fill=(0, 0, 0, 96),
        outline=(*palette[2], 105),
        width=2,
    )
    draw.line((x1, y - 4, min(x2, x1 + 180), y - 4), fill=accent, width=5)
    for line in lines:
        draw.text((x1, y), line, font=font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 210))
        y += line_h
    return True


def _fallback_overlay_text(beat):
    if (beat.get("showLyricOverlay") or beat.get("showFallbackLyricOverlay")) and not beat.get("isInstrumentalGap"):
        lyric = compact_text(beat.get("lyric") or beat.get("overlay"), 92)
        if lyric:
            return lyric
    return compact_text(beat.get("fallbackQuote"), 92)


def _beat_uses_fallback_lyric_overlay(beat):
    return bool(
        beat.get("showFallbackLyricOverlay")
        and not beat.get("isInstrumentalGap")
        and compact_text(beat.get("lyric") or beat.get("overlay"), 92)
    )


def _draw_music_visual_fallback_frame(size, palette, title, beat, seed):
    """Text-free fallback frame used only when generated images are missing."""
    img = _background(size, palette, seed=seed)
    w, h = size
    draw = ImageDraw.Draw(img, "RGBA")
    ember = (*palette[2], 245)
    gold = (*palette[1], 210)
    margin = int(w * 0.055)
    lyric_font = load_font(48, bold=True)

    for offset in range(0, 5):
        alpha = max(25, 95 - offset * 16)
        draw.rounded_rectangle(
            (
                margin + offset * 18,
                margin + offset * 12,
                w - margin - offset * 18,
                h - margin - offset * 12,
            ),
            radius=32,
            outline=(*palette[2], alpha),
            width=2,
        )
    draw.line((margin, int(h * 0.72), w - margin, int(h * 0.72)), fill=gold, width=3)
    draw.ellipse((int(w * 0.62), int(h * 0.23), int(w * 0.84), int(h * 0.62)), outline=ember, width=5)

    fallback_text = _fallback_overlay_text(beat)
    if fallback_text and (beat.get("showLyricOverlay") or beat.get("showFallbackLyricOverlay")) and not beat.get("isInstrumentalGap"):
        y = int(h * 0.68)
        for line in _wrap_text(draw, fallback_text, lyric_font, w - margin * 2)[:2]:
            paper = (246, 242, 232, 245)
            draw.text((margin, y), line, font=lyric_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 190))
            y += lyric_font.size + 8
    else:
        _draw_fallback_quote(draw, fallback_text, (margin, int(h * 0.58), int(w * 0.72), h - margin - 34), palette)
    return img.convert("RGB")


def _thumbnail_fallback_source(thumbnail_path, thumbnail_engine=""):
    thumbnail_path = Path(thumbnail_path)
    raw_path = thumbnail_path.with_name("thumbnail_openai_raw.jpg")
    if raw_path.exists() and raw_path.stat().st_size > 5000:
        return raw_path, "thumbnail_raw"
    if (
        str(thumbnail_engine or "").lower().startswith("openai")
        and thumbnail_path.exists()
        and thumbnail_path.stat().st_size > 5000
    ):
        return thumbnail_path, "thumbnail_cropped"
    return None, ""


def _compose_thumbnail_fallback_frame(thumbnail_path, output_path, palette, beat, seed, thumbnail_engine=""):
    source_path, source_label = _thumbnail_fallback_source(thumbnail_path, thumbnail_engine=thumbnail_engine)
    if not source_path:
        return False, ""
    try:
        img = Image.open(source_path).convert("RGB")
    except Exception:
        return False, ""

    # The final thumbnail can contain title text on the left. For video fallback
    # frames, crop toward the visual area so the frame feels related without
    # repeating cover typography across the whole song.
    if source_label == "thumbnail_cropped":
        src_w, src_h = img.size
        crop_left = int(src_w * 0.52)
        crop = img.crop((crop_left, 0, src_w, src_h))
        img = _resize_cover(crop, VIDEO_SIZE)
    else:
        img = _resize_cover(img, VIDEO_SIZE)

    img = img.convert("RGBA").filter(ImageFilter.GaussianBlur(0.55))
    shade = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    px = shade.load()
    w, h = VIDEO_SIZE
    for y in range(h):
        for x in range(w):
            edge = max(abs((x / max(1, w - 1)) - 0.5), abs((y / max(1, h - 1)) - 0.5)) * 2
            alpha = int(34 + max(0.0, edge - 0.35) * 104)
            px[x, y] = (0, 0, 0, min(156, alpha))
    img = Image.alpha_composite(img, shade)

    draw = ImageDraw.Draw(img, "RGBA")
    gold = (*palette[1], 125)
    ember = (*palette[2], 145)
    scene_number = int(beat.get("scene_number") or 0)
    offset = (seed + scene_number * 37) % 180
    draw.line((90 + offset, h - 96, w - 120, h - 96), fill=gold, width=3)
    draw.rounded_rectangle((74, 64, w - 74, h - 64), radius=34, outline=ember, width=2)

    fallback_text = _fallback_overlay_text(beat)
    if fallback_text and (beat.get("showLyricOverlay") or beat.get("showFallbackLyricOverlay")) and not beat.get("isInstrumentalGap"):
        paper = (246, 242, 232, 245)
        lyric_font = load_font(44, bold=True)
        y = h - 168
        for line in _wrap_text(draw, fallback_text, lyric_font, w - 170)[:2]:
            draw.text((84, y), line, font=lyric_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 190))
            y += 52
    else:
        _draw_fallback_quote(draw, fallback_text, (96, int(h * 0.61), int(w * 0.66), h - 112), palette)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=93)
    return output_path.exists() and output_path.stat().st_size > 5000, source_label


def _write_music_fallback_frame(thumbnail_path, image_path, palette, title, beat, seed, thumbnail_engine=""):
    if _music_fallback_frame_mode() == "thumbnail":
        ok, source = _compose_thumbnail_fallback_frame(thumbnail_path, image_path, palette, beat, seed, thumbnail_engine=thumbnail_engine)
        if ok:
            return source
    frame = _draw_music_visual_fallback_frame(VIDEO_SIZE, palette, title, beat, seed)
    frame.save(image_path, quality=92)
    return "local_fallback"


def _draw_power_music_brand(draw, palette, top=66):
    channel = _music_shorts_channel_name().upper()
    font = load_font(42, bold=True)
    small = load_font(22, bold=True)
    x = 64
    draw.text((x, top), channel, font=font, fill=(246, 242, 232, 246), stroke_width=2, stroke_fill=(0, 0, 0, 190))
    line_y = top + font.size + 14
    draw.line((x, line_y, x + 260, line_y), fill=(*palette[2], 235), width=6)
    draw.text((x, line_y + 16), "MUSICA CON PROPOSITO", font=small, fill=(*palette[1], 220))


def _short_cta_lines():
    return [
        "Suscribete",
        "para mas musica con proposito",
    ]


def _compose_music_short_frame(source_path, output_path, palette, title, beat, spec, show_cta=False):
    try:
        source = Image.open(source_path).convert("RGB")
    except Exception:
        source = _background(VIDEO_SIZE, palette, seed=int(beat.get("scene_number") or 1)).convert("RGB")
    bg = _resize_cover(source, SHORT_SIZE).convert("RGBA").filter(ImageFilter.GaussianBlur(9))
    shade = Image.new("RGBA", SHORT_SIZE, (0, 0, 0, 0))
    px = shade.load()
    w, h = SHORT_SIZE
    for y in range(h):
        for x in range(w):
            vertical = y / max(1, h - 1)
            edge = max(abs((x / max(1, w - 1)) - 0.5) * 2, abs(vertical - 0.5) * 1.4)
            alpha = int(58 + max(0.0, edge - 0.3) * 116)
            px[x, y] = (0, 0, 0, min(176, alpha))
    img = Image.alpha_composite(bg, shade)

    # Preserve the approved landscape frame as a premium poster inside the vertical canvas.
    fg_w = 980
    fg_h = int(fg_w * 9 / 16)
    fg = source.resize((fg_w, fg_h), Image.LANCZOS).convert("RGBA")
    fg = _add_vignette(fg, palette)
    draw = ImageDraw.Draw(img, "RGBA")
    x = (w - fg_w) // 2
    y = 392
    draw.rounded_rectangle((x - 10, y - 10, x + fg_w + 10, y + fg_h + 10), radius=32, fill=(0, 0, 0, 130))
    img.alpha_composite(fg, (x, y))

    _draw_power_music_brand(draw, palette)
    label_font = load_font(28, bold=True)
    title_font = load_font(54, bold=True)
    caption_font = load_font(36, bold=True)
    paper = (246, 242, 232, 248)
    gold = (*palette[1], 238)
    ember = (*palette[2], 235)
    label = compact_text(spec.get("title") or "Short", 40).upper()
    draw.text((64, 1010), label, font=label_font, fill=ember)
    hook = compact_text(beat.get("fallbackQuote") or beat.get("lyric") or title, 74)
    for i, line in enumerate(_wrap_text(draw, hook, title_font, w - 128)[:2]):
        draw.text((64, 1062 + i * 66), line, font=title_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 210))
    note = compact_text(spec.get("caption") or "Guarda esta energia.", 90)
    for i, line in enumerate(_wrap_text(draw, note, caption_font, w - 128)[:2]):
        draw.text((64, 1228 + i * 48), line, font=caption_font, fill=gold, stroke_width=2, stroke_fill=(0, 0, 0, 160))

    if show_cta:
        cta_font = load_font(66, bold=True)
        sub_font = load_font(36, bold=True)
        box = (54, h - 352, w - 54, h - 94)
        draw.rounded_rectangle(box, radius=34, fill=(0, 0, 0, 170), outline=ember, width=3)
        cta_lines = _short_cta_lines()
        draw.text((86, h - 310), cta_lines[0].upper(), font=cta_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 230))
        draw.text((90, h - 220), cta_lines[1], font=sub_font, fill=gold, stroke_width=2, stroke_fill=(0, 0, 0, 180))
        draw.text((90, h - 162), _music_shorts_channel_name(), font=sub_font, fill=paper, stroke_width=2, stroke_fill=(0, 0, 0, 180))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output_path, quality=93)
    return output_path.exists() and output_path.stat().st_size > 5000


def _score_short_beat(beat, profile):
    text = " ".join(
        compact_text(value, 160).lower()
        for value in [beat.get("section"), beat.get("lyric"), beat.get("storyMoment"), beat.get("fallbackQuote")]
    )
    tokens = set(_normalize_token_text(text))
    if profile == "energia":
        keywords = {"fuego", "rapido", "fuerte", "poder", "fuerza", "entreno", "hierro", "gano", "subo", "meta", "disciplina"}
    else:
        keywords = {"proposito", "mente", "evolucionar", "promesa", "version", "futuro", "elijo", "identidad", "silencio", "cambio"}
    score = len(tokens & keywords) * 4
    if beat.get("isInstrumentalGap"):
        score -= 2
    score += float(beat.get("alignmentScore") or 0)
    return score


def _select_music_short_specs(beats, duration):
    target_duration = min(max(24.0, _music_shorts_duration_seconds()), max(24.0, min(90.0, duration)))
    usable = [beat for beat in beats if isinstance(beat, dict)]

    def choose_start(profile, fallback_ratio):
        min_start = 0.0 if profile == "energia" else duration * 0.38
        max_start = max(0.0, duration - target_duration)
        candidates = [
            beat for beat in usable
            if min_start <= float(beat.get("start") or 0) <= max_start + 1
        ]
        if not candidates:
            return min(max_start, max(0.0, duration * fallback_ratio))
        best = max(candidates, key=lambda beat: (_score_short_beat(beat, profile), -abs(float(beat.get("start") or 0) - duration * fallback_ratio)))
        return min(max_start, max(0.0, float(best.get("start") or 0) - 1.0))

    first_start = choose_start("energia", 0.08)
    second_start = choose_start("identidad", 0.55)
    if abs(second_start - first_start) < target_duration * 0.6:
        second_start = min(max(0.0, duration - target_duration), max(second_start, duration * 0.52))
    return [
        {
            "index": 1,
            "label": "energia",
            "title": "Energia",
            "caption": "Guarda esta energia para cuando falte fuerza.",
            "start": round(first_start, 3),
            "end": round(min(duration, first_start + target_duration), 3),
            "duration": round(min(duration, first_start + target_duration) - first_start, 3),
        },
        {
            "index": 2,
            "label": "identidad",
            "title": "Identidad",
            "caption": "No es solo musica. Es una decision interna.",
            "start": round(second_start, 3),
            "end": round(min(duration, second_start + target_duration), 3),
            "duration": round(min(duration, second_start + target_duration) - second_start, 3),
        },
    ]


def _generate_music_short_cta_audio(output_dir, label):
    if not _music_shorts_elevenlabs_cta_enabled():
        return None
    try:
        from scripts.elevenlabs_tts import generate_narration, get_voice_settings
    except Exception:
        try:
            from elevenlabs_tts import generate_narration, get_voice_settings
        except Exception:
            return None
    voice = os.getenv("CONTENT_FACTORY_MUSIC_SHORTS_CTA_VOICE", "Diego").strip() or "Diego"
    model = os.getenv("CONTENT_FACTORY_MUSIC_SHORTS_CTA_MODEL", "eleven_multilingual_v2").strip() or "eleven_multilingual_v2"
    settings = get_voice_settings(voice)
    cta_path = output_dir / f"cta_{safe_slug(label)}.mp3"
    ok = generate_narration(
        _music_shorts_cta_text(),
        cta_path,
        voice=voice,
        model=model,
        stability=float(settings.get("stability", 0.5)),
        similarity_boost=float(settings.get("similarity_boost", 0.8)),
        speed=float(os.getenv("CONTENT_FACTORY_MUSIC_SHORTS_CTA_SPEED", "1.04")),
        style=float(settings.get("style", 0.1)),
    )
    if ok and cta_path.exists() and cta_path.stat().st_size > 1000:
        return cta_path
    return None


def _beats_for_short_window(beats, start, end):
    selected = []
    for beat in beats:
        beat_start = float(beat.get("start") or 0)
        beat_end = float(beat.get("end") or beat_start)
        overlap = max(0.0, min(end, beat_end) - max(start, beat_start))
        if overlap >= 0.25:
            selected.append((beat, max(start, beat_start), min(end, beat_end), overlap))
    if not selected and beats:
        closest = min(beats, key=lambda beat: abs(float(beat.get("start") or 0) - start))
        selected.append((closest, start, end, max(0.5, end - start)))
    return selected


def _render_power_music_short(spec, beats, assets_dir, audio_path, output_dir, palette, title):
    label = safe_slug(spec.get("label") or f"short_{spec.get('index') or 1}", "short")
    short_dir = output_dir / "shorts" / label
    frames_dir = short_dir / "frames"
    segments_dir = short_dir / "segments"
    frames_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    start = float(spec.get("start") or 0)
    end = float(spec.get("end") or start + float(spec.get("duration") or 30))
    duration = max(1.0, end - start)
    cta_seconds = min(_music_shorts_cta_seconds(), max(3.0, duration * 0.18))
    selected = _beats_for_short_window(beats, start, end)
    segment_paths = []
    for local_index, (beat, seg_start, seg_end, overlap) in enumerate(selected, start=1):
        image_path = assets_dir / f"beat_{int(beat.get('scene_number') or local_index):03d}.jpg"
        frame_path = frames_dir / f"frame_{local_index:03d}.jpg"
        segment_path = segments_dir / f"segment_{local_index:03d}.mp4"
        rel_end = seg_end - start
        show_cta = rel_end >= max(0.0, duration - cta_seconds)
        _compose_music_short_frame(image_path, frame_path, palette, title, beat, spec, show_cta=show_cta)
        segment_duration = max(0.5, overlap)
        frames = max(1, int(math.ceil(segment_duration * FPS)))
        zoom = "zoompan=z='min(zoom+0.0012,1.11)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        vf = f"scale={SHORT_SIZE[0]}:{SHORT_SIZE[1]},{zoom}:d={frames}:s={SHORT_SIZE[0]}x{SHORT_SIZE[1]}:fps={FPS},format=yuv420p"
        _run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame_path),
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
                "19",
                "-pix_fmt",
                "yuv420p",
                str(segment_path),
            ],
            timeout=max(120, int(segment_duration * 18)),
        )
        segment_paths.append(segment_path)
    concat_path = short_dir / "concat.txt"
    concat_path.write_text("".join(f"file '{path.resolve().as_posix()}'\n" for path in segment_paths), encoding="utf-8")
    silent_path = short_dir / "silent.mp4"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(silent_path)], timeout=600)

    cta_audio = _generate_music_short_cta_audio(short_dir, label)
    output_path = output_dir / "shorts" / f"POWER_MUSIC_SHORT_{int(spec.get('index') or 1):02d}_{label}.mp4"
    if cta_audio:
        cta_duration = min(probe_audio_duration(cta_audio), duration)
        delay_ms = int(max(0.0, duration - cta_duration - 0.25) * 1000)
        fade_start = max(0.0, duration - cta_duration - 0.4)
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent_path),
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(audio_path),
                "-i",
                str(cta_audio),
                "-filter_complex",
                f"[1:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={fade_start:.3f}:d=0.9[music];"
                f"[2:a]adelay={delay_ms}|{delay_ms},apad,atrim=0:{duration:.3f}[voice];"
                "[music][voice]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map",
                "0:v:0",
                "-map",
                "[a]",
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
                "-t",
                f"{duration:.3f}",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            timeout=max(300, int(duration * 12)),
        )
    else:
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(silent_path),
                "-ss",
                f"{start:.3f}",
                "-t",
                f"{duration:.3f}",
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
                str(output_path),
            ],
            timeout=max(300, int(duration * 12)),
        )
    return {
        "index": int(spec.get("index") or 0),
        "label": spec.get("label") or label,
        "title": spec.get("title") or label.title(),
        "caption": spec.get("caption") or "",
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(duration, 3),
        "fileName": output_path.name,
        "path": output_path,
        "ctaVoice": bool(cta_audio),
        "ctaText": _music_shorts_cta_text(),
        "channel": _music_shorts_channel_name(),
        "format": "youtube_short_vertical_1080x1920",
    }


def _build_power_music_shorts(beats, assets_dir, audio_path, output_dir, palette, title, duration):
    if not _music_shorts_enabled() or duration < 12:
        return []
    shorts = []
    for spec in _select_music_short_specs(beats, duration)[:2]:
        try:
            short = _render_power_music_short(spec, beats, assets_dir, audio_path, output_dir, palette, title)
            if Path(short["path"]).exists() and Path(short["path"]).stat().st_size > 5000:
                shorts.append(short)
        except Exception as exc:
            shorts.append(
                {
                    "index": int(spec.get("index") or 0),
                    "label": spec.get("label") or "",
                    "status": "failed",
                    "error": str(exc)[:300],
                    "start": spec.get("start"),
                    "end": spec.get("end"),
                    "duration": spec.get("duration"),
                }
            )
    return shorts


def _normalize_existing_short_beats(metadata, package, duration):
    raw_beats = []
    if isinstance(metadata, dict):
        raw_beats = metadata.get("visualBeats") if isinstance(metadata.get("visualBeats"), list) else []
    beats = []
    for index, item in enumerate(raw_beats or [], start=1):
        if not isinstance(item, dict):
            continue
        start = max(0.0, float(item.get("start") or 0))
        end = float(item.get("end") or 0)
        if end <= start:
            end = min(float(duration), start + max(1.0, float(item.get("duration") or 6.0)))
        beats.append(
            {
                **item,
                "scene_number": int(item.get("scene_number") or item.get("index") or index),
                "start": round(start, 3),
                "end": round(min(float(duration), end), 3),
                "duration": round(max(0.5, min(float(duration), end) - start), 3),
            }
        )
    if beats:
        return beats
    fallback_beats, _ = _build_visual_beats(
        package if isinstance(package, dict) else {},
        duration,
        max(8.0, min(16.0, float(duration) / 8.0)),
        18,
        timed_segments=None,
        show_lyric_overlay=False,
    )
    return fallback_beats


def _short_window_hero_beat(beats, start, end):
    window = _beats_for_short_window(beats, start, end)
    if window:
        return max(window, key=lambda item: item[3])[0]
    if beats:
        return min(beats, key=lambda beat: abs(float(beat.get("start") or 0) - start))
    return {"scene_number": 1, "start": start, "end": end, "lyric": "", "fallbackQuote": ""}


def _make_music_short_overlay(output_path, palette, title, beat, spec, *, cta=False):
    img = Image.new("RGBA", SHORT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    _draw_power_music_brand(draw, palette, top=62)
    paper = (246, 242, 232, 250)
    gold = (*palette[1], 238)
    ember = (*palette[2], 235)
    label_font = load_font(28, bold=True)
    title_font = load_font(54, bold=True)
    caption_font = load_font(36, bold=True)
    draw.text((64, 1010), compact_text(spec.get("title") or "Short", 40).upper(), font=label_font, fill=ember)
    hook = compact_text(beat.get("fallbackQuote") or beat.get("lyric") or title, 78)
    for i, line in enumerate(_wrap_text(draw, hook, title_font, SHORT_SIZE[0] - 128)[:2]):
        draw.text((64, 1062 + i * 66), line, font=title_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 220))
    note = compact_text(spec.get("caption") or "Guarda esta energia.", 90)
    for i, line in enumerate(_wrap_text(draw, note, caption_font, SHORT_SIZE[0] - 128)[:2]):
        draw.text((64, 1228 + i * 48), line, font=caption_font, fill=gold, stroke_width=2, stroke_fill=(0, 0, 0, 180))
    if cta:
        cta_font = load_font(66, bold=True)
        sub_font = load_font(36, bold=True)
        box = (54, SHORT_SIZE[1] - 352, SHORT_SIZE[0] - 54, SHORT_SIZE[1] - 94)
        draw.rounded_rectangle(box, radius=34, fill=(0, 0, 0, 178), outline=ember, width=3)
        cta_lines = _short_cta_lines()
        draw.text((86, SHORT_SIZE[1] - 310), cta_lines[0].upper(), font=cta_font, fill=paper, stroke_width=3, stroke_fill=(0, 0, 0, 230))
        draw.text((90, SHORT_SIZE[1] - 220), cta_lines[1], font=sub_font, fill=gold, stroke_width=2, stroke_fill=(0, 0, 0, 180))
        draw.text((90, SHORT_SIZE[1] - 162), _music_shorts_channel_name(), font=sub_font, fill=paper, stroke_width=2, stroke_fill=(0, 0, 0, 180))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path


def _render_power_music_short_from_video(spec, beats, video_path, output_dir, palette, title):
    label = safe_slug(spec.get("label") or f"short_{spec.get('index') or 1}", "short")
    short_dir = output_dir / "shorts" / label
    short_dir.mkdir(parents=True, exist_ok=True)
    start = float(spec.get("start") or 0)
    end = float(spec.get("end") or start + float(spec.get("duration") or 30))
    duration = max(1.0, end - start)
    cta_seconds = min(_music_shorts_cta_seconds(), max(3.0, duration * 0.18))
    hero = _short_window_hero_beat(beats, start, end)
    overlay_path = _make_music_short_overlay(short_dir / "overlay.png", palette, title, hero, spec, cta=False)
    cta_overlay_path = _make_music_short_overlay(short_dir / "overlay_cta.png", palette, title, hero, spec, cta=True)
    cta_audio = _generate_music_short_cta_audio(short_dir, label)
    output_path = output_dir / "shorts" / f"POWER_MUSIC_SHORT_{int(spec.get('index') or 1):02d}_{label}.mp4"
    video_filter = (
        f"[0:v]scale={SHORT_SIZE[0]}:{SHORT_SIZE[1]}:force_original_aspect_ratio=increase,"
        f"crop={SHORT_SIZE[0]}:{SHORT_SIZE[1]},boxblur=18:1,eq=brightness=-0.08:saturation=0.82[bg];"
        f"[0:v]scale=980:-2:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:392[base];"
        f"[base][1:v]overlay=0:0[brand];"
        f"[brand][2:v]overlay=0:0:enable='gte(t,{max(0.0, duration - cta_seconds):.3f})'[v]"
    )
    if cta_audio:
        cta_duration = min(probe_audio_duration(cta_audio), duration)
        delay_ms = int(max(0.0, duration - cta_duration - 0.25) * 1000)
        fade_start = max(0.0, duration - cta_duration - 0.4)
        filter_complex = (
            f"{video_filter};"
            f"[0:a]afade=t=out:st={fade_start:.3f}:d=0.9[music];"
            f"[3:a]adelay={delay_ms}|{delay_ms},apad,atrim=0:{duration:.3f}[voice];"
            "[music][voice]amix=inputs=2:duration=first:dropout_transition=0[a]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(video_path),
            "-loop",
            "1",
            "-i",
            str(overlay_path),
            "-loop",
            "1",
            "-i",
            str(cta_overlay_path),
            "-i",
            str(cta_audio),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(video_path),
            "-loop",
            "1",
            "-i",
            str(overlay_path),
            "-loop",
            "1",
            "-i",
            str(cta_overlay_path),
            "-filter_complex",
            video_filter,
            "-map",
            "[v]",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    _run(cmd, timeout=max(300, int(duration * 12)))
    return {
        "index": int(spec.get("index") or 0),
        "label": spec.get("label") or label,
        "title": spec.get("title") or label.title(),
        "caption": spec.get("caption") or "",
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(duration, 3),
        "fileName": output_path.name,
        "path": output_path,
        "ctaVoice": bool(cta_audio),
        "ctaText": _music_shorts_cta_text(),
        "channel": _music_shorts_channel_name(),
        "format": "youtube_short_vertical_1080x1920",
        "source": "existing_render_video",
    }


def render_power_music_shorts_from_existing_video(track_id, package, video_path, output_dir, metadata=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package = enrich_package_with_director_plan(package if isinstance(package, dict) else {})
    title = compact_text(package.get("title"), 100) or "Power Music"
    palette = _palette(package)
    duration = probe_media_duration(video_path)
    beats = _normalize_existing_short_beats(metadata if isinstance(metadata, dict) else {}, package, duration)
    shorts = []
    for spec in _select_music_short_specs(beats, duration)[:2]:
        try:
            short = _render_power_music_short_from_video(spec, beats, Path(video_path), output_dir, palette, title)
            if Path(short["path"]).exists() and Path(short["path"]).stat().st_size > 5000:
                shorts.append(short)
        except Exception as exc:
            shorts.append(
                {
                    "index": int(spec.get("index") or 0),
                    "label": spec.get("label") or "",
                    "status": "failed",
                    "error": str(exc)[:300],
                    "start": spec.get("start"),
                    "end": spec.get("end"),
                    "duration": spec.get("duration"),
                    "source": "existing_render_video",
                }
            )
    metadata_path = output_dir / "music_shorts_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "trackId": track_id,
                "title": title,
                "durationSeconds": duration,
                "sourceVideo": Path(video_path).name,
                "musicShorts": [{key: value for key, value in short.items() if key != "path"} for short in shorts],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"musicShorts": shorts, "metadata": metadata_path, "durationSeconds": duration, "renderer": "power_music_shorts_from_existing_video_v1"}


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


def probe_media_duration(media_path):
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
                str(media_path),
            ],
            timeout=60,
        )
        return max(1.0, float(str(result.stdout).strip()))
    except Exception:
        return probe_audio_duration(media_path)


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


def _music_transcription_enabled():
    return _env_bool("CONTENT_FACTORY_MUSIC_TRANSCRIPTION_ENABLED", default=True)


def _music_transcription_provider_order():
    configured = [
        item.strip().lower()
        for item in os.getenv("CONTENT_FACTORY_MUSIC_TRANSCRIPTION_PROVIDERS", "").split(",")
        if item.strip()
    ]
    order = configured or ["elevenlabs", "openai", "deepgram"]
    clean = []
    aliases = {"whisper": "openai", "scribe": "elevenlabs"}
    for provider in order:
        normalized = aliases.get(provider, provider)
        if normalized in {"elevenlabs", "openai", "deepgram"} and normalized not in clean:
            clean.append(normalized)
    return clean or ["openai"]


def _music_transcription_language():
    return os.getenv("CONTENT_FACTORY_MUSIC_TRANSCRIPTION_LANGUAGE", "es").strip() or "es"


def _music_transcription_timeout():
    return _env_int("CONTENT_FACTORY_MUSIC_TRANSCRIPTION_TIMEOUT_SECONDS", 180)


def _provider_api_key(provider):
    if provider == "elevenlabs":
        return os.getenv("ELEVENLABS_API_KEY", "").strip() or os.getenv("XI_API_KEY", "").strip()
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "").strip()
    if provider == "deepgram":
        return os.getenv("DEEPGRAM_API_KEY", "").strip() or os.getenv("DEEPGRAM_API_TOKEN", "").strip()
    return ""


def _normalize_token_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", text, flags=re.I)


def _word_token(value):
    tokens = _normalize_token_text(value)
    return tokens[0] if tokens else ""


def _clean_transcribed_words(words, duration):
    clean = []
    for item in words or []:
        raw = item if isinstance(item, dict) else {}
        word_text = raw.get("word") or raw.get("text") or raw.get("punctuated_word")
        token = _word_token(word_text)
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
                "word": compact_text(word_text, 40),
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


def _subtitle_alignment_quality(segments, units):
    phrase_segments = [
        segment for segment in (segments or [])
        if segment.get("alignmentMode") == "phrase_match" and float(segment.get("alignmentScore") or 0) > 0
    ]
    scores = [float(segment.get("alignmentScore") or 0) for segment in phrase_segments]
    avg_score = sum(scores) / max(1, len(scores))
    phrase_ratio = len(phrase_segments) / max(1, len(segments or []))
    coverage = len(segments or []) / max(1, len(units or []))
    min_score = _env_ratio("CONTENT_FACTORY_MUSIC_SUBTITLE_MIN_ALIGNMENT_SCORE", DEFAULT_SUBTITLE_MIN_ALIGNMENT_SCORE)
    min_phrase_ratio = _env_ratio("CONTENT_FACTORY_MUSIC_SUBTITLE_MIN_PHRASE_RATIO", DEFAULT_SUBTITLE_MIN_PHRASE_RATIO)
    min_segments = min(4, max(1, len(units or []) // 4))
    publishable = (
        len(segments or []) >= min_segments
        and coverage >= 0.35
        and phrase_ratio >= min_phrase_ratio
        and avg_score >= min_score
    )
    return {
        "publishable": publishable,
        "avgAlignmentScore": round(avg_score, 3),
        "phraseMatchRatio": round(phrase_ratio, 3),
        "coverage": round(coverage, 3),
        "minAlignmentScore": min_score,
        "minPhraseMatchRatio": min_phrase_ratio,
        "phraseMatchedSegments": len(phrase_segments),
        "minSegments": min_segments,
    }


def _audio_mime_type(audio_path):
    guessed, _ = mimetypes.guess_type(str(audio_path))
    return guessed or "audio/mpeg"


def _transcribe_with_elevenlabs_scribe(audio_path):
    api_key = _provider_api_key("elevenlabs")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not configured")
    import httpx

    endpoint = os.getenv("CONTENT_FACTORY_MUSIC_ELEVENLABS_STT_ENDPOINT", "https://api.elevenlabs.io/v1/speech-to-text").strip()
    model = os.getenv("CONTENT_FACTORY_MUSIC_ELEVENLABS_STT_MODEL", "scribe_v2").strip() or "scribe_v2"
    with open(audio_path, "rb") as file_obj:
        response = httpx.post(
            endpoint,
            headers={"xi-api-key": api_key},
            params={"enable_logging": "true"},
            data={
                "model_id": model,
                "language_code": _music_transcription_language(),
                "timestamps_granularity": "word",
                "tag_audio_events": "false",
                "diarize": "false",
            },
            files={"file": (Path(audio_path).name, file_obj, _audio_mime_type(audio_path))},
            timeout=_music_transcription_timeout(),
        )
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs STT HTTP {response.status_code}: {compact_text(response.text, 300)}")
    data = response.json()
    if isinstance(data, dict) and isinstance(data.get("transcripts"), dict):
        first = next(iter(data["transcripts"].values()), {})
        if isinstance(first, dict):
            data = first
    return {
        "provider": "elevenlabs",
        "model": model,
        "text": data.get("text") if isinstance(data, dict) else "",
        "words": data.get("words") if isinstance(data, dict) else [],
        "rawLanguage": data.get("language_code") if isinstance(data, dict) else "",
    }


def _transcribe_with_openai_whisper(audio_path):
    api_key = _provider_api_key("openai")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    try:
        from scripts.generate_subtitles import transcribe_with_whisper
    except Exception:
        from generate_subtitles import transcribe_with_whisper

    transcription = transcribe_with_whisper(Path(audio_path))
    if not isinstance(transcription, dict):
        raise RuntimeError("OpenAI Whisper returned empty transcription")
    return {
        "provider": "openai",
        "model": "whisper-1",
        "text": transcription.get("text") or "",
        "words": transcription.get("words") or [],
    }


def _transcribe_with_deepgram(audio_path):
    api_key = _provider_api_key("deepgram")
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY not configured")
    import httpx

    model = os.getenv("CONTENT_FACTORY_MUSIC_DEEPGRAM_MODEL", "nova-3").strip() or "nova-3"
    endpoint = os.getenv("CONTENT_FACTORY_MUSIC_DEEPGRAM_ENDPOINT", "https://api.deepgram.com/v1/listen").strip()
    params = {
        "model": model,
        "smart_format": "true",
        "punctuate": "true",
        "utterances": "true",
        "utt_split": os.getenv("CONTENT_FACTORY_MUSIC_DEEPGRAM_UTT_SPLIT", "0.8"),
    }
    language = _music_transcription_language()
    if language:
        params["language"] = language
    data = Path(audio_path).read_bytes()
    response = httpx.post(
        endpoint,
        headers={"Authorization": f"Token {api_key}", "Content-Type": _audio_mime_type(audio_path)},
        params=params,
        content=data,
        timeout=_music_transcription_timeout(),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Deepgram STT HTTP {response.status_code}: {compact_text(response.text, 300)}")
    payload = response.json()
    alternatives = (((payload.get("results") or {}).get("channels") or [{}])[0].get("alternatives") or [{}])
    primary = alternatives[0] if alternatives else {}
    return {
        "provider": "deepgram",
        "model": model,
        "text": primary.get("transcript") or "",
        "words": primary.get("words") or [],
    }


def _transcribe_music_audio(provider, audio_path):
    if provider == "elevenlabs":
        return _transcribe_with_elevenlabs_scribe(audio_path)
    if provider == "deepgram":
        return _transcribe_with_deepgram(audio_path)
    return _transcribe_with_openai_whisper(audio_path)


def _build_music_timed_segments(package, audio_path, duration):
    providers = _music_transcription_provider_order()
    diagnostics = {
        "enabled": bool(_music_transcription_enabled()),
        "providers": providers,
        "provider": "",
        "model": "",
        "words": 0,
        "segments": 0,
        "publishable": False,
        "visualUsable": False,
        "mode": "disabled",
        "error": "",
        "attempts": [],
    }
    if not diagnostics["enabled"]:
        diagnostics["error"] = "CONTENT_FACTORY_MUSIC_TRANSCRIPTION_ENABLED=false"
        return [], diagnostics
    units = _lyric_units(package.get("lyrics"))
    if not units:
        diagnostics["mode"] = "no_lyrics"
        diagnostics["error"] = "lyrics not available"
        return [], diagnostics

    last_error = ""
    for provider in providers:
        attempt = {"provider": provider, "status": "pending", "words": 0, "segments": 0, "error": ""}
        diagnostics["attempts"].append(attempt)
        if not _provider_api_key(provider):
            attempt["status"] = "skipped"
            attempt["error"] = f"{provider} API key not configured"
            last_error = attempt["error"]
            continue
        try:
            transcription = _transcribe_music_audio(provider, audio_path)
            attempt["model"] = transcription.get("model") if isinstance(transcription, dict) else ""
        except Exception as exc:
            attempt["status"] = "failed"
            attempt["error"] = str(exc)[:500]
            last_error = attempt["error"]
            continue
        words = _clean_transcribed_words((transcription or {}).get("words") or [], duration)
        attempt["words"] = len(words)
        if not words:
            attempt["status"] = "no_words"
            attempt["error"] = f"{provider} returned no word timestamps"
            last_error = attempt["error"]
            continue
        segments = _align_lyrics_to_transcribed_words(units, words, duration)
        attempt["segments"] = len(segments)
        quality = _subtitle_alignment_quality(segments, units)
        visual_usable = bool(segments) and quality.get("coverage", 0) >= _env_ratio(
            "CONTENT_FACTORY_MUSIC_TIMED_VISUALS_MIN_COVERAGE",
            0.18,
        )
        attempt.update({**quality, "visualUsable": visual_usable})
        if not segments:
            attempt["status"] = "alignment_empty"
            attempt["error"] = "lyrics could not be aligned to transcription"
            last_error = attempt["error"]
            continue
        diagnostics.update(quality)
        diagnostics.update(
            {
                "provider": provider,
                "model": (transcription or {}).get("model") or "",
                "words": len(words),
                "segments": len(segments),
                "visualUsable": visual_usable,
            }
        )
        if quality["publishable"]:
            attempt["status"] = "publishable"
            diagnostics["mode"] = f"{provider}_word_aligned"
            return segments, diagnostics
        if visual_usable:
            attempt["status"] = "visual_timing_only"
            diagnostics["mode"] = f"{provider}_timed_visuals_low_confidence"
            diagnostics["error"] = "alignment usable for visual timing but not strong enough for publishable subtitles"
            return segments, diagnostics
        attempt["status"] = "low_confidence"
        attempt["error"] = "lyrics transcription alignment was too weak"
        last_error = attempt["error"]

    diagnostics["mode"] = "transcription_failed"
    diagnostics["error"] = last_error or "no transcription provider produced word timestamps"
    return [], diagnostics


def _build_whisper_subtitle_segments(package, audio_path, duration):
    # Backwards-compatible wrapper for older call sites and metadata names.
    return _build_music_timed_segments(package, audio_path, duration)


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
            {"section": "Intro", "visualPrompt": "premium dark cinematic visualizer opening, black marble, gold rim light, strong silhouette, no text", "textOverlay": ""},
            {"section": "Hook", "visualPrompt": "symbolic power visualizer, steel weights, luxury city lights, ember glow, disciplined silhouette, no text", "textOverlay": ""},
            {"section": "Final", "visualPrompt": "sunrise rooftop over a city, triumphant cinematic calm, gold reflections, no text", "textOverlay": ""},
        ]
    return clean


def _clean_lyric_line(value):
    text = compact_text(value, 180)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_scene_prompt_for_image(value):
    text = compact_text(value, 180)
    lower = text.lower()
    unsafe_markers = [
        "lyric",
        "lyrics",
        "letra",
        "do not render these words",
        "inspired by these",
        "current lyric",
        "previous lyric",
        "next lyric",
    ]
    if any(marker in lower for marker in unsafe_markers):
        return ""
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


def _fallback_quote_pack(package):
    candidates = []

    def add(value):
        text = compact_text(value, 72)
        text = re.sub(r"^\[[^\]]+\]\s*", "", text).strip(" -.,;:")
        if not text:
            return
        if 8 <= len(text) <= 72 and not any(text.lower() == existing.lower() for existing in candidates):
            candidates.append(text)

    for key in ["mainHook", "mantra", "subtitle", "title"]:
        add(package.get(key))

    for unit in _lyric_units(package.get("lyrics")):
        line = compact_text(unit.get("line"), 72)
        if 16 <= len(line) <= 64:
            add(line)
        if len(candidates) >= 10:
            break

    for phrase in [
        "Mas rapido. Mas fuerte.",
        "No negocies con tu excusa.",
        "Hazlo aunque nadie mire.",
        "El fuego tambien se entrena.",
        "Tu disciplina habla por ti.",
        "La fuerza se construye en silencio.",
        "Cuando duela, sigue.",
        "No pares antes de verte cambiar.",
        "Convierte presion en poder.",
        "Hoy no gana la excusa.",
    ]:
        add(phrase)
    return candidates[:14]


def _fallback_quote_for_index(quote_pack, index):
    if not quote_pack:
        return ""
    return compact_text(quote_pack[index % len(quote_pack)], 92)


def _instrumental_visual_line(package, index):
    pack = _fallback_quote_pack(package)
    return _fallback_quote_for_index(pack, index) or compact_text(package.get("mainHook") or package.get("title"), 120) or "Instrumental power passage"


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
    tokens = set(_normalize_token_text(line))
    signals = []
    if tokens & {"miedo", "duda", "caer", "cansado", "excusa", "tiembla"}:
        signals.append("inner resistance turning into controlled strength")
    if tokens & {"cumplo", "promesa", "disciplina", "plan", "paso", "constancia"}:
        signals.append("discipline, commitment, forward motion")
    if tokens & {"fuego", "hierro", "sudor", "entreno", "levanto", "golpe"}:
        signals.append("physical power, heat, texture, effort, controlled intensity")
    if tokens & {"nino", "futuro", "historia", "version", "recuerdo"}:
        signals.append("identity transformation, memory, future self")
    if tokens & {"respiro", "calma", "silencio", "mente", "paz"}:
        signals.append("breath, focus, quiet confidence")
    if tokens & {"decido", "elijo", "hoy", "nunca", "limite", "palabra"}:
        signals.append("decisive boundary, self-command, internal leadership")
    if tokens & {"cama", "amanece", "despierto", "manana", "dia"}:
        signals.append("morning transition, leaving comfort, first disciplined action")
    if tokens & {"corro", "calle", "ruta", "camino", "cima"}:
        signals.append("endurance, road, altitude, sunrise, directional movement")
    if tokens & {"dinero", "exito", "rico", "riqueza", "oro", "lujo", "estatus", "gano", "meta"}:
        signals.append("elegant status, ambition, premium opulence, disciplined success")
    if tokens & {"mujer", "reina", "diosa", "presencia", "mirada"}:
        signals.append("confident feminine presence, elegance, magnetism, power without objectification")
    return ", ".join(signals) or "premium emotional motivation, identity, momentum, aspirational power"


def _visual_story_moment(line, index, section):
    tokens = set(_normalize_token_text(f"{section} {line}"))
    motif_bank = [
        "black marble penthouse at night, city skyline, one strong silhouette, gold rim light",
        "symmetrical luxury hallway with deep shadows, cinematic red and gold accents",
        "confident woman or man in tailored dark clothing, partial silhouette, no readable details",
        "steel dumbbells and chalk dust under dramatic light, no brand marks, no labels",
        "wet black car at night outside a glass tower, headlights cutting through fog",
        "wide staircase in an opulent building, one figure ascending with controlled power",
        "close-up of breath in cold air, face partly shadowed, controlled emotion",
        "abstract but concrete symbol: ember light inside cracked stone, clean negative space",
        "sunrise rooftop above a city, calm victory, architectural symmetry",
        "dark studio with a single spotlight, powerful posture, minimal cinematic scene",
    ]
    if tokens & {"cama", "despierto", "manana", "amanece", "dia"}:
        return "early morning transition from shadow to sunrise, leaving comfort behind, cinematic first action"
    if tokens & {"fuego", "hierro", "sudor", "entreno", "levanto"}:
        return "physical power still life: steel dumbbells or barbell plates, chalk dust, breath, focused movement, no logos"
    if tokens & {"miedo", "duda", "caer", "excusa"}:
        return "internal resistance visualized as shadow and controlled posture, tension without melodrama"
    if tokens & {"promesa", "palabra", "cumplo", "contrato"}:
        return "oath-like cinematic scene with a strong figure under dramatic light, no paper, no written words"
    if tokens & {"corro", "ruta", "calle", "camino", "cima"}:
        return "wide endurance landscape with directional movement; no repetitive close-up runner shots"
    if tokens & {"dinero", "exito", "rico", "riqueza", "oro", "lujo", "estatus", "gano", "meta"}:
        return "elegant opulence: black marble, city lights, tailored silhouette, gold reflections, disciplined success"
    if tokens & {"mujer", "reina", "diosa", "presencia", "mirada"}:
        return "powerful feminine presence: confident silhouette, cinematic luxury lighting, elegance and control"
    if tokens & {"respiro", "calma", "silencio", "mente"}:
        return "quiet breath and focus scene, cinematic close-up, negative space, no text"
    return motif_bank[index % len(motif_bank)]


def _build_music_visual_prompt(package, beat, scene, palette):
    video = _video_concept(package)
    director_plan = video.get("directorPlan") if isinstance(video.get("directorPlan"), dict) else package.get("musicVideoDirector")
    director_plan = director_plan if isinstance(director_plan, dict) else {}
    visual_bible = director_plan.get("visualBible") if isinstance(director_plan.get("visualBible"), dict) else {}
    visual_world_plan = director_plan.get("visualWorld") if isinstance(director_plan.get("visualWorld"), dict) else {}
    shot_recipe = beat.get("shotRecipe") if isinstance(beat.get("shotRecipe"), dict) else {}
    recipe_control = shot_recipe.get("controlNet") if isinstance(shot_recipe.get("controlNet"), dict) else {}
    identity = compact_text(video.get("visualIdentity"), 260) or "premium cinematic motivational music-video identity"
    visual_world = compact_text(video.get("visualWorld"), 260) or "symbolic power visualizer: luxury, discipline, ambition, desire, victory, shadow, controlled movement"
    scene_strategy = compact_text(video.get("sceneStrategy"), 280) or "emotional blocks and recurring motifs instead of literal lyric illustration"
    style = compact_text(package.get("style"), 80) or "motivational anthem"
    intention = compact_text(package.get("intention"), 90) or "discipline and identity"
    lyric = compact_text(beat.get("line") or beat.get("lyric"), 180)
    section = compact_text(beat.get("section"), 60)
    scene_prompt = _safe_scene_prompt_for_image(scene.get("visualPrompt"))
    mood = _visual_mood_from_line(lyric)
    story_moment = compact_text(beat.get("storyMoment") or _visual_story_moment(lyric, int(beat.get("index") or 0), section), 320)
    colors = ", ".join(str(c) for c in (video.get("palette") or [])[:4]) or f"deep black, gold, ember red, {palette[0]}"
    allowed_objects = ", ".join(str(item) for item in (visual_bible.get("allowedObjects") or [])[:10])
    banned_objects = ", ".join(str(item) for item in (visual_bible.get("bannedObjects") or [])[:12])
    camera_language = ", ".join(str(item) for item in (visual_bible.get("cameraLanguage") or [])[:6])
    director_world = compact_text(visual_world_plan.get("label"), 80)

    return compact_text(
        (
            "PROMPT CONTRACT: generate ONE clean, text-free, 16:9 cinematic visualizer still for a music video. "
            f"HARD EXCLUSIONS: {TEXT_FREE_NEGATIVE_PROMPT} No extra limbs, distorted hands, bad anatomy, malformed faces. "
            "Visualizer mode: symbolic, aspirational, powerful, premium; do not illustrate the lyric literally word by word. "
            "The exact song title, lyrics, and captions are NOT part of the image; backend overlays text only on thumbnail/cover. "
            "LOCKED SHOT RECIPE: obey this recipe above all other visual ideas. "
            f"Recipe id: {shot_recipe.get('id') or 'none'}. Category: {shot_recipe.get('category') or 'symbolic'}. "
            f"Recipe subject: {shot_recipe.get('subject') or 'single premium symbolic scene'}. "
            f"Human policy: {shot_recipe.get('humanPolicy') or 'avoid detailed anatomy; use silhouette when possible'}. "
            f"Wardrobe: {shot_recipe.get('wardrobe') or 'coherent cinematic wardrobe only'}. "
            f"Action: {shot_recipe.get('action') or 'controlled stillness, physically believable'}. "
            f"Prop rules: {shot_recipe.get('propRules') or 'one prop cluster only, physically grounded, no random objects'}. "
            f"Composition: {shot_recipe.get('composition') or 'clean premium composition with negative space'}. "
            f"Camera: {shot_recipe.get('camera') or 'cinematic camera, realistic perspective'}. "
            f"Physics: {shot_recipe.get('physics') or 'gravity correct, contact shadows, realistic scale, no floating objects'}. "
            f"Control guidance: {recipe_control.get('recommended') or 'none'} because {recipe_control.get('reason') or 'prompt-only lock'}. "
            f"Recipe negative constraints: {', '.join(str(item) for item in (shot_recipe.get('negativeConstraints') or [])[:14])}. "
            "Do not mix conflicting actions and wardrobe. If the subject is running or training, use athletic wear only. "
            "Weights must rest on floor, rack, or bench with visible contact shadows. No object can float or sit between legs. "
            "Flux/Kontext/Krea photoreal editorial quality, premium composition, cinematic lighting, strong symmetry, high emotional clarity. "
            f"Music Director: {DIRECTOR_VERSION}. Director world: {director_world}. "
            f"Section: {section}. Music style: {style}. Core intention: {intention}. "
            f"Visual world: {visual_world}. Scene strategy: {scene_strategy}. "
            f"Emotional cue derived from the lyric: {mood}. Visual identity to keep consistent: {identity}. Palette: {colors}. "
            f"Lyric-derived visual metaphor for this beat, highest priority after shot recipe: {story_moment}. Optional safe base scene direction: {scene_prompt}. "
            f"Allowed visual objects and motifs: {allowed_objects}. Camera language: {camera_language}. "
            f"Banned objects and failure modes: {banned_objects}. "
            "Prefer premium power motifs: confident silhouettes, luxury architecture, black marble, city lights, steel dumbbells or barbells, wet roads, sunrise rooftops, gold reflections, controlled movement. "
            "Use elegant status symbols sparingly; no cash rain, no tacky flexing, no random props. "
            "Vary subject, camera distance, setting, and action from beat to beat. "
            "Avoid generic waveform backgrounds, empty graphic templates, random neon circles, stock-photo smiles, repetitive runner shots, and literal household objects."
        ),
        2200,
    )


def _timed_segment_for_window(segments, start, end):
    if not segments:
        return 0, {}, 0.0, 0.0
    best_index = 0
    best_score = -1.0
    best_overlap = 0.0
    best_distance = 0.0
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
            best_overlap = overlap
            best_distance = distance
    return best_index, segments[best_index], best_overlap, best_distance


def _build_visual_beats(package, duration, interval_seconds, max_beats, timed_segments=None, show_lyric_overlay=False, show_fallback_lyric_overlay=False):
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
    director_plan = (_video_concept(package).get("directorPlan") if isinstance(_video_concept(package), dict) else {}) or package.get("musicVideoDirector")
    director_plan = director_plan if isinstance(director_plan, dict) else {}
    fallback_quotes = _fallback_quote_pack(package)
    instrumental_gap_seconds = _music_instrumental_gap_seconds()
    beats = []
    for index in range(beat_count):
        start = index * actual_interval
        end = duration if index == beat_count - 1 else min(duration, (index + 1) * actual_interval)
        is_instrumental_gap = False
        if timed_segments:
            segment_index, segment, overlap, distance = _timed_segment_for_window(timed_segments, start, end)
            is_instrumental_gap = overlap < 0.18 and distance >= instrumental_gap_seconds
            if is_instrumental_gap:
                unit = {"section": "Instrumental", "line": _instrumental_visual_line(package, index)}
            else:
                unit = {"section": segment.get("section"), "line": segment.get("line") or segment.get("text")}
            previous_segment = timed_segments[max(0, segment_index - 1)] if timed_segments else {}
            next_segment = timed_segments[min(len(timed_segments) - 1, segment_index + 1)] if timed_segments else {}
            previous_unit = {"line": previous_segment.get("line") or previous_segment.get("text")}
            next_unit = {"line": next_segment.get("line") or next_segment.get("text")}
            alignment_mode = "instrumental_gap" if is_instrumental_gap else (segment.get("alignmentMode") or "timed")
            alignment_score = None if is_instrumental_gap else segment.get("alignmentScore")
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
            "index": index,
            "previousLine": previous_unit.get("line") if isinstance(previous_unit, dict) else "",
            "nextLine": next_unit.get("line") if isinstance(next_unit, dict) else "",
        }
        shot_recipe = build_beat_shot_recipe(unit.get("section"), unit.get("line"), index, director_plan)
        prompt_context["shotRecipe"] = shot_recipe
        lyric_moment = lyric_visual_metaphor(unit.get("section"), unit.get("line"), index, director_plan)
        story_moment = (
            compact_text(lyric_moment, 360)
            or compact_text(shot_recipe.get("lyricMetaphor"), 360)
            or _visual_story_moment(unit.get("line"), index, unit.get("section"))
            or compact_text(shot_recipe.get("summary"), 360)
        )
        prompt_context["storyMoment"] = story_moment
        prompt = _build_music_visual_prompt(package, prompt_context, scene, palette)
        prompt_quality = prompt_gate_for_recipe(prompt, shot_recipe)
        beats.append(
            {
                "scene_number": index + 1,
                "section": compact_text(unit.get("section"), 60),
                "lyric": compact_text(unit.get("line"), 180),
                "subtitle": compact_text(unit.get("line"), 150),
                "overlay": text_overlay,
                "storyMoment": story_moment,
                "shotRecipe": shot_recipe,
                "fallbackQuote": _fallback_quote_for_index(fallback_quotes, index),
                "showLyricOverlay": bool(show_lyric_overlay),
                "showFallbackLyricOverlay": bool(show_fallback_lyric_overlay and not is_instrumental_gap and unit.get("line")),
                "prompt": prompt,
                "promptGate": prompt_quality,
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": max(0.5, end - start),
                "sourceScene": scene.get("section"),
                "alignmentMode": alignment_mode,
                "alignmentScore": alignment_score,
                "isInstrumentalGap": bool(is_instrumental_gap),
            }
        )
    return beats, actual_interval


def _comfy_music_enabled():
    default = bool(os.getenv("COMFYUI_API_KEY"))
    return _env_bool("CONTENT_FACTORY_MUSIC_COMFY_ENABLED", default=default) and bool(os.getenv("COMFYUI_API_KEY"))


def _music_image_workflow_spec(_select_image_workflow):
    workflow = _select_image_workflow("narrativa")
    workflow["label"] = os.getenv("CONTENT_FACTORY_MUSIC_COMFY_LABEL", "FLUX/Krea Power Music Premium")
    workflow["width"] = _env_int("CONTENT_FACTORY_MUSIC_COMFY_WIDTH", int(workflow.get("width") or VIDEO_SIZE[0]))
    workflow["height"] = _env_int("CONTENT_FACTORY_MUSIC_COMFY_HEIGHT", int(workflow.get("height") or VIDEO_SIZE[1]))
    custom_workflow = os.getenv("CONTENT_FACTORY_MUSIC_COMFY_WORKFLOW_PATH", "").strip()
    if custom_workflow:
        path = Path(custom_workflow)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / custom_workflow
        workflow["workflow"] = path
        workflow["label"] = os.getenv("CONTENT_FACTORY_MUSIC_COMFY_LABEL", f"Power Music custom workflow: {path.name}")
    for env_name, key in [
        ("CONTENT_FACTORY_MUSIC_COMFY_PROMPT_NODE", "prompt_node"),
        ("CONTENT_FACTORY_MUSIC_COMFY_PROMPT_INPUT", "prompt_input"),
        ("CONTENT_FACTORY_MUSIC_COMFY_SEED_NODE", "seed_node"),
        ("CONTENT_FACTORY_MUSIC_COMFY_SEED_INPUT", "seed_input"),
        ("CONTENT_FACTORY_MUSIC_COMFY_SIZE_NODE", "size_node"),
        ("CONTENT_FACTORY_MUSIC_COMFY_SAVE_NODE", "save_node"),
        ("CONTENT_FACTORY_MUSIC_COMFY_CONTROL_IMAGE_NODE", "control_image_node"),
        ("CONTENT_FACTORY_MUSIC_COMFY_CONTROL_IMAGE_INPUT", "control_image_input"),
    ]:
        value = os.getenv(env_name, "").strip()
        if value:
            workflow[key] = value
    return workflow


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
        "workflow": "",
        "workflowLabel": "",
        "missing": [],
        "invalid": [],
        "error": "",
    }
    if not _comfy_music_enabled():
        stats["error"] = "COMFYUI_API_KEY not configured or CONTENT_FACTORY_MUSIC_COMFY_ENABLED=false"
        return stats

    max_images = _env_int("CONTENT_FACTORY_MUSIC_MAX_COMFY_IMAGES", DEFAULT_MAX_COMFY_IMAGES)
    comfy_scenes = [
        {
            "scene_number": beat["scene_number"],
            "prompt": beat["prompt"],
            "shotRecipe": beat.get("shotRecipe") or {},
        }
        for beat in beats[:max_images]
    ]
    if not comfy_scenes:
        return stats

    stats["enabled"] = True
    stats["requested"] = len(comfy_scenes)
    try:
        from scripts.factory import generate_comfy_images, _select_image_workflow

        workflow = _music_image_workflow_spec(_select_image_workflow)
        stats["workflow"] = str(workflow.get("workflow") or "")
        stats["workflowLabel"] = workflow.get("label") or ""
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


def _regenerate_comfy_beat_image(beat, comfy_dir):
    stats = {
        "attempted": False,
        "success": False,
        "error": "",
        "result": {},
    }
    if not _comfy_music_enabled():
        stats["error"] = "comfy_disabled"
        return stats
    try:
        scene_num = int(beat.get("scene_number") or 0)
    except Exception:
        scene_num = 0
    if scene_num <= 0:
        stats["error"] = "invalid_scene_number"
        return stats
    comfy_dir = Path(comfy_dir)
    comfy_dir.mkdir(parents=True, exist_ok=True)
    comfy_path = comfy_dir / f"scene_{scene_num:04d}.png"
    if comfy_path.exists():
        try:
            comfy_path.unlink()
        except Exception:
            pass
    try:
        from scripts.factory import generate_comfy_images, _select_image_workflow

        workflow = _music_image_workflow_spec(_select_image_workflow)
        stats["attempted"] = True
        result = generate_comfy_images(
            [
                {
                    "scene_number": scene_num,
                    "prompt": beat.get("prompt") or "",
                    "shotRecipe": beat.get("shotRecipe") or {},
                }
            ],
            comfy_dir,
            workflow,
            pipeline_format="narrativa",
        )
        stats["result"] = result if isinstance(result, dict) else {}
        stats["success"] = comfy_path.exists() and comfy_path.stat().st_size > 5000
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

    package = enrich_package_with_director_plan(package if isinstance(package, dict) else {})
    title = compact_text(package.get("title"), 100) or "Power Music"
    subtitle = compact_text(package.get("subtitle") or package.get("mainHook"), 160)
    palette = _palette(package)
    duration = probe_audio_duration(audio_path)
    requested_interval = _env_float("CONTENT_FACTORY_MUSIC_VISUAL_INTERVAL_SECONDS", DEFAULT_VISUAL_INTERVAL_SECONDS)
    max_visual_beats = _env_int("CONTENT_FACTORY_MUSIC_MAX_VISUAL_BEATS", DEFAULT_MAX_VISUAL_BEATS)
    subtitle_segments, subtitle_diagnostics = _build_whisper_subtitle_segments(package, audio_path, duration)
    subtitle_publishable = bool(subtitle_segments) and bool(subtitle_diagnostics.get("publishable"))
    subtitle_mode = subtitle_diagnostics.get("mode") or ("off_no_reliable_timestamps" if not subtitle_segments else "alignment_low_confidence")
    show_lyric_overlay = _env_bool(
        "CONTENT_FACTORY_MUSIC_LYRIC_OVERLAY_ENABLED",
        default=False,
    ) and subtitle_publishable
    show_fallback_lyric_overlay = _music_fallback_lyrics_enabled() and subtitle_publishable
    beats, visual_interval = _build_visual_beats(
        package,
        duration,
        requested_interval,
        max_visual_beats,
        timed_segments=subtitle_segments,
        show_lyric_overlay=show_lyric_overlay,
        show_fallback_lyric_overlay=show_fallback_lyric_overlay,
    )

    cover_path = output_dir / "cover.jpg"
    thumbnail_path = output_dir / "thumbnail.jpg"
    metadata_path = output_dir / "metadata.json"
    lyrics_path = output_dir / "lyrics.txt"
    suno_path = output_dir / "suno_prompt.txt"
    subtitles_path = output_dir / "subtitles.srt"
    final_path = output_dir / "FINAL_MUSIC.mp4"

    cover = _draw_frame(COVER_SIZE, palette, title, subtitle, package.get("mainHook") or title, package.get("coverPrompt"), 11, square=True)
    cover.save(cover_path, quality=94)
    thumbnail_engine = _build_music_thumbnail(package, palette, title, subtitle, thumbnail_path)

    comfy_dir = output_dir / "comfy"
    comfy_stats = _generate_comfy_beat_images(beats, comfy_dir)
    segment_paths = []
    generated_frames = 0
    fallback_frames = 0
    thumbnail_fallback_frames = 0
    local_fallback_frames = 0
    fallback_lyric_overlay_frames = 0
    vision_qa_results = []
    qa_regenerated_frames = 0
    qa_replaced_frames = 0
    vision_qa_max_frames = _music_vision_qa_max_frames() if _music_vision_qa_enabled() else 0
    for index, beat in enumerate(beats, start=1):
        image_path = assets_dir / f"beat_{index:03d}.jpg"
        segment_path = segments_dir / f"segment_{index:03d}.mp4"
        comfy_path = comfy_dir / f"scene_{index:04d}.png"
        frame_source = "comfy"
        if comfy_path.exists() and comfy_path.stat().st_size > 5000 and _compose_generated_frame(comfy_path, image_path, palette, beat):
            generated_frames += 1
        else:
            frame_source = _write_music_fallback_frame(thumbnail_path, image_path, palette, title, beat, 100 + index, thumbnail_engine=thumbnail_engine)
            fallback_frames += 1
            if _beat_uses_fallback_lyric_overlay(beat):
                fallback_lyric_overlay_frames += 1
            if frame_source.startswith("thumbnail"):
                thumbnail_fallback_frames += 1
            else:
                local_fallback_frames += 1

        if vision_qa_max_frames and len(vision_qa_results) < vision_qa_max_frames:
            qa_result = _evaluate_music_frame_with_openai_vision(image_path, beat)
            qa_result["index"] = index
            qa_result["source"] = frame_source
            if _vision_qa_failed(qa_result):
                repair_attempts = []
                qa_result["repairAttempts"] = repair_attempts
                for attempt in range(1, _music_vision_qa_regen_attempts() + 1):
                    if frame_source != "comfy":
                        break
                    original_prompt = beat.get("prompt") or ""
                    beat["prompt"] = _qa_repair_prompt(original_prompt, qa_result, beat, attempt)
                    beat["promptGate"] = prompt_gate_for_recipe(beat["prompt"], beat.get("shotRecipe") or {})
                    repair_stats = _regenerate_comfy_beat_image(beat, comfy_dir)
                    repair_attempts.append(repair_stats)
                    if repair_stats.get("success") and _compose_generated_frame(comfy_path, image_path, palette, beat):
                        qa_regenerated_frames += 1
                        repaired_qa = _evaluate_music_frame_with_openai_vision(image_path, beat)
                        repaired_qa["index"] = index
                        repaired_qa["source"] = "comfy_repaired"
                        repaired_qa["repairAttempts"] = repair_attempts
                        repaired_qa["repairedFrom"] = qa_result
                        qa_result = repaired_qa
                        if not _vision_qa_failed(qa_result):
                            break
                    else:
                        beat["prompt"] = original_prompt
                qa_result["repairAttempts"] = repair_attempts
                if _vision_qa_failed(qa_result):
                    replacement_source = _write_music_fallback_frame(
                        thumbnail_path,
                        image_path,
                        palette,
                        title,
                        beat,
                        800 + index,
                        thumbnail_engine=thumbnail_engine,
                    )
                    qa_replaced_frames += 1
                    if frame_source not in {"local_fallback", "thumbnail_raw", "thumbnail_cropped"}:
                        fallback_frames += 1
                        if _beat_uses_fallback_lyric_overlay(beat):
                            fallback_lyric_overlay_frames += 1
                        if replacement_source.startswith("thumbnail"):
                            thumbnail_fallback_frames += 1
                        else:
                            local_fallback_frames += 1
                    qa_result["replacement"] = f"{replacement_source}_after_vision_qa"
            vision_qa_results.append(qa_result)

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
    if subtitle_publishable:
        subtitle_count = _write_subtitle_segments(subtitle_segments, subtitles_path)
    else:
        subtitles_path.write_text("", encoding="utf-8")
        subtitle_count = 0
    music_shorts = _build_power_music_shorts(beats, assets_dir, audio_path, output_dir, palette, title, duration)
    director_plan = package.get("musicVideoDirector")
    if not isinstance(director_plan, dict):
        director_plan = (_video_concept(package).get("directorPlan") if isinstance(_video_concept(package), dict) else {}) or {}
    prompt_gate_summary = {
        "passed": sum(1 for beat in beats if (beat.get("promptGate") or {}).get("passed")),
        "failed": sum(1 for beat in beats if not (beat.get("promptGate") or {}).get("passed")),
        "total": len(beats),
        "sampleFailures": [
            {
                "index": beat.get("scene_number"),
                "hits": (beat.get("promptGate") or {}).get("hits") or [],
                "goodSignals": (beat.get("promptGate") or {}).get("goodSignals"),
                "physicsSignals": (beat.get("promptGate") or {}).get("physicsSignals"),
                "recipeId": (beat.get("promptGate") or {}).get("recipeId"),
                "recipeIssues": (beat.get("promptGate") or {}).get("recipeIssues") or [],
            }
            for beat in beats
            if not (beat.get("promptGate") or {}).get("passed")
        ][:8],
    }
    visual_beat_samples = [
        {
            "index": beat.get("scene_number"),
            "section": beat.get("section"),
            "lyric": compact_text(beat.get("lyric"), 150),
            "start": beat.get("start"),
            "end": beat.get("end"),
            "sourceScene": beat.get("sourceScene"),
            "storyMoment": compact_text(beat.get("storyMoment"), 260),
            "showFallbackLyricOverlay": bool(beat.get("showFallbackLyricOverlay")),
            "shotRecipeId": ((beat.get("shotRecipe") or {}).get("id") if isinstance(beat.get("shotRecipe"), dict) else ""),
            "location": ((beat.get("shotRecipe") or {}).get("location") if isinstance(beat.get("shotRecipe"), dict) else ""),
            "motif": ((beat.get("shotRecipe") or {}).get("motif") if isinstance(beat.get("shotRecipe"), dict) else ""),
            "prompt": compact_text(beat.get("prompt"), 700),
        }
        for beat in beats[:24]
    ]
    vision_qa_summary = {
        "enabled": bool(_music_vision_qa_enabled()),
        "model": _music_vision_qa_model() if _music_vision_qa_enabled() else "",
        "checked": len(vision_qa_results),
        "passed": sum(1 for item in vision_qa_results if item.get("passed") is True),
        "failed": sum(1 for item in vision_qa_results if item.get("passed") is False),
        "minScore": _music_vision_qa_min_score(),
        "softMinScore": _music_vision_qa_soft_min_score(),
        "softAccepted": sum(1 for item in vision_qa_results if item.get("softAccepted")),
        "hardRejected": sum(1 for item in vision_qa_results if item.get("hardRejected")),
        "regenAttempts": _music_vision_qa_regen_attempts(),
        "regeneratedFrames": qa_regenerated_frames,
        "replacedFrames": qa_replaced_frames,
        "results": vision_qa_results,
    }
    metadata = {
        "trackId": track_id,
        "title": title,
        "durationSeconds": duration,
        "sceneCount": len(beats),
        "visualBeatCount": len(beats),
        "visualIntervalSeconds": round(visual_interval, 3),
        "requestedVisualIntervalSeconds": round(requested_interval, 3),
        "visualProvider": "comfy_flux" if generated_frames else ("thumbnail_fallback" if thumbnail_fallback_frames else "local_fallback"),
        "thumbnailEngine": thumbnail_engine,
        "showLyricOverlay": show_lyric_overlay,
        "comfy": comfy_stats,
        "generatedFrames": generated_frames,
        "fallbackFrames": fallback_frames,
        "thumbnailFallbackFrames": thumbnail_fallback_frames,
        "localFallbackFrames": local_fallback_frames,
        "fallbackLyricOverlayFrames": fallback_lyric_overlay_frames,
        "fallbackFrameMode": _music_fallback_frame_mode(),
        "renderer": "power_music_video_v5_shot_controlled_vision_qa",
        "visualizerMode": "symbolic_premium_text_free_director_v4",
        "directorVersion": DIRECTOR_VERSION,
        "musicVideoDirector": director_plan,
        "songVisualSeed": director_plan.get("songVisualSeed") if isinstance(director_plan, dict) else None,
        "promptGateSummary": prompt_gate_summary,
        "visualBeatSamples": visual_beat_samples,
        "visionQa": vision_qa_summary,
        "subtitleMode": subtitle_mode,
        "subtitleCount": subtitle_count,
        "subtitleDiagnostics": subtitle_diagnostics,
        "transcriptionProvider": subtitle_diagnostics.get("provider") or "",
        "fallbackQuotePack": _fallback_quote_pack(package),
        "instrumentalBeatCount": sum(1 for beat in beats if beat.get("isInstrumentalGap")),
        "musicShorts": [
            {
                key: value
                for key, value in short.items()
                if key != "path"
            }
            for short in music_shorts
        ],
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
                "isInstrumentalGap": beat.get("isInstrumentalGap"),
                "storyMoment": beat.get("storyMoment"),
                "fallbackQuote": beat.get("fallbackQuote"),
                "showLyricOverlay": beat.get("showLyricOverlay"),
                "showFallbackLyricOverlay": beat.get("showFallbackLyricOverlay"),
                "shotRecipe": beat.get("shotRecipe"),
                "promptGate": beat.get("promptGate"),
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
            "subtitles": subtitles_path.name if subtitle_count else "",
            "musicShorts": [short.get("fileName") for short in music_shorts if short.get("path")],
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
        "subtitles": subtitles_path if subtitle_count else None,
        "durationSeconds": duration,
        "sceneCount": len(beats),
        "visualBeatCount": len(beats),
        "visualIntervalSeconds": round(visual_interval, 3),
        "visualProvider": metadata["visualProvider"],
        "generatedFrames": generated_frames,
        "fallbackFrames": fallback_frames,
        "thumbnailFallbackFrames": thumbnail_fallback_frames,
        "localFallbackFrames": local_fallback_frames,
        "fallbackLyricOverlayFrames": metadata["fallbackLyricOverlayFrames"],
        "fallbackFrameMode": metadata["fallbackFrameMode"],
        "comfy": comfy_stats,
        "renderer": metadata["renderer"],
        "directorVersion": metadata["directorVersion"],
        "musicVideoDirector": metadata["musicVideoDirector"],
        "songVisualSeed": metadata["songVisualSeed"],
        "promptGateSummary": metadata["promptGateSummary"],
        "visualBeatSamples": metadata["visualBeatSamples"],
        "visionQa": metadata["visionQa"],
        "subtitleMode": metadata["subtitleMode"],
        "subtitleCount": metadata["subtitleCount"],
        "subtitleDiagnostics": metadata["subtitleDiagnostics"],
        "transcriptionProvider": metadata["transcriptionProvider"],
        "fallbackQuotePack": metadata["fallbackQuotePack"],
        "instrumentalBeatCount": metadata["instrumentalBeatCount"],
        "musicShorts": music_shorts,
        "thumbnailEngine": metadata["thumbnailEngine"],
        "showLyricOverlay": metadata["showLyricOverlay"],
        "visualizerMode": metadata["visualizerMode"],
    }
