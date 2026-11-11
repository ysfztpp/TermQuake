import { useEffect, useRef, useState } from "preact/hooks";
import { type MessageKey, type UiLang, translate } from "../i18n";
import type { Entry, Language } from "../types";
import { CheckIcon, CloseIcon } from "./icons";

const REPO = "https://github.com/ysfztpp/TermQuake";

interface Props {
  /** The entry the suggestion is about; absent when proposing a new term. */
  entry?: Entry;
  languages: Language[];
  from: Language;
  to: Language;
  ui: UiLang;
  onClose: () => void;
}

/**
 * Suggest a correction, confirm an AI suggestion, or propose a new term.
 * The site has no server: the suggestion becomes a pre-filled GitHub issue,
 * or a text the person shares with the team (WhatsApp, e-mail) themselves.
 */
export function SuggestDialog({ entry, languages, from, to, ui, onClose }: Props) {
  const t = (key: MessageKey, vars?: Record<string, string | number>) => translate(ui, key, vars);
  const [lang, setLang] = useState(to.code);
  const [term, setTerm] = useState("");
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState(false);
  const termRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    termRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const current = entry?.t[lang] ?? [];
  const aiTerm = entry?.m?.[lang]?.some((m) => m.ai) ?? false;
  const langName = languages.find((l) => l.code === lang)?.name ?? lang;
  const anchor = entry ? (entry.t[from.code]?.[0] ?? entry.t.en?.[0] ?? "") : "";
  const title = entry ? `[${lang}] Entry ${entry.id}: ${anchor}` : `[${lang}] New term: ${term}`;
  const body = [
    entry ? `Entry ${entry.id}: ${anchor}` : "New term proposal",
    `Language: ${langName} (${lang})`,
    entry ? `Current: ${current.join(" / ") || "(none)"}${aiTerm ? " [AI suggestion]" : ""}` : null,
    `Suggested: ${term}`,
    note ? `Note: ${note}` : null,
  ]
    .filter(Boolean)
    .join("\n");
  const github = `${REPO}/issues/new?labels=suggestion&title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  const ready = term.trim().length > 0;

  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ title: "TermQuake", text: body });
      else {
        await navigator.clipboard.writeText(body);
        setCopied(true);
      }
    } catch {
      /* the person cancelled, or sharing is unavailable */
    }
  };

  return (
    <div class="sheet-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="suggest-title">
        <div class="sheet-head">
          <h2 id="suggest-title">{entry ? t("suggestTitle") : t("suggestNewTitle")}</h2>
          <button type="button" class="icon-button" onClick={onClose} aria-label={t("close")}>
            <CloseIcon />
          </button>
        </div>
        {entry && <p class="sheet-context">{anchor}</p>}
        <label class="field">
          <span>{t("sLang")}</span>
          <select value={lang} onChange={(e) => setLang((e.target as HTMLSelectElement).value)}>
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.native}
              </option>
            ))}
          </select>
        </label>
        {entry && current.length > 0 && (
          <p class="sheet-current">
            {t("sCurrent")}: <strong>{current.join(" / ")}</strong>
            {aiTerm && (
              <button
                type="button"
                class="link-button"
                onClick={() => {
                  setTerm(current[0]);
                  setNote(t("sConfirmNote"));
                }}
              >
                {t("sConfirm")}
              </button>
            )}
          </p>
        )}
        <label class="field">
          <span>{t("sTerm")}</span>
          <input ref={termRef} type="text" dir="auto" value={term} onInput={(e) => setTerm((e.target as HTMLInputElement).value)} />
        </label>
        <label class="field">
          <span>{t("sNote")}</span>
          <input type="text" dir="auto" value={note} onInput={(e) => setNote((e.target as HTMLInputElement).value)} />
        </label>
        <div class="sheet-actions">
          <button type="button" class="button button--primary" disabled={!ready} onClick={share}>
            {copied ? <CheckIcon /> : null}
            {copied ? t("copied") : t("sShare")}
          </button>
          <a
            class={ready ? "button" : "button is-disabled"}
            href={ready ? github : undefined}
            aria-disabled={!ready}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t("sGithub")}
          </a>
        </div>
        <p class="sheet-small">{t("sPublic")}</p>
      </div>
    </div>
  );
}
