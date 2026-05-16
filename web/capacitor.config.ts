import type { CapacitorConfig } from "@capacitor/cli";

const productionUrl = process.env.CAPACITOR_SERVER_URL || "https://content-youtube-generator.vercel.app";
const bundledMode = process.env.CAPACITOR_BUNDLED === "true";

const config: CapacitorConfig = {
  appId: "com.valtyk.contentfactory",
  appName: "Content Factory",
  webDir: "mobile-shell",
  bundledWebRuntime: false,
  ...(bundledMode
    ? {}
    : {
        server: {
          url: productionUrl,
          cleartext: false,
          androidScheme: "https",
        },
      }),
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: "#0B0B0E",
      androidSplashResourceName: "splash",
      androidScaleType: "CENTER_CROP",
      showSpinner: false,
    },
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
    CapacitorHttp: {
      enabled: false,
    },
  },
  ios: {
    scheme: "ContentFactory",
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false,
  },
};

export default config;
