from scripts.radar import (
    NEWS_AGENT_ID,
    apply_llm_ranking,
    build_agent_queries,
    build_knowledge_queries,
    build_news_queries,
    build_title_lab,
    cache_key,
    candidate_hash,
    canonical_title_key,
    dedupe_candidates,
    knowledge_results_to_candidates,
    parse_ranking_response,
    shape_candidate,
)


NEWS_AGENT = {
    "agentId": NEWS_AGENT_ID,
    "name": "Noticias Virales",
    "description": "Eventos actuales explicados con contexto",
    "category": "news",
    "promptFile": "agent_noticias_virales.md",
}


WELLNESS_AGENT = {
    "agentId": "agent_autohipnosis",
    "name": "Autohipnosis",
    "description": "Sesiones seguras de bienestar",
    "category": "wellness",
    "format": "autohipnosis",
    "promptFile": "agent_autohipnosis.md",
}


PODCAST_AGENT = {
    "agentId": "agent_podcast_general",
    "name": "Esto no es amor",
    "description": "Conversacion sobre apego, limites y amor propio",
    "category": "podcast",
    "format": "podcast",
    "promptFile": "agent_podcast_general.md",
}


def test_candidate_hash_uses_agent_title_and_source_domain():
    first = candidate_hash(NEWS_AGENT_ID, "La noticia viral", "https://example.com/a")
    second = candidate_hash(NEWS_AGENT_ID, "La noticia viral", "https://example.com/b")
    third = candidate_hash(NEWS_AGENT_ID, "La noticia viral", "https://other.com/a")

    assert first == second
    assert first != third


def test_build_news_queries_respects_category_and_limit():
    queries = build_news_queries(market="mx", category="politica", max_queries=5)

    assert len(queries) == 5
    assert any("politica" in query for query in queries)
    assert all("Mexico" in query or "Latinoamerica" in query for query in queries)


def test_build_agent_queries_delegates_news_agent():
    queries = build_agent_queries(NEWS_AGENT, market="mx", category="all", max_queries=2)

    assert len(queries) == 2
    assert "noticias virales" in queries[0]


def test_podcast_queries_search_topics_not_brand_name():
    queries = build_agent_queries(
        PODCAST_AGENT,
        market="mx",
        category="all",
        intent="audience_pain",
        max_queries=3,
    )
    combined = " ".join(queries).lower()

    assert len(queries) == 3
    assert "esto no es amor" not in combined
    assert "apego" in combined
    assert "contacto cero" in combined
    assert "audiencia" in combined or "preguntas" in combined


def test_podcast_knowledge_queries_search_internal_topics_not_brand_name():
    queries = build_knowledge_queries(
        PODCAST_AGENT,
        market="mx",
        category="all",
        intent="audience_pain",
        max_queries=3,
    )
    combined = " ".join(queries).lower()

    assert len(queries) == 3
    assert "esto no es amor" not in combined
    assert "apego" in combined
    assert "visto" in combined


def test_knowledge_results_create_internal_signals_without_external_sources():
    candidates = knowledge_results_to_candidates(
        PODCAST_AGENT,
        "me dejo en visto pero ve mis historias apego ansiedad validacion",
        {
            "items": [
                {
                    "title": "Libro de apego",
                    "category": "08_Psicologia_y_Emociones",
                    "content": "El apego ansioso puede convertir la espera de una respuesta en una prueba de valor personal.",
                    "score": 0.82,
                }
            ]
        },
        limit=2,
        intent="audience_pain",
    )

    assert len(candidates) == 1
    assert candidates[0]["sourceType"] == "knowledge"
    assert candidates[0]["sources"] == []
    assert candidates[0]["knowledgeSignals"][0]["title"] == "Libro de apego"
    assert candidates[0]["seoTitle"]
    assert "apego ansioso" in candidates[0]["seoKeywords"]
    assert "visto" in candidates[0]["title"].lower()


def test_title_lab_generates_seed_and_adjacent_titles():
    lab = build_title_lab(
        PODCAST_AGENT,
        seed_topic="contacto cero",
        knowledge_signals=[],
        seed_limit=5,
        adjacent_limit=5,
    )

    seed_items = lab["groups"][0]["items"]
    adjacent_items = lab["groups"][1]["items"]

    assert len(seed_items) == 5
    assert len(adjacent_items) == 5
    assert all(item["viralScore"] > 0 for item in seed_items)
    assert all(item["retentionScore"] > 0 for item in seed_items)
    assert lab["retentionRanking"]
    assert any("contacto cero" in item["title"].lower() for item in seed_items)
    assert any("ex" in item["title"].lower() or "sanando" in item["title"].lower() for item in adjacent_items)


def test_title_lab_without_seed_suggests_niche_titles():
    lab = build_title_lab(PODCAST_AGENT, seed_topic="", seed_limit=5, adjacent_limit=5)

    assert lab["items"]
    assert lab["seedTopic"] == ""
    assert lab["retentionRanking"][0]["retentionScore"] >= lab["retentionRanking"][-1]["retentionScore"]
    assert any("apego" in item["title"].lower() or "ex" in item["title"].lower() for item in lab["items"])


def test_title_lab_adds_trend_and_competitor_groups_without_copying_verbatim():
    lab = build_title_lab(
        PODCAST_AGENT,
        seed_topic="contacto cero",
        trend_signals=[{"title": "No contact rule mistakes", "url": "https://example.com/trend"}],
        competitor_signals=[
            {
                "videoTitle": "The biggest no contact mistake",
                "channelTitle": "Competitor",
                "url": "https://youtube.com/watch?v=x",
                "views": 120000,
                "viewsPerDay": 4000,
            }
        ],
        seed_limit=3,
        adjacent_limit=3,
    )

    by_group = {group["id"]: group for group in lab["groups"]}

    assert by_group["trend"]["items"]
    assert by_group["competitor"]["items"]
    assert all("contacto cero" in item["title"].lower() for item in by_group["competitor"]["items"])
    assert by_group["competitor"]["items"][0]["inspiredBy"]["channelTitle"] == "Competitor"


def test_news_candidate_with_single_source_requires_medium_risk():
    candidate = shape_candidate(
        agent=NEWS_AGENT,
        title="La polemica viral del dia",
        summary="Un tema viral con mucho debate en redes.",
        angle="La historia detras de la polemica viral",
        why_now="Esta circulando hoy.",
        sources=[{"title": "Fuente", "url": "https://example.com/story", "domain": "example.com"}],
        query="noticias virales hoy",
        source_type="tavily",
    )

    assert candidate["riskLevel"] == "medium"
    assert candidate["editorialScore"] > 0
    assert candidate["scores"]["freshness"] >= 70


def test_podcast_candidate_penalizes_brand_meta_topic():
    candidate = shape_candidate(
        agent=PODCAST_AGENT,
        title="Por que Esto no es amor es importante",
        summary="Un texto sobre el nombre de la marca sin un dolor real de audiencia.",
        angle="Meta",
        why_now="Fallback",
        sources=[],
        query="q",
        source_type="fallback",
        intent="viral_topics",
    )

    assert candidate["intent"] == "viral_topics"
    assert candidate["scores"]["fit"] < 60


def test_wellness_candidate_penalizes_medical_claims():
    candidate = shape_candidate(
        agent=WELLNESS_AGENT,
        title="Autohipnosis para curar ansiedad",
        summary="Promete cura y diagnostico rapido.",
        angle="Sesion segura",
        why_now="Fallback",
        sources=[],
        query="fallback",
        source_type="fallback",
    )

    assert candidate["riskLevel"] == "high"


def test_dedupe_candidates_filters_existing_titles_and_hashes():
    first = shape_candidate(
        agent=NEWS_AGENT,
        title="Tema viral repetido",
        summary="Resumen uno",
        angle="Angulo uno",
        why_now="Ahora",
        sources=[{"title": "Uno", "url": "https://one.com/a", "domain": "one.com"}],
        query="q",
        source_type="tavily",
        rank_seed=1,
    )
    duplicate_title = {
        **first,
        "candidateHash": candidate_hash(NEWS_AGENT_ID, "Tema viral repetido", "https://two.com/a"),
        "sources": [{"title": "Dos", "url": "https://two.com/a", "domain": "two.com"}],
    }
    other = shape_candidate(
        agent=NEWS_AGENT,
        title="Tema viral nuevo",
        summary="Resumen dos",
        angle="Angulo dos",
        why_now="Ahora",
        sources=[{"title": "Tres", "url": "https://three.com/a", "domain": "three.com"}],
        query="q",
        source_type="tavily",
        rank_seed=2,
    )

    deduped = dedupe_candidates(
        [first, duplicate_title, other],
        existing_title_keys={canonical_title_key(NEWS_AGENT_ID, first["title"])},
        limit=5,
    )

    assert [item["title"] for item in deduped] == [other["title"]]


def test_parse_and_apply_llm_ranking_json_fence():
    candidate = shape_candidate(
        agent=NEWS_AGENT,
        title="Tema viral",
        summary="Resumen",
        angle="Angulo original",
        why_now="Ahora",
        sources=[],
        query="q",
        source_type="fallback",
    )
    ranked = parse_ranking_response(
        '```json\n[{"candidateHash":"%s","editorialScore":91,"angle":"Angulo nuevo","riskLevel":"low"}]\n```'
        % candidate["candidateHash"]
    )
    result = apply_llm_ranking([candidate], ranked)

    assert result[0]["editorialScore"] == 91
    assert result[0]["angle"] == "Angulo nuevo"


def test_cache_key_changes_by_scope_agent_and_window():
    base = cache_key(scope="global", agent_id="all", market="mx", language="es", category="all", window="today")
    other = cache_key(scope="agent", agent_id=NEWS_AGENT_ID, market="mx", language="es", category="all", window="today")
    later = cache_key(scope="global", agent_id="all", market="mx", language="es", category="all", window="week")
    intent = cache_key(scope="global", agent_id="all", market="mx", language="es", category="all", window="today", intent="audience_pain")

    assert base != other
    assert base != later
    assert base != intent
