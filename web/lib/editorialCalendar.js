const LONG_AGENT_ID = "agent_podcast_general_v2_largo";
const SHORTS_AGENT_ID = "agent_youtube_shorts_esto_no_es_amor";
const CAROUSEL_AGENT_ID = "agent_instagram_carousel_esto_no_es_amor";
const MYSTERY_LONG_AGENT_ID = "agent_misterios_v2";
const MYSTERY_SHORTS_AGENT_ID = "agent_youtube_shorts_archivos_prohibidos";

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

const MYSTERY_TOPIC_GROUPS = [
  {
    pillar: "Desapariciones",
    topics: [
      "El caso de Elisa Lam",
      "El vuelo de Malaysia Airlines Flight 370",
      "La desaparición de Madeleine McCann",
      "El misterio del Triángulo de las Bermudas",
      "El caso Dyatlov Pass",
      "Personas desaparecidas en parques nacionales",
      "El barco fantasma Mary Celeste",
      "El niño de Somerton",
      "El caso del hombre de Taured",
      "La colonia perdida de Roanoke",
    ],
  },
  {
    pillar: "Casos perturbadores",
    topics: [
      "El asesino Zodiac",
      "Jack el Destripador",
      "El caso Black Dahlia",
      "El culto Heaven's Gate",
      "La familia que desapareció sin dejar rastro",
      "El experimento ruso del sueño",
      "La señal UVB-76",
      "El caso de los cuerpos de Isdal",
      "El hotel más embrujado de Japón",
      "El misterio de Hinterkaifeck",
    ],
  },
  {
    pillar: "Internet y deep web",
    topics: [
      "Cicada 3301",
      "La web más perturbadora encontrada en la deep web",
      "Videos imposibles de explicar en internet",
      "El canal extraño de Local58",
      "El caso de Webdriver Torso",
      "El misterio de Erratas",
      "Transmisiones pirata más perturbadoras",
      "El video I Feel Fantastic",
      "La creepypasta que asustó internet",
      "El juego Sad Satan",
    ],
  },
  {
    pillar: "Misterios espaciales",
    topics: [
      "La señal Wow!",
      "El astronauta perdido de la URSS",
      "Sonidos extraños captados en el espacio",
      "El lado oscuro de la Luna",
      "El objeto Oumuamua",
      "El planeta nueve",
      "Señales extraterrestres reales",
      "El misterio de Marte y Cydonia",
      "Satélites fantasmas orbitando la Tierra",
      "El cosmonauta desaparecido",
    ],
  },
  {
    pillar: "Expedientes y conspiraciones",
    topics: [
      "MK Ultra",
      "El Área 51",
      "El Proyecto Montauk",
      "Archivos secretos desclasificados por la CIA",
      "Experimentos humanos secretos",
      "La conspiración de Philadelphia Experiment",
      "Operación Paperclip",
      "El misterio de los Hombres de Negro",
      "La conspiración del alunizaje",
      "El caso Roswell",
    ],
  },
  {
    pillar: "Misterios históricos",
    topics: [
      "La Atlántida",
      "¿Quién construyó las pirámides realmente?",
      "El manuscrito Voynich",
      "La máquina de Anticitera",
      "Civilizaciones perdidas bajo el océano",
      "Los gigantes de Patagonia",
      "El misterio de Göbekli Tepe",
      "El fuego griego perdido",
      "La espada imposible encontrada en roca",
      "La biblioteca perdida de Alejandría",
    ],
  },
  {
    pillar: "Fenómenos extraños",
    topics: [
      "Personas que desaparecieron en niebla",
      "Luces inexplicables en el cielo",
      "El bosque suicida de Aokigahara",
      "Sonidos del cielo escuchados en todo el mundo",
      "Las sombras captadas por cámaras",
      "Objetos encontrados fuera de tiempo",
      "El fenómeno Mandela",
      "Gente que afirma venir del futuro",
      "El misterio de Skinwalker Ranch",
      "Las backrooms",
    ],
  },
  {
    pillar: "Casos psicológicos",
    topics: [
      "El experimento Stanford",
      "El caso de la sonrisa de Glasgow",
      "Personas que despertaron en lugares desconocidos",
      "El síndrome de París",
      "El experimento Milgram",
      "El misterio de los sueños compartidos",
      "La mujer que no podía olvidar nada",
      "El pueblo donde nadie dormía",
      "Personas que desaparecieron de su propia vida",
      "La epidemia de baile de 1518",
    ],
  },
  {
    pillar: "Misterios modernos",
    topics: [
      "Señales misteriosas en Google Maps",
      "El iceberg negro fotografiado en el océano",
      "Videos de TikTok imposibles de explicar",
      "Misterios encontrados en Reddit",
      "Las coordenadas más perturbadoras de internet",
      "Inteligencias artificiales que actuaron extraño",
      "Robots que dijeron cosas perturbadoras",
      "El experimento de Facebook que salió mal",
      "El misterio de los NPC streamers",
      "Grabaciones extrañas captadas por Alexa",
    ],
  },
  {
    pillar: "Finales potentes",
    topics: [
      "Los lugares donde la gente desaparece más",
      "Misterios que el FBI nunca resolvió",
      "Los videos más perturbadores jamás grabados",
      "Fotografías imposibles de explicar",
      "Audios aterradores reales",
      "Los secretos ocultos en la Antártida",
      "Casos donde el tiempo se rompió",
      "Las llamadas telefónicas más misteriosas",
      "Las últimas palabras más perturbadoras",
      "Misterios que siguen ocurriendo hoy",
    ],
  },
];

const MYSTERY_SHORT_SEO_TITLES = {
  "El caso de Elisa Lam": "El caso Elisa Lam: el video del elevador que nadie pudo explicar",
  "El vuelo de Malaysia Airlines Flight 370": "Vuelo MH370: la desaparición aérea que sigue sin respuesta",
  "La desaparición de Madeleine McCann": "Madeleine McCann: la desaparición que obsesionó al mundo",
  "El misterio del Triángulo de las Bermudas": "Triángulo de las Bermudas: barcos y aviones que desaparecieron",
  "El caso Dyatlov Pass": "Dyatlov Pass: la noche donde nada encaja",
  "Personas desaparecidas en parques nacionales": "Personas desaparecidas en parques nacionales: el patrón inquietante",
  "El barco fantasma Mary Celeste": "Mary Celeste: el barco fantasma encontrado sin tripulación",
  "El niño de Somerton": "El niño de Somerton: el cadáver que tardó décadas en tener nombre",
  "El caso del hombre de Taured": "El hombre de Taured: el viajero de un país que no existe",
  "La colonia perdida de Roanoke": "Roanoke: la colonia perdida y la palabra que quedó",
  "El asesino Zodiac": "Asesino Zodiac: las cartas cifradas que aún inquietan al FBI",
  "Jack el Destripador": "Jack el Destripador: el asesino que Londres nunca identificó",
  "El caso Black Dahlia": "Black Dahlia: el crimen que Hollywood nunca pudo olvidar",
  "El culto Heaven's Gate": "Heaven's Gate: el culto que terminó mirando al cielo",
  "La familia que desapareció sin dejar rastro": "La familia que desapareció sin dejar rastro: el caso sin cierre",
  "El experimento ruso del sueño": "El experimento ruso del sueño: la historia que internet volvió pesadilla",
  "La señal UVB-76": "UVB-76: la señal de radio que nunca deja de transmitir",
  "El caso de los cuerpos de Isdal": "Los cuerpos de Isdal: el misterio noruego que no encaja",
  "El hotel más embrujado de Japón": "El hotel más embrujado de Japón: historias difíciles de comprobar",
  "El misterio de Hinterkaifeck": "Hinterkaifeck: el crimen rural más inquietante de Alemania",
  "Cicada 3301": "Cicada 3301: el acertijo de internet que reclutaba genios",
  "La web más perturbadora encontrada en la deep web": "La web más perturbadora de la deep web: mito, evidencia y miedo",
  "Videos imposibles de explicar en internet": "Videos imposibles de explicar: casos que internet no pudo cerrar",
  "El canal extraño de Local58": "Local58: el canal analógico que convirtió la señal en terror",
  "El caso de Webdriver Torso": "Webdriver Torso: los videos extraños que escondían una explicación",
  "El misterio de Erratas": "El misterio de Erratas: el caso viral que nadie entiende",
  "Transmisiones pirata más perturbadoras": "Transmisiones pirata perturbadoras: mensajes que interrumpieron la TV",
  "El video I Feel Fantastic": "I Feel Fantastic: el video extraño que internet nunca olvidó",
  "La creepypasta que asustó internet": "La creepypasta que asustó internet: cuando una historia se volvió leyenda",
  "El juego Sad Satan": "Sad Satan: el juego prohibido que aterrorizó a la deep web",
  "La señal Wow!": "La señal Wow!: el mensaje espacial que nunca se repitió",
  "El astronauta perdido de la URSS": "El astronauta perdido de la URSS: mito espacial o encubrimiento",
  "Sonidos extraños captados en el espacio": "Sonidos extraños del espacio: señales que parecen imposibles",
  "El lado oscuro de la Luna": "El lado oscuro de la Luna: misterios que siguen circulando",
  "El objeto Oumuamua": "Oumuamua: el objeto interestelar que dividió a los científicos",
  "El planeta nueve": "Planeta Nueve: el planeta oculto que podría estar ahí afuera",
  "Señales extraterrestres reales": "Señales extraterrestres reales: las detecciones más extrañas",
  "El misterio de Marte y Cydonia": "Marte y Cydonia: la cara que encendió teorías durante décadas",
  "Satélites fantasmas orbitando la Tierra": "Satélites fantasmas: objetos que no deberían orbitar la Tierra",
  "El cosmonauta desaparecido": "El cosmonauta desaparecido: la transmisión que nadie pudo confirmar",
  "MK Ultra": "MK Ultra: el experimento mental secreto de la CIA",
  "El Área 51": "Área 51: qué se sabe realmente de la base más famosa",
  "El Proyecto Montauk": "Proyecto Montauk: el experimento que mezcló ciencia y paranoia",
  "Archivos secretos desclasificados por la CIA": "Archivos desclasificados de la CIA: secretos que sí fueron reales",
  "Experimentos humanos secretos": "Experimentos humanos secretos: casos reales que salieron a la luz",
  "La conspiración de Philadelphia Experiment": "Philadelphia Experiment: el buque que supuestamente desapareció",
  "Operación Paperclip": "Operación Paperclip: científicos nazis dentro de Estados Unidos",
  "El misterio de los Hombres de Negro": "Hombres de Negro: el origen real de la leyenda",
  "La conspiración del alunizaje": "Conspiración del alunizaje: por qué algunos aún dudan",
  "El caso Roswell": "Roswell: el caso ovni que nunca dejó de crecer",
  "La Atlántida": "La Atlántida: mito antiguo o civilización perdida",
  "¿Quién construyó las pirámides realmente?": "Quién construyó las pirámides: lo que sí dice la evidencia",
  "El manuscrito Voynich": "Manuscrito Voynich: el libro que nadie ha logrado leer",
  "La máquina de Anticitera": "Máquina de Anticitera: tecnología antigua imposible de ignorar",
  "Civilizaciones perdidas bajo el océano": "Civilizaciones bajo el océano: ruinas que cambiaron preguntas",
  "Los gigantes de Patagonia": "Gigantes de Patagonia: el mito que recorrió el mundo",
  "El misterio de Göbekli Tepe": "Göbekli Tepe: el templo que reescribió la historia",
  "El fuego griego perdido": "Fuego griego: el arma perdida que nadie pudo recrear",
  "La espada imposible encontrada en roca": "La espada en la roca: hallazgos que parecen imposibles",
  "La biblioteca perdida de Alejandría": "Biblioteca de Alejandría: lo que perdimos para siempre",
  "Personas que desaparecieron en niebla": "Personas desaparecidas en niebla: relatos que parecen imposibles",
  "Luces inexplicables en el cielo": "Luces inexplicables en el cielo: fenómenos reales sin respuesta simple",
  "El bosque suicida de Aokigahara": "Bosque de Aokigahara: el lugar más oscuro de Japón",
  "Sonidos del cielo escuchados en todo el mundo": "Sonidos del cielo: grabaciones extrañas escuchadas en el mundo",
  "Las sombras captadas por cámaras": "Sombras captadas por cámaras: evidencia o ilusión",
  "Objetos encontrados fuera de tiempo": "Objetos fuera de tiempo: hallazgos que no deberían existir",
  "El fenómeno Mandela": "Efecto Mandela: por qué recordamos cosas que no pasaron",
  "Gente que afirma venir del futuro": "Viajeros del tiempo: personas que afirmaron venir del futuro",
  "El misterio de Skinwalker Ranch": "Skinwalker Ranch: el rancho donde todo parece ocurrir",
  "Las backrooms": "Backrooms: la leyenda que convirtió internet en laberinto",
  "El experimento Stanford": "Experimento Stanford: cuando el poder cambió a personas normales",
  "El caso de la sonrisa de Glasgow": "La sonrisa de Glasgow: el origen de una marca perturbadora",
  "Personas que despertaron en lugares desconocidos": "Personas que despertaron en lugares desconocidos: casos imposibles",
  "El síndrome de París": "Síndrome de París: cuando un viaje rompe la realidad",
  "El experimento Milgram": "Experimento Milgram: hasta dónde obedecería una persona",
  "El misterio de los sueños compartidos": "Sueños compartidos: el misterio de soñar lo mismo",
  "La mujer que no podía olvidar nada": "La mujer que no podía olvidar nada: vivir con memoria perfecta",
  "El pueblo donde nadie dormía": "El pueblo donde nadie dormía: epidemia, miedo y explicación",
  "Personas que desaparecieron de su propia vida": "Personas que desaparecieron de su propia vida: empezar de cero",
  "La epidemia de baile de 1518": "Epidemia de baile de 1518: cuando bailar se volvió mortal",
  "Señales misteriosas en Google Maps": "Señales misteriosas en Google Maps: coordenadas que inquietan",
  "El iceberg negro fotografiado en el océano": "El iceberg negro: la fotografía que parece de otro planeta",
  "Videos de TikTok imposibles de explicar": "Videos de TikTok imposibles de explicar: misterio moderno",
  "Misterios encontrados en Reddit": "Misterios encontrados en Reddit: hilos que nadie pudo cerrar",
  "Las coordenadas más perturbadoras de internet": "Coordenadas perturbadoras de internet: lugares que dan miedo",
  "Inteligencias artificiales que actuaron extraño": "IA que actuó extraño: casos que encendieron alarmas",
  "Robots que dijeron cosas perturbadoras": "Robots que dijeron cosas perturbadoras: frases que inquietaron al mundo",
  "El experimento de Facebook que salió mal": "El experimento de Facebook que salió mal: cuando las máquinas aprendieron",
  "El misterio de los NPC streamers": "NPC streamers: el fenómeno más extraño de TikTok",
  "Grabaciones extrañas captadas por Alexa": "Grabaciones extrañas de Alexa: audios que nadie esperaba escuchar",
  "Los lugares donde la gente desaparece más": "Lugares donde la gente desaparece más: patrones que asustan",
  "Misterios que el FBI nunca resolvió": "Misterios que el FBI nunca resolvió: casos abiertos",
  "Los videos más perturbadores jamás grabados": "Videos perturbadores jamás grabados: lo que muestran",
  "Fotografías imposibles de explicar": "Fotografías imposibles de explicar: imágenes que no encajan",
  "Audios aterradores reales": "Audios aterradores reales: grabaciones que siguen circulando",
  "Los secretos ocultos en la Antártida": "Secretos ocultos en la Antártida: teorías, mapas y evidencia",
  "Casos donde el tiempo se rompió": "Casos donde el tiempo se rompió: historias imposibles",
  "Las llamadas telefónicas más misteriosas": "Llamadas telefónicas misteriosas: voces que no deberían estar",
  "Las últimas palabras más perturbadoras": "Últimas palabras perturbadoras: frases antes del misterio",
  "Misterios que siguen ocurriendo hoy": "Misterios que siguen ocurriendo hoy: casos sin cierre",
};

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
    channelSlug: "esto-no-es-amor",
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
      channelSlug: "esto-no-es-amor",
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
      channelSlug: "esto-no-es-amor",
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

function isoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function mysteryDateForIndex(index) {
  const startDate = new Date("2026-06-17T12:00:00");
  const weekdayOffsets = [0, 2, 5];
  const week = Math.floor(index / weekdayOffsets.length);
  const position = index % weekdayOffsets.length;
  return isoDate(addDays(startDate, week * 7 + weekdayOffsets[position]));
}

function mysteryShortDateForIndex(index) {
  const startDate = new Date("2026-06-17T12:00:00");
  return isoDate(addDays(startDate, Math.floor(index / 2)));
}

function buildMysteryTopicEntries() {
  const maxTopics = Math.max(...MYSTERY_TOPIC_GROUPS.map((group) => group.topics.length));
  const entries = [];
  for (let topicIndex = 0; topicIndex < maxTopics; topicIndex += 1) {
    MYSTERY_TOPIC_GROUPS.forEach((group) => {
      const title = group.topics[topicIndex];
      if (!title) return;
      entries.push({
        title,
        pillar: group.pillar,
        date: mysteryDateForIndex(entries.length),
      });
    });
  }
  return entries;
}

function mysteryLongVideoEvent(entry, index) {
  return {
    id: `mystery-long-${String(index + 1).padStart(3, "0")}`,
    sourceOrder: index + 1,
    channel: "La última evidencia",
    channelSlug: "la-ultima-evidencia",
    type: "long",
    typeLabel: "Video largo",
    date: entry.date,
    time: "21:00",
    displayTime: "9:00 p.m.",
    title: entry.title,
    monthLabel: monthFromDate(entry.date),
    pillar: entry.pillar,
    agentId: MYSTERY_LONG_AGENT_ID,
    durationProfile: "long",
    derivativeAgentIds: [MYSTERY_SHORTS_AGENT_ID],
  };
}

function seoKeywordsForMysteryTopic(title, pillar) {
  const cleanTitle = title.replace(/[¿?"]/g, "").replace(/\s+/g, " ").trim();
  return `${cleanTitle}, ${pillar.toLowerCase()}, misterio real, caso sin resolver, documental corto`;
}

function mysteryShortEvent(entry, index) {
  const firstSlot = index % 2 === 0;
  const date = mysteryShortDateForIndex(index);
  return {
    id: `mystery-short-${String(index + 1).padStart(3, "0")}`,
    sourceOrder: index + 1,
    channel: "La última evidencia",
    channelSlug: "la-ultima-evidencia",
    type: "short",
    typeLabel: "Short",
    date,
    time: firstSlot ? "15:00" : "18:00",
    displayTime: firstSlot ? "3:00 p.m." : "6:00 p.m.",
    title: MYSTERY_SHORT_SEO_TITLES[entry.title] || entry.title,
    parentTopic: entry.title,
    monthLabel: monthFromDate(date),
    pillar: `${entry.pillar} · SEO Shorts`,
    agentId: MYSTERY_SHORTS_AGENT_ID,
    durationProfile: "shorts90",
    seoKeywords: seoKeywordsForMysteryTopic(entry.title, entry.pillar),
    derivativeAgentIds: [MYSTERY_LONG_AGENT_ID],
  };
}

const MYSTERY_TOPIC_ENTRIES = buildMysteryTopicEntries();
const MYSTERY_VIDEO_ROWS = MYSTERY_TOPIC_ENTRIES;
const MYSTERY_SHORT_ROWS = MYSTERY_TOPIC_ENTRIES;

export const EDITORIAL_CALENDAR_ITEMS = [
  ...SHORT_ROWS.flatMap(shortEvents),
  ...LONG_VIDEO_ROWS.map(longVideoEvent),
  ...MYSTERY_VIDEO_ROWS.map(mysteryLongVideoEvent),
  ...MYSTERY_SHORT_ROWS.map(mysteryShortEvent),
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
  const derivativeConfig = {
    [SHORTS_AGENT_ID]: {
      label: "Crear Short derivado",
      durationProfile: "shorts75",
    },
    [CAROUSEL_AGENT_ID]: {
      label: "Crear carrusel",
      durationProfile: "carousel8",
    },
    [LONG_AGENT_ID]: {
      label: "Crear largo relacionado",
      durationProfile: "long",
    },
    [MYSTERY_SHORTS_AGENT_ID]: {
      label: "Crear Short del caso",
      durationProfile: "shorts90",
    },
    [MYSTERY_LONG_AGENT_ID]: {
      label: "Crear expediente largo",
      durationProfile: "long",
    },
  };

  if (item.derivativeAgentIds?.length) {
    return item.derivativeAgentIds
      .map((agentId) => {
        const config = derivativeConfig[agentId];
        if (!config) return null;
        return {
          ...config,
          agentId,
        };
      })
      .filter(Boolean);
  }

  if (item.channelSlug === "la-ultima-evidencia") {
    return item.type === "long"
      ? [{ ...derivativeConfig[MYSTERY_SHORTS_AGENT_ID], agentId: MYSTERY_SHORTS_AGENT_ID }]
      : [{ ...derivativeConfig[MYSTERY_LONG_AGENT_ID], agentId: MYSTERY_LONG_AGENT_ID }];
  }

  if (item.type === "long") {
    return [
      { ...derivativeConfig[SHORTS_AGENT_ID], agentId: SHORTS_AGENT_ID },
      { ...derivativeConfig[CAROUSEL_AGENT_ID], agentId: CAROUSEL_AGENT_ID },
    ];
  }

  return [
    { ...derivativeConfig[LONG_AGENT_ID], agentId: LONG_AGENT_ID },
    { ...derivativeConfig[CAROUSEL_AGENT_ID], agentId: CAROUSEL_AGENT_ID },
  ];
}
