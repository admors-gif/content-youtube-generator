from scripts import factory
from scripts.factory import validate_image_assets


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


def test_image_workflow_router_uses_seedream_for_short_premium_formats():
    for format_key in ["podcast", "autohipnosis", "meditacion_larga"]:
        workflow = factory._select_image_workflow(format_key)

        assert workflow["provider"] == "seedream"
        assert workflow["workflow"].name == "seedream_5_lite_t2i_api.json"
