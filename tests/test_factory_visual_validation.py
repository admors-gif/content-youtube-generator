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
