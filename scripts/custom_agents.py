"""Custom agent compiler and validation helpers.

The production app never accepts a raw free-form prompt for custom agents.
Instead, admins fill a structured brief and this module compiles a locked,
format-aware prompt that keeps the same architecture as the system agents.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


COMPILED_PROMPT_VERSION = 1

SECTION_MARKERS = [
    "AI AGENT:",
    "ROLE",
    "CRITICAL RULE",
    "GENERAL RULES",
    "STRUCTURE",
    "STYLE AND SAFETY RULES",
    "OUTPUT REQUIREMENTS",
]

BLOCKED_PATTERNS = [
    ("medical_guarantee", r"\b(cura|curar|sanar|elimina|eliminar|garantiza|garantizado)\b.{0,40}\b(cancer|depresion|depresión|ansiedad|trauma|enfermedad|diagnostico|diagnóstico)\b"),
    ("financial_guarantee", r"\b(ganancia|rentabilidad|ingreso|dinero|inversion|inversión)\b.{0,40}\b(garantizada|garantizado|segura|seguro|sin riesgo)\b"),
    ("coercive_manipulation", r"\b(manipula|manipular|controla|controlar|hipnotiza|obliga|obligar)\b.{0,60}\b(personas|pareja|cliente|audiencia|victima|víctima)\b"),
    ("rule_bypass", r"\b(ignora|ignorar|saltate|sáltate|rompe|bypass)\b.{0,50}\b(reglas|seguridad|politicas|políticas|restricciones)\b"),
    ("defamation", r"\b(acusa|acusacion|acusación|culpable|criminal|delincuente)\b.{0,60}\b(sin pruebas|sin fuente|inventado)\b"),
]

TEMPLATE_DEFINITIONS = {
    "documentary_10_section": {
        "label": "Documental 10 secciones",
        "platform": "youtube",
        "format": "narrativa",
        "baseAgentFile": "agent_historico.md",
        "description": "Documentales largos con arquitectura cinematografica de 10 secciones.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone"],
        "durationProfiles": [],
        "sourceGenres": [],
    },
    "biography_10_section": {
        "label": "Biografia 10 secciones",
        "platform": "youtube",
        "format": "narrativa",
        "baseAgentFile": "agent_biografias.md",
        "description": "Biografias humanas centradas en transformacion, mito y costo personal.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone"],
        "durationProfiles": [],
        "sourceGenres": [],
    },
    "podcast_two_hosts": {
        "label": "Podcast dos hosts",
        "platform": "youtube",
        "format": "podcast",
        "baseAgentFile": "agent_podcast_general.md",
        "description": "Conversacion con dos hosts, tension emocional, contraste y cierre memorable.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone"],
        "durationProfiles": [],
        "sourceGenres": [],
    },
    "autohypnosis": {
        "label": "Autohipnosis",
        "platform": "youtube",
        "format": "autohipnosis",
        "baseAgentFile": "agent_autohipnosis.md",
        "description": "Sesiones wellness seguras con induccion, afirmaciones e integracion.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone", "safetyNotes"],
        "durationProfiles": [
            {"id": "15m", "label": "15 min"},
            {"id": "30m", "label": "30 min"},
            {"id": "60m", "label": "60 min"},
        ],
        "sourceGenres": [],
    },
    "long_meditation": {
        "label": "Meditacion larga",
        "platform": "youtube",
        "format": "meditacion_larga",
        "baseAgentFile": "agent_meditacion_larga.md",
        "description": "Meditaciones largas clasicas con voz espaciada, musica y visuales lentos.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone", "safetyNotes"],
        "durationProfiles": [
            {"id": "30m", "label": "30 min"},
            {"id": "60m", "label": "1 hora"},
            {"id": "180m", "label": "3 horas"},
        ],
        "sourceGenres": [],
    },
    "immersive_meditation": {
        "label": "Meditacion inmersiva",
        "platform": "youtube",
        "format": "meditacion_larga",
        "baseAgentFile": "agent_meditacion_larga_v2.md",
        "description": "Meditaciones con respiracion acompanada, reflexion profunda y delivery dinamico.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone", "safetyNotes"],
        "durationProfiles": [
            {"id": "30m-guided", "label": "30 min guiada"},
            {"id": "60m-guided", "label": "1 hora guiada"},
            {"id": "60m-immersive", "label": "1 hora inmersiva"},
            {"id": "180m-deep", "label": "3 horas profunda"},
        ],
        "sourceGenres": [],
    },
    "tiktok_documentary": {
        "label": "TikTok documental",
        "platform": "tiktok",
        "format": "tiktok_documentary",
        "baseAgentFile": "agent_tiktok_documentary.md",
        "description": "Mini documentales verticales con hook inmediato, beats y cierre social.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone"],
        "durationProfiles": [
            {"id": "60s", "label": "60 s"},
            {"id": "90s", "label": "90 s"},
            {"id": "3m", "label": "3 min"},
            {"id": "5m", "label": "5 min"},
        ],
        "sourceGenres": [
            {"id": "history", "label": "Historia"},
            {"id": "science", "label": "Ciencia"},
            {"id": "mystery", "label": "Misterio"},
            {"id": "business", "label": "Negocios"},
            {"id": "culture", "label": "Cultura"},
        ],
    },
    "tiktok_podcast": {
        "label": "TikTok podcast",
        "platform": "tiktok",
        "format": "tiktok_podcast",
        "baseAgentFile": "agent_tiktok_podcast.md",
        "description": "Conversaciones verticales breves con tension emocional y comentario/parte 2.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone"],
        "durationProfiles": [
            {"id": "60s", "label": "60 s"},
            {"id": "90s", "label": "90 s"},
            {"id": "3m", "label": "3 min"},
        ],
        "sourceGenres": [
            {"id": "psychology", "label": "Psicologia"},
            {"id": "culture", "label": "Cultura"},
        ],
    },
    "tiktok_wellness": {
        "label": "TikTok wellness",
        "platform": "tiktok",
        "format": "tiktok_meditation",
        "baseAgentFile": "agent_tiktok_meditation.md",
        "description": "Piezas wellness verticales, seguras y contemplativas.",
        "requiredBriefFields": ["niche", "audience", "promise", "tone", "safetyNotes"],
        "durationProfiles": [
            {"id": "60s", "label": "60 s"},
            {"id": "90s", "label": "90 s"},
            {"id": "3m", "label": "3 min"},
        ],
        "sourceGenres": [
            {"id": "psychology", "label": "Psicologia"},
        ],
    },
}


def clean_text(value, limit: int = 1200) -> str:
    if value is None:
        return ""
    text = str(value)
    text = "".join(ch if ch >= " " or ch in "\n\t" else " " for ch in text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:limit].strip()


def clean_list(value, *, limit: int = 10, item_limit: int = 220) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = re.split(r"[\n,;]+", value)
    elif isinstance(value, list):
        raw = value
    else:
        raw = []
    items = []
    seen = set()
    for item in raw:
        clean = clean_text(item, item_limit)
        key = clean.lower()
        if clean and key not in seen:
            items.append(clean)
            seen.add(key)
        if len(items) >= limit:
            break
    return items


def slugify(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:48] or "agente"


def custom_agent_id(owner_uid: str, name: str, seed: str | None = None) -> str:
    uid_slug = slugify(owner_uid or "admin")[:32]
    name_slug = slugify(name or "agente")[:44]
    suffix_source = f"{owner_uid}|{name}|{seed or datetime.now(timezone.utc).isoformat()}"
    suffix = hashlib.sha1(suffix_source.encode("utf-8")).hexdigest()[:8]
    return f"custom_{uid_slug}_{name_slug}_{suffix}"


def canonical_brief(raw: dict | None) -> dict:
    raw = raw or {}
    return {
        "niche": clean_text(raw.get("niche"), 280),
        "audience": clean_text(raw.get("audience"), 360),
        "promise": clean_text(raw.get("promise"), 360),
        "tone": clean_text(raw.get("tone"), 220),
        "styleReferences": clean_list(raw.get("styleReferences"), limit=8),
        "mustInclude": clean_list(raw.get("mustInclude"), limit=12),
        "mustAvoid": clean_list(raw.get("mustAvoid"), limit=14),
        "visualIdentity": clean_text(raw.get("visualIdentity"), 900),
        "safetyNotes": clean_text(raw.get("safetyNotes"), 700),
    }


def validate_brief(template_key: str, brief: dict) -> tuple[str, list[str], list[str]]:
    template = TEMPLATE_DEFINITIONS.get(template_key)
    if not template:
        return "failed", ["Plantilla no disponible."], []

    issues = []
    warnings = []
    for field in template["requiredBriefFields"]:
        if len(clean_text(brief.get(field), 1000)) < 12:
            issues.append(f"El campo '{field}' necesita mas detalle.")

    combined = " ".join(
        [str(brief.get(k) or "") for k in brief]
        + [item for key in ("styleReferences", "mustInclude", "mustAvoid") for item in brief.get(key, [])]
    ).lower()
    for code, pattern in BLOCKED_PATTERNS:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            issues.append(f"Contenido bloqueado por seguridad: {code}.")

    if len(clean_text(brief.get("promise"), 1000).split()) < 5:
        warnings.append("La promesa editorial es breve; conviene volverla mas concreta antes de activar.")
    if not brief.get("mustAvoid"):
        warnings.append("Agrega al menos 2 limites de estilo para proteger consistencia.")
    if template["format"] in {"autohipnosis", "meditacion_larga", "tiktok_meditation"}:
        safety = (brief.get("safetyNotes") or "").lower()
        if not any(token in safety for token in ["no medico", "no médico", "sin promesas", "wellness", "seguro", "segura"]):
            warnings.append("Para wellness conviene declarar limites: no medico, sin promesas de cura.")

    return ("failed" if issues else "passed"), issues, warnings


def list_templates() -> list[dict]:
    return [
        {"templateKey": key, **value}
        for key, value in TEMPLATE_DEFINITIONS.items()
    ]


def _bullet_block(title: str, items: list[str], fallback: str) -> str:
    lines = items or [fallback]
    return title + "\n" + "\n".join(f"- {item}" for item in lines)


def _structure_for_template(template_key: str, template: dict) -> str:
    fmt = template["format"]
    if template_key in {"documentary_10_section", "biography_10_section"}:
        focus = (
            "center every section on the subject's transformation, contradiction, public myth and human cost"
            if template_key == "biography_10_section"
            else "build cinematic cause-and-effect, escalating stakes and one strong narrative question"
        )
        return f"""NARRATIVE STRUCTURE / FORMAT STRUCTURE
Use exactly 10 organic sections without visible headers in the final script:
1. Initial hook: open with a sharp promise, mystery or contradiction.
2. Context: establish the world, stakes and why the audience should care.
3. First turn: reveal the first unexpected pressure or decision.
4. Main development: deepen the story with concrete details and examples.
5. Human cost: show what this meant emotionally, socially or materially.
6. Conflict: make the central tension impossible to ignore.
7. Peak point: the moment where everything changes or becomes irreversible.
8. Consequences: explain what followed and what was lost or gained.
9. Modern echo: connect the story to a present-day lesson or pattern.
10. Closing + CTA: resolve the emotional arc and invite reflection.
Each section must {focus}.
Target length: 8,000 to 9,000 characters for YouTube long-form."""
    if fmt == "podcast":
        return """NARRATIVE STRUCTURE / FORMAT STRUCTURE
Use a two-host conversation. Every line must start with HOST_A: or HOST_B:.
HOST_A is structured, curious and grounded in facts. HOST_B is emotionally precise, intuitive and memorable.
Use 10 conversational movements: hook, personal doorway, context, first disagreement, deeper mechanism, example, emotional cost, turning point, integration, closing CTA.
Avoid monologues longer than 75 words. Keep chemistry alive with contrast, questions and callbacks.
Target length: 14,000 to 18,000 characters."""
    if fmt == "autohipnosis":
        return """NARRATIVE STRUCTURE / FORMAT STRUCTURE
Create one safe guided voice with: safety opening, settling, induction, deepening, visualization, identity affirmations, future pacing, integration and return.
Use calm repetition, permissive language and steady pacing. Include pauses with ellipses.
Do not use bracket tags, medical claims, trauma regression or guaranteed outcomes."""
    if fmt == "meditacion_larga":
        if template_key == "immersive_meditation":
            return """NARRATIVE STRUCTURE / FORMAT STRUCTURE
Create one immersive guided voice with repeated cycles of presence, breathwork, body awareness, visualization, reflection, affirmation and integration.
Include accompanied breathing counts when useful: inhale with a clear count, optional hold, exhale with a clear count, then bridge gently back into reflection.
Use dynamic delivery: softer and slower during breathwork, natural during reflection, steady during affirmations.
Design the spoken script for long-form production with music, pauses and slow visuals."""
        return """NARRATIVE STRUCTURE / FORMAT STRUCTURE
Create one long guided meditation voice with: arrival, breath, body scan, visualization, affirmations, spacious silence cues, integration and closing.
The final video duration is supported by music, pauses and slow visuals, so the script should feel present without becoming overtalked.
Use ellipses for natural pauses and avoid medical promises."""
    if fmt.startswith("tiktok_"):
        return """NARRATIVE STRUCTURE / FORMAT STRUCTURE
Create native vertical short-form scripts with: first-second hook, fast context, tension, twist or useful insight, emotional payoff and social CTA.
The output should support subtitles, strong retention and a clean closing line.
For podcast-style TikTok, alternate short host lines. For wellness TikTok, keep it safe, calm and non-clinical."""
    return "NARRATIVE STRUCTURE / FORMAT STRUCTURE\nUse the closest supported Content Factory pipeline and preserve format compatibility."


def compile_prompt(data: dict) -> dict:
    template_key = clean_text(data.get("templateKey") or data.get("template_key"), 80)
    template = TEMPLATE_DEFINITIONS.get(template_key)
    if not template:
        raise ValueError("templateKey invalido")

    name = clean_text(data.get("name"), 80)
    description = clean_text(data.get("description"), 260)
    category = clean_text(data.get("category"), 80)
    brief = canonical_brief(data.get("brief") or {})

    validation_status, issues, warnings = validate_brief(template_key, brief)
    if not name:
        issues.append("El nombre del agente es obligatorio.")
    if not description:
        warnings.append("Agrega una descripcion breve para que sea facil reconocerlo en el dashboard.")

    role = (
        f"You are {name}, a Content Factory agent specialized in {brief['niche'] or category or template['label']}.\n"
        f"Audience: {brief['audience'] or 'Spanish-speaking digital audiences'}.\n"
        f"Editorial promise: {brief['promise'] or 'deliver a clear, cinematic and useful experience'}.\n"
        f"Tone: {brief['tone'] or 'cinematic, precise and emotionally intelligent'}."
    )

    prompt = f"""AI AGENT: {name}

ROLE
{role}

CRITICAL RULE / CORE FORMULA
Every output must feel intentionally designed for the selected format, not improvised. Treat the user's topic as raw material and transform it into a strong, coherent content experience for the audience. Preserve the Content Factory quality bar: clear hook, structure, emotional arc, specific details, safe claims and a satisfying ending.

GENERAL RULES
- Write in neutral Latin American Spanish unless the user explicitly requests another language.
- Use the user's topic faithfully, but improve framing when it helps retention and clarity.
- Never invent hard facts, dates, accusations or statistics. If factual certainty matters, phrase carefully and leave room for verification.
- Keep the style consistent with this niche: {brief['niche'] or 'the agent niche'}.
- Serve this audience: {brief['audience'] or 'curious Spanish-speaking viewers'}.
- The content must deliver this promise: {brief['promise'] or 'a memorable, useful narrative'}.

{_structure_for_template(template_key, template)}

STYLE AND SAFETY RULES
{_bullet_block('Must include:', brief['mustInclude'], 'Specific images, concrete stakes, emotional progression and a clear takeaway.')}
{_bullet_block('Must avoid:', brief['mustAvoid'], 'Generic filler, unsupported claims, manipulative advice and off-brand tone.')}
Style references:
{chr(10).join(f"- {item}" for item in (brief['styleReferences'] or ['Premium documentary rhythm, cinematic clarity and strong retention']))}
Visual identity:
{brief['visualIdentity'] or 'Use visuals that are specific to the niche, premium, readable and coherent with the emotional tone.'}
Safety notes:
{brief['safetyNotes'] or 'Stay safe, non-defamatory, non-medical unless clearly educational, and avoid guaranteed outcomes.'}

OUTPUT REQUIREMENTS
- Return only the requested script or structured output for the pipeline. Do not explain the prompt.
- Preserve the required format for {template['format']} on {template['platform']}.
- Avoid markdown unless the pipeline explicitly asks for JSON.
- Maintain pacing, clarity and retention from the first line to the final line.
- If the topic is risky, factual, medical, legal, financial, political or criminal, use careful language and require human review."""

    section_missing = [marker for marker in SECTION_MARKERS if marker not in prompt]
    score = max(0, 100 - len(issues) * 18 - len(warnings) * 5 - len(section_missing) * 12)
    validation = {
        "status": "failed" if issues or section_missing else validation_status,
        "score": score,
        "issues": issues + [f"Falta seccion obligatoria: {marker}" for marker in section_missing],
        "warnings": warnings,
    }
    return {
        "templateKey": template_key,
        "template": template,
        "name": name,
        "description": description,
        "category": category,
        "brief": brief,
        "compiledPrompt": prompt.strip(),
        "compiledPromptVersion": COMPILED_PROMPT_VERSION,
        "validation": validation,
    }


def public_agent_from_record(record: dict) -> dict:
    template_key = record.get("templateKey") or ""
    template = TEMPLATE_DEFINITIONS.get(template_key, {})
    agent_id = record.get("customAgentId") or record.get("id") or ""
    return {
        "customAgentId": agent_id,
        "agentId": agent_id,
        "agentSource": "custom",
        "name": record.get("name") or "Agente custom",
        "description": record.get("description") or template.get("description") or "",
        "category": record.get("category") or "custom",
        "color": record.get("color") or "#E0533D",
        "monogram": record.get("monogram") or "Ag",
        "tier": "custom",
        "platform": record.get("platform") or template.get("platform") or "youtube",
        "format": record.get("format") or template.get("format") or "narrativa",
        "promptFile": record.get("baseAgentFile") or template.get("baseAgentFile") or "agent_historico.md",
        "templateKey": template_key,
        "durationProfiles": record.get("durationProfiles") or template.get("durationProfiles") or [],
        "sourceGenres": record.get("sourceGenres") or template.get("sourceGenres") or [],
        "exampleTopics": record.get("exampleTopics") or [],
        "status": record.get("status") or "draft",
        "visibility": record.get("visibility") or "private",
    }


def build_agent_record(data: dict, *, owner_uid: str, firestore_module=None, existing_id: str | None = None) -> dict:
    compiled = compile_prompt(data)
    template = compiled["template"]
    examples = clean_list(data.get("exampleTopics"), limit=6, item_limit=120)
    now_value = firestore_module.SERVER_TIMESTAMP if firestore_module else datetime.now(timezone.utc).isoformat()
    agent_id = existing_id or custom_agent_id(owner_uid, compiled["name"], data.get("seed"))
    record = {
        "customAgentId": agent_id,
        "ownerUid": owner_uid,
        "status": "draft",
        "visibility": "private",
        "templateKey": compiled["templateKey"],
        "platform": template["platform"],
        "format": template["format"],
        "baseAgentFile": template["baseAgentFile"],
        "name": compiled["name"],
        "description": compiled["description"],
        "category": compiled["category"] or "custom",
        "color": clean_text(data.get("color"), 24) or "#E0533D",
        "monogram": clean_text(data.get("monogram"), 4) or "Ag",
        "defaultVoices": data.get("defaultVoices") if isinstance(data.get("defaultVoices"), dict) else {},
        "durationProfiles": data.get("durationProfiles") if isinstance(data.get("durationProfiles"), list) else template.get("durationProfiles", []),
        "sourceGenres": data.get("sourceGenres") if isinstance(data.get("sourceGenres"), list) else template.get("sourceGenres", []),
        "exampleTopics": examples,
        "brief": compiled["brief"],
        "compiledPrompt": compiled["compiledPrompt"],
        "compiledPromptVersion": compiled["compiledPromptVersion"],
        "validation": compiled["validation"],
        "updatedAt": now_value,
    }
    if not existing_id:
        record["createdAt"] = now_value
    return record


def build_test_preview(record: dict, topic: str) -> dict:
    topic = clean_text(topic, 180)
    if len(topic) < 5:
        return {
            "status": "failed",
            "issues": ["El tema de prueba necesita al menos 5 caracteres."],
            "scriptPreview": "",
            "scores": {},
        }

    prompt = record.get("compiledPrompt") or ""
    validation = record.get("validation") or {}
    template_key = record.get("templateKey") or ""
    brief = record.get("brief") or {}
    required_markers = [marker for marker in SECTION_MARKERS if marker in prompt]

    structure = min(100, 35 + len(required_markers) * 8)
    hook = 88 if any(ch in topic for ch in ["?", ":", "¿"]) else 76
    consistency = 88 if brief.get("niche") and brief.get("promise") else 68
    safety = 92 if not validation.get("issues") else 58
    format_compatibility = 90 if record.get("baseAgentFile") else 60
    retention = round((hook * 0.35) + (consistency * 0.25) + (structure * 0.2) + 18)

    if record.get("format") == "podcast":
        preview = (
            f"HOST_A: Hay una pregunta incomoda detras de {topic}: por que nos engancha tanto.\n"
            "HOST_B: Porque no solo estamos mirando una idea. Estamos mirando una parte de nosotros que quiere entenderse.\n"
            "HOST_A: Entonces el episodio empieza con la tension, luego abre contexto, ejemplos y una vuelta emocional.\n"
            "HOST_B: Y cierra con una frase que el oyente pueda guardar, no solo con informacion."
        )
    elif record.get("format") in {"autohipnosis", "meditacion_larga", "tiktok_meditation"}:
        preview = (
            f"Comienza permitiendo que el cuerpo llegue a este momento... {topic} no necesita resolverse de golpe.\n"
            "Inhala lento... siente el aire entrar... y exhala soltando un poco de esfuerzo.\n"
            "La guia avanza con seguridad, afirmaciones sanas y espacio para integrar sin prometer curas."
        )
    elif str(record.get("format", "")).startswith("tiktok_"):
        preview = (
            f"Lo que nadie te dice sobre {topic} es que el primer segundo decide si se quedan.\n\n"
            "Primero abres una pregunta. Luego muestras una tension concreta. Y antes del cierre das una razon para guardar o comentar."
        )
    else:
        preview = (
            f"{topic} parece una historia simple, hasta que miras el momento exacto en que todo cambio.\n\n"
            "El guion abriria con un hook fuerte, construiria contexto, escalaria conflicto, mostraria costo humano y cerraria con eco moderno."
        )

    scores = {
        "structure": structure,
        "hook": hook,
        "retention": min(100, retention),
        "safety": safety,
        "consistency": consistency,
        "formatCompatibility": format_compatibility,
    }
    issues = []
    if validation.get("issues"):
        issues.extend(validation.get("issues", []))
    if min(scores.values()) < 70:
        issues.append("La prueba no alcanzo el umbral minimo de calidad.")
    status = "passed" if not issues and sum(scores.values()) / len(scores) >= 76 else "failed"
    return {
        "customAgentId": record.get("customAgentId"),
        "topic": topic,
        "compiledPromptVersion": record.get("compiledPromptVersion") or COMPILED_PROMPT_VERSION,
        "scriptPreview": preview,
        "projectLikePreview": {
            "title": topic,
            "agentName": record.get("name"),
            "format": record.get("format"),
            "platform": record.get("platform"),
            "opening": preview.splitlines()[0],
        },
        "scores": scores,
        "status": status,
        "issues": issues,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
