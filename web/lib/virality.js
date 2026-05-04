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
