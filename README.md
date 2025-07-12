# MEB Mesleki Eğitim Ders Veri Çekme ve Ayrıştırma Projesi

## Proje Hakkında

Bu proje, Türkiye Cumhuriyeti Millî Eğitim Bakanlığı'na (MEB) bağlı Mesleki ve Teknik Eğitim Genel Müdürlüğü'nün web sitesinden (`meslek.meb.gov.tr`) alan ve ders bilgilerini çekmek, bu verileri bir web arayüzünde göstermek ve derslere ait PDF dosyalarının içeriğini yapısal veriye dönüştürmek için geliştirilmiştir.

Proje iki ana bileşenden oluşmaktadır:

1.  **Flask Backend (`server.py`):** MEB'in web sitesinden veri çeken, DBF dosyalarını indirip açan, PDF'leri ayrıştıran ve tüm bu işlemleri Server-Sent Events (SSE) üzerinden real-time olarak raporlayan bir REST API sunucusudur.
2.  **React Frontend (`src/App.js`):** Backend'den gelen verileri kullanıcı dostu bir arayüzde gösteren, real-time progress takibi yapan ve filtreleme/arama özellikli modern bir web uygulamasıdır.

### Sistem Özellikleri

#### Backend Fonksiyonalite (`server.py`)
-   **Web Scraping:** `alanlar_ve_dersler3.py` ile MEB sitesinden veri çekme
-   **Real-time İletişim:** Server-Sent Events (SSE) ile anlık progress raporlama
-   **DBF İşlemleri:** RAR/ZIP dosyalarını otomatik indirme ve açma
-   **PDF Ayrıştırma:** `oku.py` modülü ile PDF içerik analizi
-   **Önbellekleme:** JSON dosyalarında veri saklama ve cache yönetimi

#### Frontend Özellikleri (`src/App.js`)
-   **Real-time Progress:** SSE ile backend işlemlerini canlı takip
-   **Arama ve Filtreleme:** Debounced search ile performanslı filtreleme  
-   **Kategorik Veri Görüntüleme:** DBF, ÇÖP, DM, BÖM verilerini ayrı ayrı getirme
-   **Dosya İşlemleri:** DBF dosyalarını indirme, açma ve eşleştirme
-   **Hata Yönetimi:** Başarısız işlemler için retry mekanizması

#### Çekilen Veri Türleri
-   **Alanlar ve Ders Materyalleri:** Alan listeleri ve ders PDF linkleri (`dmgoster.aspx`)
-   **Ders Bilgi Formları (DBF):** Sınıf bazında DBF RAR/ZIP dosyaları (`dbflistele.aspx`)
-   **Çerçeve Öğretim Programları (ÇÖP):** Alan öğretim programları (`cercevelistele.aspx`)
-   **Bireysel Öğrenme Materyalleri (BÖM):** Modül PDF'leri (`moduller`)

!Proje Arayüzü

## Teknoloji Yığını

-   **Backend:** Python, Flask, Requests, BeautifulSoup4
-   **Frontend:** React, JavaScript, CSS
-   **PDF Parser:** Python, pdfplumber

## Kurulum ve Çalıştırma

### Gereksinimler

-   Python 3.x
-   Node.js ve npm
-   `pip` (Python paket yöneticisi)

### 1. Backend (Flask API) Kurulumu

Backend, veri çekme işlemini yönetir ve frontend'e veri sağlar.

```bash
# 1. Python için bir sanal ortam oluşturun (önerilir)
python -m venv venv
source venv/bin/activate  # macOS/Linux için
# venv\Scripts\activate    # Windows için

# 2. Gerekli Python kütüphanelerini `requirements.txt` dosyasından yükleyin
pip install -r requirements.txt

# 3. Flask sunucusunu başlatın
# Sunucu varsayılan olarak http://localhost:5001 adresinde çalışacaktır.
python server.py
```

Sunucu çalıştığında, frontend uygulaması veri çekme ve önbelleğe alınmış verileri okuma işlemlerini bu sunucu üzerinden yapacaktır.

### 2. Frontend (React Arayüzü) Kurulumu

Frontend, kullanıcıların verileri görmesini ve arama yapmasını sağlar.

```bash
# 1. Gerekli Node.js paketlerini yükleyin
npm install

# 2. React geliştirme sunucusunu başlatın
# Uygulama varsayılan olarak http://localhost:3000 adresinde açılacaktır.
npm start
```

Tarayıcınızda `http://localhost:3000` adresini açtığınızda, "Verileri Çek" butonuna tıklayarak veri kazıma işlemini başlatabilirsiniz. İşlem tamamlandığında veriler ekranda listelenecektir.

### 3. PDF İşleme

PDF dosyaları iki yolla işlenebilir:

#### A) Web Arayüzü Üzerinden (Önerilen)
1. React arayüzünde "PDF URL'si işle" özelliğini kullanın
2. PDF URL'sini girin, sistem otomatik olarak indirir ve analiz eder
3. İşlem sonuçları real-time olarak görüntülenir

#### B) Komut Satırından
```bash
# Tek PDF dosyası işleme
python oku.py dosya.pdf

# Toplu PDF işleme (eski yöntem)
python dbf_parser_final.py ./indirilen_pdfler -o cikti.sql
```

## Veri Dosyalarının Yapısı

Proje çalıştırıldığında `data/` klasörü altında bazı önemli dosyalar oluşturulur veya kullanılır:

-   `scraped_data.json`: `server.py` çalıştırıldığında MEB sitesinden çekilen ve işlenen alan/dal/ders verilerinin önbelleğe alındığı ana JSON dosyasıdır. Frontend bu dosyayı okur.
-   `dbf_data_final.json`: `dbf_parser_final.py` betiği çalıştırıldığında, PDF'lerden ayrıştırılan detaylı ders içeriklerinin yapısal olarak tutulduğu JSON dosyasıdır.
-   `indirilen_pdfler/`: (Manuel oluşturulur) Arayüzden linkleri alınan Ders Bilgi Formu (DBF) PDF'lerinin indirileceği klasördür. `dbf_parser_final.py` bu klasörü kaynak olarak kullanır.

## API Endpoints

### Veri Çekme
- `GET /api/get-cached-data` - Önbellekteki verileri getir
- `GET /api/scrape-stream` - MEB sitesinden veri çek (SSE)
- `POST /api/process-pdf` - PDF dosyasını işle (SSE)

### Kategorik Veri
- `GET /api/get-dbf` - Ders Bilgi Formu verilerini getir
- `GET /api/get-cop` - Çerçeve Öğretim Programı verilerini getir  
- `GET /api/get-dm` - Ders Materyali verilerini getir
- `GET /api/get-bom` - Bireysel Öğrenme Materyali verilerini getir

### DBF İşlemleri
- `GET /api/dbf-download-extract` - DBF dosyalarını indir ve aç (SSE)
- `GET /api/dbf-retry-extract-all` - Tüm DBF'leri tekrar aç (SSE)
- `POST /api/dbf-retry-extract` - Belirli DBF'yi tekrar aç
- `POST /api/dbf-match-refresh` - DBF eşleştirmesini güncelle

## Veri Akışı

1.  **İlk Yükleme:** Frontend önbellekten veri çeker (`/api/get-cached-data`)
2.  **Veri Çekme:** Kullanıcı butona tıklayınca SSE ile real-time veri çekme başlar
3.  **Progress Takibi:** Her adım SSE ile frontend'e gönderilir ve UI güncellenir
4.  **Önbellekleme:** Veriler `data/scraped_data.json` dosyasına kaydedilir
5.  **DBF İşlemleri:** Opsiyonel olarak DBF dosyaları otomatik indirilebilir/açılabilir
6.  **PDF İşleme:** Seçilen PDF'ler `oku.py` ile ayrıştırılıp yapısal veriye dönüştürülür

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.
