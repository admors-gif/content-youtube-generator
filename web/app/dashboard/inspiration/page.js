"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "@/components/Icon";
import { useAuth } from "@/context/AuthContext";
import { isAdminUser } from "@/lib/admin";
import { authedFetch, getApiBase } from "@/lib/apiClient";
import { SYSTEM_AGENTS } from "@/lib/agents";

const SOURCE_VIDEO_ENABLED =
  process.env.NEXT_PUBLIC_CONTENT_FACTORY_SOURCE_VIDEO_ENABLED !== "false";

const STATUS_LABELS = {
  imported: "Importado",
  transcript_ready: "Transcript listo",
  analyzed: "Analizado",
  adapted: "Adaptado",
  idea_saved: "Idea lista",
  project_prepared: "Proyecto preparado",
  project_created: "Proyecto creado",
  archived: "Archivado",
};

function Chip({ children, tone = "neutral" }) {
  const cls =
    tone === "bad"
      ? "cf-badge--bad"
      : tone === "ok"
        ? "cf-badge--ok"
        : tone === "warn"
          ? "cf-badge--warn"
          : "cf-badge--neutral";
  return <span className={`cf-badge ${cls}`}>{children}</span>;
}

function StatCard({ label, value, sub }) {
  return (
    <div className="cf-card" style={{ padding: "var(--s-4)" }}>
      <div className="cf-eyebrow">{label}</div>
      <div className="cf-h2" style={{ marginTop: 10 }}>{value}</div>
      {sub && <div className="cf-caption" style={{ marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function SourceCard({ item, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="cf-card"
      style={{
        width: "100%",
        textAlign: "left",
        padding: "var(--s-4)",
        borderColor: active ? "var(--ember)" : "var(--rule-1)",
        cursor: "pointer",
      }}
    >
      <div style={{ display: "flex", gap: 12 }}>
        {item.thumbnailUrl ? (
          <img
            src={item.thumbnailUrl}
            alt=""
            style={{
              width: 104,
              height: 58,
              objectFit: "cover",
              borderRadius: "var(--r-1)",
              border: "1px solid var(--rule-1)",
              flex: "none",
            }}
          />
        ) : (
          <div
            style={{
              width: 104,
              height: 58,
              borderRadius: "var(--r-1)",
              background: "var(--ink-2)",
              display: "grid",
              placeItems: "center",
              flex: "none",
            }}
          >
            <Icon name="clapperboard" size={20} />
          </div>
        )}
        <div style={{ minWidth: 0 }}>
          <div style={{ font: "var(--t-body)", color: "var(--paper)", fontWeight: 700, lineHeight: 1.25 }}>
            {item.title || "Video fuente"}
          </div>
          <div className="cf-caption" style={{ marginTop: 6 }}>
            {item.channelName || "YouTube"} · {STATUS_LABELS[item.status] || item.status || "Importado"}
          </div>
        </div>
      </div>
    </button>
  );
}

function scoreTone(score) {
  if (score >= 72) return "ok";
  if (score >= 55) return "warn";
  return "bad";
}

export default function InspirationPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const admin = isAdminUser(user, profile);

  const [sourceUrl, setSourceUrl] = useState("");
  const [niche, setNiche] = useState("motivacional_espiritual");
  const [library, setLibrary] = useState([]);
  const [collections, setCollections] = useState([]);
  const [source, setSource] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [derivation, setDerivation] = useState(null);
  const [route, setRoute] = useState(null);
  const [adaptation, setAdaptation] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [customAgents, setCustomAgents] = useState([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("Motivacion espiritual suave");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const podcastAgents = useMemo(() => {
    const systemPodcast = SYSTEM_AGENTS.filter((agent) => agent.format === "podcast");
    const customPodcast = customAgents.filter((agent) => agent.format === "podcast" || agent.templateKey === "podcast_two_hosts");
    return [...customPodcast, ...systemPodcast];
  }, [customAgents]);

  const recommendedAgentId = route?.agentRecommendations?.[0]?.agentId || "";
  const effectiveSelectedAgentId = selectedAgentId || recommendedAgentId || podcastAgents[0]?.agentId || "";
  const selectedAgent = podcastAgents.find((item) => item.agentId === effectiveSelectedAgentId);
  const selectedCollection = collections.find((item) => item.collectionId === selectedCollectionId);
  const titleOptions = derivation?.titles || [];
  const similarityRisk = adaptation?.sourceSafety?.similarityRisk || derivation?.similarity?.risk || "";

  async function apiFetch(path, options = {}) {
    const res = await authedFetch(user, `${getApiBase()}${path}`, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.error || "Operacion no disponible.");
    }
    return data;
  }

  async function loadLibrary() {
    if (!user || !admin || !SOURCE_VIDEO_ENABLED) return;
    const data = await apiFetch("/source-videos?limit=80");
    setLibrary(data.items || []);
  }

  async function loadCollections() {
    if (!user || !admin || !SOURCE_VIDEO_ENABLED) return;
    const data = await apiFetch("/inspiration/collections");
    const items = data.collections || [];
    setCollections(items);
    if (!selectedCollectionId && items[0]?.collectionId) setSelectedCollectionId(items[0].collectionId);
  }

  useEffect(() => {
    if (!user || !admin || !SOURCE_VIDEO_ENABLED) return;
    let cancelled = false;
    async function bootstrap() {
      try {
        const [sourcesData, agentsData, collectionsData] = await Promise.all([
          apiFetch("/source-videos?limit=80"),
          apiFetch("/custom-agents?status=active").catch(() => ({ agents: [] })),
          apiFetch("/inspiration/collections").catch(() => ({ collections: [] })),
        ]);
        if (cancelled) return;
        setLibrary(sourcesData.items || []);
        setCustomAgents((agentsData.agents || []).map((item) => item.publicAgent || item).filter((item) => item.agentId));
        const items = collectionsData.collections || [];
        setCollections(items);
        if (items[0]?.collectionId) setSelectedCollectionId(items[0].collectionId);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, admin]);

  async function openSource(item) {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await apiFetch(`/source-videos/${encodeURIComponent(item.sourceVideoId)}`);
      setSource(data.item || item);
      setAnalysis(data.analysis?.analysisId ? data.analysis : null);
      setDerivation(data.derivation?.derivationId ? data.derivation : null);
      setRoute(data.route?.recommendedAction ? data.route : null);
      setAdaptation(data.adaptation?.adaptationId ? data.adaptation : null);
      setSelectedTitle(data.adaptation?.visibleTitle || data.derivation?.recommendedTitle || data.derivation?.titles?.[0]?.title || "");
      setTranscript("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function importVideo() {
    if (!sourceUrl.trim()) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await apiFetch("/source-videos/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: sourceUrl.trim(), niche }),
      });
      setSource(data.item);
      setAnalysis(null);
      setDerivation(null);
      setRoute(null);
      setAdaptation(null);
      setSelectedTitle("");
      setTranscript("");
      setNotice("Video importado. Pega el transcript manual para analizarlo.");
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveTranscript() {
    if (!source?.sourceVideoId || transcript.trim().length < 200) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/transcript`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, transcriptSource: "manual" }),
      });
      const refreshed = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}`);
      setSource(refreshed.item);
      setAnalysis(null);
      setDerivation(null);
      setRoute(null);
      setAdaptation(null);
      setNotice("Transcript guardado. Ya puedes analizar estructura, retencion y ADN editorial.");
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function routeSource(nextAnalysis = analysis) {
    if (!source?.sourceVideoId || !nextAnalysis?.analysisId) return null;
    const data = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysisId: nextAnalysis.analysisId }),
    });
    setRoute(data.route);
    if (data.route?.agentRecommendations?.[0]?.agentId) setSelectedAgentId(data.route.agentRecommendations[0].agentId);
    return data.route;
  }

  async function analyzeSource() {
    if (!source?.sourceVideoId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: false }),
      });
      setAnalysis(data.analysis);
      setDerivation(null);
      setAdaptation(null);
      await routeSource(data.analysis);
      setNotice(data.cached ? "Analisis cacheado cargado." : "Analisis editorial listo. Revisa el triaje.");
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function derivePodcast() {
    if (!source?.sourceVideoId || !analysis?.analysisId) return null;
    const agent = podcastAgents.find((item) => item.agentId === effectiveSelectedAgentId);
    const data = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/derive-podcast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysisId: analysis.analysisId,
        selectedTitle,
        targetAgentName: agent?.name || "Podcast",
      }),
    });
    setDerivation(data.derivation);
    setSelectedTitle(data.derivation?.recommendedTitle || data.derivation?.titles?.[0]?.title || "");
    return data.derivation;
  }

  async function handleDerivePodcast() {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await derivePodcast();
      setNotice("Brief original generado. Ahora puedes adaptar a un agente o guardar la idea.");
      await loadLibrary();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function adaptToAgent(allowLowFit = false) {
    if (!source?.sourceVideoId || !analysis?.analysisId || !effectiveSelectedAgentId) return null;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const nextDerivation = derivation || await derivePodcast();
      const data = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/adapt-to-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysisId: analysis.analysisId,
          derivationId: nextDerivation?.derivationId,
          selectedTitle,
          agentId: effectiveSelectedAgentId,
          allowLowFit,
        }),
      });
      setAdaptation(data.adaptation);
      setSelectedTitle(data.adaptation?.visibleTitle || data.adaptation?.shortTopic || selectedTitle);
      setNotice("Adaptacion lista. El titulo corto se usara para preparar proyecto.");
      await loadLibrary();
      return data.adaptation;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function saveIdea() {
    if (!source?.sourceVideoId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const nextDerivation = derivation || await derivePodcast();
      const agent = podcastAgents.find((item) => item.agentId === effectiveSelectedAgentId);
      await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/save-idea`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysisId: analysis?.analysisId,
          derivationId: nextDerivation?.derivationId,
          selectedTitle,
          agentId: effectiveSelectedAgentId,
          agentName: agent?.name,
          agentFile: agent?.promptFile,
        }),
      });
      setNotice("Idea guardada en la biblioteca editorial.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function prepareProject() {
    if (!source?.sourceVideoId || !effectiveSelectedAgentId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      let nextAdaptation = adaptation;
      if (!nextAdaptation?.adaptationId) nextAdaptation = await adaptToAgent(true);
      if (!nextAdaptation?.adaptationId) return;
      const data = await apiFetch(`/source-videos/${encodeURIComponent(source.sourceVideoId)}/prepare-project-v2`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysisId: analysis?.analysisId,
          derivationId: derivation?.derivationId,
          adaptationId: nextAdaptation.adaptationId,
          agentId: effectiveSelectedAgentId,
        }),
      });
      router.push(data.preparedUrl || "/dashboard/new");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function createCollection() {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await apiFetch("/inspiration/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newCollectionName, niche }),
      });
      await loadCollections();
      setSelectedCollectionId(data.collection?.collectionId || "");
      setNotice("Coleccion creada. Agrega videos fuente para formar un agente nuevo.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function addToCollection() {
    if (!source?.sourceVideoId || !selectedCollectionId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(`/inspiration/collections/${encodeURIComponent(selectedCollectionId)}/add-source`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sourceVideoId: source.sourceVideoId }),
      });
      await loadCollections();
      setNotice("Video agregado a la coleccion.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function analyzeCollection() {
    if (!selectedCollectionId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiFetch(`/inspiration/collections/${encodeURIComponent(selectedCollectionId)}/analyze`, {
        method: "POST",
      });
      await loadCollections();
      setNotice("Coleccion analizada. Ya puede generar un agente draft.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function draftAgentFromCollection() {
    if (!selectedCollectionId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await apiFetch(`/inspiration/collections/${encodeURIComponent(selectedCollectionId)}/draft-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Alma y Claridad" }),
      });
      await loadCollections();
      setNotice(`Agente draft creado: ${data.agent?.name || "Alma y Claridad"}. Pruebalo y activalo desde Agentes.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!SOURCE_VIDEO_ENABLED) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <div className="cf-eyebrow">Inspiracion</div>
        <h1 className="cf-h2" style={{ margin: 0 }}>Modulo apagado</h1>
      </div>
    );
  }

  if (!admin) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <div className="cf-eyebrow">Admin</div>
        <h1 className="cf-h2" style={{ margin: 0 }}>Acceso admin</h1>
      </div>
    );
  }

  return (
    <div>
      <header className="cf-fade" style={{ marginBottom: "var(--s-6)" }}>
        <div className="cf-eyebrow" style={{ color: "var(--ember)" }}>Inspiracion V2</div>
        <h1 className="cf-display" style={{ margin: "8px 0 10px" }}>Videos exitosos a contenido original</h1>
        <p style={{ font: "var(--t-body-lg)", color: "var(--paper-dim)", margin: 0, maxWidth: 980 }}>
          Importa videos, detecta su ADN editorial y decide si conviene adaptar, guardar o crear un agente nuevo.
        </p>
      </header>

      {(notice || error) && (
        <div
          className="cf-card"
          style={{
            padding: "var(--s-4)",
            marginBottom: "var(--s-5)",
            color: error ? "var(--bad)" : "var(--ok)",
            borderColor: error ? "var(--bad)" : "var(--ok)",
          }}
        >
          {error || notice}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: "var(--s-4)", marginBottom: "var(--s-5)" }}>
        <StatCard label="Fuentes" value={library.length} sub="videos guardados" />
        <StatCard label="Estado" value={source ? (STATUS_LABELS[source.status] || source.status) : "sin fuente"} sub="flujo actual" />
        <StatCard label="Triaje" value={route?.recommendedAction ? "listo" : "pendiente"} sub={route?.recommendedAction || "analiza primero"} />
        <StatCard label="Credito" value="0" sub="hasta crear proyecto" />
      </div>

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(260px, 0.6fr)", gap: "var(--s-4)", alignItems: "end" }}>
          <label>
            <div className="cf-eyebrow">Link de YouTube</div>
            <input
              className="cf-input"
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
            />
          </label>
          <label>
            <div className="cf-eyebrow">Nicho</div>
            <select className="cf-input" value={niche} onChange={(event) => setNiche(event.target.value)}>
              <option value="motivacional_espiritual">Motivacional / espiritual suave</option>
              <option value="crecimiento_emocional">Crecimiento emocional</option>
              <option value="podcast_reflexivo">Podcast reflexivo</option>
            </select>
          </label>
        </div>
        <div style={{ display: "flex", gap: "var(--s-3)", marginTop: "var(--s-4)", flexWrap: "wrap" }}>
          <button className="cf-btn cf-btn--primary" type="button" onClick={importVideo} disabled={loading || !sourceUrl.trim()}>
            <Icon name="download" size={16} /> Importar video
          </button>
          <button className="cf-btn cf-btn--secondary" type="button" onClick={loadLibrary} disabled={loading}>
            <Icon name="refresh" size={16} /> Actualizar biblioteca
          </button>
        </div>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.35fr) minmax(340px, 0.65fr)", gap: "var(--s-5)", alignItems: "start" }}>
        <main style={{ display: "grid", gap: "var(--s-5)" }}>
          {source && (
            <section className="cf-card" style={{ padding: "var(--s-5)" }}>
              <div style={{ display: "flex", gap: "var(--s-4)", alignItems: "flex-start" }}>
                {source.thumbnailUrl && (
                  <img
                    src={source.thumbnailUrl}
                    alt=""
                    style={{ width: 220, aspectRatio: "16 / 9", objectFit: "cover", borderRadius: "var(--r-2)", border: "1px solid var(--rule-1)" }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="cf-eyebrow">{source.channelName || "YouTube"}</div>
                  <h2 className="cf-h2" style={{ margin: "8px 0" }}>{source.title}</h2>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Chip tone="ok">{STATUS_LABELS[source.status] || source.status}</Chip>
                    <Chip>{Number(source.views || 0).toLocaleString("es-MX")} vistas</Chip>
                    <Chip>{source.publishedAt ? source.publishedAt.slice(0, 10) : "sin fecha"}</Chip>
                  </div>
                  {source.sourceUrl && (
                    <a href={source.sourceUrl} target="_blank" rel="noreferrer" className="cf-btn cf-btn--ghost cf-btn--sm" style={{ marginTop: 14, textDecoration: "none", display: "inline-flex" }}>
                      <Icon name="externalLink" size={14} /> Abrir fuente
                    </a>
                  )}
                </div>
              </div>
            </section>
          )}

          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div className="cf-eyebrow">Transcript</div>
            <h2 className="cf-h2" style={{ margin: "8px 0 10px" }}>Pegar transcript manual</h2>
            <p className="cf-caption" style={{ margin: "0 0 14px", maxWidth: 860 }}>
              El transcript se usa como materia prima privada. El resultado final debe transformar estructura e idea, no copiar frases.
            </p>
            <textarea
              className="cf-input"
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
              placeholder="Pega aqui la transcripcion del video fuente..."
              rows={8}
              style={{ resize: "vertical" }}
            />
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 12 }}>
              <div className="cf-caption">{transcript.length.toLocaleString("es-MX")} caracteres</div>
              <button className="cf-btn cf-btn--secondary" type="button" onClick={saveTranscript} disabled={loading || !source || transcript.trim().length < 200}>
                <Icon name="check" size={16} /> Guardar transcript
              </button>
            </div>
          </section>

          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
              <div>
                <div className="cf-eyebrow">Diagnostico</div>
                <h2 className="cf-h2" style={{ margin: "8px 0 0" }}>ADN editorial</h2>
              </div>
              <button className="cf-btn cf-btn--primary" type="button" onClick={analyzeSource} disabled={loading || !source || source.transcriptStatus === "missing"}>
                <Icon name="search" size={16} /> Analizar y triar
              </button>
            </div>

            {analysis ? (
              <div style={{ display: "grid", gap: "var(--s-4)", marginTop: "var(--s-4)" }}>
                <div className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)" }}>
                  <div className="cf-eyebrow">Tesis</div>
                  <p style={{ margin: "8px 0 0", color: "var(--paper)", lineHeight: 1.5 }}>{analysis.centralThesis}</p>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--s-4)" }}>
                  <div className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)" }}>
                    <div className="cf-eyebrow">Promesa</div>
                    <p className="cf-caption" style={{ marginTop: 8, lineHeight: 1.45 }}>{analysis.emotionalPromise}</p>
                  </div>
                  <div className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)" }}>
                    <div className="cf-eyebrow">Espiritualidad</div>
                    <p className="cf-caption" style={{ marginTop: 8, lineHeight: 1.45 }}>
                      {analysis.spiritualProfile?.level || route?.spiritualProfile?.level || "none"} · espiritualidad suave al transformar.
                    </p>
                  </div>
                  <div className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)" }}>
                    <div className="cf-eyebrow">Reuso</div>
                    <p className="cf-caption" style={{ marginTop: 8, lineHeight: 1.45 }}>
                      {analysis.reusePolicy?.copyrightRisk || "medium"} · fuente solo como inspiracion estructural.
                    </p>
                  </div>
                </div>
                <div>
                  <div className="cf-eyebrow" style={{ marginBottom: 10 }}>Beats de estructura</div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {(analysis.structureBeats || []).slice(0, 8).map((beat) => (
                      <div key={`${beat.order}-${beat.label}`} className="cf-card" style={{ padding: 12, borderRadius: "var(--r-2)" }}>
                        <strong>{String(beat.order).padStart(2, "0")} · {beat.label}</strong>
                        <div className="cf-caption" style={{ marginTop: 6 }}>{beat.purpose}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="cf-card" style={{ padding: "var(--s-6)", marginTop: "var(--s-4)", textAlign: "center" }}>
                <div className="cf-caption">Guarda un transcript y ejecuta el analisis para ver tesis, estructura, retencion y triaje.</div>
              </div>
            )}
          </section>

          {analysis && (
            <section className="cf-card" style={{ padding: "var(--s-5)" }}>
              <div className="cf-eyebrow">Que quieres hacer</div>
              <h2 className="cf-h2" style={{ margin: "8px 0 14px" }}>Triaje inteligente</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--s-4)" }}>
                <button className="cf-card" type="button" onClick={() => adaptToAgent(false)} disabled={loading} style={{ padding: "var(--s-4)", textAlign: "left", cursor: "pointer" }}>
                  <div className="cf-eyebrow">Adaptar</div>
                  <h3 style={{ margin: "8px 0", color: "var(--paper)" }}>A agente existente</h3>
                  <p className="cf-caption">Transforma la fuente a la identidad del agente seleccionado.</p>
                </button>
                <button className="cf-card" type="button" onClick={saveIdea} disabled={loading} style={{ padding: "var(--s-4)", textAlign: "left", cursor: "pointer" }}>
                  <div className="cf-eyebrow">Guardar</div>
                  <h3 style={{ margin: "8px 0", color: "var(--paper)" }}>Como idea</h3>
                  <p className="cf-caption">La conserva en biblioteca sin crear proyecto ni gastar credito.</p>
                </button>
                <button className="cf-card" type="button" onClick={addToCollection} disabled={loading || !selectedCollectionId} style={{ padding: "var(--s-4)", textAlign: "left", cursor: "pointer" }}>
                  <div className="cf-eyebrow">Coleccion</div>
                  <h3 style={{ margin: "8px 0", color: "var(--paper)" }}>Alimentar agente</h3>
                  <p className="cf-caption">Agrupa videos exitosos para crear un agente nuevo en draft.</p>
                </button>
              </div>
            </section>
          )}

          {route?.agentRecommendations?.length > 0 && (
            <section className="cf-card" style={{ padding: "var(--s-5)" }}>
              <div className="cf-eyebrow">Agentes recomendados</div>
              <h2 className="cf-h2" style={{ margin: "8px 0 14px" }}>Fit editorial</h2>
              <div style={{ display: "grid", gap: "var(--s-3)" }}>
                {route.agentRecommendations.map((item) => {
                  const active = effectiveSelectedAgentId === item.agentId;
                  return (
                    <button
                      key={item.agentId}
                      type="button"
                      onClick={() => setSelectedAgentId(item.agentId)}
                      className="cf-card"
                      style={{
                        padding: "var(--s-4)",
                        textAlign: "left",
                        borderColor: active ? "var(--ember)" : "var(--rule-1)",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                        <div>
                          <strong style={{ color: "var(--paper)" }}>{item.agentName}</strong>
                          <div className="cf-caption" style={{ marginTop: 6 }}>{item.recommendation === "create_agent" ? "Mejor crear agente nuevo" : "Puede adaptarse"}</div>
                        </div>
                        <Chip tone={scoreTone(item.score)}>Fit {item.score}</Chip>
                      </div>
                      {item.warnings?.[0] && <p className="cf-caption" style={{ margin: "10px 0 0", color: "var(--bad)" }}>{item.warnings[0]}</p>}
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          <section className="cf-card" style={{ padding: "var(--s-5)" }}>
            <div className="cf-eyebrow">Brief y proyecto</div>
            <h2 className="cf-h2" style={{ margin: "8px 0 14px" }}>Adaptacion final</h2>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(260px, 0.65fr)", gap: "var(--s-4)", alignItems: "end" }}>
              <label>
                <div className="cf-eyebrow">Agente destino</div>
                <select className="cf-input" value={effectiveSelectedAgentId} onChange={(event) => setSelectedAgentId(event.target.value)}>
                  {podcastAgents.map((agent) => (
                    <option key={agent.agentId} value={agent.agentId}>
                      {agent.agentSource === "custom" ? "Mis agentes · " : ""}{agent.name}
                    </option>
                  ))}
                </select>
              </label>
              <button className="cf-btn cf-btn--secondary" type="button" onClick={handleDerivePodcast} disabled={loading || !analysis}>
                <Icon name="sparkles" size={16} /> Generar brief
              </button>
            </div>

            {derivation && (
              <div style={{ marginTop: "var(--s-4)", display: "grid", gap: "var(--s-4)" }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Chip tone={similarityRisk === "high" ? "bad" : similarityRisk === "medium" ? "warn" : "ok"}>Similitud {similarityRisk || "low"}</Chip>
                  <Chip>{derivation.model || "modelo"}</Chip>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "var(--s-4)" }}>
                  {titleOptions.map((item) => {
                    const active = selectedTitle === item.title;
                    return (
                      <button
                        key={item.title}
                        type="button"
                        onClick={() => setSelectedTitle(item.title)}
                        className="cf-card"
                        style={{ padding: "var(--s-4)", textAlign: "left", borderColor: active ? "var(--ember)" : "var(--rule-1)", cursor: "pointer" }}
                      >
                        <div style={{ font: "var(--t-h3)", color: "var(--paper)", lineHeight: 1.2 }}>{item.title}</div>
                        {item.hook && <p className="cf-caption" style={{ margin: "10px 0 0", lineHeight: 1.4 }}>{item.hook}</p>}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {adaptation && (
              <div className="cf-card" style={{ padding: "var(--s-4)", borderRadius: "var(--r-2)", marginTop: "var(--s-4)" }}>
                <div className="cf-eyebrow">Titulo corto para crear</div>
                <h3 style={{ color: "var(--paper)", margin: "8px 0" }}>{adaptation.visibleTitle}</h3>
                <p className="cf-caption" style={{ lineHeight: 1.5 }}>{adaptation.inspirationBrief}</p>
                {adaptation.warnings?.length > 0 && (
                  <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                    {adaptation.warnings.map((warning) => <div key={warning} className="cf-caption" style={{ color: "var(--bad)" }}>{warning}</div>)}
                  </div>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: "var(--s-3)", flexWrap: "wrap", marginTop: "var(--s-4)" }}>
              <button className="cf-btn cf-btn--secondary" type="button" onClick={() => adaptToAgent(true)} disabled={loading || !analysis}>
                <Icon name="check" size={16} /> Adaptar a agente
              </button>
              <button className="cf-btn cf-btn--primary" type="button" onClick={prepareProject} disabled={loading || !analysis || similarityRisk === "high"}>
                <Icon name="arrowRight" size={16} /> Preparar proyecto
              </button>
            </div>
          </section>
        </main>

        <aside style={{ display: "grid", gap: "var(--s-5)", position: "sticky", top: 24 }}>
          <section className="cf-card" style={{ padding: "var(--s-4)" }}>
            <div className="cf-eyebrow">Biblioteca</div>
            <h2 className="cf-h2" style={{ margin: "8px 0 14px" }}>Videos fuente</h2>
            <div style={{ display: "grid", gap: 10, maxHeight: "38vh", overflow: "auto", paddingRight: 4 }}>
              {library.length ? (
                library.map((item) => (
                  <SourceCard
                    key={item.sourceVideoId}
                    item={item}
                    active={source?.sourceVideoId === item.sourceVideoId}
                    onClick={() => openSource(item)}
                  />
                ))
              ) : (
                <div className="cf-card" style={{ padding: "var(--s-5)", textAlign: "center" }}>
                  <div className="cf-caption">Aun no hay videos fuente importados.</div>
                </div>
              )}
            </div>
          </section>

          <section className="cf-card" style={{ padding: "var(--s-4)" }}>
            <div className="cf-eyebrow">Colecciones</div>
            <h2 className="cf-h2" style={{ margin: "8px 0 14px" }}>Crear agente nuevo</h2>
            <div style={{ display: "grid", gap: "var(--s-3)" }}>
              <input className="cf-input" value={newCollectionName} onChange={(event) => setNewCollectionName(event.target.value)} placeholder="Nombre de coleccion" />
              <button className="cf-btn cf-btn--secondary" type="button" onClick={createCollection} disabled={loading || !newCollectionName.trim()}>
                <Icon name="plus" size={16} /> Crear coleccion
              </button>
              {collections.length > 0 && (
                <select className="cf-input" value={selectedCollectionId} onChange={(event) => setSelectedCollectionId(event.target.value)}>
                  {collections.map((item) => (
                    <option key={item.collectionId} value={item.collectionId}>
                      {item.name} · {(item.sourceVideoIds || []).length} fuente(s)
                    </option>
                  ))}
                </select>
              )}
              {selectedCollection && (
                <div className="cf-card" style={{ padding: "var(--s-3)", borderRadius: "var(--r-2)" }}>
                  <div className="cf-caption">{selectedCollection.status}</div>
                  <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(selectedCollection.aggregateDNA?.themes || []).slice(0, 5).map((theme) => <Chip key={theme}>{theme}</Chip>)}
                  </div>
                </div>
              )}
              <button className="cf-btn cf-btn--secondary" type="button" onClick={addToCollection} disabled={loading || !source || !selectedCollectionId}>
                <Icon name="plus" size={16} /> Agregar video actual
              </button>
              <button className="cf-btn cf-btn--secondary" type="button" onClick={analyzeCollection} disabled={loading || !selectedCollectionId}>
                <Icon name="search" size={16} /> Analizar coleccion
              </button>
              <button className="cf-btn cf-btn--primary" type="button" onClick={draftAgentFromCollection} disabled={loading || !selectedCollectionId}>
                <Icon name="sparkles" size={16} /> Crear agente draft
              </button>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
