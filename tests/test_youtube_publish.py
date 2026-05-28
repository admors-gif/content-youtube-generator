from datetime import datetime, timezone

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


def test_youtube_short_resource_sets_safe_upload_metadata():
    data = {
        "title": "Esto no es amor, es apego: aprende a reconocer la diferencia",
        "format": "podcast",
        "agentId": "agent_podcast_general",
    }
    short = {"index": 1, "label": "hook"}
    payload = {
        "title": "La señal que no querías ver",
        "privacyStatus": "public",
        "publishAt": "2026-05-10T18:00:00Z",
        "tags": "apego emocional, amor propio, apego emocional",
    }

    resource = api._youtube_short_resource("project-1", data, short, payload)

    assert resource["snippet"]["title"] == "La señal que no querías ver #Shorts"
    assert resource["snippet"]["tags"].count("apego emocional") == 1
    assert resource["status"]["privacyStatus"] == "private"
    assert resource["status"]["publishAt"] == "2026-05-10T18:00:00Z"
    assert resource["status"]["selfDeclaredMadeForKids"] is False
    assert resource["status"]["containsSyntheticMedia"] is True
    assert resource["paidProductPlacementDetails"]["hasPaidProductPlacement"] is False


def test_youtube_shorts_native_agent_payload_uses_youtube_platform():
    payload = api._validate_project_payload({
        "title": "Por que confundes ansiedad con amor",
        "agentId": "agent_youtube_shorts_esto_no_es_amor",
        "agentFile": "agent_youtube_shorts_esto_no_es_amor.md",
        "platform": "youtube",
        "durationProfile": "shorts75",
    })

    assert payload["platform"] == "youtube"
    assert payload["format"] == api.YOUTUBE_SHORTS_PODCAST_FORMAT
    assert payload["youtube_shorts"]["targetSeconds"] == 75
    assert payload["generation_options"]["audio_playback_speed"] == 1.25


def test_archivos_prohibidos_shorts_payload_uses_90s_documentary_format():
    payload = api._validate_project_payload({
        "title": "El ultimo mensaje del vuelo MH370",
        "agentId": "agent_youtube_shorts_archivos_prohibidos",
        "agentFile": "agent_youtube_shorts_archivos_prohibidos.md",
        "platform": "youtube",
    })

    assert payload["platform"] == "youtube"
    assert payload["format"] == api.YOUTUBE_SHORTS_DOCUMENTARY_FORMAT
    assert payload["youtube_shorts"]["durationProfile"] == "shorts90"
    assert payload["youtube_shorts"]["targetSeconds"] == 90
    assert payload["youtube_shorts"]["sourceGenre"] == "mystery"
    assert payload["generation_options"]["audio_playback_speed"] == 1.25


def test_podcast_v2_payload_adds_speed_without_touching_original():
    original = api._validate_project_payload({
        "title": "Por que confundimos intensidad con amor",
        "agentId": "agent_podcast_general",
        "agentFile": "agent_podcast_general.md",
        "platform": "youtube",
    })
    v2 = api._validate_project_payload({
        "title": "Por que confundimos intensidad con amor",
        "agentId": "agent_podcast_general_v2",
        "agentFile": "agent_podcast_general_v2.md",
        "platform": "youtube",
    })

    assert original["format"] == "podcast"
    assert "audio_playback_speed" not in original["generation_options"]
    assert v2["format"] == "podcast"
    assert v2["agent_file"] == "agent_podcast_general_v2.md"
    assert v2["generation_options"]["audio_playback_speed"] == 1.2


def test_podcast_v2_long_payload_uses_long_profile_and_speed():
    payload = api._validate_project_payload({
        "title": "Alguna vez te enamoraste o solo te obsesionaste",
        "agentId": "agent_podcast_general_v2_largo",
        "agentFile": "agent_podcast_general_v2_largo.md",
        "platform": "youtube",
        "durationProfile": "long",
    })

    assert payload["format"] == "podcast"
    assert payload["agent_file"] == "agent_podcast_general_v2_largo.md"
    assert payload["generation_options"]["audio_playback_speed"] == 1.2
    assert payload["generation_options"]["duration_profile"] == "long"


def test_youtube_publish_pack_has_native_shorts_cta():
    data = {
        "title": "Por que confundes ansiedad con amor",
        "format": api.YOUTUBE_SHORTS_PODCAST_FORMAT,
        "agentId": "agent_youtube_shorts_esto_no_es_amor",
    }

    pack = api._build_youtube_publish_pack("project-1", data)

    assert "quedate en el canal" in pack["description"]
    assert "siguiente Short" in pack["pinned_comment"]


def test_mystery_v2_publish_pack_uses_archivos_prohibidos_metadata():
    data = {
        "title": "El vuelo MH370: el avion que siguio volando en silencio",
        "agentId": "agent_misterios_v2",
        "seo_metadata": {
            "description": "Una investigacion sobre el misterio del vuelo MH370.",
            "tags": ["MH370", "aviacion"],
        },
    }

    pack = api._build_youtube_publish_pack("project-1", data)

    assert "Archivos Prohibidos - MX" in pack["description"]
    assert "misterios sin resolver" in pack["tags"]
    assert "#ArchivosProhibidosMX" in pack["hashtags"]
    assert "#MisteriosSinResolver" in pack["description"]
    assert "Que detalle" in pack["pinned_comment"]
    assert "Esto no es amor" not in pack["description"]


def test_archivos_prohibidos_shorts_publish_pack_keeps_channel_identity():
    data = {
        "title": "El ultimo mensaje del vuelo MH370",
        "agentId": "agent_youtube_shorts_archivos_prohibidos",
        "format": api.YOUTUBE_SHORTS_DOCUMENTARY_FORMAT,
    }

    pack = api._build_youtube_publish_pack("project-1", data)

    assert "Short de Archivos Prohibidos - MX" in pack["description"]
    assert "suscribete" in pack["description"]
    assert "#ArchivosProhibidosMX" in pack["hashtags"]
    assert "Esto no es amor" not in pack["description"]
    assert "siguiente Short" not in pack["pinned_comment"]


def test_youtube_shorts_pack_includes_seo_hashtags_and_offsets():
    data = {
        "title": "Por qué te obsesionas con quien no te elige.",
        "format": "podcast",
        "agentId": "agent_podcast_general",
        "shorts": [
            {"index": 1, "label": "hook", "duration": 55},
            {"index": 2, "label": "mid", "duration": 55},
            {"index": 3, "label": "end", "duration": 55},
        ],
    }

    pack = api._build_youtube_shorts_publish_pack("project-1", data)

    assert len(pack["shorts"]) == 3
    assert "#Shorts" in pack["shorts"][0]["metadata"]["hashtags"]
    assert "#EstoNoEsAmor" in pack["shorts"][0]["metadata"]["description"]
    assert pack["shorts"][0]["metadata"]["offsetHours"] == -24
    assert pack["shorts"][1]["metadata"]["offsetHours"] == -3
    assert pack["shorts"][2]["metadata"]["offsetHours"] == 24


def test_youtube_short_preflight_blocks_horizontal_or_too_long(tmp_path, monkeypatch):
    shorts_dir = tmp_path / "shorts"
    shorts_dir.mkdir()
    short_file = shorts_dir / "SHORT_01_hook.mp4"
    short_file.write_bytes(b"fake")

    monkeypatch.setattr(api, "_validate_media_file", lambda *_args, **_kwargs: (True, 181.0, ""))
    monkeypatch.setattr(api, "_youtube_video_dimensions", lambda *_args, **_kwargs: (1080, 1920))

    result = api._youtube_short_preflight(tmp_path, {"index": 1, "label": "hook"})

    assert result["eligible"] is False
    assert "180 seconds" in result["error"]

    monkeypatch.setattr(api, "_validate_media_file", lambda *_args, **_kwargs: (True, 55.0, ""))
    monkeypatch.setattr(api, "_youtube_video_dimensions", lambda *_args, **_kwargs: (1920, 1080))

    result = api._youtube_short_preflight(tmp_path, {"index": 1, "label": "hook"})

    assert result["eligible"] is False
    assert "vertical" in result["error"]


def test_youtube_publication_overview_marks_missing_uploads():
    row = api._youtube_publication_overview_row(
        "project-1",
        {
            "title": "No extrañas a esa persona",
            "status": "completed",
            "shorts": [
                {"index": 1, "label": "hook"},
                {"index": 2, "label": "mid"},
                {"index": 3, "label": "end"},
            ],
        },
        now=datetime(2026, 5, 7, tzinfo=timezone.utc),
    )

    assert row["video"]["status"] == "missing"
    assert row["shorts"]["status"] == "missing"
    assert row["shorts"]["uploaded"] == 0
    assert row["nextAction"]["kind"] == "publish_video"


def test_youtube_publication_overview_tracks_scheduled_video_and_partial_shorts():
    row = api._youtube_publication_overview_row(
        "project-1",
        {
            "title": "Esto no es amor",
            "status": "completed",
            "shorts": [
                {"index": 1, "label": "hook"},
                {"index": 2, "label": "mid"},
                {"index": 3, "label": "end"},
            ],
            "youtube": {
                "lastVideoId": "abc123",
                "lastStudioUrl": "https://studio.youtube.com/video/abc123/edit",
                "lastScheduledPublishAt": "2026-05-08T02:00:00Z",
                "shortsUploads": [
                    {
                        "index": 1,
                        "youtubeVideoId": "s1",
                        "publishAt": "2026-05-08T00:00:00Z",
                    }
                ],
            },
        },
        now=datetime(2026, 5, 7, tzinfo=timezone.utc),
    )

    assert row["video"]["status"] == "scheduled"
    assert row["shorts"]["status"] == "partial"
    assert row["shorts"]["uploaded"] == 1
    assert row["shorts"]["scheduled"] == 1
    assert row["nextAction"]["kind"] == "publish_shorts"
