"""
modules/getir_cop.py - ÇÖP (Çerçeve Öğretim Programı) İndirme Modülü

Bu modül, MEB sitesinden Çerçeve Öğretim Programı (ÇÖP) PDF'lerinin
linklerini çeker, dosyaları `utils.py` kullanarak indirir ve bu süreçte
veritabanında eksik olan alanları ekler.
"""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from .utils import normalize_to_title_case_tr, find_or_create_database, get_or_create_alan, download_and_cache_pdf, with_database
import re


def update_meb_alan_ids():
    """
    MEB'den alan ID'lerini çeker ve veritabanını günceller.
    cercevelistele.aspx sayfasındaki select dropdown'dan alan ID'lerini çıkarır.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    alan_id_map = {}  # {alan_adi: meb_alan_id}
    
    try:
        # cercevelistele.aspx sayfasından alan dropdown'unu çek
        url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
        params = {"sinif_kodu": "9", "kurum_id": "1"}
        
        response = requests.get(url, params=params, headers=headers, timeout=45)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Select dropdown'daki option'ları bul
        # Örnek: <option value="01">Adalet</option>
        select = soup.find('select', {'name': re.compile(r'.*drpalansec.*')})
        if select:
            options = select.find_all('option')
            for option in options:
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                # Boş option'ları ve "Alanlar" başlığını atla
                if value and text and value != '' and text != 'Alanlar' and value != '00':
                    alan_id_map[text] = value
                    print(f"📋 {text} -> MEB ID: {value}")
        
        return alan_id_map
                                
    except Exception as e:
        print(f"❌ MEB Alan ID güncelleme hatası: {e}")
        return {}

def get_alan_cop_links_from_specific_page(sinif_kodu="9", alan_id="08"):
    """
    Belirli bir alan ID'si için ÇÖP PDF linkini çeker.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        url = "https://meslek.meb.gov.tr/cercevegoster.aspx"
        params = {"kurum_id": "1", "sinif_kodu": sinif_kodu, "alan_id": alan_id}
        
        response = requests.get(url, params=params, headers=headers, timeout=45)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # PDF linkini bul
        pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf') and f'cop{sinif_kodu}' in x)
        
        if pdf_links:
            href = pdf_links[0].get('href', '')
            if href:
                full_url = f"https://meslek.meb.gov.tr/{href}"
                return full_url
        
        return None
        
    except Exception as e:
        print(f"❌ Alan ID {alan_id} için ÇÖP linki çekilirken hata: {e}")
        return None

def get_alan_cop_links(sinif_kodu="9"):
    """
    Tüm alanlar için ÇÖP PDF linklerini çeker.
    Önce dropdown'dan alan ID'lerini alır, sonra her alan için PDF linkini çeker.
    """
    alan_cop_map = {}
    
    # Önce MEB alan ID'lerini çek
    meb_alan_ids = update_meb_alan_ids()
    
    print(f"🔍 {len(meb_alan_ids)} alan için ÇÖP linkleri çekiliyor...")
    
    for alan_adi, meb_alan_id in meb_alan_ids.items():
        # Her alan için PDF linkini çek
        pdf_url = get_alan_cop_links_from_specific_page(sinif_kodu, meb_alan_id)
        
        if pdf_url:
            alan_cop_map[alan_adi] = {
                'url': pdf_url,
                'meb_alan_id': meb_alan_id
            }
            print(f"📋 {alan_adi} (ID: {meb_alan_id}) -> {pdf_url}")
        else:
            print(f"❌ {alan_adi} (ID: {meb_alan_id}) için PDF bulunamadı")
    
    print(f"✅ {sinif_kodu}. sınıf için {len(alan_cop_map)} alan bulundu")
    return alan_cop_map

def getir_cop_links():
    """
    Tüm sınıflar için ÇÖP linklerini paralel olarak çeker.
    Alan ID'lerini dropdown'dan eşleştirir.
    """
    all_links = []
    siniflar = ["9", "10", "11", "12"]
    
    # Önce MEB alan ID'lerini çek
    print("📋 MEB Alan ID'leri çek...")
    meb_alan_ids = update_meb_alan_ids()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_sinif = {executor.submit(get_alan_cop_links, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            sinif = future_to_sinif[future]
            try:
                data = future.result()
                for alan_adi, link_data in data.items():
                    if isinstance(link_data, dict):
                        # MEB alan ID'sini dropdown'dan eşleştir
                        meb_alan_id = meb_alan_ids.get(alan_adi)
                        
                        all_links.append({
                            'alan_adi': alan_adi, 
                            'link': link_data['url'], 
                            'sinif': sinif,
                            'meb_alan_id': meb_alan_id
                        })
                    else:
                        # Backward compatibility için string link desteği
                        meb_alan_id = meb_alan_ids.get(alan_adi)
                        all_links.append({
                            'alan_adi': alan_adi, 
                            'link': link_data, 
                            'sinif': sinif,
                            'meb_alan_id': meb_alan_id
                        })
            except Exception as exc:
                print(f'❌ {sinif}. sınıf ÇÖP linkleri çekilirken hata oluştu: {exc}')

    if not all_links:
        raise Exception("MEB sitesinden hiçbir ÇÖP linki alınamadı. Siteye erişim veya yapısal bir değişiklik olabilir.")
        
    return all_links

def get_cop():
    """
    ÇÖP (Çerçeve Öğretim Programı) linklerini çeker ve işler.
    HTML parsing ile yeni alanları kontrol eder.
    URL'leri JSON formatında gruplar ve veritabanına kaydeder.
    PDF dosyalarını indirir (açmaz).
    data/get_cop.json çıktı dosyası üretir.
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
            
            # Her seferinde HTML parsing yaparak yeni alanları kontrol et
            yield {'type': 'status', 'message': 'MEB sitesinden güncel ÇÖP linkleri çekiliyor...'}
            
            try:
                all_cops = getir_cop_links()
                yield {'type': 'status', 'message': f'{len(all_cops)} adet ÇÖP linki bulundu.'}
            except Exception as e:
                yield {'type': 'error', 'message': f'ÇÖP linkleri çekilirken hata: {str(e)}'}
                return
            
            total_cops = len(all_cops)
            yield {'type': 'status', 'message': f'{total_cops} adet ÇÖP linki işlenecek.'}
            
            # Alan bazında URL'leri grupla
            alan_cop_urls = {}
            for cop_info in all_cops:
                alan_adi = cop_info.get('alan_adi')
                cop_url = cop_info.get('link')
                sinif = cop_info.get('sinif')
                meb_alan_id = cop_info.get('meb_alan_id')
                
                if not alan_adi or not cop_url or not sinif:
                    continue
                    
                if alan_adi not in alan_cop_urls:
                    alan_cop_urls[alan_adi] = {
                        'meb_alan_id': meb_alan_id,
                        'urls': {}
                    }
                
                # Sınıf bazında URL'leri kaydet
                alan_cop_urls[alan_adi]['urls'][f'sinif_{sinif}'] = cop_url
            
            yield {'type': 'status', 'message': f'{len(alan_cop_urls)} alan için URL\'ler gruplandı.'}
            
            # ÖNCE: Tüm URL'leri veritabanına kaydet (PDF indirme durumundan bağımsız)
            yield {'type': 'status', 'message': 'URL\'ler veritabanına kaydediliyor...'}
            
            import json
            saved_alan_count = 0
            for alan_adi, alan_info in alan_cop_urls.items():
                try:
                    meb_alan_id = alan_info['meb_alan_id']
                    cop_urls_json = alan_info['urls']
                    
                    # URL'leri JSON formatında kaydet
                    cop_urls_json_string = json.dumps(cop_urls_json)
                    get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id, cop_url=cop_urls_json_string)
                    conn.commit()  # Commit after each update
                    
                    saved_alan_count += 1
                    yield {'type': 'progress', 'message': f'URL kaydedildi: {alan_adi} ({len(cop_urls_json)} sınıf)', 'progress': saved_alan_count / len(alan_cop_urls)}
                    
                except Exception as e:
                    yield {'type': 'error', 'message': f'URL kaydetme hatası ({alan_adi}): {e}'}
                    continue
            
            yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için URL\'ler veritabanına kaydedildi.'}
            
            # SONRA: PDF indirme işlemi (isteğe bağlı)
            yield {'type': 'status', 'message': 'PDF dosyaları kontrol ediliyor...'}
            
            processed_count = 0
            for alan_adi, alan_info in alan_cop_urls.items():
                try:
                    meb_alan_id = alan_info['meb_alan_id']
                    cop_urls_json = alan_info['urls']
                    
                    # PDF'leri MEB ID bazlı klasör yapısında indir/kontrol et
                    for sinif_key, cop_url in cop_urls_json.items():
                        try:
                            # MEB ID bazlı klasör yapısı: data/cop/{meb_alan_id}_{alan_adi}/
                            file_path = download_and_cache_pdf(
                                cop_url, 
                                "cop", 
                                alan_adi=alan_adi, 
                                additional_info=None,  # Dosya adını değiştirme
                                meb_alan_id=meb_alan_id
                            )
                            if file_path:
                                yield {'type': 'success', 'message': f'PDF hazır: {os.path.basename(file_path)}'}
                            else:
                                yield {'type': 'warning', 'message': f'PDF indirme başarısız: {alan_adi} {sinif_key}'}
                        except Exception as e:
                            yield {'type': 'error', 'message': f'PDF kontrol hatası ({alan_adi} {sinif_key}): {e}'}
                    
                    processed_count += 1
                    
                except Exception as e:
                    yield {'type': 'error', 'message': f'PDF işleme hatası ({alan_adi}): {e}'}
                    continue

            # JSON çıktı dosyası oluştur
            output_filename = "data/get_cop.json"
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(alan_cop_urls, f, ensure_ascii=False, indent=2)
                yield {'type': 'success', 'message': f'ÇÖP verileri kaydedildi: {output_filename}'}
            except Exception as e:
                yield {'type': 'error', 'message': f'JSON dosyası kaydedilemedi: {e}'}

            yield {'type': 'done', 'message': f'Tüm ÇÖP dosyaları işlendi. {len(alan_cop_urls)} alan için URL\'ler veritabanına kaydedildi.'}

    except Exception as e:
        yield {'type': 'error', 'message': f'ÇÖP indirme iş akışında genel hata: {str(e)}'}


# Bu dosya doğrudan çalıştırıldığında test amaçlı kullanılabilir.
if __name__ == '__main__':
    print("ÇÖP PDF İndirme ve DB Ekleme Testi Başlatılıyor...")
    for message in get_cop():
        print(f"[{message.get('type', 'log').upper()}] {message.get('message', '')}")