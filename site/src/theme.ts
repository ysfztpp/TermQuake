/**
 * Colour theme: follow the device ("auto"), or always light or always dark.
 * The choice is an attribute on <html>; styles.css reads it. Applied before the
 * first render (main.tsx) so the page never flashes the wrong colours.
 */
export type Theme = "auto" | "light" | "dark";

export const THEMES: Theme[] = ["auto", "light", "dark"];

const BAR = { light: "#ffffff", dark: "#0e1417" }; // same as the header background

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "auto") delete root.dataset.theme;
  else root.dataset.theme = theme;
  // The browser bar colour (phones) follows the theme too.
  for (const meta of document.querySelectorAll<HTMLMetaElement>(
    'meta[name="theme-color"]',
  )) {
    const scheme = meta.media.includes("dark") ? "dark" : "light";
    meta.content = BAR[theme === "auto" ? scheme : theme];
  }
}

export function asTheme(value: unknown): Theme {
  return value === "light" || value === "dark" ? value : "auto";
}
