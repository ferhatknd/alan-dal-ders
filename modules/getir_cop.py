import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sqlite3
import json
import time
from pathlib import Path

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

def getir_cop(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için Çerçeve Öğretim Programı (ÇÖP) verilerini eşzamanlı olarak çeker.
    """
    def get_cop_data_for_class(sinif_kodu):
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        class_cop_data = {}
        try:
            response = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            alan_columns = soup.find_all('div', class_='col-lg-3')
            for column in alan_columns:
                link_tag = column.find('a', href=True)
                if not link_tag or not link_tag['href'].endswith('.pdf') or 'upload/cop' not in link_tag['href']:
                    continue

                cop_link = requests.compat.urljoin(response.url, link_tag['href'])
                
                # COP yapısı farklı - img tagının alt attribute'ından alan adını al
                img_tag = link_tag.find('img', alt=True)
                if not img_tag:
                    continue

                alan_adi = img_tag.get('alt', '').strip()
                
                # Güncelleme yılını ribbon'dan al
                guncelleme_yili = ""
                ribbon = column.find('div', class_='ribbon')
                if ribbon:
                    span_tag = ribbon.find('span')
                    if span_tag:
                        guncelleme_yili = span_tag.get_text(strip=True)

                if alan_adi and cop_link:
                    class_cop_data[alan_adi] = {
                        "link": cop_link,
                        "guncelleme_yili": guncelleme_yili
                    }
        except requests.RequestException as e:
            print(f"ÇÖP Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
        return sinif_kodu, class_cop_data

    all_cop_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_cop_data[sinif] = data
            except Exception as exc:
                print(f"ÇÖP verisi işlenirken hata: {exc}")
    return all_cop_data

def find_or_create_database():
    """
    Veritabanı dosyasını bulur veya oluşturur.
    """
    db_path = "data/temel_plan.db"
    if os.path.exists(db_path):
        return db_path
    
    # data klasörü yoksa oluştur
    os.makedirs("data", exist_ok=True)
    
    # Şema dosyasından veritabanını oluştur
    schema_path = "data/schema.sql"
    if os.path.exists(schema_path):
        with sqlite3.connect(db_path) as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
        print(f"Veritabanı şemadan oluşturuldu: {db_path}")
    
    return db_path

def normalize_area_name(area_name):
    """
    Alan adını normalize eder (büyük/küçük harf ve boşluk temizliği).
    Türkçe karakterleri doğru şekilde işler.
    """
    import unicodedata
    
    if not area_name:
        return ""
    
    # Unicode normalizasyon (NFC) - noktalı i problemi için
    normalized = unicodedata.normalize('NFC', area_name)
    
    # MEB'den gelen problemli karakterleri düzelt
    # U+0130 (İ with dot above) + U+0307 (combining dot above) problemi
    normalized = normalized.replace('İ̇', 'İ')  # İ + combining dot -> sadece İ
    normalized = normalized.replace('i̇', 'i')  # i + combining dot -> sadece i
    normalized = normalized.replace('ı̇', 'i')  # ı + combining dot -> i
    
    # Diğer problemli kombinasyonlar
    normalized = normalized.replace('Ä°', 'İ')  # Latin Capital Letter I with Dot Above
    normalized = normalized.replace('ä±', 'ı')  # Latin Small Letter Dotless I
    
    # Boşlukları temizle
    normalized = normalized.strip()
    # Çoklu boşlukları tek boşluğa çevir
    normalized = ' '.join(normalized.split())
    
    # Türkçe karakterlere uygun Title Case uygula
    # Python'un title() metodu Türkçe I/ı karakterlerini doğru işleyemez
    turkish_upper_map = {
        'ı': 'I', 'i': 'İ', 'ğ': 'Ğ', 'ü': 'Ü', 'ş': 'Ş', 'ö': 'Ö', 'ç': 'Ç'
    }
    turkish_lower_map = {
        'I': 'ı', 'İ': 'i', 'Ğ': 'ğ', 'Ü': 'ü', 'Ş': 'ş', 'Ö': 'ö', 'Ç': 'ç'
    }
    
    # Önce tümünü küçük harfe çevir (Türkçe kurallarına göre)
    result = ""
    for char in normalized:
        if char in turkish_lower_map:
            result += turkish_lower_map[char]
        else:
            result += char.lower()
    
    # Sonra her kelimenin ilk harfini büyük yap (Türkçe kurallarına göre)
    words = result.split()
    title_words = []
    
    for word in words:
        if word:
            first_char = word[0]
            if first_char in turkish_upper_map:
                title_word = turkish_upper_map[first_char] + word[1:]
            else:
                title_word = first_char.upper() + word[1:]
            title_words.append(title_word)
    
    return ' '.join(title_words)

def get_existing_areas_from_db(db_path):
    """
    Veritabanından mevcut alanları al.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, alan_adi FROM temel_plan_alan ORDER BY alan_adi")
            # Hem orijinal hem normalize edilmiş adları içeren bir mapping oluştur
            areas = {}
            for alan_id, alan_adi in cursor.fetchall():
                areas[alan_adi] = alan_id
                # Normalize edilmiş versiyonu da ekle
                normalized = normalize_area_name(alan_adi)
                if normalized != alan_adi:
                    areas[normalized] = alan_id
            return areas
    except Exception as e:
        print(f"Alanlar alınırken hata: {e}")
        return {}

def get_alanlar(sinif_kodu="9"):
    """
    MEB'den alan ID'lerini ve isimlerini çeker.
    """
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    try:
        resp = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"MEB alan listesi çekilemedi: {e}")
        return []

    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec")
    if not sel:
        return []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value','').strip()
        name = opt.text.strip()
        if val and val not in ("00","0"):
            alanlar.append({"id": val, "isim": name})
    return alanlar

def update_meb_alan_ids(db_path):
    """
    MEB'den alan ID'lerini çekip veritabanındaki meb_alan_id sütununa yazar.
    Eğer alan yoksa yeni alan oluşturur.
    """
    try:
        # MEB'den alan listesini çek
        meb_alanlar = get_alanlar()
        if not meb_alanlar:
            print("MEB'den alan listesi çekilemedi")
            return False
        
        print(f"MEB'den {len(meb_alanlar)} alan bilgisi çekildi")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            updated_count = 0
            created_count = 0
            
            for meb_alan in meb_alanlar:
                meb_alan_id = meb_alan["id"]
                meb_alan_adi = meb_alan["isim"]
                
                # Normalize edilmiş alan adı
                normalized_alan_adi = normalize_area_name(meb_alan_adi)
                
                # Veritabanında bu alan adını ara (hem orijinal hem normalize edilmiş)
                cursor.execute("""
                    SELECT id, alan_adi, meb_alan_id FROM temel_plan_alan 
                    WHERE alan_adi = ? OR alan_adi = ?
                """, (meb_alan_adi, normalized_alan_adi))
                
                result = cursor.fetchone()
                if result:
                    db_id, db_alan_adi, existing_meb_id = result
                    
                    # Eğer meb_alan_id boşsa veya farklıysa güncelle
                    if not existing_meb_id or existing_meb_id != meb_alan_id:
                        cursor.execute("""
                            UPDATE temel_plan_alan 
                            SET meb_alan_id = ? 
                            WHERE id = ?
                        """, (meb_alan_id, db_id))
                        updated_count += 1
                        print(f"  Güncellendi: '{db_alan_adi}' -> MEB ID: {meb_alan_id}")
                else:
                    # Alan yoksa yeni oluştur
                    cursor.execute("""
                        INSERT INTO temel_plan_alan (alan_adi, meb_alan_id) 
                        VALUES (?, ?)
                    """, (normalized_alan_adi, meb_alan_id))
                    created_count += 1
                    print(f"  Oluşturuldu: '{normalized_alan_adi}' -> MEB ID: {meb_alan_id}")
                
            conn.commit()
            print(f"Toplam {updated_count} alan güncellendi, {created_count} yeni alan oluşturuldu")
            return True
            
    except Exception as e:
        print(f"MEB alan ID güncelleme hatası: {e}")
        return False

def update_area_cop_url(area_name, cop_url, sinif, guncelleme_yili, db_path):
    """
    Alanın ÇÖP URL'sini veritabanında günceller.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Alanı bul
            cursor.execute(
                "SELECT id, cop_url FROM temel_plan_alan WHERE alan_adi = ?",
                (area_name,)
            )
            result = cursor.fetchone()
            
            if result:
                area_id, existing_cop_url = result
                
                # Mevcut ÇÖP URL'lerini parse et
                cop_data = {}
                if existing_cop_url:
                    try:
                        cop_data = json.loads(existing_cop_url)
                    except:
                        cop_data = {}
                
                # Yeni sınıf verisini ekle
                cop_data[sinif] = {
                    'link': cop_url,
                    'guncelleme_yili': guncelleme_yili
                }
                
                # Veritabanını güncelle
                cursor.execute(
                    "UPDATE temel_plan_alan SET cop_url = ? WHERE id = ?",
                    (json.dumps(cop_data), area_id)
                )
                
                conn.commit()
                return area_id
            else:
                print(f"Alan '{area_name}' veritabanında bulunamadı - önce Adım 1'ı çalıştırın")
                return None
                
    except Exception as e:
        print(f"ÇÖP URL güncelleme hatası ({area_name}): {e}")
        return None

def download_and_save_cop_pdf(area_name, cop_url, sinif, guncelleme_yili):
    """
    ÇÖP PDF'ini indirir ve alan klasörüne kaydeder.
    """
    try:
        # Alan klasör yapısını kontrol et
        safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        cop_dir = Path(f"data/alanlar/{safe_area_name}/cop")
        cop_dir.mkdir(parents=True, exist_ok=True)
        
        # Dosya adını oluştur
        pdf_filename = f"cop_{sinif}_sinif_{guncelleme_yili}.pdf"
        pdf_path = cop_dir / pdf_filename
        
        # Eğer dosya zaten mevcutsa atla
        if pdf_path.exists():
            return str(pdf_path), False
        
        # PDF'yi indir
        response = requests.get(cop_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print(f"  ÇÖP PDF kaydedildi: {pdf_path}")
        return str(pdf_path), True
        
    except Exception as e:
        print(f"  ÇÖP PDF indirme hatası ({area_name}): {e}")
        return None, False

def save_cop_metadata(area_name, sinif_data):
    """
    ÇÖP metadata'larını JSON dosyasına kaydeder.
    """
    try:
        safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        cop_dir = Path(f"data/alanlar/{safe_area_name}/cop")
        metadata_file = cop_dir / 'cop_metadata.json'
        
        metadata = {
            'alan_adi': area_name,
            'siniflar': sinif_data,
            'toplam_sinif': len(sinif_data),
            'olusturma_tarihi': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"  ÇÖP metadata kaydedildi: {metadata_file}")
        
    except Exception as e:
        print(f"  ÇÖP metadata kaydetme hatası ({area_name}): {e}")

def getir_cop_with_db_integration(siniflar=["9", "10", "11", "12"]):
    """
    ÇÖP verilerini veritabanı entegrasyonu ile çeker ve dosyaları organize eder.
    Generator olarak her adımda ilerleme mesajı döndürür.
    """
    yield {'type': 'status', 'message': 'Adım 2: ÇÖP (Çerçeve Öğretim Programı) verileri işleniyor...'}
    
    db_path = find_or_create_database()
    if not db_path:
        yield {'type': 'error', 'message': 'Veritabanı oluşturulamadı!'}
        return
    
    # MEB alan ID'lerini güncelle
    yield {'type': 'status', 'message': 'MEB alan ID\'leri güncelleniyor...'}
    if update_meb_alan_ids(db_path):
        yield {'type': 'success', 'message': 'MEB alan ID\'leri başarıyla güncellendi'}
    else:
        yield {'type': 'warning', 'message': 'MEB alan ID\'leri güncellenirken sorun oluştu'}
    
    # Mevcut alanları veritabanından al
    existing_areas = get_existing_areas_from_db(db_path)
    if not existing_areas:
        yield {'type': 'error', 'message': 'Veritabanında alan bulunamadı! Önce Adım 1\'i çalıştırın.'}
        return
    
    yield {'type': 'status', 'message': f'Veritabanından {len(existing_areas)} alan alındı.'}
    
    def get_cop_data_for_class(sinif_kodu):
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        class_cop_data = {}
        try:
            response = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            alan_columns = soup.find_all('div', class_='col-lg-3')
            for column in alan_columns:
                link_tag = column.find('a', href=True)
                if not link_tag or not link_tag['href'].endswith('.pdf') or 'upload/cop' not in link_tag['href']:
                    continue

                cop_link = requests.compat.urljoin(response.url, link_tag['href'])
                
                # COP yapısı farklı - img tagının alt attribute'ından alan adını al
                img_tag = link_tag.find('img', alt=True)
                if not img_tag:
                    continue

                alan_adi = img_tag.get('alt', '').strip()
                
                # Güncelleme yılını ribbon'dan al
                guncelleme_yili = ""
                ribbon = column.find('div', class_='ribbon')
                if ribbon:
                    span_tag = ribbon.find('span')
                    if span_tag:
                        guncelleme_yili = span_tag.get_text(strip=True)

                if alan_adi and cop_link:
                    class_cop_data[alan_adi] = {
                        "link": cop_link,
                        "guncelleme_yili": guncelleme_yili
                    }
        except requests.RequestException as e:
            print(f"ÇÖP Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
        return sinif_kodu, class_cop_data
    
    yield {'type': 'status', 'message': f'{len(siniflar)} sınıf için ÇÖP verileri çekiliyor...'}
    
    # Tüm sınıflar için ÇÖP verilerini çek
    all_cop_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_cop_data[sinif] = data
                yield {'type': 'status', 'message': f'{sinif}. sınıf ÇÖP verileri çekildi ({len(data)} alan)'}
            except Exception as exc:
                yield {'type': 'warning', 'message': f'ÇÖP verisi işlenirken hata: {exc}'}
    
    # Alanları organize et ve veritabanına kaydet
    area_cop_data = {}
    total_processed = 0
    total_downloaded = 0
    
    for sinif, sinif_data in all_cop_data.items():
        for alan_adi, cop_info in sinif_data.items():
            # Alan adını normalize et ve veritabanında olup olmadığını kontrol et
            normalized_area_name = normalize_area_name(alan_adi)
            
            # Hem orijinal hem normalize edilmiş isimle kontrol et
            if alan_adi in existing_areas or normalized_area_name in existing_areas:
                # Alan verisini organize et
                if alan_adi not in area_cop_data:
                    area_cop_data[alan_adi] = {}
                
                area_cop_data[alan_adi][sinif] = cop_info
                
                # Veritabanına kaydet
                area_id = update_area_cop_url(
                    alan_adi, 
                    cop_info['link'], 
                    sinif, 
                    cop_info['guncelleme_yili'], 
                    db_path
                )
                
                if area_id:
                    # PDF'yi indir ve kaydet
                    pdf_path, downloaded = download_and_save_cop_pdf(
                        alan_adi, 
                        cop_info['link'], 
                        sinif, 
                        cop_info['guncelleme_yili']
                    )
                    
                    if pdf_path:
                        if downloaded:
                            total_downloaded += 1
                        total_processed += 1
                        yield {'type': 'success', 'message': f"'{alan_adi}' ({sinif}. sınıf) ÇÖP'u kaydedildi"}
                    else:
                        yield {'type': 'warning', 'message': f"'{alan_adi}' ({sinif}. sınıf) ÇÖP PDF'i indirilemedi"}
                else:
                    yield {'type': 'warning', 'message': f"'{alan_adi}' için veritabanı güncellenemedi"}
            else:
                yield {'type': 'info', 'message': f"Alan '{alan_adi}' veritabanında yok, atlanıyor"}
    
    # Her alan için metadata dosyalarını oluştur
    yield {'type': 'status', 'message': 'Alan metadata dosyaları oluşturuluyor...'}
    for alan_adi, sinif_data in area_cop_data.items():
        save_cop_metadata(alan_adi, sinif_data)
    
    # Sonuç özeti
    yield {
        'type': 'success', 
        'message': f'Adım 2 tamamlandı! {len(area_cop_data)} alan, {total_processed} ÇÖP dosyası işlendi ({total_downloaded} yeni indirme).'
    }
    
    # Son durum için JSON dosyası da oluştur (yedek)
    output_filename = "data/getir_cop_sonuc.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(area_cop_data, f, ensure_ascii=False, indent=4)
    
    yield {'type': 'done', 'message': f'ÇÖP verileri veritabanına kaydedildi. Yedek dosya: {output_filename}'}

def main():
    """
    Ana fonksiyon - komut satırından çalıştırıldığında kullanılır.
    """
    import sys
    
    # Eğer --update-meb-ids parametresi varsa sadece MEB ID güncelleme yapar
    if len(sys.argv) > 1 and sys.argv[1] == '--update-meb-ids':
        print("MEB Alan ID'leri Güncelleniyor...")
        db_path = find_or_create_database()
        if db_path:
            update_meb_alan_ids(db_path)
        return
    
    print("Adım 2: ÇÖP (Çerçeve Öğretim Programı) Verileri")
    print("Veritabanı entegrasyonu ile ÇÖP verileri çekiliyor...")
    
    for message in getir_cop_with_db_integration():
        if message['type'] == 'error':
            print(f"❌ HATA: {message['message']}")
            return
        elif message['type'] == 'warning':
            print(f"⚠️  UYARI: {message['message']}")
        elif message['type'] == 'success':
            print(f"✅ {message['message']}")
        elif message['type'] == 'done':
            print(f"🎉 {message['message']}")
            break
        else:
            print(f"ℹ️  {message['message']}")

if __name__ == "__main__":
    main()
