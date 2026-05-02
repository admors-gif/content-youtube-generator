/** @type {import('next').NextConfig} */
const nextConfig = {
  reactCompiler: true,
  images: {
    // Whitelist de dominios desde donde Next.js Image puede optimizar imágenes.
    // Ampliar cuando agreguemos más fuentes de imagen.
    remotePatterns: [
      { protocol: "https", hostname: "api.valtyk.com" },
      { protocol: "https", hostname: "storage.googleapis.com" },
      { protocol: "https", hostname: "**.firebasestorage.app" },
      { protocol: "https", hostname: "**.googleusercontent.com" },
      { protocol: "https", hostname: "i.ibb.co" },
      { protocol: "https", hostname: "*.lumalabs.ai" },
    ],
  },
};

export default nextConfig;
