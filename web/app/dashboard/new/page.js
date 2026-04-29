"use client";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { collection, addDoc, serverTimestamp, doc, updateDoc, increment } from "firebase/firestore";
import { useRouter } from "next/navigation";
import { SYSTEM_AGENTS } from "@/lib/agents";

export default function NewProjectPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [topic, setTopic] = useState("");
  const [creating, setCreating] = useState(false);
  const [previewAgent, setPreviewAgent] = useState(null);

  const creditsLeft = Math.max(0, (profile?.credits?.included || 0) - (profile?.credits?.used || 0)) + (profile?.credits?.extra || 0);

  const handleCreate = async () => {
    if (!selectedAgent || !topic.trim()) return;
    if (creditsLeft <= 0) {
      alert("No tienes créditos disponibles. Mejora tu plan o compra créditos extra.");
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
        progress: { currentStep: 0, totalSteps: 6, stepName: "Iniciando generación en la nube...", percent: 5 },
        script: { plain: "", tagged: "", wordCount: 0, estimatedMinutes: 0, approved: false },
        scenes: [],
        voice: { model: "es-US-Neural2-A", gender: "female", speed: 1.0, pitch: 0 },
        output: {},
        seo: {},
        costs: {},
        createdAt: serverTimestamp(),
        completedAt: null,
      });

      // [SPRINT 2 - PASO 1.5] Descontar crédito de Firebase
      await updateDoc(doc(db, "users", user.uid), {
        "credits.used": increment(1)
      });

      // [SPRINT 2 - PASO 1] El Timbre (Aviso a n8n en Hostinger)
      try {
        const webhookUrl = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL;
        if (webhookUrl) {
          // Disparamos la petición en background (no bloqueamos el router.push)
          fetch(webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              projectId: docRef.id,
              userId: user.uid,
              topic: topic.trim(),
              agentFile: selectedAgent.promptFile
            })
          }).catch(err => console.error("Error contactando a n8n:", err));
        } else {
          console.warn("⚠️ Falta NEXT_PUBLIC_N8N_WEBHOOK_URL en .env.local");
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

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }} className="animate-fade-in">
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>✨ Crear nuevo video</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
          {step === 1 ? "Paso 1 de 2: Elige un agente de personalidad" : "Paso 2 de 2: Describe tu idea"}
        </p>
        {/* Step indicator */}
        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          {[1, 2].map((s) => (
            <div key={s} style={{ flex: 1, height: 4, borderRadius: 2, background: s <= step ? "var(--accent)" : "var(--bg-card)", transition: "background 0.3s" }} />
          ))}
        </div>
      </div>

      {/* STEP 1: Agent Selection */}
      {step === 1 && (
        <div className="animate-fade-in">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
            {SYSTEM_AGENTS.map((agent, i) => (
              <div
                key={agent.agentId}
                className={`agent-card animate-fade-in ${selectedAgent?.agentId === agent.agentId ? "selected" : ""}`}
                style={{ "--agent-color": agent.color, animationDelay: `${i * 0.05}s`, opacity: 0 }}
                onClick={() => { setSelectedAgent(agent); setPreviewAgent(agent); }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <div style={{ fontSize: 32 }}>{agent.emoji}</div>
                  <span className={`badge badge-${agent.tier}`}>{agent.tier}</span>
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{agent.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: 12 }}>{agent.description}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Ejemplo: {agent.exampleTopics[0]}
                </div>
              </div>
            ))}
          </div>

          {/* Preview panel */}
          {previewAgent && (
            <div className="glass-card" style={{ padding: 24, marginTop: 24, borderLeft: `3px solid ${previewAgent.color}` }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
                {previewAgent.emoji} {previewAgent.name} — Ideas sugeridas:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {previewAgent.exampleTopics.map((t) => (
                  <button key={t} className="btn-secondary" style={{ fontSize: 13, padding: "8px 16px" }}
                    onClick={() => { setTopic(t); setStep(2); }}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: 24 }}>
            <button className="btn-glow" disabled={!selectedAgent} onClick={() => setStep(2)} style={{ padding: "14px 32px" }}>
              Continuar con {selectedAgent?.name || "..."} →
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Topic Input */}
      {step === 2 && (
        <div className="animate-fade-in">
          {/* Selected agent recap */}
          <div className="glass-card" style={{ padding: "16px 20px", marginBottom: 24, display: "flex", alignItems: "center", gap: 12, borderLeft: `3px solid ${selectedAgent?.color}` }}>
            <span style={{ fontSize: 28 }}>{selectedAgent?.emoji}</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700 }}>{selectedAgent?.name}</div>
              <span style={{ fontSize: 12, color: "var(--text-muted)", cursor: "pointer" }} onClick={() => setStep(1)}>Cambiar agente</span>
            </div>
          </div>

          <div style={{ maxWidth: 600 }}>
            <label style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, display: "block" }}>¿Sobre qué será tu documental?</label>
            <input className="input-field" placeholder={`Ej: ${selectedAgent?.exampleTopics[0]}`} value={topic} onChange={(e) => setTopic(e.target.value)} autoFocus style={{ marginBottom: 16, fontSize: 16 }} />

            {/* Suggestions */}
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>💡 Ideas populares:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 24 }}>
              {selectedAgent?.exampleTopics.map((t) => (
                <button key={t} className="btn-secondary" style={{ fontSize: 12, padding: "6px 14px" }} onClick={() => setTopic(t)}>
                  {t}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <button className="btn-glow" disabled={!topic.trim() || creating} onClick={handleCreate} style={{ padding: "14px 32px" }}>
                {creating ? "Creando..." : "🎬 Crear documental (1 crédito)"}
              </button>
              <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
                {creditsLeft} crédito{creditsLeft !== 1 ? "s" : ""} disponible{creditsLeft !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
