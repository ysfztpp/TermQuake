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
  /** Domain code ("expressions" for phrases and sentences). Absent when the sheet had none. */
  d?: string;
  /** Definitions by language: text and optional source. */
  def?: Record<string, { x: string; s?: string }>;
}

/** "all", or a domain code. */
export type Filter = "all" | string;
