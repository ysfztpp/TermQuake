import { fold } from "./fold";
import type { Entry, Filter } from "./types";

export interface IndexedTerm {
  entry: Entry;
  lang: string;
  text: string;
  key: string;
  primary: boolean;
}

export interface Hit {
  entry: Entry;
  score: number;
  lang: string;
  text: string;
}

/** Fold every term once at load time (a few thousand strings: milliseconds). */
export function buildIndex(entries: Entry[]): IndexedTerm[] {
  const index: IndexedTerm[] = [];
  for (const entry of entries) {
    for (const [lang, terms] of Object.entries(entry.t)) {
      terms.forEach((text, i) => index.push({ entry, lang, text, key: fold(text), primary: i === 0 }));
    }
  }
  return index;
}

export function matchesFilter(entry: Entry, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "phrases") return entry.p === 1;
  return entry.d === filter;
}

/**
 * Score one term against a folded query.
 *   100 exact   80 starts with   60 a word starts with   30 contains (3+ chars)
 */
export function scoreTerm(key: string, q: string): number {
  if (!q || !key) return 0;
  if (key === q) return 100;
  if (key.startsWith(q)) return 80;
  if ((" " + key).includes(" " + q)) return 60;
  if (q.length >= 3 && key.includes(q)) return 30;
  return 0;
}

export interface SearchOptions {
  /** Languages to search in (normally the selected pair). */
  langs: string[];
  /** Matches in this language rank slightly higher (the "from" language). */
  preferLang: string;
  filter: Filter;
  limit?: number;
}

export function search(index: IndexedTerm[], query: string, opts: SearchOptions): Hit[] {
  const q = fold(query);
  if (!q) return [];
  const best = new Map<number, Hit>();
  for (const term of index) {
    if (!opts.langs.includes(term.lang) || !matchesFilter(term.entry, opts.filter)) continue;
    const base = scoreTerm(term.key, q);
    if (!base) continue;
    const score = base + (term.lang === opts.preferLang ? 4 : 0) + (term.primary ? 2 : 0);
    const current = best.get(term.entry.id);
    if (!current || score > current.score) {
      best.set(term.entry.id, { entry: term.entry, score, lang: term.lang, text: term.text });
    }
  }
  return [...best.values()]
    .sort((a, b) => b.score - a.score || a.text.length - b.text.length || a.entry.id - b.entry.id)
    .slice(0, opts.limit ?? 200);
}

/** Alphabetical browse list for an empty search, sorted by the "from" language. */
export function browse(entries: Entry[], lang: string, filter: Filter): Entry[] {
  // ignorePunctuation: "(sudden) cardiac arrest" sorts under S, "...yı hareket" under Y.
  const collator = new Intl.Collator(lang, { sensitivity: "base", ignorePunctuation: true });
  const label = (e: Entry) => e.t[lang]?.[0];
  return entries
    .filter((e) => matchesFilter(e, filter))
    .sort((a, b) => {
      const la = label(a);
      const lb = label(b);
      if (la && lb) return collator.compare(la, lb) || a.id - b.id;
      if (la) return -1;
      if (lb) return 1;
      return a.id - b.id;
    });
}

/** First letter used for the A–Z group headings in the browse list. */
export function initial(text: string | undefined, lang: string): string {
  if (!text) return "#";
  const first = [...text.replace(/^[^\p{L}\p{N}]+/u, "")][0] ?? "#";
  return /\p{N}/u.test(first) ? "#" : first.toLocaleUpperCase(lang);
}
