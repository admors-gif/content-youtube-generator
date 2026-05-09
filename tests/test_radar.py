from scripts.radar import (
    NEWS_AGENT_ID,
    apply_llm_ranking,
    build_agent_queries,
    build_news_queries,
    cache_key,
    candidate_hash,
    canonical_title_key,
    dedupe_candidates,
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

    assert base != other
    assert base != later
