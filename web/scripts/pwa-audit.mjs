import { existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const checks = [
  "app/manifest.js",
  "app/sw.js/route.js",
  "app/offline/page.js",
  "public/icons/icon-192.png",
  "public/icons/icon-512.png",
  "public/icons/icon-512-maskable.png",
  "public/icons/apple-touch-icon.png",
  "public/screenshots/pwa-mobile.png",
  "public/screenshots/pwa-wide.png",
];

let ok = true;
for (const file of checks) {
  const full = join(root, file);
  const present = existsSync(full);
  const size = present ? statSync(full).size : 0;
  const valid = present && size > 0;
  ok = ok && valid;
  console.log(`${valid ? "OK" : "MISSING"} ${file}${present ? ` (${size} bytes)` : ""}`);
}

if (!ok) {
  process.exitCode = 1;
}
