import { Fragment } from "preact";
import { useCallback, useEffect, useMemo, useRef, useState } from "preact/hooks";
import { EntryRow } from "./components/entry-row";
import { CheckIcon, CloseIcon, Mark, OfflineIcon, SearchIcon, SwapIcon } from "./components/icons";
import { ShowMode } from "./components/show-mode";
import { detectUiLang, type MessageKey, translate, UI_LANGS, type UiLang } from "./i18n";
import { applyUpdate, useOnline, usePwa } from "./pwa";
import { browse, buildIndex, initial, search } from "./search";
import { loadPrefs, savePrefs } from "./storage";
import type { Entry, Filter, Language, Termbase } from "./types";

const DATA_URL = `${import.meta.env.BASE_URL}data/termbase.json`;
const PAPER_URL = "https://doi.org/10.1016/j.ijdrr.2026.106498";
const REPO_URL = "https://github.com/ysfztpp/TermQuake";
// Default pair per interface language: what a person using that interface most likely needs.
const DEFAULT_PAIR: Record<UiLang, [string, string]> = { tr: ["tr", "en"], en: ["en", "tr"], es: ["es", "tr"] };

function entryFromHash(): number | null {
  const m = /^#\/e\/(\d+)$/.exec(location.hash);
  return m ? Number(m[1]) : null;
}

export function App() {
  const saved = useMemo(loadPrefs, []);
  const [ui, setUi] = useState<UiLang>(
    UI_LANGS.some((l) => l.code === saved.ui) ? (saved.ui as UiLang) : detectUiLang(),
  );
  const [db, setDb] = useState<Termbase | null>(null);
  const [failed, setFailed] = useState(false);
  const [from, setFrom] = useState(saved.from ?? DEFAULT_PAIR[ui][0]);
  const [to, setTo] = useState(saved.to ?? DEFAULT_PAIR[ui][1]);
  const [filter, setFilter] = useState<Filter>(saved.filter ?? "all");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<number | null>(entryFromHash);
  const [showId, setShowId] = useState<number | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const pwa = usePwa();
  const online = useOnline();
  const t = (key: MessageKey, vars?: Record<string, string | number>) => translate(ui, key, vars);

  useEffect(() => {
    fetch(DATA_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: Termbase) => {
        const codes = data.languages.map((l) => l.code);
        // Repair saved choices that no longer exist in the data.
        const f = codes.includes(from) ? from : codes[0];
        const g = codes.includes(to) && to !== f ? to : codes.find((c) => c !== f) ?? f;
        setFrom(f);
        setTo(g);
        // A saved domain filter that no longer exists (renamed or removed) falls back to All.
        if (filter !== "all" && filter !== "phrases" && !data.domains.some((d) => d.code === filter)) {
          setFilter("all");
        }
        setDb(data);
      })
      .catch(() => setFailed(true));
  }, []);

  useEffect(() => savePrefs({ from, to, ui, filter }), [from, to, ui, filter]);
  useEffect(() => {
    document.documentElement.lang = ui;
  }, [ui]);

  // Deep links: #/e/123 opens entry 123 and keeps the address shareable.
  useEffect(() => {
    const onHash = () => setOpenId(entryFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    const target = openId === null ? location.pathname + location.search : `#/e/${openId}`;
    if (openId === null ? location.hash : location.hash !== target) history.replaceState(null, "", target);
  }, [openId]);
  // A link to an entry that was merged into another opens the one that replaced it.
  useEffect(() => {
    const target = db && openId !== null ? db.moved?.[String(openId)] : undefined;
    if (target !== undefined) setOpenId(target);
  }, [db, openId]);
  useEffect(() => {
    if (db && openId !== null) {
      document.getElementById(`entry-${openId}`)?.closest(".row")?.scrollIntoView({ block: "nearest" });
    }
  }, [db, openId]);

  const index = useMemo(() => (db ? buildIndex(db.entries) : []), [db]);
  const lang = (code: string): Language =>
    db?.languages.find((l) => l.code === code) ?? { code, name: code, native: code, dir: "ltr" };

  const deepLinked = db && openId !== null ? db.entries.find((e) => e.id === openId) : undefined;
  const list: Entry[] = useMemo(() => {
    if (!db) return [];
    if (query.trim()) return search(index, query, { langs: [from, to], preferLang: from, filter }).map((h) => h.entry);
    return browse(db.entries, from, filter);
  }, [db, index, query, from, to, filter]);
  // An entry opened by link stays visible even if the current filter hides it.
  const rows = deepLinked && !list.includes(deepLinked) && !query.trim() ? [deepLinked, ...list] : list;

  const toggle = useCallback((id: number) => setOpenId((cur) => (cur === id ? null : id)), []);
  const closeShow = useCallback(() => setShowId(null), []);

  const swap = () => {
    setFrom(to);
    setTo(from);
  };
  const choose = (side: "from" | "to", code: string) => {
    const other = side === "from" ? to : from;
    if (code === other) return swap();
    (side === "from" ? setFrom : setTo)(code);
  };

  if (failed) return <Message text={t("loadError")} />;
  if (!db) return <Message text={t("loading")} busy />;

  const fromLang = lang(from);
  const toLang = lang(to);
  const filters: { code: Filter; label: string }[] = [
    { code: "all", label: t("all") },
    ...db.domains.map((d) => ({ code: d.code, label: d.label[ui] ?? d.label.en })),
    { code: "phrases", label: t("phrases") },
  ];
  const showEntry = showId === null ? undefined : db.entries.find((e) => e.id === showId);
  const missingLink = openId !== null && !deepLinked && !db.moved?.[String(openId)] && !query.trim();
  const browsing = !query.trim();

  return (
    <>
      <a class="skip" href="#results">
        {t("skip")}
      </a>
      <header class="top">
        <div class="top-inner">
          <div class="brand">
            <Mark class="brand-mark" />
            <div>
              <h1 class="brand-name">TermQuake</h1>
              <p class="brand-tagline">{t("tagline")}</p>
            </div>
            <label class="ui-lang">
              <span class="visually-hidden">{t("interface")}</span>
              <select value={ui} onChange={(e) => setUi((e.target as HTMLSelectElement).value as UiLang)}>
                {UI_LANGS.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div class="pair">
            <LangSelect label={t("from")} value={from} languages={db.languages} onChange={(c) => choose("from", c)} />
            <button type="button" class="icon-button pair-swap" onClick={swap} aria-label={t("swap")} title={t("swap")}>
              <SwapIcon />
            </button>
            <LangSelect label={t("to")} value={to} languages={db.languages} onChange={(c) => choose("to", c)} />
          </div>

        </div>
      </header>

      <div class="finder">
        <div class="finder-inner">
          <form class="search" role="search" onSubmit={(e) => e.preventDefault()}>
            <label class="visually-hidden" for="q">
              {t("searchLabel")}
            </label>
            <SearchIcon class="search-icon" />
            <input
              id="q"
              ref={searchRef}
              type="search"
              inputMode="search"
              autoComplete="off"
              autoCorrect="off"
              spellcheck={false}
              dir="auto"
              placeholder={t("searchPlaceholder", { a: fromLang.native, b: toLang.native })}
              value={query}
              onInput={(e) => {
                setQuery((e.target as HTMLInputElement).value);
                setOpenId(null);
              }}
            />
            {query && (
              <button
                type="button"
                class="icon-button search-clear"
                aria-label={t("clear")}
                onClick={() => {
                  setQuery("");
                  searchRef.current?.focus();
                }}
              >
                <CloseIcon />
              </button>
            )}
          </form>

          <div class="filters" role="group" aria-label={t("filterLabel")}>
            {filters.map((f) => (
              <button
                type="button"
                key={f.code}
                class="filter"
                data-domain={f.code}
                aria-pressed={filter === f.code}
                onClick={() => setFilter(f.code)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {(!online || pwa.needRefresh) && (
        <div class="status" role="status">
          {!online ? (
            <p>
              <OfflineIcon /> {t("offline")}
            </p>
          ) : (
            <p>
              {t("update")}{" "}
              <button type="button" class="link-button" onClick={applyUpdate}>
                {t("reload")}
              </button>
            </p>
          )}
        </div>
      )}

      <main id="results" class="results" tabIndex={-1}>
        {missingLink && (
          <p class="empty" role="status">
            {t("notFound", { id: openId })}
          </p>
        )}
        <p class="results-count" aria-live="polite">
          {rows.length === 1 ? t("countOne") : t("count", { n: rows.length })}
        </p>
        {rows.length === 0 ? (
          <p class="empty">{t("noResults", { q: query.trim() })}</p>
        ) : (
          <ul class="rows">
            {rows.map((entry, i) => {
              const letter = browsing ? initial(entry.t[from]?.[0], from) : null;
              const prevLetter = browsing && i > 0 ? initial(rows[i - 1].t[from]?.[0], from) : null;
              return (
                <Fragment key={entry.id}>
                  {browsing && letter !== prevLetter && (
                    <li class="letter" aria-hidden="true">
                      {letter}
                    </li>
                  )}
                  <EntryRow
                    entry={entry}
                    from={fromLang}
                    to={toLang}
                    languages={db.languages}
                    domains={db.domains}
                    ui={ui}
                    open={openId === entry.id}
                    onToggle={toggle}
                    onShow={setShowId}
                  />
                </Fragment>
              );
            })}
          </ul>
        )}
      </main>

      <footer class="foot">
        <div class="foot-inner">
          <p>{t("about")}</p>
          <h2>{t("downloads")}</h2>
          <ul class="downloads">
            <li>
              <a href={`${import.meta.env.BASE_URL}downloads/termquake.tbx`} download>
                {t("dlTbx")}
              </a>
            </li>
            <li>
              <a href={`${import.meta.env.BASE_URL}downloads/termquake.csv`} download>
                {t("dlCsv")}
              </a>
            </li>
            <li>
              <a href={`${import.meta.env.BASE_URL}downloads/termquake.db`} download>
                {t("dlDb")}
              </a>
            </li>
          </ul>
          <p class="foot-links">
            <a href={PAPER_URL} rel="noopener noreferrer" target="_blank">
              {t("paper")}
            </a>
            <a href={REPO_URL} rel="noopener noreferrer" target="_blank">
              {t("code")}
            </a>
          </p>
          <p class="foot-small">{t("license")}</p>
          <p class="foot-small">
            {pwa.offlineReady && (
              <span class="offline-ready">
                <CheckIcon width="16" height="16" /> {t("offlineReady")}{" "}
              </span>
            )}
            {t("dataVersion", { date: db.data.updated, v: db.data.version })}
          </p>
        </div>
      </footer>

      {showEntry && (
        <ShowMode
          entry={showEntry}
          languages={db.languages}
          initialLang={to}
          sourceLang={from}
          ui={ui}
          onClose={closeShow}
        />
      )}
    </>
  );
}

function LangSelect({ label, value, languages, onChange }: {
  label: string;
  value: string;
  languages: Language[];
  onChange: (code: string) => void;
}) {
  return (
    <label class="pair-select">
      <span class="pair-label">{label}</span>
      <select value={value} onChange={(e) => onChange((e.target as HTMLSelectElement).value)}>
        {languages.map((l) => (
          <option key={l.code} value={l.code}>
            {l.native}
          </option>
        ))}
      </select>
    </label>
  );
}

function Message({ text, busy }: { text: string; busy?: boolean }) {
  return (
    <main class="message" aria-busy={busy}>
      <Mark class="brand-mark" />
      <p>{text}</p>
    </main>
  );
}
