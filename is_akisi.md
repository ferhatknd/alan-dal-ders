# Mesleki Eğitim Veri İşleme Sistemi - İş Akışı

## Genel Bakış

Bu sistem, Türkiye Cumhuriyeti Milli Eğitim Bakanlığı'nın mesleki ve teknik eğitim verilerini otomatik olarak toplar, organize eder ve veritabanında saklar. Sistem modüler yapıda tasarlanmış olup, her adım bağımsız olarak çalıştırılabilir.

## Sistem Mimarisi

### Ana Bileşenler

- **Database Schema**: `data/schema.sql` - 13 tablo ile kapsamlı veritabanı yapısı
- **Alan-Dal Modülü**: `modules/getir_dal.py` - MEB API'dan alan/dal verilerini çeker
- **ÇÖP Modülü**: `modules/getir_cop.py` - Çerçeve Öğretim Programı verilerini işler
- **ÇÖP Okuma Modülü**: `modules/getir_cop.py` - COP PDF'lerini okur ve analiz eder
- **Yerel Test Modülü**: `modules/getir_cop_oku_local.py` - Yerel PDF test aracı ⭐ **YENİ**
- **Debug Araçları**: `debug_*.py` dosyaları - PDF analiz ve hata ayıklama ⭐ **YENİ**
- **Normalizasyon Modülü**: `modules/utils.py` - Türkçe karakter/metin standardizasyonu ve PDF cache yönetimi ⭐ **GÜNCELLENDİ**

### Veritabanı Yapısı

```
temel_plan_alan (Alanlar)
├── temel_plan_dal (Dallar) 
│   └── temel_plan_ders_dal (İlişki)
│       └── temel_plan_ders (Dersler)
│           ├── temel_plan_ogrenme_birimi
│           ├── temel_plan_konu
│           └── temel_plan_kazanim
```

## İş Akışı Adımları

### Adım 0: Veritabanı Hazırlığı

**Amaç**: Sistem için gerekli veritabanı yapısını oluşturur.

**İşlemler**:
- `data/schema.sql` dosyasından veritabanı şeması yüklenir
- 13 ana tablo oluşturulur (alan, dal, ders, öğrenme birimi, konu, kazanım vb.)
- İndeksler ve tetikleyiciler ayarlanır
- Başlangıç verileri (ölçme yöntemleri, araç-gereç) eklenir

**Çıktı**: `data/temel_plan.db` dosyası

---

### Adım 1: Alan ve Dal Verilerini Getirme

**Dosya**: `modules/getir_dal.py`
**Fonksiyon**: `getir_dal_with_db_integration()`

**Amaç**: Türkiye'deki tüm illerdeki okullara göre mesleki eğitim alanları ve dallarını toplar.

**İşlem Akışı**:

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
- 81 il × ortalama 15 alan × ortalama 8 dal ≈ 10,000 API çağrısı
- Rate limiting: 0.3s/dal, 1.5s/il
- Session yönetimi ile çerez korunumu

---

### Adım 2: Çerçeve Öğretim Programı (ÇÖP) Verilerini İşleme

**Dosya**: `modules/getir_cop.py`
**Fonksiyon**: `getir_cop_with_db_integration()`

**Amaç**: MEB'den ÇÖP PDF dosyalarını indirir, okur ve ders bilgilerini çıkarır.

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

3. **PDF İndirme ve Organizasyon**
   - `download_and_save_cop_pdf()` fonksiyonu
   - `data/cop/{ID:02d}_-_{alan_adi}/` formatında ID bazlı klasör yapısı ⭐ **YENİ**
   - Dosya adı: `cop_{sinif}_sinif_{guncelleme_yili}.pdf`
   - Mevcut dosya kontrolü (gereksiz indirme önleme)

4. **PDF Okuma ve Analiz** ⭐ **YENİ ÖZELLIK**
   - `getir_cop.py` modülü kullanılır
   - `oku_cop_pdf()` fonksiyonu ile PDF içeriği analiz edilir
   - **Alan-Dal-Ders İlişkisi Çıkarma**:
     - PDF'den alan adı tespiti
     - HAFTALIK DERS ÇİZELGESİ bölümlerinden dal adları
     - MESLEK DERSLERİ tablolarından ders listesi
     - Dal-ders eşleştirmesi

5. **Veritabanı Entegrasyonu** ⭐ **YENİ ÖZELLIK**
   - `save_cop_results_to_db()` fonksiyonu
   - Çıkarılan ders bilgileri `temel_plan_ders` tablosuna eklenir
   - `temel_plan_ders_dal` ilişki tablosu güncellenir
   - Otomatik dal oluşturma (gerekirse)

6. **Metadata Kaydetme**
   - Her alan için `cop_metadata.json` dosyası
   - ÇÖP bilgileri `temel_plan_alan.cop_url` sütununda JSON format

**ÇÖP Okuma Detayları** (`getir_cop.py`):

- **Alan Adı Tespiti**: URL pattern veya PDF içeriğinden
- **Dal Bulma**: "DALI" keyword'ü ile biten satırlar
- **Ders Çıkarma**: Tablo ayrıştırma ile MESLEK DERSLERİ bölümü
- **Metin Temizleme**: Türkçe karakter normalizasyonu
- **Eşleştirme**: Fuzzy matching ile dal-ders ilişkilendirme

**Çıktılar**:
- İndirilmiş ÇÖP PDF dosyaları
- Veritabanında ders kayıtları
- `data/getir_cop_sonuc.json` yedek dosyası
- Alan bazında metadata dosyaları

**Performans**:
- 4 sınıf × 50 alan ≈ 200 PDF dosyası
- Paralel indirme (ThreadPoolExecutor)
- PDF okuma: pdfplumber kütüphanesi
- Memory efficient: geçici dosya kullanımı

---

## 🧪 Adım 2.5: Yerel PDF Test ve Debug Süreci ⭐ **YENİ**

**Dosyalar**: 
- `modules/getir_cop_oku_local.py` - Yerel test modülü
- `debug_gida_table.py` - Tablo analiz aracı
- `debug_meslek_dersleri.py` - Kategori algılama test aracı

**Amaç**: İndirilen PDF'lerin işlenmesi öncesi yerel test ve hata ayıklama.

**İşlem Akışı**:

1. **Yerel PDF Hazırlama**
   - PDF dosyalarını proje kök dizinine kopyalama
   - Test için sample dosyalar (örn: `gida.pdf`, `elektrik.pdf`)

2. **Standalone Test**
   ```bash
   # Tüm PDF'leri test et
   python modules/getir_cop_oku_local.py
   
   # Tek PDF'yi test et
   python -c "from modules.getir_cop_oku_local import oku_cop_pdf_file; print(oku_cop_pdf_file('gida.pdf'))"
   ```

3. **Detaylı Debug Analizi**
   ```bash
   # Tablo yapısını analiz et
   python debug_gida_table.py
   
   # MESLEK DERSLERİ kategorisini test et
   python debug_meslek_dersleri.py
   ```

4. **Sonuç Değerlendirmesi**
   - Alan adı tespiti doğruluğu
   - Dal listesi çıkarma başarısı
   - Ders-dal eşleştirme kalitesi
   - Meslek dersleri kategori algılama

5. **Algoritma İyileştirmesi**
   - Pattern matching kuralları güncelleme
   - Tablo ayrıştırma logic düzeltme
   - Metin temizleme regex'leri optimize etme

**Avantajları**:
- Hızlı iterasyon: Network'e bağımlı olmayan test
- Isolated debugging: Tek PDF odaklı analiz
- Pattern development: Yeni PDF türleri için kural geliştirme
- Quality assurance: Üretim öncesi algoritma doğrulama

---

## Veri Akışı Şeması

```
MEB API'lar → getir_dal.py → Veritabanı (Alan/Dal)
     ↓
MEB ÇÖP Sistemi → getir_cop.py → PDF İndirme
     ↓
📥 Local PDF Test → getir_cop_oku_local.py + debug_*.py → Test & Debug ⭐ YENİ
     ↓
PDF Dosyaları → getir_cop.py → Ders Çıkarma
     ↓
Veritabanı (Ders/İlişkiler) ← save_cop_results_to_db()
```

## Teknolojiler

- **Python 3.8+**
- **SQLite3**: Veritabanı
- **Requests**: HTTP API çağrıları
- **BeautifulSoup4**: HTML ayrıştırma
- **pdfplumber**: PDF okuma
- **ThreadPoolExecutor**: Paralel işlem
- **JSON**: Veri formatı

## Önemli Notlar

### Rate Limiting
- MEB API'ları için gecikme süreleri uygulanır
- Session yönetimi ile çerez korunumu
- Timeout değerleri: 10-30 saniye

### Hata Yönetimi
- Her adımda kapsamlı try-catch blokları
- Generator pattern ile real-time progress reporting
- Partial success durumları için warning mesajları

### Veri Bütünlüğü
- Foreign key constraints
- Unique constraints
- Automatic timestamp triggers
- ACID transactions

### Ölçeklenebilirlik
- Modüler yapı
- Bağımsız çalıştırılabilir adımlar
- Incremental processing
- Resume capability

## Gelecek Adımlar

3. **DBF (Ders Bilgi Formu) İşleme** - ✅ ID bazlı klasör sistemi mevcut
4. **DM (Ders Materyali) İşleme** - ⭐ **YENİ**: Ders ID bazlı organizasyon eklendi
5. **BOM (Bireysel Öğrenme Materyali) İşleme** - ⭐ **YENİ**: Ders ID bazlı organizasyon eklendi
6. **Web Arayüzü Geliştirme**
7. **API Endpoints**
8. **Raporlama Sistemi**

## 🗂️ Dosya Organizasyon Sistemi Özeti ⭐ **YENİ**

### Alan Seviyesi Organizasyonu
Tüm modüller alan ID bazlı klasör sistemi kullanır:
```
{ID:02d}_-_{Alan_Adi}/
```

### Ders Seviyesi Organizasyonu (DM & BÖM için)
DM ve BÖM modülleri ders ID bazlı alt organizasyon kullanır:
```
{alan_klasoru}/
├── sinif_{sinif}/                    # DM için
│   └── {ders_id:03d}_-_{ders_adi}.pdf
└── {ders_id:03d}_-_{ders_adi}/       # BÖM için
    └── {modul}.pdf
```

### Veritabanı ID Eşleştirmesi
- **Alan ID**: `temel_plan_alan.id` → Klasör adı prefix
- **Ders ID**: `temel_plan_ders.id` → DM/BÖM dosya organizasyonu
- **Otomatik eşleştirme**: HTML adları ↔ Veritabanı kayıtları
- **Fallback sistemi**: ID bulunamazsa eski format kullanılır

## Test ve Kalite Güvence Süreci ⭐ **YENİ**

### PDF Algoritma Test Döngüsü
```
1. PDF Sample → Local Test (getir_cop_oku_local.py)
2. Debug Analysis (debug_*.py) → Pattern Issues
3. Algorithm Fix → Code Update
4. Re-test → Validation
5. Production Deploy → getir_cop.py
```

### Quality Metrics
- **Alan Adı Doğruluğu**: >95% 
- **Dal Listesi Tamlığı**: >90%
- **Ders-Dal Eşleştirme**: >85%
- **Meslek Kategorisi Algılama**: >90%

### Debug Araçları Kullanımı
- `debug_gida_table.py`: Spesifik PDF'in tablo yapısını inceleme
- `debug_meslek_dersleri.py`: Kategori algılama algoritmasını test etme
- `modules/getir_cop_oku_local.py`: Batch test için ana araç

---

**Son Güncelleme**: 2025-01-13
**Versiyon**: 2.1 (Yerel Test ve Debug Araçları Entegrasyonu)