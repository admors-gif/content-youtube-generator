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


# ============================================================
# PASO 1: GENERAR IMÁGENES (FLUX via ComfyUI Cloud)
# ============================================================
def generate_flux_images(scenes, images_dir, workflow_path):
    """Genera imágenes FLUX para todas las escenas via ComfyUI Cloud."""
    with open(workflow_path, "r", encoding="utf-8") as f:
        base_workflow = json.load(f)
    
    stats = {"generated": 0, "skipped": 0, "failed": 0}
    
    print("\n" + "=" * 60)
    print("   PASO 1: Generando Imágenes FLUX")
    print("=" * 60)
    
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        for i, scene in enumerate(scenes):
            num = scene["scene_number"]
            prompt = scene["prompt"]
            img_path = images_dir / f"scene_{num:04d}.png"
            
            # Skip si ya existe
            if img_path.exists() and img_path.stat().st_size > 5000:
                stats["skipped"] += 1
                continue
            
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: generando imagen...")
            
            # Preparar workflow
            nodes = copy.deepcopy(base_workflow)
            nodes["200:195"]["inputs"]["text"] = f"Highly realistic cinematic film still, masterpiece, 8k resolution, anatomically perfect human proportions, natural facial features, correct number of fingers, photorealistic skin texture. {prompt}"
            nodes["200:197"]["inputs"]["seed"] = random.randint(100000000000000, 999999999999999)
            nodes["200:196"]["inputs"]["width"] = 1344
            nodes["200:196"]["inputs"]["height"] = 768
            nodes["9"]["inputs"]["filename_prefix"] = f"scene_{num:04d}"
            
            # Enviar a ComfyUI
            resp = client.post(f"{COMFYUI_BASE}/prompt", headers=COMFYUI_HEADERS, json={"prompt": nodes})
            if resp.status_code != 200:
                stats["failed"] += 1
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: HTTP {resp.status_code}")
                continue
            
            prompt_id = resp.json()["prompt_id"]
            
            # Poll hasta completar
            ok = False
            for attempt in range(60):  # 5 min max
                time.sleep(5)
                try:
                    jr = client.get(f"{COMFYUI_BASE}/jobs/{prompt_id}", headers=COMFYUI_HEADERS)
                    if jr.status_code != 200:
                        continue
                    job = jr.json()
                    status = job.get("status", "unknown")
                    
                    if status == "completed":
                        outputs = job.get("outputs", {})
                        for node_id, node_out in outputs.items():
                            if isinstance(node_out, dict) and "images" in node_out:
                                for img_info in node_out["images"]:
                                    fname = img_info.get("filename", "")
                                    subfolder = img_info.get("subfolder", "")
                                    dl = client.get(
                                        f"{COMFYUI_BASE}/view", headers=COMFYUI_HEADERS,
                                        params={"filename": fname, "subfolder": subfolder, "type": "output"}
                                    )
                                    if dl.status_code == 200 and len(dl.content) > 1000:
                                        img_path.parent.mkdir(parents=True, exist_ok=True)
                                        with open(img_path, "wb") as f:
                                            f.write(dl.content)
                                        ok = True
                        break
                    elif status in ("failed", "error"):
                        break
                except:
                    pass
            
            if ok:
                kb = img_path.stat().st_size // 1024
                stats["generated"] += 1
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: OK ({kb}KB)")
            else:
                stats["failed"] += 1
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: FALLO")
    
    print(f"\n   Resumen FLUX: {stats['generated']} generadas, {stats['skipped']} existentes, {stats['failed']} fallidas")
    return stats


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


# ============================================================
# PASO 3A: KEN BURNS — Sincronizado con audio
# ============================================================
def apply_ken_burns_all(scenes, images_dir, kenburns_dir, audio_dir, fallback_duration=5):
    """Aplica Ken Burns con duración sincronizada al audio de cada escena."""
    effects = ["breathe_in", "drift_right", "breathe_out", "drift_left", "drift_up", "drift_down"]
    fps = 30
    stats = {"generated": 0, "skipped": 0}
    
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
        
        if not img_path.exists():
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
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: Ken Burns falló")
    
    print(f"   Resumen: {stats['generated']} generados, {stats['skipped']} existentes")
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
def assemble_final_video(scenes, project_dir, mode, luma_indices=None):
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
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(vis_list), "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "30",
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
    final_video = project_dir / f"FINAL_{mode}_{safe_title}.mp4"

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
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30",
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
        size_mb = final_video.stat().st_size / (1024 * 1024)
        final_dur = get_audio_duration(final_video)
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

    # Si el formato es podcast, forzar modo narrativa: Luma no aplica para
    # podcasts (sus visuales son atmosphere/divulgación, no clips realistas).
    if data.get("format") == "podcast" and mode == "cinematico":
        print("⚠️  Format=podcast detectado — overrideando mode 'cinematico' a 'narrativa' (Luma no aplica)")
        mode = "narrativa"
    
    # Determinar título y agente
    # Usar topic para nombre de carpeta (consistente con VPS)
    raw_title = data.get("topic", "video_sin_titulo")
    seo_title = data.get("seo_metadata", {}).get("title", raw_title)
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
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
    # PASO 1: IMÁGENES FLUX
    # ════════════════════════════════════════════════════════
    if not skip_images and not images_only:
        workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
        flux_stats = generate_flux_images(scenes, images_dir, workflow_path)
    elif images_only:
        workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
        flux_stats = generate_flux_images(scenes, images_dir, workflow_path)
        print(f"\n   Modo --images-only: terminado.")
        sys.exit(0)
    
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
    
    # ════════════════════════════════════════════════════════
    # PASO 3: VISUALES (Ken Burns + Luma según modo)
    # ════════════════════════════════════════════════════════
    luma_indices = None
    
    # Ken Burns para todas las escenas (ambos modos)
    kb_stats = apply_ken_burns_all(scenes, images_dir, kenburns_dir, audio_dir)
    
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
        final_video = assemble_final_video(scenes, project_dir, mode, luma_indices)
    
    # ════════════════════════════════════════════════════════
    # PASO 5: SUBTÍTULOS (Whisper + ASS + FFmpeg)
    # ════════════════════════════════════════════════════════
    skip_subs = "--skip-subs" in sys.argv
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
