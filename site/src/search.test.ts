import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { fold } from "./fold";
import { browse, buildIndex, initial, scoreTerm, search } from "./search";
import type { Entry } from "./types";

const shared = JSON.parse(
  readFileSync(new URL("../../tests/shared/fold_cases.json", import.meta.url), "utf-8"),
) as { cases: [string, string][] };

describe("fold matches the Python pipeline", () => {
  it.each(shared.cases)("%j -> %j", (input, expected) => {
    expect(fold(input)).toBe(expected);
  });
});

const entries: Entry[] = [
  { id: 5, d: "general", t: { en: ["debris", "rubble"], tr: ["enkaz", "moloz"], es: ["escombros"] } },
  { id: 41, d: "first_aid", t: { en: ["bandage"], tr: ["sargı bezi"], es: ["venda"] } },
  { id: 43, d: "first_aid", t: { en: ["elastic bandage"], tr: ["elastik bandaj"], es: ["vendajes elásticos"] } },
  { id: 101, d: "search_rescue", t: { en: ["debris removal"], tr: ["enkaz kaldırma"], es: ["retirada de escombros"] } },
  { id: 154, p: 1, t: { en: ["What happened?"], tr: ["Ne oldu?"], es: ["¿Qué sucedió?"] } },
  { id: 470, d: "search_rescue", t: { tr: ["dolgu zemin"] } },
];
const index = buildIndex(entries);
const opts = { langs: ["en", "tr"], preferLang: "en", filter: "all" };

describe("search", () => {
  it("scores exact > prefix > word prefix > substring", () => {
    expect(scoreTerm("bandage", "bandage")).toBe(100);
    expect(scoreTerm("bandage", "band")).toBe(80);
    expect(scoreTerm("elastic bandage", "band")).toBe(60);
    expect(scoreTerm("bandage", "nda")).toBe(30);
    expect(scoreTerm("bandage", "nd")).toBe(0);
  });

  it("ranks the exact term first", () => {
    const ids = search(index, "bandage", opts).map((h) => h.entry.id);
    expect(ids).toEqual([41, 43]);
  });

  it("finds Turkish typed without a Turkish keyboard", () => {
    const hits = search(index, "sargi", opts);
    expect(hits[0].entry.id).toBe(41);
    expect(hits[0].lang).toBe("tr");
  });

  it("matches synonyms, not only the main term", () => {
    expect(search(index, "rubble", opts)[0].entry.id).toBe(5);
    expect(search(index, "moloz", opts)[0].entry.id).toBe(5);
  });

  it("only searches the selected languages", () => {
    expect(search(index, "escombros", opts)).toEqual([]);
    expect(search(index, "escombros", { ...opts, langs: ["en", "es"] }).map((h) => h.entry.id)).toEqual([5, 101]);
  });

  it("applies the domain and expression filters", () => {
    expect(search(index, "debris", { ...opts, filter: "search_rescue" }).map((h) => h.entry.id)).toEqual([101]);
    expect(search(index, "oldu", { ...opts, filter: "phrases" }).map((h) => h.entry.id)).toEqual([154]);
  });

  it("ignores punctuation and accents in queries", () => {
    expect(search(index, "  WHAT happened ", opts)[0].entry.id).toBe(154);
    expect(search(index, "que sucedio", { ...opts, langs: ["es"] })[0].entry.id).toBe(154);
  });

  it("returns nothing for an empty query", () => {
    expect(search(index, "  ?! ", opts)).toEqual([]);
  });
});

describe("browse", () => {
  it("sorts by the source language and puts entries without a term last", () => {
    const ids = browse(entries, "en", "all").map((e) => e.id);
    expect(ids.slice(0, 2)).toEqual([41, 5]);
    expect(ids.at(-1)).toBe(470);
  });

  it("uses Turkish alphabetical order", () => {
    const tr: Entry[] = [
      { id: 1, t: { tr: ["çadır"] } },
      { id: 2, t: { tr: ["cımbız"] } },
      { id: 3, t: { tr: ["dirsek"] } },
    ];
    expect(browse(tr, "tr", "all").map((e) => e.id)).toEqual([2, 1, 3]);
  });

  it("builds group initials", () => {
    expect(initial("ilk yardım", "tr")).toBe("İ");
    expect(initial("ilk yardım", "en")).toBe("I");
    expect(initial("(sudden) cardiac arrest", "en")).toBe("S");
    expect(initial("112'yi arayın", "tr")).toBe("#");
  });
});
