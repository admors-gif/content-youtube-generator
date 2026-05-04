"use client";
import React, {
  useEffect,
  useState,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { useAuth } from "@/context/AuthContext";
import { db } from "@/lib/firebase";
import { doc, onSnapshot, updateDoc } from "firebase/firestore";
import { SYSTEM_AGENTS } from "@/lib/agents";

import ProjectHeader from "@/components/project/ProjectHeader";
import ProgressPanel from "@/components/project/ProgressPanel";
import VideoPlayer from "@/components/project/VideoPlayer";
import ShortsGrid from "@/components/project/ShortsGrid";
import ThumbnailsGrid from "@/components/project/ThumbnailsGrid";
import ScriptTab from "@/components/project/ScriptTab";
import ScenesTab from "@/components/project/ScenesTab";

/**
 * Project Detail page (container).
 *
 * Fase 7.1 — REFACTOR ESTRUCTURAL:
 *   - computeViralityScore movido a `web/lib/virality.js`
 *   - 11 sub-componentes presentacionales en `web/components/project/`
 *   - Esta página queda como CONTAINER: mantiene 100% los hooks/effects/
 *     callbacks del legacy y delega rendering a los sub-componentes.
 *
 * Hooks preservados (orden idéntico al legacy):
 *   1. React.use(params) → id
 *   2. useAuth → user
 *   3. useState: project, loading, activeTab, editedScript
 *   4. useState: timerActive, timerPaused, timerSeconds
 *   5. useRef: timerRef, autoApproveTriggered
 *   6. useState: displayPercent, startTime, now
 *   7. useState: videoState
 *   8. loadVideoPlayer, copyVideoUrl (fns sin hook)
 *   9. useEffect: track startTime
 *  10. useEffect: now tick (1s mientras hay producción)
 *  11. useEffect: smooth interpolation displayPercent
 *  12. useMemo: eta
 *  13. useEffect: onSnapshot Firebase
 *  14. useEffect: auto-approve start cuando script_ready
 *  15. useCallback: executeApproval (con override moderation 403 → window.confirm)
 *  16. useEffect: countdown timer
 *
 * Fase 7.2 reemplazará el visual de los sub-componentes por cf-* + iconos.
 */

const AUTO_APPROVE_SECONDS = 180; // 3 minutes

export default function ProjectDetailsPage({ params }) {
  const resolvedParams = React.use(params);
  const { id } = resolvedParams;
  const { user } = useAuth();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("script");
  const [editedScript, setEditedScript] = useState("");

  // Auto-approve timer
  const [timerActive, setTimerActive] = useState(false);
  const [timerPaused, setTimerPaused] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(AUTO_APPROVE_SECONDS);
  const timerRef = useRef(null);
  const autoApproveTriggered = useRef(false);

  // Smooth Progress Bar State
  const [displayPercent, setDisplayPercent] = useState(0);
  const [startTime, setStartTime] = useState(null);
  // 'now' tick — evita Date.now() durante render (impure function rule)
  const [now, setNow] = useState(() => Date.now());

  // Inline video player state
  const [videoState, setVideoState] = useState({
    url: null,
    loading: false,
    error: null,
  });

  const loadVideoPlayer = async () => {
    setVideoState({ url: null, loading: true, error: null });
    const vpsBase =
      process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
    try {
      const res = await fetch(
        `${vpsBase}/video-url/${encodeURIComponent(id)}`,
      );
      const data = await res.json();
      if (data.url) {
        const finalUrl = data.url.startsWith("http")
          ? data.url
          : `${vpsBase}${data.url}`;
        setVideoState({ url: finalUrl, loading: false, error: null });
      } else {
        setVideoState({
          url: null,
          loading: false,
          error: data.error || "URL no disponible",
        });
      }
    } catch (err) {
      setVideoState({ url: null, loading: false, error: err.message });
    }
  };

  const copyVideoUrl = async () => {
    if (!videoState.url) return;
    try {
      await navigator.clipboard.writeText(videoState.url);
    } catch {
      // Silent fail; copy is nice-to-have
    }
  };

  // Track when generation starts.
  // Lint disable explícito documentado: el setState dentro de useEffect es
  // legítimo aquí porque (a) usamos functional setter idempotente y
  // (b) startTime no está en deps. La alternativa con useRef genera otro lint
  // error ("read ref in render") al usarlo en getETA.
  useEffect(() => {
    const percent = project?.progress?.percent || 0;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStartTime((prev) => {
      if (percent > 0 && percent < 100) return prev ?? Date.now();
      if (percent >= 100 || project?.status === "error")
        return prev === null ? prev : null;
      return prev;
    });
  }, [project?.progress?.percent, project?.status]);

  // Mantiene 'now' actualizado cada segundo mientras hay producción activa
  useEffect(() => {
    if (!startTime) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, [startTime]);

  // Smooth interpolation: setState dentro de setInterval (asíncrono),
  // no en body del effect → satisface la regla de React 19.
  useEffect(() => {
    const realPercent = project?.progress?.percent || 0;
    const interval = setInterval(() => {
      setDisplayPercent((prev) => {
        if (realPercent >= 100 || realPercent === 0) return realPercent;
        if (realPercent > prev + 5) return realPercent - 2;
        if (prev >= realPercent - 0.5) return prev;
        return prev + 0.3;
      });
    }, 600);
    return () => clearInterval(interval);
  }, [project?.progress?.percent]);

  // ETA derivada — useMemo evita recálculos
  const eta = useMemo(() => {
    if (!startTime || displayPercent >= 100 || displayPercent === 0)
      return null;
    const elapsed = (now - startTime) / 1000;
    const rate = displayPercent / elapsed;
    if (rate <= 0) return null;
    const remaining = (100 - displayPercent) / rate;
    const mins = Math.floor(remaining / 60);
    const secs = Math.floor(remaining % 60);
    if (mins > 15) return null;
    return mins > 0 ? `~${mins}m ${secs}s restantes` : `~${secs}s restantes`;
  }, [now, displayPercent, startTime]);

  // Firebase realtime listener
  useEffect(() => {
    if (!user || !id) return;
    const unsub = onSnapshot(doc(db, "projects", id), (docSnap) => {
      if (docSnap.exists()) {
        const data = docSnap.data();
        setProject(data);
        if (data.script?.plain) {
          // Functional setter: solo escribe si el editor local está vacío
          // (evita sobrescribir cambios del usuario sin meter editedScript en deps)
          setEditedScript((prev) => prev || data.script.plain);
        }
      }
      setLoading(false);
    });
    return () => unsub();
  }, [user, id]);

  // Auto-approve: start timer when script is ready
  useEffect(() => {
    if (
      project?.script?.plain &&
      project?.status === "script_ready" &&
      !project?.script?.approved &&
      !autoApproveTriggered.current
    ) {
      setTimerActive(true);
      setTimerPaused(false);
      setTimerSeconds(AUTO_APPROVE_SECONDS);
    } else {
      setTimerActive(false);
    }
  }, [project?.script?.plain, project?.status, project?.script?.approved]);

  // Core approval logic (manual + auto). Acepta override para 403 moderación.
  const executeApproval = useCallback(
    async ({ overrideModeration = false } = {}) => {
      try {
        setTimerActive(false);
        await updateDoc(doc(db, "projects", id), {
          "script.plain": editedScript,
          "script.approved": true,
          status: "producing",
          "progress.percent": 2,
          "progress.stepName": "Iniciando producción...",
        });
        const vpsUrl =
          process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
        try {
          const res = await fetch(`${vpsUrl}/produce`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ projectId: id, overrideModeration }),
          });
          if (res.status === 403) {
            const data = await res.json().catch(() => ({}));
            const items = (data.critical_blocks || [])
              .map(
                (b) => `  • ${b.category}: ${(b.score * 100).toFixed(0)}%`,
              )
              .join("\n");
            const confirmed = window.confirm(
              "⚠️ El análisis de contenido detectó material que puede afectar la monetización o violar políticas:\n\n" +
                items +
                "\n\n¿Quieres continuar de todos modos? (Asumes la responsabilidad de revisar el resultado antes de publicar)",
            );
            if (confirmed) {
              await fetch(`${vpsUrl}/produce`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  projectId: id,
                  overrideModeration: true,
                }),
              });
            } else {
              await updateDoc(doc(db, "projects", id), {
                "script.approved": false,
                status: "script_ready",
                "progress.percent": 0,
                "progress.stepName":
                  "Revisión pendiente — edita el guión y vuelve a aprobar",
              });
            }
          }
        } catch (fetchErr) {
          console.error("Error contactando servidor:", fetchErr);
        }
      } catch (e) {
        alert("Error: " + e.message);
      }
    },
    [id, editedScript],
  );

  // Countdown timer
  useEffect(() => {
    if (!timerActive || timerPaused) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => {
      setTimerSeconds((prev) => {
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
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
          font: "var(--t-mono-sm)",
          color: "var(--paper-mute)",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        ENTRANDO AL ESTUDIO
      </div>
    );
  }

  if (!project) {
    return (
      <div
        className="cf-card"
        style={{
          padding: "var(--s-7)",
          textAlign: "center",
          color: "var(--paper-dim)",
        }}
      >
        <div
          style={{
            font: "var(--t-mono-sm)",
            color: "var(--paper-mute)",
            marginBottom: 8,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          PROYECTO NO ENCONTRADO
        </div>
        <div>Verifica el enlace o vuelve al dashboard.</div>
      </div>
    );
  }

  const agent = SYSTEM_AGENTS.find((a) => a.agentId === project.agentId);
  const isProcessing =
    project.progress?.percent > 0 &&
    project.progress?.percent < 100 &&
    project.status !== "error";

  // Manual approve handler — desactiva el auto-approve flag y ejecuta
  const handleSaveScript = async () => {
    autoApproveTriggered.current = true;
    setTimerActive(false);
    await executeApproval();
  };

  // Download video handler — fetch URL firmada y abre en nueva pestaña
  const handleDownloadVideo = async () => {
    const vpsBase =
      process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
    try {
      const res = await fetch(
        `${vpsBase}/video-url/${encodeURIComponent(id)}`,
      );
      const data = await res.json();
      if (data.url) {
        const finalUrl = data.url.startsWith("http")
          ? data.url
          : `${vpsBase}${data.url}`;
        window.open(finalUrl, "_blank", "noopener,noreferrer");
      } else {
        alert(`No se pudo obtener el enlace: ${data.error || "desconocido"}`);
      }
    } catch (err) {
      alert(`Error al obtener el enlace: ${err.message}`);
    }
  };

  const TABS = [
    { id: "script", label: "Guión y voz" },
    { id: "scenes", label: "Escenas" },
  ];

  return (
    <div style={{ paddingBottom: "var(--s-7)" }}>
      <ProjectHeader
        project={project}
        agent={agent}
        id={id}
        onDownloadVideo={handleDownloadVideo}
      />

      {/* Live progress: solo cuando isProcessing */}
      {isProcessing && (
        <div
          className="cf-fade cf-fade--1"
          style={{ marginBottom: "var(--s-6)" }}
        >
          <ProgressPanel
            displayPercent={displayPercent}
            stepName={project.progress?.stepName}
            eta={eta}
            status={project.status}
            scenes={project.scenes}
          />
        </div>
      )}

      {project.status === "completed" && (
        <VideoPlayer
          project={project}
          videoState={videoState}
          onLoad={loadVideoPlayer}
          onCopyUrl={copyVideoUrl}
        />
      )}

      {project.status === "completed" && (
        <ShortsGrid shorts={project.shorts} />
      )}

      {project.status === "completed" && (
        <ThumbnailsGrid thumbnails={project.thumbnails} />
      )}

      {/* Tabs editorial */}
      <div
        style={{
          display: "flex",
          gap: 4,
          borderBottom: "1px solid var(--rule-1)",
          marginBottom: "var(--s-5)",
        }}
      >
        {TABS.map((t) => {
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                all: "unset",
                cursor: "pointer",
                padding: "12px 20px",
                fontSize: 15,
                fontWeight: active ? 600 : 400,
                color: active ? "var(--paper)" : "var(--paper-dim)",
                borderBottom: `2px solid ${active ? "var(--ember)" : "transparent"}`,
                marginBottom: -1,
                transition: "all var(--dur-base) var(--ease-out)",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="cf-fade cf-fade--2">
        {activeTab === "script" && (
          <ScriptTab
            project={project}
            editedScript={editedScript}
            setEditedScript={setEditedScript}
            timerActive={timerActive}
            timerSeconds={timerSeconds}
            timerPaused={timerPaused}
            setTimerPaused={setTimerPaused}
            autoApproveSeconds={AUTO_APPROVE_SECONDS}
            onApprove={handleSaveScript}
          />
        )}
        {activeTab === "scenes" && <ScenesTab project={project} />}
      </div>
    </div>
  );
}
