import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

/** Kernel demo UI root (`vidhubijakam-demo/standalone/`) */
const standaloneRoot = path.dirname(fileURLToPath(import.meta.url));
/** `vidhubijakam-demo/` — Vite envDir (`.env` for ECAD_API_PORT / keys) */
const repoRoot = path.resolve(standaloneRoot, "..");

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, "");
  const apiPort = env.ECAD_API_PORT ?? env.VITE_PROXY_API_PORT ?? "8000";
  /** Same as main SPA: repo-root `.env` for local dev (never commit real keys). */
  const deepSeek = env.DEEP_SEEK_API_KEY ?? "";

  return {
    root: standaloneRoot,
    envDir: repoRoot,
    publicDir: false,
    plugins: [react()],
    define: {
      "import.meta.env.VITE_DEFAULT_DEEP_SEEK_API_KEY": JSON.stringify(deepSeek),
    },
    server: {
      host: "127.0.0.1",
      port: 5180,
      strictPort: true,
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: path.join(standaloneRoot, "dist-kernel"),
      emptyOutDir: true,
    },
  };
});
