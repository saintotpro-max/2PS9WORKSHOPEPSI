import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Servi derrière le WAF sous /dashboard/ ; en développement, les appels /dashboard/api
// sont relayés vers une instance déployée (tunnel SSH vers le WAF par exemple).
export default defineConfig({
  base: "/dashboard/",
  plugins: [react(), tailwindcss()],
  build: { chunkSizeWarningLimit: 800 },   // un seul paquet, servi sur le LAN
  server: {
    proxy: { "/dashboard/api": { target: process.env.API_TARGET || "https://localhost:8443", secure: false } },
  },
});
