import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sqlite3
import json
import time
from pathlib import Path
import re
try:
    from .utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
    from .utils_database import with_database
except ImportError:
    from utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
    from utils_database import with_database

# Doğru URL: https://meslek.meb.gov.tr/moduller (debug ile doğrulandı)
BASE_BOM_URL = "https://meslek.meb.gov.tr/moduller"
BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

BOM_ROOT_DIR = "data/bom"

@with_database
def get_areas_from_db(cursor):
    """
    Veritabanından alan ID, adları ve MEB ID'leri çeker (BOM için).
    Returns: dict {alan_adi: {'id': alan_id, 'meb_alan_id': meb_alan_id}}
    """
    try:
        cursor.execute("SELECT id, alan_adi, meb_alan_id FROM temel_plan_alan ORDER BY alan_adi")
        results = cursor.fetchall()
        return {alan_adi: {'id': alan_id, 'meb_alan_id': meb_alan_id} for alan_id, alan_adi, meb_alan_id in results}
    except Exception as e:
        print(f"Veritabanı okuma hatası: {e}")
        return {}

@with_database
def get_ders_ids_from_db(cursor):
    """
    Veritabanından ders ID'lerini ve adlarını çeker (BÖM ders organizasyonu için)
    Returns: dict {ders_adi: ders_id}
    """
    try:
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


def find_matching_area_id(html_area_name, db_areas):
    """
    HTML'den gelen alan adını veritabanındaki alanlarla eşleştirir (BOM için).
    Returns: (alan_id, meb_alan_id, matched_name) veya (None, None, None)
    """
    normalized_html_name = normalize_to_title_case_tr(html_area_name)
    
    # Tam eşleşme kontrolü
    if normalized_html_name in db_areas:
        area_info = db_areas[normalized_html_name]
        return area_info['id'], area_info['meb_alan_id'], normalized_html_name
    
    # Kısmi eşleşme kontrolü
    for db_name, area_info in db_areas.items():
        if normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower():
            print(f"BOM Kısmi eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_info['id']})")
            return area_info['id'], area_info['meb_alan_id'], db_name
    
    print(f"BOM Eşleşme bulunamadı: '{html_area_name}' (normalize: '{normalized_html_name}')")
    return None, None, None

def extract_update_year(date_string):
    """
    Tarih stringinden yıl bilgisini çıkarır.
    Örnek: "12.12.2024 00:00:00" → "2024"
    """
    if not date_string:
        return None
    
    # Tarih formatları için regex pattern'leri
    patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY formatı
        r'(\d{4})-(\d{2})-(\d{2})',   # YYYY-MM-DD formatı
        r'(\d{4})',                   # 4 haneli yıl
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, str(date_string))
        for match in matches:
            if isinstance(match, tuple):
                # Tuple'dan yıl bilgisini al
                for group in match:
                    if len(group) == 4 and group.isdigit():
                        year = int(group)
                        if 2000 <= year <= 2030:  # Mantıklı yıl aralığı
                            return str(year)
            else:
                # Direkt match
                if len(match) == 4 and match.isdigit():
                    year = int(match)
                    if 2000 <= year <= 2030:
                        return str(year)
    
    return None

def sanitize_filename(name):
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir.
    utils.py'deki merkezi sanitize_filename_tr fonksiyonunu kullanır.
    """
    return sanitize_filename_tr(name)

def get_alanlar_from_moduller():
    """
    BOM moduller sayfasından doğru alan ID'lerini çeker.
    Bu fonksiyon moduller sayfasında kullanılan gerçek ID formatını döndürür.
    """
    try:
        resp = requests.get(BASE_BOM_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Moduller sayfası yüklenemedi: {e}")
        return []

    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Moduller sayfasındaki alan dropdown'unu bul
    alan_dropdown = soup.find('select', {'name': 'ctl00$ContentPlaceHolder1$DropDownList1'})
    if not alan_dropdown:
        print("Moduller sayfasında alan dropdown bulunamadı!")
        return []
    
    alanlar = []
    for opt in alan_dropdown.find_all('option'):
        val = opt.get('value','').strip()
        name = opt.text.strip()
        if val and val not in ("00","0") and name != "Alanlar":
            alanlar.append({"id": val, "isim": name})
    
    return alanlar

def get_alanlar(sinif_kodu="9"):
    """
    BOM için alanları çeker - artık moduller sayfasından doğru ID'leri alır.
    sinif_kodu parametresi geriye uyumluluk için korundu ama kullanılmıyor.
    """
    return get_alanlar_from_moduller()

def get_aspnet_form_data(soup):
    form_data = {}
    for input_tag in soup.find_all('input', {'type': ['hidden', 'submit', 'text', 'image']}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value
    return form_data

def get_bom_for_alan(alan_id, alan_adi, session):
    bom_data = {"dersler": []}
    try:
        initial_resp = session.get(BASE_BOM_URL, headers=HEADERS, timeout=20)
        initial_resp.raise_for_status()
        initial_soup = BeautifulSoup(initial_resp.text, 'html.parser')

        form_data = get_aspnet_form_data(initial_soup)
        form_data['ctl00$ContentPlaceHolder1$DropDownList1'] = alan_id
        form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$DropDownList1'

        ders_list_resp = session.post(BASE_BOM_URL, data=form_data, headers=HEADERS, timeout=20)
        ders_list_resp.raise_for_status()
        ders_list_soup = BeautifulSoup(ders_list_resp.text, 'html.parser')

        ders_select = ders_list_soup.find('select', {'name': 'ctl00$ContentPlaceHolder1$DropDownList2'})
        if not ders_select:
            return bom_data

        ders_options = ders_select.find_all('option')
        if len(ders_options) <= 1:
            return bom_data

        for ders_option in ders_options:
            ders_value = ders_option.get('value')
            ders_adi = ders_option.text.strip()
            if not ders_value or ders_value == '0':
                continue

            ders_form_data = get_aspnet_form_data(ders_list_soup)
            ders_form_data['ctl00$ContentPlaceHolder1$DropDownList1'] = alan_id
            ders_form_data['ctl00$ContentPlaceHolder1$DropDownList2'] = ders_value
            ders_form_data['ctl00$ContentPlaceHolder1$Button1'] = 'Listele'

            modul_resp = session.post(BASE_BOM_URL, data=ders_form_data, headers=HEADERS, timeout=20)
            modul_resp.raise_for_status()
            modul_soup = BeautifulSoup(modul_resp.text, 'html.parser')

            ders_modulleri = []
            modul_table = modul_soup.find('table', id='ctl00_ContentPlaceHolder1_GridView1')
            if modul_table:
                for row in modul_table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        modul_adi = cols[0].get_text(strip=True)
                        link_tag = cols[1].find('a', href=True)
                        if link_tag:
                            # URL base'ini meslek.meb.gov.tr olarak değiştir
                            if link_tag['href'].startswith('http'):
                                full_link = link_tag['href']
                            else:
                                full_link = requests.compat.urljoin("https://meslek.meb.gov.tr/", link_tag['href'])
                            
                            # Güncelleme tarihini bul (üçüncü sütundan)
                            update_date = ""
                            if len(cols) >= 3:
                                update_date = cols[2].get_text(strip=True)
                            
                            # Güncelleme yılını çıkar
                            update_year = extract_update_year(update_date)
                            
                            ders_modulleri.append({
                                "isim": modul_adi, 
                                "link": full_link,
                                "update_date": update_date,
                                "update_year": update_year
                            })
            
            if ders_modulleri:
                bom_data["dersler"].append({
                    "ders_adi": ders_adi,
                    "moduller": ders_modulleri
                })

    except requests.RequestException as e:
        print(f"BÖM Hata: '{alan_adi}' alanı için veri çekilemedi: {e}")
        return None
    
    return bom_data

def download_and_save_bom_pdf(area_name, modul_link, modul_adi, ders_adi, db_areas=None):
    """
    BOM PDF'ini indirir ve data/bom/{meb_alan_id}_{alan_adi}/ klasörüne kaydeder.
    Ders klasörü oluşturulmaz, tüm dosyalar direkt alan klasörüne kaydedilir.
    """
    try:
        # Veritabanından alan bilgilerini al (eğer daha önce alınmamışsa)
        if db_areas is None:
            db_areas = get_areas_from_db()
        
        # Alan ID'sini bul
        area_id, meb_alan_id, matched_name = find_matching_area_id(area_name, db_areas)
        
        if area_id:
            # MEB ID varsa kullan, yoksa database ID kullan
            if meb_alan_id:
                folder_name = f"{meb_alan_id}_{sanitize_filename(matched_name)}"
            else:
                folder_name = f"{area_id:02d}_{sanitize_filename(matched_name)}"
            bom_dir = Path(BOM_ROOT_DIR) / folder_name
        else:
            # ID bulunamazsa eski sistemi kullan
            safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            bom_dir = Path(BOM_ROOT_DIR) / safe_area_name
        
        # Ana alan klasörünü oluştur (ders alt klasörü oluşturulmaz)
        bom_dir.mkdir(parents=True, exist_ok=True)
        
        # Dosya adını orijinal URL'den çıkar
        pdf_filename = os.path.basename(modul_link)
        pdf_path = bom_dir / pdf_filename
        
        # Eğer dosya zaten mevcutsa atla
        if pdf_path.exists():
            return str(pdf_path), False
        
        # PDF'yi indir
        response = requests.get(modul_link, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        return str(pdf_path), True
        
    except Exception as e:
        pass  # Error handling moved to caller
        return None, False

def save_bom_metadata(area_name, bom_data, db_areas=None):
    """
    BOM metadata'larını JSON dosyasına kaydeder (yeni dizin yapısında).
    """
    try:
        # Veritabanından alan bilgilerini al (eğer daha önce alınmamışsa)
        if db_areas is None:
            db_areas = get_areas_from_db()
        
        # Alan ID'sini bul
        area_id, meb_alan_id, matched_name = find_matching_area_id(area_name, db_areas)
        
        if area_id:
            # MEB ID varsa kullan, yoksa database ID kullan
            if meb_alan_id:
                folder_name = f"{meb_alan_id}_{sanitize_filename(matched_name)}"
            else:
                folder_name = f"{area_id:02d}_{sanitize_filename(matched_name)}"
            bom_dir = Path(BOM_ROOT_DIR) / folder_name
        else:
            # ID bulunamazsa eski sistemi kullan
            safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
            bom_dir = Path(BOM_ROOT_DIR) / safe_area_name
        
        metadata_file = bom_dir / 'bom_metadata.json'
        
        metadata = {
            'alan_adi': area_name,
            'alan_id': area_id,
            'matched_name': matched_name,
            'dersler': bom_data.get('dersler', []),
            'toplam_ders': len(bom_data.get('dersler', [])),
            'olusturma_tarihi': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        pass  # Success message moved to caller
        
    except Exception as e:
        pass  # Error handling moved to caller


def get_bom_with_db_integration(siniflar=["9", "10", "11", "12"]):
    """
    BOM verilerini veritabanı entegrasyonu ile çeker ve dosyaları organize eder.
    Generator olarak her adımda ilerleme mesajı döndürür.
    """
    yield {'type': 'status', 'message': 'BOM (Bireysel Öğrenme Materyali) verileri işleniyor...'}
    
    # Veritabanından alan bilgilerini tek seferde al (performans için)
    db_areas = get_areas_from_db()
    if not db_areas:
        yield {'type': 'error', 'message': 'Veritabanında alan bulunamadı! Önce Adım 1\'i çalıştırın.'}
        return
    
    yield {'type': 'status', 'message': f'Veritabanından {len(db_areas)} alan alındı.'}
    
    # Ana dizini oluştur
    if not os.path.exists(BOM_ROOT_DIR):
        os.makedirs(BOM_ROOT_DIR)
    
    # Tüm sınıflardan benzersiz alanları topla
    all_alanlar_by_sinif = {sinif: get_alanlar(sinif) for sinif in siniflar}
    unique_alanlar = list({v['id']:v for k,v_list in all_alanlar_by_sinif.items() for v in v_list}.values())
    
    yield {'type': 'status', 'message': f'{len(unique_alanlar)} benzersiz alan için BOM verileri çekiliyor...'}
    
    area_bom_data = {}
    total_processed = 0
    total_downloaded = 0
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_alan = {
            executor.submit(get_bom_for_alan, alan['id'], alan['isim'], requests.Session()): alan 
            for alan in unique_alanlar if alan['id'] not in ["0", "00"]
        }
        
        for future in as_completed(future_to_alan):
            alan = future_to_alan[future]
            alan_adi = alan['isim']
            
            try:
                bom_data = future.result()
                
                if bom_data and bom_data.get("dersler"):
                    # Alan adını normalize et ve veritabanında olup olmadığını kontrol et
                    normalized_area_name = normalize_to_title_case_tr(alan_adi)
                    
                    # Hem orijinal hem normalize edilmiş isimle kontrol et
                    if alan_adi in db_areas or normalized_area_name in db_areas:
                        area_bom_data[alan_adi] = bom_data
                        
                        # Her ders ve modülü indir
                        for ders in bom_data.get("dersler", []):
                            ders_adi = ders.get("ders_adi", "")
                            for modul in ders.get("moduller", []):
                                modul_adi = modul.get("isim", "")
                                modul_link = modul.get("link", "")
                                
                                if modul_link:
                                    pdf_path, downloaded = download_and_save_bom_pdf(
                                        alan_adi, 
                                        modul_link, 
                                        modul_adi, 
                                        ders_adi,
                                        db_areas
                                    )
                                    
                                    if pdf_path:
                                        if downloaded:
                                            total_downloaded += 1
                                        total_processed += 1
                                        yield {'type': 'success', 'message': f"📄 {alan_adi} -> {os.path.basename(pdf_path)} ({ders_adi} - {modul_adi})"}
                                    else:
                                        yield {'type': 'warning', 'message': f"❌ {alan_adi} -> BOM indirilemedi ({ders_adi} - {modul_adi})"}
                        
                        # Metadata kaydet
                        save_bom_metadata(alan_adi, bom_data, db_areas)
                        ders_sayisi = len(bom_data.get('dersler', []))
                        
                        # Standardize edilmiş konsol çıktısı - alan bazlı toplam
                        # BOM için alan adından MEB ID'sini bul
                        alan_info = db_areas.get(alan_adi) or db_areas.get(normalize_to_title_case_tr(alan_adi))
                        meb_alan_id = alan_info.get('meb_alan_id') if alan_info else 'XX'
                        
                        # Alan için toplam BOM sayısını hesapla
                        toplam_bom_sayisi = sum(len(ders.get("moduller", [])) for ders in bom_data.get("dersler", []))
                        
                        yield {'type': 'progress', 'message': f'{meb_alan_id} - {alan_adi} (1/1) Toplam {toplam_bom_sayisi} BOM indi.', 'progress': 1.0}
                    else:
                        yield {'type': 'info', 'message': f"📋 {alan_adi} -> Veritabanında yok, atlanıyor"}
                else:
                    yield {'type': 'info', 'message': f"📋 {alan_adi} -> BOM verisi bulunamadı"}
                    
            except requests.exceptions.HTTPError as http_err:
                if http_err.response and 500 <= http_err.response.status_code < 600:
                    yield {'type': 'warning', 'message': f"Sunucu hatası (5xx): '{alan_adi}' alanı işlenemedi. Sunucu kaynaklı bir sorun olabilir, atlanıyor."}
                else:
                    yield {'type': 'warning', 'message': f"HTTP Hatası: '{alan_adi}' alanı işlenirken hata: {http_err}"}
            except Exception as exc:
                yield {'type': 'warning', 'message': f"Genel Hata: '{alan_adi}' alanı işlenirken hata: {exc}"}
    
    # Sonuç özeti
    yield {
        'type': 'success', 
        'message': f'BOM işlemi tamamlandı! {len(area_bom_data)} alan, {total_processed} BOM dosyası işlendi ({total_downloaded} yeni indirme).'
    }
    
    # Son durum için JSON dosyası da oluştur (yedek)
    output_filename = "data/get_bom.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(area_bom_data, f, ensure_ascii=False, indent=4)
    
    yield {'type': 'done', 'message': f'BOM verileri kaydedildi. Yedek dosya: {output_filename}'}

def get_bom():
    """
    BOM (Bireysel Öğrenme Materyali) linklerini çeker ve işler.
    CLAUDE.md prensiplerini uygular: standardize edilmiş fonksiyon adı.
    """
    for message in get_bom_with_db_integration():
        yield message

def main():
    """
    Ana fonksiyon - komut satırından çalıştırıldığında kullanılır.
    """
    print("BOM (Bireysel Öğrenme Materyali) Verileri")
    print("Veritabanı entegrasyonu ile BOM verileri çekiliyor...")
    
    for message in get_bom_with_db_integration():
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
