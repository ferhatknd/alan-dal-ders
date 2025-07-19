import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sqlite3
import json
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, Generator
import re
try:
    from .utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
    from .utils_database import with_database
    from .utils_file_management import download_and_cache_pdf
except ImportError:
    from utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
    from utils_database import with_database
    from utils_file_management import download_and_cache_pdf

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

@with_database
def update_ders_bom_url(cursor, ders_id, bom_url):
    """
    Dersin bom_url sütununu günceller.
    SOLID S: Single Responsibility - sadece veritabanı güncelleme
    
    Args:
        cursor: Veritabanı cursor
        ders_id: Ders ID'si
        bom_url: BÖM URL'si
        
    Returns:
        bool: Başarı durumu
    """
    try:
        cursor.execute(
            "UPDATE temel_plan_ders SET bom_url = ? WHERE id = ?",
            (bom_url, ders_id)
        )
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Ders BOM URL güncelleme hatası (ID: {ders_id}): {e}")
        return False

def find_matching_ders_in_db(bom_ders_adi, alan_id, db_ders_dict):
    """
    BÖM ders adını veritabanındaki derslerle eşleştirir.
    SOLID S: Single Responsibility - sadece ders eşleştirme
    
    Args:
        bom_ders_adi: BÖM ders adı
        alan_id: Alan ID'si
        db_ders_dict: Veritabanı ders mapping'i
        
    Returns:
        ders_id veya None
    """
    # Önce tam eşleşme
    normalized_bom_ders = normalize_to_title_case_tr(bom_ders_adi)
    if normalized_bom_ders in db_ders_dict:
        return db_ders_dict[normalized_bom_ders]
    
    # Kısmi eşleşme - anahtar kelimeler
    bom_keywords = set(normalized_bom_ders.lower().split())
    
    for db_ders_adi, ders_id in db_ders_dict.items():
        db_keywords = set(db_ders_adi.lower().split())
        
        # En az 2 ortak kelime veya ders adının %70'i eşleşirse
        common_words = bom_keywords.intersection(db_keywords)
        if len(common_words) >= 2 or len(common_words) / len(bom_keywords) >= 0.7:
            print(f"🔍 Eşleşme: '{bom_ders_adi}' -> '{db_ders_adi}' (ortak: {common_words})")
            return ders_id
    
    return None

# save_bom_metadata fonksiyonu kaldırıldı - BÖM metadata'ya gerek yok


def process_bom_data_for_area(alan_adi, bom_data, alan_id, db_ders_dict):
    """
    Bir alanın BÖM verilerini işler ve veritabanını günceller.
    SOLID S: Single Responsibility - alan bazlı BÖM işleme
    
    Args:
        alan_adi: Alan adı
        bom_data: BÖM verileri
        alan_id: Veritabanı alan ID'si
        db_ders_dict: Veritabanı ders mapping'i
        
    Yields:
        dict: İlerleme mesajları
        
    Returns:
        tuple: (total_matched, total_updated)
    """
    total_matched = 0
    total_updated = 0
    
    for ders in bom_data.get("dersler", []):
        ders_adi = ders.get("ders_adi", "")
        moduller = ders.get("moduller", [])
        
        if not ders_adi or not moduller:
            continue
            
        # Dersi veritabanında bul
        ders_id = find_matching_ders_in_db(ders_adi, alan_id, db_ders_dict)
        
        if ders_id:
            total_matched += 1
            
            # İlk modülün linkini al (BÖM URL'si olarak)
            ilk_modul = moduller[0]
            bom_url = ilk_modul.get("link", "")
            
            if bom_url:
                # Veritabanını güncelle
                if update_ders_bom_url(ders_id, bom_url):
                    total_updated += 1
                    yield {
                        'type': 'success', 
                        'message': f"✅ {alan_adi} -> '{ders_adi}' dersi eşleşti, BÖM URL güncellendi"
                    }
                else:
                    yield {
                        'type': 'warning', 
                        'message': f"⚠️ {alan_adi} -> '{ders_adi}' eşleşti ama veritabanı güncellenemedi"
                    }
            else:
                yield {
                    'type': 'info', 
                    'message': f"📄 {alan_adi} -> '{ders_adi}' eşleşti ama BÖM URL'si boş"
                }
        else:
            yield {
                'type': 'info', 
                'message': f"🔍 {alan_adi} -> '{ders_adi}' eşleşmeyen ders"
            }
    
    return total_matched, total_updated

def process_single_area_bom(alan, db_areas, db_ders_dict):
    """
    Tek bir alanın BÖM verilerini işler.
    SOLID S: Single Responsibility - tek alan BÖM işleme
    
    Args:
        alan: Alan bilgileri dict
        db_areas: Veritabanı alan bilgileri
        db_ders_dict: Veritabanı ders mapping'i
        
    Yields:
        dict: İlerleme mesajları
    """
    alan_adi = alan['isim']
    
    try:
        # BÖM verilerini çek
        bom_data = get_bom_for_alan(alan['id'], alan_adi, requests.Session())
        
        if bom_data and bom_data.get("dersler"):
            normalized_area_name = normalize_to_title_case_tr(alan_adi)
            
            # Veritabanında alan kontrolü
            area_info = db_areas.get(alan_adi) or db_areas.get(normalized_area_name)
            if area_info:
                alan_id = area_info['id']
                meb_alan_id = area_info.get('meb_alan_id', 'XX')
                
                # BÖM verilerini işle ve veritabanını güncelle
                total_matched = 0
                total_updated = 0
                
                for message in process_bom_data_for_area(alan_adi, bom_data, alan_id, db_ders_dict):
                    yield message
                    if message['type'] == 'success':
                        total_updated += 1
                    if message['type'] in ['success', 'warning', 'info'] and 'eşleşti' in message['message']:
                        total_matched += 1
                
                # Özet raporu
                toplam_bom_dersleri = len(bom_data.get("dersler", []))
                yield {
                    'type': 'progress', 
                    'message': f'{meb_alan_id} - {alan_adi}: {toplam_bom_dersleri} BÖM dersi, {total_matched} eşleşme, {total_updated} güncelleme', 
                    'progress': 1.0
                }
            else:
                yield {'type': 'info', 'message': f"📋 {alan_adi} -> Veritabanında yok, atlanıyor"}
        else:
            yield {'type': 'info', 'message': f"📋 {alan_adi} -> BÖM verisi bulunamadı"}
            
    except requests.exceptions.HTTPError as http_err:
        if http_err.response and 500 <= http_err.response.status_code < 600:
            yield {'type': 'warning', 'message': f"Sunucu hatası (5xx): '{alan_adi}' alanı işlenemedi."}
        else:
            yield {'type': 'warning', 'message': f"HTTP Hatası: '{alan_adi}' - {http_err}"}
    except Exception as exc:
        yield {'type': 'warning', 'message': f"Genel Hata: '{alan_adi}' - {exc}"}

def get_bom_with_db_integration(siniflar=["9", "10", "11", "12"]):
    """
    BÖM verilerini veritabanı entegrasyonu ile çeker ve ders URL'lerini günceller.
    SOLID S: Single Responsibility - BÖM workflow koordinasyonu
    
    Args:
        siniflar: İşlenecek sınıflar listesi (BÖM'de kullanılmıyor, uyumluluk için)
        
    Yields:
        dict: İlerleme mesajları
    """
    yield {'type': 'status', 'message': 'BÖM (Bireysel Öğrenme Materyali) verileri işleniyor...'}
    
    # Veritabanı bilgilerini al
    db_areas = get_areas_from_db()
    if not db_areas:
        yield {'type': 'error', 'message': 'Veritabanında alan bulunamadı! Önce Adım 1\'i çalıştırın.'}
        return
    
    db_ders_dict = get_ders_ids_from_db()
    if not db_ders_dict:
        yield {'type': 'error', 'message': 'Veritabanında ders bulunamadı! Önce dersler yüklenmelidir.'}
        return
    
    yield {'type': 'status', 'message': f'Veritabanından {len(db_areas)} alan ve {len(db_ders_dict)} ders alındı.'}
    
    # BÖM alanlarını çek
    bom_alanlari = get_alanlar_from_moduller()
    if not bom_alanlari:
        yield {'type': 'error', 'message': 'BÖM alanları çekilemedi!'}
        return
        
    yield {'type': 'status', 'message': f'{len(bom_alanlari)} BÖM alanı bulundu, işleniyor...'}
    
    # Sonuçları topla
    total_areas_processed = 0
    total_matches = 0
    total_updates = 0
    
    # SOLID D: Dependency Inversion - ThreadPoolExecutor kullanımı
    with ThreadPoolExecutor(max_workers=3) as executor:  # BÖM için daha az worker
        future_to_alan = {
            executor.submit(list, process_single_area_bom(alan, db_areas, db_ders_dict)): alan 
            for alan in bom_alanlari
        }
        
        for future in as_completed(future_to_alan):
            alan = future_to_alan[future]
            try:
                messages = future.result(timeout=180)  # 3 dakika timeout
                
                area_processed = False
                for message in messages:
                    yield message
                    
                    # İstatistik toplama
                    if message.get('type') == 'progress':
                        area_processed = True
                        # Mesajdan sayıları çıkar
                        msg = message.get('message', '')
                        if 'eşleşme' in msg and 'güncelleme' in msg:
                            # "Örnek: 5 eşleşme, 3 güncelleme" formatından sayıları çıkar
                            import re
                            matches = re.findall(r'(\d+) eşleşme', msg)
                            updates = re.findall(r'(\d+) güncelleme', msg)
                            if matches:
                                total_matches += int(matches[0])
                            if updates:
                                total_updates += int(updates[0])
                
                if area_processed:
                    total_areas_processed += 1
                        
            except Exception as exc:
                yield {'type': 'warning', 'message': f"Future hatası: '{alan['isim']}' - {exc}"}
    
    # Sonuç özeti
    yield {
        'type': 'success', 
        'message': f'BÖM işlemi tamamlandı! {total_areas_processed} alan, {total_matches} eşleşme, {total_updates} veritabanı güncellemesi.'
    }
    
    # BÖM için JSON dosyası gerekli değil - sadece veritabanı güncellemesi
    yield {'type': 'done', 'message': 'BÖM URL\'leri veritabanına kaydedildi.'}

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
