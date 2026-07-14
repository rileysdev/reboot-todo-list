import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Stock single-page Vite config. The SPA talks to the Reboot backend
// directly via the URL passed to RebootClientProvider (see main.tsx).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@api": path.resolve(__dirname, "./src/api"),
    },
    dedupe: ["react", "react-dom", "zod"],
  },
  server: {
    port: 5273,
    host: true,
    strictPort: true,
    // Proxy all Reboot traffic (RPC + reader/mutation WebSockets) to the
    // backend through this same origin. This keeps the browser talking only
    // to the origin it loaded from — essential when the SPA is reached over
    // a forwarded/tunneled host (e.g. GitHub Codespaces `*.app.github.dev`),
    // where a hardcoded `localhost:9992` would resolve to the user's own
    // machine. `ws: true` forwards the WebSocket upgrades mutations ride on.
    proxy: {
      "/__/reboot": {
        target: "http://localhost:9992",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
