export type UiLang = "tr" | "en" | "es";
export const UI_LANGS: { code: UiLang; label: string }[] = [
  { code: "tr", label: "Türkçe" },
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
];

const strings = {
  tagline: {
    en: "Disaster relief and search & rescue terms",
    tr: "Afet ve arama kurtarma terimleri",
    es: "Términos de emergencias y rescate",
  },
  from: { en: "From", tr: "Kaynak", es: "De" },
  to: { en: "To", tr: "Hedef", es: "A" },
  swap: { en: "Swap languages", tr: "Dilleri değiştir", es: "Intercambiar idiomas" },
  searchLabel: { en: "Search terms", tr: "Terim ara", es: "Buscar términos" },
  searchPlaceholder: {
    en: "Type in {a} or {b}",
    tr: "{a} ya da {b} yazın",
    es: "Escriba en {a} o {b}",
  },
  clear: { en: "Clear search", tr: "Aramayı temizle", es: "Borrar búsqueda" },
  filterLabel: { en: "Show", tr: "Göster", es: "Mostrar" },
  all: { en: "All", tr: "Tümü", es: "Todo" },
  phrases: { en: "Expressions", tr: "İfadeler", es: "Expresiones" },
  count: { en: "{n} entries", tr: "{n} kayıt", es: "{n} entradas" },
  countOne: { en: "1 entry", tr: "1 kayıt", es: "1 entrada" },
  noResults: {
    en: "Nothing matches “{q}”. Check the spelling, try a shorter word, or choose All.",
    tr: "“{q}” için sonuç yok. Yazımı kontrol edin, daha kısa bir sözcük deneyin ya da Tümü'nü seçin.",
    es: "No hay resultados para “{q}”. Revise la ortografía, pruebe una palabra más corta o elija Todo.",
  },
  missing: {
    en: "No {lang} term yet",
    tr: "Henüz {lang} karşılığı yok",
    es: "Aún no hay término en {lang}",
  },
  showFull: { en: "Show full screen", tr: "Tam ekran göster", es: "Mostrar en grande" },
  showHint: {
    en: "Hold the phone up so the other person can read it.",
    tr: "Telefonu karşınızdakinin okuyabileceği şekilde tutun.",
    es: "Muestre el teléfono para que la otra persona pueda leerlo.",
  },
  close: { en: "Close", tr: "Kapat", es: "Cerrar" },
  copy: { en: "Copy", tr: "Kopyala", es: "Copiar" },
  copied: { en: "Copied", tr: "Kopyalandı", es: "Copiado" },
  definition: { en: "Definition", tr: "Tanım", es: "Definición" },
  source: { en: "Source", tr: "Kaynak", es: "Fuente" },
  entry: { en: "Entry {n}", tr: "Kayıt {n}", es: "Entrada {n}" },
  report: {
    en: "Report a problem with this entry",
    tr: "Bu kayıttaki bir hatayı bildirin",
    es: "Informar de un error en esta entrada",
  },
  offlineReady: {
    en: "Saved on this device. Works without internet.",
    tr: "Bu cihaza kaydedildi. İnternetsiz çalışır.",
    es: "Guardado en este dispositivo. Funciona sin internet.",
  },
  offline: {
    en: "No connection. All terms still work.",
    tr: "Bağlantı yok. Tüm terimler çalışmaya devam ediyor.",
    es: "Sin conexión. Todos los términos siguen disponibles.",
  },
  update: {
    en: "Updated terms are available.",
    tr: "Güncellenmiş terimler hazır.",
    es: "Hay términos actualizados.",
  },
  reload: { en: "Load update", tr: "Güncellemeyi yükle", es: "Cargar actualización" },
  loading: { en: "Loading terms…", tr: "Terimler yükleniyor…", es: "Cargando términos…" },
  loadError: {
    en: "The terms could not be loaded. Check the connection and reload the page.",
    tr: "Terimler yüklenemedi. Bağlantıyı kontrol edip sayfayı yenileyin.",
    es: "No se pudieron cargar los términos. Compruebe la conexión y recargue la página.",
  },
  interface: { en: "Interface language", tr: "Arayüz dili", es: "Idioma de la interfaz" },
  about: {
    en: "TermQuake was started by translation students at Boğaziçi University after the 6 February 2023 earthquakes, and grew with volunteer translators, interpreters and developers. It helps volunteer interpreters and anyone in a disaster zone communicate with search and rescue teams.",
    tr: "TermQuake, 6 Şubat 2023 depremlerinin ardından Boğaziçi Üniversitesi çeviri öğrencileri tarafından başlatıldı; gönüllü çevirmenler, tercümanlar ve yazılımcılarla büyüdü. Gönüllü tercümanların ve afet bölgesindeki herkesin arama kurtarma ekipleriyle iletişim kurmasına yardım eder.",
    es: "TermQuake nació entre estudiantes de traducción de la Universidad Boğaziçi tras los terremotos del 6 de febrero de 2023 y creció con traductores, intérpretes y desarrolladores voluntarios. Ayuda a intérpretes voluntarios y a cualquier persona en una zona de desastre a comunicarse con los equipos de rescate.",
  },
  downloads: { en: "Download the data", tr: "Verileri indirin", es: "Descargar los datos" },
  dlTbx: { en: "TBX, for translation tools", tr: "TBX, çeviri araçları için", es: "TBX, para herramientas de traducción" },
  dlCsv: { en: "CSV, for spreadsheets", tr: "CSV, tablolar için", es: "CSV, para hojas de cálculo" },
  dlDb: { en: "SQLite database", tr: "SQLite veritabanı", es: "Base de datos SQLite" },
  license: {
    en: "Terminology © Boğaziçi University Department of Translation and Interpreting Studies, licensed CC BY-NC 4.0.",
    tr: "Terimler © Boğaziçi Üniversitesi Çeviribilim Bölümü, CC BY-NC 4.0 lisansıyla.",
    es: "Terminología © Departamento de Traducción e Interpretación, Universidad Boğaziçi, licencia CC BY-NC 4.0.",
  },
  paper: { en: "Read the article", tr: "Makaleyi okuyun", es: "Leer el artículo" },
  code: { en: "Source code", tr: "Kaynak kod", es: "Código fuente" },
  dataVersion: {
    en: "Data updated {date}, version {v}",
    tr: "Veri güncellemesi {date}, sürüm {v}",
    es: "Datos actualizados el {date}, versión {v}",
  },
  skip: { en: "Skip to results", tr: "Sonuçlara geç", es: "Ir a los resultados" },
} satisfies Record<string, Record<UiLang, string>>;

export type MessageKey = keyof typeof strings;

export function translate(lang: UiLang, key: MessageKey, vars: Record<string, string | number> = {}): string {
  return strings[key][lang].replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? ""));
}

export function detectUiLang(): UiLang {
  const prefs = typeof navigator === "undefined" ? [] : navigator.languages ?? [navigator.language];
  for (const tag of prefs) {
    const base = tag.toLowerCase().split("-")[0];
    if (base === "tr" || base === "en" || base === "es") return base;
  }
  return "en";
}
