/**
 * Search key: lowercase, accent-free, Turkish i/ı unified, punctuation removed.
 * "SARGI BEZİ", "sargı bezi" and "sargi bezi" all become "sargi bezi", so people
 * can search without a Turkish keyboard. Tested against fold.cases.json.
 */

// Below U+0800 (Latin, Greek, Cyrillic, Armenian, Hebrew, Arabic) combining
// marks are accents or vowel points and are ignored. In Indic, Japanese etc.
// they are part of the letter and are kept.
const ACCENT_SCRIPTS_END = 0x0800;
const NONSPACING_MARK = /\p{Mn}/u;
const FORMAT_CHARS = /\p{Cf}/gu;
const NON_WORD = /[^\p{L}\p{N}\p{M}]+/gu;
const SPACES = /\s+/g;

export function fold(text: string): string {
  let stripped = "";
  let base = 0;
  // Format characters (ZWNJ, ZWJ, ...) are dropped, not turned into spaces, so
  // Persian "مراقبت‌های" (with ZWNJ) and "مراقبتهای" (typed without it) match.
  for (const ch of text.normalize("NFKD").replace(FORMAT_CHARS, "")) {
    if (NONSPACING_MARK.test(ch)) {
      if (base < ACCENT_SCRIPTS_END) continue;
    } else {
      base = ch.codePointAt(0) ?? 0;
    }
    stripped += ch;
  }
  return stripped
    .replace(/ı/g, "i")
    .toLowerCase()
    .replace(/ß/g, "ss")
    .replace(/ς/g, "σ")
    .replace(NON_WORD, " ")
    .replace(SPACES, " ")
    .trim()
    .normalize("NFC");
}
