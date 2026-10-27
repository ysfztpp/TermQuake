/**
 * Remembers a person's choices (language pair, interface language, filter) on
 * their own device. Storage can be unavailable (private mode, blocked site
 * data), so every access is guarded and the app works without it.
 */
const KEY = "termquake.prefs.v1";

export interface Prefs {
  from?: string;
  to?: string;
  ui?: string;
  filter?: string;
}

export function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Prefs) : {};
  } catch {
    return {};
  }
}

export function savePrefs(prefs: Prefs): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    /* storage unavailable: preferences simply aren't remembered */
  }
}
