from datetime import datetime, timezone

from scripts.source_video import (
    aggregate_collection_dna,
    agent_fit,
    build_fallback_analysis,
    build_project_topic,
    chunk_transcript,
    clean_transcript,
    draft_agent_payload_from_collection,
    derivation_prompt,
    normalize_adaptation,
    normalize_derivation,
    parse_youtube_url,
    project_intent_payload,
    route_source_video,
    similarity_guard,
    stable_source_video_id,
    transcript_hash,
)


def test_parse_youtube_url_common_shapes():
    assert parse_youtube_url("https://www.youtube.com/watch?v=ABCDEFGHI12") == "ABCDEFGHI12"
    assert parse_youtube_url("https://youtu.be/ABCDEFGHI12?si=test") == "ABCDEFGHI12"
    assert parse_youtube_url("https://www.youtube.com/shorts/ABCDEFGHI12") == "ABCDEFGHI12"
    assert parse_youtube_url("ABCDEFGHI12") == "ABCDEFGHI12"


def test_clean_and_chunk_transcript():
    raw = "[00:01] Hola mundo. 00:02 Este es un mensaje largo. " * 300
    clean = clean_transcript(raw)
    assert "[00:01]" not in clean
    assert "00:02" not in clean
    chunks = chunk_transcript(clean, max_chars=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 520 for chunk in chunks)


def test_transcript_hash_and_source_id_are_stable():
    assert transcript_hash(" Hola   mundo ") == transcript_hash("Hola mundo")
    assert stable_source_video_id("u1", "ABCDEFGHI12") == stable_source_video_id("u1", "ABCDEFGHI12")
    assert stable_source_video_id("u1", "ABCDEFGHI12") != stable_source_video_id("u2", "ABCDEFGHI12")


def test_similarity_guard_detects_repeated_phrases():
    source = "la vida te pide cambiar antes de estar listo y aceptar el proceso con humildad " * 6
    generated = "la vida te pide cambiar antes de estar listo y aceptar el proceso con humildad"
    report = similarity_guard(source, generated)
    assert report["risk"] in {"medium", "high"}
    assert report["matches"]


def test_fallback_analysis_and_project_topic_are_original_brief():
    metadata = {"title": "El mensaje que cambio mi vida", "channelName": "Canal Fuente"}
    transcript = (
        "A veces uno cree que necesita una respuesta inmediata. "
        "Pero el proceso real empieza cuando aceptas mirar tu historia con calma. "
    ) * 20
    analysis = build_fallback_analysis(metadata, transcript)
    derivation = normalize_derivation(None, analysis, metadata)
    topic = build_project_topic(derivation, analysis, metadata, selected_title="Cuando la vida te pide cambiar")
    assert "Brief original para podcast" in topic
    assert "No copiar frases literales" in topic
    assert "Cuando la vida te pide cambiar" in topic


def test_derivation_prompt_accepts_firestore_like_dates():
    analysis = {
        "centralThesis": "El miedo paraliza cuando la persona cree que esta sola.",
        "createdAt": datetime(2026, 5, 12, tzinfo=timezone.utc),
        "structureBeats": [{"order": 1, "label": "Hook", "purpose": "Abrir tension"}],
    }
    messages = derivation_prompt(analysis, {"title": "Video fuente"})
    assert "2026-05-12" in messages[1]["content"]
    assert "Object of type" not in messages[1]["content"]


def test_route_recommends_new_agent_for_explicit_spiritual_source_vs_esto_no_es_amor():
    analysis = {
        "centralThesis": "El miedo se vence confiando en Dios durante la tormenta.",
        "emotionalPromise": "Transformar miedo en fe y calma.",
        "spiritualReferences": ["Dios", "Cristo", "Mateo 8"],
        "audiencePainPoints": ["ansiedad", "perdida de control"],
        "themes": ["miedo", "control", "fe"],
    }
    esto_no_es_amor = {
        "agentId": "agent_podcast_general",
        "name": "Esto no es amor",
        "description": "Podcast emocional sobre apego, amor propio, limites y relaciones.",
        "format": "podcast",
    }
    fit = agent_fit(analysis, esto_no_es_amor)
    route = route_source_video(analysis, [esto_no_es_amor])
    assert fit["identityRisk"] in {"medium", "high"}
    assert route["recommendedAction"] == "create_agent"


def test_project_intent_payload_keeps_short_topic_and_internal_brief_separate():
    source = {"title": "Dante Gebel #345", "channelName": "Dante Gebel", "videoId": "ABCDEFGHI12"}
    analysis = build_fallback_analysis(source, "el miedo aparece cuando perdemos control " * 80)
    derivation = normalize_derivation(None, analysis, source)
    adaptation = {
        "visibleTitle": "Cuando el miedo a perder el control te hace confundir amor con refugio",
        "shortTopic": "Cuando el miedo a perder el control te hace confundir amor con refugio",
        "inspirationBrief": "Brief interno largo y util para el generador.",
        "adaptationRules": ["Transformar espiritualidad explicita en lenguaje emocional suave."],
    }
    intent = project_intent_payload(
        uid="u1",
        agent={"agentId": "agent_podcast_general", "name": "Esto no es amor", "promptFile": "agent_podcast_general.md"},
        source=source,
        analysis=analysis,
        derivation=derivation,
        adaptation=adaptation,
        source_video_id="sv1",
    )
    assert len(intent["shortTopic"]) <= 170
    assert intent["inspirationBrief"]["episodeBrief"] == adaptation["inspirationBrief"]
    assert intent["inspirationBrief"]["sourceChannel"] == "Dante Gebel"


def test_normalize_adaptation_reframes_spiritual_output_for_esto_no_es_amor():
    source = {"title": "Dante Gebel #345 | Por que tienes miedo", "channelName": "Dante Gebel"}
    analysis = {
        "centralThesis": "El miedo aparece cuando perdemos el control y buscamos a Cristo como Capitan.",
        "emotionalPromise": "Transformar miedo en fe.",
        "audiencePain": "ansiedad, control, miedo al abandono",
        "structureBeats": [{"order": 1, "label": "Tormenta", "purpose": "abrir miedo"}],
    }
    derivation = normalize_derivation(None, analysis, source)
    raw = {
        "visibleTitle": "Capitan de Capitanes: la noche que deje de tener miedo",
        "shortTopic": "Capitan de Capitanes",
        "inspirationBrief": "Cristo como capitan en la tormenta y exegesis biblica.",
    }
    out = normalize_adaptation(
        raw,
        analysis,
        derivation,
        source,
        {"agentId": "agent_podcast_general", "name": "Esto no es amor", "format": "podcast"},
    )
    lowered = (out["visibleTitle"] + " " + out["inspirationBrief"]).lower()
    assert "capitan" not in lowered
    assert "cristo" not in lowered
    assert "amor" in lowered or "control" in lowered


def test_collection_aggregate_can_seed_draft_agent_payload():
    sources = [{"title": "Video 1"}, {"title": "Video 2"}]
    analyses = [
        {
            "centralThesis": "El miedo baja cuando la persona encuentra proposito.",
            "emotionalPromise": "Pasar de ansiedad a claridad.",
            "spiritualReferences": ["Dios"],
            "themes": ["miedo", "proposito"],
            "metaphors": ["tormenta"],
        },
        {
            "centralThesis": "La fe suave ayuda a atravesar crisis.",
            "emotionalPromise": "Encontrar calma en medio de la presion.",
            "spiritualReferences": ["alma"],
            "themes": ["fe", "calma"],
            "retentionMoments": ["pregunta emocional inicial"],
        },
    ]
    aggregate = aggregate_collection_dna(sources, analyses)
    payload = draft_agent_payload_from_collection({"name": "Motivacion espiritual suave"}, aggregate)
    assert aggregate["sourceCount"] == 2
    assert aggregate["suggestedAgentTemplate"] == "podcast_two_hosts"
    assert payload["templateKey"] == "podcast_two_hosts"
    assert payload["brief"]["niche"]
