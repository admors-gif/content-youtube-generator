"use client";
import { useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import {
  collection,
  addDoc,
  serverTimestamp,
  doc,
  updateDoc,
  increment,
} from "firebase/firestore";
import { useRouter } from "next/navigation";
import { SYSTEM_AGENTS } from "@/lib/agents";
import Icon from "@/components/Icon";
import { getAgentColor, getMonogram } from "@/lib/agentVisual";

/**
 * Wizard Nuevo Documental — Editorial Cinematic v2.
 *
 * Preserva 100% la lógica del legacy:
 *   - state (step / selectedAgent / topic / creating / previewAgent /
 *     ideaInput / recommendations / recommending / recommendError)
 *   - fetchRecommendations() → POST /recommend-agent
 *   - recommendationMap (rank por agentId)
 *   - creditsLeft
 *   - handleCreate() → addDoc + decrement crédito + webhook n8n + redirect
 *
 * Aplica visual del kit:
 *   - Header: back + eyebrow ember PASO N DE 2 + display Fraunces italic
 *   - Step 1: recommender card + filter strip + agent grid 280px + sticky CTA
 *   - Step 2: card recap + textarea con contador + warn ember + back / crear
 *
 * OMITIDO (decisión confirmada): selector de duración Short/Mid/Long.
 * Mantener 1 crédito = 1 video. No romper backend.
 */

const TIER_FILTERS = [
  { id: "all",     label: "Todos" },
  { id: "starter", label: "Starter" },
  { id: "creator", label: "Creator" },
];

/* ── AgentCard ──────────────────────────────────────────────────────────── */

function AgentCard({ agent, selected, onSelect, recommendation }) {
  const color = agent.color || "#E0533D";
  const mono = getMonogram(agent.agentId);
  const isRec = !!recommendation;

  return (
    <button
      onClick={onSelect}
      style={{
        all: "unset",
        cursor: "pointer",
        display: "block",
        background: "var(--ink-1)",
        border: `1px solid ${selected ? color : "var(--rule-1)"}`,
        borderRadius: "var(--r-3)",
        padding: "var(--s-5)",
        position: "relative",
        overflow: "hidden",
        transition:
          "border-color var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out)",
        boxShadow: selected
          ? `0 0 0 4px ${color}33`
          : isRec
            ? `0 0 0 1px ${color}55`
            : "var(--shadow-1)",
        width: "100%",
        boxSizing: "border-box",
      }}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.borderColor = "var(--rule-2)";
      }}
      onMouseLeave={(e) => {
        if (!selected)
          e.currentTarget.style.borderColor = isRec
            ? `${color}55`
            : "var(--rule-1)";
      }}
    >
      {/* Top rule del color del agente */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: color,
        }}
      />

      {/* Badge de rank si está recomendado */}
      {isRec && (
        <span
          className="cf-badge"
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            background: "var(--ember-tint)",
            color: "var(--ember)",
            border: "1px solid var(--ember)",
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            letterSpacing: "0.08em",
            zIndex: 1,
          }}
          title={recommendation.reason || "Recomendado para tu idea"}
        >
          {String(recommendation.rank).padStart(2, "0")}
        </span>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 14,
          marginTop: 8,
        }}
      >
        {/* Tile monograma */}
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: "var(--r-2)",
            background: `${color}22`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color,
            fontFamily: "var(--font-display)",
            fontStyle: "italic",
            fontWeight: 800,
            fontSize: 22,
            lineHeight: 1,
            letterSpacing: "-0.02em",
          }}
        >
          {mono}
        </div>
        <span
          className={`cf-badge cf-badge--${agent.tier}`}
          style={{ marginRight: isRec ? 56 : 0 }}
        >
          {agent.tier?.toUpperCase()}
        </span>
      </div>

      <div
        style={{
          font: "var(--t-h3)",
          fontWeight: 600,
          color: "var(--paper)",
          marginBottom: 6,
          fontSize: 17,
        }}
      >
        {agent.name}
      </div>
      <div
        style={{
          font: "var(--t-caption)",
          color: "var(--paper-dim)",
          lineHeight: 1.5,
          marginBottom: isRec && recommendation.reason ? 10 : 0,
        }}
      >
        {agent.description}
      </div>

      {isRec && recommendation.reason && (
        <div
          style={{
            font: "var(--t-caption)",
            color: "var(--ember)",
            fontStyle: "italic",
            padding: "8px 10px",
            background: "var(--ember-tint)",
            borderRadius: "var(--r-1)",
            borderLeft: `2px solid var(--ember)`,
            lineHeight: 1.45,
          }}
        >
          {recommendation.reason}
        </div>
      )}
    </button>
  );
}

/* ── NewProjectPage ─────────────────────────────────────────────────────── */

export default function NewProjectPage() {
  const { user, profile } = useAuth();
  const router = useRouter();

  /* PRESERVADO: state legacy (previewAgent se eliminó porque el kit
   * incorpora los exampleTopics directamente como chips en step 2;
   * el resto de la lógica queda intacta). */
  const [step, setStep] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [topic, setTopic] = useState("");
  const [creating, setCreating] = useState(false);

  const [ideaInput, setIdeaInput] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [recommending, setRecommending] = useState(false);
  const [recommendError, setRecommendError] = useState(null);

  /* Filtro de tier (visual del kit, no estaba en legacy pero coexiste) */
  const [tierFilter, setTierFilter] = useState("all");

  /* PRESERVADO: fetchRecommendations */
  const fetchRecommendations = async () => {
    const idea = ideaInput.trim();
    if (idea.length < 5) {
      setRecommendError("Escribe al menos unas palabras de tu idea");
      return;
    }
    setRecommending(true);
    setRecommendError(null);
    setRecommendations([]);
    const apiBase =
      process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
    try {
      const res = await fetch(`${apiBase}/recommend-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: idea }),
      });
      const data = await res.json();
      if (data.recommendations?.length) {
        setRecommendations(data.recommendations);
        if (!topic) setTopic(idea);
      } else {
        setRecommendError(data.error || "No se pudo sugerir, elige manualmente");
      }
    } catch {
      setRecommendError("Error de conexión, elige manualmente");
    } finally {
      setRecommending(false);
    }
  };

  /* PRESERVADO: mapa de recomendaciones por agentId */
  const recommendationMap = recommendations.reduce((acc, r, i) => {
    acc[r.agent_id] = { rank: i + 1, ...r };
    return acc;
  }, {});

  /* PRESERVADO: créditos */
  const creditsLeft =
    Math.max(
      0,
      (profile?.credits?.included || 0) - (profile?.credits?.used || 0),
    ) + (profile?.credits?.extra || 0);

  /* PRESERVADO: handleCreate completo (addDoc + decrement + webhook n8n) */
  const handleCreate = async () => {
    if (!selectedAgent || !topic.trim()) return;
    if (creditsLeft <= 0) {
      alert(
        "No tienes créditos disponibles. Mejora tu plan o compra créditos extra.",
      );
      return;
    }
    setCreating(true);
    try {
      const docRef = await addDoc(collection(db, "projects"), {
        userId: user.uid,
        title: topic.trim(),
        agentId: selectedAgent.agentId,
        agentFile: selectedAgent.promptFile,
        status: "draft",
        progress: {
          currentStep: 0,
          totalSteps: 6,
          stepName: "Iniciando generación en la nube...",
          percent: 5,
        },
        script: {
          plain: "",
          tagged: "",
          wordCount: 0,
          estimatedMinutes: 0,
          approved: false,
        },
        scenes: [],
        voice: {
          model: "es-US-Neural2-A",
          gender: "female",
          speed: 1.0,
          pitch: 0,
        },
        output: {},
        seo: {},
        costs: {},
        createdAt: serverTimestamp(),
        completedAt: null,
      });

      // Descontar crédito
      await updateDoc(doc(db, "users", user.uid), {
        "credits.used": increment(1),
      });

      // Webhook n8n (background, no bloquea redirect)
      try {
        const webhookUrl = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL;
        if (webhookUrl) {
          fetch(webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              projectId: docRef.id,
              userId: user.uid,
              topic: topic.trim(),
              agentFile: selectedAgent.promptFile,
            }),
          }).catch((err) => console.error("Error contactando a n8n:", err));
        } else {
          console.warn("Falta NEXT_PUBLIC_N8N_WEBHOOK_URL en .env.local");
        }
      } catch (err) {
        console.error("Error al preparar el webhook:", err);
      }

      router.push(`/dashboard/project/${docRef.id}`);
    } catch (e) {
      alert("Error al crear proyecto: " + e.message);
    } finally {
      setCreating(false);
    }
  };

  /* Filtrado de agentes por tier */
  const filteredAgents = useMemo(
    () =>
      SYSTEM_AGENTS.filter(
        (a) => tierFilter === "all" || a.tier === tierFilter,
      ),
    [tierFilter],
  );

  /* Word/char count para textarea */
  const wordCount = topic.trim().split(/\s+/).filter(Boolean).length;
  const charCount = topic.length;

  return (
    <div>
      {/* Header */}
      <header className="cf-fade" style={{ marginBottom: "var(--s-7)" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 8,
          }}
        >
          <button
            onClick={() => router.push("/dashboard")}
            style={{
              all: "unset",
              cursor: "pointer",
              color: "var(--paper-mute)",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              font: "var(--t-mono-sm)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              transition: "color var(--dur-base) var(--ease-out)",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--paper)")}
            onMouseLeave={(e) =>
              (e.currentTarget.style.color = "var(--paper-mute)")
            }
          >
            <Icon name="arrowLeft" size={14} /> VOLVER
          </button>
          <div
            style={{
              font: "var(--t-mono-sm)",
              color: "var(--ember)",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            · PASO {step} DE 2
          </div>
        </div>
        <h1
          className="cf-display"
          style={{
            margin: 0,
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            lineHeight: 0.95,
          }}
        >
          {step === 1 ? (
            <>
              Elige un{" "}
              <em style={{ color: "var(--ember)", fontStyle: "italic" }}>
                agente
              </em>
            </>
          ) : (
            <>
              Cuéntanos la{" "}
              <em style={{ color: "var(--ember)", fontStyle: "italic" }}>
                historia
              </em>
            </>
          )}
        </h1>
        <p
          style={{
            color: "var(--paper-dim)",
            margin: "10px 0 0",
            maxWidth: 620,
            lineHeight: 1.5,
          }}
        >
          {step === 1
            ? "Cada agente está entrenado en un género — investigación, voz narrativa, ritmo y archivo."
            : "Más detalle = mejor guión. Mencionar fechas, lugares y personajes mejora la cita de fuentes."}
        </p>
      </header>

      {/* STEP 1 — Agent Selection */}
      {step === 1 && (
        <>
          {/* Recommender card */}
          <div
            className="cf-card cf-fade cf-fade--1"
            style={{
              padding: "var(--s-5)",
              marginBottom: "var(--s-6)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 6,
              }}
            >
              <Icon name="sparkles" size={16} style={{ color: "var(--ember)" }} />
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--ember)",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                }}
              >
                RECOMENDADOR
              </div>
            </div>
            <div
              style={{
                fontWeight: 600,
                marginBottom: 6,
                color: "var(--paper)",
              }}
            >
              ¿No sabes cuál elegir? Cuéntanos tu idea
            </div>
            <div
              style={{
                font: "var(--t-caption)",
                color: "var(--paper-dim)",
                marginBottom: 14,
              }}
            >
              Te marcamos los 3 agentes que mejor encajan. Es opcional —
              también puedes elegir manualmente abajo.
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <input
                className="cf-input"
                placeholder='Ej: "La caída del Imperio Romano" o "Por qué los gatos ronronean"'
                value={ideaInput}
                onChange={(e) => setIdeaInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !recommending) fetchRecommendations();
                }}
                style={{ flex: "1 1 280px" }}
              />
              <button
                className="cf-btn cf-btn--primary"
                onClick={fetchRecommendations}
                disabled={recommending || ideaInput.trim().length < 5}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  whiteSpace: "nowrap",
                }}
              >
                {recommending ? (
                  <>
                    <Icon name="refresh" size={16} />
                    Pensando…
                  </>
                ) : (
                  <>
                    <Icon name="sparkles" size={16} />
                    Sugerir agentes
                  </>
                )}
              </button>
            </div>
            {recommendError && (
              <div
                style={{
                  marginTop: 10,
                  font: "var(--t-caption)",
                  color: "var(--bad)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Icon name="alert" size={14} /> {recommendError}
              </div>
            )}
            {recommendations.length > 0 && (
              <div
                style={{
                  marginTop: 12,
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  letterSpacing: "0.06em",
                }}
              >
                {recommendations.length} AGENTES MARCADOS · CLICK PARA
                SELECCIONAR
              </div>
            )}
          </div>

          {/* Filter strip */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: "var(--s-5)",
              flexWrap: "wrap",
            }}
          >
            {TIER_FILTERS.map((f) => {
              const active = tierFilter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => setTierFilter(f.id)}
                  className={`cf-btn cf-btn--sm ${active ? "cf-btn--secondary" : "cf-btn--ghost"}`}
                  style={
                    active
                      ? { borderColor: "var(--ember)", color: "var(--ember)" }
                      : undefined
                  }
                >
                  {f.label}
                </button>
              );
            })}
            <div style={{ flex: 1 }} />
            <div
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-mute)",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
              }}
            >
              {filteredAgents.length} AGENTES
            </div>
          </div>

          {/* Agent grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "var(--s-4)",
              marginBottom: "var(--s-7)",
            }}
          >
            {filteredAgents.map((agent, i) => (
              <div
                key={agent.agentId}
                className={`cf-fade cf-fade--${(i % 4) + 1}`}
              >
                <AgentCard
                  agent={agent}
                  selected={selectedAgent?.agentId === agent.agentId}
                  recommendation={recommendationMap[agent.agentId]}
                  onSelect={() => setSelectedAgent(agent)}
                />
              </div>
            ))}
          </div>

          {/* Sticky CTA */}
          <div
            style={{
              position: "sticky",
              bottom: 0,
              background:
                "linear-gradient(180deg, transparent, var(--ink-0) 40%)",
              padding: "var(--s-7) 0 var(--s-5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 12,
              flexWrap: "wrap",
              zIndex: 4,
            }}
          >
            {selectedAgent && (
              <div
                style={{
                  marginRight: "auto",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: "var(--r-2)",
                    background: `${getAgentColor(selectedAgent.agentId)}22`,
                    color: getAgentColor(selectedAgent.agentId),
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: "var(--font-display)",
                    fontStyle: "italic",
                    fontWeight: 800,
                    fontSize: 16,
                    lineHeight: 1,
                  }}
                >
                  {getMonogram(selectedAgent.agentId)}
                </div>
                <div>
                  <div
                    style={{
                      font: "var(--t-mono-sm)",
                      color: "var(--paper-mute)",
                      letterSpacing: "0.18em",
                      textTransform: "uppercase",
                    }}
                  >
                    SELECCIONADO
                  </div>
                  <div
                    style={{
                      color: "var(--paper)",
                      fontWeight: 600,
                    }}
                  >
                    {selectedAgent.name}
                  </div>
                </div>
              </div>
            )}
            <button
              className="cf-btn cf-btn--primary"
              disabled={!selectedAgent}
              onClick={() => setStep(2)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              Siguiente <Icon name="arrowRight" size={16} />
            </button>
          </div>
        </>
      )}

      {/* STEP 2 — Topic input */}
      {step === 2 && selectedAgent && (
        <div style={{ maxWidth: 720 }} className="cf-fade">
          {/* Card recap + textarea + warn */}
          <div
            className="cf-card"
            style={{
              padding: "var(--s-6)",
              marginBottom: "var(--s-5)",
            }}
          >
            {/* Recap header */}
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
                  width: 48,
                  height: 48,
                  borderRadius: "var(--r-2)",
                  background: `${getAgentColor(selectedAgent.agentId)}22`,
                  color: getAgentColor(selectedAgent.agentId),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontWeight: 800,
                  fontSize: 20,
                  lineHeight: 1,
                }}
              >
                {getMonogram(selectedAgent.agentId)}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    font: "var(--t-mono-sm)",
                    color: "var(--paper-mute)",
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                  }}
                >
                  AGENTE
                </div>
                <div
                  style={{
                    font: "var(--t-h3)",
                    color: "var(--paper)",
                    fontWeight: 600,
                  }}
                >
                  {selectedAgent.name}
                </div>
              </div>
              <button
                className="cf-btn cf-btn--ghost cf-btn--sm"
                onClick={() => setStep(1)}
              >
                Cambiar
              </button>
            </div>

            {/* Textarea */}
            <label style={{ display: "block", marginBottom: "var(--s-5)" }}>
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  marginBottom: 8,
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                }}
              >
                TEMA · OBLIGATORIO
              </div>
              <textarea
                className="cf-input"
                rows={4}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                autoFocus
                placeholder={`Ej: ${selectedAgent.exampleTopics?.[0] || "Tu idea aquí"}`}
                style={{
                  fontFamily: "var(--font-display)",
                  fontStyle: "italic",
                  fontSize: 18,
                  lineHeight: 1.45,
                  resize: "vertical",
                  minHeight: 100,
                }}
              />
              <div
                style={{
                  font: "var(--t-mono-sm)",
                  color: "var(--paper-mute)",
                  marginTop: 6,
                  display: "flex",
                  justifyContent: "space-between",
                  letterSpacing: "0.06em",
                }}
              >
                <span>
                  {wordCount} palabra{wordCount === 1 ? "" : "s"}
                </span>
                <span>{charCount} caracteres</span>
              </div>
            </label>

            {/* Suggestions chips */}
            {selectedAgent.exampleTopics?.length > 0 && (
              <div style={{ marginBottom: "var(--s-5)" }}>
                <div
                  style={{
                    font: "var(--t-mono-sm)",
                    color: "var(--paper-mute)",
                    marginBottom: 10,
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                  }}
                >
                  IDEAS POPULARES
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {selectedAgent.exampleTopics.map((t) => (
                    <button
                      key={t}
                      className="cf-btn cf-btn--ghost cf-btn--sm"
                      onClick={() => setTopic(t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Cost warn */}
            <div
              style={{
                padding: "12px 14px",
                background: "var(--ember-tint)",
                border: "1px solid var(--ember)",
                borderRadius: "var(--r-2)",
                display: "flex",
                alignItems: "center",
                gap: 12,
                color: "var(--paper)",
              }}
            >
              <Icon name="coins" size={18} style={{ color: "var(--ember)" }} />
              <div style={{ flex: 1, fontSize: 14, lineHeight: 1.4 }}>
                Este vídeo costará{" "}
                <strong style={{ color: "var(--ember)" }}>1 crédito</strong>.
                Tienes{" "}
                <strong style={{ color: "var(--paper)" }}>
                  {creditsLeft} disponible{creditsLeft === 1 ? "" : "s"}
                </strong>
                .
              </div>
            </div>
          </div>

          {/* Botones inferiores */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <button
              className="cf-btn cf-btn--ghost"
              onClick={() => setStep(1)}
              style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
            >
              <Icon name="arrowLeft" size={16} /> Atrás
            </button>
            <button
              className="cf-btn cf-btn--primary"
              disabled={!topic.trim() || creating || creditsLeft <= 0}
              onClick={handleCreate}
              style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
            >
              {creating ? (
                <>
                  <Icon name="refresh" size={16} />
                  Creando…
                </>
              ) : (
                <>
                  Crear documental <Icon name="arrowRight" size={16} />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
