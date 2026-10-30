import { useState } from "preact/hooks";
import { type UiLang, translate } from "../i18n";
import type { Domain, Entry, Language } from "../types";
import { CheckIcon, CopyIcon, ExpandIcon } from "./icons";

const REPO = "https://github.com/ysfztpp/TermQuake";

interface Props {
  entry: Entry;
  from: Language;
  to: Language;
  languages: Language[];
  domains: Domain[];
  ui: UiLang;
  open: boolean;
  onToggle: (id: number) => void;
  onShow: (id: number) => void;
}

export function EntryRow({ entry, from, to, languages, domains, ui, open, onToggle, onShow }: Props) {
  const t = (key: Parameters<typeof translate>[1], vars?: Record<string, string | number>) =>
    translate(ui, key, vars);
  const src = entry.t[from.code] ?? [];
  const tgt = entry.t[to.code] ?? [];
  const domain = domains.find((d) => d.code === entry.d);
  const panelId = `entry-${entry.id}`;

  return (
    <li class={open ? "row is-open" : "row"} data-domain={entry.d ?? "none"}>
      <button
        type="button"
        class="row-head"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => onToggle(entry.id)}
      >
        <span class="row-src" lang={from.code} dir={from.dir}>
          {src.length ? (
            <>
              <strong>{src[0]}</strong>
              {src.length > 1 && <span class="row-syn"> / {src.slice(1).join(" / ")}</span>}
            </>
          ) : (
            <span class="row-missing">{t("missing", { lang: from.native })}</span>
          )}
        </span>
        <span class="row-tgt" lang={to.code} dir={to.dir}>
          {tgt.length ? (
            <>
              <span class="row-tgt-main">{tgt[0]}</span>
              {tgt.length > 1 && <span class="row-syn"> / {tgt.slice(1).join(" / ")}</span>}
            </>
          ) : (
            <span class="row-missing">{t("missing", { lang: to.native })}</span>
          )}
        </span>
        {domain && <span class="row-domain">{domain.label[ui] ?? domain.label.en}</span>}
      </button>
      {open && (
        <Detail entry={entry} order={orderLanguages(languages, from, to)} ui={ui} id={panelId} onShow={onShow} to={to} />
      )}
    </li>
  );
}

function orderLanguages(languages: Language[], from: Language, to: Language): Language[] {
  return [from, to, ...languages.filter((l) => l.code !== from.code && l.code !== to.code)];
}

function Detail({ entry, order, ui, id, onShow, to }: {
  entry: Entry;
  order: Language[];
  ui: UiLang;
  id: string;
  onShow: (id: number) => void;
  to: Language;
}) {
  const [copied, setCopied] = useState(false);
  const t = (key: Parameters<typeof translate>[1], vars?: Record<string, string | number>) =>
    translate(ui, key, vars);
  const target = entry.t[to.code] ?? [];
  const reportTitle = `Entry ${entry.id}: ${entry.t.en?.[0] ?? entry.t.tr?.[0] ?? ""}`;
  const reportUrl = `${REPO}/issues/new?template=term-correction.yml&entry=${entry.id}&title=${encodeURIComponent(reportTitle)}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(target.join(" / "));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard blocked: nothing to do */
    }
  };

  return (
    <div class="detail" id={id}>
      <dl class="detail-langs">
        {order.map((lang) => {
          const terms = entry.t[lang.code] ?? [];
          const def = entry.def?.[lang.code];
          return (
            <div class="detail-lang" key={lang.code}>
              <dt>{lang.native}</dt>
              <dd lang={lang.code} dir={lang.dir}>
                {terms.length ? (
                  <ul class="term-list">
                    {terms.map((term, i) => (
                      <li key={term} class={i === 0 ? "term-main" : undefined}>
                        {term}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p class="row-missing">{t("missing", { lang: lang.native })}</p>
                )}
                {def && (
                  <p class="definition">
                    <span class="definition-label">{t("definition")}: </span>
                    {def.x}
                    {def.s && <span class="definition-source"> ({t("source")}: {def.s})</span>}
                  </p>
                )}
              </dd>
            </div>
          );
        })}
      </dl>

      <div class="detail-actions">
        {target.length > 0 && (
          <>
            <button type="button" class="button button--primary" onClick={() => onShow(entry.id)}>
              <ExpandIcon />
              {t("showFull")}
            </button>
            <button type="button" class="button" onClick={copy} aria-live="polite">
              {copied ? <CheckIcon /> : <CopyIcon />}
              {copied ? t("copied") : `${t("copy")} (${to.native})`}
            </button>
          </>
        )}
      </div>
      <p class="detail-meta">
        <a href={`#/e/${entry.id}`}>{t("entry", { n: entry.id })}</a>
        <a href={reportUrl} target="_blank" rel="noopener noreferrer">
          {t("report")}
        </a>
      </p>
    </div>
  );
}
