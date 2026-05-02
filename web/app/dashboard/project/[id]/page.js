"use client";
import React, { useEffect, useState, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { doc, onSnapshot, updateDoc } from "firebase/firestore";
import { SYSTEM_AGENTS } from "@/lib/agents";

// ── Virality Score Engine ──
function computeViralityScore(text) {
  if (!text || text.length < 50) return null;
  const words = text.split(/\s+/);
  const wordCount = words.length;
  const sentences = text.split(/[.!?]+/).filter(Boolean);

  // 1. Hooks (questions, exclamations, power phrases)
  const hooks = (text.match(/\?/g) || []).length;
  const exclamations = (text.match(/!/g) || []).length;
  const powerPhrases = ['imagina', 'secreto', 'verdad', 'nadie te dice', 'increíble', 'impactante', 'descubre', 'revelado', 'sorprendente', 'poderoso', 'extraordinario', 'fascinante'];
  const powerCount = powerPhrases.reduce((c, p) => c + (text.toLowerCase().match(new RegExp(p, 'gi')) || []).length, 0);
  const hookScore = Math.min(100, ((hooks * 8) + (exclamations * 3) + (powerCount * 12)));

  // 2. Emotional triggers
  const emotionalWords = ['miedo', 'amor', 'muerte', 'odio', 'pasión', 'poder', 'dolor', 'sangre', 'traición', 'venganza', 'gloria', 'destino', 'guerra', 'locura', 'esperanza', 'terror', 'misterio', 'oscuro', 'prohibido', 'peligro'];
  const emotionalCount = emotionalWords.reduce((c, w) => c + (text.toLowerCase().match(new RegExp(`\\b${w}`, 'gi')) || []).length, 0);
  const emotionScore = Math.min(100, emotionalCount * 10);

  // 3. Pacing (avg words per sentence — ideal 12-18)
  const avgWordsPerSentence = wordCount / Math.max(sentences.length, 1);
  const pacingScore = avgWordsPerSentence >= 10 && avgWordsPerSentence <= 20 ? 90 : avgWordsPerSentence < 10 ? 65 : 55;

  // 4. SEO / Structure
  const hasNumbers = /\d/.test(text);
  const hasLists = text.includes('1.') || text.includes('•');
  const paragraphs = text.split(/\n\n+/).length;
  const structureScore = Math.min(100, (hasNumbers ? 20 : 0) + (hasLists ? 15 : 0) + Math.min(paragraphs * 5, 40) + (wordCount > 800 ? 25 : wordCount > 400 ? 15 : 5));

  // 5. Retention (narrative arcs, cliffhangers)
  const cliffhangers = ['pero', 'sin embargo', 'lo que no sabían', 'entonces', 'de pronto', 'hasta que', 'lo peor', 'lo mejor'];
  const cliffCount = cliffhangers.reduce((c, p) => c + (text.toLowerCase().match(new RegExp(p, 'gi')) || []).length, 0);
  const retentionScore = Math.min(100, cliffCount * 8 + (wordCount > 1000 ? 20 : 10));

  const overall = Math.round((hookScore * 0.25) + (emotionScore * 0.2) + (pacingScore * 0.2) + (structureScore * 0.15) + (retentionScore * 0.2));

  return { overall, hookScore: Math.round(hookScore), hooks, emotionScore: Math.round(emotionScore), pacingScore: Math.round(pacingScore), structureScore: Math.round(structureScore), retentionScore: Math.round(retentionScore), avgWordsPerSentence: Math.round(avgWordsPerSentence) };
}

export default function ProjectDetailsPage({ params }) {
  const resolvedParams = React.use(params);
  const { id } = resolvedParams;
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("script");
  const [editedScript, setEditedScript] = useState("");

  // ── Auto-approve timer ──
  const AUTO_APPROVE_SECONDS = 180; // 3 minutes
  const [timerActive, setTimerActive] = useState(false);
  const [timerPaused, setTimerPaused] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(AUTO_APPROVE_SECONDS);
  const timerRef = useRef(null);
  const autoApproveTriggered = useRef(false);

  // ── Smooth Progress Bar State ──
  const [displayPercent, setDisplayPercent] = useState(0);
  const [startTime, setStartTime] = useState(null);

  // ── Inline video player state (lazy-loaded, fetches signed URL on click) ──
  const [videoState, setVideoState] = useState({ url: null, loading: false, error: null });

  const loadVideoPlayer = async () => {
    setVideoState({ url: null, loading: true, error: null });
    const vpsBase = process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
    try {
      const res = await fetch(`${vpsBase}/video-url/${encodeURIComponent(id)}`);
      const data = await res.json();
      if (data.url) {
        const finalUrl = data.url.startsWith("http") ? data.url : `${vpsBase}${data.url}`;
        setVideoState({ url: finalUrl, loading: false, error: null });
      } else {
        setVideoState({ url: null, loading: false, error: data.error || "URL no disponible" });
      }
    } catch (err) {
      setVideoState({ url: null, loading: false, error: err.message });
    }
  };

  const copyVideoUrl = async () => {
    if (!videoState.url) return;
    try {
      await navigator.clipboard.writeText(videoState.url);
    } catch (e) {
      // Silent fail; copy is nice-to-have
    }
  };

  // Track when generation starts
  useEffect(() => {
    if (project?.progress?.percent > 0 && project?.progress?.percent < 100 && !startTime) {
      setStartTime(Date.now());
    }
    if (project?.progress?.percent >= 100 || project?.status === "error") {
      setStartTime(null);
    }
  }, [project?.progress?.percent]);

  // Smooth interpolation: gradually creep toward realPercent, NEVER exceeding it
  useEffect(() => {
    const realPercent = project?.progress?.percent || 0;

    if (realPercent >= 100 || realPercent === 0) {
      setDisplayPercent(realPercent);
      return;
    }

    // Jump forward if backend jumped ahead
    if (realPercent > displayPercent + 5) {
      setDisplayPercent(realPercent - 2);
    }

    // Creep slowly toward realPercent (never exceed it)
    const interval = setInterval(() => {
      setDisplayPercent((prev) => {
        if (prev >= realPercent - 0.5) return prev; // Don't exceed real %
        return prev + 0.3; // Slow, smooth increment
      });
    }, 600);

    return () => clearInterval(interval);
  }, [project?.progress?.percent, displayPercent]);

  // Calculate ETA
  const getETA = () => {
    if (!startTime || displayPercent >= 100 || displayPercent === 0) return null;
    const elapsed = (Date.now() - startTime) / 1000;
    const rate = displayPercent / elapsed; // percent per second
    if (rate <= 0) return null;
    const remaining = (100 - displayPercent) / rate;
    const mins = Math.floor(remaining / 60);
    const secs = Math.floor(remaining % 60);
    if (mins > 15) return null; // Don't show unreasonable estimates
    return mins > 0 ? `~${mins}m ${secs}s restantes` : `~${secs}s restantes`;
  };

  useEffect(() => {
    if (!user || !id) return;

    // Escuchar cambios en tiempo real desde Firebase
    const unsub = onSnapshot(doc(db, "projects", id), (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        setProject(data);
        if (!editedScript && data.script?.plain) {
          setEditedScript(data.script.plain);
        }
      }
      setLoading(false);
    });

    return () => unsub();
  }, [user, id]);

  // ── Auto-approve: start timer when script is ready ──
  useEffect(() => {
    if (project?.script?.plain && project?.status === "script_ready" && !project?.script?.approved && !autoApproveTriggered.current) {
      setTimerActive(true);
      setTimerPaused(false);
      setTimerSeconds(AUTO_APPROVE_SECONDS);
    } else {
      setTimerActive(false);
    }
  }, [project?.script?.plain, project?.status, project?.script?.approved]);

  // Core approval logic (used by both manual and auto-approve)
  const executeApproval = useCallback(async () => {
    try {
      setTimerActive(false);
      await updateDoc(doc(db, "projects", id), {
        "script.plain": editedScript,
        "script.approved": true,
        "status": "producing",
        "progress.percent": 2,
        "progress.stepName": "Iniciando producción...",
      });
      const vpsUrl = process.env.NEXT_PUBLIC_VPS_API_URL;
      if (vpsUrl) {
        fetch(`${vpsUrl}/produce`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projectId: id })
        }).catch(err => console.error("Error contactando VPS:", err));
      }
    } catch(e) {
      alert("Error: " + e.message);
    }
  }, [id, editedScript]);

  useEffect(() => {
    if (!timerActive || timerPaused) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => {
      setTimerSeconds(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          if (!autoApproveTriggered.current) {
            autoApproveTriggered.current = true;
            executeApproval();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [timerActive, timerPaused, executeApproval]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
        <div className="spinner"></div>
      </div>
    );
  }

  if (!project) {
    return <div>Proyecto no encontrado.</div>;
  }

  const agent = SYSTEM_AGENTS.find(a => a.agentId === project.agentId);
  const isProcessing = project.progress?.percent > 0 && project.progress?.percent < 100 && project.status !== "error";
  const eta = getETA();

  const handleSaveScript = async () => {
    autoApproveTriggered.current = true;
    setTimerActive(false);
    await executeApproval();
  };

  return (
    <div className="animate-fade-in" style={{ paddingBottom: "80px" }}>
      {/* Header Premium */}
      <div className="glass-card" style={{ marginBottom: "32px", padding: "24px", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "16px", borderLeft: `4px solid ${agent?.color || 'var(--accent)'}` }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <span style={{ fontSize: "32px" }}>{agent?.emoji}</span>
            <span className="badge badge-pro">{project.status.toUpperCase()}</span>
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: "800", margin: "0 0 4px 0" }}>{project.title}</h1>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)", margin: 0 }}>
            Agente: {agent?.name || project.agentId} • Creado: {project.createdAt?.toDate().toLocaleDateString()}
          </p>
        </div>

        {/* Barra de Progreso Mágica — Smooth Interpolation */}
        <div style={{ background: "var(--bg-card)", padding: "16px", borderRadius: "12px", border: "1px solid var(--border)", minWidth: "300px", position: "relative", overflow: "hidden" }}>
          {/* Barra animada suave */}
          <div style={{
            position: "absolute", top: 0, left: 0, height: "4px",
            background: displayPercent >= 100 ? "var(--success, #4ade80)" : "var(--accent)",
            transition: "width 0.8s ease-out",
            width: `${Math.round(displayPercent)}%`,
            boxShadow: isProcessing ? "0 0 12px var(--accent), 0 0 24px var(--accent)" : "0 0 10px var(--accent)"
          }} />
          {/* Shimmer effect while processing */}
          {isProcessing && (
            <div style={{
              position: "absolute", top: 0, left: 0, height: "4px", width: "100%",
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
              animation: "shimmer 2s infinite",
            }} />
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontSize: "11px", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px", color: displayPercent >= 100 ? "var(--success, #4ade80)" : "var(--accent)" }}>Progreso</span>
            <span style={{ fontSize: "12px", fontFamily: "monospace" }}>{Math.round(displayPercent)}%</span>
          </div>
          <p style={{ fontSize: "14px", fontWeight: "500", margin: 0, animation: isProcessing ? "pulse 2s infinite" : "none" }}>
            {project.progress?.stepName || "Procesando..."}
          </p>
          {eta && (
            <p style={{ fontSize: "11px", color: "var(--text-muted)", margin: "6px 0 0 0", fontFamily: "monospace" }}>
              ⏱️ {eta}
            </p>
          )}
        </div>

        {/* Botones de descarga */}
        {(project.status === "completed" || project.status === "producing") && (
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {project.status === "completed" && (
                <button
                  onClick={async () => {
                    const vpsBase = process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
                    try {
                      const res = await fetch(`${vpsBase}/video-url/${encodeURIComponent(id)}`);
                      const data = await res.json();
                      if (data.url) {
                        // Storage signed URL o fallback a /download/video del VPS
                        const finalUrl = data.url.startsWith("http") ? data.url : `${vpsBase}${data.url}`;
                        window.open(finalUrl, "_blank", "noopener,noreferrer");
                      } else {
                        alert(`No se pudo obtener URL: ${data.error || "desconocido"}`);
                      }
                    } catch (err) {
                      alert(`Error al obtener URL de descarga: ${err.message}`);
                    }
                  }}
                  className="btn-glow"
                  style={{ padding: "10px 20px", fontSize: "13px", border: "none", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "8px" }}
                >
                  📥 Descargar Video
                </button>
              )}
            {(() => {
                const folder = project.videoFolder || project.title?.replace(/ /g, '_').replace(/[^a-zA-Z0-9_\-]/g, '_');
                const vpsBase = process.env.NEXT_PUBLIC_VPS_API_URL || "http://100.99.207.113:8085";
                return (
                  <a
                    href={`${vpsBase}/download/images/${encodeURIComponent(folder)}`}
                    className="btn-secondary"
                    style={{ padding: "10px 20px", fontSize: "13px", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "8px" }}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    🖼️ Descargar Imágenes (ZIP)
                  </a>
                );
              })()}
          </div>
        )}

      </div>

      {/* Reproductor de video (solo cuando el proyecto está completado) */}
      {project.status === "completed" && (
        <div className="glass-card animate-fade-in" style={{ marginBottom: "32px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: videoState.url ? "16px" : "0" }}>
            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: "bold", display: "flex", alignItems: "center", gap: "8px" }}>
              🎬 Reproductor
              {project.hasSubtitles && <span className="badge badge-free" style={{ fontSize: "10px" }}>Con subtítulos</span>}
              {project.videoSizeMB && <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "normal" }}>{project.videoSizeMB} MB</span>}
            </h3>
            {!videoState.url && !videoState.loading && (
              <button
                onClick={loadVideoPlayer}
                className="btn-glow"
                style={{ padding: "8px 16px", fontSize: "13px", border: "none", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                ▶️ Cargar reproductor
              </button>
            )}
            {videoState.loading && (
              <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Cargando URL firmada…</span>
            )}
            {videoState.url && (
              <button
                onClick={copyVideoUrl}
                className="btn-secondary"
                style={{ padding: "6px 12px", fontSize: "12px", cursor: "pointer" }}
                title="Copiar URL al portapapeles (válida 7 días)"
              >
                📋 Copiar URL
              </button>
            )}
          </div>

          {videoState.error && (
            <div style={{ padding: "12px", background: "rgba(220, 38, 38, 0.1)", border: "1px solid rgba(220, 38, 38, 0.3)", borderRadius: "8px", color: "#fca5a5", fontSize: "13px" }}>
              ❌ {videoState.error}
              <button onClick={loadVideoPlayer} style={{ marginLeft: "12px", padding: "4px 10px", fontSize: "12px", background: "transparent", border: "1px solid currentColor", color: "inherit", borderRadius: "4px", cursor: "pointer" }}>
                Reintentar
              </button>
            </div>
          )}

          {videoState.url && (
            <video
              src={videoState.url}
              controls
              preload="metadata"
              style={{ width: "100%", maxHeight: "70vh", background: "#000", borderRadius: "8px", display: "block" }}
            >
              Tu navegador no soporta video HTML5.
            </video>
          )}

          {!videoState.url && !videoState.loading && !videoState.error && (
            <p style={{ margin: "12px 0 0 0", fontSize: "12px", color: "var(--text-muted)" }}>
              El video se sirve desde Firebase Storage con URL firmada (válida 7 días, se renueva al cargar).
            </p>
          )}
        </div>
      )}

      {/* Tabs Menu */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "24px", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
        <button 
          style={{ padding: "8px 16px", fontSize: "14px", fontWeight: "bold", transition: "all 0.3s", color: activeTab === 'script' ? 'var(--accent)' : 'var(--text-secondary)', borderBottom: activeTab === 'script' ? '2px solid var(--accent)' : '2px solid transparent', background: "none", borderTop: "none", borderLeft: "none", borderRight: "none", cursor: "pointer" }} 
          onClick={() => setActiveTab("script")}
        >
          📄 Guión (Teleprompter)
        </button>
        <button 
          style={{ padding: "8px 16px", fontSize: "14px", fontWeight: "bold", transition: "all 0.3s", color: activeTab === 'scenes' ? 'var(--accent)' : 'var(--text-secondary)', borderBottom: activeTab === 'scenes' ? '2px solid var(--accent)' : '2px solid transparent', background: "none", borderTop: "none", borderLeft: "none", borderRight: "none", cursor: "pointer" }} 
          onClick={() => setActiveTab("scenes")}
        >
          🎬 Escenas Visuales
        </button>
      </div>

      {/* Tab: Script */}
      {activeTab === "script" && (
        <div className="animate-fade-in" style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: "24px" }}>
          <div>
            <div className="glass-card" style={{ padding: "24px", position: "relative" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>Edición de Guión</h3>
                {project.script?.plain ? (
                  project.status === "producing" ? (
                    <span className="badge badge-starter" style={{ animation: "pulse 2s infinite" }}>⚙️ Produciendo...</span>
                  ) : project.script?.approved && project.status !== "script_ready" ? (
                    <span className="badge badge-free">✅ Ya aprobado</span>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {/* Timer display */}
                      {timerActive && (
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{
                            position: "relative", width: "38px", height: "38px",
                            borderRadius: "50%",
                            background: `conic-gradient(${timerPaused ? '#facc15' : 'var(--accent)'} ${(timerSeconds / AUTO_APPROVE_SECONDS) * 360}deg, rgba(255,255,255,0.1) 0deg)`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                          }}>
                            <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: "var(--bg-card)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontFamily: "monospace", fontWeight: "bold" }}>
                              {Math.floor(timerSeconds / 60)}:{String(timerSeconds % 60).padStart(2, '0')}
                            </div>
                          </div>
                          <button
                            onClick={() => setTimerPaused(!timerPaused)}
                            style={{ background: "none", border: "1px solid var(--border)", borderRadius: "6px", padding: "4px 10px", fontSize: "12px", cursor: "pointer", color: timerPaused ? "#facc15" : "var(--text-secondary)" }}
                          >
                            {timerPaused ? "▶️ Reanudar" : "⏸️ Pausar"}
                          </button>
                        </div>
                      )}
                      <button onClick={handleSaveScript} className="btn-glow" style={{ padding: "8px 16px", fontSize: "13px" }}>
                        Aprobar y Producir 🚀
                      </button>
                    </div>
                  )
                ) : (
                  <span className="badge badge-free" style={{ animation: "pulse 2s infinite" }}>Esperando a la IA...</span>
                )}
              </div>
              
              {project.script?.plain ? (
                 <textarea 
                 value={editedScript}
                 onChange={(e) => setEditedScript(e.target.value)}
                 style={{ width: "100%", background: "rgba(0,0,0,0.2)", color: "white", padding: "16px", borderRadius: "8px", border: "1px solid var(--border)", outline: "none", fontFamily: "serif", fontSize: "18px", lineHeight: "1.6", resize: "vertical", minHeight: "500px" }}
                 placeholder="El guión aparecerá aquí..."
               />
              ) : (
                <div style={{ height: "400px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", textAlign: "center", border: "2px dashed var(--border)", borderRadius: "12px" }}>
                  <div style={{ fontSize: "48px", marginBottom: "16px", animation: "bounce 2s infinite" }}>🤖</div>
                  <h4 style={{ fontSize: "18px", fontWeight: "bold", margin: "0 0 8px 0" }}>El Chef está cocinando</h4>
                  <p style={{ color: "var(--text-muted)", fontSize: "14px", maxWidth: "300px", margin: 0 }}>
                    El motor de IA está investigando el tema y escribiendo una narrativa cinematográfica. Esto toma de 1 a 2 minutos.
                  </p>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="glass-card" style={{ padding: "20px" }}>
              <h4 style={{ fontWeight: "bold", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px" }}>📊 Estadísticas</h4>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "12px", fontSize: "14px" }}>
                <li style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Palabras:</span>
                  <span style={{ fontFamily: "monospace" }}>{project.script?.wordCount || 0}</span>
                </li>
                <li style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Minutos est:</span>
                  <span style={{ fontFamily: "monospace" }}>{project.script?.estimatedMinutes || 0} min</span>
                </li>
                <li style={{ display: "flex", justifyContent: "space-between", paddingBottom: "8px" }}>
                  <span style={{ color: "var(--text-secondary)" }}>Estado:</span>
                  <span style={{ color: project.script?.approved ? "#4ade80" : "#facc15", fontWeight: "bold" }}>
                    {project.script?.approved ? "Aprobado" : "Borrador"}
                  </span>
                </li>
              </ul>
            </div>

            {/* Virality Score Panel */}
            {editedScript && (() => {
              const score = computeViralityScore(editedScript);
              if (!score) return null;
              const scoreColor = score.overall >= 75 ? '#4ade80' : score.overall >= 50 ? '#facc15' : '#f87171';
              const ScoreBar = ({ label, value, emoji }) => (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
                  <span style={{ width: "16px" }}>{emoji}</span>
                  <span style={{ flex: 1, color: "var(--text-secondary)" }}>{label}</span>
                  <div style={{ width: "60px", height: "6px", background: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${value}%`, height: "100%", background: value >= 75 ? '#4ade80' : value >= 50 ? '#facc15' : '#f87171', borderRadius: "3px", transition: "width 0.5s" }} />
                  </div>
                  <span style={{ fontFamily: "monospace", fontSize: "11px", width: "28px", textAlign: "right" }}>{value}</span>
                </div>
              );
              return (
                <div className="glass-card" style={{ padding: "20px" }}>
                  <h4 style={{ fontWeight: "bold", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: "8px" }}>🔥 Viralidad</h4>
                  {/* Overall score circle */}
                  <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "16px" }}>
                    <div style={{
                      width: "56px", height: "56px", borderRadius: "50%",
                      background: `conic-gradient(${scoreColor} ${score.overall * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <div style={{ width: "44px", height: "44px", borderRadius: "50%", background: "var(--bg-card)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "900", color: scoreColor }}>
                        {score.overall}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: "700", color: scoreColor }}>
                        {score.overall >= 80 ? "🚀 Viral" : score.overall >= 60 ? "👍 Bueno" : score.overall >= 40 ? "⚡ Mejorable" : "📝 Revisar"}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{score.hooks} hooks detectados</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <ScoreBar label="Hooks" value={score.hookScore} emoji="🎣" />
                    <ScoreBar label="Emoción" value={score.emotionScore} emoji="❤️" />
                    <ScoreBar label="Ritmo" value={score.pacingScore} emoji="🥁" />
                    <ScoreBar label="Estructura" value={score.structureScore} emoji="📐" />
                    <ScoreBar label="Retención" value={score.retentionScore} emoji="🧲" />
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Tab: Escenas */}
      {activeTab === "scenes" && (
        <div className="animate-fade-in">
          {(!project.scenes || project.scenes.length === 0) ? (
            <div className="glass-card" style={{ padding: "48px", textAlign: "center" }}>
              <div style={{ fontSize: "48px", marginBottom: "16px", animation: "pulse 2s infinite" }}>🎬</div>
              <h3 style={{ fontSize: "20px", fontWeight: "bold", margin: "0 0 8px 0" }}>Analizando Escenas</h3>
              <p style={{ color: "var(--text-muted)", margin: 0 }}>El Director de Fotografía está dividiendo tu guión en prompts visuales cada 5 segundos...</p>
            </div>
          ) : (
            <>
              {/* Contador de progreso de imágenes */}
              {project.status === "producing" && (
                <div className="glass-card" style={{ padding: "16px 24px", marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "24px", animation: "pulse 2s infinite" }}>🎨</span>
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: "bold" }}>Generando imágenes</div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        {project.scenes.filter(s => s.imageUrl).length} de {project.scenes.length} listas
                      </div>
                    </div>
                  </div>
                  <div style={{ width: "120px", height: "8px", background: "var(--bg-primary)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ 
                      width: `${(project.scenes.filter(s => s.imageUrl).length / project.scenes.length) * 100}%`,
                      height: "100%", background: "linear-gradient(90deg, var(--accent), var(--accent-secondary))",
                      borderRadius: "4px", transition: "width 1s ease"
                    }} />
                  </div>
                </div>
              )}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "24px" }}>
                {project.scenes.map((scene, idx) => (
                  <div key={idx} className="glass-card" style={{ overflow: "hidden", transition: "all 0.3s" }}>
                    <div style={{ aspectRatio: "16/9", background: "var(--bg-dark)", display: "flex", justifyContent: "center", alignItems: "center", position: "relative", overflow: "hidden" }}>
                      {scene.imageUrl ? (
                        <img 
                          src={scene.imageUrl} 
                          alt={`Scene ${idx+1}`} 
                          style={{ width: "100%", height: "100%", objectFit: "cover", animation: "fadeIn 0.8s ease" }} 
                          loading="lazy"
                        />
                      ) : project.status === "producing" ? (
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative", width: "100%", height: "100%", justifyContent: "center" }}>
                          <div style={{ 
                            position: "absolute", inset: 0,
                            background: "linear-gradient(90deg, transparent 0%, rgba(139,92,246,0.08) 50%, transparent 100%)",
                            animation: "shimmer 2.5s infinite"
                          }} />
                          <span style={{ fontSize: "28px", marginBottom: "8px", animation: "pulse 3s infinite" }}>🖌️</span>
                          <span style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "2px", color: "var(--accent)", fontWeight: "bold" }}>Generando...</span>
                        </div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                          <span style={{ fontSize: "24px", marginBottom: "8px" }}>🎨</span>
                          <span style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-muted)" }}>En cola</span>
                        </div>
                      )}
                      <div className="badge" style={{ position: "absolute", top: "8px", left: "8px", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}>
                        Escena {idx + 1}
                      </div>
                      {scene.imageUrl && (
                        <div className="badge" style={{ position: "absolute", top: "8px", right: "8px", background: "rgba(74,222,128,0.2)", color: "#4ade80", backdropFilter: "blur(4px)" }}>
                          ✅
                        </div>
                      )}
                    </div>
                    <div style={{ padding: "16px" }}>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", margin: 0 }}>{scene.prompt || scene}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

    </div>
  );
}
