import json
import shutil
from pathlib import Path

from scripts import factory
from scripts.factory import validate_image_assets


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", content=b""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = content

    def json(self):
        return self._payload


def test_validate_image_assets_requires_exact_scene_filenames(tmp_path):
    scenes = [
        {"scene_number": 1},
        {"scene_number": 2},
    ]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    (images_dir / "scene_0001.png").write_bytes(b"x" * 6000)
    (images_dir / "scene_0002.copied_neighbor.bak.png").write_bytes(b"x" * 6000)

    result = validate_image_assets(scenes, images_dir)

    assert result["ready"] == [1]
    assert result["missing"] == [2]
    assert result["invalid"] == []


def test_validate_image_assets_rejects_tiny_scene_file(tmp_path):
    scenes = [{"scene_number": 1}]
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    (images_dir / "scene_0001.png").write_bytes(b"tiny")

    result = validate_image_assets(scenes, images_dir)

    assert result["ready"] == []
    assert result["missing"] == []
    assert result["invalid"] == [1]


def test_autohypnosis_music_is_disabled_without_explicit_asset():
    result = factory._get_autohypnosis_music_config({
        "format": "autohipnosis",
        "autohipnosis": {},
    })

    assert result == {"enabled": False}


def test_autohypnosis_music_resolves_only_curated_assets(tmp_path, monkeypatch):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    track = music_dir / "sleep.mp3"
    track.write_bytes(b"fake-audio")
    monkeypatch.setattr(factory, "AUTOHYPNOSIS_MUSIC_DIR", music_dir)

    result = factory._get_autohypnosis_music_config({
        "format": "autohipnosis",
        "autohipnosis": {
            "background_music": {
                "enabled": True,
                "asset": "../sleep.mp3",
                "volume_db": -12,
            },
        },
    })

    assert result["enabled"] is True
    assert result["asset"] == track.resolve()
    assert result["volume_db"] == -16.0


def test_curated_wellness_music_asset_resolves_from_repo():
    result = factory._get_autohypnosis_music_config({
        "format": "autohipnosis",
        "autohipnosis": {
            "background_music": {
                "enabled": True,
                "asset": "blue_room_deep_sleep.mp3",
                "volume_db": -22,
            },
        },
    })

    assert result["enabled"] is True
    assert result["asset"].name == "blue_room_deep_sleep.mp3"
    assert result["asset"].is_file()
    assert result["volume_db"] == -22.0


def test_long_meditation_music_uses_procedural_fallback_without_asset():
    result = factory._get_autohypnosis_music_config({
        "format": "meditacion_larga",
        "longMeditation": {
            "background_music": {
                "enabled": True,
                "asset": None,
                "volume_db": -30,
                "procedural_fallback": True,
            },
        },
    })

    assert result["enabled"] is True
    assert result["procedural"] is True
    assert result["volume_db"] == -30.0


def test_long_meditation_target_duration_for_scene_prefers_explicit_value():
    scene = {"target_duration_seconds": 1800}

    assert factory._target_duration_for_scene(scene, fallback_duration=5) == 1800
    assert factory._target_duration_for_scene({}, fallback_duration=7) == 7


def test_output_folder_uses_project_id_when_available():
    folder_a = factory._resolve_output_folder({
        "topic": "Autoconfianza profunda antes de dormir",
        "project_id": "abc123",
    })
    folder_b = factory._resolve_output_folder({
        "topic": "Autoconfianza profunda antes de dormir",
        "project_id": "xyz789",
    })

    assert folder_a != folder_b
    assert folder_a.endswith("__abc123")
    assert folder_b.endswith("__xyz789")


def test_output_folder_keeps_legacy_title_without_project_id():
    folder = factory._resolve_output_folder({
        "topic": "Autoconfianza profunda antes de dormir",
    })

    assert folder == "Autoconfianza_profunda_antes_de_dormir"


def test_explicit_output_folder_cannot_escape_project_directory():
    folder = factory._resolve_output_folder({
        "topic": "Autoconfianza",
        "output_folder": "../evil/final",
    })

    assert folder == "final"


def test_image_workflow_router_preserves_documentary_flux_path():
    documentary = factory._select_image_workflow("narrativa")
    cinematic = factory._select_image_workflow("cinematico")

    assert documentary["provider"] == "flux"
    assert documentary["workflow"].name == "flux1_krea_dev_api.json"
    assert cinematic["provider"] == "flux"
    assert cinematic["workflow"].name == "flux1_krea_dev_api.json"


def test_image_workflow_router_uses_flux_for_short_premium_formats():
    for format_key in ["podcast", "autohipnosis", "meditacion_larga"]:
        workflow = factory._select_image_workflow(format_key)

        assert workflow["provider"] == "flux"
        assert workflow["workflow"].name == "flux1_krea_dev_api.json"
        assert workflow["width"] == 1344
        assert workflow["height"] == 768


def test_image_workflow_router_uses_vertical_flux_for_tiktok():
    workflow = factory._select_image_workflow("tiktok_podcast")

    assert workflow["provider"] == "flux"
    assert workflow["workflow"].name == "flux1_krea_dev_api.json"
    assert workflow["height"] > workflow["width"]
    assert abs((workflow["width"] / workflow["height"]) - (9 / 16)) < 0.02


def test_tiktok_delivery_cover_uses_first_scene_image(tmp_path):
    from PIL import Image

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    first = images_dir / "scene_001.png"
    Image.new("RGB", (900, 1600), (20, 20, 24)).save(first)

    factory.write_tiktok_delivery_assets(
        tmp_path,
        {
            "format": "tiktok_podcast",
            "topic": "Esto no es amor, es apego",
            "tiktok": {
                "caption": "Caption lista",
                "hashtags": ["#EstoNoEsAmor", "#ApegoEmocional"],
                "scores": {"hookScore": 88},
            },
        },
        final_video=None,
    )

    cover = tmp_path / "tiktok" / "cover.jpg"
    metadata = json.loads((tmp_path / "tiktok" / "metadata.json").read_text(encoding="utf-8"))

    assert cover.is_file()
    with Image.open(cover) as img:
        assert img.size == (1080, 1920)
        assert img.format == "JPEG"
    assert metadata["coverFile"] == "cover.jpg"
    assert metadata["coverSource"] == "first_image"


def test_tiktok_delivery_cover_falls_back_to_video_frame(monkeypatch, tmp_path):
    from PIL import Image

    final_video = tmp_path / "FINAL_TIKTOK.mp4"
    final_video.write_bytes(b"fake")

    def fake_fallback(_final_video, cover_path):
        Image.new("RGB", (1080, 1920), (0, 0, 0)).save(cover_path)
        return True

    monkeypatch.setattr(factory, "_render_tiktok_cover_fallback_from_video", fake_fallback)

    factory.write_tiktok_delivery_assets(
        tmp_path,
        {
            "format": "tiktok_podcast",
            "topic": "Fallback de portada",
            "tiktok": {"hashtags": ["#TikTok"]},
        },
        final_video=final_video,
    )

    metadata = json.loads((tmp_path / "tiktok" / "metadata.json").read_text(encoding="utf-8"))

    assert (tmp_path / "tiktok" / "cover.jpg").is_file()
    assert metadata["coverFile"] == "cover.jpg"
    assert metadata["coverSource"] == "video_frame"


def test_runtime_image_generation_does_not_route_through_seedream(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.flux_posts = 0

        def __enter__(self):
            calls["client"] = self
            return self

        def __exit__(self, *args):
            return False

        def close(self):
            return None

        def post(self, url, headers=None, json=None):
            prompt_graph = (json or {}).get("prompt", {})
            assert "25" not in prompt_graph
            self.flux_posts += 1
            return _FakeResponse(payload={"prompt_id": f"flux-{self.flux_posts}"})

        def get(self, url, headers=None, params=None):
            if "/jobs/flux-" in url:
                return _FakeResponse(payload={
                    "status": "completed",
                    "outputs": {
                        "9": {
                            "images": [{
                                "filename": "scene.png",
                                "subfolder": "",
                                "type": "output",
                            }],
                        },
                    },
                })
            if url.endswith("/view"):
                return _FakeResponse(content=b"x" * (factory.IMAGE_MIN_BYTES + 1024))
            return _FakeResponse(status_code=404)

    calls = {}
    monkeypatch.setattr(factory.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(factory.httpx, "Client", FakeClient)

    images_dir = Path(".test-output") / "flux-only" / "images"
    shutil.rmtree(images_dir.parent, ignore_errors=True)
    try:
        scenes = [
            {"scene_number": 1, "prompt": "object-only podcast scene"},
            {"scene_number": 2, "prompt": "empty studio podcast scene"},
        ]
        stats = factory.generate_comfy_images(
            scenes,
            images_dir,
            factory._select_image_workflow("podcast"),
            pipeline_format="podcast",
        )
    finally:
        shutil.rmtree(images_dir.parent, ignore_errors=True)

    assert stats["generated"] == 2
    assert stats["fallback"] == 0
    assert stats["failed"] == 0
    assert calls["client"].flux_posts == 2
