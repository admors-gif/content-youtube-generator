import copy
import hashlib
import re
import unicodedata
from datetime import datetime, timezone


DIRECTOR_VERSION = "power_music_director_v4_song_seed_lyric_metaphor"

EXCLUDED_VIDEO_TOOLS = {
    "luma": "disabled_by_request",
    "runway": "disabled_by_request",
}

BANNED_IMAGE_OBJECTS = [
    "readable text",
    "letters",
    "typography",
    "captions",
    "lyrics",
    "logos",
    "watermarks",
    "screens with writing",
    "posters",
    "book pages",
    "fake UI",
    "random household appliances",
    "clothes iron",
    "ironing board",
    "laundry",
    "office papers",
    "cheap motivational quote poster",
    "cash rain",
    "tacky flexing",
    "repetitive runner close-up",
    "floating weights",
    "floating objects",
    "object between legs",
    "impossible scale",
    "deformed human body",
    "office suit while running",
    "two mismatched people",
]

PROMPT_REJECTION_MARKERS = [
    "render the words",
    "show the text",
    "visible text",
    "lyrics on screen",
    "poster with",
    "poster that says",
    "sign that says",
    "write the title",
    "write the lyrics",
    "caption at bottom",
    "typographic layout",
]


VISUAL_WORLDS = {
    "luxury_ascent": {
        "label": "Luxury Ascent",
        "description": "dark luxury, disciplined ambition, status without tackiness, victory built in silence",
        "palette": ["deep black", "champagne gold", "crimson ember", "cold city blue"],
        "locations": [
            "black marble penthouse with city lights",
            "opulent staircase with deep shadows",
            "glass tower lobby at night",
            "wet avenue outside a luxury building",
            "sunrise rooftop above the city",
        ],
        "motifs": [
            "tailored silhouette",
            "gold rim light",
            "architectural symmetry",
            "controlled posture",
            "reflections on black marble",
        ],
    },
    "athletic_power": {
        "label": "Athletic Power",
        "description": "physical discipline, steel, breath, speed, early morning effort, premium training energy",
        "palette": ["deep black", "steel gray", "ember red", "sunrise gold"],
        "locations": [
            "industrial training space with dramatic light",
            "empty stadium tunnel before sunrise",
            "wide road at blue hour",
            "minimal boxing gym with one spotlight",
            "cold air rooftop training scene",
        ],
        "motifs": [
            "steel dumbbells",
            "barbell plates without brand marks",
            "chalk dust",
            "breath in cold air",
            "single decisive movement",
        ],
    },
    "feminine_power": {
        "label": "Feminine Power",
        "description": "magnetism, elegance, self-command, beauty as authority, confidence without objectification",
        "palette": ["velvet black", "warm gold", "deep burgundy", "soft ivory"],
        "locations": [
            "luxury corridor with cinematic shadows",
            "dark studio with one elegant spotlight",
            "city balcony at night",
            "gallery-like interior with negative space",
            "wet black street with gold reflections",
        ],
        "motifs": [
            "confident feminine silhouette",
            "direct gaze without glamor cliche",
            "tailored dark clothing",
            "controlled movement",
            "soft gold reflections",
        ],
    },
    "inner_child_victory": {
        "label": "Inner Child Victory",
        "description": "protection, memory, future-self strength, emotional repair without literal childhood scenes",
        "palette": ["deep navy", "warm gold", "soft crimson", "porcelain light"],
        "locations": [
            "quiet hallway between shadow and warm light",
            "minimal room with sunrise line on the floor",
            "mirror wall with adult future-self reflection",
            "empty theater stage with one spotlight",
            "rooftop at sunrise with calm posture",
        ],
        "motifs": [
            "adult silhouette protecting a memory",
            "warm light entering a dark room",
            "future-self reflection",
            "open doorway into sunrise",
            "calm hand over heart without close-up anatomy issues",
        ],
    },
    "shadow_to_power": {
        "label": "Shadow To Power",
        "description": "internal resistance transformed into control, desire, momentum and cinematic dominance",
        "palette": ["near black", "crimson ember", "electric gold", "smoke gray"],
        "locations": [
            "symmetrical dark hallway",
            "black studio with one spotlight",
            "city tunnel with light at the end",
            "minimal concrete space with ember glow",
            "glass room with reflections and shadow",
        ],
        "motifs": [
            "strong partial silhouette",
            "controlled firelight",
            "shadow split by gold light",
            "cracked stone with ember inside",
            "calm posture under pressure",
        ],
    },
    "urban_night_drive": {
        "label": "Urban Night Drive",
        "description": "night movement, ambition in transit, neon reflections, disciplined momentum through the city",
        "palette": ["near black", "sodium gold", "electric blue", "deep crimson"],
        "locations": [
            "wet empty boulevard with premium car headlights in the distance",
            "underground parking ramp with cinematic reflections",
            "city overpass at midnight with light trails",
            "glass elevator rising through a dark tower",
            "tunnel exit opening into city light",
        ],
        "motifs": [
            "headlights cutting fog",
            "wet asphalt reflections",
            "single moving silhouette",
            "clean road lines",
            "distant skyline glow",
        ],
    },
    "summit_resolve": {
        "label": "Summit Resolve",
        "description": "endurance, altitude, open air, earned clarity and victory without noise",
        "palette": ["deep navy", "cold stone gray", "sunrise gold", "ember orange"],
        "locations": [
            "mountain road at first light",
            "concrete stair climb under sunrise",
            "empty overlook above a sleeping city",
            "windy rooftop edge with clear horizon",
            "minimal desert road with long shadow",
        ],
        "motifs": [
            "long shadow moving forward",
            "breath in cold air",
            "distant summit line",
            "sunrise edge light",
            "grounded lone figure",
        ],
    },
    "mind_forge": {
        "label": "Mind Forge",
        "description": "mental discipline, focus, pressure turned into structure, inner fire made precise",
        "palette": ["graphite black", "white hot light", "deep ember", "steel blue"],
        "locations": [
            "minimal black studio with geometric light",
            "concrete room with a single vertical beam",
            "dark training lab with clean symmetry",
            "empty arena floor under one spotlight",
            "steel corridor with precise light strips",
        ],
        "motifs": [
            "focused eyes in shadow",
            "ember line inside concrete",
            "steel texture",
            "geometric beam of light",
            "controlled breath",
        ],
    },
}


SHOT_ARCHETYPES = {
    "grounded_training_still": {
        "category": "object_still_life",
        "humanPolicy": "no visible full human body; optional blurred silhouette only in background",
        "subject": "steel barbell plates or dumbbells resting on rubber gym floor or mounted on a rack",
        "wardrobe": "none; if a person is barely visible, technical athletic wear only",
        "action": "static grounded object with contact shadows",
        "propRules": "weights must touch floor, rack or bench; never floating; never between legs; one prop cluster only",
        "composition": "low 35mm close-up, object in lower third, clean negative space, realistic gravity",
        "camera": "low-angle close detail, shallow depth of field, cinematic side light",
        "controlNet": {"recommended": "depth_or_canny", "reason": "locks object grounding and perspective"},
    },
    "athletic_motion_wide": {
        "category": "human_wide_pose",
        "humanPolicy": "single distant silhouette, full body allowed only if pose is simple and readable",
        "subject": "one athlete moving through a wide road, track tunnel or rooftop training space",
        "wardrobe": "technical athletic wear, running shoes, no office suit, no formal clothing",
        "action": "controlled forward stride, not a twisted sprint, feet grounded",
        "propRules": "no loose weights, no random bags, no signs, no screens",
        "composition": "wide shot with horizon line, subject small in frame, clear ground contact",
        "camera": "wide 28mm cinematic frame, motion direction left-to-right or toward sunrise",
        "controlNet": {"recommended": "openpose_or_dwpose", "reason": "prevents broken running anatomy"},
    },
    "controlled_portrait": {
        "category": "human_portrait",
        "humanPolicy": "one person only, waist-up or three-quarter crop; avoid hands as the main focus",
        "subject": "confident person with calm power, partial silhouette, strong posture",
        "wardrobe": "tailored dark clothing, elegant and coherent with location; no running in formal wear",
        "action": "standing, turning slightly, looking past camera, controlled emotion",
        "propRules": "no props unless one minimal architectural element supports the frame",
        "composition": "waist-up portrait, symmetrical architecture, clean background, realistic proportions",
        "camera": "85mm editorial portrait, gold rim light, shallow depth of field",
        "controlNet": {"recommended": "pose", "reason": "keeps shoulders, head and torso coherent"},
    },
    "status_architecture": {
        "category": "environment_symbol",
        "humanPolicy": "optional tiny silhouette; no close anatomy",
        "subject": "luxury architecture, black marble, glass tower, city reflections",
        "wardrobe": "if silhouette appears, tailored dark clothing and grounded stance",
        "action": "still, poised, architectural power",
        "propRules": "no cash rain, no clutter, no brand logos, no posters",
        "composition": "strong symmetry, one vanishing point, premium negative space",
        "camera": "wide 35mm architectural shot with controlled light",
        "controlNet": {"recommended": "depth", "reason": "locks perspective and prevents impossible scale"},
    },
    "shadow_symbol": {
        "category": "environment_symbol",
        "humanPolicy": "no detailed human anatomy; use shadow or silhouette only",
        "subject": "dark hallway, split shadow, ember inside cracked stone, smoke and light",
        "wardrobe": "none",
        "action": "symbolic pressure turning into control",
        "propRules": "one symbol only, physically grounded or embedded in the scene",
        "composition": "minimal centered symbol, high contrast, no random objects",
        "camera": "locked-off symmetrical frame, cinematic haze, negative space",
        "controlNet": {"recommended": "depth_or_none", "reason": "simple symbolic scene has lower anatomy risk"},
    },
    "victory_rooftop": {
        "category": "human_wide_pose",
        "humanPolicy": "single distant silhouette only, no close face, no detailed hands",
        "subject": "one grounded figure on a sunrise rooftop above the city",
        "wardrobe": "athletic jacket or tailored minimal dark clothing depending on song world; no mixed formal running action",
        "action": "standing still, walking slowly, or looking over city; no sprinting",
        "propRules": "no floating props, no phones, no papers, no signs",
        "composition": "wide sunrise composition, figure small, strong horizon, grounded feet",
        "camera": "wide cinematic sunrise shot, gentle lens flare, strong silhouette",
        "controlNet": {"recommended": "depth", "reason": "locks rooftop perspective and ground plane"},
    },
}


ARCHETYPE_SEQUENCE = [
    "status_architecture",
    "controlled_portrait",
    "grounded_training_still",
    "shadow_symbol",
    "athletic_motion_wide",
    "victory_rooftop",
]


def compact_text(value, limit=400):
    text = " ".join(str(value or "").replace("\x00", " ").split()).strip()
    return text[:limit]


def _ascii_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.lower()


def _tokens(value):
    return set(re.findall(r"[a-z0-9_]+", _ascii_text(value)))


def _text_blob(package, payload=None):
    payload = payload or {}
    parts = [
        package.get("title"),
        package.get("subtitle"),
        package.get("intention"),
        package.get("style"),
        package.get("energy"),
        package.get("lyrics"),
        payload.get("theme"),
        payload.get("visualIdentity"),
        payload.get("targetUse"),
    ]
    return " ".join(str(part or "") for part in parts)


def _stable_song_seed(package, payload=None):
    payload = payload or {}
    raw = "||".join(
        str(part or "")
        for part in [
            package.get("title"),
            package.get("subtitle"),
            package.get("mainHook"),
            package.get("mantra"),
            package.get("lyrics"),
            payload.get("visualIdentity"),
            payload.get("theme"),
        ]
    )
    if not raw.strip():
        raw = "power_music"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10], 16)


def _seeded_item(items, index, seed, stride=1):
    clean = [item for item in (items or []) if item]
    if not clean:
        return ""
    return clean[(int(index or 0) * stride + int(seed or 0)) % len(clean)]


def choose_visual_world(package, payload=None):
    tokens = _tokens(_text_blob(package, payload))
    if tokens & {"dinero", "exito", "rico", "riqueza", "lujo", "estatus", "millonario", "oro"}:
        return "luxury_ascent"
    if tokens & {"corro", "correr", "entreno", "gym", "fuerza", "hierro", "sudor", "pesas", "cardio"}:
        return "athletic_power"
    if tokens & {"mujer", "reina", "diosa", "presencia", "mirada", "magnetismo"}:
        return "feminine_power"
    if tokens & {"nino", "infancia", "futuro", "pasado", "historia", "protejo", "promesa"}:
        return "inner_child_victory"
    if tokens & {"carro", "auto", "manejar", "noche", "ciudad", "calle", "neon", "velocidad", "ruta"}:
        return "urban_night_drive"
    if tokens & {"cima", "subo", "montana", "altura", "amanecer", "resistencia", "camino", "avanzar"}:
        return "summit_resolve"
    if tokens & {"mente", "enfoque", "silencio", "control", "presion", "forja", "metal", "vision"}:
        return "mind_forge"
    return "shadow_to_power"


def choose_shot_archetype(section, line, index, world_key=None, seed=0):
    tokens = _tokens(f"{section} {line}")
    if tokens & {"pesa", "pesas", "hierro", "dumbbell", "barbell", "gym", "entreno", "levanto", "fuerza", "sudor"}:
        return "grounded_training_still"
    if tokens & {"corro", "correr", "running", "ruta", "calle", "camino", "cima", "paso", "cardio"}:
        return "athletic_motion_wide"
    if tokens & {"mujer", "reina", "diosa", "presencia", "mirada", "magnetismo", "ella"}:
        return "controlled_portrait"
    if tokens & {"dinero", "exito", "rico", "riqueza", "lujo", "estatus", "gano", "meta", "oro"}:
        return "status_architecture"
    if tokens & {"miedo", "duda", "caer", "excusa", "sombra", "ansiedad", "dolor"}:
        return "shadow_symbol"
    if tokens & {"final", "victoria", "cumplo", "promesa", "subo", "cima"}:
        return "victory_rooftop"
    seeded_index = int(index or 0) + int(seed or 0)
    if world_key == "athletic_power" and seeded_index % 4 == 1:
        return "grounded_training_still"
    if world_key == "feminine_power" and seeded_index % 3 == 1:
        return "controlled_portrait"
    if world_key == "luxury_ascent" and seeded_index % 3 != 2:
        return "status_architecture"
    return ARCHETYPE_SEQUENCE[seeded_index % len(ARCHETYPE_SEQUENCE)]


def lyric_visual_metaphor(section, line, index, plan=None):
    plan = plan if isinstance(plan, dict) else {}
    world = plan.get("visualWorld") if isinstance(plan.get("visualWorld"), dict) else {}
    world_key = world.get("key") or "shadow_to_power"
    seed = int(plan.get("songVisualSeed") or 0)
    tokens = _tokens(f"{section} {line}")

    if tokens & {"excusa", "miedo", "duda", "ansiedad", "caer", "dolor"}:
        options = [
            "a dark room split by one clean beam of light, pressure becoming direction",
            "a cracked concrete wall with a controlled ember line inside, resistance turning into power",
            "a lone figure standing still while shadow breaks behind them, calm under pressure",
        ]
    elif tokens & {"cumplo", "promesa", "palabra", "elijo", "decido", "plan"}:
        options = [
            "a grounded figure crossing a bright threshold, commitment made visible without papers or text",
            "a single silhouette at the center of a clean arena floor, decision and self-command",
            "a precise vertical light beam over a strong posture, promise turned into structure",
        ]
    elif tokens & {"fuego", "hierro", "sudor", "fuerza", "levanto", "entreno", "golpe"}:
        options = [
            "steel equipment under dramatic light with chalk dust and real contact shadows",
            "a controlled training still life: grounded iron, heat, breath, effort, no floating props",
            "an athlete silhouette beside grounded equipment, power restrained and believable",
        ]
    elif tokens & {"corro", "ruta", "camino", "cima", "paso", "subo", "avanzar"}:
        options = [
            "a wide open path at first light, one small grounded figure moving toward the horizon",
            "a concrete stair climb with long shadow and sunrise edge light",
            "a road line disappearing toward a distant summit, endurance without clutter",
        ]
    elif tokens & {"dinero", "exito", "riqueza", "oro", "lujo", "estatus", "gano", "meta"}:
        options = [
            "black marble and city lights reflected under a calm powerful silhouette",
            "a glass tower lobby at night, elegant ambition without cash or logos",
            "a luxury staircase with one figure ascending, status earned through discipline",
        ]
    elif tokens & {"mujer", "reina", "diosa", "presencia", "mirada", "magnetismo"}:
        options = [
            "a confident feminine silhouette in an elegant corridor, authority without objectification",
            "a controlled editorial portrait with gold rim light and clean negative space",
            "a poised figure on a city balcony, magnetism shown through posture and light",
        ]
    elif tokens & {"mente", "silencio", "respiro", "calma", "enfoque", "vision", "control"}:
        options = [
            "a minimal black studio with geometric light, focus becoming a physical structure",
            "a close controlled breath in cold light, quiet confidence and mental discipline",
            "a steel corridor with precise light strips, internal order made visible",
        ]
    elif world_key == "urban_night_drive":
        options = [
            "wet asphalt and distant headlights, ambition moving through the night",
            "a tunnel exit opening into city light, momentum with no random props",
            "an underground ramp with clean reflections and one grounded silhouette",
        ]
    elif world_key == "summit_resolve":
        options = [
            "a lone figure against a sunrise horizon, earned clarity after pressure",
            "a mountain road with long shadow and open air, victory without noise",
            "an empty overlook above the city, calm power after the climb",
        ]
    elif world_key == "mind_forge":
        options = [
            "ember light inside concrete geometry, pressure turned into precise focus",
            "a dark training lab with one spotlight, mind forged into discipline",
            "graphite shadows and white-hot light, internal fire made controlled",
        ]
    else:
        options = [
            "a symbolic power scene where shadow becomes movement and control",
            "a strong silhouette in a premium cinematic space, identity becoming action",
            "a minimal high-contrast scene with one clear subject and emotional pressure",
        ]
    return compact_text(_seeded_item(options, index, seed, stride=2), 260)


def _coherent_location(archetype_id, proposed_location, world_key, index, seed):
    location = compact_text(proposed_location, 160)
    if archetype_id == "grounded_training_still":
        bank = [
            "industrial training space with dramatic light",
            "minimal boxing gym with one spotlight",
            "rubber gym floor beside a steel rack",
            "dark training lab with clean symmetry",
            "cold air rooftop training corner",
        ]
        return _seeded_item(bank, index, seed, stride=2)
    if archetype_id == "athletic_motion_wide":
        bank = [
            "wide road at blue hour",
            "empty stadium tunnel before sunrise",
            "mountain road at first light",
            "city overpass at midnight with clean ground plane",
            "concrete stair climb under sunrise",
        ]
        return _seeded_item(bank, index, seed, stride=2)
    if archetype_id == "victory_rooftop":
        bank = [
            "sunrise rooftop above the city",
            "empty overlook above a sleeping city",
            "windy rooftop edge with clear horizon",
            "wide elevated terrace at first light",
            "glass tower rooftop with distant skyline",
        ]
        return _seeded_item(bank, index, seed, stride=2)
    if archetype_id == "status_architecture" and world_key not in {"luxury_ascent", "urban_night_drive"}:
        bank = [
            "glass tower lobby at night",
            "black marble penthouse with city lights",
            "opulent staircase with deep shadows",
            "underground parking ramp with cinematic reflections",
            "wet avenue outside a luxury building",
        ]
        return _seeded_item(bank, index, seed, stride=2)
    return location


def build_shot_recipe(section, sample_line, index, plan):
    plan = plan if isinstance(plan, dict) else {}
    world = plan.get("visualWorld") if isinstance(plan.get("visualWorld"), dict) else {}
    world_key = world.get("key") or "shadow_to_power"
    seed = int(plan.get("songVisualSeed") or 0)
    archetype_id = choose_shot_archetype(section, sample_line, index, world_key, seed=seed)
    archetype = copy.deepcopy(SHOT_ARCHETYPES.get(archetype_id) or SHOT_ARCHETYPES["shadow_symbol"])
    locations = world.get("locations") or VISUAL_WORLDS.get(world_key, VISUAL_WORLDS["shadow_to_power"])["locations"]
    motifs = world.get("motifs") or VISUAL_WORLDS.get(world_key, VISUAL_WORLDS["shadow_to_power"])["motifs"]
    location = _seeded_item(locations, index, seed, stride=2)
    location = _coherent_location(archetype_id, location, world_key, index, seed)
    motif = _seeded_item(motifs, index, seed // 7, stride=3)
    metaphor = lyric_visual_metaphor(section, sample_line, index, plan)
    continuity_key = f"{world_key}:{archetype_id}:{seed % 997}:{index % 4}"
    strict_physics = [
        "all visible objects obey gravity",
        "every object has contact shadows",
        "no object floats unless it is smoke, haze or light",
        "no prop is placed between legs",
        "one subject scale only; no mismatched body sizes",
        "if a person runs, clothing must be athletic, never an office suit",
        "if clothing is formal, action is standing or slow walking only",
    ]
    recipe = {
        "id": archetype_id,
        "index": index,
        "continuityKey": continuity_key,
        "location": location,
        "motif": motif,
        "lyricMetaphor": metaphor,
        "summary": f"{archetype['category']} | {metaphor} | {location}",
        "humanPolicy": archetype["humanPolicy"],
        "subject": archetype["subject"],
        "wardrobe": archetype["wardrobe"],
        "action": archetype["action"],
        "propRules": archetype["propRules"],
        "composition": archetype["composition"],
        "camera": archetype["camera"],
        "physics": strict_physics,
        "controlNet": archetype["controlNet"],
        "negativeConstraints": [
            *BANNED_IMAGE_OBJECTS,
            "extra limbs",
            "bad anatomy",
            "distorted hands",
            "malformed face",
            "two bodies merged",
            "floating dumbbell",
            "floating barbell",
            "office clothes while running",
            "repeated identical runner shot",
        ],
    }
    return recipe


def _director_nodes():
    return [
        {
            "id": "creative_brief",
            "role": "turn lyrics and intent into a visual bible",
            "retryable": True,
        },
        {
            "id": "scene_planner",
            "role": "create symbolic, non-literal beat prompts",
            "retryable": True,
        },
        {
            "id": "prompt_gate",
            "role": "reject prompts with text, logos, screens, random domestic objects or literal lyric props",
            "retryable": False,
        },
        {
            "id": "image_generation",
            "role": "generate stills with ComfyUI/Flux only",
            "retryable": True,
        },
        {
            "id": "vision_critic",
            "role": "optional OpenAI visual QA for generated frames",
            "retryable": True,
        },
        {
            "id": "renderer",
            "role": "assemble deterministic FFmpeg video with text-free frames",
            "retryable": True,
        },
        {
            "id": "analytics",
            "role": "record prompt quality, render quality and future retention signals",
            "retryable": False,
        },
    ]


def build_music_video_director_plan(package, payload=None):
    package = package if isinstance(package, dict) else {}
    song_seed = _stable_song_seed(package, payload)
    world_key = choose_visual_world(package, payload)
    world = copy.deepcopy(VISUAL_WORLDS[world_key])
    identity = compact_text(
        (package.get("videoConcept") or {}).get("visualIdentity")
        if isinstance(package.get("videoConcept"), dict)
        else "",
        300,
    )
    if not identity:
        identity = f"{world['label']} premium music visualizer identity"

    return {
        "version": DIRECTOR_VERSION,
        "createdAtIso": datetime.now(timezone.utc).isoformat(),
        "songVisualSeed": song_seed,
        "excludedTools": EXCLUDED_VIDEO_TOOLS,
        "primaryOutcome": "make music videos feel premium, coherent and watchable without literal lyric images",
        "visualWorld": {
            "key": world_key,
            **world,
            "locations": [
                _seeded_item(world.get("locations") or [], index, song_seed, stride=2)
                for index in range(len(world.get("locations") or []))
            ],
            "motifs": [
                _seeded_item(world.get("motifs") or [], index, song_seed // 7, stride=3)
                for index in range(len(world.get("motifs") or []))
            ],
        },
        "visualBible": {
            "identity": identity,
            "cameraLanguage": [
                "strong symmetry",
                "slow push-in",
                "controlled lateral movement",
                "wide establishing frame before close detail",
                "premium editorial lighting",
            ],
            "allowedObjects": world["motifs"]
            + [
                "clean architecture",
                "silhouettes",
                "smoke or haze",
                "city lights",
                "polished floor reflections",
                "minimal symbolic objects",
            ],
            "bannedObjects": BANNED_IMAGE_OBJECTS,
            "continuityRules": [
                "repeat color, light and composition language instead of repeating the same subject",
                "one iconic subject per image",
                "no readable text inside generated frames",
                "avoid literal props for every lyric line",
                "no Luma and no Runway in this pipeline",
            ],
        },
        "sceneStrategy": (
            "symbolic premium visualizer: translate each lyric beat into power, motion, luxury, shadow, "
            "discipline or victory; keep frames text-free and avoid random props"
        ),
        "qualityGates": {
            "preImagePromptGate": {
                "enabled": True,
                "rejectIfContains": PROMPT_REJECTION_MARKERS,
                "requiredSignals": ["cinematic", "text-free", "symbolic", "premium"],
            },
            "postImageVisionGate": {
                "enabledByEnv": "CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_ENABLED",
                "goal": "flag generated frames with readable text, random domestic objects, broken anatomy, floating objects or off-brand imagery",
                "default": "on_when_OPENAI_API_KEY_is_available",
            },
            "autoRepairGate": {
                "enabled": True,
                "action": "regenerate failed Comfy frames once with stricter prompt, then replace with local fallback if still failing",
            },
            "thumbnailGate": {
                "engine": "OpenAI Images when OPENAI_API_KEY is present, exact title overlay rendered by backend",
                "rule": "AI generates background only; backend renders readable title/hook",
            },
        },
        "toolStack": {
            "orchestration": {
                "langGraph": {
                    "status": "contract_ready",
                    "nodes": _director_nodes(),
                },
                "inngest": {
                    "status": "event_contract_ready",
                    "events": [
                        "music.director.plan.created",
                        "music.image.batch.requested",
                        "music.image.qa.completed",
                        "music.render.completed",
                    ],
                },
                "n8n": {
                    "status": "external_automation_ready",
                    "bestUse": "notify, archive outputs, send publish checklist or move assets between tools",
                },
            },
            "images": {
                "primary": "ComfyUI/Flux",
                "controlNet": "ready through shotRecipe.controlNet and custom Comfy workflow env vars",
                "thumbnail": "OpenAI Images background + backend exact text overlay",
                "critic": "OpenAI Vision QA with auto-repair/replacement",
                "excluded": ["Luma", "Runway"],
            },
            "render": {
                "current": "FFmpeg deterministic assembly",
                "remotionReady": True,
                "reason": "Remotion can be added later for reusable animated templates without changing prompt logic",
            },
            "design": {
                "figmaCanvaReady": True,
                "role": "visual bible templates, thumbnail systems and brand layouts",
            },
            "memory": {
                "qdrantReady": True,
                "collection": "music_visual_memory",
                "fields": ["trackId", "visualWorld", "motifs", "badObjects", "thumbnailWinner", "retentionSignals"],
            },
            "observability": {
                "langfuseReady": True,
                "traceFields": ["trackId", "directorVersion", "visualWorld", "promptGate", "comfyStats"],
            },
            "analytics": {
                "posthogReady": True,
                "events": ["music_render_started", "music_render_completed", "music_video_downloaded", "thumbnail_opened"],
            },
        },
    }


def prompt_gate(prompt):
    text = str(prompt or "").lower()
    hits = [marker for marker in PROMPT_REJECTION_MARKERS if marker in text]
    good_signals = sum(1 for signal in ["cinematic", "text-free", "symbolic", "premium"] if signal in text)
    physics_signals = sum(1 for signal in ["grounded", "contact shadow", "gravity", "not floating", "physically"] if signal in text)
    return {
        "passed": not hits and good_signals >= 2 and physics_signals >= 1,
        "hits": hits,
        "goodSignals": good_signals,
        "physicsSignals": physics_signals,
    }


def prompt_gate_for_recipe(prompt, shot_recipe=None):
    result = prompt_gate(prompt)
    recipe = shot_recipe if isinstance(shot_recipe, dict) else {}
    recipe_issues = []
    text = str(prompt or "").lower()
    if (
        recipe.get("id") == "athletic_motion_wide"
        and (("office suit" in text and "no office suit" not in text) or ("formal clothing" in text and "no formal clothing" not in text))
    ):
        recipe_issues.append("athletic_motion_with_formal_clothing")
    floating_is_negated = any(marker in text for marker in ["no floating", "never floating", "no object can float", "must touch floor"])
    if recipe.get("id") == "grounded_training_still" and "floating" in text and not floating_is_negated:
        recipe_issues.append("training_prop_can_float")
    if recipe_issues:
        result["passed"] = False
    result["recipeIssues"] = recipe_issues
    result["recipeId"] = recipe.get("id") or ""
    return result


def director_scene_prompt(section, sample_line, index, plan):
    plan = plan if isinstance(plan, dict) else {}
    world = plan.get("visualWorld") if isinstance(plan.get("visualWorld"), dict) else VISUAL_WORLDS["shadow_to_power"]
    bible = plan.get("visualBible") if isinstance(plan.get("visualBible"), dict) else {}
    cameras = bible.get("cameraLanguage") or ["strong symmetry", "premium editorial lighting"]
    camera = cameras[index % len(cameras)]
    recipe = build_shot_recipe(section, sample_line, index, plan)
    negatives = ", ".join(recipe.get("negativeConstraints", [])[:18])
    physics = "; ".join(recipe.get("physics", [])[:7])
    metaphor = recipe.get("lyricMetaphor") or lyric_visual_metaphor(section, sample_line, index, plan)
    return compact_text(
        (
            "16:9 cinematic text-free premium music visualizer still. "
            f"Section: {compact_text(section, 60)}. "
            f"Lyric emotion metadata only, do not render words: {compact_text(sample_line, 160)}. "
            f"Lyric-derived visual metaphor to express visually: {metaphor}. "
            f"Visual world: {compact_text(world.get('description'), 240)}. "
            f"LOCKED SHOT RECIPE: {recipe['id']}. Subject: {recipe['subject']}. Location: {recipe['location']}. Motif: {recipe['motif']}. "
            f"Wardrobe: {recipe['wardrobe']}. Action: {recipe['action']}. Prop rules: {recipe['propRules']}. "
            f"Composition: {recipe['composition']}. Camera: {recipe['camera']}; {camera}. Physics: {physics}. "
            "One clear iconic subject, high contrast, polished music-video lighting, clean negative space, strong composition, realistic contact shadows, physically grounded objects. "
            "No readable text, no letters, no logos, no signs, no screens, no pseudo-words, no random household objects, "
            f"no clothes iron, no ironing board, no office papers, no cheap motivational poster, no literal lyric illustration. Negative constraints: {negatives}."
        ),
        1400,
    )


def build_beat_shot_recipe(section, line, index, plan):
    return build_shot_recipe(section, line, index, plan)


def _lyric_sections(lyrics, limit=8):
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
        if len(current["lines"]) < 3:
            current["lines"].append(compact_text(line, 160))
    if current["lines"]:
        sections.append(current)
    return sections[:limit]


def enrich_package_with_director_plan(package, payload=None):
    package = copy.deepcopy(package) if isinstance(package, dict) else {}
    plan = build_music_video_director_plan(package, payload)
    video = package.get("videoConcept") if isinstance(package.get("videoConcept"), dict) else {}
    video = copy.deepcopy(video)
    video["visualIdentity"] = compact_text(
        video.get("visualIdentity")
        or plan["visualBible"]["identity"],
        300,
    )
    video["visualWorld"] = compact_text(plan["visualWorld"]["description"], 300)
    video["sceneStrategy"] = compact_text(plan["sceneStrategy"], 360)
    video["palette"] = video.get("palette") if isinstance(video.get("palette"), list) and video.get("palette") else plan["visualWorld"]["palette"]
    video["directorPlan"] = plan

    source_sections = _lyric_sections(package.get("lyrics"), limit=8)
    if not source_sections:
        existing = video.get("scenes") if isinstance(video.get("scenes"), list) else []
        source_sections = [
            {
                "section": compact_text(scene.get("section"), 60) or f"Scene {index + 1}",
                "lines": [compact_text(scene.get("textOverlay") or scene.get("visualPrompt"), 160)],
            }
            for index, scene in enumerate(existing[:8])
            if isinstance(scene, dict)
        ]
    if not source_sections:
        source_sections = [{"section": "Hook", "lines": [package.get("mainHook") or package.get("title") or "power"]}]

    video["scenes"] = [
        {
            "section": compact_text(item.get("section"), 60) or f"Scene {index + 1}",
            "shotRecipe": build_shot_recipe(
                item.get("section"),
                " / ".join(item.get("lines") or []),
                index,
                plan,
            ),
            "visualPrompt": director_scene_prompt(
                item.get("section"),
                " / ".join(item.get("lines") or []),
                index,
                plan,
            ),
            "textOverlay": "",
        }
        for index, item in enumerate(source_sections[:8])
    ]

    package["videoConcept"] = video
    package["musicVideoDirector"] = plan
    notes = package.get("productionNotes") if isinstance(package.get("productionNotes"), list) else []
    director_note = "Music Director v4 activo: seed visual por cancion, metaforas de letra, shot recipes, fisica visual, QA y reparacion automatica sin Luma/Runway."
    if director_note not in notes:
        package["productionNotes"] = [*notes, director_note][:12]
    return package
