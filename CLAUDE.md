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
- **`modules/oku_dbf.py`** - ⭐ **YENİDEN ADLANDIRILDI**: DBF PDF parsing ve içerik analizi (eski: oku.py)
- **`modules/getir_dbf.py`** - Ders Bilgi Formları (DBF) verilerini çeker, RAR/ZIP dosyalarını indirir ve açar
- **`modules/oku_cop.py`** - ⭐ **YENİ**: COP (Çerçeve Öğretim Programı) PDF parsing ve analiz modülü - Tamamen yeniden yazıldı
- **`modules/getir_cop_oku_local.py`** - ⭐ **YENİ**: Yerel PDF dosyalarını test etmek için standalone ÇÖP okuma modülü
- **`modules/getir_dm.py`** - Ders Materyalleri (DM) verilerini çeker
- **`modules/getir_bom.py`** - Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker
- **`modules/getir_dal.py`** - Alan-Dal ilişkilerini çeker
- **`modules/utils.py`** - Yardımcı fonksiyonlar, Türkçe karakter normalizasyonu ve **PDF cache yönetimi**

### 🌐 Ana Dosyalar
- **`server.py`** - Ana Flask sunucusu, tüm API endpoint'leri, veritabanı işlemleri ve **istatistik sistemi**
- **`src/App.js`** - ⭐ **YENİLENDİ**: Tek satır workflow UI, console panel, JSON popup'sız tasarım
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
- **ÇÖP Getir:** Çerçeve Öğretim Programı linklerini çek (`modules/getir_cop.py`)
- **DM Getir:** Ders Materyali linklerini çek (`modules/getir_dm.py`)
- **BÖM Getir:** Bireysel Öğrenme Materyali linklerini çek (`modules/getir_bom.py`)
- **Dal Getir:** Alan-Dal ilişkilerini çek (`modules/getir_dal.py`)

### 📄 Adım 2: PDF İşleme ve Analiz
- **DBF İndir ve Aç:** RAR/ZIP dosyalarını otomatik işle
- **ÇÖP PDF'lerini İşle:** PDF içeriklerini analiz et ve veritabanına kaydet
- **Tüm PDF'leri Tekrar İşle:** Başarısız işlemleri yeniden dene

### 💾 Adım 3: Veritabanı Güncellemeleri
- **DBF Eşleştir:** İndirilen dosyalarle dersleri eşleştir
- **Ders Saatlerini Güncelle:** DBF'lerden ders saati bilgilerini çıkar
- **Veritabanına Aktar:** Düzenlenmiş dersleri kaydet

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

**🔧 Kritik İyileştirmeler:**

**1. Alan/Dal Tespiti:**
```python
# Eski: İçindekiler bölümünden (güvenilmez)
# Yeni: HAFTALIK DERS ÇİZELGESİ üstündeki başlıklardan
"KUYUMCULUK TEKNOLOJİSİ ALANI"     → Alan: Kuyumculuk Teknolojisi  
"(TAKI İMALATI DALI)"              → Dal: Takı İmalatı
```

**2. Adjacent Column Search:**
```python
# Header detection: DERSLER sütunu index 3'te
# Data rows: Ders adları index 2'de
# Çözüm: ±2 offset ile arama [0, -1, 1, -2, 2]
```

**3. Encoding-Safe MESLEK DERSLERİ:**
```python
if ("MESLEK DERSLERİ" in kategori_cell or 
    "MESLEKİ DERSLER" in kategori_cell or
    "MESLEK DERSLER" in kategori_cell or
    "MESLEK" in kategori_cell and ("DERS" in kategori_cell)):
```

**4. Smart Filtering:**
```python
# Ders olmayan satırları filtrele
if ("TOPLAM" in potential_upper or 
    "REHBERLİK" in potential_upper and "YÖNLENDİRME" in potential_upper):
    continue  # Atla
```

**📊 Performans Sonuçları:**
- **gemi_11**: 0 → 28 ders (+∞% iyileştirme)
- **bilisim_12**: 0 → 21 ders (+∞% iyileştirme)  
- **kuyumculuk_10**: 0 → 12 ders (+∞% iyileştirme)
- **gida_12**: 0 → 17 ders (+∞% iyileştirme)

**🎯 Output Formatı:**
```
🎯 SONUÇLAR ÖZET:
   📁 PDF: data/cop/kuyumculuk_10/kuyumculuk_10_cop_program.pdf
   📚 Alan Adı: Kuyumculuk Teknolojisi
   🏭 Dal Sayısı: 1
   📖 Toplam Ders Sayısı: 12
```

### 2. 📄 getir_dbf.py

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

### 6. 📄 oku_dbf.py ⭐ **YENİDEN ADLANDIRILDI**

**Amaç:** DBF PDF parsing ve içerik analizi (eski: oku.py).

**🔧 Kritik İyileştirmeler:**
- **Daha İyi Amaç Çıkarma**: `_is_valid_amac_content()` ile 10+ kelime validasyonu
- **Kazanım Eşleştirme Düzeltmesi**: Newline karakterleri için robust handling
- **Temizlik**: Kullanılmayan fonksiyonlar kaldırıldı, sadece DBF işleme odaklı

**Desteklenen Formatlar:**
- PDF (`pdfplumber`)
- DOCX (`python-docx`)

**Ana Fonksiyonlar:**
- `oku_dbf()` - Ana DBF parsing fonksiyonu (eski: oku)
- `extract_ders_adi()` - Dosyadan ders adını çıkarır
- `extract_text_from_pdf()` - PDF metin çıkarma
- `extract_text_from_docx()` - DOCX metin çıkarma

### 7. 📄 getir_cop_oku_local.py ⭐ **YENİ**

**Amaç:** Yerel PDF dosyalarını test etmek için standalone ÇÖP okuma modülü.

**Özellikler:**
- Kök dizindeki PDF dosyalarını otomatik tarar
- `modules/getir_cop_oku.py`'deki fonksiyonları kullanır (kod tekrarı yok)
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

### 8. 📄 utils.py - PDF Cache Yönetimi ⭐ **YENİ**

**Amaç:** Merkezi PDF indirme ve cache yönetimi sistemi.

**Yeni Fonksiyonlar:**
- `download_and_cache_pdf(url, cache_type, alan_adi, additional_info)` - Organize PDF cache sistemi
- `get_temp_pdf_path(url)` - Geçici dosya yolu oluşturma

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

### ⭐ **YENİ**: İstatistik Sistemi
- `GET /api/get-statistics` - Gerçek zamanlı istatistikler (database + disk dosyaları)

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
- ⚠️ **`oku.py` artık `oku_dbf.py` oldu!**
- Import'larda doğru modül adını kullan:
  ```python
  from modules.oku_dbf import oku_dbf, extract_ders_adi  # ✅ Doğru
  from modules.oku import oku  # ❌ Eski, artık yok
  ```

### 2. UI Tasarımı ⭐ **YENİ KURAL**
- **ASLA** JSON popup/display ekranları ekleme
- Tüm veri gösterimleri console panel'de olmalı
- Button istatistikleri database + disk dosyalarından otomatik yüklenmeli
- Real-time logging için SSE kullan

### 3. Veritabanı İşlemleri
- **ASLA** veritabanı dosyasını silme
- Migration'ları `schema.sql`'den uygula
- `IF NOT EXISTS` kullan
- Transaction'ları `with sqlite3.connect()` ile yönet

### 4. PDF İşleme
- Content-based matching kullan (fuzzy matching yerine)
- `modules/oku_dbf.py`'yi DBF PDF okuma için kullan (eski: oku.py)
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

### COP PDF Analizi ⭐ **YENİ SİSTEM**
```python
# Yeni oku_cop.py modülü ile yerel PDF analizi
from modules.oku_cop import oku_cop_pdf_file, oku_tum_pdfler

# Tek PDF dosyası analizi
result = oku_cop_pdf_file("./data/cop/kuyumculuk_10/kuyumculuk_10_cop_program.pdf")

# Dizindeki tüm PDF'leri analiz et
oku_tum_pdfler("./data/cop/bilisim_12/")

# Komut satırından kullanım
python modules/oku_cop.py "./data/cop/gemi_11/"
python modules/oku_cop.py random  # Rastgele dizin seç
```

### Veri Çekme
```python
# Tüm veri tiplerini çek (eski sistem)
from modules.getir_dbf import getir_dbf
from modules.getir_dm import getir_dm
from modules.getir_bom import getir_bom
from modules.getir_dal import main as getir_dal

dbf_data = getir_dbf()
dm_data = getir_dm()
bom_data = getir_bom()
```

### PDF İşleme
```python
from modules.oku_dbf import extract_ders_adi

ders_adi = extract_ders_adi("/path/to/dbf/file.pdf")
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
- [ ] PDF content validation
- [ ] Auto-retry with exponential backoff
- [x] Content-based DBF matching ✅
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

📊 **Bu CLAUDE.md dosyası, projenin tüm kritik bilgilerini içerir ve Claude Code'un tutarlı çalışması için tasarlanmıştır.**