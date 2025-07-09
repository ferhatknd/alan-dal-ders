
-- Veritabanı Şeması Oluşturma (SQLite Uyumlu)
DROP TABLE IF EXISTS temel_plan_ders_ob_konu_kazanim;
DROP TABLE IF EXISTS temel_plan_ders_ob_konu;
DROP TABLE IF EXISTS temel_plan_ders_ogrenme_birimi;
DROP TABLE IF EXISTS temel_plan_ders_olcme;
DROP TABLE IF EXISTS temel_plan_olcme;
DROP TABLE IF EXISTS temel_plan_ders_arac;
DROP TABLE IF EXISTS temel_plan_arac;
DROP TABLE IF EXISTS temel_plan_ders_amac;
DROP TABLE IF EXISTS temel_plan_ders_dal;
DROP TABLE IF EXISTS temel_plan_ders;
DROP TABLE IF EXISTS temel_plan_dal;
DROP TABLE IF EXISTS temel_plan_alan;

CREATE TABLE temel_plan_alan (id INTEGER PRIMARY KEY AUTOINCREMENT, alan_adi TEXT NOT NULL UNIQUE, cop_url TEXT);
CREATE TABLE temel_plan_dal (id INTEGER PRIMARY KEY AUTOINCREMENT, dal_adi TEXT NOT NULL, alan_id INTEGER NOT NULL, FOREIGN KEY (alan_id) REFERENCES temel_plan_alan(id));
CREATE TABLE temel_plan_ders (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_adi TEXT NOT NULL UNIQUE, sinif INTEGER, ders_saati INTEGER, amac TEXT, dbf_url TEXT);
CREATE TABLE temel_plan_ders_dal (ders_id INTEGER NOT NULL, dal_id INTEGER NOT NULL, PRIMARY KEY (ders_id, dal_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (dal_id) REFERENCES temel_plan_dal(id));
CREATE TABLE temel_plan_ders_amac (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER NOT NULL, amac TEXT NOT NULL, UNIQUE(ders_id, amac), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id));
CREATE TABLE temel_plan_arac (id INTEGER PRIMARY KEY AUTOINCREMENT, arac_gerec TEXT NOT NULL UNIQUE);
CREATE TABLE temel_plan_ders_arac (ders_id INTEGER NOT NULL, arac_id INTEGER NOT NULL, PRIMARY KEY (ders_id, arac_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (arac_id) REFERENCES temel_plan_arac(id));
CREATE TABLE temel_plan_olcme (id INTEGER PRIMARY KEY AUTOINCREMENT, olcme_degerlendirme TEXT NOT NULL UNIQUE);
CREATE TABLE temel_plan_ders_olcme (ders_id INTEGER NOT NULL, olcme_id INTEGER NOT NULL, PRIMARY KEY (ders_id, olcme_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (olcme_id) REFERENCES temel_plan_olcme(id));
CREATE TABLE temel_plan_ders_ogrenme_birimi (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER NOT NULL, ogrenme_birimi TEXT NOT NULL, ders_saati INTEGER, UNIQUE(ders_id, ogrenme_birimi), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id));
CREATE TABLE temel_plan_ders_ob_konu (id INTEGER PRIMARY KEY AUTOINCREMENT, ogrenme_birimi_id INTEGER NOT NULL, konu TEXT NOT NULL, UNIQUE(ogrenme_birimi_id, konu), FOREIGN KEY (ogrenme_birimi_id) REFERENCES temel_plan_ders_ogrenme_birimi(id));
CREATE TABLE temel_plan_ders_ob_konu_kazanim (id INTEGER PRIMARY KEY AUTOINCREMENT, konu_id INTEGER NOT NULL, kazanim TEXT NOT NULL, UNIQUE(konu_id, kazanim), FOREIGN KEY (konu_id) REFERENCES temel_plan_ders_ob_konu(id));
-- Şema Oluşturma Sonu --


-- BİLİNMEYEN DERS DERSİ İÇİN VERİ GİRİŞİ --
INSERT OR IGNORE INTO temel_plan_alan (alan_adi) VALUES ('TANIMSIZ ALAN');
INSERT OR IGNORE INTO temel_plan_dal (dal_adi, alan_id) SELECT 'TANIMSIZ DAL', id FROM temel_plan_alan WHERE alan_adi = 'TANIMSIZ ALAN';
INSERT OR IGNORE INTO temel_plan_ders (ders_adi, sinif, ders_saati, amac, dbf_url) VALUES ('BİLİNMEYEN DERS', NULL, NULL, '', 'ANATOMİ VE FİZYOLOJİ 9 DBF.pdf');
INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) SELECT (SELECT id FROM temel_plan_ders WHERE ders_adi = 'BİLİNMEYEN DERS'), (SELECT id FROM temel_plan_dal WHERE dal_adi = 'TANIMSIZ DAL');


-- DERS SONU --


-- BİLİNMEYEN DERS DERSİ İÇİN VERİ GİRİŞİ --
INSERT OR IGNORE INTO temel_plan_alan (alan_adi) VALUES ('TANIMSIZ ALAN');
INSERT OR IGNORE INTO temel_plan_dal (dal_adi, alan_id) SELECT 'TANIMSIZ DAL', id FROM temel_plan_alan WHERE alan_adi = 'TANIMSIZ ALAN';
INSERT OR IGNORE INTO temel_plan_ders (ders_adi, sinif, ders_saati, amac, dbf_url) VALUES ('BİLİNMEYEN DERS', NULL, NULL, '', 'ATÖLYE.pdf');
INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) SELECT (SELECT id FROM temel_plan_ders WHERE ders_adi = 'BİLİNMEYEN DERS'), (SELECT id FROM temel_plan_dal WHERE dal_adi = 'TANIMSIZ DAL');


-- DERS SONU --
