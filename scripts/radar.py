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
DEFAULT_INTENT = "viral_topics"
MAX_MANUAL_LIMIT = 12
MAX_AGENT_LIMIT = 5
RADAR_CACHE_TTL_SECONDS = 3600
RADAR_CACHE_VERSION = "v4"
RADAR_INTENTS = {
    "news",
    "viral_topics",
    "audience_pain",
    "evergreen",
    "shorts_hooks",
    "calendar_gaps",
}

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

PODCAST_AGENT_IDS = {"agent_podcast_general", "agent_tiktok_podcast"}
PODCAST_TOPIC_CORE = (
    "apego emocional ruptura contacto cero limites amor propio ghosting "
    "breadcrumbing ansiedad en relaciones dependencia emocional duelo amoroso"
)
PODCAST_FALLBACK_SEEDS = {
    "viral_topics": [
        "Por que confundes ansiedad con amor",
        "La senal de que no era amor, era apego",
        "Cuando te busca justo cuando ya estabas sanando",
        "Por que el contacto cero duele como abstinencia",
    ],
    "audience_pain": [
        "Me dejo en visto pero sigue viendo mis historias",
        "Por que extraño a alguien que me hacia sentir insegura",
        "No puedo soltar aunque se que no me conviene",
        "Cuando pedir claridad se siente como rogar amor",
    ],
    "shorts_hooks": [
        "No extrañas a esa persona: extrañas la version de ti que inventaste",
        "Si te da paz solo cuando aparece, no es paz",
        "El amor no te deja revisando el celular cada cinco minutos",
        "Contacto cero no es castigo: es desintoxicacion emocional",
    ],
    "evergreen": [
        "Amor o apego: como reconocer la diferencia sin mentirte",
        "Por que elegimos personas emocionalmente no disponibles",
        "Los limites que salvan tu dignidad despues de una ruptura",
        "Como dejar de romantizar la intensidad",
    ],
    "calendar_gaps": [
        "Episodio puente: antes de volver con tu ex, escucha esto",
        "Episodio corto: tres señales de que ya estas negociando tus limites",
        "Episodio profundo: la fantasia de cierre que nunca llega",
        "Episodio derivable: contacto cero para podcast, Shorts y TikTok",
    ],
}

KNOWLEDGE_AGENT_HINTS = {
    "business": "ventas liderazgo emprendimiento marketing negociacion productividad",
    "biography": "biografia historia liderazgo legado decisiones crisis",
    "finance": "finanzas inversion riesgo burbujas dinero economia",
    "history": "historia imperios civilizaciones guerra poder vida cotidiana",
    "mystery": "misterio investigacion simbolos sociedades secretas enigmas",
    "philosophy": "filosofia estoicismo sentido disciplina virtud vida moderna",
    "psychology": "psicologia emociones trauma manipulacion conducta humana",
    "religion": "religion textos sagrados espiritualidad simbolismo fe",
    "science": "ciencia tecnologia descubrimientos universo mente futuro",
    "technology": "inteligencia artificial tecnologia futuro innovacion productividad",
    "travel": "viajes cultura lugares historia guias experiencias",
    "wellness": "habitos meditacion bienestar ansiedad descanso autoconocimiento",
}

PODCAST_KNOWLEDGE_QUERIES = {
    "viral_topics": [
        "apego ansioso ghosting contacto cero dependencia emocional limites relaciones",
        "por que alguien mira historias pero no responde ansiedad apego ruptura",
        "limerencia breadcrumbing validacion intermitente amor propio relaciones",
    ],
    "audience_pain": [
        "me dejo en visto pero ve mis historias apego ansiedad validacion",
        "no puedo soltar a mi ex dependencia emocional duelo ruptura",
        "siento que pedir claridad es rogar limites autoestima relaciones",
    ],
    "shorts_hooks": [
        "frases paradojas apego emocional contacto cero amor propio limites",
        "senales de ansiedad en relaciones ghosting dependencia emocional",
        "verdades incomodas ruptura ex validacion intermitente",
    ],
    "evergreen": [
        "diferencia entre amor apego dependencia emocional limites autoestima",
        "apego evitativo apego ansioso relaciones contacto cero duelo",
        "autoengano romantizar intensidad amor propio relaciones",
    ],
    "calendar_gaps": [
        "serie editorial apego limites ruptura contacto cero amor propio",
        "temas complementarios ansiedad relaciones dependencia emocional duelo",
        "contenido derivado podcast shorts tiktok apego ghosting limites",
    ],
}

PODCAST_TITLE_ADJACENT_TOPICS = [
    "Cuando te escribe justo cuando estabas sanando",
    "No extrañas a tu ex: extrañas la ansiedad que te daba",
    "La migaja emocional que te hace empezar de cero",
    "Por que quieres cerrar una historia que ya te cerro a ti",
    "Cuando dejar de esperar se siente como traicionar lo que sentias",
    "Si te busca solo cuando te alejas, no es amor",
    "La paz que llega cuando dejas de revisar sus historias",
    "Por que confundes intensidad con destino",
]

TITLE_LAB_POWER_WORDS = {
    "nadie",
    "verdad",
    "error",
    "errores",
    "duele",
    "secreto",
    "incomoda",
    "incómoda",
    "nunca",
    "si",
    "cuando",
    "porque",
    "por que",
    "ex",
    "vuelve",
    "deja",
    "ansiedad",
    "extrañas",
    "extranas",
}


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
    intent: str = DEFAULT_INTENT,
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
            normalize_intent(intent),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:24]


def normalize_intent(value: str | None) -> str:
    intent = normalize_text(value or DEFAULT_INTENT).replace(" ", "_")
    if intent in {"topics", "temas"}:
        return "viral_topics"
    if intent in {"pain", "dolores", "pain_points"}:
        return "audience_pain"
    if intent in {"hooks", "shorts"}:
        return "shorts_hooks"
    if intent in {"calendar", "gaps"}:
        return "calendar_gaps"
    if intent not in RADAR_INTENTS:
        return DEFAULT_INTENT
    return intent


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


def build_podcast_queries(
    agent: dict,
    *,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    intent: str = DEFAULT_INTENT,
    max_queries: int = 3,
) -> list[str]:
    intent = normalize_intent(intent)
    market_hint = "Mexico Latinoamerica" if normalize_text(market) in {"mx", "latam", "mexico"} else market
    language_hint = "en espanol para audiencia latina" if normalize_text(language) in {"es", "es-mx", "spanish", "espanol"} else f"en {language}"
    category_hint = "" if not category or category == "all" else f"{category} "
    platform_hint = "TikTok Reels Shorts" if agent_id(agent) == "agent_tiktok_podcast" or intent == "shorts_hooks" else "podcast YouTube"

    intent_queries = {
        "viral_topics": [
            f"temas virales relaciones {PODCAST_TOPIC_CORE} {market_hint} {language_hint}",
            f"preguntas populares sobre {category_hint}apego ruptura contacto cero relaciones {market_hint} {language_hint}",
            f"tendencias TikTok relaciones apego evitativo limerencia ghosting breadcrumbing {language_hint}",
        ],
        "audience_pain": [
            f"dolores reales audiencia relaciones {PODCAST_TOPIC_CORE} reddit quora {language_hint}",
            f"preguntas de personas que no pueden soltar a su ex apego ansiedad relaciones {market_hint} {language_hint}",
            f"situaciones comunes despues de una ruptura contacto cero volver con ex limites {language_hint}",
        ],
        "shorts_hooks": [
            f"frases virales hooks TikTok relaciones apego emocional ruptura contacto cero {language_hint}",
            f"ganchos de video corto amor propio limites dependencia emocional ghosting {market_hint} {language_hint}",
            f"temas para Shorts sobre ansiedad en relaciones apego evitativo breadcrumbing {language_hint}",
        ],
        "evergreen": [
            f"temas evergreen podcast relaciones apego emocional limites amor propio {language_hint}",
            f"preguntas frecuentes amor o apego dependencia emocional contacto cero ruptura {language_hint}",
            f"temas profundos relaciones psicologia popular apego ansiedad limites {market_hint} {language_hint}",
        ],
        "calendar_gaps": [
            f"ideas calendario editorial podcast relaciones apego ruptura contacto cero amor propio {language_hint}",
            f"temas derivados podcast largo shorts tiktok relaciones apego limites {market_hint} {language_hint}",
            f"huecos editoriales canal relaciones amor propio dependencia emocional {platform_hint} {language_hint}",
        ],
    }
    return intent_queries.get(intent, intent_queries["viral_topics"])[: max(1, max_queries)]


def build_agent_queries(
    agent: dict,
    *,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    intent: str = DEFAULT_INTENT,
    max_queries: int = 2,
) -> list[str]:
    aid = agent_id(agent)
    intent = normalize_intent(intent)
    if aid == NEWS_AGENT_ID or intent == "news":
        return build_news_queries(
            market=market,
            language=language,
            category=category,
            max_queries=max_queries,
        )
    if aid in PODCAST_AGENT_IDS:
        return build_podcast_queries(
            agent,
            market=market,
            language=language,
            category=category,
            intent=intent,
            max_queries=max_queries,
        )

    name = agent_label(agent)
    description = str(agent.get("description") or "").strip()
    examples = agent.get("exampleTopics") or agent.get("examples") or []
    example_hint = examples[0] if examples else description
    market_hint = "Mexico Latinoamerica" if normalize_text(market) in {"mx", "latam"} else market
    language_hint = "en espanol para audiencia latina" if normalize_text(language) in {"es", "es-mx", "spanish", "espanol"} else f"en {language}"
    base = f"{name} {description}".strip()
    if intent == "audience_pain":
        queries = [
            f"preguntas populares problemas dudas audiencia sobre {base} {market_hint} {language_hint}",
            f"dolores curiosidades debates de audiencia para video sobre {base} {language_hint}",
        ]
    elif intent == "shorts_hooks":
        queries = [
            f"hooks virales TikTok Shorts para tema {base} {market_hint} {language_hint}",
            f"frases virales preguntas cortas sobre {base} {language_hint}",
        ]
    elif intent == "evergreen":
        queries = [
            f"temas evergreen preguntas frecuentes video YouTube sobre {base} {language_hint}",
            f"ideas de contenido atemporal documental sobre {base} {market_hint} {language_hint}",
        ]
    else:
        queries = [
            f"tendencias actuales para video de YouTube sobre {base} {market_hint} {language_hint}",
            f"temas populares preguntas historias virales {base} {market_hint} {language_hint}",
        ]
    if example_hint:
        queries.append(f"ideas relacionadas con {example_hint} tendencia video documental {language_hint}")
    if category and category != "all":
        queries.append(f"{category} {name} tema actual video viral {language_hint}")
    return queries[: max(1, max_queries)]


def build_knowledge_queries(
    agent: dict,
    *,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    intent: str = DEFAULT_INTENT,
    max_queries: int = 2,
) -> list[str]:
    aid = agent_id(agent)
    intent = normalize_intent(intent)
    if aid == NEWS_AGENT_ID or intent == "news":
        return []
    if aid in PODCAST_AGENT_IDS:
        return PODCAST_KNOWLEDGE_QUERIES.get(intent, PODCAST_KNOWLEDGE_QUERIES["viral_topics"])[: max(1, max_queries)]

    name = agent_label(agent)
    description = str(agent.get("description") or "").strip()
    examples = agent.get("exampleTopics") or agent.get("examples") or []
    example_hint = " ".join(str(item) for item in examples[:2])
    agent_category = str(agent.get("category") or category or "general").strip().lower()
    category_hint = KNOWLEDGE_AGENT_HINTS.get(agent_category, agent_category)
    language_hint = "en espanol" if normalize_text(language) in {"es", "es-mx", "spanish", "espanol"} else f"en {language}"
    market_hint = "audiencia Mexico Latinoamerica" if normalize_text(market) in {"mx", "latam", "mexico"} else f"audiencia {market}"

    if intent == "audience_pain":
        queries = [
            f"problemas dudas preguntas audiencia {name} {description} {category_hint} {language_hint}",
            f"dolores conflictos objeciones curiosidades {name} {category_hint} {market_hint}",
        ]
    elif intent == "shorts_hooks":
        queries = [
            f"ideas breves paradojas mitos senales advertencias {name} {category_hint} {language_hint}",
            f"hooks frases fuertes lecciones contraintuitivas {name} {category_hint} {market_hint}",
        ]
    elif intent == "calendar_gaps":
        queries = [
            f"serie temas complementarios calendario editorial {name} {category_hint} {language_hint}",
            f"huecos contenido subtemas derivados {name} {description} {category_hint}",
        ]
    else:
        queries = [
            f"temas profundos video YouTube {name} {description} {category_hint} {language_hint}",
            f"ideas evergreen populares {name} {category_hint} {example_hint} {market_hint}",
        ]
    return [compact_text(query, 260) for query in queries if query.strip()][: max(1, max_queries)]


def estimate_radar_cost(
    agents: list[dict],
    *,
    query_limit: int = 2,
    intent: str = DEFAULT_INTENT,
    market: str = DEFAULT_MARKET,
    language: str = DEFAULT_LANGUAGE,
    category: str = DEFAULT_CATEGORY,
    search_depth: str = "basic",
    knowledge_enabled: bool = True,
    knowledge_query_limit: int | None = None,
) -> dict:
    safe_query_limit = max(1, min(5, int(query_limit or 1)))
    depth = normalize_text(search_depth or "basic")
    tavily_credits_per_query = 2 if depth == "advanced" else 1
    tavily_queries = 0
    knowledge_queries = 0
    per_agent = []
    for agent in agents or []:
        web_queries = build_agent_queries(
            agent,
            market=market,
            language=language,
            category=category,
            intent=intent,
            max_queries=safe_query_limit,
        )
        tavily_queries += len(web_queries)

        k_queries: list[str] = []
        if knowledge_enabled:
            k_limit = safe_query_limit if knowledge_query_limit is None else max(0, min(3, int(knowledge_query_limit or 0)))
            if k_limit:
                k_queries = build_knowledge_queries(
                    agent,
                    market=market,
                    language=language,
                    category=category,
                    intent=intent,
                    max_queries=k_limit,
                )
                knowledge_queries += len(k_queries)
        per_agent.append({
            "agentId": agent_id(agent),
            "agentName": agent_label(agent),
            "tavilyQueries": len(web_queries),
            "tavilyCredits": len(web_queries) * tavily_credits_per_query,
            "knowledgeQueries": len(k_queries),
            "embeddingQueries": len(k_queries),
        })
    tavily_credits = tavily_queries * tavily_credits_per_query
    return {
        "tavilyQueries": tavily_queries,
        "tavilyCredits": tavily_credits,
        "tavilyCreditsPerQuery": tavily_credits_per_query,
        "tavilySearchDepth": depth or "basic",
        "knowledgeQueries": knowledge_queries,
        "embeddingQueries": knowledge_queries,
        "notes": [
            "Buscar con cache valido no vuelve a gastar Tavily.",
            "Refrescar fuerza una corrida nueva.",
            "Cada busqueda interna usa un embedding de OpenAI para consultar Qdrant.",
        ],
        "perAgent": per_agent,
    }


def fallback_candidates_for_agent(agent: dict, *, limit: int = 3, intent: str = DEFAULT_INTENT) -> list[dict]:
    aid = agent_id(agent)
    name = agent_label(agent)
    description = compact_text(agent.get("description"), 180)
    examples = agent.get("exampleTopics") or agent.get("examples") or []
    intent = normalize_intent(intent)
    if aid in PODCAST_AGENT_IDS:
        seeds = PODCAST_FALLBACK_SEEDS.get(intent) or PODCAST_FALLBACK_SEEDS["viral_topics"]
    else:
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
                intent=intent,
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
    intent: str = DEFAULT_INTENT,
) -> list[dict]:
    response = response or {}
    intent = normalize_intent(intent)
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
                intent=intent,
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
                intent=intent,
                rank_seed=1,
            )
        )
    return candidates


def knowledge_results_to_candidates(
    agent: dict,
    query: str,
    response: dict | None,
    *,
    limit: int = 3,
    intent: str = DEFAULT_INTENT,
) -> list[dict]:
    response = response or {}
    intent = normalize_intent(intent)
    items = response.get("items") or response.get("results") or []
    if not items:
        return []

    candidates = []
    for index, item in enumerate(items[: max(1, limit)], 1):
        content = compact_text(item.get("content") or item.get("text") or "", 620)
        if not content:
            continue
        book_title = compact_text(item.get("title") or item.get("bookTitle") or "Biblioteca interna", 140)
        category = compact_text(item.get("category") or "General", 120)
        title = knowledge_candidate_title(agent, query, item, index=index)
        summary = knowledge_candidate_summary(agent, title, content, book_title, category)
        angle = knowledge_candidate_angle(agent, title, content)
        why_now = (
            "Senal encontrada en la base de conocimiento interna. "
            "Usala como inspiracion editorial, no como texto literal para el guion."
        )
        candidate = shape_candidate(
            agent=agent,
            title=title,
            summary=summary,
            angle=angle,
            why_now=why_now,
            sources=[],
            query=query,
            source_type="knowledge",
            intent=intent,
            rank_seed=100 + index,
        )
        candidate["knowledgeSignals"] = normalize_knowledge_signals([item])
        candidate["knowledgeQuery"] = compact_text(query, 260)
        candidate["knowledgeScore"] = safe_float(item.get("score"), 0.0)
        candidates.append(candidate)
    return candidates


def knowledge_candidate_title(agent: dict, query: str, item: dict, *, index: int = 1) -> str:
    aid = agent_id(agent)
    text = normalize_text(f"{query} {item.get('content') or item.get('text') or ''}")
    if aid in PODCAST_AGENT_IDS:
        if "visto" in text or "historias" in text:
            return "Me deja en visto pero sigue mirando mis historias"
        if "contacto cero" in text:
            return "Por que el contacto cero duele como abstinencia emocional"
        if "apego ansioso" in text:
            return "Cuando el apego ansioso convierte un mensaje en una prueba de amor"
        if "apego evitativo" in text:
            return "Por que te atrae alguien emocionalmente no disponible"
        if "limites" in text or "limite" in text:
            return "El limite que te cuesta poner porque todavia quieres que te elijan"
        if "breadcrumbing" in text or "validacion intermitente" in text:
            return "La migaja emocional que confundes con esperanza"
        if "limerencia" in text:
            return "Cuando no amas a la persona: amas la fantasia"
        if "duelo" in text or "ruptura" in text:
            return "El duelo invisible de soltar a quien todavia deseas"
    topic = clean_source_title(query)
    topic = re.sub(
        r"\b(temas|profundos|video|youtube|ideas|evergreen|populares|audiencia|mexico|latinoamerica|en espanol)\b",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\s+", " ", topic).strip(" .,:;")
    if not topic:
        topic = clean_source_title(item.get("title") or agent_label(agent))
    return compact_text(topic[:1].upper() + topic[1:], 160)


def knowledge_candidate_summary(agent: dict, title: str, content: str, book_title: str, category: str) -> str:
    aid = agent_id(agent)
    if aid in PODCAST_AGENT_IDS:
        return compact_text(
            f"Idea nacida de la biblioteca interna sobre relaciones: {content}",
            650,
        )
    return compact_text(
        f"Base interna ({category}, {book_title}): {content}",
        650,
    )


def knowledge_candidate_angle(agent: dict, title: str, content: str) -> str:
    aid = agent_id(agent)
    if aid in PODCAST_AGENT_IDS:
        return compact_text(f"{title}: una conversacion emocional con ejemplos reales, limites claros y cierre sanador", 240)
    if aid in {"agent_autohipnosis", "agent_meditacion_larga", "agent_tiktok_autohypnosis", "agent_tiktok_meditation"}:
        return compact_text(f"{title}: una experiencia segura de bienestar sin promesas medicas", 240)
    return compact_text(f"{title}: desarrollado con profundidad desde la biblioteca interna y convertido en historia", 240)


def normalize_knowledge_signals(items: list[dict], *, limit: int = 3) -> list[dict]:
    signals = []
    seen = set()
    for item in items[:limit]:
        title = compact_text(item.get("title") or item.get("bookTitle") or "Biblioteca interna", 140)
        category = compact_text(item.get("category") or "General", 120)
        excerpt = compact_text(item.get("content") or item.get("text") or "", 360)
        key = f"{title}|{excerpt[:80]}"
        if not excerpt or key in seen:
            continue
        seen.add(key)
        signals.append({
            "title": title,
            "category": category,
            "excerpt": excerpt,
            "score": safe_float(item.get("score"), 0.0),
        })
    return signals


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_angle(agent: dict, title: str, summary: str) -> str:
    aid = agent_id(agent)
    if aid == NEWS_AGENT_ID:
        return f"La historia detras de {title}: que paso, por que se volvio viral y que revela"
    if aid in PODCAST_AGENT_IDS:
        topic = clean_source_title(title)
        if is_podcast_brand_meta(topic, summary):
            topic = "un patron de apego que la audiencia esta viviendo"
        return f"{topic}: una conversacion sobre apego, limites, deseo y autoengano"
    if aid in {"agent_autohipnosis", "agent_meditacion_larga", "agent_tiktok_autohipnosis", "agent_tiktok_meditation"}:
        return f"{title}: una sesion segura, calmada y sin promesas medicas"
    return f"{title}: contado como una historia con contexto, giro y consecuencia"


def clean_source_title(title: str) -> str:
    text = compact_text(title, 150)
    for separator in (" | ", " - ", " – ", " — "):
        if separator in text:
            text = text.split(separator, 1)[0].strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,:;") or "Tema editorial"


def is_podcast_brand_meta(title: str, summary: str = "") -> bool:
    text = normalize_text(f"{title} {summary}")
    if "esto no es amor" not in text:
        return False
    return not any(
        term in text
        for term in [
            "apego",
            "ruptura",
            "contacto cero",
            "ghosting",
            "limites",
            "ansiedad",
            "dependencia",
            "relacion",
            "relaciones",
        ]
    )


def infer_recommended_format(agent: dict, title: str, summary: str) -> str:
    aid = agent_id(agent)
    lower = normalize_text(f"{title} {summary}")
    if str(agent.get("platform") or "").lower() == "tiktok" or aid.startswith("agent_tiktok_"):
        return "tiktok"
    if aid == "agent_podcast_general" and any(token in lower for token in ["tiktok", "shorts", "hook", "frase viral"]):
        return "both"
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
    podcast_terms = [
        "apego",
        "limites",
        "ruptura",
        "contacto cero",
        "ansiedad",
        "ghosting",
        "breadcrumbing",
        "limerencia",
        "dependencia",
        "ex",
        "duelo",
        "amor propio",
        "narcisismo",
        "validacion",
    ]
    audience += min(30, sum(1 for term in viral_terms if term in text) * 6)
    arc += min(25, sum(1 for term in ["porque", "detras", "consecuencia", "caida", "ascenso", "misterio"] if term in text) * 6)
    freshness += 25 if candidate.get("sourceType") in {"tavily", "tavily_answer"} else 0
    freshness += 10 if aid == NEWS_AGENT_ID else 0
    if candidate.get("sourceType") == "knowledge":
        fit += 12
        arc += 8
        ease += 5
    fit += 18 if normalize_text(agent_label(agent)).split(" ")[0] in text else 0
    fit += 20 if aid == NEWS_AGENT_ID and any(term in text for term in ["noticia", "viral", "redes", "polemica"]) else 0
    if aid == "agent_podcast_general":
        fit += min(30, sum(1 for term in podcast_terms if term in text) * 6)
        if is_podcast_brand_meta(candidate.get("title") or "", candidate.get("summary") or ""):
            audience -= 20
            fit -= 30
    if len(sources) >= 2:
        freshness += 10
        risk_score += 5
    if len(sources) == 0 and candidate.get("sourceType") not in {"fallback", "knowledge"}:
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
    intent: str = DEFAULT_INTENT,
    recommended_format: str | None = None,
    rank_seed: int = 0,
) -> dict:
    aid = agent_id(agent)
    intent = "news" if aid == NEWS_AGENT_ID else normalize_intent(intent)
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
        "intent": intent,
        "radarIntent": intent,
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
    apply_seo_metadata(candidate)
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


def apply_seo_metadata(candidate: dict) -> dict:
    seo_title = build_seo_title(candidate)
    keywords = build_seo_keywords(candidate)
    candidate["seoTitle"] = seo_title
    candidate["seoKeywords"] = keywords
    candidate["searchIntent"] = infer_search_intent(candidate)
    return candidate


def build_seo_title(candidate: dict, *, limit: int = 70) -> str:
    raw = clean_source_title(candidate.get("angle") or candidate.get("title") or "")
    aid = candidate.get("agentId") or ""
    text = normalize_text(raw)
    if aid in PODCAST_AGENT_IDS:
        if "contacto cero" in text and "apego" not in text:
            raw = f"{raw}: apego y contacto cero"
        elif "visto" in text and "apego" not in text:
            raw = f"{raw}: apego ansioso"
        elif "ex" in text and "ruptura" not in text:
            raw = f"{raw}: ruptura y amor propio"
        elif not any(term in text for term in ["apego", "ruptura", "contacto cero", "ghosting", "amor propio", "limites"]):
            raw = f"{raw}: relaciones y amor propio"
    elif candidate.get("agentId") == NEWS_AGENT_ID and "viral" not in text:
        raw = f"{raw}: noticia viral explicada"
    return compact_text(raw, limit)


def build_seo_keywords(candidate: dict, *, limit: int = 8) -> list[str]:
    text = normalize_text(" ".join([
        candidate.get("title") or "",
        candidate.get("angle") or "",
        candidate.get("summary") or "",
    ]))
    aid = candidate.get("agentId") or ""
    if aid in PODCAST_AGENT_IDS:
        vocabulary = [
            "apego ansioso",
            "apego evitativo",
            "contacto cero",
            "ghosting",
            "breadcrumbing",
            "dependencia emocional",
            "amor propio",
            "limites",
            "ruptura",
            "ex",
            "duelo amoroso",
            "validacion emocional",
        ]
    elif aid == NEWS_AGENT_ID:
        vocabulary = ["noticia viral", "tendencia", "redes sociales", "contexto", "que paso", "ultima hora", "debate"]
    else:
        vocabulary = [
            normalize_text(candidate.get("agentName") or "").strip(),
            normalize_text(candidate.get("category") or "").strip(),
            "documental",
            "historia",
            "explicado",
            "curiosidades",
            "youtube",
        ]
    matches = []
    for term in vocabulary:
        if term and term in text and term not in matches:
            matches.append(term)
    for token in re.findall(r"[a-záéíóúñ0-9]{4,}", text):
        if len(matches) >= limit:
            break
        if token not in matches and token not in {"para", "como", "porque", "desde", "sobre", "video"}:
            matches.append(token)
    return matches[:limit]


def infer_search_intent(candidate: dict) -> str:
    intent = normalize_intent(candidate.get("intent") or candidate.get("radarIntent"))
    if intent == "audience_pain":
        return "dolor de audiencia"
    if intent == "shorts_hooks":
        return "hook de descubrimiento"
    if intent == "evergreen":
        return "busqueda evergreen"
    if intent == "calendar_gaps":
        return "plan editorial"
    if intent == "news":
        return "actualidad"
    return "tema viral"


def build_title_lab(
    agent: dict,
    *,
    seed_topic: str = "",
    knowledge_signals: list[dict] | None = None,
    trend_signals: list[dict] | None = None,
    competitor_signals: list[dict] | None = None,
    seed_limit: int = 10,
    adjacent_limit: int = 5,
) -> dict:
    seed = compact_text(seed_topic, 120).strip()
    signals = normalize_knowledge_signals(knowledge_signals or [], limit=5)
    trend_options = title_lab_external_options(
        agent,
        trend_signals or [],
        seed_topic=seed,
        group="trend",
        limit=5,
    )
    competitor_options = title_lab_external_options(
        agent,
        competitor_signals or [],
        seed_topic=seed,
        group="competitor",
        limit=5,
    )
    seed_titles = title_lab_seed_titles(agent, seed, limit=seed_limit)
    adjacent_titles = title_lab_adjacent_titles(agent, seed, signals, limit=adjacent_limit)

    seed_options = [
        title_lab_option(agent, title, seed_topic=seed, group="seed", rank=index + 1, knowledge_signals=signals)
        for index, title in enumerate(seed_titles)
    ]
    adjacent_options = [
        title_lab_option(agent, title, seed_topic=seed, group="adjacent", rank=index + 1, knowledge_signals=signals)
        for index, title in enumerate(adjacent_titles)
    ]
    all_options = seed_options + adjacent_options + trend_options + competitor_options
    retention_ranking = rank_title_lab_retention(all_options)
    return {
        "agentId": agent_id(agent),
        "agentName": agent_label(agent),
        "seedTopic": seed,
        "groups": [
            {"id": "seed", "label": "Sobre tu idea", "items": seed_options},
            {"id": "adjacent", "label": "Ideas adicionales", "items": adjacent_options},
            {"id": "trend", "label": "Tendencias web", "items": trend_options},
            {"id": "competitor", "label": "Competidores YouTube", "items": competitor_options},
        ],
        "items": all_options,
        "retentionRanking": retention_ranking,
        "knowledgeSignals": signals,
        "trendSignals": trend_signals or [],
        "competitorSignals": competitor_signals or [],
    }


def title_lab_seed_titles(agent: dict, seed_topic: str, *, limit: int = 10) -> list[str]:
    seed = clean_seed_topic(seed_topic)
    aid = agent_id(agent)
    if not seed:
        if aid in PODCAST_AGENT_IDS:
            base = [
                "No extrañas a tu ex: extrañas la ansiedad que te daba",
                "La migaja emocional que te hace empezar de cero",
                "Por que confundes intensidad con amor",
                "Cuando te busca justo cuando ya estabas sanando",
                "El limite que te cuesta poner porque aun quieres que te elijan",
                "Si te da paz solo cuando aparece, no es paz",
                "La señal de que no era amor, era apego",
                "Por que sigues esperando un mensaje que ya sabes que no llega",
                "Cuando pedir claridad se siente como rogar amor",
                "La fantasia de cierre que nunca llega",
            ]
        else:
            name = agent_label(agent) or "este tema"
            base = [
                f"Lo que nadie esta explicando sobre {name}",
                f"La verdad incomoda detras de {name}",
                f"El error que cambia todo en {name}",
                f"Por que {name} importa mas de lo que parece",
                f"La historia oculta que convierte {name} en un gran video",
            ]
        return dedupe_title_strings(base)[:limit]

    if aid in PODCAST_AGENT_IDS:
        base = [
            f"{seed} no funciona si lo haces para que vuelva",
            f"La parte de {seed} que nadie te explica",
            f"Por que {seed} duele como abstinencia emocional",
            f"El error que arruina {seed} sin que te des cuenta",
            f"Cuando haces {seed} pero sigues revisando sus historias",
            f"{seed} no es castigo: es recuperar tu dignidad",
            f"Si rompiste {seed} por ansiedad, escucha esto antes de culparte",
            f"La verdad incomoda sobre {seed}",
            f"Lo que {seed} revela sobre tu apego",
            f"{seed}: cuando dejar de escribir se siente como perderlo todo",
            f"El lado de {seed} que solo entiendes cuando todavia duele",
            f"Antes de romper {seed}, escucha esto",
        ]
    else:
        base = [
            f"Lo que nadie esta explicando sobre {seed}",
            f"La verdad incomoda detras de {seed}",
            f"El error que cambia todo en {seed}",
            f"Por que {seed} importa mas de lo que parece",
            f"La historia oculta de {seed}",
            f"{seed}: explicado sin relleno y con contexto",
            f"El detalle de {seed} que casi todos pasan por alto",
            f"Antes de creer lo que dicen sobre {seed}, mira esto",
        ]
    return dedupe_title_strings(base)[:limit]


def title_lab_adjacent_titles(
    agent: dict,
    seed_topic: str,
    knowledge_signals: list[dict],
    *,
    limit: int = 5,
) -> list[str]:
    aid = agent_id(agent)
    seed = normalize_text(seed_topic)
    if aid in PODCAST_AGENT_IDS:
        pool = list(PODCAST_TITLE_ADJACENT_TOPICS)
        if "contacto cero" in seed:
            pool = [
                "Volvio cuando menos lo necesitabas: por que eso te confunde",
                "No extrañas a tu ex: extrañas la ansiedad que te daba",
                "La migaja emocional que te hace empezar de cero",
                "Por que quieres cerrar una historia que ya te cerro a ti",
                "Cuando dejar de esperar se siente como traicionar lo que sentias",
                "Si te busca despues del silencio, no siempre significa amor",
            ] + pool
        elif "ghosting" in seed or "visto" in seed:
            pool = [
                "Me dejo en visto pero ve mis historias: la trampa emocional",
                "Por que esperas una respuesta de quien ya te respondio con silencio",
                "La ansiedad de mirar el celular como si fuera una prueba de amor",
                "Si aparece y desaparece, esto es lo que esta entrenando en ti",
                "Cuando el silencio de alguien decide tu valor",
            ] + pool
        for signal in knowledge_signals:
            text = normalize_text(signal.get("excerpt") or "")
            if "apego ansioso" in text:
                pool.append("Cuando el apego ansioso convierte un mensaje en una prueba de amor")
            if "limite" in text or "limites" in text:
                pool.append("El limite que te cuesta poner porque todavia quieres que te elijan")
            if "duelo" in text:
                pool.append("El duelo invisible de soltar a quien todavia deseas")
    else:
        name = agent_label(agent) or "este nicho"
        pool = [
            f"Una idea fuerte para {name} que aun no estas explotando",
            f"El tema vecino de {name} con mas potencial narrativo",
            f"La pregunta que tu audiencia haria sobre {name}",
            f"El mito de {name} que merece un video completo",
            f"Un angulo inesperado para crecer en {name}",
        ]
    return dedupe_title_strings(pool)[:limit]


def title_lab_option(
    agent: dict,
    title: str,
    *,
    seed_topic: str,
    group: str,
    rank: int,
    knowledge_signals: list[dict] | None = None,
) -> dict:
    clean_title = compact_text(title, 110)
    scores = score_title_lab_option(agent, clean_title, seed_topic=seed_topic, group=group)
    option_id = candidate_hash(agent_id(agent), clean_title, f"title-lab-{group}")
    keywords = title_lab_keywords(agent, clean_title, seed_topic)
    return {
        "optionId": option_id,
        "candidateHash": option_id,
        "agentId": agent_id(agent),
        "agentName": agent_label(agent),
        "title": clean_title,
        "seoTitle": compact_text(clean_title, 70),
        "topic": seed_topic or clean_title,
        "group": group,
        "rank": rank,
        "hook": build_title_lab_hook(clean_title, agent),
        "angle": build_title_lab_angle(clean_title, agent, group),
        "seoKeywords": keywords,
        "scores": scores,
        "viralScore": scores["viral"],
        "seoScore": scores["seo"],
        "clickbaitScore": scores["clickbait"],
        "fitScore": scores["fit"],
        "retentionScore": scores["retention"],
        "overallScore": scores["overall"],
        "riskLevel": scores["riskLevel"],
        "riskReason": scores["riskReason"],
        "retentionReason": scores["retentionReason"],
        "recommendedFormat": "youtube_long",
        "knowledgeSignals": (knowledge_signals or [])[:3],
    }


def title_lab_external_options(
    agent: dict,
    signals: list[dict],
    *,
    seed_topic: str = "",
    group: str = "trend",
    limit: int = 5,
) -> list[dict]:
    options = []
    for signal in signals[:limit]:
        source_title = compact_text(signal.get("title") or signal.get("videoTitle") or signal.get("topic") or "", 120)
        if not source_title:
            continue
        remixed = remix_external_title(agent, source_title, seed_topic=seed_topic, group=group)
        option = title_lab_option(
            agent,
            remixed,
            seed_topic=seed_topic,
            group=group,
            rank=len(options) + 1,
            knowledge_signals=[],
        )
        option["inspiredBy"] = {
            "title": source_title,
            "channelTitle": signal.get("channelTitle") or "",
            "url": signal.get("url") or "",
            "views": signal.get("views") or 0,
            "viewsPerDay": signal.get("viewsPerDay") or 0,
            "publishedAt": signal.get("publishedAt") or "",
            "source": signal.get("source") or group,
        }
        boost_title_lab_option_from_signal(option, signal)
        options.append(option)
    return options


def remix_external_title(agent: dict, source_title: str, *, seed_topic: str = "", group: str = "trend") -> str:
    seed = clean_seed_topic(seed_topic)
    text = normalize_text(source_title)
    aid = agent_id(agent)
    if aid in PODCAST_AGENT_IDS:
        if seed and "contacto cero" in normalize_text(seed):
            if "error" in text:
                return "El error que arruina el contacto cero aunque parezca fuerza"
            if "no contact" in text or "contacto cero" in text:
                return "Contacto cero no funciona si lo haces desde la esperanza"
            return f"{seed}: la parte emocional que casi nadie te explica"
        if "ex" in text:
            return "No extrañas a tu ex: extrañas la ansiedad que te daba"
        if "silencio" in text or "visto" in text or "ghost" in text:
            return "Cuando el silencio de alguien decide tu valor"
        if seed:
            return f"{seed}: la verdad incomoda que tu audiencia si quiere escuchar"
        return "La verdad incomoda sobre amar desde la ansiedad"
    if seed:
        return f"{seed}: lo que esta tendencia revela de verdad"
    return f"{clean_source_title(source_title)}: explicado con un angulo nuevo"


def score_title_lab_option(agent: dict, title: str, *, seed_topic: str = "", group: str = "seed") -> dict:
    text = normalize_text(title)
    seed = normalize_text(seed_topic)
    aid = agent_id(agent)
    length = len(title)

    viral = 48
    seo = 45
    clickbait = 45
    fit = 55
    retention = 46
    risk_score = 92

    if any(word in text for word in TITLE_LAB_POWER_WORDS):
        viral += min(24, sum(1 for word in TITLE_LAB_POWER_WORDS if word in text) * 4)
        clickbait += min(24, sum(1 for word in TITLE_LAB_POWER_WORDS if word in text) * 4)
        retention += min(18, sum(1 for word in TITLE_LAB_POWER_WORDS if word in text) * 3)
    if "?" in title or text.startswith(("por que", "porque", "cuando", "si ")):
        viral += 8
        clickbait += 8
        retention += 9
    if ":" in title:
        seo += 6
        clickbait += 4
        retention += 5
    if 42 <= length <= 72:
        seo += 18
        retention += 12
    elif 30 <= length <= 90:
        seo += 10
        retention += 7
    else:
        seo -= 8
        retention -= 6
    if seed and seed in text:
        seo += 18
        fit += 12
        retention += 5
    if group == "adjacent":
        viral += 4
        seo -= 3
        retention += 3
    if group in {"trend", "competitor"}:
        viral += 4
        retention += 5
    if aid in PODCAST_AGENT_IDS:
        podcast_terms = [
            "apego",
            "ex",
            "ansiedad",
            "contacto cero",
            "historias",
            "dignidad",
            "amor",
            "limite",
            "limites",
            "extrañas",
            "extranas",
            "sanando",
        ]
        fit += min(30, sum(1 for term in podcast_terms if term in text) * 5)
        retention += min(22, sum(1 for term in podcast_terms if term in text) * 4)
        if any(term in text for term in ["no funciona", "nadie te explica", "antes de", "sigues", "vuelve", "duele"]):
            retention += 10
        if "cura" in text or "diagnostico" in text:
            risk_score -= 35
    if any(term in text for term in ["acusacion", "denuncia", "fraude", "cura", "milagro"]):
        risk_score -= 30
        retention -= 12

    viral = clamp_score(viral)
    seo = clamp_score(seo)
    clickbait = clamp_score(clickbait)
    fit = clamp_score(fit)
    retention = clamp_score(retention)
    risk_score = clamp_score(risk_score)
    overall = clamp_score(viral * 0.28 + seo * 0.20 + clickbait * 0.19 + fit * 0.18 + retention * 0.15)
    risk_level = "high" if risk_score < 45 else "medium" if risk_score < 75 else "low"
    retention_reason = title_lab_retention_reason(title, retention, group)
    return {
        "viral": viral,
        "seo": seo,
        "clickbait": clickbait,
        "fit": fit,
        "retention": retention,
        "risk": risk_score,
        "overall": overall,
        "riskLevel": risk_level,
        "riskReason": "Titulo seguro para exploracion editorial." if risk_level == "low" else "Revisar claims o sensibilidad antes de producir.",
        "retentionReason": retention_reason,
    }


def boost_title_lab_option_from_signal(option: dict, signal: dict) -> None:
    views_per_day = int(signal.get("viewsPerDay") or 0)
    views = int(signal.get("views") or 0)
    boost = 0
    if views_per_day >= 10000:
        boost = 12
    elif views_per_day >= 3000:
        boost = 9
    elif views_per_day >= 1000:
        boost = 6
    elif views >= 100000:
        boost = 4
    if boost <= 0:
        return
    scores = option.setdefault("scores", {})
    scores["retention"] = clamp_score((scores.get("retention") or option.get("retentionScore") or 0) + boost)
    scores["viral"] = clamp_score((scores.get("viral") or option.get("viralScore") or 0) + min(8, boost))
    scores["overall"] = clamp_score(
        scores.get("viral", 0) * 0.28
        + scores.get("seo", option.get("seoScore") or 0) * 0.20
        + scores.get("clickbait", option.get("clickbaitScore") or 0) * 0.19
        + scores.get("fit", option.get("fitScore") or 0) * 0.18
        + scores.get("retention", 0) * 0.15
    )
    scores["retentionReason"] = compact_text(
        f"Señal competitiva: {views_per_day:,} vistas/dia en el video fuente.".replace(",", "."),
        140,
    )
    option["viralScore"] = scores["viral"]
    option["retentionScore"] = scores["retention"]
    option["overallScore"] = scores["overall"]
    option["retentionReason"] = scores["retentionReason"]


def title_lab_retention_reason(title: str, score: int, group: str) -> str:
    text = normalize_text(title)
    reasons = []
    if text.startswith(("por que", "porque", "cuando", "si ", "antes de")):
        reasons.append("abre un loop de curiosidad desde la primera frase")
    if any(term in text for term in ["duele", "error", "verdad", "nadie", "incomoda", "ansiedad"]):
        reasons.append("promete tension emocional concreta")
    if ":" in title:
        reasons.append("combina tema SEO con giro editorial")
    if group in {"trend", "competitor"}:
        reasons.append("parte de una señal externa de demanda")
    if not reasons:
        reasons.append("tiene promesa clara y buen encaje con el nicho")
    prefix = "Alta retencion probable" if score >= 75 else "Retencion media" if score >= 58 else "Retencion por probar"
    return compact_text(f"{prefix}: {', '.join(reasons[:2])}.", 180)


def rank_title_lab_retention(options: list[dict], *, limit: int = 8) -> list[dict]:
    ranked = sorted(
        options,
        key=lambda item: (
            item.get("retentionScore") or 0,
            item.get("overallScore") or 0,
            item.get("viralScore") or 0,
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["retentionRank"] = index
    return [
        {
            "optionId": item.get("optionId"),
            "candidateHash": item.get("candidateHash"),
            "title": item.get("title"),
            "seoTitle": item.get("seoTitle"),
            "group": item.get("group"),
            "retentionScore": item.get("retentionScore") or 0,
            "overallScore": item.get("overallScore") or 0,
            "viralScore": item.get("viralScore") or 0,
            "retentionReason": item.get("retentionReason") or "",
        }
        for item in ranked[:limit]
    ]


def title_lab_keywords(agent: dict, title: str, seed_topic: str = "") -> list[str]:
    fake_candidate = {
        "agentId": agent_id(agent),
        "agentName": agent_label(agent),
        "category": agent.get("category") or "",
        "title": title,
        "angle": title,
        "summary": seed_topic,
    }
    return build_seo_keywords(fake_candidate, limit=8)


def build_title_lab_hook(title: str, agent: dict) -> str:
    if agent_id(agent) in PODCAST_AGENT_IDS:
        return compact_text(f"Si este titulo te incomoda, probablemente toca una parte de tu historia: {title}", 180)
    return compact_text(f"Hoy vamos a mirar {title} desde el angulo que casi nadie esta contando.", 180)


def build_title_lab_angle(title: str, agent: dict, group: str) -> str:
    if agent_id(agent) in PODCAST_AGENT_IDS:
        if group == "adjacent":
            return "Idea vecina del mismo nicho emocional, pensada para ampliar el calendario sin salir de la identidad del canal."
        return "Titulo diseñado para abrir una conversacion emocional, con tension, identificacion inmediata y cierre reflexivo."
    return "Titulo diseñado para funcionar como documental de YouTube con promesa clara, curiosidad y busqueda natural."


def clean_seed_topic(value: str) -> str:
    text = compact_text(value, 90).strip(" .,:;")
    return text[:1].upper() + text[1:] if text else ""


def dedupe_title_strings(titles: list[str]) -> list[str]:
    out = []
    seen = set()
    for title in titles:
        clean = compact_text(title, 120).strip()
        key = normalize_text(clean)
        if not clean or key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


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
        if llm_item.get("title"):
            candidate["title"] = compact_text(llm_item["title"], 180)
            candidate["headline"] = candidate["title"]
        if llm_item.get("summary"):
            candidate["summary"] = compact_text(llm_item["summary"], 650)
        if llm_item.get("whyNow"):
            candidate["whyNow"] = compact_text(llm_item["whyNow"], 420)
        if llm_item.get("angle"):
            candidate["angle"] = compact_text(llm_item["angle"], 240)
        if llm_item.get("riskLevel") in {"low", "medium", "high"}:
            candidate["riskLevel"] = llm_item["riskLevel"]
        if llm_item.get("riskReason"):
            candidate["riskReason"] = compact_text(llm_item["riskReason"], 260)
        if llm_item.get("recommendationReason"):
            candidate["recommendationReason"] = compact_text(llm_item["recommendationReason"], 260)
        apply_seo_metadata(candidate)
        ranked.append(candidate)
    remaining = sorted(by_hash.values(), key=lambda item: item.get("editorialScore", 0), reverse=True)
    for candidate in remaining:
        apply_seo_metadata(candidate)
    ranked.extend(remaining)
    return ranked


def build_ranking_prompt(candidates: list[dict], *, scope: str, intent: str = DEFAULT_INTENT) -> str:
    intent = normalize_intent(intent)
    compact = [
        {
            "candidateHash": c.get("candidateHash"),
            "agentId": c.get("agentId"),
            "title": c.get("title"),
            "summary": c.get("summary"),
            "angle": c.get("angle"),
            "intent": c.get("intent") or intent,
            "sources": [s.get("domain") or s.get("url") for s in c.get("sources", [])],
            "knowledgeSignals": [
                {
                    "book": s.get("title"),
                    "category": s.get("category"),
                    "excerpt": s.get("excerpt"),
                }
                for s in (c.get("knowledgeSignals") or [])[:3]
            ],
            "riskLevel": c.get("riskLevel"),
            "editorialScore": c.get("editorialScore"),
        }
        for c in candidates[:24]
    ]
    return (
        "Eres editor estrategico de Content Factory. Rankea estas ideas de video.\n"
        "Devuelve EXCLUSIVAMENTE JSON array. No markdown.\n"
        "Cada item debe conservar candidateHash e incluir: editorialScore 0-100, "
        "title, summary, angle, riskLevel low|medium|high, riskReason, recommendationReason.\n"
        "Reescribe title y angle en español latino como temas concretos, no como busquedas ni titulos SEO genericos.\n"
        "Si el agente es Esto no es amor o TikTok Podcast, NO propongas ideas sobre el nombre de la marca. "
        "Convierte cada resultado en un dolor, conflicto o pregunta real de audiencia sobre apego, ruptura, "
        "contacto cero, limites, amor propio, ghosting, ansiedad en relaciones o dependencia emocional.\n"
        "Para shorts_hooks, prioriza frases con punch emocional. Para audience_pain, prioriza situaciones que "
        "la audiencia diria en primera persona. Para evergreen, prioriza temas atemporales.\n"
        "Si hay knowledgeSignals, usalas solo para detectar temas, tensiones y profundidad; no copies frases largas "
        "ni conviertas el titulo del libro en el tema del video.\n"
        "Penaliza fuentes debiles, promesas medicas, acusaciones legales sin evidencia y sensacionalismo.\n"
        f"Scope: {scope}\n"
        f"Intent: {intent}\n"
        f"Candidatos:\n{json.dumps(compact, ensure_ascii=False)}"
    )

