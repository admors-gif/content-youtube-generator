import api


def test_youtube_publish_pack_for_podcast_contains_upload_material():
    data = {
        "title": "Por qué te obsesionas con quien no te elige.",
        "format": "podcast",
        "agentId": "agent_podcast_general",
        "seo_metadata": {
            "description": "Una conversación clara sobre apego, obsesión y amor propio.",
            "tags": ["apego emocional", "amor propio", "relaciones tóxicas"],
        },
        "scenes": [
            {"target_duration_seconds": 60},
            {"target_duration_seconds": 75, "title": "El patrón"},
            {"target_duration_seconds": 80, "title": "Cómo salir"},
        ],
    }

    pack = api._build_youtube_publish_pack("project-1", data)

    assert pack["title"] == "Por qué te obsesionas con quien no te elige."
    assert "Una conversación clara" in pack["description"]
    assert "#EstoNoEsAmor" in pack["hashtags"]
    assert "#ApegoEmocional" in pack["hashtags"]
    assert "apego emocional" in pack["tags"]
    assert "podcast en español" in pack["tags"]
    assert "00:00 Inicio" in pack["description"]
    assert "Suscríbete" in pack["description"]
    assert "crear tu propio podcast" in pack["description"]
    assert "Parte 1" not in pack["description"]
    assert "comentarios" in pack["pinned_comment"].lower()
    assert "- [ ] Subir el video final con subtítulos." in pack["checklist"]


def test_youtube_publish_pack_omits_generic_part_chapters_for_podcast():
    data = {
        "title": "Esto no es amor, es apego: aprende a reconocer la diferencia",
        "format": "podcast",
        "agentId": "agent_podcast_general",
        "scenes": [{"target_duration_seconds": 60} for _ in range(15)],
    }

    pack = api._build_youtube_publish_pack("project-1", data)

    assert pack["chapters"] == []
    assert "Parte 12" not in pack["description"]
    assert "dependencia emocional" in pack["description"]
    assert "#PodcastEnEspañol" in pack["description"]


def test_youtube_tags_are_limited_and_deduplicated():
    repeated_tags = ["amor propio"] * 10 + [f"tag largo {i}" for i in range(80)]
    data = {
        "title": "Esto no es amor, es apego",
        "format": "podcast",
        "agentId": "agent_podcast_general",
        "seo_metadata": {"tags": repeated_tags},
    }

    tags = api._youtube_tags_for_project(data, data["title"])

    assert tags.count("amor propio") == 1
    assert sum(len(tag) + 2 for tag in tags) <= 500
    assert "Esto no es amor" in tags
