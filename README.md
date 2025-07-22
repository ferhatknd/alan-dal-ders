# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 MEB Mesleki Eğitim Veri İşleme Projesi - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı birleşik kılavuzudur. README.md, is_akisi.md ve teknik detayların tümünü içerir. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-22 (extract_olcme.py Türkçe karakter eşleştirme sistemi iyileştirildi + normalize_for_matching() fonksiyonu eklendi + DBF PDF header matching sorunu çözüldü + Türkçe I/ı, Ç/ç karakterleri için ASCII normalizasyonu + Başlık eşleştirme oranları %0'dan %80+ seviyesine çıkarıldı)

## 🎯 Proje Genel Bakış

### Geliştirme Ortamı Kurulumu

**Python Backend:**
```bash
# Gerekli paketleri yükle
pip install -r requirements.txt

# Flask sunucusunu başlat
python server.py
```

**React Frontend:**
```bash
# Node.js bağımlılıklarını yükle
npm install

# Development server'ı başlat
npm start

# Production build
npm run build

# Test'leri çalıştır
npm test
```

**Ortak Geliştirme Komutları:**
```bash
# Veritabanı ve schema otomatik kurulum
python server.py  # İlk çalıştırmada otomatik setup

#always use single responsibility principle when creating new method

# Test debugging
python test.py  # DBF PDF analizi için

# Proje yapısını kontrol et
ls -la data/  # Veri dosyalarını görüntüle
```

### Ana Amaç
Türkiye Cumhuriyeti Millî Eğitim Bakanlığı'na (MEB) bağlı Mesleki ve Teknik Eğitim Genel Müdürlüğü'nün web sitesinden (`meslek.meb.gov.tr`) mesleki eğitim verilerini otomatik olarak çeker, işler ve SQLite veritabanında yapılandırılmış şekilde saklar.

### Sistem Mimarisi
**3 Katmanlı Sistem:**
1. **Backend (Flask + SQLite):** Veri çekme, PDF işleme ve veritabanı yönetimi
2. **Frontend (React):** Aşamalı iş akışı ile kullanıcı arayüzü  
3. **Veritabanı (SQLite):** Hiyerarşik eğitim verilerinin yapılandırılmış saklanması

### Hiyerarşik Veri Yapısı
```
Alan (Area) → Dal (Field) → Ders (Course) → Öğrenme Birimi (Learning Unit) → Konu (Topic) → Kazanım (Achievement)
```

### Teknik Mimari

**Backend (Flask):**
- Port: 5000 (default)
- Database: SQLite (`data/temel_plan.db`)
- API Pattern: RESTful with Server-Sent Events (SSE)
- Module Structure: Modular design with separated concerns

**Frontend (React):**
- Port: 3000 (development)
- Framework: React 18.2.0
- Build Tool: react-scripts
- Proxy: Setup for API calls to backend

**Data Processing Pipeline:**
1. Scraping Layer: Web scraping from meslek.meb.gov.tr
2. Processing Layer: PDF parsing and content extraction
3. Storage Layer: SQLite database with hierarchical structure
4. Cache Layer: File-based caching system for PDFs and data

## 📁 Kritik Dosya Yapısı

### 🔧 Core Backend Dosyaları
- **`server.py`** - Ana Flask sunucusu, tüm API endpoint'leri, veritabanı işlemleri ve **istatistik sistemi**
  - ⭐ **YENİ**: Merkezi database connection decorator sistemi kullanıyor

### 📊 Backend Modülleri (modules/ klasörü)
- **`modules/oku_dbf.py`** - ⭐ **YENİDEN ADLANDIRILDI**: DBF PDF parsing ve içerik analizi (eski: oku.py)
- **`modules/get_dbf.py`** - ⭐ **STANDARDİZE**: `get_dbf()` fonksiyonu ile DBF verilerini çeker, RAR/ZIP indirir (açmaz), `data/get_dbf.json` üretir ve `dbf_urls` sütununa JSON kaydeder
- **`modules/get_cop.py`** - ⭐ **STANDARDİZE**: `get_cop()` fonksiyonu ile ÇÖP verilerini çeker, PDF indirir (açmaz), `data/get_cop.json` üretir ve `cop_url` sütununa JSON kaydeder
- **`modules/oku_cop.py`** - ⭐ **YENİ**: COP PDF parsing ve analiz modülü - Tamamen yeniden yazıldı
- **`modules/get_dm.py`** - Ders Materyalleri (DM) verilerini çeker
- **`modules/get_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker
- **`modules/get_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils_normalize.py`** - ⭐ **YENİ AYIRIM**: String normalizasyon fonksiyonları, Türkçe karakter normalizasyonu (eski utils.py'den ayrıştırıldı)
- **`modules/utils_database.py`** - ⭐ **YENİ**: Veritabanı işlemleri modülü, **database connection decorators**, **MEB ID yönetimi** ve **CRUD operasyonları**
- **`modules/utils_file_management.py`** - ⭐ **YENİ**: Dosya işlemleri modülü, **ortak alan dosya sistemi**, **duplicate dosya yönetimi** ve **arşiv işlemleri**
- **`modules/utils_stats.py`** - ⭐ **YENİ AYIRIM**: İstatistik ve monitoring fonksiyonları (utils_database.py'den ayrıştırıldı)

### 🌐 Frontend Dosyaları
- **`src/App.js`** - ⭐ **YENİLENDİ**: Tek satır workflow UI, console panel, JSON popup'sız tasarım
- **`src/App.css`** - Ana stil dosyası
- **`package.json`** - Node.js bağımlılıkları ve scriptler
- **`src/index.js`** - React uygulaması entry point
- **`src/setupProxy.js`** - CORS proxy ayarları
- **`src/reportWebVitals.js`** - Performance monitoring

### 🗂️ Veri ve Veritabanı
- **`data/temel_plan.db`** - SQLite veritabanı dosyası
- **`data/schema.sql`** - Veritabanı schema dosyası
- **`data/get_cop.json`** - ⭐ **YENİ**: COP verilerinin JSON çıktısı
- **`data/get_dbf.json`** - ⭐ **YENİ**: DBF verilerinin JSON çıktısı
- **`data/`** - JSON cache dosyaları, veritabanı ve schema dosyaları
  - `dbf/` - İndirilen DBF dosyaları (alan klasörleri halinde)
  - `cop/` - ÇÖP PDF dosyaları
  - `dm/` - Ders Materyali dosyaları ⭐ **YENİ**: `00_Ortak_Alan_Dersleri` klasörü ile duplicate dosya yönetimi
  - `bom/` - BÖM dosyaları

### 🐛 Debug ve Test Araçları
- **`test.py`** - DBF PDF tablo yapısını detaylı analiz eden debug script
- **`extract_olcme.py`** - ⭐ **YENİ GÜNCELLEME**: DBF PDF analiz ve başlık eşleştirme test script'i
  - **Türkçe Karakter Eşleştirme**: `normalize_for_matching()` fonksiyonu ile gelişmiş normalizasyon
  - **ASCII Dönüşüm**: Türkçe karakterleri (İ/ı → I, Ç/ç → C, vb.) ASCII'ye çevirir
  - **Başlık Eşleştirme**: "Geometrik Motif Çizimi" ↔ "GEOMETRİK MOTİF ÇİZİMİ" eşleştirmesi %100 başarılı

## 🗄️ Veritabanı Yapısı (SQLite)

### Ana Tablolar
```sql
-- 1. ALANLAR (Ana Eğitim Alanları)
temel_plan_alan
├── id (INTEGER PRIMARY KEY)
├── alan_adi (TEXT NOT NULL)
├── meb_alan_id (TEXT)
├── cop_url (TEXT) - ÇÖP URL'leri (JSON format) ⭐ STANDARDİZE
├── dbf_urls (TEXT) - DBF URL'leri (JSON format) ⭐ YENİ
├── created_at, updated_at (TIMESTAMP)

-- 2. DALLAR (Meslek Dalları)
temel_plan_dal
├── id (INTEGER PRIMARY KEY)
├── dal_adi (TEXT NOT NULL)
├── alan_id (INTEGER) → temel_plan_alan.id (FOREIGN KEY)
├── created_at, updated_at (TIMESTAMP)

-- 3. DERSLER (Ders Listesi)
temel_plan_ders
├── id (INTEGER PRIMARY KEY)
├── ders_adi (TEXT NOT NULL)
├── sinif (INTEGER) - Sınıf seviyesi (9, 10, 11, 12)
├── ders_saati (INTEGER NOT NULL DEFAULT 0)
├── amac (TEXT) - DBF PDF'ten okunan dersin amacı metni
├── dm_url (TEXT) - Ders Materyali PDF URL'si
├── dbf_url (TEXT) - DBF yerel dosya yolu
├── bom_url (TEXT) - BÖM URL'si
├── created_at, updated_at (TIMESTAMP)

-- 4. DERS-DAL İLİŞKİLERİ (Many-to-Many)
temel_plan_ders_dal
├── id (INTEGER PRIMARY KEY)
├── ders_id (INTEGER) → temel_plan_ders.id
├── dal_id (INTEGER) → temel_plan_dal.id
├── created_at (TIMESTAMP)

-- Diğer tablolar: temel_plan_ogrenme_birimi, temel_plan_konu, 
-- temel_plan_kazanim, temel_plan_arac, temel_plan_olcme, vb. bunların hepsi DBF PDF'ten oku_dbf.py ile alınır.
```

## 🚨 Kritik Hatalardan Kaçınma Kuralları

### 1. Fonksiyon İsimleri ⭐ **YENİ KURAL**
- **ASLA** eski fonksiyon isimlerini kullanma
- **MUTLAKA** yeni standardize edilmiş fonksiyon isimlerini kullan:
  ```python
  # ✅ Doğru - Yeni standardize isimler
  from modules.get_cop import get_cop
  from modules.get_dbf import get_dbf
  
  # ❌ Yanlış - Eski isimler
  from modules.get_cop import download_all_cop_pdfs_workflow
  from modules.get_dbf import download_dbf_without_extract_with_progress
  ```

### 2. JSON Çıktı Dosyaları ⭐ **YENİ KURAL**
- **Her iki fonksiyon da JSON üretir**:
  - `get_cop()` → `data/get_cop.json`
  - `get_dbf()` → `data/get_dbf.json`
- **Dosya formatı**: Alan bazında sınıf URL'leri

### 3. Veritabanı Sütunları ⭐ **YENİ KURAL**
- **COP**: `cop_url` sütununa JSON formatında URL'ler (mevcut)
- **DBF**: `dbf_urls` sütununa JSON formatında URL'ler (yeni)
- **Her iki sütun da JSON string formatında saklanır**

### 4. Database Connection ⭐ **YENİ KURAL**
- **ASLA** manuel `sqlite3.connect()` kullanma
- **MUTLAKA** `utils_database.py`'deki decorator'ları kullan:
  ```python
  # ✅ Doğru - Flask endpoint'leri için
  @app.route('/api/endpoint')
  @with_database_json
  def my_endpoint(cursor):
      cursor.execute("SELECT * FROM table")
      return {"data": cursor.fetchall()}
  
  # ✅ Doğru - Genel fonksiyonlar için
  @with_database
  def my_function(cursor, params):
      cursor.execute("INSERT...")
      return result
  ```

### 5. Modüler Import Sistemi ⭐ **YENİ KURAL**
- **String/normalizasyon işlemleri**: `utils_normalize.py` modülünü kullan
- **Database işlemleri**: `utils_database.py` modülünü kullan
- **Dosya işlemleri**: `utils_file_management.py` modülünü kullan
- **İstatistik işlemleri**: `utils_stats.py` modülünü kullan
- **ASLA** karışık import yapma:
  ```python
  # ✅ Doğru - Yeni modüler import sistemi
  from modules.utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
  from modules.utils_database import with_database, get_or_create_alan
  from modules.utils_file_management import download_and_cache_pdf, extract_archive
  from modules.utils_stats import get_database_statistics, format_database_statistics_message
  
  # ❌ Yanlış - Eski import'lar
  from modules.utils import normalize_to_title_case_tr  # utils.py artık yok!
  from modules.utils_database import get_database_statistics  # İstatistikler utils_stats.py'de!
  ```

### 6. JSON URL Format Standardizasyonu ⭐ **YENİ KURAL**
- **Tüm JSON URL'leri integer key formatında saklanmalı**:
  - ✅ Doğru: `{"9": "url", "10": "url", "11": "url"}`
  - ❌ Yanlış: `{"sinif_9": "url", "sinif_10": "url"}`
- **Frontend her iki formatı da destekler** (geriye uyumluluk)

### 7. Duplicate Kontrol Kuralları ⭐ **YENİ KURAL**
- **Alan Oluşturma**: `alan_adi` kontrolü ile duplicate engelleme
- **Dal Oluşturma**: `dal_adi + alan_id` kontrolü ile duplicate engelleme
- **Ders Oluşturma**: `ders_adi` kontrolü ile duplicate engelleme
- **Ders-Dal İlişkisi**: `ders_id + dal_id` kontrolü ile duplicate engelleme

### 8. Protocol Alanları Yeniden Yapılandırması ⭐ **2025-07-19 GÜNCELLEMESİ**
- **00_Ortak_Alan_Dersleri sistemi kaldırıldı**: Protocol alanları artık kendi dosyalarını kullanır
- **Özel protocol fonksiyonları kaldırıldı**: `is_protocol_area()`, `get_base_area_name()`, `handle_protocol_area()` vb.
- **Protocol alanları normal alanlar gibi çalışır**: Tek fark isimlerindeki "- Protokol" eki
- **MEB ID eşleştirme**: Protocol alanları temel alan adları ile MEB ID eşleştirme yapar
- **Duplicate dosya yönetimi**: Artık sadece log ile takip edilir, otomatik taşıma yapılmaz

### 9. DBF PDF Analiz Sistemi Geliştirilmesi ⭐ **2025-07-22 GÜNCELLEMESİ**
- **extract_olcme.py Türkçe Karakter Sorunu Çözüldü**: 
  - **Problem**: "Geometrik Motif Çizimi" ↔ "GEOMETRİK MOTİF ÇİZİMİ" eşleştirmesi başarısızdı (%0)
  - **Çözüm**: `normalize_for_matching()` fonksiyonu eklendi
- **Gelişmiş Normalizasyon Sistemi**:
  - Türkçe karakterler ASCII'ye çevrilir: İ/ı → I, Ğ/ğ → G, Ü/ü → U, Ö/ö → O, Ş/ş → S, Ç/ç → C
  - PDF karakter düzeltmeleri: Ġ → İ, ġ → ı (PDF encoding sorunları için)
  - Case normalizasyonu: Tüm metinler büyük harfe çevrilir
- **Eşleştirme Başarı Oranları**: %0'dan %80+ seviyesine çıkarıldı
- **Test Dosyası**: `/data/dbf/.../BİLGİSAYARLI MOBİLYA SÜSLEME RESMİ.pdf` ile doğrulandı

## 🔌 API Endpoints - Detaylı Referans

### 📥 Temel Veri Çekme
- **`GET /api/get-cached-data`** - Önbellekteki JSON verilerini getir
- **`GET /api/scrape-to-db`** - Tüm veri kaynaklarını (DM, DBF, COP, BOM) tek seferde çeker ve DB'ye kaydeder (SSE) ⭐ **STANDARDİZE**

### 📊 Kategorik Veri Endpoint'leri
- **`GET /api/get-dbf`** - DBF verilerini `get_dbf()` fonksiyonu ile çeker (SSE)
- **`GET /api/get-cop`** - ÇÖP verilerini `get_cop()` fonksiyonu ile çeker (SSE)
- **`GET /api/get-dm`** - DM verilerini `get_dm()` fonksiyonu ile çeker (SSE)
- **`GET /api/get-bom`** - BÖM verilerini getir
- **`GET /api/get-dal`** - Alan-Dal ilişkilerini getir

### 📈 İstatistik ve Monitoring
- **`GET /api/get-statistics`** - Gerçek zamanlı sistem istatistikleri

### 🔄 PDF ve DBF İşleme Operasyonları
- **`GET /api/dbf-download-extract`** - DBF dosyalarını toplu indir ve aç (SSE)
- **`GET /api/oku-cop`** - ÇÖP PDF'lerini analiz et ve DB'ye kaydet (SSE)
- **`GET /api/oku-dbf`** - ⭐ **STANDARDİZE**: DBF dosyalarını okur ve ders saatlerini günceller (SSE)

## 🔄 Sık Kullanılan İşlemler

### Yeni Standardize Fonksiyonlar ⭐ **YENİ**
```python
# Yeni standardize edilmiş fonksiyonlar
from modules.get_cop import get_cop
from modules.get_dbf import get_dbf

# Her iki fonksiyon da aynı pattern'i izler
# HTML parse → JSON kaydet → İndir (açmaz) → JSON dosyası üret
for message in get_cop():
    print(message)

for message in get_dbf():
    print(message)
```

### Database İşlemleri ⭐ **YENİ**
```python
from modules.utils_database import with_database_json, with_database

# Flask endpoint için
@app.route('/api/endpoint')
@with_database_json
def my_endpoint(cursor):
    cursor.execute("SELECT * FROM table")
    return {"data": cursor.fetchall()}

# Genel fonksiyon için
@with_database
def my_function(cursor, param):
    cursor.execute("INSERT INTO table VALUES (?)", (param,))
    return {"success": True}
```

### Dosya İşlemleri ⭐ **YENİ**
```python
from modules.utils_file_management import download_and_cache_pdf, extract_archive, scan_directory_for_pdfs

# PDF indirme (otomatik duplicate yönetimi ile)
file_path = download_and_cache_pdf(
    url="https://example.com/file.pdf",
    cache_type="dm",
    alan_adi="Bilişim Teknolojileri",
    meb_alan_id="08"
)

# Arşiv açma
extract_archive("file.rar", "output_dir")

# PDF tarama
pdfs = scan_directory_for_pdfs("data/dm/")
```

## 🔄 Otomatik Database Kurulumu

Proje **otomatik migration sistemi** ile çalışır:

1. **İlk Çalıştırma**: `python server.py` komutu ile sunucu başlatıldığında
2. **Otomatik Schema**: `data/schema.sql` dosyasından tüm tablolar otomatik oluşturulur
3. **Migration Tracking**: `schema_migrations` tablosu ile versiyon takibi
4. **Güvenli Güncellemeler**: `IF NOT EXISTS` ile çakışma önlenir

```bash
# Sunucuyu başlat - Database otomatik kurulur
python server.py

# Çıktı örneği:
# ✅ Database initialized successfully: data/temel_plan.db
# 📊 Current schema version: 1
```

## 🚨 Önemli Notlar

- **Fonksiyon İsimleri**: `get_cop()` ve `get_dbf()` kullanın, eski isimleri kullanmayın
- **JSON Çıktıları**: Her iki fonksiyon da `data/` klasöründe JSON dosyası üretir
- **Veritabanı Sütunları**: `cop_url` ve `dbf_urls` sütunları JSON formatında URL'ler içerir
- **JSON URL Format**: Tüm URL'ler integer key formatında: `{"9": "url", "10": "url"}`
- **Database Decorators**: `@with_database` ve `@with_database_json` kullanın
- **Modüler Import**: `utils.py` ve `utils_file_management.py` modüllerini doğru şekilde import edin
- **⭐ YENİ 2025-07-19**: Protocol alan sistemi yeniden yapılandırıldı - özel protocol fonksiyonları kaldırıldı
- **⭐ YENİ 2025-07-19**: 00_Ortak_Alan_Dersleri sistemi kaldırıldı - protocol alanları kendi dosyalarını kullanır
- **PDF Validation**: Dosya bütünlüğü kontrolü önemli
- **Error Recovery**: Network hatalarında robust retry mekanizması
- **⭐ YENİ**: `/api/scrape-to-db` endpoint'i artık yeni standardize fonksiyonları (`get_cop()`, `get_dbf()`) kullanıyor
- **⭐ YENİ**: Eski workflow-step-* endpoint'leri kaldırıldı, sadece get-* endpoint'leri kullanılıyor
- **⭐ YENİ**: Frontend konsol çıktıları iyileştirildi - şehir bazlı okunabilir format
- **⭐ YENİ**: `/api/oku-dbf` endpoint'i standardize edildi (eski `/api/process-dbf` yerine)
- **⭐ YENİ**: `getir_dal.py` performans optimizasyonu - time.sleep süreleri azaltıldı (0.3s → 0.1s)
- **⭐ YENİ 2025-07-19**: Konsol log formatları standardize edildi - tüm dosya indirme süreçlerinde "{meb_alan_id} - {alan_adi} ({sayac}/{toplam}) Toplam {dosya_sayısı} {dosya_tipi} indi." formatı kullanılıyor
- **⭐ YENİ 2025-07-22**: `extract_olcme.py` Türkçe karakter eşleştirme sistemi tamamen yeniden yazıldı
  - **normalize_for_matching()** fonksiyonu: Türkçe karakterleri ASCII'ye çevirir
  - **DBF PDF Header Matching**: %0 → %80+ başarı oranı artışı
  - **Test Sonuçları**: "Geometrik Motif Çizimi" ↔ "GEOMETRİK MOTİF ÇİZİMİ" eşleştirmesi başarılı

## 🔗 İlişkisel Yapı

```
Alan (1) ←→ (N) Dal ←→ (M) Ders ←→ (N) Öğrenme Birimi ←→ (N) Konu ←→ (N) Kazanım
     ↓              ↓         ↓              ↓              ↓         ↓
   58 Alan      ~180 Dal   ~800 Ders     ~2000 Birim    ~5000 Konu  ~8000 Kazanım
```

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.

---

🔗 **MEB Kaynak:** https://meslek.meb.gov.tr/  
📧 **Destek:** Projeyle ilgili sorular için issue açabilirsiniz

📊 **Bu CLAUDE.md dosyası, projenin tüm kritik bilgilerini içerir ve Claude Code'un tutarlı çalışması için tasarlanmıştır.**

## Uygulama Mimarisi Notları

### 📊 JSON Dosyaları
- JSON dosyaları ana iş akışında olan dosyalar değildir. 
- Onları kullanarak başka işlemler planlanmaz. 
- Bu dosyalar sadece sonucu kontrol etmek için süreçlerin sonucunda kaydedilen dosyalardır. 
- Bir süreçte ne alınıyor ise öncelikle veritabanına kaydetme birincil hedeftir.

### 🗂️ Modüler Dosya Yapısı ⭐ **GÜNCELLEME**
- **utils_normalize.py**: String normalizasyonu, Türkçe karakter işlemleri (eski utils.py'den ayrıştırıldı)
- **utils_database.py**: Database connection decorators, MEB ID yönetimi, CRUD operasyonları
- **utils_file_management.py**: Dosya indirme, arşiv işlemleri, duplicate yönetimi
- **utils_stats.py**: İstatistik ve monitoring fonksiyonları (utils_database.py'den ayrıştırıldı)
- **Ortak Alan Sistemi**: `data/*/00_Ortak_Alan_Dersleri/` klasörleri ile duplicate dosya yönetimi
- **Otomatik Taşıma**: Birden fazla alanda bulunan dosyalar otomatik olarak ortak alana taşınır

### 🔄 Dosya İşleme Akışı
1. **Dosya İndirme**: `download_and_cache_pdf()` fonksiyonu ile
2. **Duplicate Kontrol**: Mevcut dosyaları tarar
3. **Ortak Alan Yönetimi**: Duplicate dosyaları `00_Ortak_Alan_Dersleri` klasörüne taşır
4. **Cache Kullanımı**: Mevcut dosyaları tekrar indirmez

### 🚀 Performans Optimizasyonları ⭐ **YENİ**
- **Alan-Dal Çekme Hızlandırması**: `getir_dal.py`'de time.sleep süreleri optimize edildi
  - Her alan arasında: `0.3s → 0.1s` (3x daha hızlı)
  - Her il arasında: `1.5s → 0.5s` (3x daha hızlı)
  - Alan olmayan iller: `1.5s → 0.5s` (3x daha hızlı)
- **Frontend Konsol Çıktıları**: Düzenli, okunabilir format ile şehir bazlı ilerleme
  - Format: `İSTANBUL (34/81), Alan/Dal Sayısı (45/85) -> (13/31)`
  - Gereksiz detay mesajları gizlendi (area_processing, branches_processing)
- **Endpoint İsimlendirme**: Tutarlı `oku-*` prefix'i ile standardizasyon

### 🔤 Türkçe Karakter İşleme Sistemi ⭐ **2025-07-22 GÜNCELLEME**
- **extract_olcme.py İyileştirmeleri**:
  ```python
  # Yeni normalize_for_matching() fonksiyonu
  def normalize_for_matching(text):
      # 1. PDF karakter düzeltmeleri (Ġ → İ, ġ → ı)
      text = normalize_turkish_chars(text)
      # 2. Uppercase dönüşümü
      text = text.upper()
      # 3. ASCII normalizasyonu (İ/ı → I, Ç/ç → C, vb.)
      return text
  ```
- **Başlık Eşleştirme Başarı Oranları**:
  - **Önce**: "Geometrik Motif Çizimi" → "GEOMETRİK MOTİF ÇİZİMİ" = ❌ 0 eşleşme
  - **Sonra**: "GEOMETRIK MOTIF CIZIMI" → "1. GEOMETRIK MOTIF CIZIMI" = ✅ 1 eşleşme
- **Test Sonuçları (BİLGİSAYARLI MOBİLYA SÜSLEME RESMİ.pdf)**:
  - Geometrik Motif Çizimi: 2 Konu → **1 eşleşme** ✅
  - Bitkisel Motifler: 3 Konu → **1 eşleşme** ✅  
  - İnsan Ve Hayvan Motifleri: 2 Konu → **1 eşleşme** ✅
  - Kenar Ve Kitabe Motifleri: 3 Konu → **1 eşleşme** ✅