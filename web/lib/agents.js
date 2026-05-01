/**
 * Agent catalog — system agents for Content Factory.
 * These are loaded into Firestore on first run and displayed in the UI.
 */
export const SYSTEM_AGENTS = [
  {
    agentId: "agent_horror",
    name: "Horror Histórico",
    emoji: "💀",
    description: "Plagas medievales, torturas reales, castillos malditos. Narrativa oscura y atmosférica basada en hechos reales.",
    category: "history",
    promptFile: "agent_horror.md",
    tier: "starter",
    exampleTopics: [
      "La Peste Negra de 1347",
      "Las torturas de la Santa Inquisición",
      "El castillo de Vlad el Empalador"
    ],
    color: "#8B0000",
  },
  {
    agentId: "agent_misterios",
    name: "Misterios Sin Resolver",
    emoji: "🔍",
    description: "Conspiraciones, desapariciones y casos fríos. Suspense investigativo que engancha desde el primer segundo.",
    category: "mystery",
    promptFile: "agent_misterios.md",
    tier: "starter",
    exampleTopics: [
      "La desaparición de la colonia Roanoke",
      "El triángulo de las Bermudas",
      "El caso Dyatlov: muerte en los Urales"
    ],
    color: "#1a1a2e",
  },
  {
    agentId: "agent_biografias",
    name: "Biografías Épicas",
    emoji: "👑",
    description: "Las vidas secretas de figuras legendarias. Drama humano detrás del mito histórico.",
    category: "biography",
    promptFile: "agent_biografias.md",
    tier: "starter",
    exampleTopics: [
      "La vida secreta de Nikola Tesla",
      "Cleopatra: poder, seducción y tragedia",
      "Genghis Khan: de huérfano a emperador"
    ],
    color: "#DAA520",
  },
  {
    agentId: "agent_ciencia",
    name: "Ciencia Explicada",
    emoji: "🔬",
    description: "El universo, la física cuántica y los misterios de la vida. Asombro cósmico con elegancia poética.",
    category: "science",
    promptFile: "agent_ciencia.md",
    tier: "starter",
    exampleTopics: [
      "¿Qué hay dentro de un agujero negro?",
      "La paradoja cuántica que rompe la realidad",
      "El ADN: el código que nos construye"
    ],
    color: "#00CED1",
  },
  {
    agentId: "agent_finanzas",
    name: "Catástrofes Financieras",
    emoji: "💰",
    description: "Crashes bursátiles, esquemas Ponzi y burbujas cripto. Thrillers financieros que paralizan.",
    category: "finance",
    promptFile: "agent_finanzas.md",
    tier: "creator",
    exampleTopics: [
      "El colapso de FTX y Sam Bankman-Fried",
      "La burbuja puntocom del año 2000",
      "Bernie Madoff: $65 mil millones en humo"
    ],
    color: "#228B22",
  },
  {
    agentId: "agent_filosofia",
    name: "Filosofía Estoica",
    emoji: "🧘",
    description: "Marco Aurelio, Séneca y sabiduría práctica. Meditaciones que transforman la vida moderna.",
    category: "philosophy",
    promptFile: "agent_filosofia.md",
    tier: "starter",
    exampleTopics: [
      "Marco Aurelio y el arte de no sufrir",
      "Séneca: cómo vivir cuando todo se derrumba",
      "El estoicismo aplicado al trabajo moderno"
    ],
    color: "#6A5ACD",
  },
  {
    agentId: "agent_erotico_historico",
    name: "Romance Histórico",
    emoji: "🔥",
    description: "Pasión, traición y redención en civilizaciones antiguas. Erotismo cinematográfico YouTube-safe.",
    category: "romance",
    promptFile: "agent_erotico_historico.md",
    tier: "creator",
    exampleTopics: [
      "Pasión y traición en el Antiguo Egipto",
      "Los secretos de las cortesanas de Versalles",
      "Amor prohibido en la Roma de Nerón"
    ],
    color: "#DC143C",
  },
  {
    agentId: "agent_historico",
    name: "Documental Histórico",
    emoji: "🏛️",
    description: "Reconstrucciones inmersivas de la vida cotidiana en eras pasadas. Viajes en el tiempo cinematográficos.",
    category: "history",
    promptFile: "agent_historico.md",
    tier: "free",
    exampleTopics: [
      "Un día en la vida de un samurái en 1700",
      "La caída del Imperio Romano",
      "La Revolución Francesa: sangre y libertad"
    ],
    color: "#8B7355",
  },
  {
    agentId: "agent_psicologia_oscura",
    name: "Psicología Oscura",
    emoji: "🧠",
    description: "Las mentes más perturbadoras de la historia. Análisis forense de dictadores, cultos y manipuladores.",
    category: "psychology",
    promptFile: "agent_psicologia_oscura.md",
    tier: "creator",
    exampleTopics: [
      "La mente de un dictador: Stalin",
      "Jim Jones y el suicidio masivo de Jonestown",
      "Los mecanismos de un narcisista peligroso"
    ],
    color: "#4A0E4E",
  },
  {
    agentId: "agent_civilizaciones",
    name: "Civilizaciones Perdidas",
    emoji: "🏺",
    description: "Sumeria, los Mayas, Atlántida. Exploraciones épicas de mundos que se desvanecieron en el tiempo.",
    category: "history",
    promptFile: "agent_civilizaciones.md",
    tier: "starter",
    exampleTopics: [
      "Los Mayas y su misteriosa desaparición",
      "La ciudad perdida de Petra",
      "Los secretos de la civilización del Indo"
    ],
    color: "#CD853F",
  },
  {
    agentId: "agent_true_crime",
    name: "True Crime",
    emoji: "🔪",
    description: "Casos criminales reales narrados como thrillers. Investigaciones forenses, asesinos seriales y justicia.",
    category: "crime",
    promptFile: "agent_true_crime.md",
    tier: "creator",
    exampleTopics: [
      "El caso del Zodiac Killer",
      "Ted Bundy: el monstruo carismático",
      "El misterio de Jack el Destripador"
    ],
    color: "#8B0000",
  },
  {
    agentId: "agent_mitologia",
    name: "Mitología Universal",
    emoji: "⚡",
    description: "Dioses, titanes y héroes de todas las culturas. Épicas inmortales narradas con poder cinematográfico.",
    category: "mythology",
    promptFile: "agent_mitologia.md",
    tier: "starter",
    exampleTopics: [
      "La guerra entre Zeus y los Titanes",
      "Quetzalcóatl: la serpiente emplumada",
      "Thor y Ragnarök: el fin del mundo nórdico"
    ],
    color: "#FFD700",
  },
  {
    agentId: "agent_conspiraciones",
    name: "Conspiraciones",
    emoji: "👁️",
    description: "Sociedades secretas, encubrimientos gubernamentales y teorías que desafían la versión oficial.",
    category: "mystery",
    promptFile: "agent_conspiraciones.md",
    tier: "creator",
    exampleTopics: [
      "Los Illuminati y el Nuevo Orden Mundial",
      "Área 51: qué oculta realmente el gobierno",
      "MK-Ultra: el programa de control mental de la CIA"
    ],
    color: "#2F4F4F",
  },
  {
    agentId: "agent_tecnologia",
    name: "Tecnología del Futuro",
    emoji: "🤖",
    description: "IA, implantes cerebrales, computación cuántica. El futuro que ya está aquí, explicado con claridad.",
    category: "technology",
    promptFile: "agent_tecnologia.md",
    tier: "starter",
    exampleTopics: [
      "Neuralink: el chip que lee tu mente",
      "La singularidad de la IA: ¿estamos listos?",
      "Computación cuántica explicada sin dolor"
    ],
    color: "#00BFFF",
  },
  {
    agentId: "agent_guerras",
    name: "Guerras y Batallas",
    emoji: "⚔️",
    description: "Las batallas más épicas y brutales de la historia humana. Estrategia, sacrificio y destrucción.",
    category: "history",
    promptFile: "agent_guerras.md",
    tier: "starter",
    exampleTopics: [
      "La batalla de Stalingrado: infierno en la tierra",
      "D-Day: el día más largo",
      "Las Termópilas: 300 espartanos vs un imperio"
    ],
    color: "#556B2F",
  },
  {
    agentId: "agent_espionaje",
    name: "Espionaje Real",
    emoji: "🕵️",
    description: "Operaciones encubiertas, agentes dobles y la Guerra Fría. Historias reales más intensas que la ficción.",
    category: "mystery",
    promptFile: "agent_espionaje.md",
    tier: "creator",
    exampleTopics: [
      "La red de espías del Proyecto Manhattan",
      "Aldrich Ames: el topo de la CIA",
      "El Mossad y la caza de criminales nazis"
    ],
    color: "#363636",
  },
  {
    agentId: "agent_apocalipsis",
    name: "Apocalipsis y Catástrofes",
    emoji: "🌋",
    description: "Erupciones, tsunamis, pandemias y extinciones masivas. El poder destructivo de la naturaleza y el hombre.",
    category: "science",
    promptFile: "agent_apocalipsis.md",
    tier: "starter",
    exampleTopics: [
      "La erupción de Pompeya en el año 79",
      "El asteroide que mató a los dinosaurios",
      "Chernóbil: la noche que envenenó Europa"
    ],
    color: "#FF4500",
  },
  {
    agentId: "agent_religiones",
    name: "Religiones del Mundo",
    emoji: "🕌",
    description: "Orígenes, rituales y misterios de las grandes religiones. Exploración respetuosa y fascinante.",
    category: "philosophy",
    promptFile: "agent_religiones.md",
    tier: "starter",
    exampleTopics: [
      "Los orígenes del Islam",
      "El budismo: de Siddhartha al Zen",
      "Los misterios del Vaticano"
    ],
    color: "#9370DB",
  },
  {
    agentId: "agent_metafisica",
    name: "Metafísica y Consciencia",
    emoji: "✨",
    description: "Hermetismo, leyes universales, DMT y los límites de la realidad. Filosofía para despertar.",
    category: "philosophy",
    promptFile: "agent_metafisica.md",
    tier: "creator",
    exampleTopics: [
      "El Kybalión: las 7 leyes del universo",
      "¿Vivimos en una simulación?",
      "DMT: la molécula del espíritu"
    ],
    color: "#7B68EE",
  },
  {
    agentId: "agent_imperios",
    name: "Imperios Legendarios",
    emoji: "🦅",
    description: "Ascenso, esplendor y caída de los imperios que dominaron el mundo. Poder absoluto y decadencia.",
    category: "history",
    promptFile: "agent_imperios.md",
    tier: "starter",
    exampleTopics: [
      "El Imperio Mongol: la conquista más grande",
      "El auge y caída del Imperio Británico",
      "El Imperio Otomano: 600 años de poder"
    ],
    color: "#B8860B",
  },
  {
    agentId: "agent_arte",
    name: "Arte y Genios Creativos",
    emoji: "🎨",
    description: "Las mentes creativas más brillantes y torturadas. El arte como obsesión, locura y trascendencia.",
    category: "biography",
    promptFile: "agent_arte.md",
    tier: "starter",
    exampleTopics: [
      "Van Gogh: genio, locura y girasoles",
      "Da Vinci: el hombre que lo inventó todo",
      "Frida Kahlo: dolor convertido en arte"
    ],
    color: "#FF69B4",
  },
  {
    agentId: "agent_emprendimiento",
    name: "Emprendimiento Extremo",
    emoji: "🚀",
    description: "Startups, fracasos épicos y fortunas creadas desde cero. Las historias reales detrás de los imperios modernos.",
    category: "business",
    promptFile: "agent_emprendimiento.md",
    tier: "creator",
    exampleTopics: [
      "Elon Musk: de casi quebrar a Marte",
      "WeWork: el fraude de $47 mil millones",
      "Steve Jobs: el genio que fue despedido de su propia empresa"
    ],
    color: "#FF8C00",
  },
  {
    agentId: "agent_negocios",
    name: "Negocios y Estrategia",
    emoji: "📊",
    description: "Guerras corporativas, monopolios y las decisiones que crearon o destruyeron fortunas.",
    category: "business",
    promptFile: "agent_negocios.md",
    tier: "creator",
    exampleTopics: [
      "La guerra Coca-Cola vs Pepsi",
      "Amazon: cómo Jeff Bezos conquistó el comercio",
      "Nokia: de gigante a irrelevante en 5 años"
    ],
    color: "#2E8B57",
  },
  {
    agentId: "agent_liderazgo",
    name: "Liderazgo y Poder",
    emoji: "🎖️",
    description: "Los líderes que cambiaron el curso de la historia. Carisma, estrategia y las sombras del poder.",
    category: "biography",
    promptFile: "agent_liderazgo.md",
    tier: "starter",
    exampleTopics: [
      "Winston Churchill: liderazgo bajo fuego",
      "Mandela: 27 años en prisión, cero rencor",
      "Alejandro Magno: el conquistador de 25 años"
    ],
    color: "#4169E1",
  },
  {
    agentId: "agent_biblico",
    name: "Historias Bíblicas",
    emoji: "📜",
    description: "Las narrativas más poderosas de la Biblia con rigor histórico y cinematografía épica.",
    category: "religion",
    promptFile: "agent_biblico.md",
    tier: "starter",
    exampleTopics: [
      "El Éxodo: la liberación de un pueblo",
      "David vs Goliat: fe contra imposible",
      "El Apocalipsis de Juan: visión del fin"
    ],
    color: "#8B4513",
  },
  {
    agentId: "agent_viajes",
    name: "Viajes y Exploraciones",
    emoji: "🗺️",
    description: "Las expediciones más peligrosas y los lugares más remotos del planeta. Aventura sin límites.",
    category: "travel",
    promptFile: "agent_viajes.md",
    tier: "free",
    exampleTopics: [
      "La expedición perdida de Shackleton",
      "Los lugares más peligrosos del mundo",
      "Marco Polo: el viaje que cambió Occidente"
    ],
    color: "#20B2AA",
  },
  {
    agentId: "agent_noticias_virales",
    name: "Noticias Virales",
    emoji: "📰",
    description: "Los eventos más impactantes del momento explicados con profundidad. Contenido trending con contexto real.",
    category: "news",
    promptFile: "agent_noticias_virales.md",
    tier: "creator",
    exampleTopics: [
      "Lo que nadie te dice sobre [evento actual]",
      "La verdad detrás de la noticia viral",
      "Por qué todo el mundo habla de esto"
    ],
    color: "#FF6347",
  },
];
