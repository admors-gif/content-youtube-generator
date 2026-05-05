from scripts.generate_content import (
    AUTOHYPNOSIS_MAX_VISUAL_SCENES,
    AUTOHYPNOSIS_ESTIMATED_WPM,
    _append_unique_prompt_clauses,
    _autohypnosis_duration_profile,
    _build_autohypnosis_visual_scenes,
    _normalize_autohypnosis_delivery,
    _split_text_into_balanced_segments,
)


def _sample_autohypnosis_script(paragraphs=18):
    return "\n\n".join(
        f"Parrafo {i + 1}. Respira con calma... Permite que tu cuerpo aprenda una nueva sensacion de seguridad interior."
        for i in range(paragraphs)
    )


def test_autohypnosis_delivery_removes_tts_bracket_tags():
    clean = _normalize_autohypnosis_delivery(
        "[calm] Respira profundamente...\n\n[pausa] Yo confio en mi proceso."
    )

    assert "[" not in clean
    assert "]" not in clean
    assert "Respira profundamente" in clean
    assert "Yo confio en mi proceso" in clean


def test_balanced_segments_preserve_full_autohypnosis_text():
    script = _sample_autohypnosis_script(18)
    segments = _split_text_into_balanced_segments(script, target_segments=12)

    joined = "\n\n".join(segments)

    assert len(segments) == 12
    assert "Parrafo 1." in joined
    assert "Parrafo 18." in joined
    assert joined.replace("\n\n", " ") == script.replace("\n\n", " ")


def test_autohypnosis_visual_scenes_are_capped_and_safe():
    script = _sample_autohypnosis_script(24)

    scenes = _build_autohypnosis_visual_scenes("autoconfianza profunda", script)
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert scenes
    assert len(scenes) <= AUTOHYPNOSIS_MAX_VISUAL_SCENES
    assert all(scene["narration_text"] for scene in scenes)
    assert all("no readable text" in prompt for prompt in prompts)
    assert all("hands outside frame" in prompt for prompt in prompts)
    assert all("no medical setting" in prompt for prompt in prompts)


def test_autohypnosis_prompt_clauses_are_not_duplicated():
    prompt = _append_unique_prompt_clauses(
        "Calm visual, no readable text, cinematic",
        ["no readable text", "no logos"],
    ).lower()

    assert prompt.count("no readable text") == 1
    assert "no logos" in prompt


def test_autohypnosis_duration_defaults_to_standard_profile():
    profile = _autohypnosis_duration_profile("Autoconfianza profunda antes de dormir")

    assert profile["target_minutes"] == 15
    assert AUTOHYPNOSIS_ESTIMATED_WPM == 155
