"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { SYSTEM_AGENTS } from "@/lib/agents";
import Icon from "@/components/Icon";
import { getAgentColor, getMonogram } from "@/lib/agentVisual";
import { authHeaders, getApiBase } from "@/lib/apiClient";
import { getCreditCounts } from "@/lib/credits";
import { isAdminUser } from "@/lib/admin";

/**
 * Wizard Nuevo Documental — Editorial Cinematic v2.
 *
 * Preserva 100% la lógica del legacy:
 *   - state (step / selectedAgent / topic / creating / previewAgent /
 *     ideaInput / recommendations / recommending / recommendError)
 *   - fetchRecommendations() → POST /recommend-agent
 *   - recommendationMap (rank por agentId)
 *   - creditsLeft
 *   - handleCreate() → backend transaccional + redirect
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
  { id: "custom",  label: "Mis agentes" },
];

const TIKTOK_GENERATION_ENABLED =
  process.env.NEXT_PUBLIC_CONTENT_FACTORY_TIKTOK_GENERATION_ENABLED !== "false";
const CUSTOM_AGENTS_ENABLED =
  process.env.NEXT_PUBLIC_CONTENT_FACTORY_CUSTOM_AGENTS_ENABLED !== "false";

const PLATFORM_OPTIONS = [
  {
    id: "youtube",
    label: "YouTube",
    icon: "film",
    description: "Videos largos, podcasts, wellness y shorts derivados.",
  },
  ...(TIKTOK_GENERATION_ENABLED
    ? [
        {
          id: "tiktok",
          label: "TikTok",
          icon: "zap",
          description: "Piezas verticales nativas con hook, ritmo y caption propio.",
        },
      ]
    : []),
];

const WELLNESS_FORMATS = new Set([
  "autohipnosis",
  "meditacion_larga",
  "tiktok_autohypnosis",
  "tiktok_meditation",
]);

const PERSONALIZATION_LIMITS = {
  preferredName: 40,
  purpose: 500,
  anchorPhrase: 180,
};

const EMPTY_PERSONALIZATION = {
  preferredName: "",
  purpose: "",
  anchorPhrase: "",
};

function cleanPersonalizationText(value) {
  return value.replace(/\s+/g, " ").trim();
}

function buildPersonalizationPayload(personalization) {
  const payload = {
    preferredName: cleanPersonalizationText(personalization.preferredName),
    purpose: cleanPersonalizationText(personalization.purpose),
    anchorPhrase: cleanPersonalizationText(personalization.anchorPhrase),
  };
  return Object.values(payload).some(Boolean) ? payload : null;
}

/* ── AgentCard ──────────────────────────────────────────────────────────── */

function AgentCard({ agent, selected, onSelect, recommendation }) {
  const color = agent.color || "#E0533D";
  const mono = agent.monogram || getMonogram(agent.agentId);
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

function PersonalizationField({
  icon,
  label,
  helper,
  value,
  maxLength,
  rows = 1,
  placeholder,
  onChange,
}) {
  const InputComponent = rows > 1 ? "textarea" : "input";
  return (
    <label style={{ display: "block" }}>
      <div
        style={{
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          marginBottom: 8,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Icon name={icon} size={14} /> {label}
      </div>
      <InputComponent
        className="cf-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        rows={rows > 1 ? rows : undefined}
        placeholder={placeholder}
        style={{
          minHeight: rows > 1 ? 88 : undefined,
          resize: rows > 1 ? "vertical" : undefined,
        }}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          marginTop: 6,
          font: "var(--t-caption)",
          color: "var(--paper-dim)",
          lineHeight: 1.35,
        }}
      >
        <span>{helper}</span>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--paper-mute)",
          }}
        >
          {value.length}/{maxLength}
        </span>
      </div>
    </label>
  );
}

/* ── NewProjectPage ─────────────────────────────────────────────────────── */

export default function NewProjectPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const didApplyPrefill = useRef(false);
  const admin = isAdminUser(user, profile);

  /* PRESERVADO: state legacy (previewAgent se eliminó porque el kit
   * incorpora los exampleTopics directamente como chips en step 2;
   * el resto de la lógica queda intacta). */
  const [step, setStep] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [topic, setTopic] = useState("");
  const [prefillSource, setPrefillSource] = useState("");
  const [projectIntentId, setProjectIntentId] = useState("");
  const [projectIntent, setProjectIntent] = useState(null);
  const [creating, setCreating] = useState(false);

  const [ideaInput, setIdeaInput] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [recommending, setRecommending] = useState(false);
  const [recommendError, setRecommendError] = useState(null);
  const [requestingCredits, setRequestingCredits] = useState(false);
  const [creditRequestSent, setCreditRequestSent] = useState(false);

  /* Filtro de tier (visual del kit, no estaba en legacy pero coexiste) */
  const [platform, setPlatform] = useState("youtube");
  const [tierFilter, setTierFilter] = useState("all");
  const [durationProfile, setDurationProfile] = useState("60m");
  const [sourceGenre, setSourceGenre] = useState("psychology");
  const [personalization, setPersonalization] = useState(EMPTY_PERSONALIZATION);
  const [customAgents, setCustomAgents] = useState([]);
  const [customAgentsError, setCustomAgentsError] = useState("");

  const allAgents = useMemo(
    () => [...SYSTEM_AGENTS, ...customAgents],
    [customAgents],
  );

  useEffect(() => {
    if (!user || !admin || !CUSTOM_AGENTS_ENABLED) return;
    let cancelled = false;
    async function loadCustomAgents() {
      try {
        const res = await fetch(`${getApiBase()}/custom-agents?status=active`, {
          headers: await authHeaders(user),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron cargar tus agentes.");
        const agents = (data.agents || [])
          .map((item) => item.publicAgent || item)
          .filter((item) => item.agentId);
        if (!cancelled) setCustomAgents(agents);
      } catch (err) {
        if (!cancelled) setCustomAgentsError(err.message);
      }
    }
    loadCustomAgents();
    return () => {
      cancelled = true;
    };
  }, [user, admin]);

  useEffect(() => {
    if (didApplyPrefill.current) return;
    const searchParams = new URLSearchParams(window.location.search);
    const intentId = searchParams.get("intentId") || "";
    const prefillAgentId = searchParams.get("agentId") || "";
    const prefillTopic = searchParams.get("topic") || "";
    const prefillDurationProfile = searchParams.get("durationProfile") || "";
    const source = searchParams.get("from") || "";
    if (intentId) {
      if (!user) return;
      let cancelled = false;
      async function loadProjectIntent() {
        try {
          const res = await fetch(`${getApiBase()}/project-intents/${encodeURIComponent(intentId)}`, {
            headers: await authHeaders(user),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || data.error || "No se pudo cargar el intent de Inspiracion.");
          if (cancelled) return;
          const prefill = data.prefill || {};
          const agent = allAgents.find((item) => item.agentId === prefill.agentId);
          if (prefill.agentId && !agent) return;
          if (agent) {
            setPlatform(agent.platform || "youtube");
            setSelectedAgent(agent);
            const defaultProfile = agent.durationProfiles?.find((p) => p.id === (agent.platform === "tiktok" ? "90s" : "60m"))
              || agent.durationProfiles?.[0];
            if (defaultProfile) setDurationProfile(defaultProfile.id);
            if (agent.sourceGenres?.length) setSourceGenre(agent.sourceGenres[0].id);
          }
          const nextTopic = prefill.topic || prefill.visibleTitle || data.intent?.shortTopic || data.intent?.visibleTitle || "";
          if (nextTopic) {
            setTopic(nextTopic);
            setIdeaInput(nextTopic);
          }
          setProjectIntentId(intentId);
          setProjectIntent(data.intent || null);
          setPrefillSource("inspiration");
          if (agent && nextTopic) setStep(2);
          didApplyPrefill.current = true;
        } catch (err) {
          alert(err.message);
        }
      }
      loadProjectIntent();
      return () => {
        cancelled = true;
      };
    }
    if (!prefillAgentId && !prefillTopic) return;

    const agent = allAgents.find((item) => item.agentId === prefillAgentId);
    if (prefillAgentId && !agent) return;
    const timer = window.setTimeout(() => {
      if (agent) {
        setPlatform(agent.platform || "youtube");
        setSelectedAgent(agent);
        const defaultProfile = agent.durationProfiles?.find((p) => p.id === prefillDurationProfile)
          || agent.durationProfiles?.find((p) => p.id === (agent.platform === "tiktok" ? "90s" : "60m"))
          || agent.durationProfiles?.[0];
        if (defaultProfile) setDurationProfile(defaultProfile.id);
        if (agent.sourceGenres?.length) setSourceGenre(agent.sourceGenres[0].id);
      }
      if (prefillTopic) {
        setTopic(prefillTopic);
        setIdeaInput(prefillTopic);
      }
      if (source) setPrefillSource(source);
      if (agent && prefillTopic) setStep(2);
      didApplyPrefill.current = true;
    }, 0);
    return () => window.clearTimeout(timer);
  }, [allAgents, user]);

  const selectAgent = (agent) => {
    setSelectedAgent(agent);
    const defaultProfile = agent.durationProfiles?.find((p) => p.id === (agent.platform === "tiktok" ? "90s" : "60m"))
      || agent.durationProfiles?.[0];
    if (defaultProfile) setDurationProfile(defaultProfile.id);
    if (agent.sourceGenres?.length) setSourceGenre(agent.sourceGenres[0].id);
  };

  const selectPlatform = (nextPlatform) => {
    if (nextPlatform === "tiktok" && !TIKTOK_GENERATION_ENABLED) return;
    setPlatform(nextPlatform);
    setSelectedAgent(null);
    setRecommendations([]);
    setRecommendError(null);
    setDurationProfile(nextPlatform === "tiktok" ? "90s" : "60m");
  };

  const updatePersonalization = (field, value) => {
    setPersonalization((current) => ({
      ...current,
      [field]: value,
    }));
  };

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
    const apiBase = getApiBase();
    try {
      const res = await fetch(`${apiBase}/recommend-agent`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
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

  const { remaining: creditsLeft } = getCreditCounts(profile);
  const isWellnessSelected = WELLNESS_FORMATS.has(selectedAgent?.format);
  const personalizationPayload = isWellnessSelected
    ? buildPersonalizationPayload(personalization)
    : null;

  const handleRequestCredits = async () => {
    setRequestingCredits(true);
    try {
      const res = await fetch(`${getApiBase()}/credits/request`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo enviar la solicitud.");
      setCreditRequestSent(true);
    } catch (e) {
      alert(e.message);
    } finally {
      setRequestingCredits(false);
    }
  };

  /* Crear proyecto: el backend valida saldo, descuenta crédito y dispara guion */
  const handleCreate = async () => {
    if (!selectedAgent || !topic.trim()) return;
    if (creditsLeft <= 0) {
      alert(
        "Tu cuenta aún no tiene créditos activos. Solicita activación antes de producir.",
      );
      return;
    }
    if (prefillSource) {
      const confirmed = window.confirm(
        "Este paso sí consumirá 1 crédito y creará el proyecto. ¿Quieres continuar?",
      );
      if (!confirmed) return;
    }
    setCreating(true);
    try {
      const res = await fetch(`${getApiBase()}/projects/create`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
        body: JSON.stringify({
          title: topic.trim(),
          agentId: selectedAgent.agentId,
          agentFile: selectedAgent.promptFile,
          ...(selectedAgent.agentSource === "custom" || selectedAgent.customAgentId
            ? { customAgentId: selectedAgent.customAgentId || selectedAgent.agentId }
            : {}),
          platform,
          ...(selectedAgent.durationProfiles?.length
            ? { durationProfile }
            : {}),
          ...(platform === "tiktok" && selectedAgent.sourceGenres?.length
            ? { sourceGenre }
            : {}),
          ...(personalizationPayload
            ? { personalization: personalizationPayload }
            : {}),
          ...(projectIntentId ? { intentId: projectIntentId } : {}),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.projectId) {
        const message =
          res.status === 402
            ? "Tu cuenta aún no tiene créditos activos. Solicita activación antes de producir."
            : data.detail || data.error || "No se pudo crear el proyecto.";
        alert(message);
        return;
      }

      router.push(`/dashboard/project/${data.projectId}`);
    } catch (e) {
      alert("Error al crear proyecto: " + e.message);
    } finally {
      setCreating(false);
    }
  };

  /* Filtrado de agentes por tier */
  const filteredAgents = useMemo(
    () =>
      allAgents.filter(
        (a) =>
          (a.platform || "youtube") === platform &&
          (tierFilter === "all" ||
            (tierFilter === "custom" ? a.agentSource === "custom" : a.tier === tierFilter)),
      ),
    [allAgents, platform, tierFilter],
  );

  /* Word/char count para textarea */
  const wordCount = topic.trim().split(/\s+/).filter(Boolean).length;
  const charCount = topic.length;
  const durationProfiles = selectedAgent?.durationProfiles || [];
  const selectedDurationProfile = durationProfiles.find((p) => p.id === durationProfile)
    || durationProfiles[0];

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
          <div
            className="cf-card cf-fade cf-fade--1"
            style={{
              padding: "var(--s-5)",
              marginBottom: "var(--s-5)",
            }}
          >
            <div
              style={{
                font: "var(--t-mono-sm)",
                color: "var(--paper-mute)",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              PLATAFORMA
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 10,
              }}
            >
              {PLATFORM_OPTIONS.map((option) => {
                const active = platform === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => selectPlatform(option.id)}
                    style={{
                      textAlign: "left",
                      padding: "14px 16px",
                      borderRadius: "var(--r-2)",
                      border: active
                        ? "1px solid var(--ember)"
                        : "1px solid var(--rule-1)",
                      background: active ? "var(--ember-tint)" : "var(--ink-0)",
                      color: "var(--paper)",
                      cursor: "pointer",
                      display: "flex",
                      gap: 12,
                      alignItems: "flex-start",
                    }}
                  >
                    <Icon
                      name={option.icon}
                      size={18}
                      style={{ color: active ? "var(--ember)" : "var(--paper-mute)" }}
                    />
                    <span>
                      <span
                        style={{
                          display: "block",
                          fontWeight: 700,
                          marginBottom: 4,
                          color: active ? "var(--ember)" : "var(--paper)",
                        }}
                      >
                        {option.label}
                      </span>
                      <span
                        style={{
                          display: "block",
                          font: "var(--t-caption)",
                          color: "var(--paper-dim)",
                          lineHeight: 1.4,
                        }}
                      >
                        {option.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Recommender card */}
          {platform === "youtube" ? (
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
          ) : (
            <div
              className="cf-card cf-fade cf-fade--1"
              style={{
                padding: "var(--s-5)",
                marginBottom: "var(--s-6)",
                borderColor: "rgba(20, 184, 166, 0.35)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  color: "#14B8A6",
                  font: "var(--t-mono-sm)",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                <Icon name="zap" size={16} /> TIKTOK STUDIO
              </div>
              <div style={{ color: "var(--paper)", fontWeight: 650, marginBottom: 6 }}>
                Nuevo módulo vertical nativo
              </div>
              <div style={{ font: "var(--t-caption)", color: "var(--paper-dim)", lineHeight: 1.5 }}>
                Estos agentes no recortan YouTube ni reutilizan Shorts: crean guion,
                visuales, subtítulos, caption y hashtags pensados para TikTok.
              </div>
            </div>
          )}

          {/* Filter strip */}
          {customAgentsError && admin && CUSTOM_AGENTS_ENABLED && (
            <div
              style={{
                marginBottom: 12,
                color: "var(--bad)",
                font: "var(--t-caption)",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <Icon name="alert" size={14} /> {customAgentsError}
            </div>
          )}
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
                  onSelect={() => selectAgent(agent)}
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
                    background: `${selectedAgent.color || getAgentColor(selectedAgent.agentId)}22`,
                    color: selectedAgent.color || getAgentColor(selectedAgent.agentId),
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
                  {selectedAgent.monogram || getMonogram(selectedAgent.agentId)}
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
                  background: `${selectedAgent.color || getAgentColor(selectedAgent.agentId)}22`,
                  color: selectedAgent.color || getAgentColor(selectedAgent.agentId),
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
                {selectedAgent.monogram || getMonogram(selectedAgent.agentId)}
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

            {durationProfiles.length > 0 && (
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
                  DURACIÓN DE SESIÓN
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: 8,
                  }}
                >
                  {durationProfiles.map((profile) => {
                    const active = profile.id === durationProfile;
                    return (
                      <button
                        key={profile.id}
                        type="button"
                        onClick={() => setDurationProfile(profile.id)}
                        style={{
                          textAlign: "left",
                          padding: "12px 14px",
                          borderRadius: "var(--r-2)",
                          border: active
                            ? "1px solid var(--ember)"
                            : "1px solid var(--rule-1)",
                          background: active ? "var(--ember-tint)" : "var(--ink-0)",
                          color: "var(--paper)",
                          cursor: "pointer",
                          transition:
                            "border-color var(--dur-base) var(--ease-out), background var(--dur-base) var(--ease-out)",
                        }}
                      >
                        <div
                          style={{
                            font: "var(--t-h3)",
                            fontFamily: "var(--font-display)",
                            fontWeight: 700,
                            color: active ? "var(--ember)" : "var(--paper)",
                            marginBottom: 4,
                          }}
                        >
                          {profile.label}
                        </div>
                        <div
                          style={{
                            font: "var(--t-caption)",
                            color: "var(--paper-dim)",
                            lineHeight: 1.35,
                          }}
                        >
                          {profile.description}
                        </div>
                      </button>
                    );
                  })}
                </div>
                {selectedDurationProfile && (
                  <div
                    style={{
                      marginTop: 8,
                      font: "var(--t-caption)",
                      color: "var(--paper-dim)",
                    }}
                  >
                    {platform === "tiktok"
                      ? `Formato vertical nativo con hook, beats cortos y render 9:16 de ${selectedDurationProfile.label}.`
                      : `Voz espaciada, ambiente continuo y visuales lentos durante ${selectedDurationProfile.label}.`}
                  </div>
                )}
              </div>
            )}

            {platform === "tiktok" && selectedAgent.sourceGenres?.length > 0 && (
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
                  ADN DE DOMINIO
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {selectedAgent.sourceGenres.map((genre) => {
                    const active = sourceGenre === genre.id;
                    return (
                      <button
                        key={genre.id}
                        type="button"
                        onClick={() => setSourceGenre(genre.id)}
                        className={`cf-btn cf-btn--sm ${active ? "cf-btn--secondary" : "cf-btn--ghost"}`}
                        style={
                          active
                            ? { borderColor: "#14B8A6", color: "#14B8A6" }
                            : undefined
                        }
                      >
                        {genre.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {isWellnessSelected && (
              <section
                style={{
                  marginBottom: "var(--s-5)",
                  paddingTop: "var(--s-5)",
                  borderTop: "1px solid var(--rule-1)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 16,
                    marginBottom: 14,
                  }}
                >
                  <div>
                    <div
                      style={{
                        font: "var(--t-mono-sm)",
                        color: "var(--ember)",
                        marginBottom: 6,
                        letterSpacing: "0.18em",
                        textTransform: "uppercase",
                      }}
                    >
                      PERSONALIZACIÓN OPCIONAL
                    </div>
                    <div
                      style={{
                        font: "var(--t-caption)",
                        color: "var(--paper-dim)",
                        lineHeight: 1.45,
                        maxWidth: 720,
                      }}
                    >
                      Úsalo para una sesión privada. Para contenido público,
                      deja el nombre vacío y escribe solo la intención.
                    </div>
                  </div>
                  <Icon
                    name="sparkles"
                    size={18}
                    style={{ color: selectedAgent.color || "var(--ember)" }}
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: 14,
                    marginBottom: 14,
                  }}
                >
                  <PersonalizationField
                    icon="user"
                    label="Nombre o apodo"
                    value={personalization.preferredName}
                    maxLength={PERSONALIZATION_LIMITS.preferredName}
                    placeholder="Ej: Tomás, Tommy, Ana"
                    helper="La voz lo usará con suavidad, no en cada frase."
                    onChange={(value) => updatePersonalization("preferredName", value)}
                  />
                  <PersonalizationField
                    icon="edit"
                    label="Frase ancla"
                    value={personalization.anchorPhrase}
                    maxLength={PERSONALIZATION_LIMITS.anchorPhrase}
                    placeholder="Ej: Estoy a salvo en mi propio ritmo"
                    helper="Se integrará como una afirmación memorable."
                    onChange={(value) => updatePersonalization("anchorPhrase", value)}
                  />
                </div>

                <PersonalizationField
                  icon="bookOpen"
                  label="Propósito o contexto"
                  value={personalization.purpose}
                  maxLength={PERSONALIZATION_LIMITS.purpose}
                  rows={3}
                  placeholder="Ej: Quiero sentir calma antes de dormir y confiar más en mis decisiones."
                  helper="No incluyas datos sensibles. Describe intención, momento o sensación buscada."
                  onChange={(value) => updatePersonalization("purpose", value)}
                />
              </section>
            )}

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

            {prefillSource && (
              <div
                style={{
                  padding: "12px 14px",
                  border: "1px solid var(--rule-1)",
                  borderLeft: "3px solid var(--ok)",
                  borderRadius: "var(--r-2)",
                  marginBottom: "var(--s-4)",
                  color: "var(--paper-dim)",
                  lineHeight: 1.45,
                }}
              >
                Tema preparado desde {prefillSource === "radar" ? "Radar" : prefillSource === "inspiration" ? "Inspiración" : "Biblioteca"}. Aún no se ha cobrado ningún crédito; el consumo empieza solo al pulsar el botón final.
                {projectIntent?.inspirationBrief?.sourceTitle ? ` Brief interno: ${projectIntent.inspirationBrief.sourceTitle}.` : ""}
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
                {creditsLeft > 0 ? (
                  <>
                    Este vídeo costará{" "}
                    <strong style={{ color: "var(--ember)" }}>1 crédito</strong>.
                    Tienes{" "}
                    <strong style={{ color: "var(--paper)" }}>
                      {creditsLeft} disponible{creditsLeft === 1 ? "" : "s"}
                    </strong>
                    .
                  </>
                ) : (
                  <>
                    Tu cuenta está lista, pero aún no tiene créditos activos.
                    Solicita activación y el equipo revisará tu acceso.
                  </>
                )}
              </div>
              {creditsLeft <= 0 && (
                <button
                  type="button"
                  className="cf-btn cf-btn--secondary cf-btn--sm"
                  onClick={handleRequestCredits}
                  disabled={requestingCredits || creditRequestSent}
                  style={{ flexShrink: 0 }}
                >
                  {creditRequestSent
                    ? "Solicitud enviada"
                    : requestingCredits
                      ? "Enviando"
                      : "Solicitar activación"}
                </button>
              )}
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
                  {platform === "tiktok"
                    ? "Crear TikTok"
                    : isWellnessSelected
                    ? "Crear sesión"
                    : "Crear documental"}{" "}
                  <Icon name="arrowRight" size={16} />
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
