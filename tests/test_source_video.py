from datetime import datetime, timezone

from scripts.source_video import (
    build_fallback_analysis,
    build_project_topic,
    chunk_transcript,
    clean_transcript,
    derivation_prompt,
    normalize_derivation,
    parse_youtube_url,
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
