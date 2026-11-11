import { type MessageKey, type UiLang, translate } from "../i18n";
import type { Entry, Language } from "../types";

/** Per language: how many entries have a term written by people, and how many only an AI suggestion. */
export function Coverage({ entries, languages, ui }: { entries: Entry[]; languages: Language[]; ui: UiLang }) {
  const t = (key: MessageKey, vars?: Record<string, string | number>) => translate(ui, key, vars);
  const total = entries.length || 1;
  const rows = languages.map((l) => {
    let human = 0;
    let ai = 0;
    for (const e of entries) {
      if (!e.t[l.code]?.length) continue;
      if (e.m?.[l.code]?.[0]?.ai) ai++;
      else human++;
    }
    return { l, human, ai };
  });
  return (
    <details class="coverage">
      <summary>{t("coverage")}</summary>
      <p class="foot-small">{t("coverageHelp")}</p>
      <ul>
        {rows.map(({ l, human, ai }) => (
          <li key={l.code}>
            <span class="cov-name" lang={l.code}>
              {l.native}
            </span>
            <svg class="cov-bar" viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true">
              <rect class="cov-rest" width="100" height="6" />
              <rect class="cov-human" width={(100 * human) / total} height="6" />
              <rect class="cov-ai" x={(100 * human) / total} width={(100 * ai) / total} height="6" />
            </svg>
            <span class="cov-num">
              {human}
              {ai > 0 && <span class="cov-num-ai"> + {ai} AI</span>}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}
