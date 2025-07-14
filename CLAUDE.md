# 🤖 CLAUDE.md - MEB Mesleki Eğitim Veri İşleme Projesi Kılavuzu

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı teknik kılavuzudur. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

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

### 🔧 Core Modüller (modules/ klasörü)
- **`modules/oku.py`** - PDF parsing ve içerik analizi (ÇÖP, DBF, DM dosyaları için)
- **`modules/getir_dbf.py`** - Ders Bilgi Formları (DBF) verilerini çeker, RAR/ZIP dosyalarını indirir ve açar
- **`modules/getir_cop.py`** - ⭐ **YENİ**: ÇÖP HTML scraping ve PDF indirme modülü
- **`modules/oku_cop.py`** - ⭐ **YENİ**: ÇÖP PDF okuma ve analiz modülü (geliştirilmiş algoritmalar)
- **`test_oku_cop.py`** - ⭐ **YENİ**: oku_cop.py modülü test aracı
- **`modules/getir_cop_oku_local.py`** - ⭐ **YENİ**: Yerel PDF dosyalarını test etmek için standalone ÇÖP okuma modülü
- **`modules/getir_dm.py`** - Ders Materyalleri (DM) verilerini çeker
- **`modules/getir_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker
- **`modules/getir_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils.py`** - Yardımcı fonksiyonlar, Türkçe karakter normalizasyonu ve **merkezi PDF cache yönetimi** ⭐ **GÜNCELLENDİ**

### 🌐 Ana Dosyalar
- **`server.py`** - Ana Flask sunucusu, tüm API endpoint'leri ve veritabanı işlemleri
- **`src/App.js`** - Ana React komponenti, aşamalı iş akışı UI
- **`data/temel_plan.db`** - SQLite veritabanı dosyası
- **`data/schema.sql`** - Veritabanı schema dosyası

### 🐛 Debug ve Test Araçları
- **`debug_gida_table.py`** - PDF tablo yapısını detaylı analiz eden debug script
- **`debug_meslek_dersleri.py`** - MESLEK DERSLERİ kategori algılama test aracı
- **`debug_cop_system.py`** - ⭐ **YENİ**: COP sistemi kapsamlı debug aracı, PDF indirme/okuma/veritabanı testleri
- **`*.pdf`** (kök dizin) - Test için kullanılan sample PDF dosyaları

## 🗄️ Veritabanı Yapısı (SQLite)

### Ana Tablolar
```sql
-- 1. ALANLAR (Ana Eğitim Alanları)
temel_plan_alan
├── id (INTEGER PRIMARY KEY)
├── alan_adi (TEXT NOT NULL)
├── meb_alan_id (TEXT)
├── cop_url (TEXT) - ÇÖP URL'leri (JSON format)
├── dbf_urls (TEXT) - DBF URL'leri (JSON format)
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
├── amac (TEXT)
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
-- temel_plan_kazanim, temel_plan_arac, temel_plan_olcme, vb.
```

## 🔄 Aşamalı İş Akışı

### 🚀 Adım 1: Temel Veri Çekme
- **Verileri Çek:** MEB sitesinden ana veri çekme
- **DBF Getir:** Ders Bilgi Formu linklerini çek (`modules/getir_dbf.py`)
- **ÇÖP Getir:** Çerçeve Öğretim Programı linklerini çek (`modules/getir_cop.py`) ⭐ **YENİ MODÜL**
- **DM Getir:** Ders Materyali linklerini çek (`modules/getir_dm.py`)
- **BÖM Getir:** Bireysel Öğrenme Materyali linklerini çek (`modules/getir_bom.py`)
- **Dal Getir:** Alan-Dal ilişkilerini çek (`modules/getir_dal.py`)

### 📄 Adım 2: PDF İşleme ve Analiz
- **DBF İndir ve Aç:** RAR/ZIP dosyalarını otomatik işle
- **ÇÖP PDF'lerini İndir:** `modules/getir_cop.py` ile PDF indirme ⭐ **YENİ**
- **ÇÖP PDF'lerini İşle:** `modules/oku_cop.py` ile PDF içeriklerini analiz et ⭐ **YENİ**
- **Tüm PDF'leri Tekrar İşle:** Başarısız işlemleri yeniden dene

### 💾 Adım 3: Veritabanı Güncellemeleri
- **DBF Eşleştir:** İndirilen dosyalarle dersleri eşleştir
- **Ders Saatlerini Güncelle:** DBF'lerden ders saati bilgilerini çıkar
- **Veritabanına Aktar:** Düzenlenmiş dersleri kaydet

## 📋 Modül Detayları ve Kritik Bilgiler

### 1. 📄 getir_cop.py ⭐ **YENİ MODÜL**

**Kaynak URL:** `https://meslek.meb.gov.tr/cercevelistele.aspx`

**Ana Fonksiyonlar:**
- `getir_cop_links(siniflar)` - MEB sitesinden ÇÖP linklerini çeker (paralel işlem)
- `download_cop_pdfs(alan_list, cache)` - PDF'leri toplu indirir (utils.py entegrasyonu)
- `get_cop_metadata(save_to_file)` - ÇÖP metadata'sını toplar ve kaydeder
- `validate_cop_links(cop_data)` - ÇÖP linklerinin geçerliliğini kontrol eder
- `get_cop_data_for_class(sinif_kodu)` - Belirli sınıf için ÇÖP verilerini çeker

**Kritik Mantık:**
- Her sınıf için (9-12) paralel HTTP istekleri
- BeautifulSoup ile HTML ayrıştırma
- PDF URL'leri ve güncelleme yılları çıkarma
- **Merkezi indirme**: `utils.download_and_cache_pdf()` fonksiyonu
- **Cache yönetimi**: Mevcut dosya kontrolü, gereksiz indirme önleme
- **Alan ID entegrasyonu**: Veritabanı ile ID eşleştirmesi

### 2. 📄 oku_cop.py ⭐ **YENİ MODÜL**

**Amaç:** PDF okuma ve analiz işlemleri - ÇÖP PDF dosyalarından alan, dal ve ders bilgilerini çıkarır.

**Ana Fonksiyonlar:**
- `extract_alan_dal_ders_from_pdf(pdf_source, debug)` - Tam PDF analizi (alan/dal/ders)
- `oku_cop_pdf(pdf_source, debug)` - JSON formatında sonuç döndürür  
- `oku_cop_pdf_file(pdf_path, debug)` - Yerel PDF dosyasını okur
- `oku_folder_pdfler(folder_path, debug)` - Klasördeki tüm PDF'leri okur
- `validate_pdf_content(pdf_source)` - PDF içeriğinin geçerliliğini kontrol eder
- `find_alan_name_in_text(text, pdf_url)` - PDF'den alan adını çıkarır (geliştirilmiş)
- `find_dallar_from_icindekiler(text, debug)` - İçindekiler'den dal listesi (basitleştirilmiş)
- `find_lessons_in_cop_pdf(pdf, alan_adi, debug)` - Dal-ders eşleştirmesi (dinamik sütun)

**Kritik Mantık:**
- **Geliştirilmiş algoritmalar**: İçindekiler analizi, dinamik sütun algılama
- **URL-based fallback**: PDF'den alan adı bulunamazsa URL'den tahmin
- **Basitleştirilmiş dal bulma**: "DALI" keyword'ü ile öncesindeki metin
- **Dinamik MESLEK DERSLERİ algılama**: Farklı tablo yapılarına uyum
- **Yerel + Remote desteği**: Hem URL hem dosya yolu kabul eder
- **Content-based matching**: Fuzzy matching yerine içerik bazlı eşleştirme

### 3. 📄 test_oku_cop.py ⭐ **YENİ TEST ARACI**

**Amaç:** oku_cop.py modülünün fonksiyonlarını test eder ve doğrular.

**Ana Fonksiyonlar:**
- `test_single_pdf(pdf_path, debug)` - Tek PDF dosyasını test eder
- `test_folder(folder_path, debug)` - Klasördeki tüm PDF'leri test eder
- `test_all_pdfs_in_current_dir(debug)` - Kök dizindeki PDF'leri test eder
- `validate_pdf_files(file_paths)` - PDF doğrulama testi
- `print_summary(all_results)` - Test sonuçlarının özeti

**Kullanım Örnekleri:**
```bash
python test_oku_cop.py                    # Kök dizindeki tüm PDF'leri test et
python test_oku_cop.py gida.pdf          # Belirli bir PDF'yi test et
python test_oku_cop.py data/cop/          # Klasördeki PDF'leri test et
python test_oku_cop.py --debug gida.pdf  # Debug modu ile test et
python test_oku_cop.py --validate *.pdf  # PDF'leri doğrula
python test_oku_cop.py --json            # JSON formatında sonuç
```

**Özellikler:**
- **Kapsamlı Test**: Alan/dal/ders çıkarma algoritmalarını doğrular
- **Validation**: PDF içerik geçerliliği kontrolü
- **İstatistikler**: Başarı oranı, çıkarılan veri sayıları
- **Debug Modu**: Detaylı algoritma analizi
- **JSON Export**: Programatik kullanım için JSON çıktı

### 4. 📄 getir_dbf.py

**Amaç:** Ders Bilgi Formu (DBF) verilerini çeker, indirip açar ve içeriklerini analiz eder.

**Kaynak URL:** `https://meslek.meb.gov.tr/dbflistele.aspx`

**Dosya Organizasyonu:**
```
data/dbf/
├── {ID:02d}_-_{Alan_Adi}/
│   ├── alan.rar (orijinal)
│   ├── alan/ (açılmış)
│   │   ├── 9.SINIF/
│   │   ├── 10.SINIF/
│   │   └── 11.SINIF/

Örnek:
├── 01_-_Adalet/
├── 03_-_Bilişim_Teknolojileri/
└── 04_-_Biyomedikal_Cihaz_Teknolojileri/
```

**Kritik Özellikler:**
- RAR/ZIP otomatik açma (`rarfile`, `zipfile`)
- **YENİ**: PDF içeriğinden gerçek ders adı çıkarma (fuzzy matching yerine)
- Progress tracking ile SSE desteği
- Retry mekanizması

**Ana Fonksiyonlar:**
- `getir_dbf(siniflar)` - DBF linklerini çeker
- `download_and_extract_dbf()` - İndirir ve açar
- `scan_dbf_files_and_extract_courses()` - İçerik analizi (YENİ)
- `extract_course_name_from_dbf()` - PDF'den ders adı (YENİ)

### 3. 📄 getir_dm.py

**Amaç:** Ders Materyali (DM) verilerini çeker.

**Kaynak URL:** 
- `https://meslek.meb.gov.tr/cercevelistele.aspx` (Alan listesi)
- `https://meslek.meb.gov.tr/dmgoster.aspx` (DM listesi)

**Veri Yapısı:**
```python
{
    "9": {
        "Bilişim Teknolojileri": [
            {"isim": "Ders Adı", "sinif": "9. Sınıf", "link": "PDF URL"}
        ]
    }
}
```

**Dosya Organizasyonu:** ⭐ **YENİ ID Sistemi**
```
data/dm/
├── {ID:02d}_-_{Alan_Adi}/
│   ├── sinif_9/
│   │   └── {ders_id:03d}_-_{Ders_Adi}.pdf
│   ├── sinif_10/
│   └── dm_metadata.json

Örnek:
├── 03_-_Bilişim_Teknolojileri/
│   ├── sinif_9/
│   │   ├── 001_-_Programlama_Temelleri.pdf
│   │   └── 002_-_Bilgisayar_Donanım.pdf
│   └── dm_metadata.json
```

**Kritik Mantık:**
- Sınıf → Alan → Ders hiyerarşisi
- Dinamik alan ID'lerini HTML'den çıkarma
- Fuzzy matching ile veritabanı eşleştirmesi

### 4. 📄 getir_bom.py

**Amaç:** Bireysel Öğrenme Materyali (BÖM) verilerini çeker.

**Kaynak URL:** `https://meslek.meb.gov.tr/moduller`

**Kritik Özellikler:**
- ASP.NET form işleme (ViewState yönetimi)
- 3 aşamalı form gönderimi (Ana sayfa → Alan seç → Ders seç)
- Paralel işleme (5 worker)
- Session yönetimi

**Veri Yapısı:**
```python
{
    "04": {  # Alan ID
        "dersler": [
            {
                "ders_adi": "Ders Adı",
                "moduller": [{"isim": "Modül", "link": "PDF URL"}]
            }
        ]
    }
}
```

**Dosya Organizasyonu:** ⭐ **YENİ ID Sistemi**
```
data/bom/
├── {ID:02d}_-_{Alan_Adi}/
│   ├── {ders_id:03d}_-_{Ders_Adi}/
│   │   ├── {modul_01}.pdf
│   │   ├── {modul_02}.pdf
│   │   └── modül_listesi.json
│   ├── bom_metadata.json
│   └── alan_bilgileri.json

Örnek:
├── 04_-_Biyomedikal_Cihaz_Teknolojileri/
│   ├── 015_-_Medikal_Cihaz_Bakım/
│   │   ├── Modül_01_Temel_Bilgiler.pdf
│   │   ├── Modül_02_Uygulama.pdf
│   │   └── modül_listesi.json
│   └── bom_metadata.json
```

### 5. 📄 getir_dal.py

**Amaç:** Alan-Dal ilişkilerini MEB'in AJAX sisteminden çeker.

**Kaynak URL:** `https://mtegm.meb.gov.tr/kurumlar/`

**Kritik Özellikler:**
- 81 il bazında tarama
- AJAX istekleri (JSON response)
- Session yönetimi
- Rate limiting (0.3s-1.5s arası)
- Benzersiz alan-dal kombinasyonları

**API Endpoint'leri:**
- `/api/getIller.php` - İl listesi
- `/api/getAlanlar.php` - Alan listesi
- `/api/getDallar.php` - Dal listesi

### 6. 📄 oku.py

**Amaç:** PDF parsing ve içerik analizi.

**Desteklenen Formatlar:**
- PDF (`pdfplumber`)
- DOCX (`python-docx`)

**Ana Fonksiyonlar:**
- `extract_ders_adi()` - Dosyadan ders adını çıkarır
- `extract_text_from_pdf()` - PDF metin çıkarma
- `extract_text_from_docx()` - DOCX metin çıkarma

### 7. 📄 getir_cop_oku_local.py ⭐ **YENİ**

**Amaç:** Yerel PDF dosyalarını test etmek için standalone ÇÖP okuma modülü.

**Özellikler:**
- Kök dizindeki PDF dosyalarını otomatik tarar
- `modules/oku_cop.py`'deki fonksiyonları kullanır (kod tekrarı yok)
- Stand-alone çalışma desteği (import hatası durumunda sys.path yönetimi)
- Terminal çıktısında detaylı analiz sonuçları

**Ana Fonksiyonlar:**
- `extract_alan_dal_ders_from_cop_file(pdf_path)` - Yerel PDF'den veri çıkarma
- `oku_cop_pdf_file(pdf_path)` - Tek PDF dosyasını okuma
- `oku_tum_pdfler(root_dir)` - Dizindeki tüm PDF'leri toplu okuma

**Kullanım:**
```bash
# Script olarak çalıştırma
python modules/getir_cop_oku_local.py

# Modül olarak kullanma
from modules.getir_cop_oku_local import oku_cop_pdf_file
result = oku_cop_pdf_file("test.pdf")
```

### 8. 📄 utils.py - Merkezi Cache Yönetimi ⭐ **GÜNCELLENDİ**

**Amaç:** Merkezi PDF indirme ve cache yönetimi sistemi.

**Yeni/Güncellenmiş Fonksiyonlar:**
- `download_and_cache_pdf(url, cache_type, alan_adi, additional_info, alan_id)` - Organize PDF cache sistemi
- `get_temp_pdf_path(url)` - Geçici dosya yolu oluşturma
- `get_cop_cache_path(alan_adi, sinif, year, alan_id)` - ⭐ **YENİ**: ÇÖP için özel cache yolu
- `validate_pdf_file(file_path)` - ⭐ **YENİ**: PDF dosya doğrulama
- `cleanup_temp_files(temp_dir)` - ⭐ **YENİ**: Geçici dosya temizleme
- `create_cache_structure(base_path)` - ⭐ **YENİ**: Cache klasör yapısı oluşturma
- `normalize_to_title_case_tr(name)` - Türkçe karakter normalizasyonu (mevcut)

**Cache Yapısı:** ⭐ **YENİ ID Bazlı Organizasyon**
```
data/
├── cop/     # Çerçeve Öğretim Programları
│   └── {ID:02d}_-_{alan_adi}/
│       └── cop_{sinif}_sinif_{yil}.pdf
├── dbf/     # Ders Bilgi Formları  
│   └── {ID:02d}_-_{alan_adi}/
│       └── {alan}_dbf_package.rar
├── dm/      # Ders Materyalleri
│   └── {ID:02d}_-_{alan_adi}/
│       └── sinif_{sinif}/
│           └── {ders_id:03d}_-_{ders_adi}.pdf
└── bom/     # Bireysel Öğrenme Materyalleri
    └── {ID:02d}_-_{alan_adi}/
        └── {ders_id:03d}_-_{ders_adi}/
            └── {modul}.pdf

Örnek:
├── 03_-_Bilişim_Teknolojileri/
│   ├── cop_9_sinif_2023.pdf
│   ├── sinif_9/
│   │   ├── 001_-_Programlama_Temelleri.pdf
│   │   └── 002_-_Bilgisayar_Donanım.pdf
│   └── 001_-_Programlama_Temelleri/
│       ├── Modül_01_Temel_Kavramlar.pdf
│       └── Modül_02_Uygulama.pdf
```

**Avantajları:**
- Kod tekrarı önleme
- Organize dosya yapısı
- Otomatik cache kontrolü
- Güvenli dosya adlandırma

## 🔌 API Endpoints

### Veri Çekme
- `GET /api/get-cached-data` - Önbellekteki verileri getir
- `GET /api/scrape-to-db` - MEB'den veri çek ve DB'ye kaydet (SSE)
- `POST /api/process-pdf` - PDF dosyasını işle (SSE)

### Kategorik Veri
- `GET /api/get-dbf` - DBF verilerini getir
- `GET /api/get-cop` - ÇÖP verilerini getir  
- `GET /api/get-dm` - DM verilerini getir
- `GET /api/get-bom` - BÖM verilerini getir

### PDF ve DBF İşlemleri
- `GET /api/dbf-download-extract` - DBF dosyalarını indir/aç (SSE)
- `GET /api/dbf-retry-extract-all` - Tüm DBF'leri tekrar aç (SSE)
- `POST /api/process-cop-pdfs` - ÇÖP PDF'lerini işle (SSE)
- `POST /api/update-ders-saatleri-from-dbf` - DBF'lerden ders saatlerini güncelle (SSE)

### Veritabanı
- `POST /api/dbf-match-refresh` - DBF eşleştirmesini güncelle
- `POST /api/export-to-database` - Düzenlenmiş dersleri DB'ye aktar

## 🚨 Kritik Hatalardan Kaçınma Kuralları

### 1. Modül İsimleri ⭐ **GÜNCELLENDİ**
- ✅ **YENİ MODÜLLER kullan**: `getir_cop.py` ve `oku_cop.py`
- ⚠️ **DEPRECATED**: `getir_cop.py + oku_cop.py` sadece geriye uyumluluk için
- Import'larda yeni modül adlarını kullan:
  ```python
  # YENİ (önerilen)
  from modules.getir_cop import getir_cop_links, download_cop_pdfs
  from modules.oku_cop import oku_cop_pdf, extract_alan_dal_ders_from_pdf
  
  # ESKİ (deprecated - dosya silindi)
  # from modules.getir_cop_oku import getir_cop, oku_cop_pdf_legacy
  ```

### 2. Veritabanı İşlemleri
- **ASLA** veritabanı dosyasını silme
- Migration'ları `schema.sql`'den uygula
- `IF NOT EXISTS` kullan
- Transaction'ları `with sqlite3.connect()` ile yönet

### 3. PDF İşleme
- Content-based matching kullan (fuzzy matching yerine)
- `modules/oku.py`'yi PDF okuma için kullan
- Encoding: `UTF-8` ile dosya okuma/yazma

### 4. Error Handling
- Her API çağrısında try-catch kullan
- SSE mesajlarında error type belirt
- Timeout değerlerini koru (10-20 saniye)

### 5. Dosya Yolları
- **ASLA** hard-coded path kullanma
- `os.path.join()` ile platform-agnostic yollar
- `data/` klasörü yapısını koru

## 🔧 Geliştirme Ortamı

### Python Bağımlılıkları
```python
# Core
flask
sqlite3 (built-in)
requests
beautifulsoup4

# PDF İşleme
pdfplumber
python-docx

# Archive İşleme
rarfile
zipfile (built-in)

# Utilities
fuzzywuzzy  # (optional, legacy)
```

### Frontend
```javascript
// React
react
react-dom

// Styling
CSS3 (responsive)

// Real-time
Server-Sent Events (SSE)
```

## 📈 Performans ve İstatistikler

### Veri Hacmi
- **58 Meslek Alanı**
- **~180 Dal**
- **~800 Ders**
- **~2000 DBF dosyası**
- **~1200 BÖM modülü**

### Performans Metrikleri
- **DBF İndirme**: ~50 MB/dakika
- **ÇÖP İşleme**: ~4 saniye (paralel)
- **DM Çekme**: ~30 saniye
- **BÖM Çekme**: ~45 saniye (ASP.NET karmaşıklığı)
- **Dal Çekme**: ~5 dakika (81 il taraması)

## 🔄 Sık Kullanılan İşlemler

### Veri Çekme ⭐ **GÜNCELLENDİ**
```python
# YENİ MODÜL YAPISI
from modules.getir_dbf import getir_dbf
from modules.getir_cop import getir_cop_links, download_cop_pdfs  # YENİ
from modules.oku_cop import oku_cop_pdf  # YENİ
from modules.getir_dm import getir_dm
from modules.getir_bom import getir_bom
from modules.getir_dal import main as getir_dal

# Veri çekme
dbf_data = getir_dbf()
cop_data = getir_cop_links()  # ESKİ: getir_cop()
dm_data = getir_dm()
bom_data = getir_bom()

# ÇÖP PDF'leri indir ve analiz et
pdf_files = download_cop_pdfs(alan_list, cache=True)
for pdf_file in pdf_files.values():
    result = oku_cop_pdf(pdf_file)
```

### PDF İşleme
```python
from modules.oku import extract_ders_adi

ders_adi = extract_ders_adi("/path/to/dbf/file.pdf")
```

### Yerel PDF Test ⭐ **GÜNCELLENDİ**
```python
# YENİ MODÜL ile yerel PDF test
from modules.oku_cop import oku_cop_pdf_file, oku_folder_pdfler

# Tek dosya analizi
result = oku_cop_pdf_file("gida.pdf", debug=True)
print(result)

# Klasör bazlı toplu analiz
results = oku_folder_pdfler("data/cop/gida_12/", debug=True)

# Legacy modül ile test (alternatif)
from modules.getir_cop_oku_local import oku_cop_pdf_file as legacy_oku
legacy_result = legacy_oku("gida.pdf")

# YENİ test aracı (önerilen)
import subprocess
subprocess.run(["python", "test_oku_cop.py", "gida.pdf", "--debug"])

# Debug araçları
python debug_gida_table.py      # Tablo yapısı analizi
python debug_meslek_dersleri.py # MESLEK DERSLERİ algılama testi
```

### PDF Cache Yönetimi ⭐ **GÜNCELLENDİ**
```python
from modules.utils import (
    download_and_cache_pdf, 
    get_cop_cache_path,
    validate_pdf_file, 
    cleanup_temp_files
)

# Organize cache sistemi (ÇÖP için özel)
file_path = download_and_cache_pdf(
    url="https://example.com/cop.pdf",
    cache_type="cop",
    alan_adi="Bilişim Teknolojileri",
    additional_info="9_sinif_2023",
    alan_id="03"  # YENİ: ID bazlı organizasyon
)

# ÇÖP cache yolu oluşturma
cache_path = get_cop_cache_path(
    alan_adi="Gıda Teknolojisi",
    sinif="12",
    year="2023",
    alan_id="04"
)

# PDF doğrulama ve temizlik
if validate_pdf_file(file_path):
    print("PDF geçerli")

cleanup_temp_files()  # Geçici dosyaları temizle
```

### Veritabanı Güncelleme
```python
import sqlite3

with sqlite3.connect('data/temel_plan.db') as conn:
    cursor = conn.cursor()
    # SQL işlemleri
    conn.commit()
```

## 🚀 Gelecek Geliştirmeler

### Planlanan Özellikler
- [ ] Incremental updates
- [x] PDF content validation ✅ (oku_cop.py)
- [ ] Auto-retry with exponential backoff
- [x] Content-based DBF matching ✅
- [x] Modular architecture ✅ (getir_cop.py + oku_cop.py)
- [ ] Real-time monitoring

### Optimizasyon Alanları
- [ ] Async processing
- [ ] Connection pooling
- [ ] Memory optimization
- [ ] Caching strategies

## 📝 Son Notlar

- **MEB Sistem Değişiklikleri**: Site yapısı değişirse modüller güncellenmeli
- **Session Yönetimi**: Özellikle BÖM ve Dal modülleri için kritik
- **PDF Validation**: Dosya bütünlüğü kontrolü önemli
- **Error Recovery**: Network hatalarında robust retry mekanizması

---

## 🔄 Modül Yapısı Değişiklikleri v2.2 ⭐ **YENİ**

### API Migration Kılavuzu

| Eski API (Deprecated) | Yeni API (Önerilen) | Modül | Durum |
|----------------------|---------------------|-------|--------|
| `getir_cop()` | `getir_cop_links()` | getir_cop.py | ✅ Aktif |
| `extract_alan_and_dallar_from_cop_pdf()` | `extract_alan_dal_ders_from_pdf()` | oku_cop.py | ✅ Geliştirildi |
| `oku_cop_pdf_legacy()` | `oku_cop_pdf()` | oku_cop.py | ✅ Aktif |
| `save_cop_results_to_db()` | server.py endpoints | server.py | ⚠️ Değişti |
| - | `oku_cop_pdf_file()` | oku_cop.py | 🆕 Yeni |
| - | `oku_folder_pdfler()` | oku_cop.py | 🆕 Yeni |
| - | `download_cop_pdfs()` | getir_cop.py | 🆕 Yeni |

### Yeni Özellikler Özeti
- **Temiz Sorumluluk Ayrımı**: HTML/indirme vs PDF/analiz
- **Geliştirilmiş Algoritmalar**: İçindekiler analizi, dinamik sütun algılama  
- **Yerel Test Desteği**: Folder bazlı PDF okuma
- **Merkezi Cache**: utils.py ile organize indirme sistemi
- **Validation**: PDF içerik doğrulama fonksiyonları
- **Backward Compatibility**: Eski kod çalışmaya devam eder

### Migration Adımları
1. **Yeni import'ları güncelleyin** (yukarıdaki tablo)
2. **Test edin** (`getir_cop.py + oku_cop.py` wrapper hala çalışır)
3. **Aşamalı geçiş** (eski API deprecation warning verir)
4. **Gelecek**: `getir_cop.py + oku_cop.py` kaldırılacak

---

📊 **Bu CLAUDE.md dosyası, projenin tüm kritik bilgilerini içerir ve Claude Code'un tutarlı çalışması için tasarlanmıştır.**