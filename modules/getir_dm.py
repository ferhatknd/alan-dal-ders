"""
modules/getir_dm.py - DM (Ders Materyali) İndirme Modülü

Bu modül, MEB sitesinden Ders Materyali (DM) PDF'lerinin
linklerini çeker, dosyaları `utils.py` kullanarak indirir ve bu süreçte
veritabanında eksik olan alanları ekler.

Doğru URL: https://meslek.meb.gov.tr/dm_listele.aspx?sinif_kodu={sinif}&kurum_id=1
"""

import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import time

try:
    from .utils import normalize_to_title_case_tr, find_or_create_database, get_or_create_alan, download_and_cache_pdf, with_database
except ImportError:
    from utils import normalize_to_title_case_tr, find_or_create_database, get_or_create_alan, download_and_cache_pdf, with_database

# Doğru URL yapısı
BASE_DM_URL = "https://meslek.meb.gov.tr/dm_listele.aspx"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

@with_database
def get_areas_from_db_with_meb_id(cursor):
    """
    Veritabanından alan ID, adı ve MEB ID'sini çeker.
    Returns: dict {alan_adi: {'id': alan_id, 'meb_alan_id': meb_alan_id}}
    """
    try:
        cursor.execute("SELECT id, alan_adi, meb_alan_id FROM temel_plan_alan ORDER BY alan_adi")
        results = cursor.fetchall()
        return {alan_adi: {'id': area_id, 'meb_alan_id': meb_alan_id} for area_id, alan_adi, meb_alan_id in results}
    except Exception as e:
        print(f"Veritabanı okuma hatası: {e}")
        return {}

def extract_update_year(date_string):
    """
    Tarih stringinden yıl bilgisini çıkarır.
    Örnek: "12.12.2024 00:00:00" → "2024"
    """
    if not date_string:
        return None
    
    # Tarih formatları için regex pattern'leri
    patterns = [
        r'(\d{4})',  # 4 haneli yıl
        r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY formatı
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD formatı
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(date_string))
        if match:
            # En uzun match'i (yıl) al
            groups = match.groups()
            for group in groups:
                if len(group) == 4 and group.isdigit():
                    year = int(group)
                    if 2000 <= year <= 2030:  # Mantıklı yıl aralığı
                        return str(year)
    
    return None

def get_dm_data_for_class(sinif_kodu):
    """
    Belirli bir sınıf için DM verilerini çeker.
    Doğru URL kullanır: dm_listele.aspx?sinif_kodu={sinif}&kurum_id=1
    """
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    class_dm_data = {}
    
    try:
        response = requests.get(BASE_DM_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Card yapısından bilgileri çıkar
        cards = soup.find_all('div', class_='card')
        
        for card in cards:
            try:
                # Card header'dan alan adını çıkar
                card_header = card.find('div', class_='card-header')
                if not card_header:
                    continue
                    
                alan_adi = card_header.get_text(strip=True)
                if not alan_adi:
                    continue
                
                # Card body'den PDF linklerini çıkar
                card_body = card.find('div', class_='card-body')
                if not card_body:
                    continue
                
                dm_list = []
                
                # Liste elemanlarını bul
                list_items = card_body.find_all('li') or card_body.find_all('a', href=True)
                
                for item in list_items:
                    if item.name == 'li':
                        link_tag = item.find('a', href=True)
                    else:
                        link_tag = item
                    
                    if not link_tag:
                        continue
                    
                    href = link_tag.get('href', '').strip()
                    if not href.endswith('.pdf'):
                        continue
                    
                    # PDF URL'sini tam URL'ye çevir
                    if href.startswith('http'):
                        pdf_url = href
                    else:
                        pdf_url = f"https://meslek.meb.gov.tr/{href.lstrip('/')}"
                    
                    # Ders adını ve metadata'yı çıkar
                    title_text = link_tag.get_text(strip=True)
                    
                    # Güncelleme tarihini bul (parent element'lerde ara)
                    update_date = ""
                    parent = item.parent
                    while parent and not update_date:
                        date_text = parent.get_text()
                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_text)
                        if date_match:
                            update_date = date_match.group(1)
                            break
                        parent = parent.parent
                    
                    # Güncelleme yılını çıkar
                    update_year = extract_update_year(update_date)
                    
                    dm_info = {
                        'title': title_text,
                        'pdf_url': pdf_url,
                        'update_date': update_date,
                        'update_year': update_year,
                        'sinif': sinif_kodu
                    }
                    
                    dm_list.append(dm_info)
                
                if dm_list:
                    class_dm_data[alan_adi] = dm_list
                    
            except Exception as e:
                print(f"Card işleme hatası: {e}")
                continue
        
        return class_dm_data
        
    except Exception as e:
        print(f"DM verileri çekilirken hata (Sınıf {sinif_kodu}): {e}")
        return {}

def get_dm():
    """
    DM (Ders Materyali) linklerini çeker ve işler.
    HTML parsing ile card yapısından bilgileri çıkarır.
    URL'leri JSON formatında gruplar ve veritabanına kaydeder.
    PDF dosyalarını indirir (açmaz).
    data/get_dm.json çıktı dosyası üretir.
    Progress mesajları yield eder.
    """
    # Database connection handling
    db_path = find_or_create_database()
    if not db_path:
        yield {'type': 'error', 'message': 'Database not found'}
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Tüm sınıflar için DM verilerini çek
            siniflar = ["9", "10", "11", "12"]
            yield {'type': 'status', 'message': 'MEB sitesinden güncel DM linkleri çekiliyor...'}
            
            all_dm_data = {}
            total_dm_count = 0
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_sinif = {executor.submit(get_dm_data_for_class, sinif): sinif for sinif in siniflar}
                
                for future in as_completed(future_to_sinif):
                    sinif = future_to_sinif[future]
                    try:
                        sinif_data = future.result()
                        if sinif_data:
                            all_dm_data[sinif] = sinif_data
                            sinif_count = sum(len(dm_list) for dm_list in sinif_data.values())
                            total_dm_count += sinif_count
                            yield {'type': 'success', 'message': f'{sinif}. sınıf: {len(sinif_data)} alan, {sinif_count} DM bulundu'}
                    except Exception as e:
                        yield {'type': 'error', 'message': f'{sinif}. sınıf DM verileri çekilirken hata: {e}'}
            
            yield {'type': 'status', 'message': f'Toplam {total_dm_count} DM linki bulundu.'}
            
            # Alan bazında URL'leri grupla ve veritabanına kaydet
            alan_dm_urls = {}
            processed_areas = set()
            
            for sinif, sinif_data in all_dm_data.items():
                for alan_adi, dm_list in sinif_data.items():
                    if alan_adi not in alan_dm_urls:
                        alan_dm_urls[alan_adi] = {
                            'siniflar': {}
                        }
                    
                    # Sınıf bazında DM'leri kaydet
                    alan_dm_urls[alan_adi]['siniflar'][sinif] = dm_list
                    processed_areas.add(alan_adi)
            
            yield {'type': 'status', 'message': f'{len(processed_areas)} alan için DM verileri gruplandı.'}
            
            # Veritabanı alanlarını al
            db_areas = get_areas_from_db_with_meb_id()
            
            # ÖNCE: Tüm URL'leri veritabanına kaydet
            yield {'type': 'status', 'message': 'DM URL\'leri veritabanına kaydediliyor...'}
            
            saved_alan_count = 0
            for alan_adi, alan_info in alan_dm_urls.items():
                try:
                    # Alan bilgilerini veritabanından al
                    normalized_alan_adi = normalize_to_title_case_tr(alan_adi)
                    area_db_info = db_areas.get(normalized_alan_adi) or db_areas.get(alan_adi)
                    
                    if area_db_info:
                        meb_alan_id = area_db_info['meb_alan_id']
                        
                        # DM URL'lerini JSON formatında kaydet
                        dm_urls_json = json.dumps(alan_info['siniflar'])
                        
                        # Veritabanında dm_url sütunu yoksa, get_or_create_alan kullan
                        get_or_create_alan(cursor, normalized_alan_adi, meb_alan_id=meb_alan_id)
                        
                        # DM URL'lerini ayrı olarak güncelle (eğer sütun varsa)
                        try:
                            cursor.execute("""
                                UPDATE temel_plan_alan 
                                SET dm_url = ?
                                WHERE alan_adi = ?
                            """, (dm_urls_json, normalized_alan_adi))
                        except sqlite3.OperationalError:
                            # dm_url sütunu yoksa atla
                            pass
                        
                        conn.commit()
                        saved_alan_count += 1
                        yield {'type': 'progress', 'message': f'DM URL kaydedildi: {alan_adi}', 'progress': saved_alan_count / len(alan_dm_urls)}
                    else:
                        # Alan veritabanında yoksa otomatik oluştur
                        alan_id = get_or_create_alan(cursor, normalized_alan_adi)
                        conn.commit()
                        yield {'type': 'warning', 'message': f'Yeni alan oluşturuldu: {alan_adi}'}
                        saved_alan_count += 1
                        
                except Exception as e:
                    yield {'type': 'error', 'message': f'DM URL kaydetme hatası ({alan_adi}): {e}'}
                    continue
            
            yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için DM URL\'leri veritabanına kaydedildi.'}
            
            # SONRA: PDF indirme işlemi (isteğe bağlı)
            yield {'type': 'status', 'message': 'PDF dosyaları kontrol ediliyor...'}
            
            processed_pdf_count = 0
            for alan_adi, alan_info in alan_dm_urls.items():
                try:
                    # Alan bilgilerini al
                    normalized_alan_adi = normalize_to_title_case_tr(alan_adi)
                    area_db_info = db_areas.get(normalized_alan_adi) or db_areas.get(alan_adi)
                    
                    if area_db_info:
                        meb_alan_id = area_db_info['meb_alan_id']
                        
                        # Her sınıfın PDF'lerini indir
                        for sinif, dm_list in alan_info['siniflar'].items():
                            for dm_info in dm_list:
                                try:
                                    # MEB ID bazlı klasör yapısı: data/dm/{meb_alan_id}_{alan_adi}/
                                    file_path = download_and_cache_pdf(
                                        dm_info['pdf_url'],
                                        "dm",
                                        alan_adi=normalized_alan_adi,
                                        additional_info=None,  # Dosya adını değiştirme
                                        meb_alan_id=meb_alan_id
                                    )
                                    if file_path:
                                        processed_pdf_count += 1
                                        yield {'type': 'success', 'message': f'PDF hazır: {os.path.basename(file_path)}'}
                                    else:
                                        yield {'type': 'warning', 'message': f'PDF indirme başarısız: {alan_adi} - {dm_info["title"]}'}
                                except Exception as e:
                                    yield {'type': 'error', 'message': f'PDF kontrol hatası ({alan_adi} - {dm_info["title"]}): {e}'}
                    
                except Exception as e:
                    yield {'type': 'error', 'message': f'PDF işleme hatası ({alan_adi}): {e}'}
                    continue
            
            # JSON çıktı dosyası oluştur
            output_filename = "data/get_dm.json"
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(alan_dm_urls, f, ensure_ascii=False, indent=2)
                yield {'type': 'success', 'message': f'DM verileri kaydedildi: {output_filename}'}
            except Exception as e:
                yield {'type': 'error', 'message': f'JSON dosyası kaydedilemedi: {e}'}
            
            yield {'type': 'done', 'message': f'Tüm DM dosyaları işlendi. {len(alan_dm_urls)} alan için URL\'ler veritabanına kaydedildi.'}
            
    except Exception as e:
        yield {'type': 'error', 'message': f'DM indirme iş akışında genel hata: {str(e)}'}

# Bu dosya doğrudan çalıştırıldığında test amaçlı kullanılabilir.
if __name__ == '__main__':
    print("DM PDF İndirme ve DB Ekleme Testi Başlatılıyor...")
    for message in get_dm():
        print(f"[{message.get('type', 'log').upper()}] {message.get('message', '')}")