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
from .utils_normalize import normalize_to_title_case_tr
from .utils_database import find_or_create_database, get_or_create_alan, with_database, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached
from .utils_file_management import download_and_cache_pdf
import re
import json


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

def extract_update_year(html_content):
    """
    HTML içeriğinden güncelleme yılını çıkarır.
    Örnek: "12.12.2024 00:00:00" → "2024"
    """
    if not html_content:
        return None
    
    # Tarih formatları için regex pattern'leri
    patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY formatı
        r'(\d{4})-(\d{2})-(\d{2})',   # YYYY-MM-DD formatı
        r'(\d{4})',                   # 4 haneli yıl
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, str(html_content))
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

def get_alan_cop_links(sinif):
    """
    Belirli bir sınıf için tüm alanların ÇÖP linklerini çeker.
    
    Args:
        sinif (str): Sınıf kodu (9, 10, 11, 12)
    
    Returns:
        dict: {alan_adi: {'url': cop_url, 'update_year': year}}
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    alan_links = {}
    
    try:
        # MEB sitesinden ÇÖP linklerini çek
        url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
        params = {"sinif_kodu": sinif, "kurum_id": "1"}
        
        response = requests.get(url, params=params, headers=headers, timeout=45)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ÇÖP linklerini içeren tablo/yapıyı bul
        # PDF linklerini filtrele
        cop_links = soup.find_all('a', href=True)
        
        for link in cop_links:
            href = link.get('href', '').strip()
            
            # PDF linklerini filtrele (upload/cop9/, upload/cop10/, vb.)
            if href.endswith('.pdf') and f'cop{sinif}' in href:
                # Link metni veya parent elementten alan adını çıkar
                link_text = link.get_text(strip=True)
                
                # Link text'i varsa alan adını çıkar
                if link_text:
                    # "AdaletMTAL9.SınıfÇerçeve Öğretim Programı2024-41" -> "Adalet"
                    # "Aile ve Tüketici HizmetleriMTAL9.SınıfÇerçeve Öğretim Programı2024-41" -> "Aile ve Tüketici Hizmetleri"
                    alan_adi = link_text
                    
                    # MTAL kelimesinden önceki kısmı al
                    if 'MTAL' in alan_adi:
                        alan_adi = alan_adi.split('MTAL')[0].strip()
                    
                    # Diğer temizlik işlemleri
                    alan_adi = alan_adi.replace('Çerçeve Öğretim Programı', '').strip()
                    alan_adi = re.sub(r'\d{4}-\d+', '', alan_adi).strip()  # 2024-41 gibi ifadeleri temizle
                    
                    # Eğer alan adı yoksa dosya adından çıkar
                    if not alan_adi:
                        # upload/cop9/adalet_9.pdf -> adalet
                        filename = href.split('/')[-1].replace('.pdf', '')
                        alan_adi = filename.replace(f'_{sinif}', '').replace('_', ' ').title()
                    
                    if alan_adi:
                        # PDF URL'sini tam URL'ye çevir
                        if href.startswith('http'):
                            pdf_url = href
                        else:
                            pdf_url = f"https://meslek.meb.gov.tr/{href}"
                        
                        # Güncelleme yılını HTML içeriğinden çıkar
                        update_year = extract_update_year(response.text)
                        
                        alan_links[alan_adi] = {
                            'url': pdf_url,
                            'update_year': update_year
                        }
                        
                        print(f"  {sinif}. sınıf ÇÖP: {alan_adi}")
        
        print(f"📋 {sinif}. sınıf için {len(alan_links)} ÇÖP linki bulundu")
        return alan_links
        
    except Exception as e:
        print(f"❌ {sinif}. sınıf ÇÖP linkleri çekilirken hata: {e}")
        return {}

def get_cop_links():
    """
    Tüm sınıflar için ÇÖP linklerini paralel olarak çeker.
    Alan ID'lerini dropdown'dan eşleştirir.
    """
    all_links = []
    siniflar = ["9", "10", "11", "12"]
    
    # Önce MEB alan ID'lerini çek (cache'den)
    print("📋 MEB Alan ID'leri çek...")
    meb_alan_ids = get_meb_alan_ids_cached()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_sinif = {executor.submit(get_alan_cop_links, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            sinif = future_to_sinif[future]
            try:
                data = future.result()
                for alan_adi, link_data in data.items():
                    if isinstance(link_data, dict):
                        # MEB alan ID'sini dropdown'dan eşleştir
                        # Protokol alanlar için özel eşleştirme
                        meb_alan_id = meb_alan_ids.get(alan_adi)
                        
                        # Eğer bulunamadıysa ve protokol alan ise temel alan adı ile ara
                        if not meb_alan_id and (" - Protokol" in alan_adi or " - protokol" in alan_adi):
                            import re
                            base_alan_adi = re.sub(r'\s*-\s*[Pp]rotokol\s*$', '', alan_adi).strip()
                            meb_alan_id = meb_alan_ids.get(base_alan_adi)
                            if meb_alan_id:
                                print(f"🔗 Protokol alan MEB ID eşleştirildi: {alan_adi} -> {base_alan_adi} -> {meb_alan_id}")
                        
                        all_links.append({
                            'alan_adi': alan_adi, 
                            'link': link_data['url'], 
                            'sinif': sinif,
                            'meb_alan_id': meb_alan_id,
                            'update_year': link_data.get('update_year')
                        })
                    else:
                        # Backward compatibility için string link desteği
                        meb_alan_id = meb_alan_ids.get(alan_adi)
                        
                        # Protokol alanlar için özel eşleştirme
                        if not meb_alan_id and (" - Protokol" in alan_adi or " - protokol" in alan_adi):
                            import re
                            base_alan_adi = re.sub(r'\s*-\s*[Pp]rotokol\s*$', '', alan_adi).strip()
                            meb_alan_id = meb_alan_ids.get(base_alan_adi)
                            if meb_alan_id:
                                print(f"🔗 Protokol alan MEB ID eşleştirildi: {alan_adi} -> {base_alan_adi} -> {meb_alan_id}")
                        
                        all_links.append({
                            'alan_adi': alan_adi, 
                            'link': link_data, 
                            'sinif': sinif,
                            'meb_alan_id': meb_alan_id,
                            'update_year': None
                        })
            except Exception as exc:
                print(f'❌ {sinif}. sınıf ÇÖP linkleri çekilirken hata oluştu: {exc}')

    if not all_links:
        raise Exception("MEB sitesinden hiçbir ÇÖP linki alınamadı. Siteye erişim veya yapısal bir değişiklik olabilir.")
        
    return all_links

def get_cop_with_cursor():
    """
    ÇÖP (Çerçeve Öğretim Programı) linklerini çeker ve işler.
    HTML parsing ile yeni alanları kontrol eder.
    URL'leri JSON formatında gruplar ve veritabanına kaydeder.
    PDF dosyalarını indirir (açmaz).
    data/get_cop.json çıktı dosyası üretir.
    Progress mesajları yield eder.
    """
    try:
            
            # Her seferinde HTML parsing yaparak yeni alanları kontrol et
            yield {'type': 'status', 'message': 'MEB sitesinden güncel ÇÖP linkleri çekiliyor...'}
            
            try:
                all_cops = get_cop_links()
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
                update_year = cop_info.get('update_year')
                
                if not alan_adi or not cop_url or not sinif:
                    continue
                    
                if alan_adi not in alan_cop_urls:
                    alan_cop_urls[alan_adi] = {
                        'meb_alan_id': meb_alan_id,
                        'urls': {}
                    }
                
                # Sınıf bazında URL'leri ve güncelleme yılını kaydet
                alan_cop_urls[alan_adi]['urls'][str(sinif)] = {
                    'url': cop_url,
                    'update_year': update_year
                }
            
            yield {'type': 'status', 'message': f'{len(alan_cop_urls)} alan için URL\'ler gruplandı.'}
            
            # ÖNCE: Tüm URL'leri veritabanına kaydet (PDF indirme durumundan bağımsız)
            yield {'type': 'status', 'message': 'URL\'ler veritabanına kaydediliyor...'}
            
            import json
            saved_alan_count = 0
            for alan_adi, alan_info in alan_cop_urls.items():
                try:
                    data_meb_id = alan_info['meb_alan_id']
                    cop_urls_json = alan_info['urls']
                    
                    # MEB ID'yi fallback stratejisi ile al
                    meb_alan_id, source = get_meb_alan_id_with_fallback(alan_adi, data_meb_id)
                    
                    # URL'leri JSON formatında kaydet
                    cop_urls_json_string = json.dumps(cop_urls_json)
                    with_database(lambda c: get_or_create_alan(c, alan_adi, meb_alan_id=meb_alan_id, cop_url=cop_urls_json_string))()
                    # Commit handled by @with_database decorator
                    
                    saved_alan_count += 1
                    yield {'type': 'progress', 'message': f'URL kaydedildi: {alan_adi} ({len(cop_urls_json)} sınıf)', 'progress': saved_alan_count / len(alan_cop_urls)}
                    
                except Exception as e:
                    yield {'type': 'error', 'message': f'URL kaydetme hatası ({alan_adi}): {e}'}
                    continue
            
            yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için URL\'ler veritabanına kaydedildi.'}
            
            # Merkezi istatistik fonksiyonunu kullan (CLAUDE.md kuralları)
            try:
                from .utils_database import get_database_statistics, format_database_statistics_message
                stats = get_database_statistics()
                stats_message = format_database_statistics_message(stats)
                yield {'type': 'info', 'message': stats_message}
            except Exception as e:
                yield {'type': 'warning', 'message': f'İstatistik alınamadı: {e}'}
            
            # SONRA: PDF indirme işlemi (isteğe bağlı)
            yield {'type': 'status', 'message': 'PDF dosyaları kontrol ediliyor...'}
            
            processed_count = 0
            for alan_adi, alan_info in alan_cop_urls.items():
                try:
                    data_meb_id = alan_info['meb_alan_id']
                    cop_urls_json = alan_info['urls']
                    
                    # MEB ID'yi fallback stratejisi ile al
                    meb_alan_id, source = get_meb_alan_id_with_fallback(alan_adi, data_meb_id)
                    
                    # PDF'leri MEB ID bazlı klasör yapısında indir/kontrol et
                    for sinif_key, sinif_data in cop_urls_json.items():
                        try:
                            # Sınıf verisinden URL'i al
                            if isinstance(sinif_data, dict):
                                cop_url = sinif_data['url']
                            else:
                                cop_url = sinif_data  # Backward compatibility
                            
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

@with_database
def get_cop(cursor):
    """
    ÇÖP (Çerçeve Öğretim Programı) linklerini çeker ve işler.
    CLAUDE.md prensiplerini uygular: @with_database decorator kullanır.
    """
    for message in get_cop_with_cursor():
        yield message

# Bu dosya doğrudan çalıştırıldığında test amaçlı kullanılabilir.
if __name__ == '__main__':
    print("ÇÖP PDF İndirme ve DB Ekleme Testi Başlatılıyor...")
    for message in get_cop():
        print(f"[{message.get('type', 'log').upper()}] {message.get('message', '')}")