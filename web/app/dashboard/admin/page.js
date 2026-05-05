"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { authHeaders, getApiBase } from "@/lib/apiClient";
import { isAdminUser } from "@/lib/admin";
import Icon from "@/components/Icon";

function fmtDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("es-MX", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Stat({ label, value }) {
  return (
    <div className="cf-card" style={{ padding: "var(--s-4)" }}>
      <div className="cf-mono-sm" style={{ color: "var(--paper-mute)", marginBottom: 8 }}>
        {label}
      </div>
      <div className="cf-h3" style={{ margin: 0 }}>
        {value}
      </div>
    </div>
  );
}

export default function AdminPage() {
  const { user, profile } = useAuth();
  const [users, setUsers] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [queue, setQueue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [amounts, setAmounts] = useState({});
  const [granting, setGranting] = useState("");

  const isAdmin = isAdminUser(user, profile);

  const loadAdminData = async () => {
    if (!user || !isAdmin) return;
    setLoading(true);
    setError("");
    try {
      const headers = await authHeaders(user);
      const [usersRes, metricsRes, queueRes] = await Promise.all([
        fetch(`${getApiBase()}/admin/users`, { headers }),
        fetch(`${getApiBase()}/metrics`, { headers }),
        fetch(`${getApiBase()}/queue/health`, { headers }),
      ]);
      const usersData = await usersRes.json().catch(() => ({}));
      const metricsData = await metricsRes.json().catch(() => ({}));
      const queueData = await queueRes.json().catch(() => ({}));
      if (!usersRes.ok) throw new Error(usersData.detail || usersData.error || "No se pudo cargar usuarios");
      setUsers(usersData.users || []);
      setMetrics(metricsRes.ok ? metricsData : null);
      setQueue(queueRes.ok ? queueData : null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadAdminData();
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, isAdmin]);

  const grantCredits = async (uid) => {
    const amount = Math.max(1, Math.min(25, Number(amounts[uid]) || 1));
    setGranting(uid);
    setError("");
    try {
      const res = await fetch(`${getApiBase()}/admin/users/${uid}/credits`, {
        method: "POST",
        headers: await authHeaders(user, { "Content-Type": "application/json" }),
        body: JSON.stringify({ amount }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron asignar créditos");
      await loadAdminData();
    } catch (e) {
      setError(e.message);
    } finally {
      setGranting("");
    }
  };

  if (!isAdmin) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-6)" }}>
        <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 12 }}>
          ACCESO RESTRINGIDO
        </div>
        <h1 className="cf-h2" style={{ margin: 0 }}>
          Esta vista es solo para administración.
        </h1>
      </div>
    );
  }

  const pending = users.filter((u) => u.creditRequest?.status === "pending").length;

  return (
    <div>
      <header style={{ marginBottom: "var(--s-6)" }}>
        <div className="cf-mono-sm" style={{ color: "var(--ember)", marginBottom: 10 }}>
          PANEL ADMIN
        </div>
        <h1 className="cf-display" style={{ margin: 0 }}>
          Operación y créditos
        </h1>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 14,
          marginBottom: "var(--s-5)",
        }}
      >
        <Stat label="Solicitudes" value={pending} />
        <Stat label="Procesos activos" value={metrics?.jobs?.active ?? "—"} />
        <Stat label="Workers ocupados" value={queue?.active_tasks ?? "—"} />
        <Stat label="Completados 24h" value={metrics?.jobs?.completed_24h ?? "—"} />
      </div>

      {error && (
        <div
          className="cf-card"
          style={{
            padding: "var(--s-4)",
            borderColor: "var(--ember)",
            color: "var(--paper)",
            marginBottom: "var(--s-5)",
          }}
        >
          {error}
        </div>
      )}

      <div className="cf-card" style={{ padding: "var(--s-5)" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            marginBottom: "var(--s-4)",
          }}
        >
          <div>
            <div className="cf-mono-sm" style={{ color: "var(--paper-mute)", marginBottom: 6 }}>
              USUARIOS
            </div>
            <h2 className="cf-h3" style={{ margin: 0 }}>
              Solicitudes y saldo
            </h2>
          </div>
          <button className="cf-btn cf-btn--secondary cf-btn--sm" onClick={loadAdminData}>
            <Icon name="refresh" size={14} /> Actualizar
          </button>
        </div>

        {loading ? (
          <div className="cf-mono-sm">CARGANDO OPERACIÓN</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {users.map((item) => {
              const requestStatus = item.creditRequest?.status || "sin solicitud";
              return (
                <div
                  key={item.uid}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(220px, 1.2fr) repeat(4, minmax(90px, 0.6fr)) minmax(230px, 0.9fr)",
                    gap: 12,
                    alignItems: "center",
                    padding: "14px 0",
                    borderTop: "1px solid var(--rule-1)",
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {item.email || item.displayName || item.uid}
                    </div>
                    <div className="cf-mono-sm" style={{ color: "var(--paper-mute)" }}>
                      {requestStatus.toUpperCase()} · {fmtDate(item.creditRequest?.requestedAt)}
                    </div>
                  </div>
                  <div className="cf-mono-sm">PLAN {String(item.plan || "free").toUpperCase()}</div>
                  <div className="cf-mono-sm">CRÉD. {item.credits?.remaining ?? 0}</div>
                  <div className="cf-mono-sm">ACT. {item.projects?.active ?? 0}</div>
                  <div className="cf-mono-sm">TOTAL {item.projects?.total ?? 0}</div>
                  <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                    <input
                      type="number"
                      min="1"
                      max="25"
                      value={amounts[item.uid] || 1}
                      onChange={(e) => setAmounts((prev) => ({ ...prev, [item.uid]: e.target.value }))}
                      aria-label={`Créditos para ${item.email}`}
                      style={{
                        width: 72,
                        background: "var(--ink-2)",
                        border: "1px solid var(--rule-1)",
                        borderRadius: "var(--r-2)",
                        color: "var(--paper)",
                        padding: "8px 10px",
                      }}
                    />
                    <button
                      className="cf-btn cf-btn--primary cf-btn--sm"
                      onClick={() => grantCredits(item.uid)}
                      disabled={granting === item.uid}
                    >
                      <Icon name="plus" size={14} />
                      {granting === item.uid ? "Asignando" : "Asignar"}
                    </button>
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
