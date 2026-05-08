from scripts.generate_content import (
    _build_podcast_visual_scenes,
    _build_tiktok_visual_scenes,
    _group_blocks_into_scenes,
    _tiktok_duration_profile,
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


def test_podcast_visual_prompts_are_object_led_and_text_safe():
    grouped = _group_blocks_into_scenes(
        _dialogue_blocks(30),
        target_scene_count=12,
        max_scene_count=15,
    )

    scenes = _build_podcast_visual_scenes("autoconfianza y disciplina", grouped)
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert scenes
    assert all("object-led" in prompt or "empty-room" in prompt for prompt in prompts)
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

    assert any("phone face down" in prompt for prompt in prompts)
    assert any("two chairs" in prompt for prompt in prompts)
    assert any("loose red thread" in prompt for prompt in prompts)
    assert any("empty mirror" in prompt for prompt in prompts)
    assert "attachment mistaken for love" in combined
    assert "esto no es amor" not in combined
    assert "symbolic object related to" not in combined
    assert "podcast mood" not in combined
    assert "listening chair" not in combined
    assert "studio environment" not in combined


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
        "no people",
        "no faces",
        "no hands",
        "no fingers",
        "no microphones",
        "no speakers",
        "no headphones",
        "no audio gear",
        "no podcast equipment",
        "no studio equipment",
        "no cameras",
        "no laptops",
        "no waveform graphics",
    ]
    for prompt in prompts:
        assert all(rule in prompt for rule in required_guardrails)


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
    assert all("no readable text" in prompt for prompt in prompts)
    assert all("no hands" in prompt for prompt in prompts)
    assert all("no faces" in prompt for prompt in prompts)
    assert all("no microphones" in prompt for prompt in prompts)
    assert all("no speakers" in prompt for prompt in prompts)
    assert all("no headphones" in prompt for prompt in prompts)
