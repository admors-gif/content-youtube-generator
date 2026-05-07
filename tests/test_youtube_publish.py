import api


def test_youtube_video_resource_defaults_to_private_and_safe_metadata():
    data = {
        "title": "Por qué te obsesionas con quien no te elige.",
        "format": "podcast",
        "agentId": "agent_podcast_general",
        "seo_metadata": {
            "description": "Una conversación sobre apego emocional y amor propio.",
            "tags": ["apego emocional", "amor propio"],
        },
    }

    resource = api._build_youtube_video_resource("project-1", data, {})

    assert resource["snippet"]["title"] == data["title"]
    assert resource["snippet"]["categoryId"] == "22"
    assert "apego emocional" in resource["snippet"]["tags"]
    assert resource["status"]["privacyStatus"] == "private"
    assert resource["status"]["selfDeclaredMadeForKids"] is False
    assert "publishAt" not in resource["status"]


def test_youtube_video_resource_keeps_scheduled_upload_private():
    data = {"title": "Esto no es amor, es apego", "format": "podcast"}
    payload = {
        "title": "Título editado",
        "privacyStatus": "public",
        "publishAt": "2026-05-10T18:00:00Z",
        "tags": "apego emocional, amor propio, apego emocional",
    }

    resource = api._build_youtube_video_resource("project-1", data, payload)

    assert resource["snippet"]["title"] == "Título editado"
    assert resource["snippet"]["tags"].count("apego emocional") == 1
    assert resource["status"]["privacyStatus"] == "private"
    assert resource["status"]["publishAt"] == "2026-05-10T18:00:00Z"


def test_youtube_thumbnail_warning_is_clear_for_channel_permission_error():
    raw = (
        'youtube thumbnail upload failed: { "error": { "code": 403, '
        '"message": "The authenticated user doesn\'t have permissions to upload and set custom video thumbnails." }}'
    )

    warning = api._youtube_thumbnail_warning(raw)

    assert "video sí se subió" in warning
    assert "miniatura personalizada" in warning
    assert "{" not in warning
    assert "403" not in warning


def test_youtube_public_channel_doc_exposes_long_upload_status():
    class Snapshot:
        id = "channel-1"

        def to_dict(self):
            return {
                "channelId": "channel-1",
                "title": "Esto no es amor",
                "longUploadsStatus": "disallowed",
                "madeForKids": False,
            }

    channel = api._youtube_public_channel_doc(Snapshot())

    assert channel["longUploadsStatus"] == "disallowed"
    assert channel["madeForKids"] is False


def test_youtube_config_status_reports_missing_oauth_env(monkeypatch):
    for key in [
        "YOUTUBE_OAUTH_CLIENT_ID",
        "YOUTUBE_OAUTH_CLIENT_SECRET",
        "YOUTUBE_OAUTH_REDIRECT_URI",
        "CONTENT_FACTORY_YOUTUBE_STATE_SECRET",
        "CONTENT_FACTORY_YOUTUBE_TOKEN_SECRET",
        "CONTENT_FACTORY_ADMIN_TOKEN",
    ]:
        monkeypatch.delenv(key, raising=False)

    status = api._youtube_config_status()

    assert status["configured"] is False
    assert "client_id" in status["missing"]
    assert "client_secret" in status["missing"]
