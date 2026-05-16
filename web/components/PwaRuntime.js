"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Icon from "@/components/Icon";
import {
  isIosSafari,
  isStandaloneApp,
  registerAppServiceWorker,
  requestProjectNotifications,
} from "@/lib/notifications";
import { setupNativeBridge } from "@/lib/nativeBridge";

const PWA_ENABLED = process.env.NEXT_PUBLIC_PWA_ENABLED !== "false";

export default function PwaRuntime() {
  const { user } = useAuth();
  const [installPrompt, setInstallPrompt] = useState(null);
  const [installed, setInstalled] = useState(() => isStandaloneApp());
  const [dismissed, setDismissed] = useState(false);
  const [notificationState, setNotificationState] = useState(() =>
    typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted"
      ? "enabled"
      : "idle"
  );
  const [message, setMessage] = useState("");

  const ios = useMemo(() => isIosSafari(), []);

  useEffect(() => {
    if (!PWA_ENABLED) return;
    registerAppServiceWorker().catch(() => {});
    let nativeHandle = null;
    setupNativeBridge()
      .then((handle) => {
        nativeHandle = handle;
      })
      .catch(() => {});

    const onBeforeInstallPrompt = (event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
      setMessage("App instalada");
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onInstalled);
      nativeHandle?.remove?.();
    };
  }, []);

  if (!PWA_ENABLED || dismissed) return null;

  const canInstall = !installed && Boolean(installPrompt);
  const showInstallHelp = !installed && ios && !canInstall;
  const showNotifications = Boolean(user) && notificationState !== "enabled";
  if (!canInstall && !showInstallHelp && !showNotifications) return null;

  const handleInstall = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const choice = await installPrompt.userChoice.catch(() => null);
    if (choice?.outcome === "accepted") {
      setMessage("Instalando Content Factory");
    }
    setInstallPrompt(null);
  };

  const handleNotifications = async () => {
    if (!user) return;
    try {
      setNotificationState("loading");
      await requestProjectNotifications(user);
      setNotificationState("enabled");
      setMessage("Avisos de proyectos activados");
    } catch (error) {
      setNotificationState("error");
      setMessage(error.message || "No se pudieron activar los avisos");
    }
  };

  return (
    <div className="cf-pwa-card cf-card" role="status">
      <button
        type="button"
        aria-label="Ocultar opciones de app"
        className="cf-pwa-close"
        onClick={() => setDismissed(true)}
      >
        <Icon name="x" size={14} />
      </button>
      <div className="cf-eyebrow" style={{ color: "var(--ember)" }}>
        APP MOVIL
      </div>
      <div className="cf-pwa-title">Content Factory en tu celular</div>
      {showInstallHelp && (
        <p className="cf-caption" style={{ margin: "8px 0 0" }}>
          En iPhone: abre el menú Compartir de Safari y elige “Agregar a inicio”.
        </p>
      )}
      {message && <p className="cf-caption" style={{ margin: "8px 0 0" }}>{message}</p>}
      <div className="cf-pwa-actions">
        {canInstall && (
          <button type="button" className="cf-btn cf-btn--primary cf-btn--sm" onClick={handleInstall}>
            <Icon name="download" size={15} /> Instalar
          </button>
        )}
        {showNotifications && (
          <button
            type="button"
            className="cf-btn cf-btn--secondary cf-btn--sm"
            onClick={handleNotifications}
            disabled={notificationState === "loading"}
          >
            <Icon name="bell" size={15} />
            {notificationState === "loading" ? "Activando" : "Avisos"}
          </button>
        )}
      </div>
    </div>
  );
}
