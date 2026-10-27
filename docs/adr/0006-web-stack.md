# 0006. Preact + TypeScript + Vite, Atkinson Hyperlegible

**Status:** accepted, October 2026

## Context
The app must load fast on weak connections, be easy for future student
developers to work on, and be readable under stress, outdoors, at arm's length.

## Decision
- Preact 10 (React's API in ~4 KB) with TypeScript, built by Vite;
  vite-plugin-pwa (Workbox) for offline support. Preact 11 was weeks old at
  the time; we chose the mature line.
- Typeface: Atkinson Hyperlegible Next, designed for low-vision legibility
  (clear I/l/1, i/ı). Self-hosted, Turkish and Spanish glyphs included.
- One quiet layout and one bold element: "Show full screen" puts a term in very
  large type for showing the phone to someone, and keeps the screen awake.
- Interface in Turkish, English and Spanish; language pair remembered on the device.

## Consequences
- About 15 KB of gzipped JavaScript; the whole app plus data precaches in under 200 KB.
- Anyone who knows React can contribute.
