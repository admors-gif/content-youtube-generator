"""Helpers for turning a source YouTube video into original podcast briefs.

The functions in this module are intentionally pure and dependency-light so the
API layer can provide Firestore, YouTube, and LLM clients without making tests
fragile.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse


DEFAULT_NICHE = "motivacional_espiritual"
DEFAULT_TARGET_FORMAT = "podcast"
DEFAULT_TARGET_AGENT_ID = "agent_podcast_general"
MAX_TRANSCRIPT_CHARS = 120_000
MAX_CHUNK_CHARS = 4_000
MAX_PREPARE_TOPIC_CHARS = 1_900


def compact_text(value: object, limit: int = 500) -> str:
    text = str(value or "")
    text = "".join(ch if (ch >= " " or ch in "\n\t") else " " for ch in text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "..."
    return text


def json_safe(value: object):
    """Return a JSON-serializable copy of Firestore/SDK-shaped values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return compact_text(value, 1000)


def normalize_key(value: object) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_youtube_url(value: str) -> str:
    """Return a YouTube video id from common URL shapes or an empty string."""
    text = str(value or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = parsed.path or ""
    query = parse_qs(parsed.query or "")

    if "youtube.com" in host and query.get("v"):
        candidate = str(query["v"][0] or "").strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate

    if "youtu.be" in host:
        candidate = path.strip("/").split("/")[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate

    match = re.search(r"/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})", path)
    if match:
        return match.group(1)

    match = re.search(r"(?:v=|/)([A-Za-z0-9_-]{11})(?:[?&#/]|$)", text)
    return match.group(1) if match else ""


def youtube_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else ""


def stable_source_video_id(uid: str, video_id: str) -> str:
    raw = f"{uid or 'admin'}|{video_id}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:32]


def transcript_hash(transcript: str) -> str:
    clean = clean_transcript(transcript)
    return hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest()[:24]


def clean_transcript(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?\]", " ", text)
    text = re.sub(r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_TRANSCRIPT_CHARS]


def chunk_transcript(value: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = clean_transcript(value)
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(sentence), max_chars):
                part = sentence[start : start + max_chars].strip()
                if part:
                    chunks.append(part)
            continue
        if len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


def _sentences_from_text(text: str, limit: int = 8) -> list[str]:
    sentences = [
        compact_text(item, 240)
        for item in re.split(r"(?<=[.!?])\s+", clean_transcript(text))
        if len(item.strip()) > 40
    ]
    return sentences[:limit]


def build_fallback_analysis(metadata: dict | None, transcript: str) -> dict:
    metadata = metadata or {}
    title = compact_text(metadata.get("title") or "Video fuente", 160)
    channel = compact_text(metadata.get("channelName") or metadata.get("channelTitle") or "", 120)
    sentences = _sentences_from_text(transcript, 10)
    chunks = chunk_transcript(transcript, max_chars=1600)[:6]
    beats = []
    for idx, chunk in enumerate(chunks):
        beats.append({
            "order": idx + 1,
            "label": [
                "Hook emocional",
                "Contexto del conflicto",
                "Desarrollo de la idea",
                "Giro o revelacion",
                "Integracion practica",
                "Cierre reflexivo",
            ][min(idx, 5)],
            "purpose": compact_text(chunk, 260),
        })

    return {
        "centralThesis": sentences[0] if sentences else f"Transformar el mensaje central de '{title}' en una conversacion original.",
        "emotionalPromise": "Ayudar al oyente a reinterpretar su historia con mas calma, responsabilidad y esperanza.",
        "audiencePain": "Personas que buscan sentido, claridad emocional y una forma mas amable de mirar sus procesos.",
        "structureBeats": beats,
        "keyMetaphors": [],
        "softSpiritualReferences": ["Referencias suaves a fe, proposito, gratitud o conciencia sin tono dogmatico."],
        "retentionMoments": [
            "Abrir con una pregunta personal y reconocible.",
            "Crear un giro entre lo que el oyente cree que necesita y lo que realmente puede integrar.",
            "Cerrar con una invitacion concreta a actuar distinto esta semana.",
        ],
        "titleIdeas": [
            f"Lo que este mensaje revela sobre tu proposito",
            "Cuando la vida te pide cambiar antes de estar listo",
            "La verdad incomoda que necesitas escuchar con calma",
        ],
        "podcastBrief": (
            f"Crear un podcast original inspirado en la tesis de '{title}'"
            + (f" de {channel}" if channel else "")
            + ". Mantener el nucleo emocional y transformar la estructura en dialogo, sin copiar frases ni imitar al creador."
        ),
        "transformationGuidance": "Usar la fuente como mapa de ideas, no como texto final. Cambiar ejemplos, lenguaje y ritmo conversacional.",
        "copyrightRisk": "medium",
        "safetyRisk": "low",
        "model": "heuristic_fallback",
    }


def analysis_prompt(metadata: dict, transcript_chunks: list[str], niche: str = DEFAULT_NICHE) -> list[dict]:
    source = {
        "title": metadata.get("title") or "",
        "channelName": metadata.get("channelName") or metadata.get("channelTitle") or "",
        "publishedAt": metadata.get("publishedAt") or "",
        "views": metadata.get("views") or 0,
        "niche": niche,
        "chunks": transcript_chunks[:18],
    }
    system = (
        "You are an editorial analyst for a Spanish content studio. Analyze source videos only as inspiration. "
        "Do not copy text, do not imitate the creator, and do not output long verbatim excerpts. "
        "Return strict JSON in Spanish."
    )
    user = (
        "Analiza este video fuente para convertirlo despues en un podcast original. "
        "Extrae la tesis, estructura emocional, momentos de retencion, metaforas y riesgos. "
        "El nicho inicial es motivacional/emocional con espiritualidad suave. "
        "JSON requerido: centralThesis, emotionalPromise, audiencePain, structureBeats[{order,label,purpose}], "
        "keyMetaphors[], softSpiritualReferences[], retentionMoments[], titleIdeas[], podcastBrief, "
        "transformationGuidance, copyrightRisk(low|medium|high), safetyRisk(low|medium|high).\n\n"
        + json.dumps(source, ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def derivation_prompt(
    analysis: dict,
    metadata: dict | None = None,
    *,
    target_agent_name: str = "Podcast",
    selected_title: str = "",
) -> list[dict]:
    metadata = metadata or {}
    payload = {
        "sourceTitle": metadata.get("title") or "",
        "sourceChannel": metadata.get("channelName") or metadata.get("channelTitle") or "",
        "targetAgentName": target_agent_name,
        "selectedTitle": selected_title,
        "analysis": analysis,
    }
    system = (
        "You are a senior podcast development producer. Create original Spanish podcast briefs inspired by a source idea. "
        "Never copy long phrases, never imitate the source creator, never claim affiliation, and avoid sermonizing. "
        "Use emotional clarity, conversational tension, and soft spirituality only when it serves the idea. "
        "Return strict JSON."
    )
    user = (
        "Convierte el analisis en opciones de podcast original. "
        "JSON requerido: titles[{title,hook,seoKeywords[],retentionReason}], recommendedTitle, "
        "episodeBrief, structure[{section,purpose}], openingHook, cta, similarityWarning.\n\n"
        + json.dumps(json_safe(payload), ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def normalize_analysis(raw: dict | None, metadata: dict | None, transcript: str) -> dict:
    fallback = build_fallback_analysis(metadata, transcript)
    if not isinstance(raw, dict):
        return fallback
    out = {**fallback, **raw}
    out["centralThesis"] = compact_text(out.get("centralThesis"), 600)
    out["emotionalPromise"] = compact_text(out.get("emotionalPromise"), 360)
    out["audiencePain"] = compact_text(out.get("audiencePain"), 360)
    out["podcastBrief"] = compact_text(out.get("podcastBrief"), 900)
    out["transformationGuidance"] = compact_text(out.get("transformationGuidance"), 700)
    out["copyrightRisk"] = str(out.get("copyrightRisk") or "medium").lower()
    out["safetyRisk"] = str(out.get("safetyRisk") or "low").lower()
    for key in ("keyMetaphors", "softSpiritualReferences", "retentionMoments", "titleIdeas"):
        values = out.get(key)
        out[key] = [compact_text(v, 180) for v in values[:10]] if isinstance(values, list) else fallback.get(key, [])
    beats = []
    for idx, item in enumerate(out.get("structureBeats") if isinstance(out.get("structureBeats"), list) else []):
        if not isinstance(item, dict):
            continue
        beats.append({
            "order": int(item.get("order") or idx + 1),
            "label": compact_text(item.get("label") or f"Bloque {idx + 1}", 80),
            "purpose": compact_text(item.get("purpose") or item.get("summary") or "", 320),
        })
    out["structureBeats"] = beats or fallback["structureBeats"]
    return out


def normalize_derivation(raw: dict | None, analysis: dict, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    base_title = compact_text((analysis.get("titleIdeas") or [metadata.get("title") or "Episodio inspirado"])[0], 120)
    fallback = {
        "titles": [
            {
                "title": base_title,
                "hook": compact_text(analysis.get("centralThesis"), 220),
                "seoKeywords": ["proposito", "claridad emocional", "crecimiento personal"],
                "retentionReason": "Promete una reinterpretacion emocional con aplicacion practica.",
            }
        ],
        "recommendedTitle": base_title,
        "episodeBrief": compact_text(analysis.get("podcastBrief"), 1000),
        "structure": [
            {"section": item.get("label"), "purpose": item.get("purpose")}
            for item in (analysis.get("structureBeats") or [])[:8]
        ],
        "openingHook": compact_text(analysis.get("centralThesis"), 260),
        "cta": "Invitar al oyente a observar que decision pequena puede tomar esta semana desde mas calma.",
        "similarityWarning": "",
        "model": "heuristic_fallback",
    }
    if not isinstance(raw, dict):
        return fallback
    out = {**fallback, **raw}
    titles = []
    for item in out.get("titles") if isinstance(out.get("titles"), list) else []:
        if isinstance(item, str):
            titles.append({"title": compact_text(item, 120), "hook": "", "seoKeywords": [], "retentionReason": ""})
        elif isinstance(item, dict):
            title = compact_text(item.get("title"), 120)
            if title:
                titles.append({
                    "title": title,
                    "hook": compact_text(item.get("hook"), 220),
                    "seoKeywords": [compact_text(v, 40) for v in (item.get("seoKeywords") or [])[:8]],
                    "retentionReason": compact_text(item.get("retentionReason"), 220),
                })
    out["titles"] = titles[:8] or fallback["titles"]
    out["recommendedTitle"] = compact_text(out.get("recommendedTitle") or out["titles"][0]["title"], 120)
    out["episodeBrief"] = compact_text(out.get("episodeBrief"), 1200)
    out["openingHook"] = compact_text(out.get("openingHook"), 320)
    out["cta"] = compact_text(out.get("cta"), 260)
    out["similarityWarning"] = compact_text(out.get("similarityWarning"), 260)
    structure = []
    for idx, item in enumerate(out.get("structure") if isinstance(out.get("structure"), list) else []):
        if not isinstance(item, dict):
            continue
        structure.append({
            "section": compact_text(item.get("section") or f"Bloque {idx + 1}", 80),
            "purpose": compact_text(item.get("purpose"), 260),
        })
    out["structure"] = structure or fallback["structure"]
    return out


def parse_json_object(text: str) -> dict | None:
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _word_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", clean_transcript(text).lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return [w for w in re.findall(r"[a-z0-9áéíóúñü]+", normalized) if len(w) >= 4]


def similarity_guard(source_text: str, generated_text: str, n: int = 5) -> dict:
    source_words = _word_tokens(source_text)
    gen_words = _word_tokens(generated_text)
    if len(source_words) < n or len(gen_words) < n:
        return {"risk": "low", "overlapRatio": 0.0, "matches": []}
    source_grams = {" ".join(source_words[i : i + n]) for i in range(0, len(source_words) - n + 1)}
    gen_grams = [" ".join(gen_words[i : i + n]) for i in range(0, len(gen_words) - n + 1)]
    matches = sorted({gram for gram in gen_grams if gram in source_grams})[:12]
    ratio = len(matches) / max(1, len(set(gen_grams)))
    risk = "high" if ratio >= 0.08 or len(matches) >= 8 else "medium" if ratio >= 0.035 or len(matches) >= 4 else "low"
    return {"risk": risk, "overlapRatio": round(ratio, 4), "matches": matches}


def build_project_topic(derivation: dict, analysis: dict, metadata: dict | None = None, selected_title: str = "") -> str:
    metadata = metadata or {}
    title = compact_text(selected_title or derivation.get("recommendedTitle") or (derivation.get("titles") or [{}])[0].get("title"), 140)
    parts = [
        title,
        "",
        "Brief original para podcast:",
        compact_text(derivation.get("episodeBrief") or analysis.get("podcastBrief"), 900),
        "",
        "Hook inicial:",
        compact_text(derivation.get("openingHook") or analysis.get("centralThesis"), 300),
        "",
        "Estructura sugerida:",
    ]
    for item in (derivation.get("structure") or [])[:8]:
        parts.append(f"- {compact_text(item.get('section'), 70)}: {compact_text(item.get('purpose'), 180)}")
    parts.extend([
        "",
        "Reglas editoriales:",
        "- Usar el video fuente solo como inspiracion de idea y estructura.",
        "- No copiar frases literales ni imitar al creador.",
        "- Convertirlo en conversacion original con ejemplos propios.",
        "- Mantener espiritualidad suave, emocional y no dogmatica.",
    ])
    source_title = compact_text(metadata.get("title"), 160)
    if source_title:
        parts.extend(["", f"Referencia interna: video fuente '{source_title}'. No mencionarlo como afiliacion."])
    return compact_text("\n".join(parts), MAX_PREPARE_TOPIC_CHARS)


def public_source_video(doc_id: str, data: dict | None) -> dict:
    data = data or {}
    return {
        "sourceVideoId": data.get("sourceVideoId") or doc_id,
        "sourceUrl": data.get("sourceUrl") or youtube_video_url(data.get("videoId") or ""),
        "platform": data.get("platform") or "youtube",
        "videoId": data.get("videoId") or "",
        "channelId": data.get("channelId") or "",
        "channelName": data.get("channelName") or "",
        "title": data.get("title") or "",
        "description": data.get("description") or "",
        "publishedAt": data.get("publishedAt") or "",
        "views": data.get("views") or 0,
        "duration": data.get("duration") or "",
        "thumbnailUrl": data.get("thumbnailUrl") or "",
        "transcriptStatus": data.get("transcriptStatus") or "missing",
        "status": data.get("status") or "imported",
        "niche": data.get("niche") or DEFAULT_NICHE,
        "analysisId": data.get("analysisId") or "",
        "derivationId": data.get("derivationId") or "",
        "createdAt": data.get("createdAt"),
        "updatedAt": data.get("updatedAt"),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
