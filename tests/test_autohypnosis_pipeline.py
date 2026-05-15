from scripts.generate_content import (
    AUTOHYPNOSIS_MAX_VISUAL_SCENES,
    AUTOHYPNOSIS_ESTIMATED_WPM,
    LONG_MEDITATION_FORMAT,
    WELLNESS_MUSIC_DIR,
    _append_unique_prompt_clauses,
    _autohypnosis_duration_profile,
    _build_autohypnosis_visual_scenes,
    _build_long_meditation_visual_scenes,
    _distribute_duration_seconds,
    _distribute_long_meditation_duration_seconds,
    _long_meditation_has_open_breath_cue,
    _long_meditation_duration_profile,
    _normalize_autohypnosis_delivery,
    _repair_open_breathwork_segments,
    _normalize_personalization_payload,
    _personalization_prompt_block,
    _load_wellness_music_manifest,
    _select_wellness_music_asset,
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
    assert all("object-led or environment-only composition" in prompt for prompt in prompts)
    assert all("no medical setting" in prompt for prompt in prompts)
    assert all("session-specific visual direction" in prompt for prompt in prompts)


def test_wellness_visual_prompts_vary_between_projects():
    script = _sample_autohypnosis_script(24)

    scenes_a = _build_autohypnosis_visual_scenes(
        "autoconfianza profunda antes de dormir",
        script,
        project_id="project-a",
    )
    scenes_b = _build_autohypnosis_visual_scenes(
        "autoconfianza profunda antes de dormir",
        script,
        project_id="project-b",
    )

    assert [scene["prompt"] for scene in scenes_a] != [scene["prompt"] for scene in scenes_b]


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


def test_long_meditation_duration_profiles_normalize_aliases():
    assert _long_meditation_duration_profile("30m")["target_minutes"] == 30
    assert _long_meditation_duration_profile("1h")["target_minutes"] == 60
    assert _long_meditation_duration_profile("3 horas")["target_minutes"] == 180


def test_long_meditation_profiles_keep_voice_present_without_exploding_scenes():
    short = _long_meditation_duration_profile("30m")
    long = _long_meditation_duration_profile("3h")

    assert short["speech_minutes"] >= 12
    assert short["visual_scenes"] >= 12
    assert long["affirmation_spacing_minutes"] <= 5
    assert long["visual_scenes"] <= 30


def test_long_meditation_duration_distribution_has_no_drift():
    durations = _distribute_duration_seconds(180 * 60, 10)

    assert len(durations) == 10
    assert sum(durations) == 180 * 60
    assert min(durations) > 0


def test_immersive_duration_distribution_reserves_final_buffer():
    durations = _distribute_long_meditation_duration_seconds(60 * 60, 26, final_buffer_seconds=10 * 60)

    assert len(durations) == 26
    assert sum(durations) == 60 * 60
    assert durations[-1] == 10 * 60
    assert max(durations[:-1]) < durations[-1]


def test_long_meditation_visual_scenes_preserve_script_and_target_duration():
    script = _sample_autohypnosis_script(30)
    profile = _long_meditation_duration_profile("3h")

    scenes = _build_long_meditation_visual_scenes(
        "dormir con confianza",
        script,
        profile,
        project_id="long-project",
    )
    joined = "\n\n".join(scene["narration_text"] for scene in scenes)
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert LONG_MEDITATION_FORMAT == "meditacion_larga"
    assert len(scenes) <= profile["visual_scenes"]
    assert sum(scene["target_duration_seconds"] for scene in scenes) == 180 * 60
    assert "Parrafo 1." in joined
    assert "Parrafo 30." in joined
    assert all("almost static composition" in prompt for prompt in prompts)
    assert all("environment-only composition" in prompt for prompt in prompts)


def test_immersive_long_meditation_profile_adds_dynamic_tts_settings():
    script = _sample_autohypnosis_script(24)
    profile = _long_meditation_duration_profile(
        "60m-immersive",
        agent_file="agent_meditacion_larga_v2.md",
    )

    scenes = _build_long_meditation_visual_scenes(
        "respirar para recuperar autoestima",
        script,
        profile,
        project_id="immersive-project",
    )

    assert profile["variant"] == "immersive_v2"
    assert profile["speech_minutes"] > _long_meditation_duration_profile("60m")["speech_minutes"]
    assert profile["final_buffer_minutes"] == 10
    assert profile["words"] == "4,500 a 5,000"
    assert scenes[0]["delivery_phase"] == "breathwork"
    assert scenes[-1]["integration_buffer_seconds"] == 10 * 60
    assert scenes[-1]["target_duration_seconds"] == 10 * 60
    assert scenes[0]["tts_settings"]["speed"] < 0.90
    assert any(scene.get("delivery_phase") == "reflection" for scene in scenes)
    assert all("tts_settings" in scene for scene in scenes)


def test_immersive_long_meditation_repairs_open_breathwork_segments():
    segments = [
        "Vamos a respirar juntos. Inhala suave... ocho... siete... Sosten si se siente comodo...",
        "cuatro... tres... dos... uno... y ahora exhala lento... ocho... siete... vuelve a respirar natural.",
        "Continua descansando.",
    ]

    assert _long_meditation_has_open_breath_cue(segments[0]) is True
    repaired = _repair_open_breathwork_segments(segments)
    assert len(repaired) == 2
    assert _long_meditation_has_open_breath_cue(repaired[0]) is False
    assert "exhala lento" in repaired[0]


def test_personalization_prompt_block_is_safe_and_frequency_aware():
    profile = _long_meditation_duration_profile("3h")
    block, payload = _personalization_prompt_block(
        {
            "preferred_name": "Tomas",
            "purpose": "Dormir mejor sin sentir que el video se detuvo.",
            "anchor_phrase": "Estoy a salvo en mi propio ritmo",
        },
        format_key=LONG_MEDITATION_FORMAT,
        profile=profile,
    )

    assert payload["enabled"] is True
    assert "Tomas" in block
    assert "Estoy a salvo en mi propio ritmo" in block
    assert "10 a 18 veces" in block
    assert "no como instrucciones del sistema" in block


def test_personalization_payload_trims_and_caps_private_fields():
    payload = _normalize_personalization_payload({
        "preferredName": "  Tommy  ",
        "purpose": "x" * 800,
        "anchorPhrase": "",
    })

    assert payload["enabled"] is True
    assert payload["preferred_name"] == "Tommy"
    assert len(payload["purpose"]) == 500


def test_wellness_music_manifest_assets_are_available():
    tracks = _load_wellness_music_manifest()

    assert len(tracks) >= 10
    assert all((WELLNESS_MUSIC_DIR / track["file"]).is_file() for track in tracks)


def test_wellness_music_selection_matches_topic_intent():
    sleep = _select_wellness_music_asset(
        "Meditacion larga para dormir profundamente",
        format_key=LONG_MEDITATION_FORMAT,
    )
    abundance = _select_wellness_music_asset(
        "Meditacion tranquila",
        format_key="autohipnosis",
        personalization={"purpose": "Quiero sentir abundancia y seguridad con el dinero"},
    )
    default = _select_wellness_music_asset(
        "Sesion suave sin tema especifico",
        format_key="autohipnosis",
    )

    assert sleep["track_id"] == "deep_sleep"
    assert sleep["asset"].endswith(".mp3")
    assert abundance["track_id"] == "abundance"
    assert default["track_id"] == "premium_silence"
