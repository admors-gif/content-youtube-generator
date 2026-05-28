from pathlib import Path

from scripts.generate_content import (
    YOUTUBE_SHORTS_DOCUMENTARY_FORMAT,
    YOUTUBE_SHORTS_PODCAST_FORMAT,
    _build_podcast_visual_scenes,
    _build_tiktok_visual_scenes,
    _create_claude_message_text,
    _emotion_prompt_file_for_format,
    _fallback_youtube_shorts_script,
    _group_blocks_into_scenes,
    _score_vertical_short_script,
    _normalize_vertical_script_text,
    _parse_podcast_script,
    _podcast_duration_profile,
    _youtube_shorts_quality_passed,
    _strip_podcast_model_preamble,
    _tiktok_duration_profile,
    _with_podcast_duration_profile,
)


def _dialogue_blocks(count=120):
    blocks = []
    for i in range(count):
        speaker = "A" if i % 2 == 0 else "B"
        name = "MATEO" if speaker == "A" else "LUCÍA"
        blocks.append({
            "speaker": speaker,
            "name": name,
            "text": f"Bloque {i + 1} con una idea clara para conservar el diálogo completo.",
        })
    return blocks


def test_podcast_dialogue_blocks_are_preserved_when_capped():
    blocks = _dialogue_blocks(120)

    scenes = _group_blocks_into_scenes(
        blocks,
        target_scene_count=12,
        max_scene_count=15,
    )

    preserved = []
    for scene in scenes:
        preserved.extend(scene["dialogue_blocks"])

    assert len(scenes) <= 15
    assert len(preserved) == len(blocks)
    assert [b["text"] for b in preserved] == [b["text"] for b in blocks]


def test_podcast_duration_profile_is_embedded_in_parent_payload():
    payload = _with_podcast_duration_profile(
        {"show_name": "Esto no es amor", "total_blocks": 12},
        {"key": "standard"},
    )

    assert payload["duration_profile"] == "standard"
    assert payload["show_name"] == "Esto no es amor"


def test_podcast_v2_long_defaults_to_long_profile():
    profile = _podcast_duration_profile("agent_podcast_general_v2_largo.md")

    assert profile["key"] == "long"
    assert profile["characters_min"] == 22000
    assert profile["characters_max"] == 26000
    assert profile["target_visual_scenes"] == 16


def test_roundtable_largo_alias_still_uses_extended_profile():
    profile = _podcast_duration_profile("agent_podcast_mesa_redonda.md", "largo")

    assert profile["key"] == "extended"


def test_claude_message_text_uses_streaming_when_requested():
    class FakeStream:
        text_stream = iter(["MATEO: Una idea.", "\nLUCIA: Otra idea."])

        def get_final_message(self):
            return None

    class FakeStreamManager:
        def __init__(self):
            self.stream = FakeStream()

        def __enter__(self):
            return self.stream

        def __exit__(self, *_args):
            return False

    class FakeMessages:
        def __init__(self):
            self.stream_called = False

        def stream(self, **_kwargs):
            self.stream_called = True
            return FakeStreamManager()

        def create(self, **_kwargs):
            raise AssertionError("non-streaming create should not be called")

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    client = FakeClient()
    text = _create_claude_message_text(
        client,
        use_stream=True,
        model="claude-test",
        max_tokens=22000,
        system="system",
        messages=[{"role": "user", "content": "tema"}],
    )

    assert client.messages.stream_called is True
    assert text == "MATEO: Una idea.\nLUCIA: Otra idea."


def test_podcast_visual_prompts_are_conceptual_and_text_safe():
    grouped = _group_blocks_into_scenes(
        _dialogue_blocks(30),
        target_scene_count=12,
        max_scene_count=15,
    )

    scenes = _build_podcast_visual_scenes("autoconfianza y disciplina", grouped)
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert scenes
    assert all("esto no es amor visual identity" in prompt for prompt in prompts)
    assert all("conceptual emotional cover" in prompt for prompt in prompts)
    assert all("one central symbolic metaphor" in prompt for prompt in prompts)
    assert all("16:9 horizontal" in prompt for prompt in prompts)
    assert all("no readable text" in prompt for prompt in prompts)
    assert not any("hands outside" in prompt for prompt in prompts)
    assert not any("fingers not visible" in prompt for prompt in prompts)
    assert not any("human hands near" in prompt for prompt in prompts)
    assert not any("face not visible" in prompt for prompt in prompts)


def test_esto_no_es_amor_prompts_use_channel_specific_relationship_motifs():
    grouped = _group_blocks_into_scenes(
        _dialogue_blocks(45),
        target_scene_count=12,
        max_scene_count=15,
    )

    scenes = _build_podcast_visual_scenes(
        "Esto no es amor, es apego: aprende a reconocer la diferencia",
        grouped,
    )
    prompts = [scene["prompt"].lower() for scene in scenes]
    combined = " ".join(prompts)

    assert any("glowing cracked heart" in prompt for prompt in prompts)
    assert any("crimson threads" in prompt for prompt in prompts)
    assert any("side-profile silhouette" in prompt for prompt in prompts)
    assert any("fractured emotional reflection" in prompt for prompt in prompts)
    assert "attachment mistaken for love" in combined
    assert "esto no es amor visual identity" in combined
    assert "symbolic object related to" not in combined
    assert "podcast mood" not in combined
    assert "listening chair" not in combined
    assert "studio environment" not in combined
    assert "phone face down" not in combined
    assert "coffee cups" not in combined
    assert "pair of shoes" not in combined
    assert "shoes separated" not in combined
    assert "door left slightly ajar" not in combined


def test_podcast_visual_prompts_block_audio_gear_people_and_generated_text():
    grouped = _group_blocks_into_scenes(
        _dialogue_blocks(30),
        target_scene_count=12,
        max_scene_count=15,
    )

    scenes = _build_podcast_visual_scenes(
        "Apego emocional y amor propio",
        grouped,
    )
    prompts = [scene["prompt"].lower() for scene in scenes]

    required_guardrails = [
        "no readable text",
        "no pseudo-text",
        "no visible hands",
        "no fingers",
        "no microphones",
        "no speakers",
        "no headphones",
        "no audio gear",
        "no podcast equipment",
        "no studio equipment",
        "no phones as main subject",
        "no cups",
        "no shoes",
        "no random hallway",
        "no random doors",
        "no detailed faces",
        "no realistic close-up faces",
    ]
    for prompt in prompts:
        assert all(rule in prompt for rule in required_guardrails)


def test_tiktok_podcast_prompt_requires_natural_brand_ctas():
    prompt = Path("prompts/agent_tiktok_podcast.md").read_text(encoding="utf-8").lower()

    assert "cta de marca" in prompt
    assert "parte organica de la conversacion" in prompt
    assert "guarda esto para cuando vuelvas a confundir ansiedad con amor" in prompt
    assert "comenta 'apego'" in prompt
    assert "mandaselo a alguien que necesita dejar de esperar un mensaje" in prompt


def test_tiktok_visual_prompts_are_vertical_and_safe():
    profile = _tiktok_duration_profile("90s")
    scenes = _build_tiktok_visual_scenes(
        "No extrañas a esa persona: extrañas cómo te hacía sentir",
        "LUCIA: No extrañas amor.\nMATEO: Extrañas una versión de ti esperando una señal.",
        profile,
        "tiktok_podcast",
        source_genre="psychology",
    )
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert 1 <= len(scenes) <= profile["visual_max"]
    assert all(scene["aspect_ratio"] == "9:16" for scene in scenes)
    assert all("vertical 9:16" in prompt for prompt in prompts)
    assert all("esto no es amor visual identity" in prompt for prompt in prompts)
    assert all("conceptual thumbnail-style cover image" in prompt for prompt in prompts)
    assert all("one clear focal metaphor" in prompt for prompt in prompts)
    assert all("not everything that feels intense is love" in prompt for prompt in prompts)
    assert all("no stretched objects" in prompt for prompt in prompts)
    assert all("no readable text" in prompt for prompt in prompts)
    assert all("no visible hands" in prompt for prompt in prompts)
    assert all("no detailed faces" in prompt for prompt in prompts)
    assert all("no microphones" in prompt for prompt in prompts)
    assert all("no speakers" in prompt for prompt in prompts)
    assert all("no headphones" in prompt for prompt in prompts)
    assert all("no phones as main subject" in prompt for prompt in prompts)
    assert all("no cups" in prompt for prompt in prompts)
    assert all("no shoes" in prompt for prompt in prompts)
    assert all("no tabletop product photography" in prompt for prompt in prompts)
    assert not any("phone face down" in prompt for prompt in prompts)


def test_youtube_shorts_profile_uses_five_vertical_scenes():
    profile = _tiktok_duration_profile("shorts75")
    scenes = _build_tiktok_visual_scenes(
        "Por que confundes ansiedad con amor",
        (
            "LUCIA: No era amor, era ansiedad pidiendo una respuesta.\n"
            "MATEO: Y si te quedas, te explico como se siente esa trampa por dentro."
        ),
        profile,
        YOUTUBE_SHORTS_PODCAST_FORMAT,
        source_genre="psychology",
    )
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert profile["target_seconds"] == 75
    assert len(scenes) == 5
    assert profile["word_min"] == 190
    assert profile["word_max"] == 220
    assert profile["word_hard_max"] == 240
    assert all(scene["platform"] == "youtube" for scene in scenes)
    assert all(scene["aspect_ratio"] == "9:16" for scene in scenes)
    assert all(scene.get("dialogue_blocks") for scene in scenes)
    assert not any("ceramic cups" in prompt for prompt in prompts)
    assert not any("door left slightly open" in prompt for prompt in prompts)
    assert not any("tiktok safe zones" in prompt for prompt in prompts)
    assert all("youtube shorts safe zones" in prompt for prompt in prompts)


def test_youtube_shorts_normalizes_list_script_and_keeps_five_scenes():
    profile = _tiktok_duration_profile("shorts75")
    raw_script = str([
        "LUCIA: Cuanto mas alguien te ignora, mas lo quieres. Por que pasa eso?",
        "MATEO: Porque no es amor lo que sientes. Es tu sistema nervioso buscando cerrar algo abierto.",
        "LUCIA: O sea, la obsesion no es por la persona.",
        "MATEO: Es por la herida que esa persona activo.",
        "LUCIA: Eso duele escucharlo.",
        "MATEO: Duele porque es verdad, pero tambien te devuelve poder.",
        "LUCIA: Entonces como sales de ese ciclo?",
        "MATEO: Reconociendo que persigues una sensacion aprendida.",
        "LUCIA: No estas persiguiendo a alguien.",
        "MATEO: Estas persiguiendo sentirte suficiente.",
        "LUCIA: Guarda esto para cuando confundas ansiedad con amor.",
    ])

    normalized = _normalize_vertical_script_text(raw_script)
    scenes = _build_tiktok_visual_scenes(
        "Por que te obsesionas con quien no te elige",
        raw_script,
        profile,
        YOUTUBE_SHORTS_PODCAST_FORMAT,
        source_genre="psychology",
    )

    assert normalized.startswith("LUCIA:")
    assert "['" not in normalized
    assert len(scenes) == 5
    assert all(scene.get("dialogue_blocks") for scene in scenes)


def test_youtube_shorts_uses_podcast_emotion_tagger():
    assert _emotion_prompt_file_for_format(False, YOUTUBE_SHORTS_PODCAST_FORMAT) == "emotion_tagger_podcast.md"
    assert _emotion_prompt_file_for_format(False, YOUTUBE_SHORTS_DOCUMENTARY_FORMAT) == "emotion_tagger.md"
    assert _emotion_prompt_file_for_format(False, "tiktok_documentary") == "emotion_tagger.md"


def test_youtube_shorts_quality_gate_matches_winning_structure():
    script = (
        "MATEO: Si su nombre en tus historias te dio esperanza, cuidado: eso no es amor. Es ansiedad disfrazada.\n"
        "LUCIA: Porque una persona puede mirarte todos los dias y aun asi no elegirte nunca.\n"
        "MATEO: Quedate, porque esto puede ahorrarte semanas de obsesion.\n"
        "LUCIA: Tu no estas esperando una vista. Estas esperando que esa vista signifique: todavia me quiere.\n"
        "MATEO: Pero cuando alguien tiene interes real, actua. Escribe. Propone. Se acerca.\n"
        "LUCIA: Cuando solo tiene curiosidad, consume tu vida desde lejos.\n"
        "MATEO: Y ahi aparece el apego. El rechazo se vuelve reto. La ausencia se vuelve promesa.\n"
        "LUCIA: No te engancho su amor. Te engancho la posibilidad.\n"
        "MATEO: Esa puerta entreabierta alimenta la herida: si ahora me elige, entonces si valgo.\n"
        "LUCIA: Pero tu autoestima no puede depender de alguien que solo mira y no hace nada.\n"
        "MATEO: No estas confundida porque sea profundo. Estas confundida porque duele.\n"
        "LUCIA: El amor no te deja analizando una pantalla para sentir paz.\n"
        "MATEO: Si tienes que adivinar, no es claridad. Si tienes que perseguir, no es cuidado.\n"
        "LUCIA: Suscribete. En este canal aprendemos a soltar las migajas antes de confundirlas con amor."
    )

    scores = _score_vertical_short_script(script, YOUTUBE_SHORTS_PODCAST_FORMAT)

    assert scores["overall"] >= 90
    assert scores["emotionScore"] >= 80
    assert scores["retentionScore"] >= 85
    assert _youtube_shorts_quality_passed(scores)


def test_youtube_documentary_shorts_quality_gate_uses_mystery_terms():
    script = _fallback_youtube_shorts_script(
        "El ultimo mensaje del vuelo MH370",
        YOUTUBE_SHORTS_DOCUMENTARY_FORMAT,
    )
    scores = _score_vertical_short_script(script, YOUTUBE_SHORTS_DOCUMENTARY_FORMAT)

    assert scores["overall"] >= 90
    assert scores["hookScore"] >= 85
    assert scores["emotionScore"] >= 80
    assert scores["retentionScore"] >= 85


def test_podcast_parser_ignores_model_preamble_and_leading_tags():
    tagged = (
        "Here is the complete script with the emotion tags inserted:\n\n"
        "[serious, authoritative] LUCIA: Te obsesionas con quien no te elige.\n"
        "MATEO: Exacto. No es sobre esa persona."
    )

    clean = _strip_podcast_model_preamble(tagged)
    blocks = _parse_podcast_script(clean)

    assert clean.startswith("[serious")
    assert len(blocks) == 2
    assert blocks[0]["name"] == "LUCIA"
    assert "Te obsesionas" in blocks[0]["text"]
