/** Shape of public/data/termbase.json, written by `termquake export`. */
export interface Termbase {
  schema: number;
  data: { version: string; updated: string; pipeline: string; commit: string };
  languages: Language[];
  domains: Domain[];
  entries: Entry[];
}

export interface Language {
  code: string;
  name: string;
  native: string;
  dir: "ltr" | "rtl";
}

export interface Domain {
  code: string;
  label: Record<string, string>;
}

export interface Entry {
  /** Stable id: the sheet's Nr. column. */
  id: number;
  /** Terms by language code; the first one in each list is the main term. */
  t: Record<string, string[]>;
  /** Domain code. Absent for expressions and uncategorised entries. */
  d?: string;
  /** 1 when the entry is an expression (a phrase or sentence), not a term. */
  p?: 1;
  /** Definitions by language: text and optional source. */
  def?: Record<string, { x: string; s?: string }>;
}

/** "phrases" selects expressions; any other value is a domain code. */
export type Filter = "all" | "phrases" | string;
