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
