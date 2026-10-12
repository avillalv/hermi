import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  envDir: "../..",
  plugins: [react(), tailwindcss()],
  // /v1/admin and the fake-Access signer are same-origin for the console (infra/cloudflare/access.md); in dev the proxy stands in for the edge route.
  server: { port: 5173, strictPort: true, proxy: { "/v1/admin": { target: "http://localhost:8100", changeOrigin: false }, "/v1/dev/admin-session": { target: "http://localhost:8100", changeOrigin: false } } },
  test: { exclude: ["e2e/**", "node_modules/**"], environment: "jsdom", setupFiles: ["./src/setup.ts"], css: { include: [/tokens\.css/] } },
});
