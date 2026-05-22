import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const defaultPreviewAllowedHosts = [
  "app.marspotatolab.com",
  "plantlab-web-418533861080.us-central1.run.app",
  "plantlab-web-efvri7f4ma-uc.a.run.app",
  "candidate---plantlab-web-efvri7f4ma-uc.a.run.app",
];

const previewAllowedHosts = (process.env.PLANTLAB_WEB_ALLOWED_HOSTS ?? "")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
  preview: {
    allowedHosts: previewAllowedHosts.length ? previewAllowedHosts : defaultPreviewAllowedHosts,
  },
});
