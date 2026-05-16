export default function manifest() {
  return {
    name: "Content Factory",
    short_name: "Factory",
    description:
      "Crea, monitorea y publica videos con agentes de Content Factory.",
    start_url: "/dashboard?source=pwa",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#0B0B0E",
    theme_color: "#0B0B0E",
    lang: "es-MX",
    categories: ["productivity", "video", "business"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      {
        src: "/icons/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    screenshots: [
      {
        src: "/screenshots/pwa-mobile.png",
        sizes: "750x1334",
        type: "image/png",
        form_factor: "narrow",
      },
      {
        src: "/screenshots/pwa-wide.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
      },
    ],
    shortcuts: [
      {
        name: "Nuevo video",
        short_name: "Nuevo",
        description: "Crear un nuevo proyecto",
        url: "/dashboard/new?source=pwa_shortcut",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
      },
      {
        name: "Publicaciones",
        short_name: "Publicar",
        description: "Revisar publicaciones y pendientes",
        url: "/dashboard/publications?source=pwa_shortcut",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
      },
    ],
  };
}
