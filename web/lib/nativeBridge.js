export async function setupNativeBridge() {
  if (typeof window === "undefined") return null;
  const { Capacitor } = await import("@capacitor/core").catch(() => ({ Capacitor: null }));
  if (!Capacitor?.isNativePlatform?.()) return null;

  const { App } = await import("@capacitor/app");
  const handle = await App.addListener("appUrlOpen", (event) => {
    const rawUrl = event?.url || "";
    if (!rawUrl) return;
    try {
      const url = new URL(rawUrl);
      if (url.protocol === "contentfactory:" && url.hostname === "project" && url.pathname) {
        window.location.href = `/dashboard/project/${url.pathname.replace("/", "")}`;
        return;
      }
      if (url.protocol === "contentfactory:" && url.hostname === "dashboard") {
        window.location.href = "/dashboard";
        return;
      }
      if (url.hostname === "content-youtube-generator.vercel.app") {
        window.location.href = `${url.pathname}${url.search}${url.hash}`;
      }
    } catch {
      // Ignore invalid deep links.
    }
  });
  return handle;
}
