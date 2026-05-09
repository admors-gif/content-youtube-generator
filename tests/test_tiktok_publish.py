import api


def test_tiktok_idempotency_key_is_stable_and_schedule_sensitive():
    first = api._tiktok_idempotency_key(
        "uid1",
        "account1",
        "project1",
        "hash1",
        "2026-05-09T02:00:00+00:00",
    )
    second = api._tiktok_idempotency_key(
        "uid1",
        "account1",
        "project1",
        "hash1",
        "2026-05-09T02:00:00+00:00",
    )
    different_time = api._tiktok_idempotency_key(
        "uid1",
        "account1",
        "project1",
        "hash1",
        "2026-05-10T02:00:00+00:00",
    )

    assert first == second
    assert first != different_time
    assert api._tiktok_job_doc_id(first).startswith("tt_")


def test_tiktok_caption_pack_keeps_aigc_and_hashtags():
    pack = api._tiktok_caption_pack(
        "project1",
        {
            "title": "Esto no es amor",
            "tiktok": {
                "caption": "Un cierre emocional.",
                "hashtags": ["#EstoNoEsAmor", "#ApegoEmocional"],
            },
        },
    )

    assert pack["isAigc"] is True
    assert pack["brandedContent"] is False
    assert "#EstoNoEsAmor" in pack["caption"]
    assert pack["hashtags"] == ["#EstoNoEsAmor", "#ApegoEmocional"]


def test_tiktok_caption_pack_respects_user_edited_hashtags():
    pack = api._tiktok_caption_pack(
        "project1",
        {
            "title": "Esto no es amor",
            "tiktok": {"hashtags": ["#Viejo"]},
        },
        {
            "caption": "Caption editado",
            "hashtags": ["Nuevo", "#ApegoEmocional", "nuevo"],
        },
    )

    assert pack["hashtags"] == ["#Nuevo", "#ApegoEmocional"]
    assert "Caption editado" in pack["caption"]
    assert "#Nuevo #ApegoEmocional" in pack["caption"]


def test_tiktok_preflight_rejects_horizontal_video(monkeypatch, tmp_path):
    video = tmp_path / "FINAL_TIKTOK.mp4"
    video.write_bytes(b"fake")

    monkeypatch.setattr(api, "_youtube_project_video_dir", lambda _data: tmp_path)
    monkeypatch.setattr(api, "_tiktok_final_video_file", lambda _video_dir: video)
    monkeypatch.setattr(api, "_validate_media_file", lambda *_args, **_kwargs: (True, 90.0, ""))
    monkeypatch.setattr(api, "_youtube_video_dimensions", lambda _path: (1920, 1080))

    preflight = api._tiktok_video_preflight({"videoFolder": "folder"})

    assert preflight["eligible"] is False
    assert "vertical" in preflight["error"].lower()


def test_tiktok_preflight_accepts_vertical_under_ten_minutes(monkeypatch, tmp_path):
    video = tmp_path / "FINAL_TIKTOK.mp4"
    video.write_bytes(b"x" * 1024)

    monkeypatch.setattr(api, "_youtube_project_video_dir", lambda _data: tmp_path)
    monkeypatch.setattr(api, "_tiktok_final_video_file", lambda _video_dir: video)
    monkeypatch.setattr(api, "_validate_media_file", lambda *_args, **_kwargs: (True, 90.0, ""))
    monkeypatch.setattr(api, "_youtube_video_dimensions", lambda _path: (1080, 1920))

    preflight = api._tiktok_video_preflight({"videoFolder": "folder"})

    assert preflight["eligible"] is True
    assert preflight["durationSeconds"] == 90.0
    assert preflight["width"] == 1080
    assert preflight["height"] == 1920


def test_tiktok_public_account_doc_does_not_expose_tokens():
    class FakeDoc:
        id = "open123"

        def to_dict(self):
            return {
                "openId": "open123",
                "displayName": "Canal TikTok",
                "accessTokenEncrypted": "secret",
                "refreshTokenEncrypted": "secret",
            }

    public = api._tiktok_public_account_doc(FakeDoc())

    assert public["accountId"] == "open123"
    assert public["displayName"] == "Canal TikTok"
    assert "accessTokenEncrypted" not in public
    assert "refreshTokenEncrypted" not in public
