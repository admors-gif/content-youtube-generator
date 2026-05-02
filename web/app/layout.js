import "./globals.css";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/context/AuthContext";

// next/font self-hostea Inter, evita FOUT y request externo en runtime.
// Reemplaza el <link> manual a fonts.googleapis.com (next/font/google
// es la forma blessed por Next 13+).
const inter = Inter({
  weight: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: "Content Factory — Documentales con IA",
  description: "Crea documentales cinematográficos de YouTube automatizados con inteligencia artificial. Decenas de agentes especializados, narración profesional, y video listo para publicar.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es" className={inter.className}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
