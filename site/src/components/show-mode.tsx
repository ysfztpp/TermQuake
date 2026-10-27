import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
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
  const dialogRef = useRef<HTMLDivElement>(null);
  const t = (key: Parameters<typeof translate>[1]) => translate(ui, key);

  // Layout effect: runs before the dialog is painted, so it is never visible
  // without focus inside it and a working Escape key.
  useLayoutEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "Tab") {
        trapFocus(e, dialogRef.current);
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.classList.add("no-scroll");
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("no-scroll");
      opener?.focus();
    };
  }, [onClose]);

  // Keep the screen on while a term is shown. Browsers drop the lock when the
  // page is hidden, so take it again when the page becomes visible.
  useEffect(() => {
    let lock: WakeLockSentinel | undefined;
    const acquire = () => {
      if (document.visibilityState !== "visible" || !navigator.wakeLock) return;
      navigator.wakeLock
        .request("screen")
        .then((l) => {
          lock = l;
        })
        .catch(() => {});
    };
    acquire();
    document.addEventListener("visibilitychange", acquire);
    return () => {
      document.removeEventListener("visibilitychange", acquire);
      void lock?.release().catch(() => {});
    };
  }, []);

  const meta = languages.find((l) => l.code === lang);
  const [main, ...alternatives] = entry.t[lang] ?? [];
  const source = lang !== sourceLang ? entry.t[sourceLang]?.[0] : undefined;
  const long = (main?.length ?? 0) > 28;

  return (
    <div class="show" role="dialog" aria-modal="true" aria-label={meta?.native ?? lang} ref={dialogRef}>
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
        <p class="show-source" lang={sourceLang} dir={languages.find((l) => l.code === sourceLang)?.dir ?? "auto"}>
          {source}
        </p>
      )}
      <p class="show-hint">{t("showHint")}</p>
    </div>
  );
}

/** Keep Tab / Shift+Tab inside the dialog (aria-modal), cycling between its buttons. */
function trapFocus(e: KeyboardEvent, dialog: HTMLElement | null) {
  if (!dialog) return;
  const focusable = [...dialog.querySelectorAll<HTMLElement>("button, [href], [tabindex]:not([tabindex='-1'])")];
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (e.shiftKey && (active === first || !dialog.contains(active))) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && (active === last || !dialog.contains(active))) {
    e.preventDefault();
    first.focus();
  }
}
