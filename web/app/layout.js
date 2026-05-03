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
