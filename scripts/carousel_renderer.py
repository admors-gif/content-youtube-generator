"""Static carousel renderer for Content Factory.

Comfy generates text-free backgrounds. This module overlays the final copy in a
deterministic way so Instagram/TikTok slides never depend on image-model text.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


INSTAGRAM_SIZE = (1080, 1350)
TIKTOK_SIZE = (1080, 1920)
CRIMSON = (224, 83, 61)
DEEP_CRIMSON = (120, 28, 28)
PAPER = (248, 244, 236)
PAPER_DIM = (202, 194, 184)
BLACK = (5, 5, 8)


def _font_path() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/montserrat/Montserrat-BoldItalic.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/georgiaz.ttf",
        "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return None


def _mono_font_path() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    return _font_path()


def _load_font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _mono_font_path() if mono else _font_path()
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return max(0, box[2] - box[0])


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = str(text or "").split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int, mono: bool = False):
    size = start_size
    while size >= min_size:
        font = _load_font(size, mono=mono)
        lines = _wrap_text(draw, text, font, max_width)
        if lines and max(_text_width(draw, line, font) for line in lines) <= max_width:
            return font, lines
        size -= 2
    font = _load_font(min_size, mono=mono)
    return font, _wrap_text(draw, text, font, max_width)


def _cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    src_w, src_h = image.size
    dst_w, dst_h = size
    scale = max(dst_w / max(1, src_w), dst_h / max(1, src_h))
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - dst_w) // 2)
    top = max(0, (resized.height - dst_h) // 2)
    return resized.crop((left, top, left + dst_w, top + dst_h))


def _prepare_background(path: Path, size: tuple[int, int]) -> Image.Image:
    if path.is_file():
        image = Image.open(path)
    else:
        image = Image.new("RGB", size, BLACK)
    bg = _cover_resize(image, size)
    bg = ImageEnhance.Color(bg).enhance(0.82)
    bg = ImageEnhance.Contrast(bg).enhance(1.12)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=0.35))
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    px = overlay.load()
    w, h = size
    for y in range(h):
        top_alpha = int(120 * (1 - y / h))
        bottom_alpha = int(190 * (y / h) ** 1.7)
        alpha = max(top_alpha, bottom_alpha, 72)
        for x in range(w):
            edge = abs((x / w) - 0.5) * 2
            vignette = int(70 * edge ** 1.8)
            px[x, y] = (0, 0, 0, min(225, alpha + vignette))
    return Image.alpha_composite(bg.convert("RGBA"), overlay)


def _line_height(font: ImageFont.ImageFont) -> int:
    box = font.getbbox("Ag")
    return max(1, box[3] - box[1])


def _draw_lines(draw: ImageDraw.ImageDraw, xy: tuple[int, int], lines: list[str], font, fill, spacing: int):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += _line_height(font) + spacing
    return y


def _render_slide(
    background_path: Path,
    slide: dict[str, Any],
    output_path: Path,
    size: tuple[int, int],
    *,
    variant: str,
) -> dict[str, Any]:
    canvas = _prepare_background(background_path, size)
    draw = ImageDraw.Draw(canvas)
    w, h = size
    margin_x = 84 if variant == "instagram" else 78
    max_width = w - margin_x * 2
    index = int(slide.get("index") or 1)
    role = str(slide.get("role") or "slide").upper()
    headline = str(slide.get("headline") or "").strip()
    body = str(slide.get("body") or "").strip()
    layout = str(slide.get("layout") or "").lower()

    eyebrow_font = _load_font(25, mono=True)
    footer_font = _load_font(24, mono=True)
    headline_start = 86 if variant == "instagram" else 90
    body_start = 42 if variant == "instagram" else 46
    if layout == "cover":
        headline_start += 12
    if layout == "quote":
        headline_start += 8

    headline_font, headline_lines = _fit_font(draw, headline, max_width, headline_start, 44)
    body_font, body_lines = _fit_font(draw, body, max_width, body_start, 26)
    block_h = (
        len(headline_lines) * (_line_height(headline_font) + 12)
        + 18
        + len(body_lines) * (_line_height(body_font) + 8)
    )
    if layout == "cover":
        y = int(h * 0.38) - block_h // 2
    elif layout == "quote":
        y = int(h * 0.42) - block_h // 2
    else:
        y = int(h * 0.34)
    y = max(125, min(y, h - block_h - 170))

    draw.text((margin_x, 78), f"{index:02d} / 08   {role}", font=eyebrow_font, fill=CRIMSON)
    y = _draw_lines(draw, (margin_x, y), headline_lines, headline_font, PAPER, 12)
    y += 18
    _draw_lines(draw, (margin_x, y), body_lines, body_font, PAPER_DIM, 8)

    rule_y = h - 112
    draw.line((margin_x, rule_y, margin_x + 178, rule_y), fill=CRIMSON, width=4)
    draw.text((margin_x, rule_y + 24), "ESTO NO ES AMOR", font=footer_font, fill=PAPER_DIM)
    draw.rectangle((w - margin_x - 28, rule_y + 23, w - margin_x, rule_y + 51), fill=CRIMSON)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", optimize=True)
    return {
        "file": output_path.name,
        "width": w,
        "height": h,
        "headlineLines": len(headline_lines),
        "bodyLines": len(body_lines),
    }


def render_carousel_package(
    project_dir: Path,
    carousel: dict[str, Any],
    scenes: list[dict[str, Any]],
    *,
    public_base_url: str = "",
    folder: str = "",
) -> dict[str, Any]:
    project_dir = Path(project_dir)
    images_dir = project_dir / "images"
    carousel_dir = project_dir / "carousel"
    bg_dir = carousel_dir / "backgrounds"
    instagram_dir = carousel_dir / "instagram"
    tiktok_dir = carousel_dir / "tiktok"
    for directory in (bg_dir, instagram_dir, tiktok_dir):
        directory.mkdir(parents=True, exist_ok=True)

    slides = carousel.get("slides") if isinstance(carousel.get("slides"), list) else []
    if not slides:
        raise ValueError("carousel slides missing")

    rendered_slides = []
    updated_scenes = []
    for slide in slides:
        index = int(slide.get("index") or len(rendered_slides) + 1)
        source = images_dir / f"scene_{index:04d}.png"
        bg_copy = bg_dir / f"slide_{index:02d}_background.png"
        if source.is_file() and not bg_copy.is_file():
            shutil.copy2(source, bg_copy)
        instagram_path = instagram_dir / f"slide_{index:02d}.png"
        tiktok_path = tiktok_dir / f"slide_{index:02d}.png"
        instagram_meta = _render_slide(bg_copy if bg_copy.is_file() else source, slide, instagram_path, INSTAGRAM_SIZE, variant="instagram")
        tiktok_meta = _render_slide(bg_copy if bg_copy.is_file() else source, slide, tiktok_path, TIKTOK_SIZE, variant="tiktok")
        # Keep existing UI previews working through /images/{folder}/scene_0001.png.
        preview_path = images_dir / f"scene_{index:04d}.png"
        shutil.copy2(instagram_path, preview_path)
        public_url = f"{public_base_url.rstrip('/')}/images/{folder}/scene_{index:04d}.png" if public_base_url and folder else ""
        rendered = {
            "index": index,
            "role": slide.get("role"),
            "headline": slide.get("headline"),
            "body": slide.get("body"),
            "instagramFile": f"carousel/instagram/{instagram_path.name}",
            "tiktokFile": f"carousel/tiktok/{tiktok_path.name}",
            "backgroundFile": f"carousel/backgrounds/{bg_copy.name}" if bg_copy.is_file() else "",
            "imageUrl": public_url,
            "instagram": instagram_meta,
            "tiktok": tiktok_meta,
        }
        rendered_slides.append(rendered)
        source_scene = next((s for s in scenes if int(s.get("scene_number", s.get("sceneNumber", 0)) or 0) == index), {})
        updated = dict(source_scene)
        updated["imageUrl"] = public_url
        updated["status"] = "ready"
        updated["carousel_slide"] = {
            "index": index,
            "role": slide.get("role"),
            "headline": slide.get("headline"),
            "body": slide.get("body"),
            "layout": slide.get("layout"),
            "altText": slide.get("altText"),
        }
        updated_scenes.append(updated)

    caption = str(carousel.get("caption") or "").strip()
    hashtags = carousel.get("hashtags") if isinstance(carousel.get("hashtags"), list) else []
    cta = carousel.get("cta") if isinstance(carousel.get("cta"), dict) else {}
    alt_lines = [str(slide.get("altText") or "") for slide in slides]

    (carousel_dir / "caption.txt").write_text(caption, encoding="utf-8")
    (carousel_dir / "hashtags.txt").write_text(" ".join(str(tag) for tag in hashtags), encoding="utf-8")
    (carousel_dir / "cta.txt").write_text(str(cta.get("text") or ""), encoding="utf-8")
    (carousel_dir / "alt_text.txt").write_text("\n".join(alt_lines), encoding="utf-8")
    metadata = {
        "format": "instagram_carousel",
        "primarySize": "1080x1350",
        "secondarySize": "1080x1920",
        "slides": rendered_slides,
        "caption": caption,
        "hashtags": hashtags,
        "cta": cta,
        "qualityScores": carousel.get("quality_scores") or carousel.get("qualityScores") or {},
    }
    (carousel_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "status": "ready",
        "slideCount": len(rendered_slides),
        "slides": rendered_slides,
        "caption": caption,
        "hashtags": hashtags,
        "cta": cta,
        "qualityScores": metadata["qualityScores"],
        "delivery": {
            "folder": "carousel",
            "instagram": "carousel/instagram",
            "tiktok": "carousel/tiktok",
            "metadataFile": "carousel/metadata.json",
        },
        "updatedScenes": updated_scenes,
    }
