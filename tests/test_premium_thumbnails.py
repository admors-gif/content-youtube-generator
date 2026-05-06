from pathlib import Path

import api


def test_attraction_thumbnail_plans_are_clickable_and_text_safe():
    title = "La ciencia detrás de la atracción que nadie te explicó"

    plans = api._thumbnail_hook_plans(title, agent_id="agent_podcast_general")
    prompt = api._build_premium_thumbnail_prompt(title, plans[0], agent_id="agent_podcast_general")

    assert len(plans) == 3
    assert plans[0]["hook"] == "TU CEREBRO\nYA ELIGIÓ"
    assert all(len(plan["hook"].splitlines()) <= 3 for plan in plans)
    assert "Main headline text to render exactly, large and crisp, on separate lines" in prompt
    assert 'Line 1: "TU CEREBRO"' in prompt
    assert 'Line 2: "YA ELIGIÓ"' in prompt
    assert "slashes" in prompt
    assert "The thumbnail must already include the headline text" in prompt
    assert "No visible hands or fingers" in prompt
    assert "TU CEREBRO" in prompt


def test_esto_no_es_amor_thumbnail_plans_are_object_led_and_channel_specific():
    title = "Esto no es amor, es apego: aprende a reconocer la diferencia"

    plans = api._thumbnail_hook_plans(title, agent_id="agent_podcast_general")
    prompt = api._build_premium_thumbnail_prompt(title, plans[0], agent_id="agent_podcast_general")

    assert len(plans) == 3
    assert plans[0]["hook"] == "NO ES AMOR\nES APEGO"
    assert plans[1]["hook"] == "DEJA DE\nPERSEGUIR"
    assert plans[2]["hook"] == "ELIGE\nTU PAZ"
    assert all(plan.get("avoid_people") is True for plan in plans)
    assert all("microphone" not in plan["concept"] for plan in plans)
    assert all("speaker" not in plan["concept"] for plan in plans)
    assert all("headphone" not in plan["concept"] for plan in plans)
    assert "phone face down" in prompt
    assert "No people, no faces, no silhouettes" in prompt
    assert "no microphones" in prompt
    assert "no speakers" in prompt
    assert "no headphones" in prompt
    assert "Faces must be realistic" not in prompt
    assert "cinematic podcast set with a microphone" not in prompt


def test_generation_size_uses_landscape_size_for_latest_image_models():
    assert api._thumbnail_generation_size("gpt-image-1.5") == "1536x1024"
    assert api._thumbnail_generation_size("gpt-image-1") == "1536x1024"
    assert api._thumbnail_generation_size("chatgpt-image-latest") == "1536x1024"


def test_thumbnail_model_normalizes_unsupported_media_models(monkeypatch):
    monkeypatch.setenv("CONTENT_FACTORY_PREMIUM_THUMBNAIL_MODEL", "gpt-image-2")
    assert api._thumbnail_model() == "gpt-image-1.5"

    monkeypatch.setenv("CONTENT_FACTORY_PREMIUM_THUMBNAIL_MODEL", "sora-2")
    assert api._thumbnail_model() == "gpt-image-1.5"


def test_autohypnosis_thumbnail_plan_avoids_medical_claims_and_generated_text():
    plans = api._thumbnail_hook_plans(
        "Autohipnosis para autoconfianza profunda",
        agent_id="agent_autohipnosis",
    )
    prompt = api._build_premium_thumbnail_prompt(
        "Autohipnosis para autoconfianza profunda",
        plans[0],
        agent_id="agent_autohipnosis",
    )

    assert plans[0]["hook"] == "CONFÍA\nEN TI"
    assert "guided meditation thumbnail" in prompt
    assert 'Line 1: "CONFÍA"' in prompt
    assert 'Line 2: "EN TI"' in prompt
    assert 'Do not render the format badge text "MEDITACIÓN GUIADA"' in prompt
    assert "Reserve the top-right corner" in prompt
    assert "medical claims" in prompt
    assert "CONFÍA" in prompt


def test_wellness_thumbnail_plans_change_with_topic_intent():
    confidence = api._thumbnail_hook_plans(
        "Autohipnosis para autoconfianza profunda",
        agent_id="agent_autohipnosis",
    )
    sleep = api._thumbnail_hook_plans(
        "Meditación larga para dormir profundamente",
        agent_id="agent_meditacion_larga",
    )
    abundance = api._thumbnail_hook_plans(
        "Afirmaciones espaciadas para abundancia tranquila",
        agent_id="agent_meditacion_larga",
    )

    assert confidence[0]["hook"] == "CONFÍA\nEN TI"
    assert sleep[0]["hook"] == "DUERME\nPROFUNDO"
    assert abundance[0]["hook"] == "MENTE\nABIERTA"
    assert {p["variant"] for p in confidence} != {p["variant"] for p in sleep}


def test_autohypnosis_badge_is_always_guided_meditation():
    assert api._thumbnail_format_badge("agent_autohipnosis") == "MEDITACIÓN GUIADA"
    assert api._thumbnail_format_badge("agent_podcast_general") == "PODCAST"
    assert api._thumbnail_format_badge("agent_ciencia") is None


def test_premium_thumbnail_renderer_outputs_valid_jpeg(tmp_path):
    from PIL import Image, ImageDraw

    base = tmp_path / "base.png"
    out = tmp_path / "thumb.jpg"
    img = Image.new("RGB", (1280, 720), (8, 12, 18))
    draw = ImageDraw.Draw(img)
    draw.ellipse((110, 90, 420, 400), fill=(20, 120, 180))
    draw.ellipse((860, 90, 1170, 400), fill=(180, 40, 55))
    draw.rectangle((0, 420, 1280, 720), fill=(14, 14, 18))
    img.save(base)

    ok = api._render_premium_thumbnail(
        Path(base),
        "CIENCIA\nDE LA ATRACCIÓN",
        Path(out),
        variant="impacto",
        badge="PODCAST",
    )

    assert ok is True
    assert out.exists()
    assert out.stat().st_size > 10_000


def test_generated_thumbnail_finalize_outputs_youtube_jpeg(tmp_path):
    from PIL import Image, ImageDraw

    raw = tmp_path / "raw.jpg"
    out = tmp_path / "final.jpg"
    img = Image.new("RGB", (1536, 1024), (12, 10, 30))
    draw = ImageDraw.Draw(img)
    draw.rectangle((120, 220, 1416, 804), fill=(30, 18, 80))
    draw.text((430, 460), "CONFÍA EN TI", fill=(255, 255, 255))
    img.save(raw)

    ok = api._finalize_generated_thumbnail(Path(raw), Path(out), badge="MEDITACIÓN GUIADA")

    assert ok is True
    assert out.exists()
    assert Image.open(out).size == (1280, 720)


def test_generated_thumbnail_canvas_preserves_full_portrait_safe_area():
    from PIL import Image

    img = Image.new("RGB", (1536, 1024), (12, 10, 30))
    canvas = api._fit_generated_thumbnail_canvas(img)

    assert canvas.size == (1280, 720)
