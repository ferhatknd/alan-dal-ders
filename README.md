# MEB Mesleki Eğitim Ders Veri Çekme ve Ayrıştırma Projesi

## Proje Hakkında

Bu proje, Türkiye Cumhuriyeti Millî Eğitim Bakanlığı'na (MEB) bağlı Mesleki ve Teknik Eğitim Genel Müdürlüğü'nün web sitesinden (`meslek.meb.gov.tr`) alan ve ders bilgilerini çekmek, bu verileri bir web arayüzünde göstermek ve derslere ait PDF dosyalarının içeriğini yapısal veriye dönüştürmek için geliştirilmiştir.

Proje üç ana bileşenden oluşmaktadır:

1.  **Veri Çekici ve API (`server.py` & `alanlar_ve_dersler3.py`):** MEB'in web sitesinden tüm alanları, sınıfları ve bu alanlara ait dersleri (isim, PDF linki vb.) kazıyan Python tabanlı bir web scraper ve bu verileri sunan bir Flask API'sidir.
2.  **Web Arayüzü (React):** Flask API'sinden gelen verileri listeleyen, aranabilir ve filtrelenebilir bir şekilde kullanıcıya sunan modern bir web arayüzüdür.
3.  **PDF Ayrıştırıcı (`dbf_parser_final.py`):** İndirilen ders bilgi formu (DBF) PDF'lerini işleyerek içerisindeki ders adı, kazanımlar, üniteler, konular gibi detaylı bilgileri çıkaran ve bir SQLite veritabanına aktarılmak üzere SQL komutları üreten bir komut satırı aracıdır.

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

### 3. PDF Ayrıştırıcı Kullanımı

Bu araç, web arayüzü aracılığıyla linklerini elde ettiğiniz PDF dosyalarını indirip bir klasöre koyduktan sonra kullanılır. PDF'lerin içindeki detaylı müfredat bilgilerini ayıklayıp bir `.sql` dosyası oluşturur.

*Not: Gerekli kütüphaneler bir önceki adımda `requirements.txt` ile yüklendiği için ek bir kurulum gerekmez.*

```bash
# PDF'lerinizin bulunduğu dizini ve çıktı dosyasının adını belirtin.
python dbf_parser_final.py ./indirilen_pdfler -o cikti.sql
```

Bu komut, `indirilen_pdfler` klasöründeki tüm PDF'leri işleyecek ve veritabanı şeması ile birlikte `INSERT` komutlarını içeren `cikti.sql` dosyasını oluşturacaktır.

## Veri Dosyalarının Yapısı

Proje çalıştırıldığında `data/` klasörü altında bazı önemli dosyalar oluşturulur veya kullanılır:

-   `scraped_data.json`: `server.py` çalıştırıldığında MEB sitesinden çekilen ve işlenen alan/dal/ders verilerinin önbelleğe alındığı ana JSON dosyasıdır. Frontend bu dosyayı okur.
-   `dbf_data_final.json`: `dbf_parser_final.py` betiği çalıştırıldığında, PDF'lerden ayrıştırılan detaylı ders içeriklerinin yapısal olarak tutulduğu JSON dosyasıdır.
-   `indirilen_pdfler/`: (Manuel oluşturulur) Arayüzden linkleri alınan Ders Bilgi Formu (DBF) PDF'lerinin indirileceği klasördür. `dbf_parser_final.py` bu klasörü kaynak olarak kullanır.

## Veri Akışı

1.  Kullanıcı, React arayüzündeki butona tıklar.
2.  Frontend, Flask backend'indeki `/api/scrape-stream` endpoint'ine istek gönderir.
3.  Backend, `alanlar_ve_dersler3.py` scriptini kullanarak MEB sitesinden verileri çekmeye başlar.
4.  İlerleme durumu anlık olarak (Server-Sent Events ile) arayüze gönderilir.
5.  Veri çekme işlemi tamamlandığında, sonuçlar `data/scraped_data.json` dosyasına önbelleklenir.
6.  Arayüz, gelen verileri işleyerek kullanıcıya sunar.
7.  (Manuel Adım) Kullanıcı, arayüzdeki linkleri kullanarak istediği derslerin PDF'lerini indirir.
8.  (Manuel Adım) `dbf_parser_final.py` aracı ile bu PDF'ler işlenerek veritabanı için SQL dosyası oluşturulur.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.
