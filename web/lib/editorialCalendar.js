const LONG_AGENT_ID = "agent_podcast_general_v2_largo";
const SHORTS_AGENT_ID = "agent_youtube_shorts_esto_no_es_amor";
const CAROUSEL_AGENT_ID = "agent_instagram_carousel_esto_no_es_amor";

const LONG_VIDEO_ROWS = [
  ["2026-06-02", "¿El enamoramiento es una elección o simplemente pasa?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-04", "¿Alguna vez te has enamorado... o solo te obsesionaste?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-07", "Qué se siente estar enamorado de verdad", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-09", "Enamoramiento vs apego: cómo saber qué estás sintiendo", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-11", "La diferencia entre gustar, necesitar, idealizar y amar", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-14", "No todo lo que se siente fuerte es amor", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-16", "¿Te enamoraste de la persona o de lo que imaginaste?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-18", "¿El amor es una elección o un sentimiento?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-21", "La frase \"el amor se elige\" puede ser peligrosa si no entiendes esto", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-23", "Amar también es decidir, pero no todo se debe aguantar", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-25", "¿Puedes construir amor con alguien o tiene que nacer solo?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-28", "¿Vale la pena estar en una relación en 2026?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-06-30", "Relaciones sanas: ¿compañía o pérdida de libertad?", "Junio 2026", "Enamoramiento, amor y elección"],
  ["2026-07-02", "Si tu lenguaje del amor es contacto físico, ¿tu pareja tiene que dártelo?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-05", "Lenguajes del amor: ¿necesidad legítima o expectativa peligrosa?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-07", "¿Te mintió si prometió cambiar y no lo hizo?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-09", "La diferencia entre una mentira y una promesa que alguien no pudo cumplir", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-12", "Cuando alguien dice \"sí puedo\" pero sus acciones dicen otra cosa", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-14", "¿Está bien terminar a alguien por no cumplir lo que prometió?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-16", "No te enamores de lo que promete, mira lo que sostiene", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-19", "Cuando pides amor y te dan excusas", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-21", "¿Tu pareja no puede darte amor o simplemente no quiere?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-23", "El problema de amar a alguien que entiende tus necesidades pero no las cuida", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-26", "¿Es válido terminar una relación porque no recibes tu lenguaje del amor?", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-28", "Contacto físico en pareja: necesidad, deseo o validación", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-07-30", "No todos aman como tú necesitas ser amado", "Julio 2026", "Lenguajes del amor, promesas y decepción"],
  ["2026-08-02", "Red flags que parecen románticas pero son peligrosas", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-04", "La red flag que casi todos justifican por amor", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-06", "Si hace esto al inicio, no lo ignores", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-09", "Red flags de una persona emocionalmente no disponible", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-11", "Red flags en mensajes: cómo alguien te muestra su interés real", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-13", "La peor red flag: sentir que tienes que ganarte su amor", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-16", "Cuando tu cuerpo detecta una red flag antes que tu mente", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-18", "Green flags en una relación sana", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-20", "La green flag más importante: claridad emocional", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-23", "Green flags que no son emocionantes, pero sí sanas", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-25", "La persona correcta no te deja adivinando", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-27", "Green flags de alguien emocionalmente disponible", "Agosto 2026", "Red flags y green flags"],
  ["2026-08-30", "Cómo se siente una relación sana después de relaciones caóticas", "Agosto 2026", "Red flags y green flags"],
  ["2026-09-01", "No es aburrido, es seguro: la green flag que confundimos", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-03", "Cuando alguien te da paz y no ansiedad", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-06", "La green flag que muchas personas ignoran porque no se siente intensa", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-08", "¿Por qué me cuesta tanto enamorarme?", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-10", "Nunca me he enamorado: ¿miedo, bloqueo o elección?", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-13", "Cuando el miedo al amor se disfraza de independencia", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-15", "¿Te cuesta enamorarte o te cuesta confiar?", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-17", "Por qué algunas personas se desconectan cuando alguien se acerca", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-20", "El miedo a depender emocionalmente de alguien", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-22", "Cuando no te enamoras porque no quieres perder el control", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-24", "¿Eres frío o estás protegiendo una herida?", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-27", "La diferencia entre no estar listo y tener miedo a amar", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-09-29", "Por qué el amor sano puede asustarte", "Septiembre 2026", "Miedo a enamorarse y dificultad para confiar"],
  ["2026-10-01", "¿Por qué nos infantilizamos en una relación?", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-04", "Cuando quieres que tu pareja te cuide como si fuera tu padre o madre", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-06", "La niña interior y el niño interior en las relaciones", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-08", "¿Buscas pareja o buscas ser rescatado?", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-11", "Cuando una relación activa tu parte más vulnerable", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-13", "No quieres una pareja, quieres una figura de seguridad", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-15", "Por qué en el amor volvemos a sentirnos niños", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-18", "Cuando el miedo al abandono te hace comportarte como niño", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-20", "El amor adulto no debería convertirse en dependencia infantil", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-22", "Cómo amar desde adulto sin pedir que te salven", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-25", "¿Está mal querer que alguien me mantenga?", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-27", "Querer que te mantengan: ¿amor, comodidad o dependencia?", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-10-29", "La diferencia entre recibir apoyo y depender de alguien", "Octubre 2026", "Infantilización, niño interior y dependencia"],
  ["2026-11-01", "¿Una relación debe ser 50/50 o cada pareja decide sus reglas?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-03", "Cuando buscas seguridad económica porque emocionalmente no te sientes segura", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-05", "¿Ser mantenida es una red flag?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-08", "El dinero también revela heridas en el amor", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-10", "¿Quieres una pareja o alguien que te resuelva la vida?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-12", "Dependencia económica en pareja: lo que nadie quiere decir", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-15", "Amor, dinero y poder: la conversación incómoda que toda pareja debería tener", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-17", "¿El amor se elige o nos vendieron esa idea para aguantar de más?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-19", "Si tu pareja no habla tu lenguaje del amor, ¿deberías terminar?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-22", "¿Te mintió o tú quisiste creerle demasiado?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-24", "Red flags que confundimos con química", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-26", "Green flags que parecen aburridas si vienes del caos", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-11-29", "¿Quieres pareja o quieres que alguien te cuide como mamá o papá?", "Noviembre 2026", "Amor, dinero, poder y temas controversiales"],
  ["2026-12-01", "No me he enamorado nunca: ¿soy frío o estoy herido?", "Diciembre 2026", "Cierre de ciclo"],
  ["2026-12-03", "Preguntas incómodas sobre el amor que todos deberían hacerse", "Diciembre 2026", "Cierre de ciclo"],
];

const SHORT_ROWS = [
  ["2026-05-26", "Me dejó en visto, pero ve mis historias: lo que realmente significa", "Si mira tus historias pero no responde, no confundas curiosidad con interés"],
  ["2026-05-27", "3 razones por las que alguien ve tus historias y no te contesta", "La señal que ignoras cuando te dejan en visto"],
  ["2026-05-28", "La verdad incómoda: quizá no era amor, era apego", "No todo lo que llamas amor te está cuidando"],
  ["2026-05-29", "5 señales de que eso que llamas amor te está rompiendo", "Cuando el amor se siente como ansiedad, escucha esto"],
  ["2026-05-30", "Intensidad no es amor: la frase que cambia todo", "Si duele todo el tiempo, no lo romantices"],
  ["2026-05-31", "Contacto cero no es inmadurez, es protección", "Bloquear también puede ser amor propio cuando hay dolor"],
  ["2026-06-01", "3 señales de que necesitas contacto cero", "Extrañar no significa que debas volver"],
  ["2026-06-02", "¿Te enamoraste o te obsesionaste?", "La diferencia entre amor y obsesión en 60 segundos"],
  ["2026-06-03", "Si piensas en esa persona todo el día, quizá no es amor", "No quieres a la persona: quieres que te elija"],
  ["2026-06-04", "¿Quieres pareja o alguien que te cuide como mamá/papá?", "Cuando una relación activa tu niño interior"],
  ["2026-06-05", "Por qué en el amor volvemos a sentirnos niños", "La diferencia entre apoyo y dependencia emocional"],
  ["2026-06-06", "Si quieres que tu pareja te salve, escucha esto", "Amor adulto: no es que te rescaten, es que te acompañen"],
  ["2026-06-07", "¿El enamoramiento se elige o simplemente pasa?", "La verdad sobre enamorarse: ¿decisión o química?"],
  ["2026-06-08", "3 señales de que solo estás idealizando", "No elegiste enamorarte, pero sí puedes elegir qué haces"],
  ["2026-06-09", "¿Qué se siente estar enamorado de verdad?", "Enamoramiento real vs necesidad emocional"],
  ["2026-06-10", "Si nunca te has enamorado, escucha esto", "Amar no siempre se siente como en las películas"],
  ["2026-06-11", "Enamoramiento vs apego: la diferencia que nadie te explica", "Si te da ansiedad, quizá no es enamoramiento"],
  ["2026-06-12", "3 señales de que estás apegado, no enamorado", "No confundas necesidad con amor"],
  ["2026-06-13", "Cuando el apego se disfraza de enamoramiento", "La prueba simple para saber si es amor o ansiedad"],
  ["2026-06-14", "Gustar, necesitar, idealizar o amar: no son lo mismo", "¿Te gusta la persona o la versión que imaginaste?"],
  ["2026-06-15", "La idealización es una trampa emocional", "3 preguntas para saber si estás amando o necesitando"],
  ["2026-06-16", "No todo lo que se siente fuerte es amor", "Lo intenso también puede ser una señal de alarma"],
  ["2026-06-17", "Por qué confundimos intensidad con destino", "Si te desestabiliza, no lo llames amor todavía"],
  ["2026-06-18", "¿Te enamoraste de la persona o de lo que imaginaste?", "A veces extrañas una historia que nunca pasó"],
  ["2026-06-19", "No extrañas a la persona, extrañas la posibilidad", "Cuando te enamoras del potencial de alguien"],
  ["2026-06-20", "La fantasía duele más que la realidad", "Soltar una ilusión también es duelo"],
  ["2026-06-21", "¿El amor es una elección o un sentimiento?", "Amar no es solo sentir bonito"],
  ["2026-06-22", "El amor se siente, pero también se sostiene", "Si solo hay emoción y no acciones, cuidado"],
  ["2026-06-23", "La frase \"el amor se elige\" puede ser peligrosa", "Elegir amar no significa aguantarlo todo"],
  ["2026-06-24", "No uses \"el amor se elige\" para justificar dolor", "Dónde termina el amor y empieza el autoabandono"],
  ["2026-06-25", "Amar también es decidir, pero no todo se debe aguantar", "El límite entre paciencia y pérdida de dignidad"],
  ["2026-06-26", "3 cosas que no deberías aguantar por amor", "Si amar te borra, no es amor sano"],
  ["2026-06-27", "No confundas compromiso con resignación", "Amar no debería costarte tu paz"],
  ["2026-06-28", "¿El amor se construye o tiene que nacer solo?", "La química inicia, pero las acciones sostienen"],
  ["2026-06-29", "Puedes construir amor, pero no solo con intención", "Cuando uno construye y el otro solo promete"],
  ["2026-06-30", "¿Vale la pena estar en una relación en 2026?", "Relación o paz: la pregunta que muchos se hacen"],
  ["2026-07-01", "Estar solo no siempre es fracaso", "Una relación sana suma, no te absorbe"],
  ["2026-07-02", "Relaciones sanas: ¿compañía o pérdida de libertad?", "El amor sano no debería sentirse como encierro"],
  ["2026-07-03", "3 señales de que una relación respeta tu libertad", "Estar en pareja sin perderte a ti"],
  ["2026-07-04", "No confundas independencia con miedo a amar", "La pareja correcta no te quita mundo, lo expande"],
  ["2026-07-05", "Si tu lenguaje del amor es contacto físico, ¿tu pareja tiene que dártelo?", "Pedir contacto físico: ¿necesidad legítima o exigencia?"],
  ["2026-07-06", "Cuando tu pareja sabe lo que necesitas y no lo hace", "No todos pueden amar como tú necesitas"],
  ["2026-07-07", "Lenguajes del amor: ¿necesidad o expectativa peligrosa?", "El problema de exigir que te amen a tu manera"],
  ["2026-07-08", "Amar a alguien no significa leerle la mente", "Pedir amor sano no es ser intenso"],
  ["2026-07-09", "¿Te mintió si prometió cambiar y no lo hizo?", "Prometer no es amar: cumplir también importa"],
  ["2026-07-10", "La diferencia entre mentira y falta de capacidad", "Cuando sus acciones contradicen sus promesas"],
  ["2026-07-11", "No te enamores de lo que promete", "Mira lo que sostiene, no lo que dice"],
  ["2026-07-12", "¿Fue mentira o una promesa que no pudo sostener?", "Las promesas también son responsabilidad emocional"],
  ["2026-07-13", "Cuando alguien dice \"sí puedo\", pero no puede", "¿Terminar por promesas rotas es exagerado?"],
  ["2026-07-14", "Cuando alguien dice \"sí puedo\" pero sus acciones dicen otra cosa", "Si sus acciones no llegan, las palabras no alcanzan"],
];

export const EDITORIAL_STATUS = [
  { id: "pending", label: "Pendiente" },
  { id: "creating", label: "En creación" },
  { id: "created", label: "Creado" },
  { id: "scheduled", label: "Programado" },
  { id: "published", label: "Publicado" },
  { id: "measured", label: "Medido" },
];

export const EDITORIAL_SIGNAL = [
  { id: "unknown", label: "Sin medir" },
  { id: "normal", label: "Normal" },
  { id: "promising", label: "Prometedor" },
  { id: "winner", label: "Ganador" },
  { id: "avoid", label: "No repetir" },
];

function longVideoEvent(row, index) {
  const [date, title, monthLabel, pillar] = row;
  return {
    id: `long-${String(index + 1).padStart(3, "0")}`,
    sourceOrder: index + 1,
    channel: "Esto no es amor",
    type: "long",
    typeLabel: "Video largo",
    date,
    time: "20:00",
    displayTime: "Video largo",
    title,
    monthLabel,
    pillar,
    agentId: LONG_AGENT_ID,
    durationProfile: "long",
    derivativeAgentIds: [SHORTS_AGENT_ID, CAROUSEL_AGENT_ID],
  };
}

function shortEvents(row, index) {
  const [date, title1500, title1800] = row;
  const dayNumber = index + 1;
  return [
    {
      id: `short-${String(dayNumber).padStart(3, "0")}-1500`,
      sourceOrder: dayNumber,
      channel: "Esto no es amor",
      type: "short",
      typeLabel: "Short",
      date,
      time: "15:00",
      displayTime: "3:00 p.m.",
      title: title1500,
      monthLabel: monthFromDate(date),
      pillar: "Shorts de apoyo y descubrimiento",
      agentId: SHORTS_AGENT_ID,
      durationProfile: "shorts75",
      derivativeAgentIds: [LONG_AGENT_ID, CAROUSEL_AGENT_ID],
    },
    {
      id: `short-${String(dayNumber).padStart(3, "0")}-1800`,
      sourceOrder: dayNumber,
      channel: "Esto no es amor",
      type: "short",
      typeLabel: "Short",
      date,
      time: "18:00",
      displayTime: "6:00 p.m.",
      title: title1800,
      monthLabel: monthFromDate(date),
      pillar: "Shorts de apoyo y descubrimiento",
      agentId: SHORTS_AGENT_ID,
      durationProfile: "shorts75",
      derivativeAgentIds: [LONG_AGENT_ID, CAROUSEL_AGENT_ID],
    },
  ];
}

function monthFromDate(date) {
  const parsed = new Date(`${date}T12:00:00`);
  const month = new Intl.DateTimeFormat("es-MX", {
    month: "long",
  }).format(parsed);
  const year = parsed.getFullYear();
  return `${month.replace(/^\w/, (letter) => letter.toUpperCase())} ${year}`;
}

export const EDITORIAL_CALENDAR_ITEMS = [
  ...SHORT_ROWS.flatMap(shortEvents),
  ...LONG_VIDEO_ROWS.map(longVideoEvent),
].sort((a, b) => {
  const left = `${a.date}T${a.time || "23:59"}:00`;
  const right = `${b.date}T${b.time || "23:59"}:00`;
  return left.localeCompare(right);
});

export function buildCreateContentHref(item, overrides = {}) {
  const agentId = overrides.agentId || item.agentId;
  const topic = overrides.topic || item.title;
  const durationProfile = overrides.durationProfile || item.durationProfile || "";
  const params = new URLSearchParams({
    agentId,
    topic,
    from: "agenda",
  });
  if (durationProfile) params.set("durationProfile", durationProfile);
  return `/dashboard/new?${params.toString()}`;
}

export function derivativeOptionsForItem(item) {
  const options = [];
  if (item.type === "long") {
    options.push({
      label: "Crear Short derivado",
      agentId: SHORTS_AGENT_ID,
      durationProfile: "shorts75",
    });
    options.push({
      label: "Crear carrusel",
      agentId: CAROUSEL_AGENT_ID,
      durationProfile: "carousel8",
    });
  } else {
    options.push({
      label: "Crear largo relacionado",
      agentId: LONG_AGENT_ID,
      durationProfile: "long",
    });
    options.push({
      label: "Crear carrusel",
      agentId: CAROUSEL_AGENT_ID,
      durationProfile: "carousel8",
    });
  }
  return options;
}
