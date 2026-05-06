"use client";
import { computeViralityScore } from "@/lib/virality";

/**
 * ViralityPanel — Editorial Cinematic v2.
 *
 * cf-card sidebar con eyebrow ÍNDICE DE VIRALIDAD + conic-gradient ember
 * con score Fraunces italic + verdict label + 5 ScoreBar con cf-mono.
 *
 * Sin emojis estructurales (decisión: producto editorial).
 */
function ScoreBar({ label, value }) {
  const color =
    value >= 75 ? "var(--ok)" : value >= 50 ? "var(--warn)" : "var(--bad)";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}
    >
      <span
        style={{
          flex: 1,
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </span>
      <div
        style={{
          width: 70,
          height: 4,
          background: "var(--ink-2)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${value}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
            transition: "width var(--dur-base) var(--ease-out)",
          }}
        />
      </div>
      <span
        style={{
          font: "var(--t-mono-sm)",
          fontFamily: "var(--font-mono)",
          fontWeight: 600,
          color,
          width: 28,
          textAlign: "right",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function getVerdict(overall) {
  if (overall >= 80) return { label: "VIRAL", color: "var(--ok)" };
  if (overall >= 60) return { label: "BUENO", color: "var(--ok)" };
  if (overall >= 40) return { label: "MEJORABLE", color: "var(--warn)" };
  return { label: "REVISAR", color: "var(--bad)" };
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function countMatches(text, words) {
  const lower = (text || "").toLowerCase();
  return words.reduce((total, word) => total + (lower.match(new RegExp(`\\b${word}\\b`, "g")) || []).length, 0);
}

function computeWellnessScore(text) {
  const clean = String(text || "");
  if (!clean.trim()) return null;

  const words = clean.split(/\s+/).filter(Boolean);
  const paragraphs = clean.split(/\n\s*\n+/).filter((p) => p.trim());
  const sentences = clean.split(/[.!?…]+/).filter((s) => s.trim());
  const calmTerms = countMatches(clean, [
    "calma",
    "calmar",
    "tranquilo",
    "tranquila",
    "tranquilidad",
    "respira",
    "respiración",
    "respiracion",
    "descansa",
    "descanso",
    "duerme",
    "dormir",
    "suave",
    "seguro",
    "segura",
    "suelta",
    "soltar",
    "paz",
  ]);
  const affirmationTerms = countMatches(clean, [
    "puedes",
    "puedo",
    "confías",
    "confio",
    "confío",
    "confianza",
    "mereces",
    "merezco",
    "permito",
    "permites",
    "elijo",
    "eliges",
    "soy",
    "estoy",
    "aprendo",
    "reconozco",
  ]);
  const safetyTerms = countMatches(clean, [
    "seguro",
    "segura",
    "pausar",
    "detenerte",
    "abrir los ojos",
    "control",
    "libertad",
    "bienestar",
    "no es tratamiento",
  ]);
  const clinicalRisk = countMatches(clean, ["cura", "curar", "diagnóstico", "diagnostico", "trauma"]);
  const ellipses = (clean.match(/\.{3}|…/g) || []).length;
  const avgSentenceWords = words.length / Math.max(1, sentences.length);
  const paragraphCount = Math.max(1, paragraphs.length);
  const pauseDensity = ellipses / Math.max(1, words.length / 100);

  const calm = clampScore(50 + calmTerms * 5 + Math.min(ellipses, 28) * 1.6 - clinicalRisk * 14);
  const clarity = clampScore(
    88 - Math.abs(avgSentenceWords - 18) * 1.2 + (words.length >= 700 ? 8 : 0) - clinicalRisk * 10,
  );
  const depth = clampScore(48 + affirmationTerms * 3.5 + Math.min(paragraphCount, 12) * 2);
  const rhythm = clampScore(58 + Math.min(pauseDensity, 4) * 9 + (avgSentenceWords >= 10 && avgSentenceWords <= 28 ? 18 : 0));
  const safety = clampScore(72 + safetyTerms * 7 - clinicalRisk * 20);
  const overall = clampScore((calm + clarity + depth + rhythm + safety) / 5);

  return { overall, calm, clarity, depth, rhythm, safety };
}

function getWellnessVerdict(overall) {
  if (overall >= 82) return { label: "PROFUNDO", color: "var(--ok)" };
  if (overall >= 65) return { label: "SERENO", color: "var(--ok)" };
  if (overall >= 45) return { label: "AJUSTAR", color: "var(--warn)" };
  return { label: "REVISAR", color: "var(--bad)" };
}

export default function ViralityPanel({ text, format }) {
  const isWellness = ["autohipnosis", "meditacion_larga"].includes(format);
  const isLongMeditation = format === "meditacion_larga";
  const score = isWellness
    ? computeWellnessScore(text)
    : computeViralityScore(text);
  if (!score) return null;

  const verdict = isWellness
    ? getWellnessVerdict(score.overall)
    : getVerdict(score.overall);
  const conicDeg = score.overall * 3.6;

  return (
    <div className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          marginBottom: 14,
        }}
      >
        {isWellness
          ? isLongMeditation
            ? "ÍNDICE DE DESCANSO"
            : "ÍNDICE DE CALMA"
          : "ÍNDICE DE VIRALIDAD"}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          marginBottom: "var(--s-5)",
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            background: `conic-gradient(var(--ember) ${conicDeg}deg, var(--ink-3) 0deg)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 12px rgba(224, 83, 61, 0.35)",
          }}
        >
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: "50%",
              background: "var(--ink-1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-display)",
              fontStyle: "italic",
              fontWeight: 800,
              fontSize: 20,
              color: "var(--paper)",
              letterSpacing: "-0.02em",
            }}
          >
            {score.overall}
          </div>
        </div>
        <div>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: verdict.color,
              fontWeight: 700,
              letterSpacing: "0.18em",
            }}
          >
            {verdict.label}
          </div>
          <div
            style={{
              font: "var(--t-caption)",
              color: "var(--paper-dim)",
              marginTop: 2,
            }}
          >
            {isWellness
              ? isLongMeditation
                ? "sesión larga"
                : "sesión guiada"
              : `${score.hooks} hook${score.hooks === 1 ? "" : "s"} detectado${score.hooks === 1 ? "" : "s"}`}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {isWellness ? (
          <>
            <ScoreBar label="Calma" value={score.calm} />
            <ScoreBar label="Claridad" value={score.clarity} />
            <ScoreBar label={isLongMeditation ? "Afirmaciones" : "Profundidad"} value={score.depth} />
            <ScoreBar label="Ritmo" value={score.rhythm} />
            <ScoreBar label="Seguridad" value={score.safety} />
          </>
        ) : (
          <>
            <ScoreBar label="Hooks" value={score.hookScore} />
            <ScoreBar label="Emoción" value={score.emotionScore} />
            <ScoreBar label="Ritmo" value={score.pacingScore} />
            <ScoreBar label="Estructura" value={score.structureScore} />
            <ScoreBar label="Retención" value={score.retentionScore} />
          </>
        )}
      </div>
    </div>
  );
}
