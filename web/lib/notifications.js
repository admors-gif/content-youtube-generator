import { getApiBase, authedFetch } from "@/lib/apiClient";
import { app } from "@/lib/firebase";

export async function registerAppServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return null;
  }
  return navigator.serviceWorker.register("/sw.js", { scope: "/" });
}

export function isStandaloneApp() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)")?.matches ||
    window.navigator.standalone === true
  );
}

export function isIosSafari() {
  if (typeof window === "undefined") return false;
  const ua = window.navigator.userAgent || "";
  return /iphone|ipad|ipod/i.test(ua) && /safari/i.test(ua) && !/crios|fxios|edgios/i.test(ua);
}

export async function requestProjectNotifications(user) {
  if (typeof window === "undefined") {
    throw new Error("Las notificaciones solo funcionan en el navegador");
  }
  const { Capacitor } = await import("@capacitor/core").catch(() => ({ Capacitor: null }));
  if (Capacitor?.isNativePlatform?.()) {
    const { PushNotifications } = await import("@capacitor/push-notifications");
    const current = await PushNotifications.checkPermissions();
    const permission = current.receive === "granted" ? current : await PushNotifications.requestPermissions();
    if (permission.receive !== "granted") {
      throw new Error("Permiso de notificaciones no concedido");
    }
    const token = await new Promise((resolve, reject) => {
      let settled = false;
      const cleanup = [];
      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        cleanup.forEach((item) => item?.remove?.());
        fn(value);
      };
      PushNotifications.addListener("registration", (registration) => {
        finish(resolve, registration.value);
      }).then((handle) => cleanup.push(handle));
      PushNotifications.addListener("registrationError", (error) => {
        finish(reject, new Error(error.error || "No se pudo registrar el dispositivo"));
      }).then((handle) => cleanup.push(handle));
      PushNotifications.register();
      window.setTimeout(() => finish(reject, new Error("Timeout registrando notificaciones")), 15000);
    });
    const platform = Capacitor.getPlatform?.() || "native";
    const response = await authedFetch(user, `${getApiBase()}/notifications/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        platform: `capacitor-${platform}`,
        userAgent: window.navigator.userAgent || "",
        appVersion: "native-v1",
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.error || "No se pudo registrar el dispositivo");
    }
    return data;
  }

  if (!("Notification" in window)) {
    throw new Error("Este navegador no soporta notificaciones");
  }

  const permission =
    Notification.permission === "granted"
      ? "granted"
      : await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Permiso de notificaciones no concedido");
  }

  const [{ getMessaging, getToken, isSupported }] = await Promise.all([
    import("firebase/messaging"),
  ]);
  if (!(await isSupported())) {
    throw new Error("Firebase Messaging no está soportado en este navegador");
  }

  const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
  if (!vapidKey) {
    throw new Error("NEXT_PUBLIC_FIREBASE_VAPID_KEY no configurado");
  }

  const registration = await registerAppServiceWorker();
  const messaging = getMessaging(app);
  const token = await getToken(messaging, {
    vapidKey,
    serviceWorkerRegistration: registration || undefined,
  });
  if (!token) {
    throw new Error("No se pudo obtener token de notificaciones");
  }

  const platform = isStandaloneApp() ? "pwa" : "web";
  const response = await authedFetch(user, `${getApiBase()}/notifications/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      token,
      platform,
      userAgent: window.navigator.userAgent || "",
      appVersion: "pwa-v1",
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || "No se pudo registrar el dispositivo");
  }
  return data;
}
