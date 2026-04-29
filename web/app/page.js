"use client";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [user, loading, router]);

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
          Elige un agente especializado, escribe tu idea, y obtén un documental cinematográfico de 10 minutos listo para YouTube. Guión, imágenes, narración y video — todo automatizado.
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

      {/* Agent Preview Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, maxWidth: 700, width: "100%" }} className="animate-fade-in animate-fade-in-delay-2">
        {[
          { emoji: "💀", name: "Horror", color: "#8B0000" },
          { emoji: "🔍", name: "Misterios", color: "#1a1a6e" },
          { emoji: "👑", name: "Biografías", color: "#DAA520" },
          { emoji: "🔬", name: "Ciencia", color: "#00CED1" },
          { emoji: "🧘", name: "Filosofía", color: "#6A5ACD" },
        ].map((a) => (
          <div key={a.name} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "20px 12px", textAlign: "center", borderTop: `3px solid ${a.color}` }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>{a.emoji}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>{a.name}</div>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div style={{ display: "flex", gap: 48, marginTop: 64, color: "var(--text-muted)", fontSize: 14 }} className="animate-fade-in animate-fade-in-delay-3">
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)" }}>10</div>
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
