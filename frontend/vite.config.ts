import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend always calls the backend with same-origin relative URLs; the Vite
// server rewrites them to the FastAPI process. `CF_BACKEND_URL` retargets that
// hop so the end-to-end suite can serve a production build against its own
// throwaway backend without the app knowing which one it is talking to.
const backendUrl = process.env.CF_BACKEND_URL ?? "http://localhost:8000";

const proxy = {
  "/api": { target: backendUrl, changeOrigin: true },
  "/health": { target: backendUrl, changeOrigin: true },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  // `vite preview` serves the real build output. The e2e suite drives this, so
  // the same proxy has to exist here and not only on the dev server.
  preview: { port: 4173, proxy },
});
