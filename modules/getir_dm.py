import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sqlite3
import json
import time
from pathlib import Path
try:
    from .utils import normalize_to_title_case_tr
except ImportError:
    from utils import normalize_to_title_case_tr

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

DM_ROOT_DIR = "data/dm"

def get_areas_from_db_for_dm():
    """
    Veritabanından alan ID ve adlarını çeker (DM için).
    Returns: dict {alan_adi: alan_id}
    """
    db_path = "data/temel_plan.db"
    if not os.path.exists(db_path):
        print(f"Veritabanı bulunamadı: {db_path}")
        return {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, alan_adi FROM temel_plan_alan ORDER BY alan_adi")
            results = cursor.fetchall()
            return {alan_adi: alan_id for alan_id, alan_adi in results}
    except Exception as e:
        print(f"Veritabanı okuma hatası: {e}")
        return {}

def get_ders_ids_from_db():
    """
    Veritabanından ders ID'lerini ve adlarını çeker (DM ders organizasyonu için)
    Returns: dict {ders_adi: ders_id}
    """
    db_path = "data/temel_plan.db"
    if not os.path.exists(db_path):
        print(f"Veritabanı bulunamadı: {db_path}")
        return {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, ders_adi FROM temel_plan_ders ORDER BY ders_adi")
            results = cursor.fetchall()
            
        # {ders_adi: id} şeklinde mapping oluştur
        ders_dict = {}
        for ders_id, ders_adi in results:
            if ders_adi:
                ders_dict[ders_adi.strip()] = ders_id
                
        return ders_dict
    except Exception as e:
        print(f"Veritabanı ders bilgileri çekme hatası: {e}")
        return {}

def normalize_dm_area_name(html_area_name):
    """
    HTML'den gelen alan adını utils.py standardına göre normalize eder.
    """
    return normalize_to_title_case_tr(html_area_name)

def find_matching_area_id_for_dm(html_area_name, db_areas):
    """
    HTML'den gelen alan adını veritabanındaki alanlarla eşleştirir (DM için).
    Returns: (alan_id, matched_name) veya (None, None)
    """
    normalized_html_name = normalize_dm_area_name(html_area_name)
    
    # Tam eşleşme kontrolü
    if normalized_html_name in db_areas:
        return db_areas[normalized_html_name], normalized_html_name
    
    # Kısmi eşleşme kontrolü
    for db_name, area_id in db_areas.items():
        if normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower():
            print(f"DM Kısmi eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
            return area_id, db_name
    
    print(f"DM Eşleşme bulunamadı: '{html_area_name}' (normalize: '{normalized_html_name}')")
    return None, None

def sanitize_filename_dm(name):
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir (DM için).
    """
    name = name.replace(" ", "_")
    import re
    name = re.sub(r"[^\w\-_.()]", "", name)
    return name

def get_alanlar(sinif_kodu="9"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    try:
        resp = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
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

def get_dersler_for_alan(alan_id, alan_adi, sinif_kodu="9"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1", "alan_id": alan_id}
    try:
        resp = requests.get(BASE_DERS_ALT_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return []

    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    dersler = []
    for div in soup.find_all('div', class_='p-0 bg-light'):
        a = div.find('a', href=True)
        if not a: continue
        ul = a.find('ul', class_='list-group')
        if not ul: continue

        items = ul.find_all('li')
        ders_adi = items[0].get_text(" ", strip=True)
        sinif_text = ""
        for li in items:
            text = li.get_text(" ", strip=True)
            if "Sınıf" in text and any(char.isdigit() for char in text):
                sinif_text = text
                break
        link = requests.compat.urljoin(resp.url, a['href'].strip())

        dersler.append({"isim": ders_adi,
                        "sinif": sinif_text,
                        "link": link})
    return dersler

def download_and_save_dm_pdf(area_name, ders_link, ders_adi, sinif, db_areas=None):
    """
    DM PDF'ini indirir ve data/dm/{ID}-{alan_adi}/ klasörüne kaydeder.
    """
    try:
        # Veritabanından alan bilgilerini al (eğer daha önce alınmamışsa)
        if db_areas is None:
            db_areas = get_areas_from_db_for_dm()
        
        # Alan ID'sini bul
        area_id, matched_name = find_matching_area_id_for_dm(area_name, db_areas)
        
        if area_id:
            # Klasör adını ID + alan adı formatında oluştur
            folder_name = f"{area_id:02d} - {matched_name}"
            dm_dir = Path(DM_ROOT_DIR) / sanitize_filename_dm(folder_name)
            print(f"  DM Klasör: {folder_name}")
        else:
            # ID bulunamazsa eski sistemi kullan
            safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            dm_dir = Path(DM_ROOT_DIR) / safe_area_name
            print(f"  DM ID bulunamadı, eski format kullanılıyor: {area_name}")
        
        # Sınıf alt klasörü oluştur
        sinif_dir = dm_dir / f"sinif_{sinif}"
        sinif_dir.mkdir(parents=True, exist_ok=True)
        
        # Dosya adını oluştur
        safe_ders_adi = sanitize_filename_dm(ders_adi)
        pdf_filename = f"{safe_ders_adi}.pdf"
        pdf_path = sinif_dir / pdf_filename
        
        # Eğer dosya zaten mevcutsa atla
        if pdf_path.exists():
            return str(pdf_path), False
        
        # PDF'yi indir
        response = requests.get(ders_link, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print(f"  DM PDF kaydedildi: {pdf_path}")
        return str(pdf_path), True
        
    except Exception as e:
        print(f"  DM PDF indirme hatası ({area_name} - {ders_adi}): {e}")
        return None, False

def save_dm_metadata(area_name, sinif_data, db_areas=None):
    """
    DM metadata'larını JSON dosyasına kaydeder (yeni dizin yapısında).
    """
    try:
        # Veritabanından alan bilgilerini al (eğer daha önce alınmamışsa)
        if db_areas is None:
            db_areas = get_areas_from_db_for_dm()
        
        # Alan ID'sini bul
        area_id, matched_name = find_matching_area_id_for_dm(area_name, db_areas)
        
        if area_id:
            # Klasör adını ID + alan adı formatında oluştur
            folder_name = f"{area_id:02d} - {matched_name}"
            dm_dir = Path(DM_ROOT_DIR) / sanitize_filename_dm(folder_name)
        else:
            # ID bulunamazsa eski sistemi kullan
            safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            dm_dir = Path(DM_ROOT_DIR) / safe_area_name
        
        metadata_file = dm_dir / 'dm_metadata.json'
        
        metadata = {
            'alan_adi': area_name,
            'alan_id': area_id,
            'matched_name': matched_name,
            'siniflar': sinif_data,
            'toplam_sinif': len(sinif_data),
            'olusturma_tarihi': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"  DM metadata kaydedildi: {metadata_file}")
        
    except Exception as e:
        print(f"  DM metadata kaydetme hatası ({area_name}): {e}")

def getir_dm(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar ve alanlar için Ders Materyali (PDF) verilerini çeker.
    """
    all_dm_data = {}
    for sinif in siniflar:
        alanlar = get_alanlar(sinif)
        sinif_dm = {}
        for alan in alanlar:
            dersler = get_dersler_for_alan(alan["id"], alan["isim"], sinif)
            sinif_dm[alan["isim"]] = dersler
        all_dm_data[sinif] = sinif_dm
    return all_dm_data

def getir_dm_with_db_integration(siniflar=["9", "10", "11", "12"]):
    """
    DM verilerini veritabanı entegrasyonu ile çeker ve dosyaları organize eder.
    Generator olarak her adımda ilerleme mesajı döndürür.
    """
    yield {'type': 'status', 'message': 'DM (Ders Materyali) verileri işleniyor...'}
    
    # Veritabanından alan bilgilerini tek seferde al (performans için)
    db_areas = get_areas_from_db_for_dm()
    if not db_areas:
        yield {'type': 'error', 'message': 'Veritabanında alan bulunamadı! Önce Adım 1\'i çalıştırın.'}
        return
    
    yield {'type': 'status', 'message': f'Veritabanından {len(db_areas)} alan alındı.'}
    
    # Ana dizini oluştur
    if not os.path.exists(DM_ROOT_DIR):
        os.makedirs(DM_ROOT_DIR)
    
    # Alanları organize et
    area_dm_data = {}
    total_processed = 0
    total_downloaded = 0
    
    for sinif in siniflar:
        yield {'type': 'status', 'message': f'{sinif}. sınıf DM verileri çekiliyor...'}
        
        alanlar = get_alanlar(sinif)
        for alan in alanlar:
            alan_adi = alan["isim"]
            
            # Alan adını normalize et ve veritabanında olup olmadığını kontrol et
            normalized_area_name = normalize_dm_area_name(alan_adi)
            
            # Hem orijinal hem normalize edilmiş isimle kontrol et
            if alan_adi in db_areas or normalized_area_name in db_areas:
                dersler = get_dersler_for_alan(alan["id"], alan_adi, sinif)
                
                if dersler:
                    # Alan verisini organize et
                    if alan_adi not in area_dm_data:
                        area_dm_data[alan_adi] = {}
                    
                    area_dm_data[alan_adi][sinif] = dersler
                    
                    # Her dersi indir
                    for ders in dersler:
                        if ders.get('link'):
                            pdf_path, downloaded = download_and_save_dm_pdf(
                                alan_adi, 
                                ders['link'], 
                                ders['isim'], 
                                sinif,
                                db_areas
                            )
                            
                            if pdf_path:
                                if downloaded:
                                    total_downloaded += 1
                                total_processed += 1
                                yield {'type': 'success', 'message': f"'{alan_adi}' - '{ders['isim']}' ({sinif}. sınıf) DM kaydedildi"}
                            else:
                                yield {'type': 'warning', 'message': f"'{alan_adi}' - '{ders['isim']}' ({sinif}. sınıf) DM indirilemedi"}
                else:
                    yield {'type': 'info', 'message': f"'{alan_adi}' ({sinif}. sınıf) için ders bulunamadı"}
            else:
                yield {'type': 'info', 'message': f"Alan '{alan_adi}' veritabanında yok, atlanıyor"}
    
    # Her alan için metadata dosyalarını oluştur
    yield {'type': 'status', 'message': 'Alan metadata dosyaları oluşturuluyor...'}
    for alan_adi, sinif_data in area_dm_data.items():
        save_dm_metadata(alan_adi, sinif_data, db_areas)
    
    # Sonuç özeti
    yield {
        'type': 'success', 
        'message': f'DM işlemi tamamlandı! {len(area_dm_data)} alan, {total_processed} DM dosyası işlendi ({total_downloaded} yeni indirme).'
    }
    
    # Son durum için JSON dosyası da oluştur (yedek)
    output_filename = "data/getir_dm_sonuc.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(area_dm_data, f, ensure_ascii=False, indent=4)
    
    yield {'type': 'done', 'message': f'DM verileri kaydedildi. Yedek dosya: {output_filename}'}

def main():
    """
    Ana fonksiyon - komut satırından çalıştırıldığında kullanılır.
    """
    print("DM (Ders Materyali) Verileri")
    print("Veritabanı entegrasyonu ile DM verileri çekiliyor...")
    
    for message in getir_dm_with_db_integration():
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
