"use client";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { collection, query, where, orderBy, onSnapshot, deleteDoc, doc, updateDoc, increment } from "firebase/firestore";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const STATUS_MAP = {
  draft: { label: "Borrador", color: "var(--text-muted)", icon: "📝" },
  scripting: { label: "Generando guión", color: "var(--warning)", icon: "🧠" },
  prompting: { label: "Creando prompts", color: "var(--warning)", icon: "🎬" },
  imaging: { label: "Generando imágenes", color: "var(--accent)", icon: "🖼️" },
  voicing: { label: "Narración TTS", color: "var(--accent-secondary)", icon: "🎙️" },
  assembling: { label: "Ensamblando video", color: "var(--accent)", icon: "🎥" },
  completed: { label: "Completado", color: "var(--success)", icon: "✅" },
  failed: { label: "Error", color: "var(--danger)", icon: "❌" },
};

export default function DashboardPage() {
  const { user, profile } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);

  const handleDelete = async (e, project) => {
    e.stopPropagation();
    const isCompleted = project.status === "completed";
    const msg = isCompleted
      ? `¿Eliminar "${project.title}"?\n\n⚠️ Este video ya fue completado. El crédito NO será devuelto.`
      : `¿Eliminar "${project.title}"?\n\n✅ Se te devolverá el crédito.`;
    if (!confirm(msg)) return;
    try {
      await deleteDoc(doc(db, "projects", project.id));
      // Solo devolver crédito si el proyecto NO se completó
      if (!isCompleted) {
        await updateDoc(doc(db, "users", user.uid), {
          "credits.used": increment(-1)
        });
      }
    } catch (err) {
      alert("Error al eliminar: " + err.message);
    }
  };

  useEffect(() => {
    if (!user) return;
    const q = query(
      collection(db, "projects"),
      where("userId", "==", user.uid),
      orderBy("createdAt", "desc")
    );
    const unsub = onSnapshot(q, (snap) => {
      setProjects(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
      setLoadingProjects(false);
    }, (error) => {
      console.warn("⚠️ Firestore index missing, using fallback query:", error.message);
      // Fallback: query without orderBy (no composite index needed)
      const fallbackQ = query(
        collection(db, "projects"),
        where("userId", "==", user.uid)
      );
      const unsub2 = onSnapshot(fallbackQ, (snap) => {
        const sorted = snap.docs
          .map((d) => ({ id: d.id, ...d.data() }))
          .sort((a, b) => (b.createdAt?.seconds || 0) - (a.createdAt?.seconds || 0));
        setProjects(sorted);
        setLoadingProjects(false);
      });
      return () => unsub2();
    });
    return () => unsub();
  }, [user]);

  const creditsLeft = Math.max(0, (profile?.credits?.included || 0) - (profile?.credits?.used || 0)) + (profile?.credits?.extra || 0);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 36 }} className="animate-fade-in">
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>
          Hola, {profile?.displayName?.split(" ")[0] || "Creador"} 👋
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
          {projects.length === 0
            ? "Crea tu primer documental cinematográfico con IA"
            : `Tienes ${projects.length} proyecto${projects.length !== 1 ? "s" : ""}`}
        </p>
      </div>

      {/* Quick Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 36 }} className="animate-fade-in animate-fade-in-delay-1">
        {[
          { label: "Videos creados", value: profile?.totalVideosCreated || 0, icon: "🎥", color: "var(--accent)" },
          { label: "Créditos", value: creditsLeft, icon: "🪙", color: "var(--warning)" },
          { label: "Plan", value: (profile?.plan || "free").toUpperCase(), icon: "⭐", color: "var(--success)" },
        ].map((s) => (
          <div key={s.label} className="glass-card" style={{ padding: "20px 24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>{s.label}</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.value}</div>
              </div>
              <div style={{ fontSize: 28 }}>{s.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div style={{ marginBottom: 36 }} className="animate-fade-in animate-fade-in-delay-2">
        <button className="btn-glow" onClick={() => router.push("/dashboard/new")} style={{ fontSize: 16, padding: "14px 32px" }}>
          ✨ Crear nuevo video
        </button>
      </div>

      {/* Projects List */}
      <div className="animate-fade-in animate-fade-in-delay-3">
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Mis Proyectos</h2>
        {loadingProjects ? (
          <div style={{ color: "var(--text-muted)", padding: 40, textAlign: "center" }}>Cargando proyectos...</div>
        ) : projects.length === 0 ? (
          <div className="glass-card" style={{ padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🎬</div>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Aún no tienes proyectos</div>
            <div style={{ fontSize: 14, color: "var(--text-muted)", marginBottom: 24 }}>Crea tu primer documental en minutos</div>
            <button className="btn-glow" onClick={() => router.push("/dashboard/new")}>Empezar ahora</button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {projects.map((p) => {
              const st = STATUS_MAP[p.status] || STATUS_MAP.draft;
              return (
                <div key={p.id} className="glass-card" style={{ padding: "20px 24px", cursor: "pointer" }} onClick={() => router.push(`/dashboard/project/${p.id}`)}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
                    <div style={{ flex: 1, minWidth: 200 }}>
                      <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{p.title || "Sin título"}</div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        Agente: {p.agentId?.replace("agent_", "").replace(/_/g, " ")}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 16 }}>{st.icon}</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: st.color }}>{st.label}</span>
                      {p.progress?.percent > 0 && p.status !== "completed" && (
                        <div style={{ width: 60, height: 6, background: "var(--bg-primary)", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ width: `${p.progress.percent}%`, height: "100%", background: "var(--accent)", borderRadius: 3, transition: "width 0.5s" }} />
                        </div>
                      )}
                      <button
                        onClick={(e) => handleDelete(e, p)}
                        title="Eliminar proyecto"
                        style={{
                          background: "transparent",
                          border: "1px solid rgba(255,59,48,0.3)",
                          color: "var(--danger, #ff3b30)",
                          borderRadius: 6,
                          padding: "4px 10px",
                          fontSize: 12,
                          cursor: "pointer",
                          marginLeft: 4,
                          transition: "all 0.2s",
                        }}
                        onMouseEnter={(e) => { e.target.style.background = "rgba(255,59,48,0.15)"; }}
                        onMouseLeave={(e) => { e.target.style.background = "transparent"; }}
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
