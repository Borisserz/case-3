import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
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
