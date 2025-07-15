-- MEB Mesleki Eğitim Veri İşleme Sistemi
-- Database Schema v1.0
-- Türkiye Cumhuriyeti Milli Eğitim Bakanlığı Mesleki ve Teknik Eğitim Veritabanı

-- =============================================================================
-- 1. ALANLAR (Ana Eğitim Alanları)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_alan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alan_adi TEXT NOT NULL,
    meb_alan_id TEXT,
    cop_url TEXT,  -- ÇÖP PDF URL'leri (JSON format)
    dbf_urls TEXT, -- DBF dosya URL'leri (JSON format)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 2. DALLAR (Meslek Dalları)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_dal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dal_adi TEXT NOT NULL,
    alan_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alan_id) REFERENCES temel_plan_alan(id) ON DELETE CASCADE
);

-- =============================================================================
-- 3. DERSLER (Ders Listesi)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_adi TEXT NOT NULL,
    sinif INTEGER, -- Sınıf seviyesi (9, 10, 11, 12)
    ders_saati INTEGER NOT NULL DEFAULT 0, -- Haftalık ders saati
    amac TEXT, -- Dersin amacı ve açıklaması
    dm_url TEXT, -- Ders Materyali PDF URL'si
    dbf_url TEXT, -- Ders Bilgi Formu PDF yerel dosya yolu
    bom_url TEXT, -- Bireysel Öğrenme Materyali URL'si
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ders_adi, sinif) -- Aynı ders + sınıf kombinasyonu önleme
);

-- =============================================================================
-- 4. DERS-DAL İLİŞKİLERİ (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ders_dal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    dal_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id) ON DELETE CASCADE,
    FOREIGN KEY (dal_id) REFERENCES temel_plan_dal(id) ON DELETE CASCADE,
    UNIQUE(ders_id, dal_id)
);

-- =============================================================================
-- 5. ÖĞRENME BİRİMLERİ (Ders Alt Bölümleri)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ogrenme_birimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    birim_adi TEXT NOT NULL,
    sure INTEGER, -- Süre (saat)
    aciklama TEXT, -- Birim açıklaması
    sira INTEGER, -- Sıralama
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id) ON DELETE CASCADE
);

-- =============================================================================
-- 6. KONULAR (Öğrenme Birimi Konuları)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_konu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ogrenme_birimi_id INTEGER NOT NULL,
    konu_adi TEXT NOT NULL,
    detay TEXT, -- Konu detayları
    sira INTEGER, -- Sıralama
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ogrenme_birimi_id) REFERENCES temel_plan_ogrenme_birimi(id) ON DELETE CASCADE
);

-- =============================================================================
-- 7. KAZANIMLAR (Öğrenme Hedefleri)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_kazanim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    konu_id INTEGER NOT NULL,
    kazanim_adi TEXT NOT NULL,
    seviye TEXT, -- Kazanım seviyesi (Temel, Orta, İleri)
    kod TEXT, -- Kazanım kodu
    sira INTEGER, -- Sıralama
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (konu_id) REFERENCES temel_plan_konu(id) ON DELETE CASCADE
);

-- =============================================================================
-- 8. ARAÇ-GEREÇ (Ders Araçları)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_arac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arac_adi TEXT NOT NULL UNIQUE,
    kategori TEXT, -- Araç kategorisi (Yazılım, Donanım, Malzeme, vs.)
    aciklama TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 9. DERS-ARAÇ İLİŞKİLERİ (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ders_arac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    arac_id INTEGER NOT NULL,
    miktar INTEGER DEFAULT 1, -- Gerekli miktar
    zorunlu BOOLEAN DEFAULT 0, -- Zorunlu mu?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id) ON DELETE CASCADE,
    FOREIGN KEY (arac_id) REFERENCES temel_plan_arac(id) ON DELETE CASCADE,
    UNIQUE(ders_id, arac_id)
);

-- =============================================================================
-- 10. ÖLÇME DEĞERLENDİRME (Assessment Methods)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_olcme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    olcme_adi TEXT NOT NULL UNIQUE,
    aciklama TEXT,
    agirlik_yuzdesi INTEGER, -- Ağırlık yüzdesi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 11. DERS-ÖLÇME İLİŞKİLERİ (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ders_olcme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    olcme_id INTEGER NOT NULL,
    agirlik_yuzdesi INTEGER DEFAULT 0, -- Bu derste ağırlık yüzdesi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id) ON DELETE CASCADE,
    FOREIGN KEY (olcme_id) REFERENCES temel_plan_olcme(id) ON DELETE CASCADE,
    UNIQUE(ders_id, olcme_id)
);

-- =============================================================================
-- 12. DERS AMAÇLARI (Course Objectives)
-- =============================================================================
CREATE TABLE IF NOT EXISTS temel_plan_ders_amac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    amac TEXT NOT NULL,
    sira INTEGER, -- Sıralama
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id) ON DELETE CASCADE
);

-- =============================================================================
-- 13. MIGRATION TABLOSU (Schema Versioning)
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- İNDEXLER (Performance Optimization)
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_temel_plan_dal_alan_id ON temel_plan_dal(alan_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_ders_dal_ders_id ON temel_plan_ders_dal(ders_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_ders_dal_dal_id ON temel_plan_ders_dal(dal_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_ders_sinif ON temel_plan_ders(sinif);
CREATE INDEX IF NOT EXISTS idx_temel_plan_ogrenme_birimi_ders_id ON temel_plan_ogrenme_birimi(ders_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_konu_ogrenme_birimi_id ON temel_plan_konu(ogrenme_birimi_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_kazanim_konu_id ON temel_plan_kazanim(konu_id);
CREATE INDEX IF NOT EXISTS idx_temel_plan_alan_adi ON temel_plan_alan(alan_adi);
CREATE INDEX IF NOT EXISTS idx_temel_plan_dal_adi ON temel_plan_dal(dal_adi);
CREATE INDEX IF NOT EXISTS idx_temel_plan_ders_adi ON temel_plan_ders(ders_adi);

-- =============================================================================
-- BAŞLANGIÇ VERİLERİ (Initial Data)
-- =============================================================================

-- Temel ölçme değerlendirme yöntemleri
INSERT OR IGNORE INTO temel_plan_olcme (olcme_adi, aciklama, agirlik_yuzdesi) VALUES
('Yazılı Sınav', 'Geleneksel yazılı sınav', 40),
('Proje Ödevi', 'Dönem projesi değerlendirmesi', 30),
('Performans Görevi', 'Uygulamalı performans değerlendirmesi', 20),
('Sözlü Sınav', 'Sözlü değerlendirme', 10),
('Portfolyo', 'Öğrenci portfolyosu', 15),
('Laboratuvar Raporu', 'Laboratuvar çalışması raporu', 25),
('Sunum', 'Öğrenci sunumu', 15),
('Grup Çalışması', 'Grup projesi değerlendirmesi', 20);

-- Temel araç-gereç kategorileri
INSERT OR IGNORE INTO temel_plan_arac (arac_adi, kategori, aciklama) VALUES
('Bilgisayar', 'Donanım', 'Masaüstü veya dizüstü bilgisayar'),
('Projeksiyon Cihazı', 'Donanım', 'Sunum için projeksiyon cihazı'),
('Yazılım Geliştirme Ortamı', 'Yazılım', 'IDE veya kod editörü'),
('İnternet Bağlantısı', 'Altyapı', 'İnternet erişimi'),
('Teknik Doküman', 'Materyal', 'Teknik kılavuz ve dokümantasyon'),
('Laboratuvar Malzemeleri', 'Malzeme', 'Pratik çalışma malzemeleri'),
('Whiteboard', 'Donanım', 'Beyaz tahta'),
('Yazıcı', 'Donanım', 'Belge yazdırma cihazı');

-- İlk migration versiyonu
INSERT OR IGNORE INTO schema_migrations (version) VALUES (1);

-- =============================================================================
-- GÜNCELLEME TETİKLEYİCİLERİ (Update Triggers)
-- =============================================================================
CREATE TRIGGER IF NOT EXISTS update_temel_plan_alan_timestamp 
    AFTER UPDATE ON temel_plan_alan
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_alan SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temel_plan_dal_timestamp 
    AFTER UPDATE ON temel_plan_dal
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_dal SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temel_plan_ders_timestamp 
    AFTER UPDATE ON temel_plan_ders
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_ders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temel_plan_ogrenme_birimi_timestamp 
    AFTER UPDATE ON temel_plan_ogrenme_birimi
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_ogrenme_birimi SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temel_plan_konu_timestamp 
    AFTER UPDATE ON temel_plan_konu
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_konu SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temel_plan_kazanim_timestamp 
    AFTER UPDATE ON temel_plan_kazanim
    FOR EACH ROW
BEGIN
    UPDATE temel_plan_kazanim SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;