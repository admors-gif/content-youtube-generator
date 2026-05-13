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
MAX_INTENT_TOPIC_CHARS = 170


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


def _as_list(value: object, limit: int = 10, item_limit: int = 160) -> list[str]:
    if isinstance(value, str):
        raw = re.split(r"[\n,;]+", value)
    elif isinstance(value, list):
        raw = value
    else:
        raw = []
    items: list[str] = []
    seen = set()
    for item in raw:
        clean = compact_text(item, item_limit)
        key = normalize_key(clean)
        if clean and key not in seen:
            items.append(clean)
            seen.add(key)
        if len(items) >= limit:
            break
    return items


def source_dna_from_analysis(analysis: dict | None) -> dict:
    analysis = analysis or {}
    beats = analysis.get("structureBeats") if isinstance(analysis.get("structureBeats"), list) else []
    beat_labels = [compact_text(item.get("label"), 80) for item in beats if isinstance(item, dict)]
    thesis = compact_text(analysis.get("centralThesis"), 320)
    emotion = compact_text(analysis.get("emotionalPromise") or analysis.get("audiencePain"), 220)
    return {
        "coreMessage": thesis,
        "recurringEmotion": emotion,
        "structurePattern": " > ".join(label for label in beat_labels[:6] if label) or "Hook emocional > conflicto > giro > integracion",
        "hookType": "pregunta existencial" if "?" in thesis or "¿" in thesis else "tension emocional",
        "resolutionType": "integracion espiritual suave" if _spiritual_level(analysis) != "none" else "claridad emocional",
    }


def content_dna_from_analysis(analysis: dict | None) -> dict:
    analysis = analysis or {}
    beats = analysis.get("structureBeats") if isinstance(analysis.get("structureBeats"), list) else []
    beat_text = " ".join(
        compact_text((item.get("label") or "") + " " + (item.get("purpose") or ""), 240)
        for item in beats
        if isinstance(item, dict)
    )
    text = " ".join([
        compact_text(analysis.get("centralThesis"), 400),
        compact_text(analysis.get("emotionalPromise"), 300),
        compact_text(analysis.get("audiencePain"), 300),
        beat_text,
    ])
    keywords = _keyword_candidates(text)
    return {
        "themes": keywords[:10],
        "metaphors": _as_list(analysis.get("keyMetaphors"), limit=8),
        "audiencePain": _as_list(analysis.get("audiencePain"), limit=8) or [compact_text(analysis.get("audiencePain"), 220)],
        "retentionBeats": _as_list(analysis.get("retentionMoments"), limit=8),
        "titlePatterns": _as_list(analysis.get("titleIdeas"), limit=8),
    }


def _keyword_candidates(text: str) -> list[str]:
    stop = {
        "para", "pero", "como", "cuando", "donde", "porque", "desde", "sobre", "este", "esta",
        "estos", "estas", "todo", "toda", "todos", "todas", "video", "fuente", "podcast",
        "mensaje", "persona", "personas", "forma", "manera", "algo", "solo", "cada", "entre",
    }
    normalized = unicodedata.normalize("NFKD", str(text or "").lower())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    words = re.findall(r"[a-z0-9áéíóúñü]{4,}", normalized)
    counts: dict[str, int] = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in ranked[:16]]


def _spiritual_level(analysis: dict | None) -> str:
    analysis = analysis or {}
    text = " ".join([
        compact_text(analysis.get("centralThesis"), 500),
        compact_text(analysis.get("podcastBrief"), 500),
        " ".join(_as_list(analysis.get("softSpiritualReferences"), limit=10)),
    ]).lower()
    explicit = ["cristo", "biblia", "bíblia", "mateo", "dios", "jesus", "jesús", "fe", "oracion", "oración", "divina", "divino"]
    soft = ["proposito", "propósito", "alma", "gratitud", "esperanza", "sentido", "presencia", "conciencia"]
    if any(term in text for term in explicit):
        return "explicit"
    if any(term in text for term in soft):
        return "soft"
    return "none"


def spiritual_profile_from_analysis(analysis: dict | None) -> dict:
    level = _spiritual_level(analysis)
    return {
        "level": level,
        "references": _as_list((analysis or {}).get("softSpiritualReferences"), limit=8),
        "transformationPolicy": "espiritualidad suave, emocional y no dogmatica" if level != "none" else "lenguaje emocional universal",
    }


def reuse_policy_from_analysis(analysis: dict | None, similarity: dict | None = None) -> dict:
    analysis = analysis or {}
    similarity = similarity or {}
    return {
        "doNotCopy": [
            "No copiar frases largas del transcript.",
            "No imitar la voz ni personalidad del creador fuente.",
            "No insinuar afiliacion con el canal original.",
        ],
        "allowedUse": "Inspiracion estructural: tesis, tension, beats y promesa emocional transformados a lenguaje propio.",
        "copyrightRisk": str(analysis.get("copyrightRisk") or "medium").lower(),
        "similarityRisk": similarity.get("risk") or "low",
    }


def enrich_analysis_dna(analysis: dict, similarity: dict | None = None) -> dict:
    out = dict(analysis or {})
    out["sourceDNA"] = out.get("sourceDNA") if isinstance(out.get("sourceDNA"), dict) else source_dna_from_analysis(out)
    out["contentDNA"] = out.get("contentDNA") if isinstance(out.get("contentDNA"), dict) else content_dna_from_analysis(out)
    out["spiritualProfile"] = out.get("spiritualProfile") if isinstance(out.get("spiritualProfile"), dict) else spiritual_profile_from_analysis(out)
    out["reusePolicy"] = out.get("reusePolicy") if isinstance(out.get("reusePolicy"), dict) else reuse_policy_from_analysis(out, similarity)
    return out


def agent_fit(analysis: dict, agent: dict) -> dict:
    analysis = enrich_analysis_dna(analysis)
    agent_id = agent.get("agentId") or agent.get("customAgentId") or ""
    name = compact_text(agent.get("name"), 100)
    desc = " ".join([
        compact_text(agent.get("description"), 500),
        compact_text(agent.get("category"), 80),
        compact_text(agent.get("format"), 80),
        compact_text(agent.get("templateKey"), 80),
    ]).lower()
    themes = " ".join((analysis.get("contentDNA") or {}).get("themes") or []).lower()
    spiritual_level = (analysis.get("spiritualProfile") or {}).get("level") or "none"

    score = 45
    reasons = []
    warnings = []
    if (agent.get("format") or "") == "podcast" or agent.get("templateKey") == "podcast_two_hosts":
        score += 18
        reasons.append("Formato podcast compatible.")
    if agent.get("agentSource") == "custom":
        score += 8
        reasons.append("Agente personalizado puede capturar mejor un nicho especifico.")
    if any(term in desc for term in ["espiritual", "motivacional", "fe", "alma", "proposito", "propósito"]):
        score += 20 if spiritual_level != "none" else 8
        reasons.append("El tono espiritual/motivacional encaja con la fuente.")
    if any(term in desc for term in ["amor", "apego", "relacion", "relación", "lucía", "mateo"]):
        if any(term in themes for term in ["miedo", "control", "abandono", "ansiedad", "rechazo", "amor"]):
            score += 10
            reasons.append("Puede adaptarse a heridas emocionales y relaciones.")
        if spiritual_level == "explicit" and agent_id == DEFAULT_TARGET_AGENT_ID:
            score -= 28
            warnings.append("La fuente trae lenguaje espiritual explicito y este agente tiene identidad emocional/noir distinta.")
    if agent_id == DEFAULT_TARGET_AGENT_ID:
        warnings.append("Usarlo requiere transformar la fuente a identidad Esto No Es Amor, no conservar predicacion.")
    score = max(0, min(100, score))
    recommendation = "adapt" if score >= 72 else "review" if score >= 55 else "create_agent"
    return {
        "agentId": agent_id,
        "agentName": name,
        "score": score,
        "recommendation": recommendation,
        "reasons": reasons[:5],
        "warnings": warnings[:5],
        "identityRisk": "high" if score < 55 else "medium" if warnings else "low",
    }


def route_source_video(analysis: dict, agents: list[dict]) -> dict:
    enriched = enrich_analysis_dna(analysis)
    fits = [agent_fit(enriched, agent) for agent in agents]
    fits.sort(key=lambda item: item["score"], reverse=True)
    best = fits[0] if fits else {}
    recommended_action = "adapt_existing" if best.get("score", 0) >= 72 else "create_agent"
    return {
        "recommendedAction": recommended_action,
        "summary": "Adaptar a un agente existente." if recommended_action == "adapt_existing" else "Crear o alimentar un agente nuevo para este nicho.",
        "agentRecommendations": fits[:8],
        "sourceDNA": enriched.get("sourceDNA") or {},
        "contentDNA": enriched.get("contentDNA") or {},
        "spiritualProfile": enriched.get("spiritualProfile") or {},
        "reusePolicy": enriched.get("reusePolicy") or {},
    }


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


def adaptation_prompt(
    analysis: dict,
    derivation: dict,
    source: dict,
    agent: dict,
    *,
    selected_title: str = "",
    allow_low_fit: bool = False,
) -> list[dict]:
    fit = agent_fit(analysis, agent)
    payload = {
        "source": {
            "title": source.get("title") or "",
            "channelName": source.get("channelName") or "",
        },
        "analysis": enrich_analysis_dna(analysis),
        "derivation": derivation,
        "agent": {
            "agentId": agent.get("agentId") or agent.get("customAgentId") or "",
            "name": agent.get("name") or "",
            "description": agent.get("description") or "",
            "format": agent.get("format") or "",
            "category": agent.get("category") or "",
            "templateKey": agent.get("templateKey") or "",
        },
        "fit": fit,
        "selectedTitle": selected_title,
        "allowLowFit": allow_low_fit,
    }
    system = (
        "You are an editorial adaptation producer. Transform a successful source video's idea into an original project "
        "for the selected Content Factory agent. Preserve the agent identity over the source identity. Do not copy phrases, "
        "do not imitate the source creator, do not claim affiliation. If the source is spiritual, keep it soft, emotional "
        "and non-dogmatic unless the selected agent explicitly requires religious content. Return strict JSON in Spanish."
    )
    user = (
        "Adapta esta fuente al agente destino. Si el agente es 'Esto no es amor', transforma la idea hacia apego, miedo, "
        "control, abandono, limites, autoestima o relaciones; no conserves formato de predicacion, exegesis biblica, "
        "Cristo, capitanes, sermones ni referencias religiosas explicitas en el titulo o brief final. "
        "JSON requerido: visibleTitle, shortTopic, inspirationBrief, agentFitSummary, warnings[], sourceSafety{similarityRisk,copyrightRisk,identityRisk}, "
        "adaptationRules[], whyThisWorks.\n\n"
        + json.dumps(json_safe(payload), ensure_ascii=False)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _normalized_search_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _default_agent_relationship_adaptation(analysis: dict, derivation: dict) -> dict:
    thesis = compact_text(analysis.get("centralThesis") or "", 420)
    pain = compact_text(analysis.get("audiencePain") or "", 260)
    title = "Cuando el miedo a perder el control te hace confundir amor con refugio"
    text = _normalized_search_text(" ".join([thesis, pain, " ".join((analysis.get("contentDNA") or {}).get("themes") or [])]))
    if "abandono" in text or "rechazo" in text:
        title = "Cuando el miedo al abandono te hace aceptar menos amor"
    elif "ansiedad" in text:
        title = "Cuando la ansiedad te hace rogar una señal de amor"
    elif "control" in text:
        title = "Cuando perder el control te hace perseguir a quien se aleja"

    return {
        "visibleTitle": title,
        "shortTopic": compact_text(title, MAX_INTENT_TOPIC_CHARS),
        "inspirationBrief": compact_text(
            "Reimagina la tesis del video fuente dentro de la identidad Esto No Es Amor: "
            "el miedo deja de tratarse como predicacion o doctrina y se convierte en una herida emocional. "
            "El episodio debe explorar como la necesidad de control, certeza y refugio puede confundirse con amor, "
            "por que una persona se aferra a alguien que no la elige con claridad, y como recuperar dignidad sin "
            "culpa ni persecucion. Usa una metafora noir emocional: una tormenta interna, un corazon que busca "
            "controlar lo incontrolable, y una salida hacia limites, amor propio y paz.",
            1200,
        ),
        "adaptationRules": [
            "Traducir cualquier espiritualidad explicita a lenguaje emocional universal.",
            "No usar Cristo, Biblia, sermon, capitanes ni predicacion en el resultado final.",
            "Centrar el conflicto en apego, control, miedo al abandono, autoestima y limites.",
            "Mantener la identidad noir emocional de Esto No Es Amor.",
        ],
        "whyThisWorks": "Convierte una tension humana probada, miedo y control, en un angulo relacional compatible con el canal.",
    }


def _default_agent_output_is_unadapted(out: dict, source: dict) -> bool:
    source_title = source.get("title") or ""
    combined = _normalized_search_text(
        " ".join([
            out.get("visibleTitle") or "",
            out.get("shortTopic") or "",
            out.get("inspirationBrief") or "",
            source_title if source_title and source_title in (out.get("visibleTitle") or "") else "",
        ])
    )
    blocked = [
        "cristo", "biblia", "biblica", "biblico", "mateo", "dios", "fe ", " fe",
        "oracion", "divina", "divino", "capitan", "capitanes", "sermon", "predicacion",
        "predicador", "exegesis", "teologica", "ontologica",
    ]
    return any(term in combined for term in blocked)


def normalize_adaptation(raw: dict | None, analysis: dict, derivation: dict, source: dict, agent: dict, selected_title: str = "") -> dict:
    fit = agent_fit(analysis, agent)
    base_title = compact_text(
        selected_title
        or derivation.get("recommendedTitle")
        or (derivation.get("titles") or [{}])[0].get("title")
        or (analysis.get("titleIdeas") or ["Episodio inspirado"])[0],
        120,
    )
    if (agent.get("agentId") or "") == DEFAULT_TARGET_AGENT_ID:
        lower = " ".join((analysis.get("contentDNA") or {}).get("themes") or []).lower()
        if any(term in lower for term in ["miedo", "control", "ansiedad"]):
            base_title = "Cuando el miedo a perder el control te hace confundir amor con refugio"
    fallback = {
        "visibleTitle": base_title,
        "shortTopic": compact_text(base_title, MAX_INTENT_TOPIC_CHARS),
        "inspirationBrief": compact_text(
            derivation.get("episodeBrief") or analysis.get("podcastBrief") or analysis.get("centralThesis"),
            1200,
        ),
        "agentFitSummary": "Fit editorial calculado para adaptar la fuente al agente seleccionado.",
        "warnings": fit.get("warnings") or [],
        "sourceSafety": {
            "similarityRisk": (derivation.get("similarity") or {}).get("risk") or "low",
            "copyrightRisk": (analysis.get("reusePolicy") or {}).get("copyrightRisk") or analysis.get("copyrightRisk") or "medium",
            "identityRisk": fit.get("identityRisk") or "medium",
        },
        "adaptationRules": [
            "Usar el video fuente solo como estructura e inspiracion.",
            "No copiar frases literales ni imitar al creador.",
            "Priorizar la identidad del agente destino.",
            "Mantener espiritualidad suave, emocional y no dogmatica si aparece.",
        ],
        "whyThisWorks": "Convierte una tension probada en un angulo original compatible con el agente.",
    }
    if not isinstance(raw, dict):
        return fallback
    out = {**fallback, **raw}
    out["visibleTitle"] = compact_text(out.get("visibleTitle") or fallback["visibleTitle"], 140)
    out["shortTopic"] = compact_text(out.get("shortTopic") or out["visibleTitle"], MAX_INTENT_TOPIC_CHARS)
    out["inspirationBrief"] = compact_text(out.get("inspirationBrief"), 1600)
    out["agentFitSummary"] = compact_text(out.get("agentFitSummary"), 360)
    out["warnings"] = _as_list(out.get("warnings"), limit=6, item_limit=180)
    out["adaptationRules"] = _as_list(out.get("adaptationRules"), limit=8, item_limit=180) or fallback["adaptationRules"]
    out["whyThisWorks"] = compact_text(out.get("whyThisWorks"), 420)
    safety = out.get("sourceSafety") if isinstance(out.get("sourceSafety"), dict) else {}
    out["sourceSafety"] = {
        **fallback["sourceSafety"],
        **{k: compact_text(v, 80) for k, v in safety.items()},
    }
    if (agent.get("agentId") or "") == DEFAULT_TARGET_AGENT_ID and _default_agent_output_is_unadapted(out, source):
        forced = _default_agent_relationship_adaptation(analysis, derivation)
        out.update(forced)
        out["warnings"] = _as_list(
            (out.get("warnings") or []) + ["La salida original seguia demasiado cerca del nicho espiritual; se reencuadro a Esto No Es Amor."],
            limit=6,
            item_limit=180,
        )
        out["sourceSafety"] = {**out["sourceSafety"], "identityRisk": "medium"}
    return out


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
    return enrich_analysis_dna(out)


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


def project_intent_payload(
    *,
    uid: str,
    agent: dict,
    source: dict,
    analysis: dict,
    derivation: dict,
    adaptation: dict,
    source_video_id: str,
    derivation_id: str = "",
    adaptation_id: str = "",
) -> dict:
    title = compact_text(adaptation.get("visibleTitle") or adaptation.get("shortTopic"), 140)
    short_topic = compact_text(adaptation.get("shortTopic") or title, MAX_INTENT_TOPIC_CHARS)
    brief = {
        "sourceVideoId": source_video_id,
        "sourceUrl": source.get("sourceUrl") or youtube_video_url(source.get("videoId") or ""),
        "sourceTitle": source.get("title") or "",
        "sourceChannel": source.get("channelName") or "",
        "analysisId": analysis.get("analysisId") or "",
        "derivationId": derivation_id or derivation.get("derivationId") or "",
        "adaptationId": adaptation_id or adaptation.get("adaptationId") or "",
        "sourceDNA": (analysis.get("sourceDNA") or source_dna_from_analysis(analysis)),
        "contentDNA": (analysis.get("contentDNA") or content_dna_from_analysis(analysis)),
        "spiritualProfile": (analysis.get("spiritualProfile") or spiritual_profile_from_analysis(analysis)),
        "episodeBrief": adaptation.get("inspirationBrief") or derivation.get("episodeBrief") or "",
        "openingHook": derivation.get("openingHook") or analysis.get("centralThesis") or "",
        "structure": derivation.get("structure") or analysis.get("structureBeats") or [],
        "adaptationRules": adaptation.get("adaptationRules") or [],
        "whyThisWorks": adaptation.get("whyThisWorks") or "",
    }
    safety = adaptation.get("sourceSafety") or reuse_policy_from_analysis(analysis, derivation.get("similarity") or {})
    return {
        "userId": uid,
        "agentId": agent.get("agentId") or agent.get("customAgentId") or DEFAULT_TARGET_AGENT_ID,
        "agentName": agent.get("name") or "Podcast",
        "agentFile": agent.get("promptFile") or agent.get("baseAgentFile") or "agent_podcast_general.md",
        "visibleTitle": title,
        "shortTopic": short_topic,
        "sourceVideoId": source_video_id,
        "derivationId": brief["derivationId"],
        "adaptationId": brief["adaptationId"],
        "inspirationBrief": brief,
        "sourceSafety": safety,
        "status": "prepared",
    }


def aggregate_collection_dna(sources: list[dict], analyses: list[dict]) -> dict:
    enriched = [enrich_analysis_dna(item) for item in analyses if isinstance(item, dict)]
    themes: list[str] = []
    metaphors: list[str] = []
    retention: list[str] = []
    structures: list[str] = []
    promises: list[str] = []
    spiritual_levels: list[str] = []
    for item in enriched:
        content = item.get("contentDNA") or {}
        source_dna = item.get("sourceDNA") or {}
        themes.extend(content.get("themes") or [])
        metaphors.extend(content.get("metaphors") or [])
        retention.extend(content.get("retentionBeats") or [])
        structures.append(source_dna.get("structurePattern") or "")
        promises.append(compact_text(item.get("emotionalPromise"), 220))
        spiritual_levels.append((item.get("spiritualProfile") or {}).get("level") or "none")
    top_themes = _as_list(themes, limit=14, item_limit=70)
    level = "explicit" if "explicit" in spiritual_levels else "soft" if "soft" in spiritual_levels else "none"
    return {
        "sourceCount": len(sources),
        "themes": top_themes,
        "metaphors": _as_list(metaphors, limit=10),
        "retentionPatterns": _as_list(retention, limit=10),
        "structurePatterns": _as_list(structures, limit=8, item_limit=220),
        "emotionalPromises": _as_list(promises, limit=8, item_limit=220),
        "spiritualProfile": {
            "level": level,
            "transformationPolicy": "espiritualidad suave, emocional y no dogmatica" if level != "none" else "lenguaje emocional universal",
        },
        "suggestedAgentTemplate": "podcast_two_hosts",
        "suggestedName": "Alma y Claridad" if level != "none" else "Claridad Emocional",
        "suggestedDescription": "Podcast de crecimiento emocional con espiritualidad suave, historias humanas y claridad practica.",
    }


def draft_agent_payload_from_collection(collection: dict, aggregate: dict) -> dict:
    name = compact_text(collection.get("agentName") or aggregate.get("suggestedName") or "Alma y Claridad", 80)
    themes = aggregate.get("themes") or []
    promise = (
        "Transformar miedo, confusion y perdida de control en claridad emocional, esperanza practica y una forma mas serena de actuar."
    )
    if aggregate.get("emotionalPromises"):
        promise = compact_text((aggregate.get("emotionalPromises") or [promise])[0], 340)
    return {
        "templateKey": "podcast_two_hosts",
        "name": name,
        "description": compact_text(aggregate.get("suggestedDescription"), 240),
        "category": "podcast",
        "color": "#7C5CFF",
        "monogram": "AC",
        "exampleTopics": [
            "Por que tienes miedo",
            "Cuando perder el control tambien puede ser una invitacion",
            "La paz que aparece cuando dejas de pelear con todo",
        ],
        "brief": {
            "niche": compact_text(collection.get("niche") or "motivacion emocional con espiritualidad suave", 260),
            "audience": "Personas que buscan crecer emocionalmente sin sentirse juzgadas, con apertura a fe, proposito y esperanza no dogmatica.",
            "promise": promise,
            "tone": "Conversacional, vulnerable, profundo, esperanzador, con espiritualidad suave y cero tono dogmatico.",
            "styleReferences": [
                "Conversaciones motivacionales con tension emocional.",
                "Historias humanas transformadas en claridad practica.",
                "Espiritualidad suave: fe, proposito y esperanza sin predicar.",
            ],
            "mustInclude": [
                "Hook emocional fuerte en los primeros segundos.",
                "Una historia o ejemplo humano concreto.",
                "Un giro que cambie la interpretacion del problema.",
                "Cierre con accion pequena y esperanzadora.",
            ],
            "mustAvoid": [
                "Copiar frases o estructura literal de videos fuente.",
                "Imitar predicadores o canales especificos.",
                "Dogmatismo religioso o promesas espirituales absolutas.",
                "Afirmaciones medicas o terapeuticas garantizadas.",
            ],
            "visualIdentity": "Visuales sobrios, luminosos, humanos y contemplativos; simbolos de camino, luz, tormenta, calma y reconstruccion.",
            "safetyNotes": "No presentar consejos espirituales como terapia ni prometer curacion. Usar fuentes como inspiracion privada, no como texto final.",
        },
    }


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
