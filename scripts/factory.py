"""
═══════════════════════════════════════════════════════════════
  CONTENT FACTORY v2.0 — Pipeline Unificado
═══════════════════════════════════════════════════════════════

  Dos modos de producción:

  🎬 NARRATIVA: FLUX + ElevenLabs + Ken Burns
     → Rápido, barato, ideal para volumen diario
     → Costo: ~$1.60 USD/video

  🎥 CINEMÁTICO: FLUX + ElevenLabs + Luma AI + Ken Burns mix
     → Premium, clips con movimiento real
     → Costo: ~$5.35 USD/video

  Uso:
    python factory.py <FULL_json> --mode narrativa
    python factory.py <FULL_json> --mode cinematico
    python factory.py <FULL_json> --mode cinematico --luma-scenes 8

═══════════════════════════════════════════════════════════════
"""
import os, json, time, random, subprocess, copy, re, sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).parent.parent

# ============================================================
# CONFIGURACIÓN
# ============================================================
COMFYUI_API_KEY = os.getenv("COMFYUI_API_KEY")
COMFYUI_BASE = "https://cloud.comfy.org/api"
COMFYUI_HEADERS = {"X-API-Key": COMFYUI_API_KEY, "Content-Type": "application/json"}
IMAGE_MIN_BYTES = 5000
IMAGE_JOBS_FILENAME = "image_jobs.json"

GENERAL_IMAGE_PROMPT_PREFIX = (
    "Highly realistic cinematic film still, masterpiece, 8k resolution, "
    "photorealistic lighting, refined editorial composition."
)

PODCAST_IMAGE_PROMPT_PREFIX = (
    "Premium editorial podcast visual, object-led or abstract composition, "
    "empty-room or still-life framing, clean blank surfaces, no readable text, no logos, "
    "clean contemporary magazine photography, warm amber and deep teal palette."
)

AUTOHYPNOSIS_IMAGE_PROMPT_PREFIX = (
    "Premium guided self-hypnosis visual, serene wellness atmosphere, soft violet, "
    "midnight blue and warm gold palette, peaceful abstract or object-led "
    "composition, slow cinematic calm, non-clinical premium meditation aesthetic."
)

SEEDREAM_IMAGE_PROMPT_PREFIX = (
    "Premium cinematic editorial still for a Spanish audio-video production, "
    "environment-led or object-led composition, refined natural lighting, clean "
    "blank surfaces, no readable text, no logos, no watermark, no captions."
)

AUTOHYPNOSIS_MUSIC_DIR = BASE_DIR / "assets" / "audio" / "autohipnosis"
AUTOHYPNOSIS_DEFAULT_MUSIC_VOLUME_DB = -28.0
LONG_MEDITATION_FORMAT = "meditacion_larga"
WELLNESS_FORMATS = {"autohipnosis", LONG_MEDITATION_FORMAT}
LONG_MEDITATION_DEFAULT_MUSIC_VOLUME_DB = -24.0
LONG_MEDITATION_STATIC_FPS = 6

# Importar módulos propios
sys.path.insert(0, str(Path(__file__).parent))
from elevenlabs_tts import (
    generate_scene_narrations,
    generate_dual_narration,
    get_voice_for_agent, get_voice_settings, DEFAULT_VOICE, VOICE_MAP
)
from luma_video import (
    generate_cinematic_clips, upload_image_to_temp,
    create_generation, poll_generation, download_video
)
from generate_subtitles import add_subtitles_to_video
from media_validation import validate_media_file


def _scene_number(scene):
    try:
        return int(scene.get("scene_number", scene.get("sceneNumber", 0)))
    except Exception:
        return 0


def _legacy_title_slug(title: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(title or "video_sin_titulo").replace(" ", "_"))
    return slug.strip("_-") or "video_sin_titulo"


def _safe_output_folder_name(name: str | None) -> str | None:
    if not name:
        return None
    basename = Path(str(name)).name
    slug = _legacy_title_slug(basename)
    return slug or None


def _project_output_slug(title: str, project_id: str | None = None) -> str:
    title_slug = _legacy_title_slug(title)
    if not project_id:
        return title_slug
    project_slug = _legacy_title_slug(project_id)
    compact_title = title_slug[:90].rstrip("_-") or "video_sin_titulo"
    return f"{compact_title}__{project_slug}"


def _resolve_output_folder(data: dict) -> str:
    explicit = _safe_output_folder_name(data.get("output_folder") or data.get("videoFolder"))
    if explicit:
        return explicit
    return _project_output_slug(data.get("topic", "video_sin_titulo"), data.get("project_id"))


def _image_jobs_path(images_dir: Path) -> Path:
    return images_dir.parent / IMAGE_JOBS_FILENAME


def _load_image_jobs(images_dir: Path) -> dict:
    path = _image_jobs_path(images_dir)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f"   [image-jobs] metadata unreadable: {exc}")
    return {}


def _save_image_jobs(images_dir: Path, jobs: dict) -> None:
    path = _image_jobs_path(images_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def _build_image_prompt(prompt: str, pipeline_format: str = "narrativa", provider: str = "flux") -> str:
    prompt = (prompt or "").strip()
    if provider == "seedream":
        return f"{SEEDREAM_IMAGE_PROMPT_PREFIX} {prompt}".strip()
    if pipeline_format == "podcast":
        return f"{PODCAST_IMAGE_PROMPT_PREFIX} {prompt}".strip()
    if pipeline_format in WELLNESS_FORMATS:
        return f"{AUTOHYPNOSIS_IMAGE_PROMPT_PREFIX} {prompt}".strip()
    return f"{GENERAL_IMAGE_PROMPT_PREFIX} {prompt}".strip()


def _select_image_workflow(pipeline_format: str) -> dict:
    """Select the Comfy workflow without changing documentary/narrative output."""
    if pipeline_format in {"podcast", *WELLNESS_FORMATS}:
        return {
            "provider": "seedream",
            "label": "Seedream 5 Lite",
            "workflow": BASE_DIR / "config" / "seedream_5_lite_t2i_api.json",
            "prompt_node": "25",
            "prompt_input": "prompt",
            "seed_node": "25",
            "seed_input": "seed",
            "seed_max": 2147483647,
            "size_node": "25",
            "size_preset": "2560x1440 (16:9)",
            "width": 2560,
            "height": 1440,
            "save_node": "26",
        }
    return {
        "provider": "flux",
        "label": "FLUX/Krea",
        "workflow": BASE_DIR / "config" / "flux1_krea_dev_api.json",
        "prompt_node": "200:195",
        "prompt_input": "text",
        "seed_node": "200:197",
        "seed_input": "seed",
        "seed_max": 999999999999999,
        "size_node": "200:196",
        "width": 1344,
        "height": 768,
        "save_node": "9",
    }


def _apply_image_workflow_inputs(nodes: dict, spec: dict, prompt: str, scene_number: int) -> int:
    prompt_node = nodes[spec["prompt_node"]]["inputs"]
    prompt_node[spec["prompt_input"]] = prompt

    seed = random.randint(100000000, int(spec.get("seed_max") or 2147483647))
    nodes[spec["seed_node"]]["inputs"][spec["seed_input"]] = seed

    size_inputs = nodes.get(spec.get("size_node"), {}).get("inputs", {})
    if spec.get("size_preset") and "size_preset" in size_inputs:
        size_inputs["size_preset"] = spec["size_preset"]
    if spec.get("width") and "width" in size_inputs:
        size_inputs["width"] = spec["width"]
    if spec.get("height") and "height" in size_inputs:
        size_inputs["height"] = spec["height"]

    save_inputs = nodes.get(spec.get("save_node"), {}).get("inputs", {})
    if "filename_prefix" in save_inputs:
        save_inputs["filename_prefix"] = f"scene_{scene_number:04d}"
    return seed


def _workflow_error_summary(job: dict) -> dict:
    err = job.get("execution_error") if isinstance(job, dict) else None
    if not isinstance(err, dict):
        return {}
    return {
        "errorType": str(err.get("exception_type") or "")[:120],
        "errorMessage": str(err.get("exception_message") or "")[:500],
        "errorNode": str(err.get("node_id") or "")[:80],
        "errorNodeType": str(err.get("node_type") or "")[:120],
    }


def _run_single_image_job(
    client,
    base_workflow: dict,
    workflow_spec: dict,
    prompt: str,
    pipeline_format: str,
    scene_number: int,
    img_path: Path,
    image_jobs: dict,
    attempt_label: str = "primary",
) -> bool:
    nodes = copy.deepcopy(base_workflow)
    final_prompt = _build_image_prompt(
        prompt,
        pipeline_format=pipeline_format,
        provider=workflow_spec["provider"],
    )
    seed = _apply_image_workflow_inputs(nodes, workflow_spec, final_prompt, scene_number)

    previous_record = image_jobs.get(str(scene_number), {})
    record = previous_record if attempt_label != "primary" else {"sceneNumber": scene_number}
    if attempt_label != "primary":
        record.setdefault("fallbacks", []).append({
            "fromProvider": previous_record.get("provider"),
            "fromWorkflow": previous_record.get("workflow"),
            "fromJobId": previous_record.get("jobId"),
            "fromStatus": previous_record.get("status"),
            "fromError": previous_record.get("errorMessage"),
            "startedAt": datetime_now_iso(),
        })

    record.update({
        "sceneNumber": scene_number,
        "status": "submitting" if attempt_label == "primary" else f"{attempt_label}_submitting",
        "provider": workflow_spec["provider"],
        "workflow": workflow_spec["workflow"].name,
        "attempt": attempt_label,
        "prompt": prompt,
        "finalPrompt": final_prompt,
        "filenamePrefix": f"scene_{scene_number:04d}",
        "seed": seed,
        "submittedAt": datetime_now_iso(),
        "outputs": [],
    })
    image_jobs[str(scene_number)] = record
    _save_image_jobs(img_path.parent, image_jobs)

    resp = client.post(f"{COMFYUI_BASE}/prompt", headers=COMFYUI_HEADERS, json={"prompt": nodes})
    if resp.status_code != 200:
        record.update({
            "status": "submit_failed" if attempt_label == "primary" else f"{attempt_label}_submit_failed",
            "httpStatus": resp.status_code,
            "errorMessage": resp.text[:500],
            "failedAt": datetime_now_iso(),
        })
        image_jobs[str(scene_number)] = record
        _save_image_jobs(img_path.parent, image_jobs)
        return False

    prompt_id = resp.json()["prompt_id"]
    record.update({"status": "queued" if attempt_label == "primary" else f"{attempt_label}_queued", "jobId": prompt_id})
    image_jobs[str(scene_number)] = record
    _save_image_jobs(img_path.parent, image_jobs)

    for attempt in range(60):  # 5 min max
        time.sleep(5)
        try:
            jr = client.get(f"{COMFYUI_BASE}/jobs/{prompt_id}", headers=COMFYUI_HEADERS)
            if jr.status_code != 200:
                continue
            job = jr.json()
            status = job.get("status", "unknown")

            if status == "completed":
                image_outputs = _extract_image_outputs(job)
                record.update({
                    "status": "completed",
                    "outputs": image_outputs,
                    "completedAt": datetime_now_iso(),
                })
                image_jobs[str(scene_number)] = record
                _save_image_jobs(img_path.parent, image_jobs)
                for output_info in image_outputs:
                    if _download_image_output(client, output_info, img_path):
                        record.update({
                            "status": "downloaded",
                            "localPath": str(img_path),
                            "downloadedAt": datetime_now_iso(),
                            "selectedOutput": output_info,
                        })
                        image_jobs[str(scene_number)] = record
                        _save_image_jobs(img_path.parent, image_jobs)
                        return True
                return False
            elif status in ("failed", "error"):
                record.update({
                    "status": status,
                    "failedAt": datetime_now_iso(),
                    **_workflow_error_summary(job),
                })
                image_jobs[str(scene_number)] = record
                _save_image_jobs(img_path.parent, image_jobs)
                return False
        except Exception as exc:
            record["lastPollError"] = str(exc)[:200]
            image_jobs[str(scene_number)] = record
            _save_image_jobs(img_path.parent, image_jobs)

    record.update({
        "status": "failed",
        "failedAt": datetime_now_iso(),
        "errorMessage": "Timed out waiting for Comfy job completion",
    })
    image_jobs[str(scene_number)] = record
    _save_image_jobs(img_path.parent, image_jobs)
    return False


def _safe_audio_asset_path(filename: str | None) -> Path | None:
    """Resolve future curated audio beds without allowing path traversal."""
    if not filename:
        return None
    candidate = AUTOHYPNOSIS_MUSIC_DIR / Path(filename).name
    try:
        resolved = candidate.resolve()
        base = AUTOHYPNOSIS_MUSIC_DIR.resolve()
        if base not in resolved.parents and resolved != base:
            return None
    except Exception:
        return None
    return resolved if resolved.exists() and resolved.is_file() else None


def _get_autohypnosis_music_config(data: dict) -> dict:
    pipeline_format = data.get("format")
    if pipeline_format not in WELLNESS_FORMATS:
        return {"enabled": False}
    format_key = "longMeditation" if pipeline_format == LONG_MEDITATION_FORMAT else "autohipnosis"
    cfg = ((data.get(format_key) or {}).get("background_music") or {})
    if not cfg.get("enabled"):
        return {"enabled": False}
    asset = _safe_audio_asset_path(cfg.get("asset"))
    try:
        fallback_enabled = bool(cfg.get("procedural_fallback"))
    except Exception:
        fallback_enabled = False
    if not asset:
        if pipeline_format == LONG_MEDITATION_FORMAT and fallback_enabled:
            try:
                volume_db = float(cfg.get("volume_db", LONG_MEDITATION_DEFAULT_MUSIC_VOLUME_DB))
            except Exception:
                volume_db = LONG_MEDITATION_DEFAULT_MUSIC_VOLUME_DB
            volume_db = max(-36.0, min(-16.0, volume_db))
            return {
                "enabled": True,
                "procedural": True,
                "volume_db": volume_db,
            }
        print("   [music] Background music configured but asset is missing; continuing voice-only.")
        return {"enabled": False}
    try:
        volume_db = float(cfg.get("volume_db", AUTOHYPNOSIS_DEFAULT_MUSIC_VOLUME_DB))
    except Exception:
        volume_db = AUTOHYPNOSIS_DEFAULT_MUSIC_VOLUME_DB
    volume_db = max(-36.0, min(-16.0, volume_db))
    return {"enabled": True, "asset": asset, "volume_db": volume_db}


def _create_procedural_ambient_bed(project_dir: Path, duration: float, volume_db: float) -> Path | None:
    """
    Creates a copyright-safe ambient bed locally. No samples, no external music:
    only generated brown noise plus a very low sine tone.
    """
    if duration <= 0:
        return None

    ambient_path = project_dir / "ambient_bed_procedural.mp3"
    if ambient_path.exists() and ambient_path.stat().st_size > 10000:
        existing_duration = get_audio_duration(ambient_path)
        if existing_duration >= duration - 1:
            return ambient_path

    fade_out_start = max(0.0, duration - 12.0)
    filter_complex = (
        "[0:a]lowpass=f=1200,highpass=f=35,volume=0.55[noise];"
        "[1:a]volume=0.020,tremolo=f=0.10:d=0.20[tone];"
        "[noise][tone]amix=inputs=2:duration=longest,"
        "afade=t=in:st=0:d=8,"
        f"afade=t=out:st={fade_out_start:.3f}:d=12,"
        "alimiter=limit=0.85[a]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.06:d={duration:.3f}",
        "-f", "lavfi", "-i", f"sine=frequency=174:sample_rate=44100:duration={duration:.3f}",
        "-filter_complex", filter_complex,
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(ambient_path),
    ]
    timeout = max(120, min(1800, int(duration * 0.25)))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode == 0 and ambient_path.exists() and ambient_path.stat().st_size > 10000:
        print("   [music] Cama ambiental procedural generada sin assets externos.")
        return ambient_path

    print(f"   [music] Ambiente procedural falló; continuando voice-only: {result.stderr[:200]}")
    return None


def _mix_background_music(master_audio: Path, project_dir: Path, music_cfg: dict) -> Path:
    """
    Optional future hook for curated autohypnosis beds. It is disabled unless a
    vetted local asset is configured in the generation JSON, so current videos
    remain unchanged until the music library is ready.
    """
    if not music_cfg.get("enabled"):
        return master_audio

    duration = get_audio_duration(master_audio)
    if duration <= 0:
        return master_audio

    if music_cfg.get("procedural"):
        music_path = _create_procedural_ambient_bed(
            project_dir,
            duration,
            float(music_cfg.get("volume_db", LONG_MEDITATION_DEFAULT_MUSIC_VOLUME_DB)),
        )
    else:
        music_path = music_cfg.get("asset")
    if not music_path:
        return master_audio

    mixed_audio = project_dir / "master_audio_with_music.mp3"
    linear_volume = 10 ** (float(music_cfg.get("volume_db", AUTOHYPNOSIS_DEFAULT_MUSIC_VOLUME_DB)) / 20)
    fade_out_start = max(0.0, duration - 8.0)
    filter_complex = (
        f"[1:a]volume={linear_volume:.5f},"
        f"atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=4,afade=t=out:st={fade_out_start:.3f}:d=8[bed];"
        "[0:a][bed]amix=inputs=2:duration=first:dropout_transition=3,"
        "alimiter=limit=0.95[a]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(master_audio),
        "-stream_loop", "-1",
        "-i", str(music_path),
        "-filter_complex", filter_complex,
        "-map", "[a]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(mixed_audio),
    ]
    timeout = max(180, min(1800, int(duration * 0.20)))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode == 0 and mixed_audio.exists() and mixed_audio.stat().st_size > 10000:
        print(f"   [music] Cama sonora mezclada: {music_path.name}")
        return mixed_audio

    print(f"   [music] Mezcla de cama sonora falló; continuando voice-only: {result.stderr[:200]}")
    return master_audio


def _normalize_image_output(img_info: dict, node_id: str = None) -> dict:
    return {
        "nodeId": node_id,
        "filename": img_info.get("filename", ""),
        "displayName": img_info.get("display_name", img_info.get("displayName", "")),
        "subfolder": img_info.get("subfolder", ""),
        "type": img_info.get("type", "output"),
        "mediaType": img_info.get("mediaType", img_info.get("media_type", "images")),
    }


def _extract_image_outputs(job: dict) -> list:
    outputs = []
    seen = set()

    preview = job.get("preview_output")
    if isinstance(preview, dict) and preview.get("filename"):
        item = _normalize_image_output(preview, preview.get("nodeId"))
        key = (item["filename"], item["subfolder"], item["type"])
        seen.add(key)
        outputs.append(item)

    for node_id, node_out in (job.get("outputs") or {}).items():
        if not isinstance(node_out, dict):
            continue
        for img_info in node_out.get("images", []) or []:
            if not isinstance(img_info, dict):
                continue
            item = _normalize_image_output(img_info, node_id)
            key = (item["filename"], item["subfolder"], item["type"])
            if item["filename"] and key not in seen:
                seen.add(key)
                outputs.append(item)

    return outputs


def _download_image_output(client, output_info: dict, img_path: Path) -> bool:
    if not output_info.get("filename"):
        return False
    dl = client.get(
        f"{COMFYUI_BASE}/view",
        headers=COMFYUI_HEADERS,
        params={
            "filename": output_info.get("filename", ""),
            "subfolder": output_info.get("subfolder", ""),
            "type": output_info.get("type", "output"),
        },
    )
    if dl.status_code == 200 and len(dl.content) > IMAGE_MIN_BYTES:
        img_path.parent.mkdir(parents=True, exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(dl.content)
        return True
    return False


def recover_missing_images_from_metadata(scenes, images_dir, client=None) -> int:
    """Redownloads already-generated remote outputs. It never creates new jobs."""
    jobs = _load_image_jobs(images_dir)
    if not jobs:
        return 0

    owns_client = client is None
    recovered = 0
    if owns_client:
        client = httpx.Client(timeout=60.0, follow_redirects=True)

    try:
        for scene in scenes:
            num = _scene_number(scene)
            if not num:
                continue
            img_path = images_dir / f"scene_{num:04d}.png"
            if img_path.exists() and img_path.stat().st_size >= IMAGE_MIN_BYTES:
                continue
            record = jobs.get(str(num)) or {}
            for output_info in record.get("outputs", []) or []:
                try:
                    if _download_image_output(client, output_info, img_path):
                        record["status"] = "recovered"
                        record["localPath"] = str(img_path)
                        record["recoveredAt"] = datetime_now_iso()
                        jobs[str(num)] = record
                        recovered += 1
                        print(f"   [recovery] Escena {num}: descargada desde output remoto")
                        break
                except Exception as exc:
                    record["lastRecoveryError"] = str(exc)[:200]
                    jobs[str(num)] = record
    finally:
        _save_image_jobs(images_dir, jobs)
        if owns_client:
            client.close()

    return recovered


def validate_image_assets(scenes, images_dir, min_bytes=IMAGE_MIN_BYTES) -> dict:
    missing = []
    invalid = []
    ready = []
    for scene in scenes:
        num = _scene_number(scene)
        if not num:
            continue
        img_path = images_dir / f"scene_{num:04d}.png"
        if not img_path.exists():
            missing.append(num)
        elif img_path.stat().st_size < min_bytes:
            invalid.append(num)
        else:
            ready.append(num)
    return {"ready": ready, "missing": missing, "invalid": invalid}


def datetime_now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ============================================================
# PASO 1: GENERAR IMÁGENES (ComfyUI Cloud)
# ============================================================
def generate_comfy_images(scenes, images_dir, workflow_spec, pipeline_format="narrativa"):
    """Genera imágenes para todas las escenas via ComfyUI Cloud."""
    with open(workflow_spec["workflow"], "r", encoding="utf-8") as f:
        base_workflow = json.load(f)
    fallback_spec = _select_image_workflow("narrativa") if workflow_spec["provider"] != "flux" else None
    fallback_workflow = None
    if fallback_spec:
        with open(fallback_spec["workflow"], "r", encoding="utf-8") as f:
            fallback_workflow = json.load(f)
    
    stats = {"generated": 0, "skipped": 0, "failed": 0, "fallback": 0, "recovered": 0, "missing": [], "invalid": []}
    image_jobs = _load_image_jobs(images_dir)
    
    print("\n" + "=" * 60)
    print(f"   PASO 1: Generando imágenes {workflow_spec['label']}")
    print("=" * 60)
    
    primary_disabled_reason = None
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        for i, scene in enumerate(scenes):
            num = _scene_number(scene)
            prompt = scene["prompt"]
            img_path = images_dir / f"scene_{num:04d}.png"
            
            # Skip si ya existe
            if img_path.exists() and img_path.stat().st_size >= IMAGE_MIN_BYTES:
                stats["skipped"] += 1
                image_jobs.setdefault(str(num), {
                    "sceneNumber": num,
                    "status": "existing",
                    "localPath": str(img_path),
                    "updatedAt": datetime_now_iso(),
                })
                continue
            
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: generando imagen...")
            if primary_disabled_reason and fallback_spec and fallback_workflow:
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: saltando {workflow_spec['label']} ({primary_disabled_reason}), usando fallback FLUX/Krea...")
                ok = False
            else:
                ok = _run_single_image_job(
                    client,
                    base_workflow,
                    workflow_spec,
                    prompt,
                    pipeline_format,
                    num,
                    img_path,
                    image_jobs,
                    attempt_label="primary",
                )
            if not ok and fallback_spec and fallback_workflow:
                record = image_jobs.get(str(num), {})
                reason = primary_disabled_reason or record.get("errorMessage") or record.get("status") or "unknown"
                if "unauthorized" in reason.lower():
                    primary_disabled_reason = "unauthorized"
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: {workflow_spec['label']} falló ({reason[:80]}), usando fallback FLUX/Krea...")
                ok = _run_single_image_job(
                    client,
                    fallback_workflow,
                    fallback_spec,
                    prompt,
                    pipeline_format,
                    num,
                    img_path,
                    image_jobs,
                    attempt_label="fallback",
                )
            
            if ok:
                kb = img_path.stat().st_size // 1024
                stats["generated"] += 1
                if (image_jobs.get(str(num)) or {}).get("attempt") == "fallback":
                    stats["fallback"] += 1
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: OK ({kb}KB)")
            else:
                stats["failed"] += 1
                image_jobs.setdefault(str(num), {}).update({"status": "failed", "failedAt": datetime_now_iso()})
                _save_image_jobs(images_dir, image_jobs)
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: FALLO")
        _save_image_jobs(images_dir, image_jobs)
    
    recovered = recover_missing_images_from_metadata(scenes, images_dir)
    stats["recovered"] += recovered
    validation = validate_image_assets(scenes, images_dir)
    stats["missing"] = validation["missing"]
    stats["invalid"] = validation["invalid"]
    print(f"\n   Resumen {workflow_spec['label']}: {stats['generated']} generadas, {stats['skipped']} existentes, {stats['failed']} fallidas")
    if stats["fallback"]:
        print(f"   Fallback FLUX/Krea: {stats['fallback']} imágenes")
    if stats["recovered"]:
        print(f"   Recovery remoto: {stats['recovered']} imágenes descargadas")
    if stats["missing"] or stats["invalid"]:
        print(f"   [!] Visuales incompletos — missing={stats['missing']} invalid={stats['invalid']}")
    return stats


def generate_flux_images(scenes, images_dir, workflow_path, pipeline_format="narrativa"):
    """Compatibilidad para tests/scripts antiguos: fuerza el workflow FLUX."""
    spec = _select_image_workflow("narrativa")
    spec["workflow"] = Path(workflow_path)
    return generate_comfy_images(scenes, images_dir, spec, pipeline_format=pipeline_format)


# ============================================================
# PASO 2: GENERAR NARRACIÓN (ElevenLabs)
# ============================================================
def generate_narration(scenes, audio_dir, agent_name=""):
    """Genera narración con ElevenLabs, auto-seleccionando voz por agente."""
    voice = get_voice_for_agent(agent_name) if agent_name else DEFAULT_VOICE
    settings = get_voice_settings(voice)
    
    print("\n" + "=" * 60)
    print(f"   PASO 2: Narración ElevenLabs")
    print(f"   Voz: {voice} | Agente: {agent_name or 'default'}")
    print("=" * 60)
    
    stats = generate_scene_narrations(
        scenes, audio_dir, voice=voice, skip_existing=True
    )
    return stats


# ============================================================
# UTILIDAD: Obtener duración de audio
# ============================================================
def get_audio_duration(audio_path):
    """Obtiene la duración en segundos de un archivo de audio."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=10
        )
        return float(probe.stdout.strip())
    except:
        return 5.0  # fallback


def _target_duration_for_scene(scene: dict, fallback_duration: float = 5.0) -> float:
    """Returns the explicit long-form scene duration when present."""
    for key in ("target_duration_seconds", "targetDurationSeconds", "duration_seconds"):
        value = scene.get(key)
        try:
            numeric = float(value)
            if numeric > 0:
                return numeric
        except Exception:
            continue
    return float(fallback_duration)


def _pad_long_meditation_audio_segments(scenes, audio_dir: Path) -> dict:
    """
    Extends each spoken segment with silence until its target scene duration.
    This keeps TTS cost bounded while producing 30m/1h/3h sessions.
    """
    stats = {"padded": 0, "skipped": 0, "missing": [], "failed": []}
    print("\n" + "=" * 60)
    print("   PASO 2B: Espaciando voz para meditación larga")
    print("=" * 60)

    for scene in scenes:
        num = _scene_number(scene)
        if not num:
            continue
        audio_path = audio_dir / f"narration_{num:04d}.mp3"
        if not audio_path.exists() or audio_path.stat().st_size < 1000:
            stats["missing"].append(num)
            continue

        current_duration = get_audio_duration(audio_path)
        target_duration = _target_duration_for_scene(scene, current_duration)
        if current_duration >= target_duration - 1.0:
            stats["skipped"] += 1
            continue

        padded_path = audio_dir / f"narration_{num:04d}.padded.mp3"
        pad_seconds = max(0.0, target_duration - current_duration)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-af", f"apad=pad_dur={pad_seconds:.3f},atrim=0:{target_duration:.3f}",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(padded_path),
        ]
        timeout = max(60, min(900, int(target_duration * 0.15)))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and padded_path.exists() and padded_path.stat().st_size > 1000:
            padded_path.replace(audio_path)
            stats["padded"] += 1
        else:
            stats["failed"].append(num)
            print(f"   [!] Escena {num}: no se pudo espaciar audio: {result.stderr[:200]}")

    print(f"   Resumen: {stats['padded']} espaciadas, {stats['skipped']} ya listas")
    if stats["missing"] or stats["failed"]:
        print(f"   [!] Audio incompleto — missing={stats['missing']} failed={stats['failed']}")
    return stats


# ============================================================
# PASO 3A: KEN BURNS — Sincronizado con audio
# ============================================================
def apply_ken_burns_all(scenes, images_dir, kenburns_dir, audio_dir, fallback_duration=5):
    """Aplica Ken Burns con duración sincronizada al audio de cada escena."""
    effects = ["breathe_in", "drift_right", "breathe_out", "drift_left", "drift_up", "drift_down"]
    fps = 30
    stats = {"generated": 0, "skipped": 0, "missing": [], "failed": []}
    
    print("\n" + "=" * 60)
    print("   PASO 3: Ken Burns Effect (sincronizado con audio)")
    print("=" * 60)
    
    kenburns_dir.mkdir(parents=True, exist_ok=True)
    
    for i, scene in enumerate(scenes):
        num = scene["scene_number"]
        img_path = images_dir / f"scene_{num:04d}.png"
        vid_path = kenburns_dir / f"scene_{num:04d}.mp4"
        audio_path = audio_dir / f"narration_{num:04d}.mp3"
        effect = effects[(num - 1) % len(effects)]
        
        if vid_path.exists() and vid_path.stat().st_size > 10000:
            stats["skipped"] += 1
            continue
        
        if not img_path.exists() or img_path.stat().st_size < IMAGE_MIN_BYTES:
            stats["missing"].append(num)
            print(f"   [!] Escena {num}: imagen ausente o inválida")
            continue
        
        # Obtener duración del audio de esta escena
        if audio_path.exists():
            duration = get_audio_duration(audio_path)
        else:
            duration = fallback_duration
        
        # Buffer de +0.06s para compensar drift por redondeo de frames
        # El -shortest del merge final recorta el excedente
        duration_buffered = duration + 0.06
        
        tf = int(duration_buffered * fps)
        if tf < fps:  # mínimo 1 segundo
            tf = fps
        
        effects_map = {
            "breathe_in": f"zoompan=z='1+0.04*on/{tf}':x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih/2-(ih/zoom/2))':d={tf}:s=1920x1080:fps={fps}",
            "breathe_out": f"zoompan=z='1.04-0.04*on/{tf}':x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih/2-(ih/zoom/2))':d={tf}:s=1920x1080:fps={fps}",
            "drift_right": f"zoompan=z='1.05':x='trunc(on*(iw-iw/zoom)/{tf})':y='trunc(ih/2-(ih/zoom/2))':d={tf}:s=1920x1080:fps={fps}",
            "drift_left": f"zoompan=z='1.05':x='trunc(iw-iw/zoom-on*(iw-iw/zoom)/{tf})':y='trunc(ih/2-(ih/zoom/2))':d={tf}:s=1920x1080:fps={fps}",
            "drift_up": f"zoompan=z='1.05':x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih-ih/zoom-on*(ih-ih/zoom)/{tf})':d={tf}:s=1920x1080:fps={fps}",
            "drift_down": f"zoompan=z='1.05':x='trunc(iw/2-(iw/zoom/2))':y='trunc(on*(ih-ih/zoom)/{tf})':d={tf}:s=1920x1080:fps={fps}",
        }
        
        zoompan = effects_map.get(effect, effects_map["breathe_in"])
        cmd = [
            "ffmpeg", "-y", "-i", str(img_path),
            "-vf", zoompan,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "18", "-t", str(duration_buffered),
            str(vid_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and vid_path.exists():
            stats["generated"] += 1
            if (i + 1) % 10 == 0:
                print(f"   [{i+1}/{len(scenes)}] Ken Burns procesados... ({duration:.1f}s/escena)")
        else:
            stats["failed"].append(num)
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: Ken Burns falló")
    
    print(f"   Resumen: {stats['generated']} generados, {stats['skipped']} existentes")
    if stats["missing"] or stats["failed"]:
        print(f"   [!] Movimiento incompleto — missing={stats['missing']} failed={stats['failed']}")
    return stats


def apply_static_meditation_visuals_all(scenes, images_dir, kenburns_dir, audio_dir, fallback_duration=300):
    """
    Low-motion renderer for long meditations. It avoids 30fps zoompan over
    multi-hour videos, using still-image clips at low FPS for predictable cost.
    """
    fps = LONG_MEDITATION_STATIC_FPS
    stats = {"generated": 0, "skipped": 0, "missing": [], "failed": []}

    print("\n" + "=" * 60)
    print("   PASO 3: Visuales casi estáticos (meditación larga)")
    print("=" * 60)

    kenburns_dir.mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(scenes):
        num = _scene_number(scene)
        img_path = images_dir / f"scene_{num:04d}.png"
        vid_path = kenburns_dir / f"scene_{num:04d}.mp4"
        audio_path = audio_dir / f"narration_{num:04d}.mp3"

        if vid_path.exists() and vid_path.stat().st_size > 1000:
            stats["skipped"] += 1
            continue

        if not img_path.exists() or img_path.stat().st_size < IMAGE_MIN_BYTES:
            stats["missing"].append(num)
            print(f"   [!] Escena {num}: imagen ausente o inválida")
            continue

        duration = get_audio_duration(audio_path) if audio_path.exists() else _target_duration_for_scene(scene, fallback_duration)
        duration_buffered = duration + 0.06
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,setsar=1,"
            f"fps={fps},format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-t", f"{duration_buffered:.3f}",
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "24",
            "-tune", "stillimage",
            "-r", str(fps),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(vid_path),
        ]
        timeout = max(120, min(1800, int(duration_buffered * 0.35)))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and vid_path.exists() and vid_path.stat().st_size > 1000:
            stats["generated"] += 1
            print(f"   [{i+1}/{len(scenes)}] Visual lento listo ({duration/60:.1f} min)")
        else:
            stats["failed"].append(num)
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: visual lento falló")

    print(f"   Resumen: {stats['generated']} generados, {stats['skipped']} existentes")
    if stats["missing"] or stats["failed"]:
        print(f"   [!] Visuales lentos incompletos — missing={stats['missing']} failed={stats['failed']}")
    return stats


# ============================================================
# PASO 3B: LUMA CLIPS (Cinemático)
# ============================================================
def generate_luma_clips(scenes, images_dir, luma_dir, max_luma=15):
    """Genera clips cinemáticos con Luma AI para escenas seleccionadas."""
    
    # Seleccionar escenas para Luma (intro, clímax, cierre + distribuidas)
    total = len(scenes)
    if max_luma >= total:
        luma_indices = list(range(total))
    else:
        # Siempre incluir: primera, última, y distribuir el resto
        luma_indices = [0, total - 1]  # intro y cierre
        
        # Distribuir uniformemente las restantes
        remaining = max_luma - 2
        if remaining > 0:
            step = total / (remaining + 1)
            for j in range(1, remaining + 1):
                idx = int(j * step)
                if idx not in luma_indices and idx < total:
                    luma_indices.append(idx)
        
        luma_indices = sorted(set(luma_indices))[:max_luma]
    
    luma_scenes = [scenes[i] for i in luma_indices]
    
    print("\n" + "=" * 60)
    print(f"   PASO 3B: Luma AI — Clips Cinemáticos")
    print(f"   Escenas seleccionadas: {len(luma_scenes)} de {total}")
    print(f"   Índices: {[scenes[i]['scene_number'] for i in luma_indices]}")
    print("=" * 60)
    
    stats = generate_cinematic_clips(
        luma_scenes, images_dir, luma_dir, skip_existing=True
    )
    return stats, luma_indices


# ============================================================
# PASO 4: ENSAMBLAR VIDEO FINAL (sync perfecto)
# ============================================================
def assemble_final_video(
    scenes,
    project_dir,
    mode,
    luma_indices=None,
    format_label=None,
    music_config=None,
    low_motion=False,
):
    """
    Ensamblaje con sync perfecto:
    1. Crear master audio (concatenar todas las narraciones)
    2. Crear visual por escena:
       - Normal: Ken Burns (ya sincronizado)
       - Luma: 5s nativo + xfade 0.5s + Ken Burns el resto
    3. Concatenar todos los visuales en master visual
    4. Merge master_visual + master_audio → FINAL
    """
    kenburns_dir = project_dir / "kenburns"
    luma_dir = project_dir / "luma_clips"
    audio_dir = project_dir / "audio"
    composites_dir = project_dir / "composites"
    composites_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 60)
    print("   PASO 4: Ensamblaje Final (v3 — sync perfecto)")
    print("=" * 60)
    
    # ── STEP 1: Crear master audio ──
    print("   4.1 Creando master audio...")
    master_audio = project_dir / "master_audio.mp3"
    narration_files = sorted(audio_dir.glob("narration_*.mp3"))
    
    if not narration_files:
        print("   [!] No hay narraciones")
        return None
    
    audio_list = project_dir / "_audio_list.txt"
    with open(audio_list, "w", encoding="utf-8") as f:
        for af in narration_files:
            safe_path = str(af.absolute()).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(audio_list), "-c", "copy", str(master_audio)
    ], capture_output=True, text=True)
    audio_list.unlink(missing_ok=True)

    master_audio = _mix_background_music(master_audio, project_dir, music_config or {})

    master_audio_dur = get_audio_duration(master_audio)
    print(f"   Master audio: {master_audio_dur:.1f}s ({master_audio_dur/60:.1f} min)")
    
    # ── STEP 2: Crear visual por escena ──
    print("   4.2 Creando visuales por escena...")
    visual_clips = []
    luma_count = 0
    xfade_dur = 0.5  # crossfade entre Luma y Ken Burns
    
    for i, scene in enumerate(scenes):
        num = scene["scene_number"]
        kb_path = kenburns_dir / f"scene_{num:04d}.mp4"
        
        if not kb_path.exists():
            continue
        
        # ¿Es escena Luma?
        is_luma = (mode == "cinematico" and luma_indices and i in luma_indices)
        luma_path = luma_dir / f"luma_{num:04d}.mp4" if is_luma else None
        
        if is_luma and luma_path and luma_path.exists():
            # ── Escena Luma: 5s Luma nativo + xfade + Ken Burns restante ──
            composite_path = composites_dir / f"composite_{num:04d}.mp4"
            luma_dur = get_audio_duration(luma_path)
            kb_dur = get_audio_duration(kb_path)
            total_target = kb_dur  # Ken Burns ya tiene la duración del audio
            
            # Offset del xfade = cuando termina Luma menos overlap
            offset = max(luma_dur - xfade_dur, 0.5)
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(luma_path),
                "-i", str(kb_path),
                "-filter_complex",
                f"[0:v]scale=1920:1080,fps=30,setsar=1[luma];"
                f"[1:v]fps=30,setsar=1[kb];"
                f"[luma][kb]xfade=transition=fade:duration={xfade_dur}:offset={offset:.2f}[v]",
                "-map", "[v]", "-an",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-t", f"{total_target:.2f}",
                str(composite_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and composite_path.exists():
                visual_clips.append(composite_path)
                luma_count += 1
            else:
                # Fallback: usar Ken Burns solo
                visual_clips.append(kb_path)
        else:
            # ── Escena normal: Ken Burns directo ──
            visual_clips.append(kb_path)
        
        if (i + 1) % 10 == 0:
            print(f"   [{i+1}/{len(scenes)}] visuales procesados...")
    
    if not visual_clips:
        print("   [!] No hay clips visuales")
        return None

    if len(visual_clips) != len(scenes):
        expected = [_scene_number(scene) for scene in scenes]
        present = []
        for scene in scenes:
            num = _scene_number(scene)
            if (kenburns_dir / f"scene_{num:04d}.mp4").exists():
                present.append(num)
        missing = [num for num in expected if num and num not in present]
        print(f"   [!] Visuales incompletos para montaje final — missing={missing}")
        return None
    
    print(f"   {len(visual_clips)} clips ({luma_count} Luma+KB composites)")
    
    # ── STEP 3: Concatenar todos los visuales ──
    print("   4.3 Concatenando visual master...")
    master_visual = project_dir / "master_visual.mp4"
    vis_list = project_dir / "_visual_list.txt"
    
    with open(vis_list, "w", encoding="utf-8") as f:
        for vf in visual_clips:
            safe_path = str(vf.absolute()).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
    
    # Concat con re-encode para uniformizar codec entre KB y composites
    target_fps = LONG_MEDITATION_STATIC_FPS if low_motion else 30
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(vis_list), "-an",
        "-c:v", "libx264",
        "-preset", "veryfast" if low_motion else "fast",
        "-crf", "24" if low_motion else "20",
        "-pix_fmt", "yuv420p", "-r", str(target_fps),
        str(master_visual)
    ]
    
    result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=1800)
    vis_list.unlink(missing_ok=True)
    
    if result.returncode != 0 or not master_visual.exists():
        print(f"   [!] Error concat visual: {result.stderr[:300]}")
        return None
    
    master_visual_dur = get_audio_duration(master_visual)
    print(f"   Master visual: {master_visual_dur:.1f}s ({master_visual_dur/60:.1f} min)")
    print(f"   Master audio:  {master_audio_dur:.1f}s ({master_audio_dur/60:.1f} min)")
    print(f"   Diferencia:    {master_visual_dur - master_audio_dur:+.1f}s")
    
    # ── STEP 4: Merge final (video + audio) ──
    print("   4.4 Merge final...")
    safe_title = project_dir.name
    label = format_label or mode
    final_video = project_dir / f"FINAL_{label}_{safe_title}.mp4"

    # FIX B7 (2026-05-03): si el video es más corto que el audio, `-shortest`
    # cortaba la narración 1-2s antes del final. Ahora detectamos el déficit
    # y extendemos el video clonando el último frame (tpad) + 0.5s de aire
    # para que la última palabra termine de pronunciarse antes del fade.
    # Si video >= audio: stream copy directo (rápido, sin re-encode).
    audio_deficit = master_audio_dur - master_visual_dur
    needs_pad = audio_deficit > 0.05  # tolerance 50ms
    pad_seconds = audio_deficit + 0.5  # extra 0.5s de respiración al final

    if needs_pad:
        print(f"   [PAD] Video {audio_deficit:.2f}s más corto que audio — extendiendo último frame +{pad_seconds:.2f}s")
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(master_visual),
            "-i", str(master_audio),
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={pad_seconds:.3f}[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "veryfast" if low_motion else "fast",
            "-crf", "24" if low_motion else "20",
            "-pix_fmt", "yuv420p", "-r", str(target_fps),
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",  # ahora el shortest = audio (que termina antes del pad extra)
            "-movflags", "+faststart",
            str(final_video)
        ]
    else:
        # Video con buffer suficiente: merge directo (rápido)
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(master_visual),
            "-i", str(master_audio),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(final_video)
        ]
    
    result = subprocess.run(mix_cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0 and final_video.exists():
        valid_final, final_dur, validation_error = validate_media_file(
            final_video,
            min_duration_seconds=30,
        )
        if not valid_final:
            print(f"   [!] Video final invalido: {validation_error}")
            return None
        size_mb = final_video.stat().st_size / (1024 * 1024)
        dur_min = int(final_dur // 60)
        dur_sec = int(final_dur % 60)
        
        print(f"   [OK] Video final: {final_video.name}")
        print(f"   [OK] Tamaño: {size_mb:.1f}MB | Duración: {dur_min}:{dur_sec:02d}")
        return final_video
    else:
        print(f"   [!] Error merge: {result.stderr[:300]}")
        return None


# ============================================================
# MAIN — PIPELINE UNIFICADO
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
═══════════════════════════════════════════════════════════════
  CONTENT FACTORY v2.0 — Pipeline Unificado
═══════════════════════════════════════════════════════════════

  Uso:
    python factory.py <FULL_json> [opciones]

  Modos:
    --mode narrativa     FLUX + ElevenLabs + Ken Burns (default)
    --mode cinematico    FLUX + ElevenLabs + Luma + Ken Burns

  Opciones:
    --voice NAME         Forzar voz (Salvatore, Lorenzo, Diego, Serafina)
    --luma-scenes N      Número de escenas Luma en cinemático (default: 15)
    --images-only        Solo generar imágenes
    --skip-images        Saltar generación de imágenes
    --skip-assembly      No ensamblar video final

  Ejemplos:
    python factory.py guion.json --mode narrativa
    python factory.py guion.json --mode cinematico --luma-scenes 8
    python factory.py guion.json --mode cinematico --voice Serafina
        """)
        sys.exit(1)
    
    # Parse argumentos
    json_path = Path(sys.argv[1])
    mode = "narrativa"
    forced_voice = None
    luma_scenes = 15
    images_only = "--images-only" in sys.argv
    skip_images = "--skip-images" in sys.argv
    skip_assembly = "--skip-assembly" in sys.argv
    
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1].lower()
    
    if "--voice" in sys.argv:
        idx = sys.argv.index("--voice")
        if idx + 1 < len(sys.argv):
            forced_voice = sys.argv[idx + 1]
    
    if "--luma-scenes" in sys.argv:
        idx = sys.argv.index("--luma-scenes")
        if idx + 1 < len(sys.argv):
            luma_scenes = int(sys.argv[idx + 1])
    
    # Cargar guión
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data.get("video_scenes", [])
    if not scenes:
        print("[!] No se encontraron escenas en el JSON")
        sys.exit(1)

    pipeline_format = data.get("format", "narrativa")
    is_long_meditation_format = pipeline_format == LONG_MEDITATION_FORMAT

    # Algunos formatos usan visuales atmosféricos y largos; Luma no aporta
    # suficiente valor frente a visuales lentos y encarece el resultado.
    if pipeline_format in {"podcast", *WELLNESS_FORMATS} and mode == "cinematico":
        print(f"⚠️  Format={data.get('format')} detectado — overrideando mode 'cinematico' a 'narrativa'")
        mode = "narrativa"

    # Label visible en filename: refleja el formato real, no el modo interno del pipeline.
    format_label = pipeline_format if pipeline_format in {"podcast", *WELLNESS_FORMATS} else mode

    # Determinar título y agente
    # Usar topic para nombre de carpeta (consistente con VPS)
    raw_title = data.get("topic", "video_sin_titulo")
    seo_title = data.get("seo_metadata", {}).get("title", raw_title)
    safe_title = _resolve_output_folder(data)
    agent_name = data.get("agent", data.get("agent_name", ""))
    
    # Directorios del proyecto
    project_dir = BASE_DIR / "output" / "videos" / safe_title
    images_dir = project_dir / "images"
    kenburns_dir = project_dir / "kenburns"
    audio_dir = project_dir / "audio"
    luma_dir = project_dir / "luma_clips"
    
    for d in [images_dir, kenburns_dir, audio_dir]:
        d.mkdir(parents=True, exist_ok=True)
    if mode == "cinematico":
        luma_dir.mkdir(parents=True, exist_ok=True)
    
    # Determinar voz
    voice = forced_voice or get_voice_for_agent(agent_name) or DEFAULT_VOICE
    
    # ════════════════════════════════════════════════════════
    # BANNER
    # ════════════════════════════════════════════════════════
    mode_emoji = "🎬" if mode == "narrativa" else "🎥"
    
    pipeline_start = time.time()
    
    print("\n" + "═" * 60)
    print(f"  {mode_emoji} CONTENT FACTORY v2.0 — {mode.upper()}")
    print("═" * 60)
    print(f"   📖 {raw_title}")
    print(f"   🎬 {len(scenes)} escenas")
    print(f"   🎙️ Voz: {voice}")
    print(f"   🤖 Agente: {agent_name or 'general'}")
    if mode == "cinematico":
        print(f"   🎥 Luma clips: {luma_scenes}")
    print("═" * 60)
    
    # ════════════════════════════════════════════════════════
    # PASO 1: IMÁGENES
    # ════════════════════════════════════════════════════════
    image_workflow = _select_image_workflow(pipeline_format)
    if not skip_images and not images_only:
        flux_stats = generate_comfy_images(
            scenes,
            images_dir,
            image_workflow,
            pipeline_format=pipeline_format,
        )
    elif images_only:
        flux_stats = generate_comfy_images(
            scenes,
            images_dir,
            image_workflow,
            pipeline_format=pipeline_format,
        )
        print(f"\n   Modo --images-only: terminado.")
        if flux_stats.get("missing") or flux_stats.get("invalid"):
            print(f"   [!] --images-only incompleto: missing={flux_stats.get('missing')} invalid={flux_stats.get('invalid')}")
            sys.exit(2)
        sys.exit(0)

    image_validation = validate_image_assets(scenes, images_dir)
    if image_validation["missing"] or image_validation["invalid"]:
        print(f"   [!] Visuales incompletos antes de voz: missing={image_validation['missing']} invalid={image_validation['invalid']}")
        sys.exit(2)
    
    # ════════════════════════════════════════════════════════
    # PASO 2: NARRACIÓN ELEVENLABS
    # ════════════════════════════════════════════════════════
    # Bifurcación por formato: podcast usa dual narration (2 voces alternando
    # por dialogue_block), narrativa/cinematico usa single voice.
    is_podcast_format = data.get("format") == "podcast"
    if is_podcast_format:
        podcast_cfg = data.get("podcast") or {}
        voice_a = (podcast_cfg.get("host_a") or {}).get("voice") or "Salvatore"
        voice_b = (podcast_cfg.get("host_b") or {}).get("voice") or "Serafina"
        print("\n" + "=" * 60)
        print(f"   PASO 2: Narración PODCAST (dual voice)")
        print(f"   Host A: {voice_a} | Host B: {voice_b}")
        print("=" * 60)
        tts_stats = generate_dual_narration(
            scenes, audio_dir,
            voice_a=voice_a, voice_b=voice_b,
            skip_existing=True,
        )
    else:
        tts_stats = generate_narration(scenes, audio_dir, agent_name)

    if is_long_meditation_format:
        pad_stats = _pad_long_meditation_audio_segments(scenes, audio_dir)
        if pad_stats.get("missing") or pad_stats.get("failed"):
            print(f"   [!] Audio meditación larga incompleto: missing={pad_stats.get('missing')} failed={pad_stats.get('failed')}")
            sys.exit(2)
    
    # ════════════════════════════════════════════════════════
    # PASO 3: VISUALES (Ken Burns + Luma según modo)
    # ════════════════════════════════════════════════════════
    luma_indices = None
    
    # Ken Burns para formatos narrativos; visuales estáticos para meditación larga.
    if is_long_meditation_format:
        kb_stats = apply_static_meditation_visuals_all(scenes, images_dir, kenburns_dir, audio_dir)
    else:
        kb_stats = apply_ken_burns_all(scenes, images_dir, kenburns_dir, audio_dir)
    if kb_stats.get("missing") or kb_stats.get("failed"):
        print(f"   [!] Movimiento incompleto: missing={kb_stats.get('missing')} failed={kb_stats.get('failed')}")
        sys.exit(2)
    
    # Luma solo en modo cinemático
    if mode == "cinematico":
        luma_stats, luma_indices = generate_luma_clips(
            scenes, images_dir, luma_dir, max_luma=luma_scenes
        )
    
    # ════════════════════════════════════════════════════════
    # PASO 4: ENSAMBLAJE FINAL
    # ════════════════════════════════════════════════════════
    final_video = None
    if not skip_assembly:
        final_video = assemble_final_video(
            scenes,
            project_dir,
            mode,
            luma_indices,
            format_label=format_label,
            music_config=_get_autohypnosis_music_config(data),
            low_motion=is_long_meditation_format,
        )
    
    # ════════════════════════════════════════════════════════
    # PASO 5: SUBTÍTULOS (Whisper + ASS + FFmpeg)
    # ════════════════════════════════════════════════════════
    skip_subs = "--skip-subs" in sys.argv or is_long_meditation_format
    subtitled_video = None
    
    if final_video and not skip_subs:
        try:
            master_audio = project_dir / "master_audio.mp3"
            subtitled_video = add_subtitles_to_video(
                video_path=final_video,
                audio_path=master_audio if master_audio.exists() else None
            )
            if subtitled_video:
                # El video subtitulado es ahora el principal
                final_video = subtitled_video
        except Exception as e:
            print(f"   ⚠️ Subtítulos fallaron (video sin subs disponible): {e}")
    
    # ════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ════════════════════════════════════════════════════════
    total_time = (time.time() - pipeline_start) / 60
    
    print("\n" + "═" * 60)
    print(f"  🏆 PRODUCCIÓN FINALIZADA — {mode.upper()}")
    print("═" * 60)
    print(f"   ⏱️  Tiempo total: {total_time:.1f} minutos")
    print(f"   📖 {raw_title}")
    print(f"   🎙️ Voz: {voice}")
    if final_video:
        size_mb = final_video.stat().st_size / (1024 * 1024)
        print(f"   🎥 Video final: {final_video.name} ({size_mb:.1f}MB)")
    if subtitled_video:
        print(f"   📝 Subtítulos: ✅ Incluidos")
    else:
        print(f"   📝 Subtítulos: ⚠️ No disponibles")
    print(f"   📁 Proyecto: {project_dir}")
    print("═" * 60)
