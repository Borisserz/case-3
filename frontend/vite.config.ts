import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const dayjsEsm = fileURLToPath(new URL("./node_modules/dayjs/esm/", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      // dayjs "main" is the UMD file. Mermaid is left unbundled (below), so the
      // browser imports that file as ESM and dies: no export named "default".
      // Point the bare import and the plugin files at the real ESM build.
      {
        find: /^dayjs\/plugin\/(.+?)(?:\.js)?$/,
        replacement: `${dayjsEsm}plugin/$1/index.js`,
      },
      {
        find: /^dayjs$/,
        replacement: `${dayjsEsm}index.js`,
      },
    ],
  },
  optimizeDeps: {
    // Mermaid loads mindmap/timeline/… with a dynamic import. Prebundling
    // rewrites that to a .vite/deps file the browser cannot fetch, so a
    // scheme on a slide shows «Не удалось отрисовать схему».
    exclude: ["mermaid"],
    // Mermaid stays raw, so its `import dayjs from "dayjs"` is served as-is.
    // dayjs's package entry is UMD and has no default export. Prebundle the
    // ESM entry (aliased above) or every scheme dies before it is drawn.
    include: [
      "dayjs",
      "dayjs/plugin/isoWeek.js",
      "dayjs/plugin/customParseFormat.js",
      "dayjs/plugin/advancedFormat.js",
      "dayjs/plugin/duration.js",
      // Mermaid imports `{ sanitizeUrl }` from this package. Its "main" is CJS,
      // so the raw file has no named ESM export and every scheme fails to draw.
      "@braintree/sanitize-url",
      // UMD builds. A default import of the raw file dies the same way.
      "fastdom",
      "fastdom/extensions/fastdom-promised.js",
      "cytoscape",
      "cytoscape-cose-bilkent",
      "cytoscape-fcose",
    ],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // Local agent: old uvicorn on :8000 may be stuck; prefer :8001 when needed.
        target: process.env.CASE3_API_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
        // Long SSE (/events) must not hit Node's default proxy idle timeout.
        timeout: 0,
        proxyTimeout: 0,
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes, req) => {
            const url = String(req.url || "");
            if (!url.includes("/events") && !url.includes("/summary/stream")) {
              return;
            }
            // Discourage proxy/client buffering of long-lived SSE.
            proxyRes.headers["cache-control"] = "no-cache, no-transform";
            proxyRes.headers["x-accel-buffering"] = "no";
            delete proxyRes.headers["content-length"];
          });
          proxy.on("error", (err, req) => {
            const code =
              err && typeof err === "object" && "code" in err
                ? String((err as { code?: string }).code || "")
                : "";
            const url = String(
              req && typeof req === "object" && "url" in req
                ? (req as { url?: string }).url || ""
                : "",
            );
            // API restart / SSE idle reset — EventSource falls back to poll; not actionable.
            if (
              (code === "ECONNRESET" || code === "EPIPE") &&
              url.includes("/events")
            ) {
              return;
            }
            console.warn(`[vite api proxy] ${code || err.message} ${url}`);
          });
        },
      },
    },
  },
});
