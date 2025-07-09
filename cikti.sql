
-- Veritabanı Şeması Oluşturma (SQLite Uyumlu)
-- Bu komutlar, verilerin ekleneceği tabloları oluşturur.

DROP TABLE IF EXISTS temel_plan_alan;
CREATE TABLE temel_plan_alan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alan_adi TEXT NOT NULL UNIQUE,
    cop_url TEXT
);

DROP TABLE IF EXISTS temel_plan_dal;
CREATE TABLE temel_plan_dal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dal_adi TEXT NOT NULL,
    alan_id INTEGER NOT NULL,
    FOREIGN KEY (alan_id) REFERENCES temel_plan_alan(id)
);

DROP TABLE IF EXISTS temel_plan_ders;
CREATE TABLE temel_plan_ders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_adi TEXT NOT NULL UNIQUE,
    sinif INTEGER NOT NULL,
    ders_saati INTEGER NOT NULL,
    amac TEXT,
    dbf_url TEXT
);

DROP TABLE IF EXISTS temel_plan_ders_dal;
CREATE TABLE temel_plan_ders_dal (
    ders_id INTEGER NOT NULL,
    dal_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, dal_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (dal_id) REFERENCES temel_plan_dal(id)
);

DROP TABLE IF EXISTS temel_plan_ders_amac;
CREATE TABLE temel_plan_ders_amac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    amac TEXT NOT NULL,
    UNIQUE(ders_id, amac),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id)
);

DROP TABLE IF EXISTS temel_plan_arac;
CREATE TABLE temel_plan_arac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arac_gerec TEXT NOT NULL UNIQUE
);

DROP TABLE IF EXISTS temel_plan_ders_arac;
CREATE TABLE temel_plan_ders_arac (
    ders_id INTEGER NOT NULL,
    arac_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, arac_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (arac_id) REFERENCES temel_plan_arac(id)
);

DROP TABLE IF EXISTS temel_plan_olcme;
CREATE TABLE temel_plan_olcme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    olcme_degerlendirme TEXT NOT NULL UNIQUE
);

DROP TABLE IF EXISTS temel_plan_ders_olcme;
CREATE TABLE temel_plan_ders_olcme (
    ders_id INTEGER NOT NULL,
    olcme_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, olcme_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (olcme_id) REFERENCES temel_plan_olcme(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ogrenme_birimi;
CREATE TABLE temel_plan_ders_ogrenme_birimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    ogrenme_birimi TEXT NOT NULL,
    ders_saati INTEGER,
    UNIQUE(ders_id, ogrenme_birimi),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ob_konu;
CREATE TABLE temel_plan_ders_ob_konu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ogrenme_birimi_id INTEGER NOT NULL,
    konu TEXT NOT NULL,
    UNIQUE(ogrenme_birimi_id, konu),
    FOREIGN KEY (ogrenme_birimi_id) REFERENCES temel_plan_ders_ogrenme_birimi(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ob_konu_kazanim;
CREATE TABLE temel_plan_ders_ob_konu_kazanim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    konu_id INTEGER NOT NULL,
    kazanim TEXT NOT NULL,
    UNIQUE(konu_id, kazanim),
    FOREIGN KEY (konu_id) REFERENCES temel_plan_ders_ob_konu(id)
);

-- Şema Oluşturma Sonu --

