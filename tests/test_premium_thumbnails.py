from pathlib import Path

import api


def test_attraction_thumbnail_plans_are_clickable_and_text_safe():
    title = "La ciencia detrás de la atracción que nadie te explicó"

    plans = api._thumbnail_hook_plans(title, agent_id="agent_podcast_general")
    prompt = api._build_premium_thumbnail_prompt(title, plans[0], agent_id="agent_podcast_general")

    assert len(plans) == 3
    assert plans[0]["hook"] == "TU CEREBRO\nYA ELIGIÓ"
    assert all(len(plan["hook"].splitlines()) <= 3 for plan in plans)
    assert "No generated text" in prompt
    assert "No visible hands or fingers" in prompt
    assert "TU CEREBRO" not in prompt


def test_generation_size_uses_exact_thumbnail_ratio_for_latest_image_model():
    assert api._thumbnail_generation_size("gpt-image-2") == "1280x720"
    assert api._thumbnail_generation_size("gpt-image-1") == "1536x1024"


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

    assert plans[0]["hook"] == "REPROGRAMA\nTU MENTE"
    assert "guided self-hypnosis thumbnail" in prompt
    assert "No generated text" in prompt
    assert "medical claims" in prompt
    assert "REPROGRAMA" not in prompt


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
