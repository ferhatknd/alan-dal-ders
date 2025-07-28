# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 MEB Mesleki Eğitim Veri İşleme Projesi - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı birleşik kılavuzudur. README.md, is_akisi.md ve teknik detayların tümünü içerir. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-28 (Environment Variable sistemi eklendi - çoklu bilgisayar desteği)

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

**Environment Setup (Çoklu Bilgisayar Desteği):**
```bash
# 1. .env dosyasını kontrol et ve PROJECT_ROOT'u ayarla
# İş bilgisayarı (mevcut):
# PROJECT_ROOT=/Volumes/Dropbox2TB/Estherian Dropbox/Ferhat Kondakcı/github/alan-dal-ders

# Ev bilgisayarı için örnek:
# PROJECT_ROOT=C:\Users\YourName\Documents\GitHub\alan-dal-ders

# 2. python-dotenv paketini yükle (yeni dependency)
pip install python-dotenv

# 3. Sunucuyu başlat
python server.py  # İlk çalıştırmada otomatik setup
```

**Ortak Geliştirme Komutları:**
```bash
# always use single responsibility principle when creating new method

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
- **`modules/oku_dbf.py`** - ⭐ **DBF Koordinatörü**: PDF okuma işlemleri utils_oku_dbf.py'ye taşındı, sadece koordinasyon ve veritabanı entegrasyonu yapar
- **`modules/utils_oku_dbf.py`** - ⭐ **YENİ MODÜL**: DBF PDF okuma fonksiyonları (extract_olcme.py'den kopyalandı, 48.4% başarı oranı)
- **`modules/get_dbf.py`** - ⭐ **STANDARDİZE**: `get_dbf()` fonksiyonu ile DBF verilerini çeker, RAR/ZIP indirir (açmaz), `data/get_dbf.json` üretir ve `dbf_urls` sütununa JSON kaydeder
- **`test_unzip.py`** - ⭐ **YENİ AYIRIM**: DBF RAR/ZIP dosyalarını açan standalone script, `modules.utils_file_management.extract_archive` kullanır
- **`modules/get_cop.py`** - ⭐ **STANDARDİZE**: `get_cop()` fonksiyonu ile ÇÖP verilerini çeker, PDF indirir (açmaz), `data/get_cop.json` üretir ve `cop_url` sütununa JSON kaydeder
- **`modules/oku_cop.py`** - ⭐ **YENİ**: COP PDF parsing ve analiz modülü - Tamamen yeniden yazıldı
- **`modules/get_dm.py`** - Ders Materyalleri (DM) verilerini çeker
- **`modules/get_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker
- **`modules/get_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils_normalize.py`** - ⭐ **YENİ AYIRIM**: String normalizasyon fonksiyonları, Türkçe karakter normalizasyonu (eski utils.py'den ayrıştırıldı)
- **`modules/utils_database.py`** - ⭐ **YENİ**: Veritabanı işlemleri modülü, **database connection decorators**, **MEB ID yönetimi** ve **CRUD operasyonları**
- **`modules/utils_file_management.py`** - ⭐ **YENİ**: Dosya işlemleri modülü, **ortak alan dosya sistemi**, **duplicate dosya yönetimi** ve **arşiv işlemleri**
- **`modules/utils_stats.py`** - ⭐ **YENİ AYIRIM**: İstatistik ve monitoring fonksiyonları (utils_database.py'den ayrıştırıldı)
- **`modules/utils_env.py`** - ⭐ **YENİ 2025-07-28**: Environment variable yönetimi, PROJECT_ROOT desteği, çoklu bilgisayar uyumluluğu

### 🌐 Frontend Dosyaları
- **`src/App.js`** - ⭐ **YENİLENDİ**: Tek satır workflow UI, console panel, JSON popup'sız tasarım
- **`src/App.css`** - Ana stil dosyası
- **`package.json`** - Node.js bağımlılıkları ve scriptler
- **`src/index.js`** - React uygulaması entry point
- **`src/setupProxy.js`** - CORS proxy ayarları
- **`src/reportWebVitals.js`** - Performance monitoring

### 🗂️ Veri ve Veritabanı
- **`data/temel_plan.db`** - SQLite veritabanı dosyası ⭐ **UPDATED**: PROJECT_ROOT env variable bazlı path
- **`data/schema.sql`** - Veritabanı schema dosyası ⭐ **UPDATED**: PROJECT_ROOT env variable bazlı path
- **`data/get_cop.json`** - ⭐ **UPDATED**: COP verilerinin JSON çıktısı (env aware path)
- **`data/get_dbf.json`** - ⭐ **UPDATED**: DBF verilerinin JSON çıktısı (env aware path)
- **`data/get_dm.json`** - ⭐ **UPDATED**: DM verilerinin JSON çıktısı (env aware path)
- **`.env`** - ⭐ **YENİ 2025-07-28**: Environment variables (PROJECT_ROOT tanımı)
- **`data/`** - JSON cache dosyaları, veritabanı ve schema dosyaları ⭐ **UPDATED**: Tüm path'ler PROJECT_ROOT bazlı
  - `dbf/` - İndirilen DBF dosyaları (alan klasörleri halinde)
  - `cop/` - ÇÖP PDF dosyaları
  - `dm/` - Ders Materyali dosyaları ⭐ **YENİ**: `00_Ortak_Alan_Dersleri` klasörü ile duplicate dosya yönetimi
  - `bom/` - BÖM dosyaları

### 🐛 Debug ve Test Araçları
- **`test.py`** - DBF PDF tablo yapısını detaylı analiz eden debug script
- **`extract_olcme.py`** - ⭐ **2025-07-26 GÜNCELLEME**: DBF PDF analiz ve başlık eşleştirme test script'i  
  - **Simple String Matching**: BERT/Semantic sistemi kaldırıldı, basit case-insensitive string matching kullanır
  - **Pattern Matching**: Madde numaraları için "1. " veya "1 " pattern'i kullanır
  - **PyMuPDF**: PDF okuma işlemleri PyPDF2'den PyMuPDF'e dönüştürüldü
  - **✅ YENİ**: Basit text normalizasyonu ve hızlı string eşleştirme sistemi
  - **📝 Fonksiyon Adları**: `ex_kazanim_tablosu()` - Kazanım tablosu çıkarma, `ex_temel_bilgiler()` - Temel ders bilgilerini çıkarma, `get_all_dbf_files()` - PDF/DOCX dosya yönetimi (API optimize)
  - **🔧 Header Pattern**: Çoklu pattern sistemi ile farklı tablo başlık formatlarını destekler (5 farklı pattern)

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

### 📚 Modüler Sistem Yapısı
- **`modules/utils_oku_dbf.py`** (Ana PDF işleme fonksiyonları):
  - `process_dbf_file()` - Tek DBF dosyası işleme
  - `process_multiple_dbf_files()` - Çoklu DBF dosyası işleme
  - `get_all_dbf_files()` - Dosya tarama ve validation
  - `ex_kazanim_tablosu()` - Kazanım tablosu çıkarma
  - `ex_temel_bilgiler()` - Temel ders bilgileri çıkarma
  - `extract_ob_tablosu()` - Öğrenme birimi analizi
- **`modules/oku_dbf.py`** (Koordinasyon fonksiyonları):
  - `DBFProcessor` sınıfı - Koordinasyon ve istatistik yönetimi
  - `oku_dbf()` - Legacy uyumluluk fonksiyonu
  - `process_dbf_archives_and_read()` - Arşiv işleme workflow
- **`modules/oku_cop.py`** (COP işleme fonksiyonları):
  - `extract_alan_dal_from_table_headers()` - Alan/dal bilgisi çıkarma
  - `extract_ders_info_from_schedules()` - Ders programı analizi  
  - `process_cop_file()` - Ana ÇÖP dosya işleme
- **`modules/utils_env.py`** (Environment yönetimi - YENİ 2025-07-28):
  - `get_project_root()` - PROJECT_ROOT environment variable okuma
  - `get_data_path()` - data/ klasörü altında path oluşturma
  - `get_output_json_path()` - JSON çıktı dosyası path'leri

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

### 6. PyMuPDF Migration Kuralları ⭐ **2025-07-27 YENİ**
- **DOCX İşleme**: Artık PyMuPDF ile yapılır, python-docx tamamen kaldırıldı
- **Unified Processing**: PDF ve DOCX dosyaları aynı API ile işlenir (`fitz.open`)
- **Table Extraction**: `page.find_tables()` ve `table.extract()` kullanılır
- **Dependency Cleanup**: requirements.txt'den python-docx kaldırıldı
- **Performance**: Tek kütüphane kullanımı ile daha tutarlı performans
- **Code Examples**:
  ```python
  # ✅ YENİ YÖNTEM (PyMuPDF for DOCX)
  doc = fitz.open(file_path)  # PDF ve DOCX için aynı
  for page_num in range(len(doc)):
      page = doc.load_page(page_num)
      tables = page.find_tables()
      for table in tables:
          data = table.extract()
  
  # ❌ ESKİ YÖNTEM (python-docx - Kaldırıldı)
  doc = docx.Document(file_path)
  for table in doc.tables:
      for row in table.rows:
          for cell in row.cells:
              text = cell.text
  ```

### 7. Simple String Matching Kuralları ⭐ **2025-07-26 YENİ YAKLAŞIM**
- **Case-Insensitive Matching**: `.upper()` kullanarak büyük/küçük harf farkını yok say
- **Pattern Matching**: Madde numaraları için "1. " veya "1 " pattern'i kullan, basit find() değil
- **Basic Normalization**: Sadece `re.sub(r'\\s+', ' ', text.strip())` ile whitespace normalizasyonu
- **Performance**: BERT/AI işlemlerine göre çok daha hızlı, basit string operations

### 8. Madde Numarası Pattern Matching ⭐ **KORUNAN KURAL**
- **ASLA** basit `find("2")` kullanma - "15-20. yüzyıllara" içindeki "20"yi bulur (YANLIŞ)
- **MUTLAKA** pattern kullan: `find("2. ")` veya `find("2 ")` - Sadece gerçek konu numaralarını bulur (DOĞRU)
- **Tarih Aralıkları**: "15-20", "1950-1960" gibi ifadeler konu numarası olarak algılanmamalı
- **Sequential Processing**: Konu numaraları sıralı olarak işlenmeli (1, 2, 3, 4, 5...)

### 9. Environment Variable Path Management ⭐ **YENİ 2025-07-28**
- **ASLA** hardcoded path kullanma - `/Users/ferhat/...` veya `C:\Users\...` gibi
- **MUTLAKA** `utils_env.py` modülünü kullan:
  ```python
  # ✅ Doğru - Environment aware path sistemi
  from modules.utils_env import get_project_root, get_data_path, get_output_json_path
  
  project_root = get_project_root()  # .env'den PROJECT_ROOT okur
  dbf_path = get_data_path("dbf")    # PROJECT_ROOT/data/dbf
  json_path = get_output_json_path("get_cop.json")  # PROJECT_ROOT/data/get_cop.json
  
  # ❌ Yanlış - Hardcoded paths
  base_path = "/Users/ferhat/github/alan-dal-ders/data/dbf"  # Sadece bir bilgisayarda çalışır!
  json_path = "data/get_cop.json"  # Relative path, çalışma dizinine bağımlı
  ```
- **Çoklu Bilgisayar Desteği**: `.env` dosyasında PROJECT_ROOT tanımla, her bilgisayarda farklı olabilir
- **Fallback Davranış**: PROJECT_ROOT tanımlı değilse `os.getcwd()` kullanılır

## 🔄 Son Güncelleme Detayları - 2025-07-28

### ✅ Environment Variable Sistemi Eklendi:

1. **Çoklu Bilgisayar Desteği**:
   - **Yeni Modül**: `modules/utils_env.py` - Environment variable yönetimi
   - **PROJECT_ROOT**: `.env` dosyasından path okuma sistemi
   - **Cross-Platform**: Windows, macOS, Linux desteği ✅

2. **Path Management Sistemi**:
   - **Hardcoded Path'ler Kaldırıldı**: `/Users/ferhat/...` gibi sabit path'ler kaldırıldı
   - **Dynamic Path**: `get_project_root()`, `get_data_path()`, `get_output_json_path()` fonksiyonları
   - **Fallback Mechanism**: PROJECT_ROOT yoksa `os.getcwd()` kullanılır ✅

3. **Güncellenen Modüller**:
   - **utils_oku_dbf.py**: DBF dosya tarama sistemi env aware
   - **server.py**: Veritabanı ve schema path'leri env bazlı
   - **get_cop.py, get_dbf.py, get_dm.py**: JSON output path'leri env aware
   - **requirements.txt**: `python-dotenv` dependency eklendi ✅

4. **Configuration**:
   - **`.env` Dosyası**: PROJECT_ROOT tanımı ve örnekler
   - **Setup Instructions**: İş/ev bilgisayarı için farklı path ayarları
   - **Debug Output**: Path kontrolü için konsol mesajları ✅

## 🔄 Önceki Güncelleme Detayları - 2025-07-27

### ✅ Modüler API Sistemi Tamamlandı:

1. **Fonksiyon Adı Güncelleme**:
   - **Eski**: `komutlar()` fonksiyonu (komut satırı aracı döneminden kalma)
   - **Yeni**: `get_all_dbf_files()` fonksiyonu (API sistemi için optimize)
   - **Amaç**: Sadece API istekleri ile çalışma, komut satırı aracı özelliklerinin kaldırılması ✅

2. **Kod Temizleme**:
   - **Kaldırılan**: `komutlar()` fonksiyonundaki rastgele seçim, string arama gibi komut satırı özellikleri
   - **Korunan**: Dosya validation, bozuk dosya tespiti, PyMuPDF unified processing
   - **Sonuç**: Daha temiz ve API odaklı kod yapısı ✅

3. **Import Güncelleme**:
   - **server.py**: `komutlar` → `get_all_dbf_files` 
   - **modules/oku_dbf.py**: Import güncellendi
   - **dbf_isleme_istatistik.py**: Test scripti güncellendi
   - **Sonuç**: Tüm sistem yeni API yapısına uyumlu ✅

### ✅ PyMuPDF Migration Tamamlandı:

1. **python-docx Dependency Kaldırıldı**:
   - **Kaldırılan**: python-docx paketi requirements.txt'den kaldırıldı
   - **Sonuç**: Daha az dependency, daha temiz kurulum ✅

2. **DOCX Processing → PyMuPDF**:
   - **Eski Sistem**: python-docx ile DOCX tablo okuma (ayrı API)
   - **Yeni Sistem**: PyMuPDF ile PDF ve DOCX için unified processing (tek API)
   - **Performance**: Daha tutarlı ve güvenilir tablo çıkarma ✅

3. **Code Standardization**:
   - **Unified API**: `fitz.open()` ile PDF ve DOCX dosyaları aynı şekilde işlenir
   - **Table Processing**: `page.find_tables()` ve `table.extract()` standardı
   - **Sonuç**: Daha temiz ve maintainable kod ✅

### 🔧 Teknik Değişiklikler:

1. **modules/oku_dbf.py - PyMuPDF Migration**:
   ```python
   # ❌ KALDIRILAN (python-docx)
   import docx
   doc = docx.Document(file_path)
   for table in doc.tables:
       for row in table.rows:
           for cell in row.cells:
               text = cell.text
   
   # ✅ YENİ YÖNTEM (PyMuPDF)
   import fitz
   doc = fitz.open(file_path)
   for page_num in range(len(doc)):
       page = doc.load_page(page_num)
       tables = page.find_tables()
       for table in tables:
           data = table.extract()
   ```

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
- **`GET /api/dbf-download-extract`** - ⭐ **ESKİ SİSTEM**: DBF dosyalarını toplu indir ve aç (SSE) - Artık manuel unzip kullanılıyor
- **`GET /api/oku-cop`** - ÇÖP PDF'lerini analiz et ve DB'ye kaydet (SSE)
- **`GET /api/oku-dbf`** - ⭐ **STANDARDİZE**: Çıkarılmış DBF PDF/DOCX dosyalarını okur ve `temel_plan_ders.dbf_url` sütununa kaydeder (SSE)

## 🔄 DBF İşleme Workflow - 3 Aşamalı Sistem ⭐ **YENİ AÇIKLAMA**

### Aşama 1: DBF RAR Dosyalarını İndirme
```bash
# Frontend: "Getir DBF" butonuna basıldığında
GET /api/get-dbf
```
- `modules/get_dbf.py` ile meslek.meb.gov.tr'den RAR/ZIP dosyaları indirilir
- İndirilen dosyalar `data/dbf/alan_adi/` klasörlerine kaydedilir
- `temel_plan_alan.dbf_urls` sütununa JSON formatında RAR URL'leri kaydedilir
- **ÖNEMLI**: Bu aşamada RAR dosyaları açılmaz, sadece indirilir

### Aşama 2: RAR Dosyalarını Manuel Açma
```bash
# Terminal'de manuel çalıştırma
python test_unzip.py data/dbf
```
- `test_unzip.py` script'i `data/dbf/` dizinindeki tüm RAR/ZIP dosyalarını tarar
- `modules.utils_file_management.extract_archive` fonksiyonu ile dosyalar açılır
- Açılan PDF/DOCX dosyaları alan klasörleri içinde organize edilir
- Her RAR dosyası kendi klasöründe açılır (örn: `data/dbf/Bilisim_Teknolojileri/9_sinif_ders.pdf`)

### Aşama 3: PDF/DOCX Dosyalarını Okuma ve Veritabanı Kaydı
```bash
# Frontend: "Oku DBF" butonuna basıldığında
GET /api/oku-dbf
```
- `modules/oku_dbf.py` ile açılmış PDF/DOCX dosyaları okunur
- Her dosyadan ders bilgileri, öğrenme birimleri, konular ve kazanımlar çıkarılır
- Ders adı eşleştirmesi yapılarak `temel_plan_ders.dbf_url` sütununa dosya yolu kaydedilir
- İlişkisel tablolara (ogrenme_birimi, konu, kazanim) veriler eklenir

### İş Akışı Özeti
```
1. "Getir DBF" → RAR indir → temel_plan_alan.dbf_urls (JSON)
2. "python test_unzip.py data/dbf" → RAR aç → PDF/DOCX dosyaları
3. "Oku DBF" → PDF oku → temel_plan_ders.dbf_url (dosya yolu)
```

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

### DBF İşleme Sistemi ⭐ **YENİ**
```python
from modules.utils_oku_dbf import get_all_dbf_files, process_dbf_file

# Tüm DBF dosyalarını API sistemi için al
all_files = get_all_dbf_files(validate_files=True)

# Tek dosya işle
result = process_dbf_file(file_path)
print(f"Başarı: {result['success']}")
print(f"Temel bilgiler: {result['temel_bilgiler']}")
print(f"Kazanım tablosu: {result['kazanim_tablosu_data']}")
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

### PyMuPDF Unified Processing ⭐ **YENİ**
```python
import fitz

# PDF ve DOCX için aynı API
doc = fitz.open(file_path)  # .pdf veya .docx dosyası

# Tablo çıkarma
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    tables = page.find_tables()
    for table in tables:
        data = table.extract()
        # data[row_idx][col_idx] şeklinde erişim

doc.close()
```

### Environment İşlemleri ⭐ **YENİ 2025-07-28**
```python
from modules.utils_env import get_project_root, get_data_path, get_output_json_path

# PROJECT_ROOT'u al
project_root = get_project_root()  # .env'den PROJECT_ROOT okur

# Data klasörü path'leri
dbf_path = get_data_path("dbf")    # PROJECT_ROOT/data/dbf
cop_path = get_data_path("cop")    # PROJECT_ROOT/data/cop

# JSON output path'leri  
cop_json = get_output_json_path("get_cop.json")  # PROJECT_ROOT/data/get_cop.json
dbf_json = get_output_json_path("get_dbf.json")  # PROJECT_ROOT/data/get_dbf.json
```

## 🚨 Önemli Notlar

- **Fonksiyon İsimleri**: `get_cop()` ve `get_dbf()` kullanın, eski isimleri kullanmayın
- **JSON Çıktıları**: Her iki fonksiyon da `data/` klasöründe JSON dosyası üretir
- **Veritabanı Sütunları**: 
  - `temel_plan_alan.cop_url` - ÇÖP PDF URL'leri (JSON format)
  - `temel_plan_alan.dbf_urls` - DBF RAR dosya URL'leri (JSON format)
  - `temel_plan_ders.dbf_url` - İşlenmiş DBF PDF/DOCX dosya yolları (string format)
- **⭐ YENİ DBF Workflow**: 3 aşamalı sistem - İndir RAR → Manuel unzip → Oku PDF/DOCX
- **Database Decorators**: `@with_database` ve `@with_database_json` kullanın
- **Modüler Import**: Doğru modüllerden import yapın (`utils_*.py`)
- **⭐ YENİ 2025-07-28**: Environment Variable sistemi - çoklu bilgisayar desteği
- **⭐ YENİ 2025-07-28**: `utils_env.py` modülü - PROJECT_ROOT bazlı path yönetimi
- **⭐ YENİ 2025-07-28**: `.env` dosyası desteği - `python-dotenv` dependency
- **⭐ YENİ 2025-07-27**: PyMuPDF unified processing - PDF ve DOCX için tek API
- **⭐ YENİ 2025-07-27**: python-docx tamamen kaldırıldı, dependencies azaltıldı
- **⭐ KORUNAN**: Pattern Matching - "1. " veya "1 " kullanın, basit find() değil
- **⭐ YENİ 2025-07-26**: Simple String Matching sistemi - case-insensitive `.upper()` kullanın
- **⭐ YENİ 2025-07-27**: `komutlar()` → `get_all_dbf_files()` - API sistemi optimize

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.

---

🔗 **MEB Kaynak:** https://meslek.meb.gov.tr/  
📧 **Destek:** Projeyle ilgili sorular için issue açabilirsiniz

📊 **Bu CLAUDE.md dosyası, projenin tüm kritik bilgilerini içerir ve Claude Code'un tutarlı çalışması için tasarlanmıştır.**

## 🗺️ DBF İşleme Migration Yol Haritası - 2025-07-27

### 🎯 Migration Hedefi
`extract_olcme.py` dosyasındaki başarılı fonksiyonları `modules/oku_dbf.py` modülüne entegre etmek ve relasyonel veritabanı yapısına uygun hale getirmek.

### 📊 Mevcut Başarı Oranları (dbf_isleme_istatistik.py ile doğrulandı)
- **585 TAM EŞLEŞME** (48.4% başarı oranı)
- **1,164 toplam başlık eşleşmesi** olan dosya
- **2,407 toplam işlenen dosya**

### 🔄 Migration Fazları

#### **Faz 1: Core Function Integration**
**Target**: `extract_olcme.py` → `modules/oku_dbf.py`
```python
# Entegre edilecek fonksiyonlar:
- ex_kazanim_tablosu() → DBFExtractor.extract_kazanim_tablosu()
- extract_ob_tablosu() → DBFExtractor.extract_ogrenme_birimleri()
- ex_temel_bilgiler() → DBFExtractor.extract_course_info()
- normalize_turkish_text() → utils_normalize.py'den kullan
```

**✅ Migration Prensipleri:**
- PyMuPDF unified processing (mevcut)
- Simple string matching (case-insensitive `.upper()`)
- Pattern matching: "1. " veya "1 " kullanımı
- File integrity validation

#### **Faz 1.5: String Parsing & Hierarchy**
**Target**: String tabanlı verileri relasyonel yapıya dönüştürme
```python
# Hedef parsing sistemi:
"1. Öğrenme Birimi Adı" → temel_plan_ogrenme_birimi table
"  1.1. Konu Adı" → temel_plan_konu table  
"    1.1.1. Kazanım açıklaması" → temel_plan_kazanim table

# Parser fonksiyonları:
- parse_ob_hierarchy() - Öğrenme birimi ayrıştırma
- parse_konu_items() - Konu maddeleri ayrıştırma
- parse_kazanim_items() - Kazanım maddeleri ayrıştırma
```

#### **Faz 2: Database Integration** 
**Target**: Relasyonel veritabanı kaydetme sistemi
```python
# utils_database.py prensipleri ile:
@with_database
def save_dbf_data_relational(cursor, course_data):
    # 1. Course name resolution via COP integration
    course_name = resolve_course_name_from_cop(course_data['ders_adi'])
    
    # 2. INSERT OR IGNORE pattern (ders_adi unique key)
    cursor.execute("INSERT OR IGNORE INTO temel_plan_ders (ders_adi, ...) VALUES (?, ...)", 
                   (course_name, ...))
    
    # 3. Foreign key hierarchy: Ders → OB → Konu → Kazanım
    for ob in course_data['ogrenme_birimleri']:
        ob_id = insert_or_get_ob(cursor, ders_id, ob)
        for konu in ob['konular']:
            konu_id = insert_or_get_konu(cursor, ob_id, konu)
            for kazanim in konu['kazanimlar']:
                insert_kazanim(cursor, konu_id, kazanim)
```

#### **Faz 3: COP Integration**
**Target**: `modules/oku_cop.py` ile ders adı çözümleme
```python
from modules.oku_cop import resolve_course_name_from_cop

# Ders adı resolution sistemi:
def resolve_course_name_from_cop(dbf_course_name):
    """
    DBF'teki ders adını COP verilerinden normalize edilmiş 
    ders adı ile eşleştir
    """
    # COP veritabanından eşleşen ders adını bul
    # INSERT OR IGNORE için unique key olarak kullan
    return normalized_course_name
```

#### **Faz 4: API Enhancement**
**Target**: Mevcut `/api/oku-dbf` endpoint'ini geliştirme (YENİ ENDPOINT YARATMIYORUZ)
```python
@app.route('/api/oku-dbf')
@with_database_json
def oku_dbf_enhanced(cursor):
    """
    Mevcut endpoint'i enhancement:
    1. extract_olcme.py fonksiyonlarını kullan
    2. Relasyonel DB kaydetme yap
    3. COP integration ile ders adı çözümle
    4. SSE ile progress tracking
    """
    # Mevcut API pattern'i koruyarak enhancement
```

#### **Faz 5: Testing & Validation**
**Target**: Migration doğrulama sistemi
```python
# Test senaryoları:
1. 585 TAM EŞLEŞME dosyasının doğru parse edilmesi
2. Relasyonel veri bütünlüğü kontrolü
3. COP integration doğrulaması
4. Performance karşılaştırması (eski vs yeni sistem)
```

### 🔧 Teknik Implementation Detayları

#### **Database Schema Updates**
```sql
-- Gerekli yeni sütunlar/tablolar:
ALTER TABLE temel_plan_ders ADD COLUMN dbf_processed_at TIMESTAMP;
ALTER TABLE temel_plan_ders ADD COLUMN processing_method TEXT; -- 'extract_olcme' vs 'legacy'

-- Foreign key integrity:
temel_plan_ders (ders_adi UNIQUE) ← temel_plan_ogrenme_birimi.ders_id
temel_plan_ogrenme_birimi.id ← temel_plan_konu.ogrenme_birimi_id  
temel_plan_konu.id ← temel_plan_kazanim.konu_id
```

#### **Migration Safety**
```python
# Backward compatibility:
- Mevcut oku_dbf.py fonksiyonları deprecated olarak işaretle
- extract_olcme.py fonksiyonları side-by-side çalışsın
- Gradual migration: dosya dosya geçiş yapılabilir
- Rollback capability: eski sisteme dönüş mümkün olsun

# Error handling:
- File corruption detection (mevcut)
- Parse error recovery
- Database transaction rollback
- Progress tracking ve resume capability
```

### 🎯 Success Metrics
1. **585 perfect match dosyasının %100'ü başarılı işlenmeli**
2. **Relasyonel data integrity %100 korunmalı** 
3. **COP integration ile course name resolution %95+ başarı**
4. **Processing speed: Current system ile aynı veya daha hızlı**
5. **API backward compatibility: Mevcut frontend çalışmaya devam etmeli**

### 📋 Implementation Order
```
✅ Faz 1: Core Function Integration (Priority: HIGH)
✅ Faz 1.5: String Parsing & Hierarchy (Priority: HIGH)  
✅ Faz 2: Database Integration (Priority: HIGH)
✅ Faz 3: COP Integration (Priority: MEDIUM)
✅ Faz 4: API Enhancement (Priority: MEDIUM)
✅ Faz 5: Testing & Validation (Priority: MEDIUM)
```

### 🔗 Dependencies
- `modules/utils_database.py` - Database decorators ve CRUD
- `modules/utils_normalize.py` - String normalization
- `modules/oku_cop.py` - Course name resolution
- `extract_olcme.py` - Source functions (migration source)
- `dbf_isleme_istatistik.py` - Success validation tool

**🎯 Bu roadmap, user feedback'i doğrultusunda mevcut `/api/oku-dbf` endpoint'ini enhance etmeyi, COP integration yapmayı ve INSERT OR IGNORE pattern'ini kullanmayı hedefler.**

## Uygulama Mimarisi Notları

### Yeni Standart Kurallar

- **UYGULAMA** kelimesinin tamamı büyük harfle yazılmalıdır, diğer tüm stop words'lerde olduğu gibi.