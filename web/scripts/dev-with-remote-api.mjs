import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const server = spawn(
  process.execPath,
  [require.resolve("next/dist/bin/next"), "dev", ...process.argv.slice(2)],
  {
    stdio: "inherit",
    windowsHide: true,
    env: { ...process.env, NEXT_PUBLIC_VPS_API_URL: "https://api.valtyk.com" },
  },
);

server.on("error", (error) => {
  console.error("No se pudo iniciar Content Factory:", error.message);
  process.exitCode = 1;
});
server.on("exit", (code) => {
  process.exitCode = code ?? 1;
});
