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
      },
    },
  },
});
