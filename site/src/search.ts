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
  return filter === "all" || entry.d === filter;
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
  /** Also find terms in languages outside the pair (ranked below the pair's own matches). */
  allLangs?: boolean;
}

export function search(index: IndexedTerm[], query: string, opts: SearchOptions): Hit[] {
  const q = fold(query);
  if (!q) return [];
  const best = new Map<number, Hit>();
  for (const term of index) {
    const inPair = opts.langs.includes(term.lang);
    if ((!inPair && !opts.allLangs) || !matchesFilter(term.entry, opts.filter)) continue;
    const base = scoreTerm(term.key, q);
    if (!base) continue;
    const score =
      base + (inPair ? 0 : -25) + (term.lang === opts.preferLang ? 4 : 0) + (term.primary ? 2 : 0);
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

/** Edit distance between two strings, stopping early once it exceeds `max`. */
export function distance(a: string, b: string, max: number): number {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const row = [i];
    let best = i;
    for (let j = 1; j <= b.length; j++) {
      const v = Math.min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      row.push(v);
      if (v < best) best = v;
    }
    if (best > max) return max + 1;
    prev = row;
  }
  return prev[b.length];
}

/** "Did you mean": terms within one or two typos of the query, closest first. */
export function suggest(index: IndexedTerm[], query: string, langs: string[], max = 3): string[] {
  const q = fold(query);
  if (q.length < 3) return [];
  const limit = q.length <= 5 ? 1 : 2;
  const found = new Map<string, number>();
  for (const term of index) {
    if (!langs.includes(term.lang)) continue;
    for (const word of term.key.includes(" ") ? [term.key, ...term.key.split(" ")] : [term.key]) {
      const d = distance(word, q, limit);
      if (d <= limit) {
        const label = word === term.key ? term.text : word;
        if (d < (found.get(label) ?? 99)) found.set(label, d);
        break;
      }
    }
  }
  return [...found]
    .sort((a, b) => a[1] - b[1] || a[0].length - b[0].length)
    .slice(0, max)
    .map(([text]) => text);
}

/** The entries without AI suggestions (for people who want human-written terms only). */
export function withoutAi(entries: Entry[]): Entry[] {
  return entries.map((e) => {
    if (!e.m && !e.def) return e;
    const t: Entry["t"] = {};
    const m: NonNullable<Entry["m"]> = {};
    for (const [lang, terms] of Object.entries(e.t)) {
      const meta = e.m?.[lang];
      const keep = terms.map((_, i) => !meta?.[i]?.ai);
      const kept = terms.filter((_, i) => keep[i]);
      if (kept.length === 0) continue;
      t[lang] = kept;
      if (meta) m[lang] = meta.filter((_, i) => keep[i]);
    }
    const def = e.def
      ? Object.fromEntries(Object.entries(e.def).filter(([, d]) => !d.ai))
      : undefined;
    return { ...e, t, m, def: def && Object.keys(def).length ? def : undefined };
  });
}
