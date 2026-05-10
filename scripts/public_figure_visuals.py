"""
Public figure visual support for biography-style videos.

This module stays deliberately conservative: it can improve generated prompts
with an editorial visual dossier and it only uses external still images when
their Wikimedia metadata contains a reusable license.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover - production dependency, defensive import.
    Image = None
    ImageOps = None


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIMEDIA_USER_AGENT = os.getenv(
    "CONTENT_FACTORY_WIKIMEDIA_USER_AGENT",
    "ContentFactory/1.0 (https://content-youtube-generator.vercel.app)",
)

ALLOWED_LICENSE_FAMILIES = ("public_domain", "cc0", "cc_by", "cc_by_sa")
BLOCKED_LICENSE_MARKERS = (
    "noncommercial",
    "non commercial",
    "non-commercial",
    "cc-by-nc",
    "cc by-nc",
    "cc by nc",
    "noderivatives",
    "no derivatives",
    "cc-by-nd",
    "cc by-nd",
    "cc by nd",
    "fair use",
    "non-free",
    "non free",
    "unfree",
    "all rights reserved",
    "copyrighted",
    "unknown",
)

BIOGRAPHY_AGENT_FILE = "agent_biografias.md"
PUBLIC_FIGURE_PREFIXES = (
    "la vida secreta de",
    "la vida tragica de",
    "la tragica vida de",
    "la verdadera historia de",
    "la vida de",
    "vida de",
    "biografia de",
    "biografía de",
    "historia de",
    "quien fue",
    "quién fue",
    "el ascenso y caida de",
    "el ascenso y caída de",
    "la caida de",
    "la caída de",
)

HUMAN_DESCRIPTION_HINTS = (
    "actor",
    "actress",
    "artist",
    "author",
    "composer",
    "dancer",
    "director",
    "human",
    "musician",
    "performer",
    "person",
    "philosopher",
    "politician",
    "singer",
    "writer",
    "artista",
    "autor",
    "cantante",
    "compositor",
    "compositora",
    "escritor",
    "escritora",
    "filosofo",
    "filósofo",
    "humano",
    "musico",
    "músico",
    "persona",
    "politico",
    "político",
)

CURATED_PUBLIC_FIGURE_CUES = {
    "michael jackson": {
        "aliases": ["Michael Joseph Jackson", "MJ", "King of Pop"],
        "eras": [
            {
                "label": "Jackson 5 and Motown childhood era",
                "years": "late 1960s to mid 1970s",
                "visualCues": [
                    "young Black American pop performer",
                    "bright stage costumes",
                    "Afro hairstyle typical of the era",
                    "family band television-stage atmosphere",
                ],
            },
            {
                "label": "Thriller and global breakthrough era",
                "years": "early to mid 1980s",
                "visualCues": [
                    "slim adult pop star silhouette",
                    "curly shoulder-length dark hair",
                    "red or black military-inspired jacket",
                    "white socks with black loafers",
                    "high-energy concert lighting",
                ],
            },
            {
                "label": "Bad, Dangerous and later stadium era",
                "years": "late 1980s to 1990s",
                "visualCues": [
                    "black fedora and single white glove as performance symbols",
                    "sharp military jackets and metallic details",
                    "moonwalk-era stage posture",
                    "dramatic stadium spotlight and smoke",
                ],
            },
        ],
        "signatureWardrobe": [
            "black fedora",
            "single white glove",
            "military-style stage jackets",
            "black loafers with white socks",
            "sequined performance details",
        ],
        "signatureSettings": [
            "concert stage under a hard white spotlight",
            "1980s music video set",
            "rehearsal studio with mirrors",
            "award-show backstage corridor",
            "archival press photography environment",
        ],
        "avoid": [
            "generic adult man",
            "random business portrait",
            "unrelated facial structure",
            "ordinary office clothing",
            "anonymous modern influencer look",
        ],
    }
}


def env_flag_enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", "disabled"}


def coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def public_figure_visuals_enabled() -> bool:
    return env_flag_enabled("CONTENT_FACTORY_PUBLIC_FIGURE_VISUALS_ENABLED", True)


def archive_images_enabled() -> bool:
    return env_flag_enabled("CONTENT_FACTORY_PUBLIC_FIGURE_ARCHIVE_IMAGES_ENABLED", True)


def compact_text(value: Any, max_len: int = 500) -> str:
    text = strip_html(str(value or ""))
    text = " ".join(text.split())
    return text[:max_len].strip()


def strip_html(value: str) -> str:
    if not value:
        return ""
    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split()).strip()


def normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return " ".join(text.split())


def _clean_subject(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .,:;!¡?¿\"'()[]{}")
    return text[:120].strip()


def extract_subject_from_topic(topic: str, agent_file: str = "") -> str:
    raw = _clean_subject(topic)
    if not raw:
        return ""

    lowered = normalize_key(raw)
    for prefix in PUBLIC_FIGURE_PREFIXES:
        normalized_prefix = normalize_key(prefix)
        if lowered.startswith(normalized_prefix + " "):
            words_to_remove = len(normalized_prefix.split())
            original_words = raw.split()
            return _clean_subject(" ".join(original_words[words_to_remove:]))

    if ":" in raw:
        before, after = [part.strip() for part in raw.split(":", 1)]
        if normalize_key(before) in {
            "la mente de un dictador",
            "la vida de",
            "biografia",
            "biografia de",
            "historia de",
        }:
            return _clean_subject(after)
        if len(after.split()) <= 5 and any(ch.isupper() for ch in after):
            return _clean_subject(after)

    if Path(str(agent_file or "")).name == BIOGRAPHY_AGENT_FILE:
        return raw
    return ""


def should_prepare_public_figure_visuals(topic: str, agent_file: str, generation_options: dict | None = None) -> bool:
    if not public_figure_visuals_enabled():
        return False
    options = generation_options or {}
    explicit = options.get("publicFigureVisualsEnabled", options.get("public_figure_visuals_enabled"))
    if explicit is not None:
        return coerce_bool(explicit, default=True)
    if Path(str(agent_file or "")).name == BIOGRAPHY_AGENT_FILE:
        return True
    return bool(extract_subject_from_topic(topic, agent_file))


def license_family(license_name: str, usage_terms: str = "") -> str | None:
    combined = normalize_key(f"{license_name} {usage_terms}")
    if not combined:
        return None
    if any(marker in combined for marker in BLOCKED_LICENSE_MARKERS):
        return None
    if "public domain" in combined or combined in {"pd", "pdm"} or combined.startswith("pd "):
        return "public_domain"
    if "cc0" in combined or "creative commons zero" in combined:
        return "cc0"
    if "cc by sa" in combined or "cc by-sa" in combined or "creative commons attribution share alike" in combined:
        return "cc_by_sa"
    if "cc by" in combined or "cc-by" in combined or "creative commons attribution" in combined:
        return "cc_by"
    return None


def is_allowed_license(license_name: str, usage_terms: str = "") -> bool:
    return license_family(license_name, usage_terms) in ALLOWED_LICENSE_FAMILIES


def _metadata_value(extmetadata: dict, key: str) -> str:
    raw = (extmetadata or {}).get(key) or {}
    if isinstance(raw, dict):
        raw = raw.get("value")
    return compact_text(raw, 700)


def _reference_id(title: str, url: str) -> str:
    return hashlib.sha1(f"{title}|{url}".encode("utf-8")).hexdigest()[:16]


def reference_from_commons_page(page: dict) -> dict | None:
    info = ((page or {}).get("imageinfo") or [{}])[0] or {}
    ext = info.get("extmetadata") or {}
    title = compact_text((page or {}).get("title") or info.get("canonicaltitle") or "", 180)
    file_url = info.get("url") or ""
    thumb_url = info.get("thumburl") or file_url
    mime = str(info.get("mime") or "").lower()
    if not title or not file_url:
        return None
    if not mime.startswith("image/") or any(kind in mime for kind in ("svg", "gif", "tiff")):
        return None

    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    if width and height and (width < 320 or height < 320):
        return None

    license_name = _metadata_value(ext, "LicenseShortName") or _metadata_value(ext, "UsageTerms")
    usage_terms = _metadata_value(ext, "UsageTerms")
    family = license_family(license_name, usage_terms)
    if family not in ALLOWED_LICENSE_FAMILIES:
        return None

    author = (
        _metadata_value(ext, "Artist")
        or _metadata_value(ext, "Credit")
        or _metadata_value(ext, "ObjectName")
        or "Unknown author"
    )
    description = _metadata_value(ext, "ImageDescription") or _metadata_value(ext, "ObjectName") or title
    license_url = _metadata_value(ext, "LicenseUrl")
    description_url = info.get("descriptionurl") or ""
    attribution = f"{author} / Wikimedia Commons / {license_name or usage_terms}".strip()

    return {
        "id": _reference_id(title, file_url),
        "title": title,
        "description": compact_text(description, 500),
        "author": compact_text(author, 240),
        "license": compact_text(license_name or usage_terms, 120),
        "licenseFamily": family,
        "licenseUrl": license_url,
        "source": "Wikimedia Commons",
        "sourcePage": description_url,
        "imageUrl": file_url,
        "downloadUrl": thumb_url or file_url,
        "mime": mime,
        "width": width,
        "height": height,
        "sha1": info.get("sha1") or "",
        "attribution": attribution,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
    }


def _mediawiki_get(url: str, params: dict, timeout: float = 10.0) -> dict:
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def search_wikidata_entity(subject: str, language: str = "es", timeout: float = 8.0) -> dict:
    if not subject:
        return {}
    for lang in (language, "en"):
        try:
            data = _mediawiki_get(
                WIKIDATA_API_URL,
                {
                    "action": "wbsearchentities",
                    "format": "json",
                    "language": lang,
                    "uselang": lang,
                    "type": "item",
                    "limit": 3,
                    "search": subject,
                },
                timeout=timeout,
            )
            matches = data.get("search") or []
            if matches:
                top = matches[0]
                description = compact_text(top.get("description"), 240)
                return {
                    "id": top.get("id") or "",
                    "label": top.get("label") or subject,
                    "description": description,
                    "url": top.get("concepturi") or "",
                    "language": lang,
                }
        except Exception:
            continue
    return {}


def search_commons_images(subject: str, limit: int = 8, timeout: float = 12.0) -> list[dict]:
    if not subject or not archive_images_enabled():
        return []
    try:
        data = _mediawiki_get(
            COMMONS_API_URL,
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "generator": "search",
                "gsrnamespace": "6",
                "gsrsearch": subject,
                "gsrlimit": min(max(limit * 3, 10), 30),
                "prop": "imageinfo",
                "iiprop": "url|mime|size|sha1|extmetadata",
                "iiurlwidth": "1920",
                "iiextmetadatalanguage": "en",
                "iiextmetadatafilter": "LicenseShortName|UsageTerms|LicenseUrl|Artist|Credit|ObjectName|ImageDescription|AttributionRequired",
            },
            timeout=timeout,
        )
    except Exception:
        return []

    refs = []
    seen = set()
    for page in ((data.get("query") or {}).get("pages") or []):
        ref = reference_from_commons_page(page)
        if not ref:
            continue
        searchable = normalize_key(" ".join([ref.get("title", ""), ref.get("description", "")]))
        if normalize_key(subject).split()[0:1] and normalize_key(subject).split()[0] not in searchable:
            continue
        if ref["id"] in seen:
            continue
        seen.add(ref["id"])
        refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def _curated_cues_for(subject: str) -> dict:
    return CURATED_PUBLIC_FIGURE_CUES.get(normalize_key(subject), {})


def _derive_reference_cues(references: list[dict]) -> list[str]:
    cues = []
    for ref in references[:6]:
        text = compact_text(ref.get("description") or ref.get("title"), 160)
        if text and text not in cues:
            cues.append(text)
    return cues


def build_subject_visual_profile(
    topic: str,
    agent_file: str = "",
    references: list[dict] | None = None,
    entity: dict | None = None,
) -> dict:
    subject = extract_subject_from_topic(topic, agent_file)
    references = references or []
    entity = entity or {}
    curated = _curated_cues_for(subject)
    aliases = [subject]
    aliases.extend(curated.get("aliases") or [])
    entity_label = entity.get("label")
    if entity_label and entity_label not in aliases:
        aliases.append(entity_label)

    description = compact_text(entity.get("description"), 220)
    public_confidence = 0.72 if subject else 0.0
    if Path(str(agent_file or "")).name == BIOGRAPHY_AGENT_FILE:
        public_confidence = max(public_confidence, 0.82)
    if entity:
        public_confidence = max(public_confidence, 0.88)
    if description and any(hint in normalize_key(description) for hint in HUMAN_DESCRIPTION_HINTS):
        public_confidence = max(public_confidence, 0.94)

    generic_cues = _derive_reference_cues(references)
    signature_wardrobe = curated.get("signatureWardrobe") or []
    signature_settings = curated.get("signatureSettings") or [
        "archival press setting",
        "public performance or work environment",
        "period-accurate streets, rooms and institutions",
        "documentary portrait lighting",
    ]
    avoid = curated.get("avoid") or [
        "generic adult man or woman",
        "random influencer face",
        "unrelated ethnicity, age or body type",
        "modern office portrait unless historically relevant",
        "fake readable text, logos or watermarks",
    ]

    return {
        "enabled": bool(subject),
        "subject": subject,
        "aliases": [item for item in aliases if item],
        "wikidata": entity,
        "publicFigureConfidence": round(public_confidence, 2),
        "description": description,
        "eras": curated.get("eras") or [],
        "referenceDerivedCues": generic_cues,
        "signatureWardrobe": signature_wardrobe,
        "signatureSettings": signature_settings,
        "avoid": avoid,
        "visualContinuityRule": (
            f"Maintain one coherent editorial depiction of {subject}. Use era-aware age, wardrobe, "
            "hair, posture, public settings and documentary symbols. If exact likeness is uncertain, "
            "prefer silhouettes, back views, archival rooms, objects and symbolic scenes instead of "
            "inventing a random face."
        ),
        "licensePolicy": {
            "allowed": list(ALLOWED_LICENSE_FAMILIES),
            "blocked": ["NC", "ND", "fair use", "unknown", "all rights reserved"],
            "requiresAttribution": True,
        },
    }


def format_visual_profile_for_prompt(profile: dict | None) -> str:
    if not profile or not profile.get("enabled"):
        return ""
    parts = [
        f"Subject: {profile.get('subject')}",
        f"Aliases: {', '.join(profile.get('aliases') or [])}",
        f"Continuity: {profile.get('visualContinuityRule')}",
    ]
    if profile.get("description"):
        parts.append(f"Public description: {profile['description']}")
    if profile.get("signatureWardrobe"):
        parts.append("Signature wardrobe/symbols: " + "; ".join(profile["signatureWardrobe"][:8]))
    if profile.get("signatureSettings"):
        parts.append("Likely settings: " + "; ".join(profile["signatureSettings"][:8]))
    for era in profile.get("eras") or []:
        cues = "; ".join((era.get("visualCues") or [])[:5])
        parts.append(f"Era - {era.get('label')} ({era.get('years')}): {cues}")
    if profile.get("referenceDerivedCues"):
        parts.append("Reference-derived cues: " + "; ".join(profile["referenceDerivedCues"][:6]))
    if profile.get("avoid"):
        parts.append("Avoid: " + "; ".join(profile["avoid"][:8]))
    parts.append(
        "Legal/editorial note: generated images are illustrative editorial depictions, not real photos."
    )
    return "\n".join(parts)


def prepare_public_figure_visuals(
    topic: str,
    agent_file: str,
    generation_options: dict | None = None,
    max_references: int = 8,
) -> dict:
    if not should_prepare_public_figure_visuals(topic, agent_file, generation_options):
        return {"enabled": False, "detected": False, "reason": "feature_disabled_or_not_public_figure"}

    subject = extract_subject_from_topic(topic, agent_file)
    if not subject:
        return {"enabled": False, "detected": False, "reason": "subject_not_detected"}

    entity = search_wikidata_entity(subject)
    references = search_commons_images(subject, limit=max_references)
    profile = build_subject_visual_profile(topic, agent_file, references=references, entity=entity)
    attributions = [ref["attribution"] for ref in references if ref.get("attribution")]
    warnings = [
        "External images are used only when Wikimedia metadata exposes a reusable license.",
        "AI-generated scenes are illustrative and must not be described as real photographs.",
    ]
    if not references:
        warnings.append("No reusable Wikimedia images were found; generated visuals will use the subject dossier only.")

    return {
        "enabled": True,
        "detected": True,
        "subject": subject,
        "profile": profile,
        "references": references,
        "attributions": attributions,
        "referencesCount": len(references),
        "source": "wikidata+wikimedia_commons",
        "warnings": warnings,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def _scene_number(scene: dict) -> int:
    try:
        return int(scene.get("scene_number") or scene.get("sceneNumber") or 0)
    except Exception:
        return 0


def annotate_scenes_with_public_figure_visuals(
    scenes: list[dict],
    visual_data: dict | None,
    max_archive_images: int = 4,
) -> list[dict]:
    if not scenes or not visual_data or not visual_data.get("detected"):
        return scenes
    profile = visual_data.get("profile") or {}
    subject = profile.get("subject") or visual_data.get("subject") or ""
    context = format_visual_profile_for_prompt(profile)
    for scene in scenes:
        if subject:
            scene["public_figure_subject"] = subject
        if context:
            scene["public_figure_visual_context"] = context[:1800]

    references = visual_data.get("references") or []
    if not references or max_archive_images <= 0:
        return scenes

    count = min(len(references), max_archive_images, len(scenes))
    if count <= 0:
        return scenes
    if count == 1:
        indices = [0]
    else:
        indices = sorted({round(i * (len(scenes) - 1) / (count - 1)) for i in range(count)})
    refs = references[: len(indices)]
    for idx, ref in zip(indices, refs):
        scene = scenes[idx]
        scene["visual_source"] = "licensed_archive"
        scene["visualSource"] = "licensed_archive"
        scene["archive_reference_id"] = ref.get("id")
        scene["archiveReference"] = {
            "id": ref.get("id"),
            "title": ref.get("title"),
            "source": ref.get("source"),
            "sourcePage": ref.get("sourcePage"),
            "imageUrl": ref.get("imageUrl"),
            "downloadUrl": ref.get("downloadUrl"),
            "author": ref.get("author"),
            "license": ref.get("license"),
            "licenseUrl": ref.get("licenseUrl"),
            "attribution": ref.get("attribution"),
        }
    return scenes


def _valid_image_file(path: Path, min_bytes: int = 5000) -> bool:
    return path.exists() and path.stat().st_size >= min_bytes


def download_assigned_reference_images(
    scenes: list[dict],
    images_dir: Path,
    max_width: int = 1920,
    timeout: float = 25.0,
) -> dict:
    stats = {"attempted": 0, "downloaded": 0, "skipped": 0, "failed": 0, "files": []}
    if Image is None or ImageOps is None:
        stats["error"] = "pillow_unavailable"
        return stats
    images_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for scene in scenes:
            ref = scene.get("archiveReference") or {}
            if not ref:
                continue
            num = _scene_number(scene)
            if not num:
                continue
            target = images_dir / f"scene_{num:04d}.png"
            if _valid_image_file(target):
                stats["skipped"] += 1
                continue
            url = ref.get("downloadUrl") or ref.get("imageUrl")
            if not url:
                stats["failed"] += 1
                continue
            stats["attempted"] += 1
            try:
                response = client.get(url)
                response.raise_for_status()
                with Image.open(BytesIO(response.content)) as img:
                    img = ImageOps.exif_transpose(img)
                    if img.mode not in {"RGB", "L"}:
                        img = img.convert("RGB")
                    elif img.mode == "L":
                        img = img.convert("RGB")
                    if max(img.size) > max_width:
                        img.thumbnail((max_width, max_width), Image.Resampling.LANCZOS)
                    img.save(target, "PNG", optimize=True)
                if _valid_image_file(target):
                    scene["visual_source"] = "licensed_archive_ready"
                    scene["visualSource"] = "licensed_archive_ready"
                    scene["archive_image_local_path"] = str(target)
                    scene["archiveImageLocalPath"] = str(target)
                    stats["downloaded"] += 1
                    stats["files"].append({"sceneNumber": num, "path": str(target), "referenceId": ref.get("id")})
                else:
                    target.unlink(missing_ok=True)
                    stats["failed"] += 1
            except Exception:
                target.unlink(missing_ok=True)
                stats["failed"] += 1
    return stats


def legacy_title_slug(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(title or "video_sin_titulo").replace(" ", "_"))
    return slug.strip("_-") or "video_sin_titulo"


def project_output_slug(title: str, project_id: str | None = None) -> str:
    title_slug = legacy_title_slug(title)
    if not project_id:
        return title_slug
    project_slug = legacy_title_slug(project_id)
    compact_title = title_slug[:90].rstrip("_-") or "video_sin_titulo"
    return f"{compact_title}__{project_slug}"


def write_public_figure_visual_outputs(
    project_dir: Path,
    visual_data: dict | None,
    scenes: list[dict] | None = None,
    download_stats: dict | None = None,
) -> None:
    if not visual_data or not visual_data.get("detected"):
        return
    project_dir.mkdir(parents=True, exist_ok=True)
    profile = visual_data.get("profile") or {}
    references = visual_data.get("references") or []
    payload = {
        **visual_data,
        "downloadStats": download_stats or visual_data.get("downloadStats") or {},
        "archiveSceneCount": len([s for s in scenes or [] if (s.get("archiveReference") or {})]),
    }
    (project_dir / "subject_visual_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project_dir / "visual_references.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = []
    for ref in references:
        line = ref.get("attribution") or ""
        if ref.get("sourcePage"):
            line = f"{line} - {ref['sourcePage']}".strip()
        if line and line not in lines:
            lines.append(line)
    if lines:
        (project_dir / "visual_attributions.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
