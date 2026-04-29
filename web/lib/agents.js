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
];
