const FIREBASE_CONFIG = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
};

function swSource() {
  return `
const CACHE_NAME = "content-factory-shell-v1";
const OFFLINE_URL = "/offline";
const STATIC_ASSETS = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-512-maskable.png",
  "/icons/apple-touch-icon.png"
];
const FIREBASE_CONFIG = ${JSON.stringify(FIREBASE_CONFIG)};

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function isSensitiveRequest(request) {
  const url = new URL(request.url);
  if (request.method !== "GET") return true;
  if (url.pathname.startsWith("/api/download")) return true;
  if (url.pathname.includes("/download/")) return true;
  if (url.pathname.endsWith(".mp4") || url.pathname.endsWith(".zip") || url.pathname.endsWith(".mp3")) return true;
  if (url.hostname.includes("api.valtyk.com")) return true;
  if (url.hostname.includes("firestore.googleapis.com")) return true;
  if (url.hostname.includes("firebasestorage")) return true;
  if (request.headers.has("authorization")) return true;
  return false;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (isSensitiveRequest(request)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        const copy = response.clone();
        if (response.ok && ["style", "script", "font", "image"].includes(request.destination)) {
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});

if (FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.messagingSenderId) {
  try {
    importScripts("https://www.gstatic.com/firebasejs/12.12.1/firebase-app-compat.js");
    importScripts("https://www.gstatic.com/firebasejs/12.12.1/firebase-messaging-compat.js");
    firebase.initializeApp(FIREBASE_CONFIG);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage((payload) => {
      const title = payload.notification?.title || payload.data?.title || "Content Factory";
      const body = payload.notification?.body || payload.data?.body || "Hay una actualización en tu estudio.";
      const url = payload.data?.url || "/dashboard";
      self.registration.showNotification(title, {
        body,
        icon: "/icons/icon-192.png",
        badge: "/icons/icon-192.png",
        data: { url },
      });
    });
  } catch (error) {
    console.warn("Firebase Messaging no disponible en service worker", error);
  }
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/dashboard";
  event.waitUntil(self.clients.openWindow(url));
});
`;
}

export function GET() {
  return new Response(swSource(), {
    headers: {
      "Content-Type": "application/javascript; charset=utf-8",
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Service-Worker-Allowed": "/",
    },
  });
}
