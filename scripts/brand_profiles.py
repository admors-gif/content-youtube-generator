"""Internal brand profiles for channel-specific generation defaults.

V1 intentionally has no UI editor. Projects store a snapshot of the profile
used at creation time so later brand changes do not mutate old productions.
"""
from __future__ import annotations

import copy


DEFAULT_BRAND_PROFILE_ID = "esto_no_es_amor"


BRAND_PROFILES = {
    DEFAULT_BRAND_PROFILE_ID: {
        "id": DEFAULT_BRAND_PROFILE_ID,
        "name": "Esto No Es Amor",
        "locked": True,
        "version": 1,
        "palette": {
            "black": "#050506",
            "crimson": "#D5123F",
            "softRed": "#B6423A",
            "offWhite": "#F5EFE6",
            "smoke": "#6E6A67",
        },
        "style": (
            "dark emotional noir, intimate cinematic symbolism, elegant minimalism, "
            "deep black backgrounds, crimson glow, off-white highlights, smoky gray atmosphere"
        ),
        "coreMessage": (
            "No todo lo que se siente intenso es amor; a veces es una herida pidiendo ser vista."
        ),
        "allowedElements": [
            "broken heart",
            "cracks",
            "smoke",
            "crimson light",
            "shadow silhouettes",
            "side profiles",
            "fading figures",
            "subtle audio lines",
            "fractured emotional mirrors",
            "red threads",
            "emotional distance",
            "healing symbolism",
        ],
        "forbiddenElements": [
            "large speakers",
            "studio gear",
            "headphones as main subject",
            "microphones as main subject",
            "detailed hands",
            "visible fingers",
            "realistic close-up faces",
            "smiling stock-photo couples",
            "happy romantic scenes",
            "random shoes",
            "random hallways",
            "random doors",
            "phones as main subject",
            "cups as main subject",
            "pastel colors",
            "cartoon style",
            "clutter",
            "text inside the generated image",
        ],
        "visualTemplate": (
            "Create a cinematic, emotionally intense cover image for the brand \"Esto No Es Amor\". "
            "Use a dark, elegant, moody noir aesthetic with black, deep crimson glow, off-white highlights "
            "and smoky gray atmosphere. Communicate one clear emotional metaphor related to the episode theme. "
            "Prefer conceptual cover art, silhouettes, side profiles, shadow figures, cracked heart symbolism, "
            "red threads, smoke, fractures and negative space. The image must be readable in one second, "
            "minimal, dramatic, psychologically clear and emotionally powerful."
        ),
        "negativePrompt": (
            "extra fingers, deformed hands, bad anatomy, distorted face, malformed face, bad eyes, "
            "asymmetrical face, speaker boxes, headphones as main subject, microphones as main subject, "
            "studio equipment, random hallway, random doors, shoes, furniture clutter, multiple unrelated objects, "
            "cartoon style, childish style, bright pastel colors, stock photo look, smiling happy couple, "
            "low contrast, blurry composition, confusing scene, text inside image, watermark, ugly composition"
        ),
        "ctas": [
            "Si esto te hizo sentido, sigueme. Aqui hablamos de lo que casi nadie sabe explicar del amor.",
            "Guarda esto para cuando vuelvas a confundir ansiedad con amor.",
            "Comenta \"apego\" si quieres que haga una segunda parte.",
            "Si alguna vez amaste desde la ansiedad, este canal es para ti.",
            "Sigueme si estas aprendiendo a elegirte sin sentir culpa.",
            "Mandaselo a alguien que necesita dejar de esperar un mensaje.",
            "Aqui no hablamos de amor bonito. Hablamos de las heridas que confundimos con amor.",
        ],
        "seoKeywords": [
            "apego emocional",
            "amor propio",
            "dependencia emocional",
            "relaciones",
            "contacto cero",
            "sanacion emocional",
            "heridas emocionales",
            "autoestima",
            "ghosting",
        ],
        "platformRules": {
            "youtube": {
                "aspectRatio": "16:9",
                "visualMode": "conceptual emotional cover, horizontal thumbnail-safe",
            },
            "tiktok": {
                "aspectRatio": "9:16",
                "visualMode": "vertical conceptual emotional cover, TikTok safe zones",
                "captionSafe": True,
            },
        },
    }
}


def get_brand_profile(profile_id: str | None = None) -> dict:
    profile = BRAND_PROFILES.get(profile_id or DEFAULT_BRAND_PROFILE_ID)
    if not profile:
        profile = BRAND_PROFILES[DEFAULT_BRAND_PROFILE_ID]
    return copy.deepcopy(profile)


def brand_profile_snapshot(profile_id: str | None = None) -> dict:
    profile = get_brand_profile(profile_id)
    profile["snapshotVersion"] = profile.get("version", 1)
    return profile

