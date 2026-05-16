import "./globals.css";
import { Inter_Tight, Fraunces, JetBrains_Mono } from "next/font/google";
import { AuthProvider } from "@/context/AuthContext";

// Editorial-cinematic typography stack (v2 design system).
// next/font self-hostea + evita FOUT + elimina request externo.
// Las CSS variables se asignan a --font-{display,sans,mono} en globals.css.

const interTight = Inter_Tight({
  weight: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans-loaded",
});

const fraunces = Fraunces({
  // weight: omitido → font variable, soporta cualquier weight 100-900
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  axes: ["opsz"],
  variable: "--font-display-loaded",
});

const jetBrainsMono = JetBrains_Mono({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono-loaded",
});

export const metadata = {
  title: "Content Factory — Documentales con IA",
  description:
    "Crea documentales cinematográficos automatizados con IA. Veintiocho agentes especializados, narración profesional, video listo para YouTube.",
  manifest: "/manifest.webmanifest",
  applicationName: "Content Factory",
  appleWebApp: {
    capable: true,
    title: "Content Factory",
    statusBarStyle: "black-translucent",
  },
  formatDetection: {
    telephone: false,
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  viewportFit: "cover",
  themeColor: "#0B0B0E",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="es"
      className={`${interTight.variable} ${fraunces.variable} ${jetBrainsMono.variable}`}
    >
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
