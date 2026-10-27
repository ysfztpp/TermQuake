import preact from "@preact/preset-vite";
import { defineConfig, type Plugin } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// GitHub Pages serves the site from /<repo>/; the deploy workflow sets BASE_PATH.
const base = process.env.BASE_PATH ?? "/";

// Strict Content-Security-Policy, added to the built page only (Vite's dev
// server needs inline scripts). Everything is self-hosted, so nothing else is allowed.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "manifest-src 'self'",
  "worker-src 'self'",
  "base-uri 'self'",
  "form-action 'none'",
  "object-src 'none'",
].join("; ");

function contentSecurityPolicy(): Plugin {
  return {
    name: "termquake-csp",
    apply: "build",
    transformIndexHtml: (html) =>
      html.replace(
        "<meta charset=\"UTF-8\" />",
        `<meta charset="UTF-8" />\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`,
      ),
  };
}

export default defineConfig({
  base,
  plugins: [
    preact(),
    contentSecurityPolicy(),
    VitePWA({
      // Ask before swapping in a new version, so nobody is reloaded mid-lookup.
      registerType: "prompt",
      injectRegister: false,
      includeAssets: ["favicon.svg", "icons/apple-touch-icon.png"],
      manifest: {
        name: "TermQuake: disaster relief terminology",
        short_name: "TermQuake",
        description:
          "Offline search-and-rescue and disaster-relief terms in English, Turkish and Spanish.",
        lang: "en",
        start_url: ".",
        scope: ".",
        display: "standalone",
        orientation: "portrait",
        background_color: "#F5F7F6",
        theme_color: "#172026",
        categories: ["education", "medical", "reference", "utilities"],
        icons: [
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Precache the whole app and its data on first visit: after that it
        // works with no connection at all. Downloads are fetched on demand.
        globPatterns: ["**/*.{html,js,css,woff2,svg,png,json,webmanifest}"],
        globIgnores: ["downloads/**"],
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        cleanupOutdatedCaches: true,
        navigateFallback: "index.html",
      },
    }),
  ],
  build: {
    target: "es2020",
    sourcemap: true,
  },
});
