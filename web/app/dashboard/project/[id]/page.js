"use client";
import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { doc, onSnapshot, updateDoc } from "firebase/firestore";
import { SYSTEM_AGENTS } from "@/lib/agents";

export default function ProjectDetailsPage({ params }) {
  const resolvedParams = React.use(params);
  const { id } = resolvedParams;
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("script"); // script, scenes, audio
  const [editedScript, setEditedScript] = useState("");

  // ── Smooth Progress Bar State ──
  const [displayPercent, setDisplayPercent] = useState(0);
  const [startTime, setStartTime] = useState(null);

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

  // Funciones para guardar cambios en el script y disparar producción
  const handleSaveScript = async () => {
    const confirmed = confirm(
      "✅ ¿Aprobar guión y comenzar producción cinemática?\n\n" +
      "Pipeline Cinemático:\n" +
      "1. 🎨 Generación de imágenes (FLUX)\n" +
      "2. 🎙️ Narración profesional (ElevenLabs)\n" +
      "3. 🎥 Clips cinemáticos (Luma AI)\n" +
      "4. 🎬 Ken Burns sincronizado\n" +
      "5. 📽️ Ensamblaje final HD\n\n" +
      "El proceso tarda ~10-15 min según la cantidad de escenas."
    );
    if (!confirmed) return;

    try {
      // 1. Guardar guión aprobado en Firebase
      await updateDoc(doc(db, "projects", id), {
        "script.plain": editedScript,
        "script.approved": true,
        "status": "producing",
        "progress.percent": 2,
        "progress.stepName": "Iniciando producción...",
      });

      // 2. Disparar pipeline de producción en el VPS
      const vpsUrl = process.env.NEXT_PUBLIC_VPS_API_URL;
      if (vpsUrl) {
        fetch(`${vpsUrl}/produce`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projectId: id })
        }).catch(err => console.error("Error contactando VPS:", err));
      } else {
        console.warn("⚠️ Falta NEXT_PUBLIC_VPS_API_URL en .env.local");
      }

      alert("🚀 ¡Producción iniciada! Puedes ver el progreso en la barra superior.");
    } catch(e) {
      alert("Error al guardar: " + e.message);
    }
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
              <a
                href={`/api/download/video/${encodeURIComponent(project.title?.replace(/ /g, '_').replace(/[^a-zA-Z0-9_\-]/g, '_'))}`}
                className="btn-glow"
                style={{ padding: "10px 20px", fontSize: "13px", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "8px" }}
                download
              >
                📥 Descargar Video
              </a>
            )}
            <a
              href={`/api/download/images/${encodeURIComponent(project.title?.replace(/ /g, '_').replace(/[^a-zA-Z0-9_\-]/g, '_'))}`}
              className="btn-secondary"
              style={{ padding: "10px 20px", fontSize: "13px", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "8px" }}
              download
            >
              🖼️ Descargar Imágenes (ZIP)
            </a>
          </div>
        )}

      </div>

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
        <button 
          style={{ padding: "8px 16px", fontSize: "14px", fontWeight: "bold", transition: "all 0.3s", color: activeTab === 'audio' ? 'var(--accent)' : 'var(--text-secondary)', borderBottom: activeTab === 'audio' ? '2px solid var(--accent)' : '2px solid transparent', background: "none", borderTop: "none", borderLeft: "none", borderRight: "none", cursor: "pointer" }} 
          onClick={() => setActiveTab("audio")}
        >
          🔊 Audio TTS
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
                    <button onClick={handleSaveScript} className="btn-glow" style={{ padding: "8px 16px", fontSize: "13px" }}>
                      Aprobar y Producir 🚀
                    </button>
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

      {/* Tab: Audio */}
      {activeTab === "audio" && (
        <div className="glass-card animate-fade-in" style={{ padding: "48px", textAlign: "center" }}>
          <div style={{ fontSize: "48px", marginBottom: "24px" }}>🎙️</div>
          <h3 style={{ fontSize: "24px", fontWeight: "bold", margin: "0 0 12px 0" }}>Estudio de Audio TTS</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "400px", margin: "0 auto 24px auto", lineHeight: "1.5" }}>
            Una vez apruebes el guión, el motor de voces neuronales generará la narración perfecta para tu documental.
          </p>
          <button className="btn-secondary" disabled style={{ opacity: 0.5, cursor: "not-allowed" }}>
            Aprobar guión primero
          </button>
        </div>
      )}
    </div>
  );
}
