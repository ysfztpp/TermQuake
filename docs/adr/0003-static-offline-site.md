# 0003. Static, offline-first web app on GitHub Pages

**Status:** accepted, October 2026

## Context
The article stresses offline access, low connectivity and battery limits in
disaster zones. A site that queries a live database fails exactly when it is
needed most. The existing Firebase app reads the sheet live.

## Decision
Publish a static Progressive Web App on GitHub Pages. All terms ship as one
JSON file; a service worker precaches the app and data on the first visit, so
search works with no connection. Updates are offered, not forced. Dark mode
uses true black for OLED battery savings.

## Consequences
- No server or database for the public tool: nothing to attack, scale or pay for.
- Data size is bounded by what a phone should cache; the JSON is ~60 KB for 3
  languages and will stay well under a few MB for 30.
- The old Firebase app keeps running until the team decides to retire it or
  point its domain here.
