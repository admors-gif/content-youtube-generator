"""
Editorial radar helpers for Content Factory.

This module is intentionally dependency-light: API routes provide Tavily/LLM
clients, while the functions here normalize, score, dedupe, and shape data.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse


NEWS_AGENT_ID = "agent_noticias_virales"
DEFAULT_MARKET = "mx"
DEFAULT_LANGUAGE = "es"
DEFAULT_WINDOW = "today"
DEFAULT_CATEGORY = "all"
MAX_MANUAL_LIMIT = 12
MAX_AGENT_LIMIT = 5
RADAR_CACHE_TTL_SECONDS = 3600
RADAR_CACHE_VERSION = "v2"

HIGH_RISK_TERMS = {
    "acusacion",
    "acusación",
    "demanda",
    "denuncia",
    "fraude",
    "asesinato",
    "violacion",
    "violación",
    "abuso",
    "suicidio",
    "medico",
    "médico",
    "cura",
    "milagro",
}

NEWS_QUERIES = [
    "noticias virales hoy",
    "tendencias redes sociales hoy",
    "polemica viral esta semana",
    "historia detras de noticia viral",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def compact_text(value: str | None, limit: int = 420) -> str:
    clean = " ".join(str(value or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def source_domain(url: str | None) -> str:
    try:
        host = urlparse(str(url or "")).netloc.lower()
    except Exception:
        host = ""
    if host.startswith("www."):
        host = host[4:]
    return host


def candidate_hash(agent_id: str, title: str, primary_url: str | None = "") -> str:
    domain = source_domain(primary_url)
    raw = "|".join([normalize_text(agent_id), normalize_text(title), domain])
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:20]


def canonical_title_key(agent_id: str, title: str) -> str:
    return "|".join([normalize_text(agent_id), normalize_text(title)])


def cache_key(
    *,
    scope: str,
    agent_id: str,
    market: str,
    language: str,
    category: str,
    window: str,
) -> str:
    raw = "|".join(
        [
            RADAR_CACHE_VERSION,
            normalize_text(scope or "global"),
            normalize_text(agent_id or "all"),
            normalize_text(market or DEFAULT_MARKET),
            normalize_text(language or DEFAULT_LANGUAGE),
            normalize_text(category or DEFAULT_CATEGORY),
            normalize_text(window or DEFAULT_WINDOW),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:24]


def agent_label(agent: dict) -> str:
    return str(agent.get("name") or agent.get("agentName") or agent.get("agent_id") or agent.get("agentId") or "").strip()


def agent_id(agent: dict) -> str:
    return str(agent.get("agentId") or agent.get("agent_id") or "").strip()


def agent_file(agent: dict) -> str:
    aid = agent_id(agent)
    return str(agent.get("promptFile") or agent.get("agentFile") or f"{aid}.md").strip()


def build_news_queries(
    *,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    max_queries: int = 5,
) -> list[str]:
    market_hint = "Mexico y Latinoamerica" if normalize_text(market) in {"mx", "latam", "mexico"} else market
    language_hint = "en espanol fuentes de Mexico y Latinoamerica" if normalize_text(language) in {"es", "es-mx", "spanish", "espanol"} else f"en {language}"
    queries = [f"{q} {market_hint} {language_hint}" for q in NEWS_QUERIES]
    if category and category != "all":
        queries.append(f"{category} noticia viral tendencia {market_hint} {language_hint}")
    return queries[: max(1, max_queries)]


def build_agent_queries(
    agent: dict,
    *,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    max_queries: int = 2,
) -> list[str]:
    aid = agent_id(agent)
    if aid == NEWS_AGENT_ID:
        return build_news_queries(
            market=market,
            language=language,
            category=category,
            max_queries=max_queries,
        )

    name = agent_label(agent)
    description = str(agent.get("description") or "").strip()
    examples = agent.get("exampleTopics") or agent.get("examples") or []
    example_hint = examples[0] if examples else description
    market_hint = "Mexico Latinoamerica" if normalize_text(market) in {"mx", "latam"} else market
    language_hint = "en espanol para audiencia latina" if normalize_text(language) in {"es", "es-mx", "spanish", "espanol"} else f"en {language}"
    base = f"{name} {description}".strip()
    queries = [
        f"tendencias actuales para video de YouTube sobre {base} {market_hint} {language_hint}",
        f"temas populares preguntas historias virales {base} {market_hint} {language_hint}",
    ]
    if example_hint:
        queries.append(f"ideas relacionadas con {example_hint} tendencia video documental {language_hint}")
    if category and category != "all":
        queries.append(f"{category} {name} tema actual video viral {language_hint}")
    return queries[: max(1, max_queries)]


def fallback_candidates_for_agent(agent: dict, *, limit: int = 3) -> list[dict]:
    aid = agent_id(agent)
    name = agent_label(agent)
    description = compact_text(agent.get("description"), 180)
    examples = agent.get("exampleTopics") or agent.get("examples") or []
    seeds = examples[:limit] or [
        f"Lo que nadie esta explicando sobre {name}",
        f"La historia oculta detras de {name}",
        f"Por que {name} esta volviendo a importar",
    ]
    candidates = []
    for index, seed in enumerate(seeds[:limit], 1):
        summary = description or f"Idea editorial sugerida para {name}."
        candidates.append(
            shape_candidate(
                agent=agent,
                title=str(seed),
                summary=summary,
                angle=f"{seed}: explicado con contexto, tension narrativa y cierre claro",
                why_now="Idea evergreen generada como fallback cuando no hay busqueda web disponible.",
                sources=[],
                query="fallback",
                source_type="fallback",
                recommended_format="youtube_long" if not str(agent.get("platform")) == "tiktok" else "tiktok",
                rank_seed=index,
            )
        )
    return candidates


def tavily_results_to_candidates(
    agent: dict,
    query: str,
    response: dict | None,
    *,
    limit: int = 5,
) -> list[dict]:
    response = response or {}
    answer = compact_text(response.get("answer"), 360)
    results = response.get("results") or []
    candidates = []
    for index, item in enumerate(results[:limit], 1):
        title = compact_text(item.get("title") or query, 160)
        content = compact_text(item.get("content") or answer or title, 520)
        url = str(item.get("url") or "").strip()
        source = {
            "title": title or source_domain(url) or "Fuente",
            "url": url,
            "domain": source_domain(url),
        }
        angle = build_angle(agent, title, content)
        candidates.append(
            shape_candidate(
                agent=agent,
                title=title,
                summary=content,
                angle=angle,
                why_now=answer or f"Aparecio en busqueda editorial: {query}.",
                sources=[source] if url else [],
                query=query,
                source_type="tavily",
                rank_seed=index,
            )
        )
    if not candidates and answer:
        candidates.append(
            shape_candidate(
                agent=agent,
                title=query,
                summary=answer,
                angle=build_angle(agent, query, answer),
                why_now=answer,
                sources=[],
                query=query,
                source_type="tavily_answer",
                rank_seed=1,
            )
        )
    return candidates


def build_angle(agent: dict, title: str, summary: str) -> str:
    aid = agent_id(agent)
    if aid == NEWS_AGENT_ID:
        return f"La historia detras de {title}: que paso, por que se volvio viral y que revela"
    if aid == "agent_podcast_general":
        return f"{title}: una conversacion sobre apego, deseo, limites y autoengano"
    if aid in {"agent_autohipnosis", "agent_meditacion_larga", "agent_tiktok_autohipnosis", "agent_tiktok_meditation"}:
        return f"{title}: una sesion segura, calmada y sin promesas medicas"
    return f"{title}: contado como una historia con contexto, giro y consecuencia"


def infer_recommended_format(agent: dict, title: str, summary: str) -> str:
    aid = agent_id(agent)
    lower = normalize_text(f"{title} {summary}")
    if str(agent.get("platform") or "").lower() == "tiktok" or aid.startswith("agent_tiktok_"):
        return "tiktok"
    if aid == NEWS_AGENT_ID and any(token in lower for token in ["viral", "tiktok", "video", "redes"]):
        return "both"
    if len(summary.split()) < 45 and any(token in lower for token in ["viral", "polemica", "debate", "nadie"]):
        return "both"
    return "youtube_long"


def classify_risk(agent: dict, title: str, summary: str, sources: list[dict]) -> tuple[str, str]:
    aid = agent_id(agent)
    lower = normalize_text(f"{title} {summary}")
    hits = [term for term in HIGH_RISK_TERMS if normalize_text(term) in lower]
    if aid == NEWS_AGENT_ID and len(sources) < 2:
        if hits:
            return "high", "Tema sensible con menos de dos fuentes verificables."
        return "medium", "Noticia actual con fuente unica; revisar antes de producir."
    if aid in {"agent_autohipnosis", "agent_meditacion_larga", "agent_tiktok_autohypnosis", "agent_tiktok_meditation"}:
        if any(token in lower for token in ["cura", "curar", "depresion", "depresion", "diagnostico", "trauma"]):
            return "high", "Wellness con posible promesa medica o clinica."
    if hits:
        return "medium", "Contiene terminos sensibles; requiere revision editorial."
    return "low", "Riesgo editorial bajo para revision normal."


def score_candidate(candidate: dict, agent: dict) -> dict:
    text = normalize_text(" ".join([
        candidate.get("title") or "",
        candidate.get("summary") or "",
        candidate.get("angle") or "",
    ]))
    sources = candidate.get("sources") or []
    aid = agent_id(agent)
    audience = 55
    fit = 60
    arc = 55
    freshness = 45
    ease = 70
    risk_score = 90 if candidate.get("riskLevel") == "low" else 55 if candidate.get("riskLevel") == "medium" else 20

    viral_terms = ["viral", "polemica", "tendencia", "nadie", "secreto", "verdad", "debate", "historia"]
    audience += min(30, sum(1 for term in viral_terms if term in text) * 6)
    arc += min(25, sum(1 for term in ["porque", "detras", "consecuencia", "caida", "ascenso", "misterio"] if term in text) * 6)
    freshness += 25 if candidate.get("sourceType") in {"tavily", "tavily_answer"} else 0
    freshness += 10 if aid == NEWS_AGENT_ID else 0
    fit += 18 if normalize_text(agent_label(agent)).split(" ")[0] in text else 0
    fit += 20 if aid == NEWS_AGENT_ID and any(term in text for term in ["noticia", "viral", "redes", "polemica"]) else 0
    if aid == "agent_podcast_general":
        fit += 20 if any(term in text for term in ["amor", "apego", "limites", "ruptura", "contacto cero", "ansiedad"]) else 0
    if len(sources) >= 2:
        freshness += 10
        risk_score += 5
    if len(sources) == 0 and candidate.get("sourceType") != "fallback":
        risk_score -= 15
    if candidate.get("riskLevel") == "high":
        audience -= 10
        ease -= 20

    scores = {
        "audience": clamp_score(audience),
        "fit": clamp_score(fit),
        "storyArc": clamp_score(arc),
        "freshness": clamp_score(freshness),
        "productionEase": clamp_score(ease),
        "risk": clamp_score(risk_score),
    }
    total = round(
        scores["audience"] * 0.25
        + scores["fit"] * 0.20
        + scores["storyArc"] * 0.20
        + scores["freshness"] * 0.15
        + scores["productionEase"] * 0.10
        + scores["risk"] * 0.10
    )
    return {**scores, "overall": clamp_score(total)}


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def shape_candidate(
    *,
    agent: dict,
    title: str,
    summary: str,
    angle: str,
    why_now: str,
    sources: list[dict],
    query: str,
    source_type: str,
    recommended_format: str | None = None,
    rank_seed: int = 0,
) -> dict:
    aid = agent_id(agent)
    primary_url = (sources[0] or {}).get("url") if sources else ""
    risk_level, risk_reason = classify_risk(agent, title, summary, sources)
    candidate = {
        "candidateHash": candidate_hash(aid, title, primary_url),
        "agentId": aid,
        "agentName": agent_label(agent),
        "agentFile": agent_file(agent),
        "platform": str(agent.get("platform") or ("tiktok" if aid.startswith("agent_tiktok_") else "youtube")),
        "format": agent.get("format") or "",
        "category": agent.get("category") or "",
        "title": compact_text(title, 180),
        "headline": compact_text(title, 180),
        "summary": compact_text(summary, 650),
        "angle": compact_text(angle, 240),
        "whyNow": compact_text(why_now, 420),
        "sources": normalize_sources(sources),
        "recommendedFormat": recommended_format or infer_recommended_format(agent, title, summary),
        "riskLevel": risk_level,
        "riskReason": risk_reason,
        "sourceQuery": query,
        "sourceType": source_type,
        "rankSeed": rank_seed,
    }
    scores = score_candidate(candidate, agent)
    candidate["scores"] = scores
    candidate["editorialScore"] = scores["overall"]
    return candidate


def normalize_sources(sources: list[dict]) -> list[dict]:
    normalized = []
    seen = set()
    for source in sources or []:
        url = str(source.get("url") or "").strip()
        title = compact_text(source.get("title") or source_domain(url) or "Fuente", 140)
        domain = source.get("domain") or source_domain(url)
        key = url or domain or title
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append({"title": title, "url": url, "domain": domain})
    return normalized[:5]


def dedupe_candidates(
    candidates: list[dict],
    *,
    existing_hashes: set[str] | None = None,
    existing_title_keys: set[str] | None = None,
    limit: int = MAX_MANUAL_LIMIT,
) -> list[dict]:
    existing_hashes = existing_hashes or set()
    existing_title_keys = existing_title_keys or set()
    seen_hashes = set(existing_hashes)
    seen_titles = set(existing_title_keys)
    out = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item.get("editorialScore") or 0, -(item.get("rankSeed") or 0)),
        reverse=True,
    ):
        ch = candidate.get("candidateHash")
        title_key = canonical_title_key(candidate.get("agentId"), candidate.get("title"))
        if ch in seen_hashes or title_key in seen_titles:
            continue
        seen_hashes.add(ch)
        seen_titles.add(title_key)
        out.append(candidate)
        if len(out) >= limit:
            break
    return out


def parse_ranking_response(text: str) -> list[dict]:
    clean = (text or "").strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1] if "\n" in clean else clean
        clean = clean.rsplit("```", 1)[0].strip()
    data = json.loads(clean)
    if not isinstance(data, list):
        raise ValueError("ranking response must be a list")
    return data


def apply_llm_ranking(candidates: list[dict], llm_items: list[dict]) -> list[dict]:
    by_hash = {item.get("candidateHash"): dict(item) for item in candidates}
    ranked = []
    for llm_item in llm_items:
        ch = llm_item.get("candidateHash")
        if ch not in by_hash:
            continue
        candidate = by_hash.pop(ch)
        try:
            score = clamp_score(float(llm_item.get("editorialScore", candidate.get("editorialScore", 0))))
        except Exception:
            score = candidate.get("editorialScore", 0)
        candidate["editorialScore"] = score
        candidate.setdefault("scores", {})["overall"] = score
        if llm_item.get("angle"):
            candidate["angle"] = compact_text(llm_item["angle"], 240)
        if llm_item.get("riskLevel") in {"low", "medium", "high"}:
            candidate["riskLevel"] = llm_item["riskLevel"]
        if llm_item.get("riskReason"):
            candidate["riskReason"] = compact_text(llm_item["riskReason"], 260)
        if llm_item.get("recommendationReason"):
            candidate["recommendationReason"] = compact_text(llm_item["recommendationReason"], 260)
        ranked.append(candidate)
    ranked.extend(sorted(by_hash.values(), key=lambda item: item.get("editorialScore", 0), reverse=True))
    return ranked


def build_ranking_prompt(candidates: list[dict], *, scope: str) -> str:
    compact = [
        {
            "candidateHash": c.get("candidateHash"),
            "agentId": c.get("agentId"),
            "title": c.get("title"),
            "summary": c.get("summary"),
            "angle": c.get("angle"),
            "sources": [s.get("domain") or s.get("url") for s in c.get("sources", [])],
            "riskLevel": c.get("riskLevel"),
            "editorialScore": c.get("editorialScore"),
        }
        for c in candidates[:24]
    ]
    return (
        "Eres editor estrategico de Content Factory. Rankea estas ideas de video.\n"
        "Devuelve EXCLUSIVAMENTE JSON array. No markdown.\n"
        "Cada item debe conservar candidateHash e incluir: editorialScore 0-100, "
        "angle, riskLevel low|medium|high, riskReason, recommendationReason.\n"
        "Penaliza fuentes debiles, promesas medicas, acusaciones legales sin evidencia y sensacionalismo.\n"
        f"Scope: {scope}\n"
        f"Candidatos:\n{json.dumps(compact, ensure_ascii=False)}"
    )

