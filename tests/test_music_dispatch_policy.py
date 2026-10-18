"""Music production policy survives queueing, fallback and old Celery messages.

No live queue, Firebase client or paid provider is used by these tests.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException, Request

import api


def music_request(body):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "method": "POST", "path": "/music", "headers": []}, receive)


@pytest.mark.parametrize("body", [b"", b"  ", b"{}", b'{"productionProfile":"openai_only"}'])
def test_music_request_accepts_old_clients_and_explicit_safe_profile(body):
    assert asyncio.run(api._music_requested_production_profile(music_request(body))) == "openai_only"


@pytest.mark.parametrize("body", [b"{broken", b"[]", b"null", b'{"productionProfile":"legacy"}'])
def test_music_request_rejects_invalid_configuration(body):
    with pytest.raises(HTTPException) as error:
        asyncio.run(api._music_requested_production_profile(music_request(body)))
    assert error.value.status_code == 400


@pytest.mark.parametrize(
    "endpoint,args,queue_name",
    [
        ("music_track_produce_video", ("track-1",), "_music_queue_track_render"),
        ("music_track_produce_audio_version", ("track-1", "audio-2"), "_music_queue_track_render"),
        ("music_track_generate_audio_version_shorts", ("track-1", "audio-2"), "_music_queue_track_shorts"),
    ],
)
def test_music_endpoints_forward_request_policy_and_reject_legacy(monkeypatch, endpoint, args, queue_name):
    principal = {"uid": "owner-1"}
    monkeypatch.setattr(api, "_require_music_studio_admin", lambda request: principal)
    calls = []

    def queue(*queue_args):
        calls.append(queue_args)
        return {"ok": True}

    monkeypatch.setattr(api, queue_name, queue)
    background_tasks = BackgroundTasks()
    result = asyncio.run(
        getattr(api, endpoint)(*args, music_request(b'{"productionProfile":"openai_only"}'), background_tasks)
    )

    assert result == {"ok": True}
    assert calls == [("track-1", args[1] if len(args) > 1 else None, principal, background_tasks, "openai_only")]
    calls.clear()
    with pytest.raises(HTTPException) as error:
        asyncio.run(getattr(api, endpoint)(*args, music_request(b'{"productionProfile":"legacy"}'), background_tasks))
    assert error.value.status_code == 400
    assert calls == []


@pytest.mark.parametrize("value", [None, "", "openai_only", " OPENAI_ONLY "])
def test_music_policy_defaults_and_normalizes_to_openai_only(value):
    assert api._music_validate_production_profile(value) == "openai_only"


@pytest.mark.parametrize("value", ["legacy", "comfy", "elevenlabs", "unknown"])
def test_music_api_rejects_profiles_that_can_call_disabled_providers(value):
    with pytest.raises(HTTPException) as error:
        api._music_validate_production_profile(value)
    assert error.value.status_code == 400


@pytest.mark.parametrize("kind", ["video", "shorts"])
@pytest.mark.parametrize("explicit_profile", [False, True])
def test_music_celery_dispatch_freezes_profile_in_message(monkeypatch, kind, explicit_profile):
    calls = []
    worker = ModuleType("worker_tasks")

    def delay(*args):
        calls.append(args)
        return SimpleNamespace(id="queued-task-1")

    setattr(worker, f"produce_music_{kind}", SimpleNamespace(delay=delay))
    monkeypatch.setitem(sys.modules, "worker_tasks", worker)
    background_tasks = BackgroundTasks()
    enqueue = getattr(api, f"_enqueue_music_{kind}_job")
    kwargs = {"production_profile": "openai_only"} if explicit_profile else {}

    result = enqueue("track-1", background_tasks, "audio-2", **kwargs)

    assert result == {"queue": "celery", "taskId": "queued-task-1"}
    assert calls == [("track-1", "audio-2", "openai_only")]
    assert background_tasks.tasks == []


@pytest.mark.parametrize("kind", ["video", "shorts"])
def test_music_background_fallback_keeps_the_same_policy(monkeypatch, kind):
    worker = ModuleType("worker_tasks")

    def unavailable(*args):
        raise ConnectionError("queue unavailable")

    setattr(worker, f"produce_music_{kind}", SimpleNamespace(delay=unavailable))
    monkeypatch.setitem(sys.modules, "worker_tasks", worker)
    rendered = []

    def render(*args):
        rendered.append(args)

    monkeypatch.setattr(api, f"_run_music_{kind}_job", render)
    background_tasks = BackgroundTasks()
    result = getattr(api, f"_enqueue_music_{kind}_job")("track-1", background_tasks, "audio-2")

    assert result["queue"] == "api_background"
    assert len(background_tasks.tasks) == 1
    asyncio.run(background_tasks())
    assert rendered == [("track-1", "audio-2", "openai_only")]


@pytest.mark.parametrize("kind", ["video", "shorts"])
def test_rejected_policy_is_never_queued_or_scheduled(monkeypatch, kind):
    calls = []
    worker = ModuleType("worker_tasks")
    setattr(worker, f"produce_music_{kind}", SimpleNamespace(delay=lambda *args: calls.append(args)))
    monkeypatch.setitem(sys.modules, "worker_tasks", worker)
    background_tasks = BackgroundTasks()

    with pytest.raises(HTTPException):
        getattr(api, f"_enqueue_music_{kind}_job")("track-1", background_tasks, "audio-2", "legacy")

    assert calls == []
    assert background_tasks.tasks == []


@pytest.fixture
def worker_module(monkeypatch):
    """Execute the real workers with only Celery registration replaced."""
    fake_exceptions = ModuleType("celery.exceptions")
    fake_exceptions.SoftTimeLimitExceeded = type("SoftTimeLimitExceeded", (Exception,), {})
    fake_celery = ModuleType("celery")
    fake_celery.exceptions = fake_exceptions
    fake_app = ModuleType("worker_app")
    fake_app.celery_app = SimpleNamespace(task=lambda **options: lambda function: function)
    monkeypatch.setitem(sys.modules, "celery", fake_celery)
    monkeypatch.setitem(sys.modules, "celery.exceptions", fake_exceptions)
    monkeypatch.setitem(sys.modules, "worker_app", fake_app)
    spec = importlib.util.spec_from_file_location(
        "music_dispatch_workers_under_test", Path(api.__file__).with_name("worker_tasks.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", ["video", "shorts"])
@pytest.mark.parametrize("message_args", [("track-1",), ("track-1", "audio-2"), ("track-1", "audio-2", "openai_only")])
def test_workers_accept_old_messages_and_always_forward_policy(monkeypatch, worker_module, kind, message_args):
    calls = []

    def render(*args):
        calls.append(args)
        return {"status": "completed"}

    monkeypatch.setattr(api, f"_run_music_{kind}_job", render)
    task = SimpleNamespace(name=f"music-{kind}", request=SimpleNamespace(id="task-1", retries=0))
    result = getattr(worker_module, f"produce_music_{kind}")(task, *message_args)

    expected_audio = message_args[1] if len(message_args) > 1 else None
    assert calls == [("track-1", expected_audio, "openai_only")]
    assert result == {"status": "completed"}


@pytest.mark.parametrize("kind", ["render", "shorts"])
def test_music_queue_records_policy_before_dispatch(monkeypatch, kind):
    data = {"userId": "owner-1", "activeAudioVersionId": "audio-2"}
    writes = []

    class Reference:
        def get(self):
            return SimpleNamespace(exists=True, to_dict=lambda: data)

        def set(self, payload, merge=False):
            writes.append(payload)

    reference = Reference()
    fake_db = SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda key: reference))
    firestore = SimpleNamespace(client=lambda: fake_db, SERVER_TIMESTAMP=object())
    firebase = ModuleType("firebase_admin")
    firebase.firestore = firestore
    monkeypatch.setitem(sys.modules, "firebase_admin", firebase)
    monkeypatch.setattr(api, "_ensure_firebase_initialized", lambda: None)
    monkeypatch.setattr(api, "_music_audio_for_version", lambda *args: {"versionId": "audio-2", "fileName": "suno.mp3"})
    monkeypatch.setattr(api, "_music_running_render", lambda *args: None)
    monkeypatch.setattr(api, "_music_render_records", lambda *args: [])
    monkeypatch.setattr(api, "_music_upsert_render_record", lambda records, record: [*records, record])
    monkeypatch.setattr(api, "_power_music_public_track", lambda track_id, document: document)
    monkeypatch.setattr(
        api,
        "_music_render_for_version",
        lambda *args: {"status": "completed", "video": {"url": "https://example.invalid/video.mp4"}} if kind == "shorts" else {},
    )
    dispatched = []

    def enqueue(track_id, background_tasks, audio_version_id, profile):
        dispatched.append((track_id, audio_version_id, profile))
        return {"queue": "fake", "taskId": "job-1"}

    monkeypatch.setattr(api, "_enqueue_music_shorts_job" if kind == "shorts" else "_enqueue_music_video_job", enqueue)
    result = getattr(api, f"_music_queue_track_{kind}")("track-1", "audio-2", {"uid": "owner-1"}, BackgroundTasks())

    assert result["status"] == "queued"
    profile_key = "shortsProductionProfile" if kind == "shorts" else "productionProfile"
    assert writes[0]["render"][profile_key] == "openai_only"
    assert writes[0]["renders"][0][profile_key] == "openai_only"
    assert dispatched == [("track-1", "audio-2", "openai_only")]


def test_music_presets_advertise_effective_provider_policy(monkeypatch):
    monkeypatch.setattr(api, "_require_music_studio_admin", lambda request: {"uid": "owner-1"})
    result = api.music_presets(None)
    assert result["productionProfile"] == "openai_only"
    assert result["providerPolicy"] == api._resolve_music_production_policy("openai_only").as_metadata()
