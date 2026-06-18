import hashlib
import json
import re
from datetime import datetime, timezone


DEFAULT_LANGUAGE = "es"
DEFAULT_STYLE = "latin_trap_anthem"
DEFAULT_INTENTION = "disciplina"


INTENTION_PRESETS = [
    {
        "id": "disciplina",
        "label": "Disciplina imparable",
        "description": "No negociar contigo, cumplir incluso cuando nadie mira.",
        "seed": "Hoy no negocio conmigo. Mi palabra pesa mas que mi excusa.",
    },
    {
        "id": "autoconfianza",
        "label": "Autoconfianza",
        "description": "Seguridad, presencia, voz interna fuerte y estable.",
        "seed": "Camino como alguien que ya recordo quien es.",
    },
    {
        "id": "entrenamiento",
        "label": "Entrenamiento / correr",
        "description": "Energia fisica, resistencia, fuego, ritmo de movimiento.",
        "seed": "Cada paso confirma que mi cuerpo obedece a mi vision.",
    },
    {
        "id": "manifestacion",
        "label": "Manifestacion presente",
        "description": "Identidad futura hablada en presente, logro con calma y poder.",
        "seed": "Ya vivo desde la version que antes imaginaba.",
    },
    {
        "id": "yo_nino",
        "label": "Mensaje a mi yo de niño",
        "description": "Proteccion, orgullo, promesa cumplida, ternura con garra.",
        "seed": "Vine por el niño que fui. Nadie lo vuelve a dejar atras.",
    },
    {
        "id": "yo_futuro",
        "label": "Mensaje de mi yo futuro",
        "description": "Vision, direccion, certeza y responsabilidad emocional.",
        "seed": "Te escribo desde la cima que hoy todavia parece lejos.",
    },
    {
        "id": "hambre_emocional",
        "label": "Control de impulsos",
        "description": "Elegir lo que construye, calmar ansiedad sin castigo corporal.",
        "seed": "Mi impulso no decide mi destino. Respiro, elijo, avanzo.",
    },
    {
        "id": "exito",
        "label": "Historia de mi exito",
        "description": "Narrativa de ascenso, enfoque, dinero, calma y vision.",
        "seed": "No fue suerte: fue enfoque repetido cuando nadie aplaudia.",
    },
]


STYLE_PRESETS = [
    {
        "id": "latin_trap_anthem",
        "label": "Latin trap anthem",
        "suno": "Spanish motivational Latin trap anthem, deep 808 bass, punchy drums, cinematic dark heroic atmosphere, confident male vocal, catchy hook, gym energy, premium radio quality",
        "bpm": "92-104",
    },
    {
        "id": "rap_garra",
        "label": "Rap con garra",
        "suno": "Spanish motivational rap, aggressive but elegant delivery, hard drums, powerful chorus, cinematic brass hits, disciplined warrior energy, modern mix, no romantic theme",
        "bpm": "88-98",
    },
    {
        "id": "house_running",
        "label": "House para correr",
        "suno": "Spanish empowerment house track, driving bassline, sunrise running energy, uplifting synths, euphoric drop, emotional chorus, clean modern club production",
        "bpm": "122-128",
    },
    {
        "id": "reggaeton_power",
        "label": "Reggaeton de poder",
        "suno": "Spanish motivational reggaeton, strong dembow rhythm, confident vocal, catchy chorus, urban premium production, empowering workout energy, no romantic dependency",
        "bpm": "92-100",
    },
    {
        "id": "electronic_cinematic",
        "label": "Electronica cinematica",
        "suno": "Spanish cinematic electronic anthem, massive synths, pulsing bass, emotional build up, powerful spoken-sung hook, futuristic confidence, epic drop",
        "bpm": "118-132",
    },
    {
        "id": "sax_power",
        "label": "Saxofon con poder",
        "suno": "Spanish motivational sax house anthem, powerful saxophone lead, deep bass, energetic percussion, luxury night drive feeling, triumphant chorus, premium mix",
        "bpm": "120-126",
    },
]


TARGET_USE_PRESETS = [
    "correr por la mañana",
    "entrenar fuerza",
    "caminar con enfoque",
    "empezar el dia",
    "trabajar profundo",
    "manejar de noche",
    "visualizar metas",
]


POWER_MUSIC_SYSTEM_PROMPT = """AI AGENT: POWER MUSIC ARCHITECT

ROLE
Eres un compositor premium de musica motivacional en español, experto en hooks, rap/trap/house/reggaeton/electronica, afirmaciones conscientes, narrativa de identidad y prompts para Suno.

CORE FORMULA
La cancion debe hacer que la persona quiera moverse, entrenar, correr, volver a intentar y actuar como su version mas fuerte. No escribes poesia plana: escribes canciones cantables, recordables, con coro viral y frases repetibles.

SAFETY AND ETHICS
- No uses mensajes ocultos ni manipulacion subliminal. Todo mensaje de autoprogramacion debe ser consciente, explicito y saludable.
- No prometas curacion medica, perdida de peso garantizada, riqueza garantizada ni resultados magicos.
- Si el tema toca comida, cuerpo o impulsos, enfocalo en autocuidado, calma, eleccion y fuerza; evita castigo, hambre extrema, culpa corporal o lenguaje de trastornos alimenticios.
- No imites artistas reales, voces reales, letras existentes ni estilos demasiado identificables de una persona especifica.
- No incluyas instrucciones ilegales, odio, violencia glorificada, humillacion corporal ni misoginia.

OUTPUT
Devuelve SOLO JSON valido. Sin markdown. Sin texto fuera del JSON.
"""


def compact_text(value, limit=400):
    text = " ".join(str(value or "").replace("\x00", " ").split()).strip()
    return text[:limit]


def style_by_id(style_id: str) -> dict:
    return next((item for item in STYLE_PRESETS if item["id"] == style_id), STYLE_PRESETS[0])


def intention_by_id(intention_id: str) -> dict:
    return next((item for item in INTENTION_PRESETS if item["id"] == intention_id), INTENTION_PRESETS[0])


def parse_json_object(text: str) -> dict:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_generation_prompt(payload: dict) -> str:
    intention = intention_by_id(str(payload.get("intention") or DEFAULT_INTENTION))
    style = style_by_id(str(payload.get("style") or DEFAULT_STYLE))
    theme = compact_text(payload.get("theme"), 180) or intention["label"]
    personal_angle = compact_text(payload.get("personalAngle") or payload.get("personal_angle"), 700)
    target_use = compact_text(payload.get("targetUse") or payload.get("target_use"), 120) or TARGET_USE_PRESETS[0]
    energy = compact_text(payload.get("energy"), 80) or "alta, elegante, determinada"
    vocal_perspective = compact_text(payload.get("vocalPerspective") or payload.get("vocal_perspective"), 80) or "primera persona"
    must_include = compact_text(payload.get("mustInclude") or payload.get("must_include"), 500)
    must_avoid = compact_text(payload.get("mustAvoid") or payload.get("must_avoid"), 500)
    language = compact_text(payload.get("language"), 20) or DEFAULT_LANGUAGE

    contract = {
        "language": language,
        "theme": theme,
        "intention": intention,
        "style": style,
        "targetUse": target_use,
        "energy": energy,
        "vocalPerspective": vocal_perspective,
        "personalAngle": personal_angle,
        "mustInclude": must_include,
        "mustAvoid": must_avoid,
    }

    return f"""
CONTRATO CREATIVO:
{json.dumps(contract, ensure_ascii=False, indent=2)}

Genera un paquete premium para crear una cancion en Suno y luego producir un video en Content Factory.

REQUISITOS DE CALIDAD:
- Letra completa en español, con estructura real de cancion.
- Debe sentirse moderna, fisica, repetible y emocionalmente poderosa.
- Crea un hook/coro que se pueda repetir corriendo o entrenando.
- Usa frases de identidad: soy, elijo, cumplo, avanzo, construyo.
- Incluye un mantra principal corto y memorable.
- Evita sonar generico, religioso obligatorio o coach barato.
- La letra debe estar optimizada para Suno: secciones claras entre corchetes.
- El prompt Suno debe ser copiables y en ingles, porque Suno suele responder mejor a descripciones musicales en ingles.
- Crea visuales premium sin depender de Luma: Comfy/Flux + Ken Burns + texto cinetico.

JSON SCHEMA EXACTO:
{{
  "title": "titulo de la cancion",
  "subtitle": "promesa corta",
  "intention": "intencion",
  "style": "estilo",
  "bpm": "rango bpm",
  "energy": "energia",
  "durationTarget": "2:30-3:30",
  "lyrics": "[Intro]...",
  "mainHook": "coro o frase principal",
  "mantra": "frase corta repetible",
  "sunoPrompt": "English Suno prompt...",
  "sunoPromptAlt": "English alternate prompt...",
  "negativePrompt": "English negative style prompt...",
  "coverPrompt": "prompt visual 1:1 premium para portada",
  "videoConcept": {{
    "visualIdentity": "identidad visual",
    "palette": ["color 1", "color 2", "color 3"],
    "scenes": [
      {{"section": "Intro", "visualPrompt": "prompt 16:9", "textOverlay": "texto corto"}},
      {{"section": "Verse 1", "visualPrompt": "prompt 16:9", "textOverlay": "texto corto"}},
      {{"section": "Chorus", "visualPrompt": "prompt 16:9", "textOverlay": "texto corto"}},
      {{"section": "Bridge", "visualPrompt": "prompt 16:9", "textOverlay": "texto corto"}},
      {{"section": "Final", "visualPrompt": "prompt 16:9", "textOverlay": "texto corto"}}
    ],
    "motionDirection": "Ken Burns, glow, particles, waveform, lyric punches"
  }},
  "youtube": {{
    "title": "titulo SEO YouTube",
    "description": "descripcion lista para publicar",
    "hashtags": ["#tag"],
    "tags": ["tag"],
    "thumbnailText": "texto corto para miniatura"
  }},
  "productionNotes": [
    "nota operativa"
  ],
  "safetyNotes": [
    "nota de seguridad editorial"
  ]
}}
"""


def _as_list(value, limit=12):
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        text = compact_text(item, 160)
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _word_list(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]+", str(text or "").lower())


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _score_power_music_package(package: dict) -> dict:
    lyrics = str(package.get("lyrics") or "")
    title = compact_text(package.get("title"), 160)
    hook = compact_text(package.get("mainHook") or package.get("mantra") or title, 160)
    prompt = compact_text(package.get("sunoPrompt"), 1200)
    words = _word_list(lyrics)
    lines = [line.strip() for line in lyrics.splitlines() if line.strip() and not line.strip().startswith("[")]
    section_count = len(re.findall(r"\[[^\]]+\]", lyrics))
    line_lengths = [len(_word_list(line)) for line in lines if _word_list(line)]
    avg_line = sum(line_lengths) / max(1, len(line_lengths))
    balance = 100 - min(70, (max(line_lengths or [0]) - min(line_lengths or [0])) * 4)
    hook_words = _word_list(hook)
    hook_hits = sum(1 for line in lines if hook and hook.lower() in line.lower())
    identity_hits = sum(lyrics.lower().count(term) for term in ["soy ", "elijo", "cumplo", "avanzo", "construyo", "promesa", "camino"])
    motion_hits = sum(lyrics.lower().count(term) for term in ["corro", "respiro", "levanto", "paso", "fuego", "hierro", "sudor", "amanece", "entreno"])
    last_words = [line.split()[-1] for line in lines if line.split()]
    rhyme_endings = [word[-3:] for word in _word_list("\n".join(last_words)) if len(word) >= 4]
    repeated_endings = len(rhyme_endings) - len(set(rhyme_endings))
    prompt_terms = sum(prompt.lower().count(term) for term in ["bpm", "bass", "drum", "hook", "chorus", "vocal", "mix", "master", "energy"])

    melody = _clamp_score(45 + min(25, section_count * 4) + min(20, hook_hits * 7) + min(10, repeated_endings * 2))
    lirica = _clamp_score(45 + min(20, identity_hits * 2.5) + min(15, motion_hits * 2) + min(20, len(set(words)) / max(1, len(words)) * 80))
    ritmo = _clamp_score(40 + min(25, balance * 0.25) + (20 if 5 <= avg_line <= 11 else 8) + min(15, section_count * 2))
    viralidad = _clamp_score(42 + min(24, hook_hits * 8) + (15 if 3 <= len(hook_words) <= 8 else 4) + min(19, identity_hits * 1.5))
    musica = _clamp_score(45 + min(35, prompt_terms * 4) + (10 if package.get("bpm") else 0) + (10 if package.get("sunoPromptAlt") else 0))
    coherencia = _clamp_score(48 + min(22, section_count * 3) + min(15, len(set(_word_list(title)) & set(words)) * 4) + (15 if package.get("intention") else 0))
    impacto = _clamp_score(45 + min(30, identity_hits * 3) + min(15, motion_hits * 2) + (10 if hook_hits >= 2 else 0))
    poder = _clamp_score(46 + min(30, identity_hits * 3) + min(14, prompt.lower().count("power") * 4 + prompt.lower().count("hero") * 3) + min(10, motion_hits))

    dimensions = {
        "melodia": melody,
        "lirica": lirica,
        "ritmo": ritmo,
        "viralidad": viralidad,
        "musica": musica,
        "coherencia": coherencia,
        "impacto": impacto,
        "poder": poder,
    }
    weights = {
        "melodia": 0.12,
        "lirica": 0.14,
        "ritmo": 0.13,
        "viralidad": 0.16,
        "musica": 0.12,
        "coherencia": 0.12,
        "impacto": 0.11,
        "poder": 0.10,
    }
    total = _clamp_score(sum(dimensions[key] * weights[key] for key in dimensions))
    strengths = []
    if hook_hits >= 2:
        strengths.append("Hook repetible dentro de la letra.")
    if identity_hits >= 6:
        strengths.append("Identidad fuerte: soy/elijo/cumplo/avanzo.")
    if prompt_terms >= 5:
        strengths.append("Prompt Suno bien armado para produccion musical.")
    if section_count >= 5:
        strengths.append("Estructura cantable con secciones claras.")
    risks = []
    if hook_hits < 2:
        risks.append("El hook podria repetirse mas para mejorar recordacion.")
    if avg_line > 13:
        risks.append("Algunas lineas pueden sentirse largas para Suno.")
    if section_count < 4:
        risks.append("Faltan secciones claras para guiar la cancion.")
    suggestions = []
    if viralidad < 75:
        suggestions.append("Repetir el mantra exacto al menos dos veces en coro/final.")
    if ritmo < 75:
        suggestions.append("Acortar lineas largas y mantener frases de 6 a 10 palabras.")
    if melody < 75:
        suggestions.append("Agregar un pre-coro con frase ascendente antes del hook.")

    return {
        "version": "power_music_lyric_score_v1",
        "total": total,
        "dimensions": dimensions,
        "strengths": strengths[:5],
        "risks": risks[:5],
        "suggestions": suggestions[:5],
        "calibration": "heuristic_zero_cost",
    }


def normalize_package(data: dict, payload: dict | None = None) -> dict:
    payload = payload or {}
    style = style_by_id(str(payload.get("style") or data.get("style") or DEFAULT_STYLE))
    intention = intention_by_id(str(payload.get("intention") or data.get("intention") or DEFAULT_INTENTION))
    title = compact_text(data.get("title"), 120) or f"{intention['label']}: no negocio conmigo"
    subtitle = compact_text(data.get("subtitle"), 180) or intention["description"]
    lyrics = str(data.get("lyrics") or "").strip()
    if not lyrics:
        lyrics = fallback_package(payload)["lyrics"]

    video = data.get("videoConcept") if isinstance(data.get("videoConcept"), dict) else {}
    scenes = video.get("scenes") if isinstance(video.get("scenes"), list) else []
    normalized_scenes = []
    for scene in scenes[:8]:
        if not isinstance(scene, dict):
            continue
        normalized_scenes.append({
            "section": compact_text(scene.get("section"), 60),
            "visualPrompt": compact_text(scene.get("visualPrompt"), 900),
            "textOverlay": compact_text(scene.get("textOverlay"), 60),
        })
    if not normalized_scenes:
        normalized_scenes = fallback_package(payload)["videoConcept"]["scenes"]

    youtube = data.get("youtube") if isinstance(data.get("youtube"), dict) else {}
    package = {
        "title": title,
        "subtitle": subtitle,
        "intention": compact_text(data.get("intention"), 80) or intention["label"],
        "style": compact_text(data.get("style"), 80) or style["label"],
        "bpm": compact_text(data.get("bpm"), 40) or style["bpm"],
        "energy": compact_text(data.get("energy"), 120) or compact_text(payload.get("energy"), 120) or "alta, enfocada, poderosa",
        "durationTarget": compact_text(data.get("durationTarget"), 40) or "2:30-3:30",
        "lyrics": lyrics,
        "mainHook": compact_text(data.get("mainHook"), 260),
        "mantra": compact_text(data.get("mantra"), 160),
        "sunoPrompt": compact_text(data.get("sunoPrompt"), 900) or style["suno"],
        "sunoPromptAlt": compact_text(data.get("sunoPromptAlt"), 900),
        "negativePrompt": compact_text(data.get("negativePrompt"), 500) or "no imitation of real artists, no copyrighted melody, no sad ending, no romantic dependency, no medical claims",
        "coverPrompt": compact_text(data.get("coverPrompt"), 900),
        "videoConcept": {
            "visualIdentity": compact_text(video.get("visualIdentity"), 260) or "premium motivational cinematic identity",
            "palette": _as_list(video.get("palette"), limit=6) or ["deep black", "electric gold", "crimson ember"],
            "scenes": normalized_scenes,
            "motionDirection": compact_text(video.get("motionDirection"), 360) or "Ken Burns, glow, particles, waveform and lyric punches.",
        },
        "youtube": {
            "title": compact_text(youtube.get("title"), 120) or title,
            "description": compact_text(youtube.get("description"), 1800),
            "hashtags": _as_list(youtube.get("hashtags"), limit=12),
            "tags": _as_list(youtube.get("tags"), limit=20),
            "thumbnailText": compact_text(youtube.get("thumbnailText"), 40) or title[:40],
        },
        "productionNotes": _as_list(data.get("productionNotes"), limit=10),
        "safetyNotes": _as_list(data.get("safetyNotes"), limit=10),
        "source": "power_music_studio",
        "createdAtIso": datetime.now(timezone.utc).isoformat(),
    }
    if not package["mainHook"]:
        package["mainHook"] = title
    if not package["mantra"]:
        package["mantra"] = intention["seed"]
    package["lyricScore"] = _score_power_music_package(package)
    return package


def fallback_package(payload: dict | None = None) -> dict:
    payload = payload or {}
    intention = intention_by_id(str(payload.get("intention") or DEFAULT_INTENTION))
    style = style_by_id(str(payload.get("style") or DEFAULT_STYLE))
    theme = compact_text(payload.get("theme"), 100) or intention["label"]
    title = f"{theme}: hoy no negocio conmigo"
    return {
        "title": title,
        "subtitle": intention["description"],
        "intention": intention["label"],
        "style": style["label"],
        "bpm": style["bpm"],
        "energy": "alta, enfocada, poderosa",
        "durationTarget": "2:30-3:30",
        "lyrics": (
            "[Intro]\n"
            "Hoy me levanto con fuego tranquilo\n"
            "no le pido permiso al miedo\n\n"
            "[Verse 1]\n"
            "Yo se de donde vengo, se lo que costo\n"
            "cada noche en silencio tambien me entreno\n"
            "si mi mente me prueba, no me voy a romper\n"
            "soy la voz que responde: lo vuelvo a hacer\n\n"
            "[Pre-Chorus]\n"
            "Respiro, me ordeno, camino de frente\n"
            "mi futuro me mira y me pide presente\n\n"
            "[Chorus]\n"
            "Hoy no negocio conmigo\n"
            "hoy no abandono mi plan\n"
            "si tiembla la voz, sigo vivo\n"
            "si pesa la vida, doy mas\n\n"
            "[Bridge]\n"
            "No soy mi impulso, no soy mi excusa\n"
            "soy lo que elijo cuando nadie me escucha\n\n"
            "[Final Chorus]\n"
            "Hoy no negocio conmigo\n"
            "lo dije y lo voy a cumplir\n"
            "mi historia cambio desde el dia\n"
            "que decidi volver por mi\n"
        ),
        "mainHook": "Hoy no negocio conmigo",
        "mantra": intention["seed"],
        "sunoPrompt": style["suno"],
        "sunoPromptAlt": f"{style['suno']}, stronger chorus, more cinematic build up, motivational anthem in Spanish",
        "negativePrompt": "no imitation of real artists, no copyrighted melody, no sad ending, no romantic dependency, no medical claims",
        "coverPrompt": "Premium cinematic motivational cover art, lone runner silhouette at sunrise, black and gold palette, electric ember glow, powerful discipline identity, no readable text, no logos",
        "videoConcept": {
            "visualIdentity": "premium discipline anthem, dark heroic sunrise, gold ember energy",
            "palette": ["deep black", "electric gold", "crimson ember"],
            "scenes": [
                {"section": "Intro", "visualPrompt": "cinematic dark room before sunrise, athletic shoes on floor, gold light line entering, premium motivational mood, 16:9", "textOverlay": "HOY EMPIEZA"},
                {"section": "Verse 1", "visualPrompt": "runner silhouette on empty street at dawn, cinematic mist, gold highlights, disciplined solitude, 16:9", "textOverlay": "SIN EXCUSAS"},
                {"section": "Chorus", "visualPrompt": "powerful abstract heart and fire waveform, black gold crimson, premium anthem energy, 16:9", "textOverlay": "NO NEGOCIO"},
                {"section": "Bridge", "visualPrompt": "mirror reflection transforming into stronger self, cinematic shadows, gold rim light, no readable text, 16:9", "textOverlay": "ELIJO"},
                {"section": "Final", "visualPrompt": "sunrise mountain road, triumphant lone figure, cinematic golden sky, premium victory mood, 16:9", "textOverlay": "CUMPLO"},
            ],
            "motionDirection": "Ken Burns slow push, lyric punches on chorus, subtle waveform, ember particles.",
        },
        "youtube": {
            "title": title,
            "description": "Cancion motivacional para entrenar disciplina, enfoque y autoconfianza. Escuchala cuando necesites volver a elegirte.",
            "hashtags": ["#motivacion", "#disciplina", "#entrenamiento", "#autoconfianza"],
            "tags": ["musica motivacional", "disciplina", "gym motivation", "cancion para correr"],
            "thumbnailText": "NO NEGOCIO",
        },
        "productionNotes": ["Pegar lyrics + Suno prompt en Suno; descargar audio y volver a Content Factory para video."],
        "safetyNotes": ["Mensajes conscientes, no subliminales ocultos; no contiene promesas medicas."],
        "source": "power_music_studio_fallback",
        "createdAtIso": datetime.now(timezone.utc).isoformat(),
    }


def _first_singable_line(lyrics: str) -> str:
    for raw_line in str(lyrics or "").splitlines():
        line = raw_line.strip()
        if not line or (line.startswith("[") and line.endswith("]")):
            continue
        clean = compact_text(line, 120)
        if clean:
            return clean
    return ""


def _song_sections_from_lyrics(lyrics: str, limit: int = 6) -> list[dict]:
    sections = []
    current = {"section": "Intro", "lines": []}
    for raw_line in str(lyrics or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.fullmatch(r"\[([^\]]{1,80})\]", line)
        if match:
            if current["lines"]:
                sections.append(current)
            current = {"section": compact_text(match.group(1), 60) or "Section", "lines": []}
            continue
        if len(current["lines"]) < 4:
            current["lines"].append(compact_text(line, 160))
    if current["lines"] or current["section"]:
        sections.append(current)

    clean = []
    seen = set()
    for item in sections:
        name = compact_text(item.get("section"), 60) or "Section"
        key = name.lower()
        if key in seen and not item.get("lines"):
            continue
        seen.add(key)
        clean.append({"section": name, "lines": [line for line in item.get("lines", []) if line]})
        if len(clean) >= limit:
            break
    if clean:
        return clean
    first = _first_singable_line(lyrics) or "La cancion habla de elegir una version mas fuerte."
    return [{"section": "Song", "lines": [first]}]


def _import_scene_prompt(section: str, sample_lines: list[str], visual_identity: str, style_label: str) -> str:
    sample = " / ".join(sample_lines[:3]) or section
    return compact_text(
        (
            "16:9 cinematic text-free music-video still, Flux/Krea photoreal editorial quality, "
            f"section {section}, inspired by these lyric ideas: {sample}. "
            f"Visual identity: {visual_identity}. Musical energy: {style_label}. "
            "Represent the emotion and action of the lyrics with a concrete scene, not a generic abstract background. "
            "Use strong subject, premium lighting, clean negative space, no readable text, no logos."
        ),
        900,
    )


def build_imported_song_package(payload: dict | None = None) -> dict:
    """Create a Power Music package from a song that already has lyrics.

    This is the safe path when the user wrote/generated the song in Suno first:
    Content Factory only builds metadata, score, visual direction and video
    prompts around the provided lyrics.
    """
    payload = payload or {}
    title = compact_text(payload.get("title"), 120) or "Cancion importada"
    lyrics = str(payload.get("lyrics") or "").strip()
    style = style_by_id(str(payload.get("style") or DEFAULT_STYLE))
    intention = intention_by_id(str(payload.get("intention") or DEFAULT_INTENTION))
    subtitle = compact_text(payload.get("subtitle"), 180) or _first_singable_line(lyrics) or intention["description"]
    energy = compact_text(payload.get("energy"), 120) or "alta, enfocada, poderosa"
    visual_identity = compact_text(
        payload.get("visualIdentity") or payload.get("visual_identity"),
        260,
    )
    if not visual_identity:
        visual_identity = (
            "premium motivational music-video identity with cinematic scenes that follow the lyrics, "
            "strong movement, sunrise contrast, disciplined emotion and clean heroic energy"
        )

    sections = _song_sections_from_lyrics(lyrics, limit=7)
    scenes = []
    for item in sections:
        lines = item.get("lines") or []
        overlay = compact_text(lines[0] if lines else item.get("section"), 54)
        scenes.append(
            {
                "section": compact_text(item.get("section"), 60),
                "visualPrompt": _import_scene_prompt(item.get("section"), lines, visual_identity, style["label"]),
                "textOverlay": overlay,
            }
        )

    main_hook = compact_text(payload.get("mainHook") or payload.get("main_hook"), 260)
    if not main_hook:
        main_hook = _first_singable_line(lyrics) or title
    mantra = compact_text(payload.get("mantra"), 160) or main_hook

    youtube_title = compact_text(payload.get("youtubeTitle") or payload.get("youtube_title"), 120)
    thumbnail_text = compact_text(payload.get("thumbnailText") or payload.get("thumbnail_text"), 40) or title[:40]
    raw_package = {
        "title": title,
        "subtitle": subtitle,
        "intention": intention["label"],
        "style": style["label"],
        "bpm": compact_text(payload.get("bpm"), 40) or style["bpm"],
        "energy": energy,
        "durationTarget": compact_text(payload.get("durationTarget"), 40) or "audio importado",
        "lyrics": lyrics,
        "mainHook": main_hook,
        "mantra": mantra,
        "sunoPrompt": compact_text(payload.get("sunoPrompt"), 900) or style["suno"],
        "sunoPromptAlt": compact_text(payload.get("sunoPromptAlt"), 900) or f"{style['suno']}, alternate stronger mix, same lyrics, cinematic hook emphasis",
        "negativePrompt": compact_text(payload.get("negativePrompt"), 500)
        or "no imitation of real artists, no copyrighted melody, no readable text in visuals, no medical claims, no body shaming",
        "coverPrompt": compact_text(payload.get("coverPrompt"), 900)
        or f"Premium cinematic cover for {title}, {visual_identity}, powerful subject, dramatic light, no readable text, no logos",
        "videoConcept": {
            "visualIdentity": visual_identity,
            "palette": [
                compact_text(payload.get("primaryColor"), 40) or "#07111F azul profundo",
                compact_text(payload.get("accentColor"), 40) or "#D4A24C oro intenso",
                compact_text(payload.get("emberColor"), 40) or "#E0533D energia roja",
            ],
            "scenes": scenes,
            "motionDirection": "One lyric-aligned still every 5 seconds, subtle Ken Burns, beat cuts, premium subtitles synced by lyric block.",
        },
        "youtube": {
            "title": youtube_title or f"{title} | Musica motivacional",
            "description": compact_text(payload.get("youtubeDescription"), 1800)
            or "Cancion motivacional creada para entrenar identidad, disciplina y enfoque. Video visual generado con imagenes alineadas a la letra.",
            "hashtags": ["#motivacion", "#disciplina", "#musicamotivacional", "#power"],
            "tags": ["musica motivacional", "disciplina", "power music", title],
            "thumbnailText": thumbnail_text,
        },
        "productionNotes": [
            "Cancion importada: la letra no fue generada por Content Factory en este paso.",
            "El video se renderiza en VPS con imagenes de Comfy/Flux alineadas a la letra cada 5 segundos.",
            "Los subtitulos se sincronizan por bloques de letra aproximados al audio.",
        ],
        "safetyNotes": [
            "Mensajes de autoprogramacion explicitos y saludables, no subliminales ocultos.",
            "No imitar artistas reales ni reutilizar letras protegidas sin permiso.",
        ],
    }
    package = normalize_package(raw_package, {**payload, "style": payload.get("style") or style["id"], "intention": payload.get("intention") or intention["id"]})
    package["source"] = "external_song_import"
    package["importedSong"] = {
        "mode": "lyrics_plus_audio",
        "visualIntervalSeconds": 5,
        "subtitleSync": "lyric_blocks",
    }
    package["lyricScore"] = _score_power_music_package(package)
    return package


def stable_track_id(uid: str, package: dict) -> str:
    base = json.dumps(
        {
            "uid": uid or "anonymous",
            "title": package.get("title"),
            "lyrics": package.get("lyrics"),
            "sunoPrompt": package.get("sunoPrompt"),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "music_" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def public_track_doc(track_id: str, data: dict) -> dict:
    package = data.get("package") if isinstance(data.get("package"), dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    audio_versions = data.get("audioVersions") if isinstance(data.get("audioVersions"), list) else []
    if audio and not audio_versions:
        audio_versions = [{
            **audio,
            "versionId": audio.get("versionId") or "take_legacy",
            "label": audio.get("label") or "Version principal",
            "promptKind": audio.get("promptKind") or "unknown",
        }]
    render = data.get("render") if isinstance(data.get("render"), dict) else {}
    renders = data.get("renders") if isinstance(data.get("renders"), list) else []
    if render and render.get("audioVersionId"):
        render_version_id = str(render.get("audioVersionId") or "")
        has_render = any(str(item.get("audioVersionId") or "") == render_version_id for item in renders if isinstance(item, dict))
        if not has_render:
            renders = [*renders, render]

    def _public_value(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: _public_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_public_value(v) for v in value]
        return str(value)

    return {
        "trackId": track_id,
        "title": package.get("title") or data.get("title") or "",
        "subtitle": package.get("subtitle") or "",
        "style": package.get("style") or "",
        "intention": package.get("intention") or "",
        "status": data.get("status") or "lyrics_ready",
        "createdAt": _public_value(data.get("createdAt")),
        "updatedAt": _public_value(data.get("updatedAt")),
        "audio": _public_value(audio),
        "audioVersions": _public_value(audio_versions),
        "activeAudioVersionId": _public_value(data.get("activeAudioVersionId") or audio.get("versionId") or ""),
        "render": _public_value(render),
        "renders": _public_value(renders),
        "package": package,
    }
