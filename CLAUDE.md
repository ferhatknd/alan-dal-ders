# 🤖 CLAUDE.md - MEB Mesleki Eğitim Veri İşleme Projesi - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı birleşik kılavuzudur. README.md, is_akisi.md ve teknik detayların tümünü içerir. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-16 (JSON URL format standardizasyonu + Duplicate dal kontrolü eklendi + BOM dizin yapısı sadeleştirildi)

## 🎯 Proje Genel Bakış

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

## 📁 Kritik Dosya Yapısı

### 🔧 Core Backend Dosyaları
- **`server.py`** - Ana Flask sunucusu, tüm API endpoint'leri, veritabanı işlemleri ve **istatistik sistemi**
  - ⭐ **YENİ**: Merkezi database connection decorator sistemi kullanıyor

### 📊 Backend Modülleri (modules/ klasörü)
- **`modules/oku_dbf.py`** - ⭐ **YENİDEN ADLANDIRILDI**: DBF PDF parsing ve içerik analizi (eski: oku.py)
- **`modules/getir_dbf.py`** - ⭐ **STANDARDİZE**: `get_dbf()` fonksiyonu ile DBF verilerini çeker, RAR/ZIP indirir (açmaz), `data/get_dbf.json` üretir ve `dbf_urls` sütununa JSON kaydeder
- **`modules/getir_cop.py`** - ⭐ **STANDARDİZE**: `get_cop()` fonksiyonu ile ÇÖP verilerini çeker, PDF indirir (açmaz), `data/get_cop.json` üretir ve `cop_url` sütununa JSON kaydeder
- **`modules/oku_cop.py`** - ⭐ **YENİ**: COP PDF parsing ve analiz modülü - Tamamen yeniden yazıldı
- **`modules/getir_cop_oku_local.py`** - ⭐ **YENİ**: Yerel PDF dosyalarını test etmek için standalone ÇÖP okuma modülü
- **`modules/getir_dm.py`** - Ders Materyalleri (DM) verilerini çeker
- **`modules/getir_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker
- **`modules/getir_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils.py`** - ⭐ **GÜNCELLENDİ**: Yardımcı fonksiyonlar, Türkçe karakter normalizasyonu, **merkezi PDF cache yönetimi** ve **database connection decorators**

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
  - `dm/` - Ders Materyali dosyaları
  - `bom/` - BÖM dosyaları

### 🐛 Debug ve Test Araçları
- **`test.py`** - DBF PDF tablo yapısını detaylı analiz eden debug script

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

## 🔄 Aşamalı İş Akışı

### 🚀 Adım 1: Temel Veri Çekme

**Dosya**: `modules/getir_dal.py`
**Fonksiyon**: `getir_dal_with_db_integration()`

**Amaç**: Türkiye'deki tüm illerdeki okullara göre mesleki eğitim alanları ve dallarını toplar.

**İşlem Akışı**:

İşler öncelikle getir_dal.py ile başlar. Bu modül aşağıdaki işlemler ile Alan ve Dal bilgilerini çeker.

1. **İl Listesi Çekme**
   - Endpoint: `https://mtegm.meb.gov.tr/kurumlar/api/getIller.php`
   - Türkiye'deki 81 il bilgisini çeker

2. **Alan Listesi Çekme** (Her il için)
   - Endpoint: `https://mtegm.meb.gov.tr/kurumlar/api/getAlanlar.php`
   - POST data: `{"k_ilid": il_id}`
   - Her ilin mesleki eğitim alanlarını çeker

3. **Dal Listesi Çekme** (Her alan için)
   - Endpoint: `https://mtegm.meb.gov.tr/kurumlar/api/getDallar.php`
   - POST data: `{"k_ilid": il_id, "alan": alan_value}`
   - Her alanın alt dallarını çeker

4. **Veri Standardizasyonu**
   - `utils.normalize_to_title_case_tr()` ile Türkçe metin normalizasyonu
   - Tekrar eden alan/dal kontrolü

5. **Veritabanı Kaydetme**
   - `temel_plan_alan` tablosuna alanlar
   - `temel_plan_dal` tablosuna dallar (alan_id ile ilişkili)
   - Benzersizlik kontrolü ile duplicate önleme

6. **Dosya Organizasyonu**
   - `data/alan/{alan_adi}/dallar/dallar.json` yapısında yedek dosyalar
   - Her alan için klasör yapısı oluşturma

**Çıktılar**:
- Veritabanında alan/dal kayıtları
- `data/getir_dal_sonuc.json` yedek dosyası
- `data/alan/` klasör yapısı

**Performans**:
- 81 il × ortalama 50 alan × ortalama 3 dal ≈ 12,000 API çağrısı
- Rate limiting: 0.3s/dal, 1.5s/il
- Session yönetimi ile çerez korunumu

### 📄 Adım 2: Çerçeve Öğretim Programı (ÇÖP) İşleme - ⭐ STANDARDİZE

**Ana Modül**: `modules/getir_cop.py`
**Ana Fonksiyon**: `get_cop()` ⭐ **YENİ İSİM** (eski: `download_all_cop_pdfs_workflow()`)

**İşlem Akışı**:

1. **MEB Alan ID Güncelleme**
   - `update_meb_alan_ids()` fonksiyonu ile MEB'den alan ID'leri çeker
   - Veritabanındaki alanları MEB sistemi ile eşleştirir
   - `temel_plan_alan.meb_alan_id` sütununu günceller

2. **ÇÖP URL Tarama** (Paralel işlem)
   - Endpoint: `https://meslek.meb.gov.tr/cercevelistele.aspx`
   - Her sınıf için (9, 10, 11, 12) ÇÖP listesi çeker
   - BeautifulSoup ile HTML ayrıştırma
   - PDF linklerini ve güncelleme yıllarını çıkarır

3. **Merkezi PDF İndirme**
   - `utils.py`'deki `download_and_cache_pdf()` fonksiyonu kullanılır
   - `data/cop/{ID:02d}_{alan_adi}/` formatında ID bazlı klasör yapısı
   - **Dosya adı değiştirilmez** (orijinal MEB dosya adı korunur)
   - Mevcut dosya kontrolü (gereksiz indirmeleri önleme)

4. **Metadata Kaydetme**
   - Her alan için `cop_metadata.json` dosyası
   - ÇÖP bilgileri `temel_plan_alan.cop_url` sütununda JSON format
   - ⭐ **YENİ**: `data/get_cop.json` çıktı dosyası

**Çıktılar**:
- İndirilmiş ÇÖP PDF dosyaları (`data/cop/` klasöründe)
- Veritabanında `cop_url` sütununa JSON formatında URL'ler
- `data/get_cop.json` JSON çıktı dosyası ⭐ **YENİ**
- Alan bazında metadata dosyaları

**Performans**:
- 4 sınıf × 50 alan ≈ 200 PDF dosyası
- Paralel indirme (ThreadPoolExecutor)
- PDF okuma: pdfplumber kütüphanesi
- Memory efficient: geçici dosya kullanımı

### 💾 Adım 3: DBF (Ders Bilgi Formu) İşleme - ⭐ STANDARDİZE

**Ana Modül**: `modules/getir_dbf.py`
**Ana Fonksiyon**: `get_dbf()` ⭐ **YENİ İSİM** (eski: `download_dbf_without_extract_with_progress()`)

**Amaç**: Ders Bilgi Formu (DBF) verilerini çeker, indirip (açmaz) ve içeriklerini analiz eder.

**Kaynak URL**: `https://meslek.meb.gov.tr/dbflistele.aspx`

**İşlem Akışı**:

1. **DBF Link Çekme**
   - `getir_dbf(siniflar)` - DBF linklerini çeker
   - Sınıf bazında (9, 10, 11, 12) alan-DBF matrisi

2. **Dosya İndirme (Açmaz)**
   - RAR/ZIP dosyalarını indirir
   - Progress tracking ile SSE desteği
   - Retry mekanizması
   - **Açma işlemi kaldırıldı** (oku_dbf.py'ye taşındı)

3. **URL'leri Veritabanına Kaydetme** ⭐ **YENİ**
   - `dbf_urls` sütununa JSON formatında URL'ler
   - Alan bazında sınıf URL'leri gruplandırılır
   - Protokol alan handling ile otomatik alan oluşturma

4. **Dosya Organizasyonu**
```
data/dbf/
├── {ID:02d}_{Alan_Adi}/
│   ├── alan.rar (orijinal)
│   └── (açma işlemi kaldırıldı)
```

**Çıktılar**:
- İndirilmiş DBF RAR/ZIP dosyaları
- Veritabanında `dbf_urls` sütununa JSON formatında URL'ler ⭐ **YENİ**
- `data/get_dbf.json` JSON çıktı dosyası ⭐ **YENİ**

### 💾 Adım 4: Veritabanı Güncellemeleri
- **DBF Eşleştir:** İndirilen dosyalarla dersleri eşleştir
- **Ders Saatlerini Güncelle:** DBF'lerden ders saati bilgilerini çıkar (`modules/oku_dbf.py`)
- **Veritabanına Aktar:** Düzenlenmiş dersleri kaydet

## 📊 Ek Veri Modülleri

### DM (Ders Materyali) İşleme
**Dosya**: `modules/getir_dm.py`
**Kaynak URL**: 
- `https://meslek.meb.gov.tr/cercevelistele.aspx` (Alan listesi)
- `https://meslek.meb.gov.tr/dmgoster.aspx` (DM listesi)

**Kritik Mantık**:
- Sınıf → Alan → Ders hiyerarşisi
- Dinamik alan ID'lerini HTML'den çıkarma
- Fuzzy matching ile veritabanı eşleştirmesi

### BÖM (Bireysel Öğrenme Materyali) İşleme
**Dosya**: `modules/getir_bom.py`
**Kaynak URL**: `https://meslek.meb.gov.tr/moduller`

**Kritik Özellikler**:
- ASP.NET form işleme (ViewState yönetimi)
- 3 aşamalı form gönderimi (Ana sayfa → Alan seç → Ders seç)
- Paralel işleme (5 worker)
- Session yönetimi

## 📋 Modül Detayları ve Kritik Bilgiler

### 1. 📄 oku_cop.py - ⭐ **TAMAMEN YENİDEN YAZILDI**

**Amaç:** Yerel COP (Çerçeve Öğretim Programı) PDF dosyalarını analiz ederek alan, dal ve ders bilgilerini çıkarır.

**🚀 Yeni Mimari Özellikleri:**
- **Tablo Başlığı Tabanlı Alan/Dal Tespiti**: İçindekiler yerine HAFTALIK DERS ÇİZELGESİ başlıklarından okuma
- **Adjacent Column Search**: Header-data mismatch'leri için ±2 sütun arama algoritması  
- **Encoding-Safe Processing**: Türkçe karakter sorunları için robust algılama
- **Smart Filtering**: TOPLAM ve REHBERLİK satırları otomatik filtreleme
- **Clickable Output**: Terminal'de tıklanabilir PDF yolları

**Ana Fonksiyonlar:**
- `extract_alan_dal_from_table_headers(pdf)` - ⭐ **YENİ**: Tablo başlıklarından alan/dal tespiti
- `parse_schedule_table(table)` - ⭐ **İYİLEŞTİRİLDİ**: Gelişmiş tablo parsing + multi-row header desteği
- `find_dal_name_for_schedule(lines, index)` - Dal-tablo eşleştirmesi  
- `extract_ders_info_from_schedules(pdf)` - ⭐ **İYİLEŞTİRİLDİ**: Ders bilgilerini tablolardan çıkarma
- `oku_cop_pdf_file(pdf_path)` - ⭐ **YENİ**: Ana parsing fonksiyonu
- `oku_tum_pdfler(root_dir)` - Toplu PDF işleme

### 2. 📄 getir_dbf.py - ⭐ **STANDARDİZE**

**Amaç:** DBF verilerini çeker, indirir (açmaz) ve JSON formatında veritabanına kaydeder.

**Ana Fonksiyon**: `get_dbf()` ⭐ **YENİ İSİM** (eski: `download_dbf_without_extract_with_progress()`)

**🔧 Kritik Özellikler:**
- **Protokol Alan Desteği**: " - Protokol" formatını handle eder
- **Otomatik Alan Oluşturma**: Eksik alanları otomatik oluşturur
- **JSON Çıktı**: `data/get_dbf.json` dosyası üretir
- **Veritabanı Entegrasyonu**: `dbf_urls` sütununa JSON formatında URL'ler

**Protokol Alan Fonksiyonları:**
- `is_protocol_area(alan_adi)` - Protokol alan tespiti
- `get_base_area_name(protocol_name)` - ⭐ **DÜZELTİLDİ**: " - Protokol" formatını regex ile kaldırır
- `handle_protocol_area(cursor, alan_adi, alan_id)` - Protokol alan işleme
- `link_courses_to_protocol_area(cursor, base_area_id, protocol_area_id)` - Ders bağlantı kopyalama

### 3. 📄 getir_cop.py - ⭐ **STANDARDİZE**

**Amaç:** ÇÖP verilerini çeker, indirir (açmaz) ve JSON formatında veritabanına kaydeder.

**Ana Fonksiyon**: `get_cop()` ⭐ **YENİ İSİM** (eski: `download_all_cop_pdfs_workflow()`)

**🔧 Kritik Özellikler:**
- **Otomatik Alan Oluşturma**: Eksik alanları otomatik oluşturur
- **JSON Çıktı**: `data/get_cop.json` dosyası üretir
- **Veritabanı Entegrasyonu**: `cop_url` sütununa JSON formatında URL'ler
- **PDF İndirme**: Dosyaları indirir ama açmaz

### 4. 📄 utils.py - PDF Cache Yönetimi ⭐ **YENİ**

**Amaç:** Merkezi PDF indirme ve cache yönetimi sistemi.

**Yeni Fonksiyonlar:**
- `download_and_cache_pdf(url, cache_type, alan_adi, additional_info)` - Organize PDF cache sistemi
- `get_temp_pdf_path(url)` - Geçici dosya yolu oluşturma

**Cache Yapısı:** ⭐ **GÜNCEL MEB ID Bazlı Organizasyon**
```
data/
├── cop/     # Çerçeve Öğretim Programları
│   └── {meb_alan_id}_{alan_adi}/
│       └── [orijinal_dosya_adi].pdf
├── dbf/     # Ders Bilgi Formları  
│   └── {meb_alan_id}_{alan_adi}/
│       └── {alan}_dbf_package.rar
├── dm/      # Ders Materyalleri
│   └── {meb_alan_id}_{alan_adi}/
│       └── [orijinal_dosya_adi].pdf
└── bom/     # Bireysel Öğrenme Materyalleri
    └── {meb_alan_id}_{alan_adi}/
        └── {ders_adi}_{modul}.pdf
```

### 5. 📄 Database Connection Decorators ⭐ **YENİ**

**Amaç:** Merkezi database connection yönetimi ve kod tekrarını önleme.

**Yeni Fonksiyonlar:**
- `@with_database_json` - Flask endpoint'leri için decorator
- `@with_database` - Genel fonksiyonlar için decorator  
- `find_or_create_database()` - Otomatik database/schema kurulumu

**🔧 Kritik Özellikler:**

**1. Flask Endpoint Decorator:**
```python
@app.route('/api/endpoint')
@with_database_json
def my_endpoint(cursor):
    cursor.execute("SELECT * FROM table")
    return {"data": cursor.fetchall()}  # Otomatik JSON response
```

**2. Genel Fonksiyon Decorator:**
```python
@with_database
def my_function(cursor, param1, param2):
    cursor.execute("INSERT INTO table VALUES (?, ?)", (param1, param2))
    return {"success": True}
```

## 🔌 API Endpoints - Detaylı Referans

### 📥 Temel Veri Çekme
- **`GET /api/get-cached-data`** - Önbellekteki JSON verilerini getir
  - Response: Tüm modüllerin cache dosyalarından toplanan veriler
  - Headers: `application/json`
  
- **`GET /api/scrape-to-db`** - MEB'den veri çek ve DB'ye kaydet
  - Method: Server-Sent Events (SSE)
  - Response: Real-time progress updates
  - Headers: `text/event-stream`

### 📊 Kategorik Veri Endpoint'leri
- **`GET /api/get-dbf`** - ⭐ **STANDARDİZE**: DBF verilerini `get_dbf()` fonksiyonu ile çeker
  - Method: Server-Sent Events (SSE)
  - Response: Real-time progress updates
  - Process: HTML parsing → JSON kaydet → DBF indir (açmaz) → `data/get_dbf.json` üret
  
- **`GET /api/get-cop`** - ⭐ **STANDARDİZE**: ÇÖP verilerini `get_cop()` fonksiyonu ile çeker
  - Method: Server-Sent Events (SSE)
  - Response: Real-time progress updates
  - Process: HTML parsing → JSON kaydet → PDF indir (açmaz) → `data/get_cop.json` üret
  
- **`GET /api/get-dm`** - ⭐ **STANDARDİZE**: DM (Ders Materyali) verilerini `get_dm()` fonksiyonu ile çeker
  - Method: Server-Sent Events (SSE)
  - Response: Real-time progress updates
  - Process: HTML parsing → JSON kaydet → PDF indir (açmaz) → `data/get_dm.json` üret
  
- **`GET /api/get-bom`** - BÖM (Bireysel Öğrenme Materyali) verilerini getir
  - Response: BÖM modülleri, alan-ders-modül organizasyonu
  - Cache: `data/getir_bom_sonuc.json`
  
- **`GET /api/get-dal`** - Alan-Dal ilişkilerini getir
  - Response: 81 il bazında alan-dal matrisi
  - Cache: `data/getir_dal_sonuc.json`

### 📈 İstatistik ve Monitoring
- **`GET /api/get-statistics`** - ⭐ **YENİ**: Gerçek zamanlı sistem istatistikleri
  - Response: Database kayıt sayıları + disk dosya sayıları
  - Real-time: Veritabanı sorguları + dosya sistemi taraması
  - Format:
    ```json
    {
      "database": {
        "alanlar": 58,
        "dallar": 180,
        "dersler": 800
      },
      "files": {
        "dbf_files": 245,
        "cop_files": 89,
        "dm_files": 456
      }
    }
    ```

### 🔄 PDF ve DBF İşleme Operasyonları
- **`GET /api/dbf-download-extract`** - DBF dosyalarını toplu indir ve aç
  - Method: Server-Sent Events (SSE)
  - Process: RAR/ZIP indirme → Açma → Klasörleme
  - Response: Real-time download/extract progress
  
- **`GET /api/oku-cop`** - ÇÖP PDF'lerini analiz et ve DB'ye kaydet
  - Method: Server-Sent Events (SSE)
  - Process: PDF okuma → İçerik analizi → Veritabanı kaydetme
  - Uses: `modules/oku_cop.py`
  
- **`POST /api/update-ders-saatleri-from-dbf`** - DBF'lerden ders saatlerini güncelle
  - Method: Server-Sent Events (SSE)
  - Process: DBF PDF okuma → Ders saati çıkarma → DB güncelleme
  - Uses: `modules/oku_dbf.py`

### 🗄️ Veritabanı Yönetimi
- **`POST /api/dbf-match-refresh`** - DBF-Ders eşleştirmesini güncelle
  - Body: Manual eşleştirme kuralları
  - Process: Fuzzy matching → Manuel override → DB update
  
- **`POST /api/export-to-database`** - Düzenlenmiş dersleri veritabanına aktar
  - Body: Cleaned/processed ders veriler
  - Process: Validation → Conflict resolution → Bulk insert
  - Transaction: ACID compliant

## 🚨 Kritik Hatalardan Kaçınma Kuralları

### 1. Fonksiyon İsimleri ⭐ **YENİ KURAL**
- **ASLA** eski fonksiyon isimlerini kullanma
- **MUTLAKA** yeni standardize edilmiş fonksiyon isimlerini kullan:
  ```python
  # ✅ Doğru - Yeni standardize isimler
  from modules.getir_cop import get_cop
  from modules.getir_dbf import get_dbf
  
  # ❌ Yanlış - Eski isimler
  from modules.getir_cop import download_all_cop_pdfs_workflow
  from modules.getir_dbf import download_dbf_without_extract_with_progress
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
- **MUTLAKA** `utils.py`'deki decorator'ları kullan:
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

### 5. Protokol Alan İşleme ⭐ **DÜZELTİLDİ**
- **get_base_area_name()** fonksiyonu artık " - Protokol" formatını doğru handle eder
- **Regex tabanlı temizleme** ile tüm protokol varyasyonları desteklenir
- **Protokol alanları otomatik olarak base alanlara bağlanır**

### 6. Dosya İndirme vs Açma ⭐ **YENİ KURAL**
- **COP**: PDF dosyalarını indirir, açmaz
- **DBF**: RAR/ZIP dosyalarını indirir, açmaz
- **Açma işlemi**: `oku_dbf.py` ve `oku_cop.py` modüllerinde

### 7. UI Tasarımı ⭐ **YENİ KURAL**
- **ASLA** JSON popup/display ekranları ekleme
- Tüm veri gösterimleri console panel'de olmalı
- Button istatistikleri database + disk dosyalarından otomatik yüklenmeli (`/api/get-statistics`)
- Real-time logging için SSE kullan
- Aşamalı iş akışı UI ile organize edilmiş 3-adımlı süreç

### 8. JSON URL Format Standardizasyonu ⭐ **YENİ KURAL**
- **Tüm JSON URL'leri integer key formatında saklanmalı**:
  - ✅ Doğru: `{"9": "url", "10": "url", "11": "url"}`
  - ❌ Yanlış: `{"sinif_9": "url", "sinif_10": "url"}`
- **Frontend her iki formatı da destekler** (geriye uyumluluk)
- **Protokol dal duplicate kontrolü** eklendi (getir_dbf.py:218-228)

### 9. Duplicate Kontrol Kuralları ⭐ **YENİ KURAL**
- **Alan Oluşturma**: `alan_adi` kontrolü ile duplicate engelleme
- **Dal Oluşturma**: `dal_adi + alan_id` kontrolü ile duplicate engelleme
- **Ders Oluşturma**: `ders_adi` kontrolü ile duplicate engelleme
- **Ders-Dal İlişkisi**: `ders_id + dal_id` kontrolü ile duplicate engelleme
- **Protokol Dalları**: Artık duplicate kontrolü yapılıyor

### 10. BOM Dizin Yapısı ⭐ **YENİ KURAL**
- **Sadeleştirilmiş Yapı**: Ders klasörü oluşturulmaz, tüm dosyalar direkt alan klasörüne kaydedilir
- **Dosya Adlandırma**: `{ders_adi}_{modul}.pdf` formatında
- **Alan Organizasyonu**: `{meb_alan_id}_{alan_adi}/` formatında
- **Performans**: Daha az klasör, daha basit organizasyon

## 🔄 Sık Kullanılan İşlemler

### Yeni Standardize Fonksiyonlar ⭐ **YENİ**
```python
# Yeni standardize edilmiş fonksiyonlar
from modules.getir_cop import get_cop
from modules.getir_dbf import get_dbf

# Her iki fonksiyon da aynı pattern'i izler
# HTML parse → JSON kaydet → İndir (açmaz) → JSON dosyası üret
for message in get_cop():
    print(message)

for message in get_dbf():
    print(message)
```

### JSON Çıktı Kontrol ⭐ **GÜNCELLENDİ**
```python
import json

# COP verileri
with open('data/get_cop.json', 'r', encoding='utf-8') as f:
    cop_data = json.load(f)

# DBF verileri
with open('data/get_dbf.json', 'r', encoding='utf-8') as f:
    dbf_data = json.load(f)

# ⭐ YENİ FORMAT: {alan_adi: {"9": "url", "10": "url"}}
# Örnek:
# {
#   "Bilişim Teknolojileri": {
#     "9": "https://meslek.meb.gov.tr/upload/dbf9/siber.rar",
#     "10": "https://meslek.meb.gov.tr/upload/dbf10/siber.rar"
#   }
# }
```

### Veritabanı JSON Sütun Erişimi ⭐ **YENİ**
```python
import json

# COP URL'leri
cursor.execute("SELECT cop_url FROM temel_plan_alan WHERE alan_adi = ?", (alan_adi,))
cop_urls = json.loads(cursor.fetchone()['cop_url'])

# DBF URL'leri
cursor.execute("SELECT dbf_urls FROM temel_plan_alan WHERE alan_adi = ?", (alan_adi,))
dbf_urls = json.loads(cursor.fetchone()['dbf_urls'])
```

### PDF Cache Yönetimi ⭐ **YENİ**
```python
from modules.utils import download_and_cache_pdf, get_temp_pdf_path

# Organize cache sistemi
file_path = download_and_cache_pdf(
    url="https://example.com/cop.pdf",
    cache_type="cop",
    alan_adi="Bilişim Teknolojileri",
    additional_info="9_sinif_2023"
)

# Geçici dosya
temp_path = get_temp_pdf_path("https://example.com/test.pdf")
```

### Database İşlemleri ⭐ **YENİ**
```python
from modules.utils import with_database_json, with_database

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

## 🎯 Gelecek Geliştirmeler

### Planlanan Özellikler
- [ ] Incremental updates
- [ ] PDF content validation
- [ ] Auto-retry with exponential backoff
- [x] Content-based DBF matching ✅
- [x] Fonksiyon standardizasyonu ✅
- [x] Protokol alan düzeltmeleri ✅
- [ ] Real-time monitoring

### Optimizasyon Alanları
- [ ] Async processing
- [ ] Connection pooling
- [ ] Memory optimization
- [ ] Caching strategies

## 🚨 Önemli Notlar

- **Fonksiyon İsimleri**: `get_cop()` ve `get_dbf()` kullanın, eski isimleri kullanmayın
- **JSON Çıktıları**: Her iki fonksiyon da `data/` klasöründe JSON dosyası üretir
- **Veritabanı Sütunları**: `cop_url` ve `dbf_urls` sütunları JSON formatında URL'ler içerir
- **JSON URL Format**: ⭐ **YENİ** Tüm URL'ler integer key formatında: `{"9": "url", "10": "url"}`
- **Dosya İndirme**: Her iki fonksiyon da indirir ama açmaz
- **Protokol Alanları**: " - Protokol" formatı artık doğru handle edilir
- **Duplicate Kontrolü**: ⭐ **YENİ** Alan, dal, ders ve ilişkiler için tam duplicate kontrolü
- **BOM Dizin Yapısı**: ⭐ **YENİ** Sadeleştirilmiş yapı, ders klasörü yok, `{ders_adi}_{modul}.pdf` formatında
- **Database Decorators**: `@with_database` ve `@with_database_json` kullanın
- **PDF Validation**: Dosya bütünlüğü kontrolü önemli
- **Error Recovery**: Network hatalarında robust retry mekanizması

## 🔗 İlişkisel Yapı

```
Alan (1) ←→ (N) Dal ←→ (M) Ders ←→ (N) Öğrenme Birimi ←→ (N) Konu ←→ (N) Kazanım
     ↓              ↓         ↓              ↓              ↓         ↓
   58 Alan      ~180 Dal   ~800 Ders     ~2000 Birim    ~5000 Konu  ~8000 Kazanım
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

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.

---

🔗 **MEB Kaynak:** https://meslek.meb.gov.tr/  
📧 **Destek:** Projeyle ilgili sorular için issue açabilirsiniz

📊 **Bu CLAUDE.md dosyası, projenin tüm kritik bilgilerini içerir ve Claude Code'un tutarlı çalışması için tasarlanmıştır.**