import { useEffect, useRef, useState } from "preact/hooks";
import { type UiLang, translate } from "../i18n";
import type { Entry, Language } from "../types";
import { CloseIcon } from "./icons";

interface Props {
  entry: Entry;
  languages: Language[];
  initialLang: string;
  sourceLang: string;
  ui: UiLang;
  onClose: () => void;
}

/**
 * Full-screen, very large text, for holding the phone up to a survivor or a
 * rescuer. Keeps the screen awake while open where the browser allows it.
 */
export function ShowMode({ entry, languages, initialLang, sourceLang, ui, onClose }: Props) {
  const available = languages.filter((l) => entry.t[l.code]?.length);
  const [lang, setLang] = useState(
    available.some((l) => l.code === initialLang) ? initialLang : (available[0]?.code ?? initialLang),
  );
  const closeRef = useRef<HTMLButtonElement>(null);
  const t = (key: Parameters<typeof translate>[1]) => translate(ui, key);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");

    let lock: WakeLockSentinel | undefined;
    navigator.wakeLock
      ?.request("screen")
      .then((l) => (lock = l))
      .catch(() => {});

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
      void lock?.release().catch(() => {});
      opener?.focus();
    };
  }, [onClose]);

  const meta = languages.find((l) => l.code === lang);
  const [main, ...alternatives] = entry.t[lang] ?? [];
  const source = lang !== sourceLang ? entry.t[sourceLang]?.[0] : undefined;
  const long = (main?.length ?? 0) > 28;

  return (
    <div class="show" role="dialog" aria-modal="true" aria-label={meta?.native ?? lang}>
      <div class="show-bar">
        <div class="show-langs" role="group" aria-label={t("to")}>
          {available.map((l) => (
            <button
              type="button"
              key={l.code}
              class="show-lang"
              aria-pressed={l.code === lang}
              onClick={() => setLang(l.code)}
            >
              {l.native}
            </button>
          ))}
        </div>
        <button type="button" class="icon-button" ref={closeRef} onClick={onClose} aria-label={t("close")}>
          <CloseIcon width="26" height="26" />
        </button>
      </div>

      <div class="show-body" lang={lang} dir={meta?.dir ?? "auto"}>
        <p class={long ? "show-main show-main--long" : "show-main"}>{main}</p>
        {alternatives.length > 0 && <p class="show-alt">{alternatives.join(" / ")}</p>}
      </div>

      {source && (
        <p class="show-source" lang={sourceLang}>
          {source}
        </p>
      )}
      <p class="show-hint">{t("showHint")}</p>
    </div>
  );
}
