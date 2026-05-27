/**
 * Virality Score Engine.
 *
 * Calcula 5 sub-scores (Hooks / Emoción / Ritmo / Estructura / Retención)
 * + un overall ponderado, en base al texto crudo del guión.
 *
 * Heurística diseñada para narración cinematográfica en español. No es ML,
 * son reglas léxicas calibradas. Útil como guidance para el creador, no
 * como predictor cuantitativo de viralidad real.
 *
 * Devuelve null si el texto es muy corto (< 50 chars). Eso evita scores
 * ruidosos para guiones recién empezados o vacíos.
 */
export function computeViralityScore(text) {
  if (!text || text.length < 50) return null;
  const words = text.split(/\s+/);
  const wordCount = words.length;
  const sentences = text.split(/[.!?]+/).filter(Boolean);

  // 1. Hooks (questions, exclamations, power phrases)
  const hooks = (text.match(/\?/g) || []).length;
  const exclamations = (text.match(/!/g) || []).length;
  const powerPhrases = [
    "imagina", "secreto", "verdad", "nadie te dice", "increíble",
    "impactante", "descubre", "revelado", "sorprendente", "poderoso",
    "extraordinario", "fascinante",
  ];
  const powerCount = powerPhrases.reduce(
    (c, p) => c + (text.toLowerCase().match(new RegExp(p, "gi")) || []).length,
    0,
  );
  const hookScore = Math.min(
    100,
    hooks * 8 + exclamations * 3 + powerCount * 12,
  );

  // 2. Emotional triggers
  const emotionalWords = [
    "miedo", "amor", "muerte", "odio", "pasión", "poder", "dolor", "sangre",
    "traición", "venganza", "gloria", "destino", "guerra", "locura",
    "esperanza", "terror", "misterio", "oscuro", "prohibido", "peligro",
  ];
  const emotionalCount = emotionalWords.reduce(
    (c, w) =>
      c + (text.toLowerCase().match(new RegExp(`\\b${w}`, "gi")) || []).length,
    0,
  );
  const emotionScore = Math.min(100, emotionalCount * 10);

  // 3. Pacing (avg words per sentence — ideal 12-18)
  const avgWordsPerSentence = wordCount / Math.max(sentences.length, 1);
  const pacingScore =
    avgWordsPerSentence >= 10 && avgWordsPerSentence <= 20
      ? 90
      : avgWordsPerSentence < 10
        ? 65
        : 55;

  // 4. SEO / Structure
  const hasNumbers = /\d/.test(text);
  const hasLists = text.includes("1.") || text.includes("•");
  const paragraphs = text.split(/\n\n+/).length;
  const structureScore = Math.min(
    100,
    (hasNumbers ? 20 : 0) +
      (hasLists ? 15 : 0) +
      Math.min(paragraphs * 5, 40) +
      (wordCount > 800 ? 25 : wordCount > 400 ? 15 : 5),
  );

  // 5. Retention (narrative arcs, cliffhangers)
  const cliffhangers = [
    "pero", "sin embargo", "lo que no sabían", "entonces", "de pronto",
    "hasta que", "lo peor", "lo mejor",
  ];
  const cliffCount = cliffhangers.reduce(
    (c, p) => c + (text.toLowerCase().match(new RegExp(p, "gi")) || []).length,
    0,
  );
  const retentionScore = Math.min(
    100,
    cliffCount * 8 + (wordCount > 1000 ? 20 : 10),
  );

  const overall = Math.round(
    hookScore * 0.25 +
      emotionScore * 0.2 +
      pacingScore * 0.2 +
      structureScore * 0.15 +
      retentionScore * 0.2,
  );

  return {
    overall,
    hookScore: Math.round(hookScore),
    hooks,
    emotionScore: Math.round(emotionScore),
    pacingScore: Math.round(pacingScore),
    structureScore: Math.round(structureScore),
    retentionScore: Math.round(retentionScore),
    avgWordsPerSentence: Math.round(avgWordsPerSentence),
  };
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function countMatches(text, words) {
  const lower = (text || "").toLowerCase();
  return words.reduce(
    (total, word) =>
      total + (lower.match(new RegExp(`\\b${word}\\b`, "g")) || []).length,
    0,
  );
}

/**
 * Vertical Short Score Engine.
 *
 * Separado del score de YouTube/documental: aquí un guion corto no debe ser
 * castigado por no tener listas, capítulos largos o estructura SEO. Mide lo
 * que importa para una pieza vertical: hook inmediato, tensión emocional,
 * ritmo conversacional, claridad de beats y cierre social.
 */
export function computeVerticalShortScore(text, format = "") {
  if (!text || text.length < 50) return null;

  const clean = String(text || "").trim();
  const lower = clean.toLowerCase();
  const words = clean.split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  const lines = clean.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const sentences = clean.split(/[.!?…]+/).filter((sentence) => sentence.trim());
  const firstLine = lines[0] || "";
  const firstLineWords = firstLine.split(/\s+/).filter(Boolean).length;
  const avgSentenceWords = wordCount / Math.max(sentences.length, 1);
  const isPodcast = format === "tiktok_podcast" || format === "youtube_shorts_podcast";

  const hookTerms = [
    "no es amor",
    "apego",
    "ansiedad",
    "obsesión",
    "obsesion",
    "nadie te dice",
    "si te pasa esto",
    "la verdad",
    "deja de",
    "por qué",
    "porque",
    "extrañas",
    "confundes",
    "te eliges",
  ];
  const emotionalTerms = [
    "amor",
    "apego",
    "ansiedad",
    "abandono",
    "rechazo",
    "herida",
    "duelo",
    "obsesión",
    "obsesion",
    "dependencia",
    "autoestima",
    "soltar",
    "ghosting",
    "límite",
    "limite",
    "dolor",
    "paz",
  ];
  const retentionTerms = [
    "pero",
    "sin embargo",
    "a veces",
    "lo que pasa",
    "la pregunta",
    "el problema",
    "no extrañas",
    "no estás",
    "no estas",
    "en realidad",
    "hasta que",
    "porque",
  ];
  const ctaTerms = [
    "comenta",
    "guarda",
    "sígueme",
    "sigueme",
    "suscríbete",
    "suscribete",
    "canal",
    "quédate",
    "quedate",
    "parte 2",
    "episodio completo",
  ];
  const speakerTurns = (clean.match(/^[A-ZÁÉÍÓÚÑ]{3,12}:/gm) || []).length;
  const questionCount = (clean.match(/\?/g) || []).length;
  const hookTermCount = countMatches(clean, hookTerms);
  const emotionCount = countMatches(clean, emotionalTerms);
  const retentionCount = countMatches(clean, retentionTerms);
  const ctaCount = countMatches(clean, ctaTerms);

  const idealMin = format === "tiktok_documentary" ? 120 : 95;
  const idealMax = format === "tiktok_documentary" ? 500 : 260;
  const lengthFit =
    wordCount >= idealMin && wordCount <= idealMax
      ? 18
      : wordCount < idealMin
        ? Math.max(0, 18 - (idealMin - wordCount) / 6)
        : Math.max(4, 18 - (wordCount - idealMax) / 18);

  const hookScore = clampScore(
    46 +
      (firstLineWords >= 4 && firstLineWords <= 18 ? 18 : 6) +
      Math.min(hookTermCount * 7, 22) +
      Math.min(questionCount * 5, 12),
  );
  const emotionScore = clampScore(42 + Math.min(emotionCount * 6, 46) + (lower.includes("esto no es amor") ? 8 : 0));
  const rhythmScore = clampScore(
    44 +
      (avgSentenceWords >= 5 && avgSentenceWords <= 16 ? 24 : 10) +
      Math.min(lines.length * 2, 16) +
      (isPodcast && speakerTurns >= 4 ? 14 : 0),
  );
  const structureScore = clampScore(
    36 +
      lengthFit +
      (lines.length >= 5 ? 14 : lines.length * 2) +
      Math.min(speakerTurns * 4, isPodcast ? 22 : 10) +
      Math.min(ctaCount * 8, 16),
  );
  const retentionScore = clampScore(
    40 +
      Math.min(retentionCount * 7, 35) +
      Math.min(questionCount * 4, 12) +
      Math.min(ctaCount * 8, 16) +
      (wordCount <= idealMax + 80 ? 8 : 0),
  );

  const overall = clampScore(
    hookScore * 0.24 +
      emotionScore * 0.22 +
      rhythmScore * 0.18 +
      structureScore * 0.18 +
      retentionScore * 0.18,
  );

  return {
    overall,
    hookScore,
    hooks: hookTermCount + questionCount,
    emotionScore,
    pacingScore: rhythmScore,
    structureScore,
    retentionScore,
    avgWordsPerSentence: Math.round(avgSentenceWords),
    wordCount,
  };
}

export function computeTikTokScore(text, format = "") {
  return computeVerticalShortScore(text, format);
}

/**
 * Carousel Score Engine.
 *
 * Optimizado para carruseles de Instagram: no premia duracion ni SEO, premia
 * portada con golpe, retencion de swipe, claridad, potencial de guardado y CTA.
 */
export function computeCarouselScore(text) {
  if (!text || text.length < 50) return null;

  const clean = String(text || "").trim();
  const lower = clean.toLowerCase();
  const lines = clean.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const words = clean.split(/\s+/).filter(Boolean);
  const slideMarkers = (clean.match(/slide\s*\d|^\d{1,2}[).:-]/gim) || []).length;
  const questionCount = (clean.match(/\?/g) || []).length;
  const imperativeCount = countMatches(clean, [
    "guarda",
    "comparte",
    "busca",
    "suscribete",
    "suscríbete",
    "manda",
    "envia",
    "envía",
    "lee",
    "mira",
  ]);
  const hookTerms = countMatches(clean, [
    "no es amor",
    "si te pasa esto",
    "nadie te dice",
    "la verdad",
    "deja de",
    "confundes",
    "ansiedad",
    "apego",
    "obsesion",
    "obsesión",
    "rechazo",
  ]);
  const emotionTerms = countMatches(clean, [
    "amor",
    "miedo",
    "dolor",
    "herida",
    "abandono",
    "rechazo",
    "ansiedad",
    "culpa",
    "apego",
    "soltar",
    "suficiente",
    "intensidad",
  ]);
  const swipeTerms = countMatches(clean, [
    "pero",
    "entonces",
    "porque",
    "la trampa",
    "el giro",
    "lo incomodo",
    "en realidad",
    "hasta que",
    "no necesitas",
  ]);
  const saveTerms = countMatches(clean, [
    "guarda",
    "recuerda",
    "frase",
    "cuando vuelvas",
    "necesitas",
    "si esto",
    "mandaselo",
    "mándaselo",
  ]);
  const ctaTerms = countMatches(clean, [
    "youtube",
    "canal",
    "episodio completo",
    "suscribete",
    "suscríbete",
    "busca esto no es amor",
  ]);

  const firstLineWords = (lines[0] || "").split(/\s+/).filter(Boolean).length;
  const avgWordsPerLine = words.length / Math.max(lines.length, 1);
  const hasEightSlides = slideMarkers >= 6 || lines.length >= 8;

  const hookScore = clampScore(48 + hookTerms * 7 + questionCount * 5 + (firstLineWords >= 4 && firstLineWords <= 14 ? 22 : 6));
  const swipeRetention = clampScore(46 + swipeTerms * 7 + (hasEightSlides ? 22 : 8) + (avgWordsPerLine <= 28 ? 12 : 0));
  const emotionScore = clampScore(42 + emotionTerms * 5 + (lower.includes("esto no es amor") ? 8 : 0));
  const clarityScore = clampScore(54 + (avgWordsPerLine >= 5 && avgWordsPerLine <= 28 ? 26 : 8) + (hasEightSlides ? 10 : 0));
  const saveShareScore = clampScore(44 + saveTerms * 9 + imperativeCount * 5 + (questionCount >= 1 ? 6 : 0));
  const ctaScore = clampScore(45 + ctaTerms * 11 + imperativeCount * 5);
  const overall = clampScore(
    hookScore * 0.2 +
      swipeRetention * 0.2 +
      emotionScore * 0.18 +
      clarityScore * 0.17 +
      saveShareScore * 0.15 +
      ctaScore * 0.1,
  );

  return {
    overall,
    hookScore,
    hooks: hookTerms + questionCount,
    emotionScore,
    pacingScore: swipeRetention,
    structureScore: clarityScore,
    retentionScore: saveShareScore,
    ctaScore,
    wordCount: words.length,
  };
}
