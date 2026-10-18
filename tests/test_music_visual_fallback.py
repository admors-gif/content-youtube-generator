"""Regression tests for the first real music render, with no paid API calls."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts import power_music_video as music


def approved_qa(**overrides):
    return {"enabled": True, "passed": True, "score": 95, "brandFit": 95, "storyRelevance": 95, "issues": [], **overrides}


@pytest.mark.parametrize("explanation", [
    "environment fits the story", "no anatomy issues", "no readable text", "appropriate human scale", "no logo or watermark",
])
def test_positive_or_negated_words_cannot_reject_an_approved_image(explanation):
    assert not music._vision_qa_failed(approved_qa(issues=[explanation]))


@pytest.mark.parametrize("flag", [
    "hasReadableText", "hasRandomDomesticObject", "hasUnauthorizedAthleticContent",
    "hasAnatomyDefect", "hasPhysicalInconsistency", "hasWatermark", "hasLogo", "hasUnrelatedContent",
])
def test_explicit_defect_flags_still_reject_high_scoring_images(flag):
    result = approved_qa(**{flag: True})
    assert music._vision_qa_failed(result)
    assert result["hardRejected"] is True


@pytest.mark.parametrize("code", ["readable_text", "anatomy_defect", "physical_inconsistency", "unrelated_content", "logo"])
def test_structured_defect_codes_still_reject(code):
    assert music._vision_qa_failed(approved_qa(hardIssueCodes=[code]))


@pytest.mark.parametrize("field", ["score", "brandFit", "storyRelevance"])
def test_low_scores_cannot_be_rescued_by_positive_explanations(field):
    assert music._vision_qa_failed(approved_qa(issues=["environment fits the story"], **{field: 30}))


def test_fallback_never_invents_slogans_or_draws_old_card(monkeypatch):
    for method in ("rounded_rectangle", "ellipse", "line"):
        monkeypatch.setattr(music.ImageDraw.ImageDraw, method, lambda *args, **kwargs: pytest.fail("The retired card shape was drawn"))
    monkeypatch.setattr(music.ImageDraw.ImageDraw, "text", lambda *args, **kwargs: pytest.fail("Unrequested text was drawn"))
    palette = music._palette({})
    plain = music._draw_music_visual_fallback_frame((320, 180), palette, "Song", {}, 17)
    old_quote = music._draw_music_visual_fallback_frame((320, 180), palette, "Song", {"fallbackQuote": "Mas rapido. Mas fuerte."}, 17)
    assert plain.tobytes() == old_quote.tobytes()
    assert plain.getextrema()[0][0] != plain.getextrema()[0][1]
    assert music._fallback_quote_pack({}) == []
    assert "Mas rapido. Mas fuerte." not in music._fallback_quote_pack({"lyrics": "Me doy otra oportunidad"})


def test_only_actual_enabled_lyrics_can_be_overlaid():
    beat = {"lyric": "Me doy otra oportunidad", "fallbackQuote": "Invented slogan"}
    assert music._fallback_overlay_text(beat) == ""
    assert music._fallback_overlay_text({**beat, "showFallbackLyricOverlay": True}) == beat["lyric"]
    assert music._fallback_overlay_text({**beat, "showLyricOverlay": True, "isInstrumentalGap": True}) == ""
    assert music._fallback_overlay_text({"overlay": "Invented slogan", "showLyricOverlay": True}) == ""


def test_fallback_pool_excludes_rejected_unapproved_and_same_scene_sources(tmp_path):
    rejected, safe, unchecked, same_scene = [tmp_path / name for name in ("bad.jpg", "safe.jpg", "unchecked.jpg", "same.jpg")]
    pool = [
        {"approved": True, "path": rejected, "scene_number": 1},
        {"approved": True, "path": safe, "scene_number": 3},
        {"approved": False, "path": unchecked, "scene_number": 4},
        {"approved": True, "path": same_scene, "scene_number": 2},
    ]
    selected = music._approved_music_fallback_candidates({"scene_number": 2}, pool, rejected_paths=[rejected])
    assert [item["path"] for item in selected] == [safe]


def test_fallback_avoids_adjacent_images_when_another_approved_source_exists(tmp_path):
    pool = [{"approved": True, "path": tmp_path / f"{index}.jpg", "scene_number": index, "section": "Chorus"} for index in (1, 3, 8)]
    candidates = music._approved_music_fallback_candidates({"scene_number": 2, "section": "Chorus"}, pool, avoid_paths=[pool[0]["path"], pool[1]["path"]])
    assert candidates[0]["scene_number"] == 8


@pytest.fixture
def offline_render(monkeypatch):
    events = []
    beats = [
        {"scene_number": index, "section": "Verse", "lyric": f"Original song line {index}", "prompt": "a coastal landscape", "storyMoment": "recovery", "shotRecipe": {}, "promptGate": {"passed": True}, "start": (index - 1) * 5, "end": index * 5, "duration": 5, "showLyricOverlay": True}
        for index in (1, 2, 3)
    ]

    def fake_run(command, **kwargs):
        events.append(("assembly", Path(command[-1]).name))
        Path(command[-1]).write_bytes(b"offline-video")

    def compose(source, target, palette, beat):
        events.append(("compose", Path(source).name, bool(beat.get("showLyricOverlay"))))
        Path(target).write_bytes(b"offline-frame" * 500)
        return True

    def generated(beats, directory):
        Path(directory).mkdir(parents=True, exist_ok=True)
        for beat in beats:
            (Path(directory) / f"scene_{beat['scene_number']:04d}.jpg").write_bytes(b"source" * 1000)
        return {"generated": len(beats), "availableScenes": [beat["scene_number"] for beat in beats], "error": ""}

    monkeypatch.setattr(music, "_prepare_music_story_for_render", lambda package, **kwargs: (package, {"source": "human", "fallback": False}))
    monkeypatch.setattr(music, "enrich_package_with_director_plan", lambda package: package)
    monkeypatch.setattr(music, "probe_audio_duration", lambda path: 15)
    monkeypatch.setattr(music, "_draw_frame", lambda *args, **kwargs: Image.new("RGB", (16, 16)))
    monkeypatch.setattr(music, "_build_music_thumbnail", lambda *args, **kwargs: "openai_test_exact_overlay")
    monkeypatch.setattr(music, "_build_whisper_subtitle_segments", lambda *args, **kwargs: ([], {"mode": "disabled"}))
    monkeypatch.setattr(music, "_build_visual_beats", lambda *args, **kwargs: (beats, 5))
    monkeypatch.setattr(music, "_run", fake_run)
    monkeypatch.setattr(music, "_compose_generated_frame", compose)
    monkeypatch.setattr(music, "_generate_openai_beat_images", generated)
    monkeypatch.setattr(music, "_build_power_music_shorts", lambda *args, **kwargs: [])
    monkeypatch.setattr(music, "_music_vision_qa_enabled", lambda: True)
    monkeypatch.setattr(music, "_regenerate_openai_beat_image", lambda *args: {"attempted": True, "success": False, "error": "offline"})
    monkeypatch.setenv("CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_REGEN_ATTEMPTS", "1")
    monkeypatch.setenv("CONTENT_FACTORY_MUSIC_FALLBACK_FRAME_MODE", "approved_song_image")
    return beats, events


def test_source_qa_precedes_overlays_and_early_rejection_can_use_a_future_approved_image(monkeypatch, tmp_path, offline_render):
    beats, events = offline_render

    def evaluate(path, beat):
        assert path.parent.name == "openai_images"
        assert not beat["showLyricOverlay"]
        events.append(("qa", path.name))
        return approved_qa(hasUnrelatedContent=path.name == "scene_0001.jpg")

    monkeypatch.setattr(music, "_evaluate_music_frame_with_openai_vision", evaluate)
    result = music.render_power_music_video("test", {"title": "Otra oportunidad"}, tmp_path / "audio.mp3", tmp_path)
    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    first = metadata["visualBeats"][0]
    assert first["renderSource"] == "approved_song_image"
    assert first["fallbackSourceScene"] == 3  # Scene 2 is the next shot; avoid immediate repetition.
    assert first["fallbackSourceFile"] == "scene_0003.jpg"
    assert first["needsVisualReview"] is True
    assert result["approvedVisualSources"] == 2
    assert result["approvedSongFallbackFrames"] == 1
    assert result["localFallbackFrames"] == 0
    assert result["generatedFrames"] == 2
    assert result["degradedOutput"] and result["visualReviewRequired"]
    assert result["fallbackDurationSeconds"] == 5
    assert result["visionQa"]["replacedFrames"] == 1
    assert all(item["evaluatedLayer"] == "source_image" for item in result["visionQa"]["results"])
    assert max(i for i, event in enumerate(events) if event[0] == "qa") < min(i for i, event in enumerate(events) if event[0] == "assembly")
    assert ("compose", "scene_0003.jpg", True) in events  # Authorized lyric added after QA.


def test_qa_errors_and_unchecked_sources_cannot_enter_approved_fallback_pool(monkeypatch, tmp_path, offline_render):
    monkeypatch.setattr(music, "_evaluate_music_frame_with_openai_vision", lambda *args: {"enabled": True, "passed": None, "error": "offline QA unavailable"})
    monkeypatch.setattr(music, "_music_vision_qa_max_frames", lambda: 1)
    result = music.render_power_music_video("test", {}, tmp_path / "audio.mp3", tmp_path)
    assert result["approvedVisualSources"] == 0
    assert result["generatedFrames"] == 3
    assert result["degradedOutput"] is True
    assert result["visionQa"]["checked"] == 1
    assert result["visualReviewRequired"] is True
    assert result["unreviewedSourceFrames"] == 3


@pytest.mark.parametrize("case", ["budget", "soft_accepted"])
def test_kept_sources_still_request_human_review_when_qa_is_incomplete_or_soft(monkeypatch, tmp_path, offline_render, case):
    monkeypatch.setattr(music, "_evaluate_music_frame_with_openai_vision", lambda *args: approved_qa(score=75) if case == "soft_accepted" else approved_qa())
    monkeypatch.setattr(music, "_music_vision_qa_max_frames", lambda: 1 if case == "budget" else 3)
    result = music.render_power_music_video("test", {}, tmp_path / "audio.mp3", tmp_path)
    assert result["generatedFrames"] == 3
    assert result["fallbackFrames"] == 0
    assert result["visualReviewRequired"] is True
    assert result["unreviewedSourceFrames"] == (2 if case == "budget" else 0)


@pytest.mark.parametrize("partial_score", ["score", "brandFit"])
def test_soft_accepted_image_stays_in_its_own_scene_but_cannot_replace_rejected_scenes(monkeypatch, tmp_path, offline_render, partial_score):
    def evaluate(path, beat):
        return approved_qa(**{partial_score: 75}) if path.name == "scene_0002.jpg" else approved_qa(hasUnrelatedContent=True)

    monkeypatch.setattr(music, "_evaluate_music_frame_with_openai_vision", evaluate)
    result = music.render_power_music_video("test", {}, tmp_path / "audio.mp3", tmp_path)
    metadata = json.loads(result["metadata"].read_text(encoding="utf-8"))
    assert result["approvedVisualSources"] == 0
    assert result["approvedSongFallbackFrames"] == 0
    assert result["generatedFrames"] == 1  # Preserve the existing soft-acceptance policy for its own shot.
    assert result["localFallbackFrames"] == 2
    assert [beat["renderSource"] for beat in metadata["visualBeats"]] == ["local_fallback", "openai_images", "local_fallback"]
    assert result["visionQa"]["softAccepted"] == 1
    assert result["visualReviewRequired"] is True


def insert_context(shot_type="abstract", *, human_policy=None, subject=None):
    continuity = {"protagonist": "Mother and daughter", "wardrobe": "blue coats", "locations": ["a coastal railway station"], "visualLanguage": "warm light over weathered blue surfaces"}
    brief = {"premise": "Mother and daughter embrace after years apart", "explicitVisualDirection": "Mother and daughter embrace", "continuity": continuity, "athleticStory": False}
    recipe = {
        "shotType": shot_type, "visualTreatment": "hybrid", "visualFunction": "an emotional pause expressed through light and texture",
        "subject": subject or "amber reflections on blue glass", "action": "let a warm reflection flow across weathered glass", "location": "a coastal railway station",
        "humanPolicy": human_policy or "no visible people, faces or bodies", "wardrobe": "blue coats", "storyEmotion": "relief and reconnection",
        "authoredAction": "Mother and daughter embrace", "storyPremise": brief["premise"], "lyricMetaphor": "Mother and daughter embrace", "continuity": continuity,
    }
    beat = {"section": "Chorus", "lyric": "I let the distance go", "storyMoment": "Mother and daughter embrace", "storyBrief": brief, "shotRecipe": recipe}
    return {"musicVideoDirector": {"storyBrief": brief, "continuity": continuity}}, beat


@pytest.mark.parametrize("shot_type", ["abstract", "environment"])
def test_final_insert_prompt_cannot_reintroduce_offscreen_cast_or_human_plot_action(shot_type):
    package, beat = insert_context(shot_type)
    prompt = music._build_music_visual_prompt(package, beat, {}, music._palette(package))
    assert "Mother and daughter" not in prompt
    assert "blue coats" not in prompt
    assert "embrace" not in prompt
    assert "warm reflection flow" in prompt
    assert "coastal railway station" in prompt
    assert "Do not illustrate the off-screen human plot action literally" in prompt
    repaired = music._qa_repair_prompt(prompt, {"issues": ["watermark"]}, beat, 1)
    assert "Mother and daughter" not in repaired
    assert "blue coats" not in repaired
    assert "embrace" not in repaired
    assert "preserving its shotType" in repaired


def test_authored_hand_detail_keeps_its_human_policy_without_forcing_the_whole_cast():
    package, beat = insert_context("detail", human_policy="only the mother's hands are visible; no full bodies", subject="the mother's hands touching weathered glass")
    prompt = music._build_music_visual_prompt(package, beat, {}, music._palette(package))
    assert "only the mother's hands are visible" in prompt
    assert "the mother's hands touching weathered glass" in prompt
    assert "no visible people, faces or bodies" not in prompt
    assert "Mother and daughter embrace" not in prompt


def test_critic_context_grades_insert_emotion_material_and_location_instead_of_cast(monkeypatch, tmp_path):
    sent = []

    def create(**kwargs):
        sent.append(kwargs["messages"][0]["content"][0]["text"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(approved_qa())))])

    monkeypatch.setattr(music, "_music_vision_qa_enabled", lambda: True)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))))
    image = tmp_path / "source.jpg"
    Image.new("RGB", (16, 16)).save(image)
    _, beat = insert_context()
    assert not music._vision_qa_failed(music._evaluate_music_frame_with_openai_vision(image, beat))
    prompt = sent[0]
    assert "Mother and daughter" not in prompt
    assert "blue coats" not in prompt
    assert "embrace" not in prompt
    assert '"shotType": "abstract"' in prompt
    assert "warm reflection flow" in prompt
    assert "judge emotion, materials, location, light and shotType" in prompt
    assert "an authored hand detail or optional distant silhouette is allowed" in prompt
    assert "hasLogo boolean" in prompt
