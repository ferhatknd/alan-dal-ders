# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 MEB Ünitelendirilmiş Yıllık Plan Üretme Otomasyonu - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim kaynaklarından aldığı belgelerle Ünitelendirilmiş Yıllık Plan Üretme Otomasyonunun kapsamlı kılavuzudur. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-30 (Schema uyumsuzluk düzeltmeleri, öğrenme birimi yükleme sorunu çözümü ve debug log temizliği)

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

# 1. .env dosyasını kontrol et ve PROJECT_ROOT'u ayarlama örneği:
# PROJECT_ROOT=/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders

# 2. DOCX to PDF conversion için LibreOffice kurulumu (opsiyonel, ama önerilen):
# macOS:
brew install --cask libreoffice

# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install libreoffice

# Windows:
# https://www.libreoffice.org/download/download/ adresinden indirin

# LibreOffice kurulu değilse PyMuPDF fallback kullanılır (düşük kalite)

### Ana Amaç
Türkiye Cumhuriyeti Millî Eğitim Bakanlığı'na (MEB) bağlı Mesleki ve Teknik Eğitim Genel Müdürlüğü'nün web sitesinden (`meslek.meb.gov.tr`) mesleki eğitim verilerini otomatik olarak çeker, işler ve SQLite veritabanında yapılandırılmış şekilde saklar. Bu yapılandırılmış veri tabanı https://github.com/dogrucevap/node-yillikplan adresinde reposu bulunan ve https://plan.dogru.app adresinde online yayında olan projenin yıllık plan arşivini oluşturur. 

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
- Architecture: Modular component system with separation of concerns

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
- **`modules/oku_dbf.py`** - ⭐ **DBF Koordinatörü**: Sadece koordinasyon ve veritabanı entegrasyonu yapar
- **`modules/utils_dbf1.py`** - ⭐ **YENİ MODÜLERİ**: Sayfa 1 işlemleri (temel bilgiler, kazanım tablosu, dosya okuma - fitz kullanılan tek yer)
- **`modules/utils_dbf2.py`** - ⭐ **YENİ MODÜLERİ**: Sayfa 2+ işlemleri (öğrenme birimleri, konu analizi - fitz kullanmaz, text pass edilir)
- **`modules/get_dbf.py`** - `get_dbf()` fonksiyonu ile DBF verilerini çeker, RAR/ZIP indirir (açmaz), `data/get_dbf.json` üretir ve `dbf_urls` sütununa JSON kaydeder
- **`test_unzip.py`** - ⭐ **GEÇİCİ AYIRIM**: DBF RAR/ZIP dosyalarını açan standalone script, `modules.utils_file_management.extract_archive` kullanır
- **`modules/get_cop.py`** - `get_cop()` fonksiyonu ile ÇÖP verilerini çeker, PDF indirir (açmaz), `data/get_cop.json` üretir ve `cop_url` sütununa JSON kaydeder
- **`modules/oku_cop.py`** - COP PDF parsing ve analiz modülü - Tamamen yeniden yazıldı
- **`modules/get_dm.py`** - Ders Materyalleri (DM) verilerini çeker - Sonra geliştirilecek
- **`modules/get_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker - Sonra geliştirilecek
- **`modules/get_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils_normalize.py`** - : String normalizasyon fonksiyonları, Türkçe karakter normalizasyonu
- **`modules/utils_database.py`** - Veritabanı işlemleri modülü, **database connection decorators**, **MEB ID yönetimi** ve **CRUD operasyonları**
- **`modules/utils_file_management.py`** - Dosya işlemleri modülü, **ortak alan dosya sistemi**, **duplicate dosya yönetimi** ve **arşiv işlemleri**
- **`modules/utils_stats.py`** -  İstatistik ve monitoring fonksiyonları
- **`modules/utils_env.py`** - Environment variable yönetimi, PROJECT_ROOT desteği, çoklu bilgisayar uyumluluğu
- **`modules/utils_docx_to_pdf.py`** - ⭐ **YENİ 2025-07-28**: DOC/DOCX to PDF conversion modülü, same directory caching, PyMuPDF unified processing

### 🌐 Frontend Dosyaları ⭐ **UI/UX İYİLEŞTİRMELERİ TAMAMLANDI**
- **`src/App.js`** - Ana layout ve API bağlantıları, workflow yönetimi
- **`src/App.css`** - Ana layout ve workflow stilleri
- **`src/components/DataTable.js`** - ⭐ **YENİ**: Tablo yönetimi bileşeni (filtreleme, sıralama, arama) + DBF button file type detection (PDF/DOCX/DBF)
- **`src/components/DataTable.css`** - Tablo ile ilgili tüm stiller
- **`src/components/CourseEditor.js`** - ⭐ **KAPSAMLI YENİLEME**: Sidebar ve document viewer bileşeni 
  - **Split-screen PDF viewer** (PDF sol, editor sağ)
  - **Flexible sidebar width** (course name length bazlı, max 50% viewport)
  - **Unified dropdown system** (COP ve DBF dropdowns)
  - **PDF/DOCX document viewer** (PDF native viewer + DOCX→PDF conversion with cache)
  - **Header layout redesign** (course name + DBF toggle button)
- **`src/components/CourseEditor.css`** - ⭐ **KAPSAMLI YENİLEME**: Sidebar ve document viewer stilleri
  - **MaterialUI-style dropdowns** (unified CSS classes)
  - **Flexible sidebar styling** (dynamic width calculations)
  - **Split-screen layout** (resize handle, responsive design)
  - **Document viewer styling** (loading states, error handling)
- **`package.json`** - Node.js bağımlılıkları ve scriptler
- **`src/index.js`** - React uygulaması entry point
- **`src/setupProxy.js`** - CORS proxy ayarları
- **`src/reportWebVitals.js`** - Performance monitoring

### 🗂️ Veri ve Veritabanı
- **`data/temel_plan.db`** - SQLite veritabanı dosyası ⭐ **UPDATED**: PROJECT_ROOT env variable bazlı path
- **`data/schema.sql`** - Veritabanı schema dosyası ⭐ **UPDATED**: PROJECT_ROOT env variable bazlı path
- **`data/get_cop.json`** - COP verilerinin JSON çıktısı (env aware path)
- **`data/get_dbf.json`** - DBF verilerinin JSON çıktısı (env aware path)
- **`data/get_dm.json`** - DM verilerinin JSON çıktısı (env aware path)
- **`.env`** - Environment variables (PROJECT_ROOT tanımı)
- **`data/`** - JSON cache dosyaları, veritabanı ve schema dosyaları ⭐ **UPDATED**: Tüm path'ler PROJECT_ROOT bazlı
  - `dbf/` - İndirilen DBF dosyaları (alan klasörleri halinde)
  - `cop/` - ÇÖP PDF dosyaları
  - `dm/` - Ders Materyali dosyaları `00_Ortak_Alan_Dersleri` klasörü ile duplicate dosya yönetimi
  - `bom/` - BÖM dosyaları

### 🐛 Debug ve Test Araçları
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
  - `ex_ob_tablosu()` - Öğrenme birimi analizi
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

### 10. Database Schema Tutarlılığı ⭐ **YENİ 2025-07-28**
- **ASLA** `server.py`'de duplicate database fonksiyonları yazma
- **MUTLAKA** `utils_database.py`'deki merkezi fonksiyonları kullan:
  ```python
  # ✅ Doğru - Merkezi database fonksiyonları
  from modules.utils_database import find_or_create_database, get_or_create_alan, create_or_get_ders
  
  # ❌ Yanlış - server.py'de duplicate fonksiyonlar
  def find_or_create_database():  # Bu fonksiyon zaten utils_database.py'de var!
      pass
  ```
- **Schema ile Uyumlu Tablo Adları**: Sadece `data/schema.sql`'deki tablo adlarını kullan:
  - ✅ `temel_plan_ogrenme_birimi` (schema'da var)
  - ❌ `temel_plan_ders_ogrenme_birimi` (schema'da yok)
  - ✅ `temel_plan_konu` (schema'da var)  
  - ❌ `temel_plan_ders_ob_konu` (schema'da yok)
  - ✅ `temel_plan_kazanim` (schema'da var)
  - ❌ `temel_plan_ders_ob_konu_kazanim` (schema'da yok)
- **Schema ile Uyumlu Sütun Adları**: Sadece `data/schema.sql`'deki sütun adlarını kullan:
  - ✅ `arac_adi` (schema'da var)
  - ❌ `arac_gerec` (schema'da yok)
  - ✅ `olcme_adi` (schema'da var)
  - ❌ `olcme_degerlendirme` (schema'da yok)
  - ✅ `birim_adi` (schema'da var)
  - ❌ `ogrenme_birimi` (schema'da yok)
  - ✅ `sure` (schema'da var)
  - ❌ `ders_saati` (öğrenme birimi tablosunda yok)
- **Database İşlemlerinde Consistency**: Her yeni database işlemi öncesi schema.sql ile uyumluluğu kontrol et

### 11. Schema Uyumsuzluk Hataları ⭐ **YENİ 2025-07-30**
- **ASLA** schema'da olmayan sütunları SQL sorgularında kullanma
- **MUTLAKA** schema.sql'deki exact sütun adlarını kullan:
  ```python
  # ❌ YANLIŞ - Schema'da olmayan sütunlar
  cursor.execute("SELECT id, birim_adi, sure, aciklama FROM temel_plan_ogrenme_birimi")  # aciklama yok!
  cursor.execute("SELECT id, konu_adi, detay FROM temel_plan_konu")  # detay yok!
  
  # ✅ DOĞRU - Schema uyumlu sütunlar
  cursor.execute("SELECT id, birim_adi, sure, sira FROM temel_plan_ogrenme_birimi")
  cursor.execute("SELECT id, konu_adi, sira FROM temel_plan_konu")
  ```
- **Schema Validation**: Her SQL sorgusu yazımından önce `data/schema.sql` kontrol et
- **Error Prevention**: "no such column" hatalarını önlemek için schema first yaklaşımı

## 🔄 Son Güncelleme Detayları - 2025-07-30

### ✅ Schema Uyumsuzluk Düzeltmeleri Tamamlandı:

1. **Öğrenme Birimi Yükleme Sorunu Çözüldü**:
   - **Problem**: CourseEditor sidebar açıldığında "❌ Learning units loading failed: no such column: aciklama" hatası
   - **Kök Neden**: `server.py`'de `/api/load` endpoint'i schema'da olmayan `aciklama` ve `detay` sütunlarını çekmeye çalışıyordu
   - **Çözüm**: Tüm SQL sorgularında schema uyumlu sütun adları kullanıldı (sadece `id`, `birim_adi`, `sure`, `sira`)
   - **Sonuç**: Öğrenme birimi verileri artık başarılı şekilde yüklenir ✅

2. **Schema Validation Sistemi**:
   - **Kaldırılan Alanlar**: `aciklama` (öğrenme birimi), `detay` (konu tablosu) - Schema'da mevcut değil
   - **Korunan Alanlar**: `birim_adi`, `sure`, `sira` (öğrenme birimi), `konu_adi`, `sira` (konu tablosu)
   - **SQL Sorgu Düzeltmeleri**: Tüm API endpoint'lerinde schema uyumlu SELECT statement'ları
   - **Hiyerarşik Veri**: Öğrenme birimi → Konu → Kazanım ilişkisi korundu ✅

3. **Debug Log Temizliği**:
   - **Azaltılan Loglar**: COP/DBF dropdown tekrarlanan debug mesajları temizlendi
   - **DocumentViewer**: Verbose PDF loading logları azaltıldı
   - **Sidebar**: Flexible width calculation logları temizlendi
   - **Korunan Loglar**: Kritik error mesajları ve başarı bildirileri korundu
   - **Sonuç**: Konsol çıktısı %70 daha temiz ve anlamlı ✅

4. **CourseEditor.js Stabilizasyonu**:
   - **Fresh Data Loading**: `/api/load?type=ders&id=X` ile güncel ders bilgileri
   - **Learning Units Loading**: `/api/load?type=ogrenme_birimi&parent_id=X` ile öğrenme birimleri
   - **Error Handling**: Schema uyumsuzluk hatalarına karşı koruma
   - **Fallback Mechanism**: API hatası durumunda prop data kullanımı ✅

### 🔧 Teknik Değişiklikler:

1. **server.py SQL Düzeltmeleri**:
   ```python
   # ❌ ESKİ - Schema uyumsuz
   cursor.execute("SELECT id, birim_adi, sure, aciklama, sira FROM temel_plan_ogrenme_birimi")
   cursor.execute("SELECT id, konu_adi, detay, sira FROM temel_plan_konu")
   
   # ✅ YENİ - Schema uyumlu  
   cursor.execute("SELECT id, birim_adi, sure, sira FROM temel_plan_ogrenme_birimi")
   cursor.execute("SELECT id, konu_adi, sira FROM temel_plan_konu")
   ```

2. **CourseEditor.js Log Optimizasyonu**:
   ```javascript
   // ❌ ESKİ - Verbose logging
   console.log('🔍 CopDropdown render - copUrls:', copUrls);
   console.log('📏 Flexible sidebar for course...', courseName);
   
   // ✅ YENİ - Reduced logging
   // COP Dropdown debug (reduced logging)
   // Flexible sidebar width calculated
   ```

## 🔄 Önceki Güncelleme Detayları - 2025-07-28

### ✅ Frontend UI/UX İyileştirmeleri Tamamlandı:

1. **PDF Viewer Loading Sorunu Çözüldü**:
   - **Problem**: PDF viewer "Belge yükleniyor..." durumunda takılı kalıyordu, PDF dosyaları açılmıyordu
   - **Çözüm**: `DocumentViewer` component'inde loading state yönetimi düzeltildi, PDF için loading disabled
   - **Sonuç**: PDF dosyaları anında yüklenir ve görüntülenir ✅

2. **Split-Screen Layout Sistemi**:
   - **Layout Değişikliği**: PDF viewer sol panel, course editor sağ panel konumlandırması
   - **Resize Handle**: Manuel olarak panel genişliklerini ayarlama özelliği
   - **Responsive Design**: Mobil cihazlarda dikey layout'a geçiş ✅

3. **Flexible Sidebar Width Sistemi**:
   - **Dynamic Width**: Course name uzunluğuna göre sidebar genişliği otomatik ayarlanır
   - **Viewport Constraint**: Maximum %50 viewport genişliği sınırı
   - **CSS Calculation**: `width: min(${baseWidth}px, 50vw)` formülü ile hesaplama ✅

4. **Unified Dropdown System**:
   - **COP Dropdown**: ÇÖP PDF'lerini seçme sistemi (JSON URL parsing ile)
   - **DBF Dropdown**: Alan-level DBF RAR dosyalarını açma sistemi
   - **MaterialUI Style**: Unified CSS classes (.dropdown-container, .dropdown-toggle, .dropdown-menu, .dropdown-item)
   - **Height Matching**: 56px MaterialTextField height standardı ✅

5. **Header Layout Redesign**:
   - **Course Name Display**: Flexible width ile course name tam görünür
   - **DBF Toggle Button**: "DBF:PDF" veya "DBF:DOCX" formatında dosya tipi gösterimi
   - **Toggle Functionality**: PDF açık/kapalı duruma göre buton davranışı ✅

6. **Document Viewer Geliştirmeleri**:
   - **PDF Support**: Native iframe ile PDF görüntüleme
   - **DOCX Support**: ⭐ **YENİ**: PyMuPDF ile DOCX→PDF conversion + same directory caching
   - **DOC Support**: ⭐ **YENİ**: .doc dosyaları da desteklenir (unified processing)
   - **Cache System**: ⭐ **YENİ**: Converted PDF'ler aynı dizinde `_converted.pdf` suffix ile saklanır
   - **File Type Detection**: URL extension bazlı (.pdf, .docx, .doc) dosya tipi tespiti
   - **Error Handling**: Loading timeouts, error states, fallback mechanisms ✅

7. **DataTable File Type Integration**:
   - **Dynamic Button Text**: DBF sütununda "📄 PDF", "📄 DOCX", "📄 DBF" dynamic text
   - **File Extension Detection**: `row.dbf_url.toLowerCase().endsWith()` ile tespit
   - **Consistent UI**: Tüm file type butonları aynı styling ✅

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

### 💾 Unified Data Management ⭐ **YENİ 2025-07-28**
- **`GET /api/load`** - ⭐ **UNİFİED LOAD ENDPOINT**: Alan, dal, ders, konu, kazanım verilerini çeker
  - **Query Parameters**: `type` (alan|dal|ders|konu|kazanim), `id` (entity ID), `parent_id` (parent entity ID)
  - **Examples**: 
    - `/api/load?type=ders&id=123` → Tek ders fresh data (sidebar için)
    - `/api/load?type=alan` → Tüm alanlar
    - `/api/load?type=dal&parent_id=5` → Belirli alanın dalları
    - `/api/load?type=konu&parent_id=10` → Belirli öğrenme biriminin konuları
- **`POST /api/save`** - ⭐ **UNİFİED SAVE ENDPOINT**: Tek ders güncelleme (update mode) veya çoklu ders kaydetme (batch mode) destekler

### 🔄 Document Conversion Operations ⭐ **YENİ 2025-07-28**
- **`POST /api/convert-docx-to-pdf`** - DOC/DOCX dosyalarını PDF'e çevirir (cache-aware, same directory storage)

### 🔄 PDF ve DBF İşleme Operasyonları
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
from modules.utils_dbf1 import get_all_dbf_files, process_dbf_file

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

### /api/save Endpoint Kullanımı ⭐ **YENİ 2025-07-28**
```javascript
// Tek course güncelleme (Update Mode)
const response = await fetch('http://localhost:5001/api/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    ders_id: 123,
    ders_adi: "Güncellenmiş Ders Adı",
    sinif: 9,
    ders_saati: 4,
    amac: "Ders amacı metni",
    dm_url: "https://example.com/dm.pdf",
    dbf_url: "data/dbf/alan/ders.pdf",
    bom_url: "https://example.com/bom.pdf"
  })
});

// Çoklu course kaydetme (Batch Mode)
const response = await fetch('http://localhost:5001/api/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    courses: [
      { ders_adi: "Ders 1", sinif: 9, ders_saati: 2 },
      { ders_adi: "Ders 2", sinif: 10, ders_saati: 3 }
    ]
  })
});
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
- **⭐ YENİ 2025-07-28**: Frontend UI/UX İyileştirmeleri - PDF viewer loading fix, split-screen layout, flexible sidebar, unified dropdowns, header redesign
- **⭐ YENİ 2025-07-28**: `/api/save` Unified Endpoint - Tek ders güncelleme ve çoklu ders kaydetme tek endpoint'te birleştirildi, `/api/update-table-row` kaldırıldı
- **⭐ YENİ 2025-07-28**: `/api/load` Unified Endpoint - Alan, dal, ders, konu, kazanım tüm veri tiplerini destekler, `/api/course/<id>` kaldırıldı
- **⭐ YENİ 2025-07-28**: Fresh Data Loading - CourseEditor sidebar açıldığında DB'den en güncel veri çeker (cached table data değil)
- **⭐ YENİ 2025-07-28**: Save Feedback System - Kaydet butonunda success/error feedback, disabled state ve visual indicators
- **⭐ YENİ 2025-07-30**: Schema Uyumsuzluk Düzeltmeleri - "no such column" hatalarının çözümü ve öğrenme birimi yükleme sorunu düzeltildi
- **⭐ YENİ 2025-07-30**: Debug Log Temizliği - CourseEditor.js konsol çıktısı %70 azaltıldı, sadece kritik mesajlar korundu

### 🌐 Unified API System ⭐ **YENİ 2025-07-28**

#### **1. /api/load Endpoint Usage**
- **ASLA** eski endpoint'leri kullanma: `/api/course/<id>` (kaldırıldı)
- **MUTLAKA** yeni unified endpoint kullan:
  ```javascript
  // ✅ Doğru - Fresh ders data loading
  const response = await fetch(`/api/load?type=ders&id=${course.ders_id}`);
  const result = await response.json();
  if (result.success) {
    setEditData(result.data); // Fresh data from DB
  }
  
  // ✅ Doğru - Tüm alanları yükle
  const response = await fetch('/api/load?type=alan');
  
  // ✅ Doğru - Belirli alanın dalları
  const response = await fetch(`/api/load?type=dal&parent_id=${alanId}`);
  
  // ❌ Yanlış - Eski endpoint
  const response = await fetch(`/api/course/${courseId}`); // Artık yok!
  ```

#### **2. Save Feedback Implementation**
- **ASLA** onSave'den sonra hemen sidebar kapat
- **MUTLAKA** save feedback göster:
  ```javascript
  // ✅ Doğru - Save feedback ile async handling
  const handleSave = async () => {
    setSaveStatus('saving');
    setSaveMessage('Kaydediliyor...');
    
    try {
      await onSave(editData); // Wait for completion
      setSaveStatus('success');
      setSaveMessage('✅ Başarıyla kaydedildi!');
      setTimeout(() => onClose(), 1500); // Delay close
    } catch (error) {
      setSaveStatus('error');
      setSaveMessage(`❌ Hata: ${error.message}`);
    }
  };
  
  // ❌ Yanlış - Hemen kapat, feedback yok
  const handleSave = () => {
    onSave(editData);
    onClose(); // Kullanıcı kaydetme durumunu göremez
  };
  ```

#### **3. Fresh Data Loading Pattern**
- **ASLA** sadece prop'tan gelen course data kullan
- **MUTLAKA** DB'den fresh data çek:
  ```javascript
  // ✅ Doğru - Fresh data priority
  useEffect(() => {
    if (course && course.ders_id && isOpen) {
      fetch(`/api/load?type=ders&id=${course.ders_id}`)
        .then(res => res.json())
        .then(result => {
          if (result.success) {
            setEditData(result.data); // Fresh DB data
          } else {
            setEditData(course); // Fallback to prop data
          }
        });
    }
  }, [course, isOpen]);
  
  // ❌ Yanlış - Sadece prop data
  useEffect(() => {
    if (course && isOpen) {
      setEditData(course); // Cached table data, fresh değil
    }
  }, [course, isOpen]);
  ```

### 📱 Frontend UI/UX Kuralları ⭐ **YENİ 2025-07-28**

#### **1. PDF Viewer Loading Management**
- **ASLA** `setPdfLoading(true)` kullanıp false yapmayı unutma
- **MUTLAKA** PDF dosyaları için loading state'i disable et:
  ```javascript
  // ✅ Doğru - PDF için loading disabled
  useEffect(() => {
    if (pdfUrl && fileType === 'pdf') {
      setPdfLoading(false); // PDF için loading disable
    }
  }, [pdfUrl]);
  
  // ❌ Yanlış - Loading state takılı kalır
  useEffect(() => {
    setPdfLoading(true); // Asla false yapılmıyor!
  }, [pdfUrl]);
  ```

#### **2. COP URL JSON Parsing**
- **ASLA** COP URLs'lerinin string olduğunu varsayma
- **MUTLAKA** object/string type checking yap:
  ```javascript
  // ✅ Doğru - Type-safe URL parsing
  const actualUrl = typeof urlData === 'object' && urlData.url ? urlData.url : urlData;
  
  // ❌ Yanlış - "fileUrl.split is not a function" hatası
  const parts = fileUrl.split('/'); // fileUrl object olabilir!
  ```

#### **3. Flexible Sidebar Width**
- **ASLA** fixed width kullanma
- **MUTLAKA** course name length bazlı dynamic width:
  ```javascript
  // ✅ Doğru - Dynamic width calculation
  const baseWidth = Math.max(400, Math.min(charCount * 8 + 200, 800));
  return { width: `min(${baseWidth}px, 50vw)` };
  
  // ❌ Yanlış - Fixed width
  return { width: '400px' }; // Course name kesik görünür
  ```

#### **4. Unified Dropdown CSS Classes**
- **ASLA** farklı dropdown'lar için farklı CSS classes kullanma
- **MUTLAKA** unified classes kullan:
  ```css
  /* ✅ Doğru - Unified classes */
  .dropdown-container { /* shared styles */ }
  .dropdown-toggle { height: 56px; /* MaterialTextField match */ }
  .dropdown-menu { /* shared styles */ }
  .dropdown-item { /* shared styles */ }
  
  /* ❌ Yanlış - Farklı classes */
  .cop-dropdown-container { /* COP specific */ }
  .dbf-dropdown-container { /* DBF specific */ }
  ```

#### **5. File Type Detection**
- **ASLA** hardcoded file extensions kontrolü yapma
- **MUTLAKA** lowercase + endsWith pattern kullan:
  ```javascript
  // ✅ Doğru - Safe file type detection
  const fileType = url.toLowerCase().endsWith('.pdf') ? 'PDF' : 
                   url.toLowerCase().endsWith('.docx') ? 'DOCX' : 'DBF';
  
  // ❌ Yanlış - Case sensitive veya indexOf
  const fileType = url.includes('.PDF') ? 'PDF' : 'DBF'; // .pdf miss eder
  ```

#### **6. DOCX Viewer Localhost Limitation**
- **ASLA** DOCX dosyaları için Google Docs Viewer ile localhost URL kullanma
- **MUTLAKA** download interface provide et:
  ```javascript
  // ✅ Doğru - DOCX için download interface
  return (
    <div style={{ textAlign: 'center' }}>
      <a href={url} download>📥 Dosyayı İndir</a>
      <button onClick={() => window.open(url, '_blank')}>🔗 Yeni Sekmede Aç</button>
    </div>
  );
  
  // ❌ Yanlış - Google Docs Viewer localhost'ta çalışmaz
  <iframe src={`https://docs.google.com/viewer?url=${url}`} />
  ```

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır.