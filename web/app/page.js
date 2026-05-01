"use client";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { SYSTEM_AGENTS } from "@/lib/agents";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

  // Show 8 representative agents from different categories
  const previewAgents = SYSTEM_AGENTS.filter((_, i) => i % Math.ceil(SYSTEM_AGENTS.length / 8) === 0).slice(0, 8);

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", background: "radial-gradient(ellipse at top, #1a1a2e 0%, #0a0a0f 70%)" }}>
      {/* Hero */}
      <div style={{ textAlign: "center", maxWidth: 700, marginBottom: 48 }} className="animate-fade-in">
        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 2, marginBottom: 16 }}>
          ⚡ Content Factory
        </div>
        <h1 style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, lineHeight: 1.1, marginBottom: 20, background: "linear-gradient(135deg, #f0f0f5 0%, #7c3aed 50%, #06b6d4 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Documentales con IA en minutos, no semanas
        </h1>
        <p style={{ fontSize: 18, color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: 36 }}>
          Elige entre {SYSTEM_AGENTS.length} agentes especializados, escribe tu idea, y obtén un documental cinematográfico de 10 minutos listo para YouTube. Guión, imágenes, narración y video — todo automatizado.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <button className="btn-glow" onClick={() => router.push("/login")} style={{ fontSize: 17, padding: "16px 36px" }}>
            Crear mi primer video gratis →
          </button>
          <button className="btn-secondary" onClick={() => router.push("/login")} style={{ fontSize: 17, padding: "16px 36px" }}>
            Iniciar sesión
          </button>
        </div>
      </div>

      {/* Agent Preview Grid — Dynamic from SYSTEM_AGENTS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, maxWidth: 700, width: "100%" }} className="animate-fade-in animate-fade-in-delay-2">
        {previewAgents.map((a) => (
          <div key={a.agentId} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 12px", textAlign: "center", borderTop: `3px solid ${a.color}`, cursor: "pointer", transition: "transform 0.2s, border-color 0.2s" }}
            onClick={() => router.push("/login")}
            onMouseOver={(e) => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.borderColor = a.color; }}
            onMouseOut={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.borderColor = "var(--border)"; }}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>{a.emoji}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>{a.name.split(" ")[0]}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 12, fontSize: 13, color: "var(--text-muted)" }} className="animate-fade-in animate-fade-in-delay-2">
        +{SYSTEM_AGENTS.length - previewAgents.length} agentes más disponibles
      </div>

      {/* Stats */}
      <div style={{ display: "flex", gap: 48, marginTop: 48, color: "var(--text-muted)", fontSize: 14 }} className="animate-fade-in animate-fade-in-delay-3">
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)" }}>{SYSTEM_AGENTS.length}</div>
          <div>Agentes IA</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent-secondary)" }}>~$2</div>
          <div>Por video</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--success)" }}>10 min</div>
          <div>Documentales</div>
        </div>
      </div>
    </div>
  );
}
