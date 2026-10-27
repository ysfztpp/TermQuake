-- Reference data derived from the current Google Sheet columns and domains.
-- Language codes are BCP 47. Kurdish column = Kurmanji (kmr, Latin script);
-- Serbian entries are Cyrillic (sr-Cyrl).

INSERT INTO language (code, name_en, name_native, script, direction, sort_order) VALUES
 ('en','English','English','Latn','ltr',1),
 ('tr','Turkish','Türkçe','Latn','ltr',2),
 ('es','Spanish','Español','Latn','ltr',10),
 ('de','German','Deutsch','Latn','ltr',11),
 ('ru','Russian','Русский','Cyrl','ltr',12),
 ('fr','French','Français','Latn','ltr',13),
 ('kmr','Kurdish (Kurmanji)','Kurmancî','Latn','ltr',14),
 ('zza','Zazaki','Zazakî','Latn','ltr',15),
 ('ar','Arabic','العربية','Arab','rtl',16),
 ('el','Greek','Ελληνικά','Grek','ltr',17),
 ('ja','Japanese','日本語','Jpan','ltr',18),
 ('he','Hebrew','עברית','Hebr','rtl',19),
 ('it','Italian','Italiano','Latn','ltr',20),
 ('hy','Armenian','Հայերեն','Armn','ltr',21),
 ('nl','Dutch','Nederlands','Latn','ltr',22),
 ('zh-Hans','Chinese (Simplified)','简体中文','Hans','ltr',23),
 ('zh-Hant','Chinese (Traditional)','繁體中文','Hant','ltr',24),
 ('bg','Bulgarian','Български','Cyrl','ltr',25),
 ('ko','Korean','한국어','Kore','ltr',26),
 ('fa','Persian','فارسی','Arab','rtl',27),
 ('hi','Hindi','हिन्दी','Deva','ltr',28),
 ('pt','Portuguese','Português','Latn','ltr',29),
 ('sv','Swedish','Svenska','Latn','ltr',30),
 ('ro','Romanian','Română','Latn','ltr',31),
 ('sr-Cyrl','Serbian','Српски','Cyrl','ltr',32),
 ('mk','Macedonian','Македонски','Cyrl','ltr',33),
 ('hu','Hungarian','Magyar','Latn','ltr',34),
 ('fi','Finnish','Suomi','Latn','ltr',35),
 ('sq','Albanian','Shqip','Latn','ltr',36),
 ('cs','Czech','Čeština','Latn','ltr',37),
 ('pl','Polish','Polski','Latn','ltr',38);

-- "İfadeler / Expressions" is not a subject field; it becomes concept.entry_type = 'phrase'.
INSERT INTO domain (id, code) VALUES
 (1,'general'), (2,'search_rescue'), (3,'first_aid'), (4,'medical'), (5,'misc');

INSERT INTO domain_label (domain_id, lang, label) VALUES
 (1,'en','General Terms'),   (1,'tr','Genel Terimler'),
 (2,'en','Search & Rescue'), (2,'tr','Arama Kurtarma'),
 (3,'en','First Aid'),       (3,'tr','İlk Yardım'),
 (4,'en','Medical Terms'),   (4,'tr','Tıbbi Terimler'),
 (5,'en','Miscellaneous'),   (5,'tr','Diğer'),
 (1,'es','Términos generales'), (2,'es','Búsqueda y rescate'), (3,'es','Primeros auxilios'),
 (4,'es','Términos médicos'),   (5,'es','Varios');

INSERT INTO source (short_name, title, url) VALUES
 ('TDK','Türk Dil Kurumu Güncel Türkçe Sözlük','https://sozluk.gov.tr'),
 ('AFAD','Afet ve Acil Durum Yönetimi Başkanlığı','https://www.afad.gov.tr'),
 ('TQ-SHEET','TermQuake Google Sheet (legacy)','https://docs.google.com/spreadsheets/d/1LfFJZxpbCbz2lRpKQ0_kTMKNJVDJ9FyrlAoP15TU8wU');

INSERT INTO contributor (display_name, role) VALUES ('legacy-import','bot');
