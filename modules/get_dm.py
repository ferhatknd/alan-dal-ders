"""
modules/get_dm.py - DM (Ders Materyali) İndirme Modülü

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
    from .utils_normalize import normalize_to_title_case_tr
    from .utils_database import find_or_create_database, get_or_create_alan, with_database, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached
    from .utils_file_management import download_and_cache_pdf
except ImportError:
    from utils_normalize import normalize_to_title_case_tr
    from utils_database import find_or_create_database, get_or_create_alan, with_database, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached
    from utils_file_management import download_and_cache_pdf

# Doğru URL yapısı
BASE_DM_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"
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

def parse_dm_card(card_div):
    """
    DM card HTML yapısını parse eder.
    
    Beklenen yapı:
    <div class="col-lg-3">
        <div class="card">
            <a href="/upload/dersmateryali/pdf/BY2024KT0902.pdf">
        <div class="card-body">
            <ul class="list-group">
                <li><b>Klavye Teknikleri</b></li>
                <li>Adalet</li>
                <li>9.Sınıf</li>
                <li>Alan Dersi</li>
                <li>12.12.2024 00:00:00</li>
    """
    try:
        # PDF linkini bul
        pdf_link = card_div.find('a', href=True)
        if not pdf_link:
            return None
        
        href = pdf_link.get('href', '').strip()
        if not href.endswith('.pdf'):
            return None
        
        # PDF URL'sini tam URL'ye çevir
        if href.startswith('http'):
            pdf_url = href
        else:
            pdf_url = f"https://meslek.meb.gov.tr{href}"
        
        # Ders adını bul (<b> tagından)
        title_element = card_div.find('b')
        if not title_element:
            return None
        
        title = title_element.get_text(strip=True)
        if not title:
            return None
        
        # List item'larından bilgileri çıkar
        list_items = card_div.find_all('li')
        
        alan_adi = ""
        sinif = ""
        update_date = ""
        
        for li in list_items:
            text = li.get_text(strip=True)
            
            # Ders adını skip et (zaten aldık)
            if title in text:
                continue
                
            # Sınıf bilgisi
            if '.Sınıf' in text or '.sınıf' in text:
                sinif = text.replace('.Sınıf', '').replace('.sınıf', '').strip()
            
            # Tarih bilgisi (format: 12.12.2024 00:00:00)
            elif re.match(r'\d{2}\.\d{2}\.\d{4}', text):
                update_date = text
            
            # Alan adı (diğer bilgiler değilse)
            elif text and 'Alan Dersi' not in text and 'Ortak Ders' not in text:
                # İlk bulduğumuz metin muhtemelen alan adı
                if not alan_adi:
                    alan_adi = text
        
        # Güncelleme yılını çıkar
        update_year = extract_update_year(update_date)
        
        return {
            'title': title,
            'pdf_url': pdf_url,
            'update_date': update_date,
            'update_year': update_year,
            'sinif': sinif,
            'alan_adi': alan_adi
        }
        
    except Exception as e:
        print(f"DM card parse hatası: {e}")
        return None

def get_dm_data_for_area(sinif_kodu, alan_id, alan_adi):
    """
    Belirli bir alan+sınıf için DM verilerini çeker.
    Doğru URL kullanır: dmgoster.aspx?kurum_id=1&sinif_kodu={sinif}&alan_id={alan_id}
    """
    params = {"kurum_id": "1", "sinif_kodu": sinif_kodu, "alan_id": alan_id}
    dm_list = []
    
    try:
        # Debug logging
        url = f"{BASE_DM_URL}?kurum_id=1&sinif_kodu={sinif_kodu}&alan_id={alan_id}"
        print(f"DM URL istegi: {url}")
        
        response = requests.get(BASE_DM_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        # col-lg-3 divlerini bul (DM card yapısı)
        card_divs = soup.find_all('div', class_='col-lg-3')
        
        print(f"  {alan_adi} ({sinif_kodu}. sınıf): {len(card_divs)} card bulundu")
        
        for card_div in card_divs:
            try:
                # Card'ı parse et
                dm_info = parse_dm_card(card_div)
                if dm_info:
                    # Sınıf ve alan bilgilerini ekle
                    dm_info['sinif'] = sinif_kodu
                    dm_info['alan_adi'] = alan_adi
                    dm_list.append(dm_info)
                    print(f"    DM bulundu: {dm_info['title']}")
                    
            except Exception as e:
                print(f"Card işleme hatası: {e}")
                continue
        
        return dm_list
        
    except Exception as e:
        print(f"DM verileri çekilirken hata ({alan_adi} - Sınıf {sinif_kodu}): {e}")
        return []

@with_database
def get_dm_with_cursor(cursor):
    """
    DM (Ders Materyali) linklerini çeker ve işler.
    HTML parsing ile card yapısından bilgileri çıkarır.
    URL'leri JSON formatında gruplar ve veritabanına kaydeder.
    PDF dosyalarını indirir (açmaz).
    data/get_dm.json çıktı dosyası üretir.
    Progress mesajları yield eder.
    """
    try:
            
            # Veritabanından alan bilgilerini al
            cursor.execute("SELECT id, alan_adi, meb_alan_id FROM temel_plan_alan ORDER BY alan_adi")
            results = cursor.fetchall()
            db_areas = {alan_adi: {'id': area_id, 'meb_alan_id': meb_alan_id} for area_id, alan_adi, meb_alan_id in results}
            
            # Sadece meb_alan_id olan alanları filtrele
            areas_with_meb_id = {alan_adi: info for alan_adi, info in db_areas.items() if info.get('meb_alan_id')}
            
            if not areas_with_meb_id:
                # Eğer DB'de meb_alan_id'li alan yoksa, MEB'den çek ve alanları oluştur
                yield {'type': 'warning', 'message': 'Veritabanında meb_alan_id bulunan alan yok. MEB\'den alan ID\'leri çekiliyor...'}
                
                # MEB'den alan ID'lerini çek
                meb_alan_ids = get_meb_alan_ids_cached()
                
                if not meb_alan_ids:
                    yield {'type': 'error', 'message': 'MEB\'den alan ID\'leri çekilemedi. DM işlemi iptal ediliyor.'}
                    return
                
                # Alanları oluştur
                created_count = 0
                for alan_adi, meb_alan_id in meb_alan_ids.items():
                    try:
                        get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id)
                        created_count += 1
                    except Exception as e:
                        yield {'type': 'warning', 'message': f'Alan oluşturma hatası ({alan_adi}): {e}'}
                
                yield {'type': 'success', 'message': f'✅ {created_count} alan otomatik oluşturuldu.'}
                
                # Yeni oluşturulan alanları tekrar çek
                cursor.execute("SELECT id, alan_adi, meb_alan_id FROM temel_plan_alan ORDER BY alan_adi")
                results = cursor.fetchall()
                db_areas = {alan_adi: {'id': area_id, 'meb_alan_id': meb_alan_id} for area_id, alan_adi, meb_alan_id in results}
                areas_with_meb_id = {alan_adi: info for alan_adi, info in db_areas.items() if info.get('meb_alan_id')}
                
                if not areas_with_meb_id:
                    yield {'type': 'error', 'message': 'Alan oluşturma işlemi başarısız. DM işlemi iptal ediliyor.'}
                    return
            
            yield {'type': 'status', 'message': f'{len(areas_with_meb_id)} alan için DM verileri çekiliyor...'}
            
            # Tüm sınıflar için DM verilerini çek
            siniflar = ["9", "10", "11", "12"]
            alan_dm_urls = {}
            total_dm_count = 0
            
            # Tüm alan+sınıf kombinasyonları için task listesi oluştur
            tasks = []
            for alan_adi, alan_info in areas_with_meb_id.items():
                meb_alan_id = alan_info['meb_alan_id']
                for sinif in siniflar:
                    tasks.append((alan_adi, sinif, meb_alan_id))
            
            yield {'type': 'status', 'message': f'{len(tasks)} alan+sınıf kombinasyonu için paralel DM çekimi başlatılıyor...'}
            
            # ThreadPoolExecutor ile paralel veri çekme
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Future'ları submit et
                future_to_task = {
                    executor.submit(get_dm_data_for_area, sinif, meb_alan_id, alan_adi): (alan_adi, sinif, meb_alan_id)
                    for alan_adi, sinif, meb_alan_id in tasks
                }
                
                # Alan bazında sonuçları grupla
                completed_tasks = 0
                
                for future in as_completed(future_to_task):
                    alan_adi, sinif, meb_alan_id = future_to_task[future]
                    completed_tasks += 1
                    
                    try:
                        dm_list = future.result()
                        
                        # Alan için sinif_dm_data structure'ı oluştur
                        if alan_adi not in alan_dm_urls:
                            alan_dm_urls[alan_adi] = {}
                        
                        if dm_list:
                            alan_dm_urls[alan_adi][sinif] = dm_list
                            total_dm_count += len(dm_list)
                            yield {'type': 'success', 'message': f'📋 {alan_adi} ({sinif}. sınıf) -> {len(dm_list)} DM bulundu'}
                        else:
                            yield {'type': 'info', 'message': f'📋 {alan_adi} ({sinif}. sınıf) -> DM bulunamadı'}
                    
                    except Exception as e:
                        yield {'type': 'error', 'message': f'{alan_adi} ({sinif}. sınıf) DM çekilirken hata: {e}'}
                        continue
                    
                    # Progress update sadece önemli milestone'larda (25, 50, 75, 100%)
                    if completed_tasks in [len(tasks)//4, len(tasks)//2, len(tasks)*3//4, len(tasks)]:
                        progress_pct = (completed_tasks / len(tasks)) * 100
                        yield {'type': 'status', 'message': f'%{progress_pct:.0f} tamamlandı ({completed_tasks}/{len(tasks)})'}
            
            # Boş alan verilerini temizle
            alan_dm_urls = {alan_adi: sinif_data for alan_adi, sinif_data in alan_dm_urls.items() if sinif_data}
            
            yield {'type': 'status', 'message': f'Toplam {total_dm_count} DM linki bulundu.'}
            yield {'type': 'status', 'message': f'{len(alan_dm_urls)} alan için DM verileri gruplandı.'}
            
            # ÖNCE: Tüm URL'leri veritabanına kaydet
            yield {'type': 'status', 'message': 'DM URL\'leri veritabanına kaydediliyor...'}
            
            saved_alan_count = 0
            for alan_adi, sinif_dm_data in alan_dm_urls.items():
                try:
                    # Alan bilgilerini veritabanından al
                    normalized_alan_adi = normalize_to_title_case_tr(alan_adi)
                    area_db_info = db_areas.get(normalized_alan_adi) or db_areas.get(alan_adi)
                    
                    if area_db_info:
                        data_meb_id = area_db_info['meb_alan_id']
                        
                        # MEB ID'yi fallback stratejisi ile al
                        meb_alan_id, source = get_meb_alan_id_with_fallback(normalized_alan_adi, data_meb_id)
                        
                        # DM URL'lerini JSON formatında kaydet
                        dm_urls_json = json.dumps(sinif_dm_data)
                        
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
                        
                        # Commit otomatik olarak decorator tarafından yapılır
                        saved_alan_count += 1
                        sınıf_sayısı = len(sinif_dm_data)
                        
                        # Toplam DM sayısını hesapla
                        toplam_dm_sayisi = sum(len(dm_list) for dm_list in sinif_dm_data.values())
                        
                        # Standardize edilmiş konsol çıktısı - alan bazlı toplam
                        yield {'type': 'progress', 'message': f'{meb_alan_id} - {alan_adi} ({saved_alan_count}/{len(alan_dm_urls)}) Toplam {toplam_dm_sayisi} DM indi.', 'progress': saved_alan_count / len(alan_dm_urls)}
                    else:
                        # Alan veritabanında yoksa otomatik oluştur
                        alan_id = get_or_create_alan(cursor, normalized_alan_adi)
                        # Commit otomatik olarak decorator tarafından yapılır
                        yield {'type': 'warning', 'message': f'Yeni alan oluşturuldu: {alan_adi}'}
                        saved_alan_count += 1
                        
                except Exception as e:
                    yield {'type': 'error', 'message': f'DM URL kaydetme hatası ({alan_adi}): {e}'}
                    continue
            
            yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için DM URL\'leri veritabanına kaydedildi.'}
            
            # SONRA: PDF indirme işlemi (isteğe bağlı)
            yield {'type': 'status', 'message': 'PDF dosyaları kontrol ediliyor...'}
            
            processed_pdf_count = 0
            for alan_adi, sinif_dm_data in alan_dm_urls.items():
                try:
                    # Alan bilgilerini al
                    normalized_alan_adi = normalize_to_title_case_tr(alan_adi)
                    area_db_info = db_areas.get(normalized_alan_adi) or db_areas.get(alan_adi)
                    
                    if area_db_info:
                        data_meb_id = area_db_info['meb_alan_id']
                        
                        # MEB ID'yi fallback stratejisi ile al
                        meb_alan_id, source = get_meb_alan_id_with_fallback(normalized_alan_adi, data_meb_id)
                        
                        # Her sınıfın PDF'lerini indir
                        for sinif, dm_list in sinif_dm_data.items():
                            for dm_info in dm_list:
                                try:
                                    # MEB ID bazlı klasör yapısı: data/dm/{meb_alan_id}_{alan_adi}/
                                    # Ortak dosyalar otomatik olarak 00_Ortak_Alan_Dersleri klasörüne taşınır
                                    file_path = download_and_cache_pdf(
                                        dm_info['pdf_url'],
                                        "dm",
                                        alan_adi=normalized_alan_adi,
                                        additional_info=None,  # Dosya adını değiştirme
                                        meb_alan_id=meb_alan_id
                                    )
                                    if file_path:
                                        processed_pdf_count += 1
                                        yield {'type': 'success', 'message': f'📄 {alan_adi} -> {os.path.basename(file_path)} ({dm_info["title"]})'}
                                    else:
                                        yield {'type': 'warning', 'message': f'❌ PDF indirme başarısız: {alan_adi} - {dm_info["title"]}'}
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

def get_dm():
    """
    DM (Ders Materyali) linklerini çeker ve işler.
    CLAUDE.md prensiplerini uygular: @with_database decorator kullanır.
    """
    for message in get_dm_with_cursor():
        yield message

# Bu dosya doğrudan çalıştırıldığında test amaçlı kullanılabilir.
if __name__ == '__main__':
    print("DM PDF İndirme ve DB Ekleme Testi Başlatılıyor...")
    for message in get_dm():
        print(f"[{message.get('type', 'log').upper()}] {message.get('message', '')}")