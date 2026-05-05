import { withSentryConfig } from "@sentry/nextjs";

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

const sentryOptions = {
  silent: !process.env.CI,
};

if (process.env.SENTRY_ORG) {
  sentryOptions.org = process.env.SENTRY_ORG;
}

if (process.env.SENTRY_PROJECT) {
  sentryOptions.project = process.env.SENTRY_PROJECT;
}

if (process.env.SENTRY_AUTH_TOKEN) {
  sentryOptions.authToken = process.env.SENTRY_AUTH_TOKEN;
  sentryOptions.widenClientFileUpload = true;
}

export default withSentryConfig(nextConfig, sentryOptions);
