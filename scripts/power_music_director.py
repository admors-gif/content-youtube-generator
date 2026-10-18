import copy
import hashlib
import re
import unicodedata
from datetime import datetime, timezone


DIRECTOR_VERSION = "power_music_director_v6_narrative_storyboard"
STORYBOARD_CONTENT_VERSION = "music_storyboard_v1"

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
        "description": "physical discipline, breath, speed, early morning effort, premium training energy",
        "palette": ["deep black", "steel gray", "ember red", "sunrise gold"],
        "locations": [
            "industrial training space with dramatic light",
            "empty stadium tunnel before sunrise",
            "wide road at blue hour",
            "minimal boxing gym with one spotlight",
            "cold air rooftop training scene",
        ],
        "motifs": [
            "grounded training stance",
            "empty stadium tunnel",
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
            "quiet studio with clean symmetry",
            "concrete courtyard under one spotlight",
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


VISUAL_WORLDS.update({
    "everyday_resolve": {
        "label": "Everyday Resolve",
        "description": "an intimate story of finding direction again, ordinary places changing with the protagonist's emotional state",
        "palette": ["muted blue", "warm amber", "soft charcoal", "natural skin tones"],
        "locations": ["quiet apartment beside a window", "shared apartment courtyard", "tree-lined neighborhood street", "small public garden", "pedestrian passage near the same neighborhood"],
        "motifs": ["window light crossing a familiar room", "a reflection in the courtyard window", "tree shadows across the pavement", "an open passage into the same garden", "changing daylight on the same walls"],
    },
    "emotional_recovery": {
        "label": "Emotional Recovery",
        "description": "a personal story of letting go, recovering calm and rebuilding trust, expressed through familiar spaces and restrained human gestures",
        "palette": ["soft blue gray", "warm ivory", "faded terracotta", "gentle daylight"],
        "locations": ["quiet lived-in room beside a window", "small courtyard outside the room", "neighborhood path after rain", "sheltered garden near home", "same room opening into morning light"],
        "motifs": ["rain fading on a window", "a curtain opening to natural light", "a reflection resolving in clear glass", "water settling in a garden pool", "sunlight returning to the same doorway"],
    },
})


SHOT_ARCHETYPES = {
    "grounded_training_still": {
        "category": "object_still_life",
        "humanPolicy": "no visible full human body; optional blurred silhouette only in background",
        "subject": "disciplined training detail with optional equipment secondary, grounded on floor or rack",
        "wardrobe": "none; if a person is barely visible, technical athletic wear only",
        "action": "static grounded object with contact shadows",
        "propRules": "equipment is optional and secondary; if weights appear they must touch floor, rack or bench; never floating; never between legs; one prop cluster only",
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


SHOT_ARCHETYPES.update({
    "setting_establishing": {
        "category": "environment_wide", "humanPolicy": "same protagonist may appear small in frame",
        "subject": "the established story location, with the protagonist quietly present",
        "wardrobe": "same simple everyday outfit throughout the story", "action": "observing the surroundings without posing",
        "propRules": "use only objects already present in the story location; introduce no symbolic equipment",
        "composition": "wide establishing frame, realistic perspective and clear spatial geography",
        "camera": "wide 28mm environmental frame, natural motivated light",
        "controlNet": {"recommended": "none", "reason": "story composition is described in the image prompt"},
    },
    "character_moment": {
        "category": "human_portrait", "humanPolicy": "one recurring adult protagonist, medium framing, relaxed natural anatomy",
        "subject": "the same protagonist responding to the moment with a restrained expression",
        "wardrobe": "same simple everyday outfit throughout the story", "action": "pausing, observing, then relaxing their posture",
        "propRules": "no added props; emotion comes from gesture and light",
        "composition": "medium portrait connected visibly to the established location",
        "camera": "natural eye-level 50mm portrait, restrained depth of field",
        "controlNet": {"recommended": "none", "reason": "simple natural posture"},
    },
    "environment_detail": {
        "category": "environment_detail", "humanPolicy": "no close human anatomy",
        "subject": "one existing detail of the established story location",
        "wardrobe": "none", "action": "light or reflections changing across the same space",
        "propRules": "the detail must belong to the established setting, without adding objects from lyric metaphors",
        "composition": "close environmental detail, physical texture, clear contact and scale",
        "camera": "50mm detail shot with natural light and tactile texture",
        "controlNet": {"recommended": "none", "reason": "simple environmental detail"},
    },
    "story_transition": {
        "category": "human_wide_pose", "humanPolicy": "one recurring protagonist, full body only at a distance",
        "subject": "the same protagonist moving through the established story location",
        "wardrobe": "same simple everyday outfit throughout the story", "action": "slow natural walking from shadow toward clearer light",
        "propRules": "no new props; keep the environment recognizable",
        "composition": "medium-wide frame with a clear direction of movement and grounded feet",
        "camera": "35mm frame, gentle lateral perspective, coherent geography",
        "controlNet": {"recommended": "none", "reason": "simple walking posture without complex action"},
    },
})


ARCHETYPE_SEQUENCE = [
    "setting_establishing", "character_moment", "environment_detail",
    "story_transition", "character_moment", "setting_establishing",
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


def normalize_storyboard(value):
    """Accept versioned authored stories, never infer provenance from old scenes."""
    if not isinstance(value, dict) or value.get("contentVersion") != STORYBOARD_CONTENT_VERSION:
        return {}
    source = value.get("source")
    if source not in {"composer", "openai_story_planner", "human"}:
        return {}
    if any(not isinstance(value.get(key), str) for key in ["premise", "protagonist", "wardrobe"]):
        return {}
    text_fields = {key: compact_text(value.get(key), limit) for key, limit in [
        ("premise", 900), ("protagonist", 500), ("wardrobe", 350),
    ]}
    if not all(text_fields.values()):
        return {}
    locations = value.get("locations")
    beats = value.get("beats")
    if not isinstance(locations, list) or not isinstance(beats, list):
        return {}
    locations = list(dict.fromkeys(compact_text(item, 240) for item in locations if isinstance(item, str) and item.strip()))[:12]
    if not locations or not beats or len(beats) > 32:
        return {}
    clean_beats = []
    for beat in beats:
        if not isinstance(beat, dict):
            return {}
        if any(not isinstance(beat.get(key), str) for key in ["section", "location", "action", "emotion"]):
            return {}
        clean = {key: compact_text(beat.get(key), limit) for key, limit in [
            ("section", 80), ("location", 240), ("action", 700), ("emotion", 240),
        ]}
        if not all(clean.values()) or clean["location"] not in locations:
            return {}
        clean_beats.append(clean)
    result = {"contentVersion": STORYBOARD_CONTENT_VERSION, "source": source, **text_fields, "locations": locations, "beats": clean_beats}
    if isinstance(value.get("inputSignature"), str) and value["inputSignature"].strip():
        result["inputSignature"] = compact_text(value["inputSignature"], 256)
    return result


def _storyboard_beat(section, index, plan):
    storyboard = normalize_storyboard(plan.get("storyboard"))
    if not storyboard:
        return {}, {}
    section_key = _ascii_text(section).strip().strip("[]")
    exact_index = int(index or 0)
    if 0 <= exact_index < len(storyboard["beats"]):
        indexed = storyboard["beats"][exact_index]
        if _ascii_text(indexed["section"]).strip().strip("[]") == section_key:
            return storyboard, copy.deepcopy(indexed)
    matches = [beat for beat in storyboard["beats"] if _ascii_text(beat["section"]).strip().strip("[]") == section_key]
    beats = matches or storyboard["beats"]
    return storyboard, copy.deepcopy(beats[int(index or 0) % len(beats)])


def storyboard_sports(storyboard):
    """Collect every sport/fitness equipment domain, rather than one winner."""
    if not isinstance(storyboard, dict):
        return set()
    evidence = [storyboard.get(key) for key in ["premise", "protagonist", "wardrobe"]]
    evidence.extend(storyboard.get("locations") or [])
    for beat in storyboard.get("beats") or []:
        if isinstance(beat, dict):
            evidence.extend(beat.get(key) for key in ["action", "emotion", "location"])
    # Newlines keep negations scoped to their own field, while a "boxing
    # gym" and subsequent "same gym" share the story's sport context.
    return sports_in_text("\n".join(str(part) for part in evidence if part))


def storyboard_has_athletics(storyboard):
    return bool(storyboard_sports(storyboard))


def _affirmative_sport_text(value):
    text = _ascii_text(value)
    # A negated list belongs to one clause: "sin boxeo ni gimnasio" must
    # remove both nouns, while the next sentence can still establish a sport.
    text = re.sub(r"\b(?:sin|without|avoid|evitar)\b[^,.;\n]*", "", text)
    text = re.sub(
        r"\bno\s+(?:es\s+|hay\s+|usar\s+|quiero\s+|incluir\s+)?"
        r"(?:gym|gimnasio|pesas|deportes?|sports?|weights?|entrenamiento|boxeo|boxing|atleta|athlete|corredor|corredora|tenis|tennis|natacion|swimming)\b(?:\s+(?:ni|or|and)\s+\w+)*",
        "", text,
    )
    return text


def _text_blob(package, payload=None):
    """Story evidence only. Listening context and music genre are not scenery."""
    payload = payload or {}
    video = package.get("videoConcept") if isinstance(package.get("videoConcept"), dict) else {}
    parts = [
        package.get("title"),
        package.get("subtitle"),
        package.get("lyrics"),
        payload.get("theme") or video.get("userStoryContext"),
        payload.get("visualBrief") or payload.get("visual_brief"),
        payload.get("visualIdentity") or payload.get("visual_identity"),
    ]
    return " ".join(str(part or "") for part in parts)


def sports_in_text(value):
    """Affirmative sport evidence; generic strength metaphors grant no props."""
    text = _affirmative_sport_text(value)
    tokens = _tokens(text)
    aliases = {
        "boxing": {"boxeo", "boxeador", "boxeadora", "boxing", "boxer"},
        "swimming": {"nadador", "nadadora", "natacion", "swimming", "swimmer"},
        "running": {"maraton", "marathon", "corredor", "corredora", "runner"},
        "tennis": {"tenis", "tennis", "tenista"},
        "basketball": {"baloncesto", "basquetbol", "basketball"},
        "football": {"futbol", "soccer", "football"},
        "strength_training": {"pesas", "mancuerna", "mancuernas", "dumbbell", "dumbbells", "barbell", "barbells", "weightlifting", "weights", "rack"},
    }
    sports = {sport for sport, words in aliases.items() if tokens & words}
    if re.search(
        r"\b(?:levanto|levantar|levantando|lifting)\s+(?:las?\s+|una?\s+)?(?:pesas|weights|barra)\b"
        r"|\bbarra\s+(?:olimpica|de\s+pesas)\b|\b(?:squat|weight)\s+(?:bar|rack)\b"
        r"|\b(?:exercise|weight)\s+machines?\b|\bmaquinas?\s+(?:de\s+)?(?:ejercicio|entrenamiento)\b",
        text,
    ):
        sports.add("strength_training")
    if re.search(
        r"\b(?:corro|correr|corriendo|run|running)\s+(?:por\s+|en\s+|on\s+|the\s+|la\s+|el\s+){0,3}(?:pista|estadio|track|stadium)\b"
        r"|\b(?:carrera|race)\s+(?:de\s+)?\d+\s*(?:km|kilometros|kilometers)\b",
        text,
    ):
        sports.add("running")
    if not sports and tokens & {"gym", "gimnasio"}:
        sports.add("strength_training")
    if not sports and tokens & {"atleta", "athlete"}:
        sports.add("athletics")
    return sports


def _has_athletic_story(text):
    return bool(sports_in_text(text))


def _explicit_visual_direction(package, payload=None):
    payload = payload or {}
    video = package.get("videoConcept") if isinstance(package.get("videoConcept"), dict) else {}
    # Persist only human direction. Legacy model-generated visualIdentity often
    # contains the gym/luxury boilerplate this director is replacing.
    return compact_text(
        payload.get("visualBrief") or payload.get("visual_brief")
        or payload.get("visualIdentity") or payload.get("visual_identity")
        or video.get("userVisualDirection"),
        600,
    )


def build_story_brief(package, payload=None):
    payload = payload or {}
    video = package.get("videoConcept") if isinstance(package.get("videoConcept"), dict) else {}
    story_theme = compact_text(payload.get("theme") or video.get("userStoryContext"), 300)
    direction = _explicit_visual_direction(package, payload)
    story_text = _text_blob(package, {**payload, "visualBrief": direction})
    authorized_sports = sports_in_text(story_text)
    athletic_story = bool(authorized_sports)
    sport = next((item for item in ["boxing", "swimming", "tennis", "basketball", "football", "running", "strength_training", "athletics"] if item in authorized_sports), "none")
    # Lyrics remain available as evidence in the plan, but raw phrases are not
    # sent to the image model where "me levanto" can become weight lifting.
    lyric_evidence = [
        compact_text(line, 180) for line in str(package.get("lyrics") or "").splitlines()
        if line.strip() and not line.strip().startswith("[")
    ][:8]
    storyboard = normalize_storyboard(video.get("storyboard"))
    if storyboard and not storyboard_sports(storyboard).issubset(authorized_sports):
        storyboard = {}
    narrative_source = storyboard.get("source") or ("human_direction_fallback" if direction else "heuristic_fallback")
    continuity = {
        "protagonist": storyboard.get("protagonist") or ("the character or characters established in the explicit human direction" if direction else "one recurring adult protagonist, same appearance and simple wardrobe"),
        "wardrobe": storyboard.get("wardrobe") or "keep the same story-appropriate wardrobe across scenes",
        "locations": storyboard.get("locations") or ("only the locations established in the explicit human direction" if direction else "a connected group of locations belonging to the same story"),
        "visualLanguage": "consistent palette, daylight progression and camera direction",
    }
    return {
        "basis": "lyrics_and_explicit_visual_direction",
        "songTitle": compact_text(package.get("title"), 120),
        "lyricEvidence": lyric_evidence,
        "explicitVisualDirection": direction,
        "explicitStoryTheme": story_theme,
        "athleticStory": athletic_story,
        "sport": sport,
        "authorizedSports": sorted(authorized_sports),
        "narrativeSource": narrative_source,
        "premise": storyboard.get("premise") or direction or "No authored story is available; provisional emotional direction inferred from the lyrics.",
        "storyboard": storyboard,
        "warnings": [] if storyboard else ["No validated authored storyboard is available. This visual direction is a provisional fallback, not a semantic screenplay."],
        "listeningContextIsScenery": False,
        "approach": "cinematic story with scenes related to the full song, not a separate object for each line",
        "emotionalArc": [beat["emotion"] for beat in storyboard["beats"]] if storyboard else [
            "establish the protagonist and the song's emotional tension",
            "show a small decision or shift in perspective in the same environment",
            "resolve the emotional movement through posture, action and changing light",
        ],
        "continuity": continuity,
        "interpretationRule": "Treat strength, weight, rising, fighting and running from the past as emotional metaphors unless the song establishes an actual sport story.",
    }


def _stable_song_seed(package, payload=None):
    raw = "||".join(
        str(part or "")
        for part in [
            package.get("title"),
            package.get("subtitle"),
            package.get("mainHook"),
            package.get("mantra"),
            package.get("lyrics"),
            _explicit_visual_direction(package, payload),
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
    if _has_athletic_story(_text_blob(package, payload)):
        return "athletic_power"
    if tokens & {"infancia", "ninez", "nino", "nina"}:
        return "inner_child_victory"
    if tokens & {"ruptura", "desamor", "duelo", "sanar", "sanando", "ansiedad", "perdono", "perdonar", "respiro", "soltar", "adios"}:
        return "emotional_recovery"
    if tokens & {"lujo", "millonario", "penthouse", "mansiones"}:
        return "luxury_ascent"
    if tokens & {"carro", "auto", "manejar", "conduzco", "neon"}:
        return "urban_night_drive"
    if tokens & {"montana", "sendero", "desierto", "cumbre"}:
        return "summit_resolve"
    return "everyday_resolve"


def choose_shot_archetype(section, line, index, world_key=None, seed=0):
    tokens = _tokens(f"{section} {line}")
    # Athletic imagery is opt-in at song/story level. A line saying "mi
    # palabra pesa" or "me levanto" cannot change the location into a gym.
    if world_key == "athletic_power":
        if tokens & {"pesas", "dumbbell", "dumbbells", "barbell", "barbells"}:
            return "grounded_training_still"
        seeded_index = int(index or 0) + int(seed or 0)
        return ["setting_establishing", "athletic_motion_wide", "character_moment", "environment_detail"][seeded_index % 4]
    seeded_index = int(index or 0) + int(seed or 0)
    return ARCHETYPE_SEQUENCE[seeded_index % len(ARCHETYPE_SEQUENCE)]


def _story_stage(section):
    section = _ascii_text(section)
    if any(word in section for word in ["outro", "final", "ending", "cierre"]):
        return 2
    if any(word in section for word in ["chorus", "coro", "bridge", "puente", "verse 2", "verso 2"]):
        return 1
    return 0


def lyric_visual_metaphor(section, line, index, plan=None):
    plan = plan if isinstance(plan, dict) else {}
    storyboard, story_beat = _storyboard_beat(section, index, plan)
    if storyboard:
        return f"{story_beat['emotion']}. {story_beat['action']}"
    world = plan.get("visualWorld") if isinstance(plan.get("visualWorld"), dict) else {}
    world_key = world.get("key") or "everyday_resolve"
    seed = int(plan.get("songVisualSeed") or 0)
    tokens = _tokens(line)
    stage = _story_stage(section)
    if world_key == "athletic_power":
        options = [
            "the established athlete preparing calmly in the same sporting location, without inventing equipment",
            "the same athlete practicing the sport established by the song, with a simple believable action",
            "the same athlete pausing after their effort, the story resolving through posture and light",
        ]
        return options[stage]
    if tokens & {"miedo", "duda", "ansiedad", "dolor", "lloro", "triste"}:
        emotion = "a restrained expression of vulnerability gradually giving way to composure"
    elif tokens & {"elijo", "decido", "cumplo", "promesa", "vuelvo", "levantare", "levanto"}:
        emotion = "a small deliberate action and a more assured posture, expressing a personal decision"
    elif tokens & {"respiro", "calma", "libre", "suelto", "soltar", "perdono"}:
        emotion = "a relaxed breath and an unguarded expression, expressing emotional release"
    else:
        emotion = "a subtle change in expression and posture following the song's emotional movement"
    progression = [
        "establish the familiar setting and the protagonist's initial emotional state",
        "return to the established place as the protagonist makes a small meaningful change",
        "resolve in the same connected story world, with clearer light and a calmer, more assured protagonist",
    ][stage]
    # A detail shot can carry the emotion without inventing a new literal prop.
    detail = _seeded_item(world.get("motifs") or VISUAL_WORLDS["everyday_resolve"]["motifs"], index // 3, seed)
    return compact_text(f"{progression}; {emotion}; recurring environmental cue: {detail}", 480)


def build_shot_recipe(section, sample_line, index, plan):
    plan = plan if isinstance(plan, dict) else {}
    world = plan.get("visualWorld") if isinstance(plan.get("visualWorld"), dict) else {}
    world_key = world.get("key") or "everyday_resolve"
    brief = plan.get("storyBrief") if isinstance(plan.get("storyBrief"), dict) else {}
    athletic_story = bool(brief.get("athleticStory")) if brief else world_key == "athletic_power"
    if not athletic_story and world_key == "athletic_power":
        world_key = "everyday_resolve"
        world = VISUAL_WORLDS[world_key]
    seed = int(plan.get("songVisualSeed") or 0)
    archetype_id = choose_shot_archetype(section, sample_line, index, world_key, seed=seed)
    archetype = copy.deepcopy(SHOT_ARCHETYPES.get(archetype_id) or SHOT_ARCHETYPES["shadow_symbol"])
    locations = world.get("locations") or VISUAL_WORLDS.get(world_key, VISUAL_WORLDS["shadow_to_power"])["locations"]
    motifs = world.get("motifs") or VISUAL_WORLDS.get(world_key, VISUAL_WORLDS["shadow_to_power"])["motifs"]
    location = _seeded_item(locations, _story_stage(section), seed)
    motif = _seeded_item(motifs, index // 3, seed // 7)
    if archetype_id == "grounded_training_still":
        archetype["subject"] = "the specific grounded training equipment explicitly established by the song"
    if archetype_id == "athletic_motion_wide":
        sport = brief.get("sport") or "running"
        archetype["subject"] = f"the same athlete practicing {sport.replace('_', ' ')} in the established sporting location"
        archetype["action"] = "one simple natural action appropriate to the established sport, physically grounded"
    if athletic_story and archetype["wardrobe"] != "none":
        archetype["wardrobe"] = "the same sport-appropriate training outfit throughout the story"
    if archetype_id == "environment_detail":
        archetype["subject"] = f"an environmental detail already in the established location: {motif}"
    metaphor = lyric_visual_metaphor(section, sample_line, index, plan)
    storyboard, story_beat = _storyboard_beat(section, index, plan)
    direction = brief.get("explicitVisualDirection") or ""
    if storyboard:
        location = story_beat["location"]
        motif = story_beat["emotion"]
        archetype.update({
            "category": "story_scene",
            "subject": storyboard["protagonist"],
            "humanPolicy": "only the character or characters established in the authored story, with natural anatomy and interaction",
            "wardrobe": storyboard["wardrobe"],
            "action": story_beat["action"],
            "propRules": "allow the objects and interactions established in the authored story; add no unrelated props",
            "composition": "clear cinematic framing suited to the authored cast and action, keeping the specified setting recognizable",
            "camera": ["35mm medium-wide story frame", "50mm medium story frame", "28mm wide story frame"][int(index or 0) % 3],
        })
    elif direction:
        # A provisional human brief still outranks every inferred apartment,
        # street or training-room recipe. The semantic planner can replace
        # this fallback with a fully authored storyboard before generation.
        location = f"Only the setting established by this human direction: {direction}"
        motif = "details belonging to the human-directed story, with no inferred locations or props"
        archetype.update({
            "category": "story_scene",
            "subject": "the character or characters and central subject established in the human creative direction",
            "humanPolicy": "only the cast established in the human creative direction",
            "wardrobe": "the consistent wardrobe established by the human direction, appropriate to that story",
            "action": "the event or interaction established by the human direction, following the song's emotional progression",
            "propRules": "allow the objects explicitly requested by the human direction; do not substitute unrelated objects",
            "composition": "clear cinematic framing suited to the human-directed cast and event, keeping the specified setting recognizable",
            "camera": ["35mm medium-wide story frame", "50mm medium story frame", "28mm wide story frame"][int(index or 0) % 3],
        })
        metaphor = f"Develop the human-directed event within its specified setting: {direction}"
    continuity_key = f"{world_key}:{seed % 997}:same_protagonist"
    strict_physics = [
        "all visible objects obey gravity",
        "every object has contact shadows",
        "no object floats unless it is smoke, haze or light",
        "no prop is placed between legs",
        "natural proportions and coherent scale for every story character and the environment",
    ]
    recipe = {
        "id": archetype_id,
        "category": archetype["category"],
        "index": index,
        "athleticStory": athletic_story,
        "storyStage": _story_stage(section),
        "storyEmotion": story_beat.get("emotion") or "",
        "storyPremise": storyboard.get("premise") or direction,
        "narrativeSource": brief.get("narrativeSource") or "heuristic_fallback",
        "continuity": brief.get("continuity") or {},
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
            "role": "generate cinematic story stills with OpenAI Images; ComfyUI is an optional explicit choice",
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
    payload = payload or {}
    brief = build_story_brief(package, payload)
    song_seed = _stable_song_seed(package, payload)
    world_key = choose_visual_world(package, {**payload, "visualBrief": brief["explicitVisualDirection"]})
    world = copy.deepcopy(VISUAL_WORLDS[world_key])
    storyboard = brief["storyboard"]
    if storyboard:
        world_key = "authored_story"
        world = {
            "label": "Authored Cinematic Story",
            "description": storyboard["premise"],
            "palette": world["palette"],
            "locations": storyboard["locations"],
            "motifs": list(dict.fromkeys(beat["emotion"] for beat in storyboard["beats"])),
        }
    elif brief["explicitVisualDirection"]:
        world_key = "human_direction"
        world = {
            "label": "Human Creative Direction — Provisional",
            "description": brief["explicitVisualDirection"],
            "palette": world["palette"],
            "locations": [f"only the setting specified by the human direction: {brief['explicitVisualDirection']}"],
            "motifs": ["details belonging to the human-directed scene, with no added locations or props"],
        }
    elif brief["athleticStory"]:
        sport_worlds = {
            "running": (["the same outdoor running track", "the track entrance and adjacent path", "the same track at warmer morning light"], ["track markings", "morning light across the track", "the athlete's shadow on the track"]),
            "boxing": (["the same modest boxing training room", "the edge of the same boxing ring", "the same training room after practice"], ["ropes around the ring", "light across the ring canvas", "the athlete's shadow on the canvas"]),
            "swimming": (["the same quiet swimming pool", "the edge of the same pool", "the same swimming lanes after practice"], ["lane markings under clear water", "light reflected on the pool edge", "ripples settling in the same swimming lane"]),
            "tennis": (["the same local tennis court", "the baseline of the same tennis court", "the same tennis court after practice"], ["court boundary lines", "light across the tennis net", "shadows beside the same court"]),
            "basketball": (["the same local basketball court", "the sideline of the same basketball court", "the same basketball court after practice"], ["court boundary lines", "light near the basketball hoop", "shadows beside the same court"]),
            "football": (["the same local football field", "the sideline of the same football field", "the same football field after practice"], ["field boundary lines", "light near the goal", "shadows beside the same field"]),
            "athletics": (["the sporting location explicitly established by the song", "the entrance of that same sporting location", "that same sporting location after practice"], ["details established by the sporting story", "light on the same sporting surface", "the athlete's shadow in the same location"]),
            "court_or_field_sport": (["the same local sports court or field", "the entrance beside the same playing area", "the same playing area after practice"], ["markings on the playing surface", "morning light on the same playing area", "shadows near the sidelines"]),
            "strength_training": (["the same restrained strength-training room", "the same training area beside a grounded rack", "the same training room after practice"], ["light on the training floor", "grounded equipment established in the song", "the athlete's shadow beside the rack"]),
        }
        world["locations"], world["motifs"] = sport_worlds[brief["sport"]]
    identity = brief["explicitVisualDirection"] or f"Cinematic story: {world['description']}"

    return {
        "version": DIRECTOR_VERSION,
        "createdAtIso": datetime.now(timezone.utc).isoformat(),
        "songVisualSeed": song_seed,
        "storyBrief": brief,
        "storyboard": storyboard,
        "athleticStory": brief["athleticStory"],
        "continuity": brief["continuity"],
        "excludedTools": EXCLUDED_VIDEO_TOOLS,
        "primaryOutcome": "tell a coherent cinematic story related to the song while keeping lyric metaphors from becoming unrelated props",
        "visualWorld": {
            "key": world_key,
            **world,
            "locations": world["locations"],
            "motifs": world["motifs"],
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
            "allowedObjects": world["motifs"],
            "bannedObjects": BANNED_IMAGE_OBJECTS,
            "continuityRules": [
                "keep the same protagonist, wardrobe and connected settings across scenes",
                "advance through tension, decision and resolution; vary framing rather than inventing unrelated locations",
                "one clear scene focus; include only the cast and objects established in the story",
                "no readable text inside generated frames",
                "avoid literal props for every lyric line",
                "listening context, musical genre and words such as strength, weight or rising do not authorize athletic scenery",
                "no Luma and no Runway in this pipeline",
            ],
        },
        "sceneStrategy": (
            "cinematic story related to the full lyrics: establish a recurring protagonist and connected locations, "
            "develop the emotional arc by song section, vary framing and action while preserving continuity; "
            "keep generated frames text-free and do not literalize each phrase"
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
                "action": "repair failed generated frames once when regeneration is enabled, then use a local fallback",
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
                "primary": "OpenAI Images",
                "optional": "ComfyUI/Flux when explicitly selected",
                "controlNet": "optional only for explicit Comfy workflows; OpenAI uses the shot recipe directly",
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
    brief = plan.get("storyBrief") if isinstance(plan.get("storyBrief"), dict) else {}
    direction = compact_text(brief.get("explicitVisualDirection"), 400)
    metaphor = recipe.get("lyricMetaphor") or lyric_visual_metaphor(section, sample_line, index, plan)
    return compact_text(
        (
            "16:9 cinematic text-free premium music-video still; symbolic emotional storytelling within a coherent story. "
            "No words, captions, logos, random props or literal objects from lyric metaphors. Physically grounded, realistic contact shadows. "
            f"Story world: {compact_text(world.get('description'), 240)}. "
            f"Creative direction: {direction or 'a cinematic story related to the full song'}. "
            f"Continuity: {compact_text((brief.get('continuity') or {}).get('protagonist'), 500)}; consistent wardrobe, connected locations and palette. "
            f"Section: {compact_text(section, 60)}. Emotional progression: {metaphor}. "
            f"LOCKED SHOT RECIPE: {recipe['id']}. Subject: {recipe['subject']}. Location: {recipe['location']}. "
            f"Wardrobe: {recipe['wardrobe']}. Action: {recipe['action']}. Prop rules: {recipe['propRules']}. "
            f"Composition: {recipe['composition']}. Camera: {recipe['camera']}; {camera}."
        ),
        2400,
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
    video["userVisualDirection"] = plan["storyBrief"]["explicitVisualDirection"]
    video["userStoryContext"] = plan["storyBrief"]["explicitStoryTheme"]
    video["storyboard"] = copy.deepcopy(plan["storyboard"])
    video["visualIdentity"] = compact_text(plan["visualBible"]["identity"], 600)
    video["visualWorld"] = compact_text(plan["visualWorld"]["description"], 300)
    video["sceneStrategy"] = compact_text(plan["sceneStrategy"], 360)
    video["palette"] = video.get("palette") if isinstance(video.get("palette"), list) and video.get("palette") else plan["visualWorld"]["palette"]
    video["directorPlan"] = plan

    source_sections = [
        {"section": beat["section"], "lines": []}
        for beat in plan["storyboard"].get("beats", [])
    ] or _lyric_sections(package.get("lyrics"), limit=8)
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
    notes = [note for note in notes if not str(note).startswith("Music Director v")]
    director_note = "Music Director v6: storyboard cinematografico preservado con reparto, acciones y lugares; contexto de escucha separado de la historia. Direccion heuristica provisional si falta un storyboard validado."
    if director_note not in notes:
        package["productionNotes"] = [*notes, director_note][:12]
    return package
