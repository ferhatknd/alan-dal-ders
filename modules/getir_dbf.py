import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import sqlite3
try:
    from .oku_dbf import extract_ders_adi
    from .utils import normalize_to_title_case_tr, sanitize_filename_tr
    from .utils_database import with_database, get_or_create_alan, find_or_create_database, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached
    from .utils_file_management import download_and_cache_pdf
except ImportError:
    from oku_dbf import extract_ders_adi
    from utils import normalize_to_title_case_tr, sanitize_filename_tr
    from utils_database import with_database, get_or_create_alan, find_or_create_database, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached
    from utils_file_management import download_and_cache_pdf

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbfgoster.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

DBF_ROOT_DIR = "data/dbf"

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

@with_database
def get_areas_from_db(cursor):
    """
    Veritabanından alan ID ve adlarını çeker.
    Returns: dict {alan_adi: alan_id}
    """
    try:
        cursor.execute("SELECT id, alan_adi FROM temel_plan_alan ORDER BY alan_adi")
        results = cursor.fetchall()
        return {alan_adi: alan_id for alan_id, alan_adi in results}
    except Exception as e:
        print(f"Veritabanı okuma hatası: {e}")
        return {}


def find_matching_area_id(html_area_name, db_areas):
    """
    HTML'den gelen alan adını veritabanındaki alanlarla eşleştirir.
    Returns: (alan_id, matched_name) veya (None, None)
    """
    normalized_html_name = normalize_to_title_case_tr(html_area_name)
    
    # Tam eşleşme kontrolü
    if normalized_html_name in db_areas:
        return db_areas[normalized_html_name], normalized_html_name
    
    # Kısmi eşleşme kontrolü
    for db_name, area_id in db_areas.items():
        if normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower():
            print(f"Kısmi eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
            return area_id, db_name
    
    print(f"Eşleşme bulunamadı: '{html_area_name}' (normalize: '{normalized_html_name}')")
    return None, None

def get_dbf_data_for_alan_and_sinif(alan_adi, meb_alan_id, sinif_kodu):
    """
    Belirli bir alan ve sınıf için DBF verilerini çeker.
    COP'daki yöntemle aynı prensip: spesifik alan+sınıf sayfasına git.
    """
    params = {"kurum_id": "1", "sinif_kodu": sinif_kodu, "alan_id": meb_alan_id}
    
    try:
        response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # DBF linkini bul (RAR/ZIP dosyası)
        dbf_links = soup.find_all('a', href=lambda x: x and (x.endswith('.rar') or x.endswith('.zip')))
        
        if dbf_links:
            for link in dbf_links:
                href = link.get('href', '')
                if href:
                    # Tam URL'yi oluştur
                    if href.startswith('http'):
                        dbf_url = href
                    else:
                        dbf_url = requests.compat.urljoin(response.url, href)
                    
                    # Tarih bilgisini bul
                    tarih = ""
                    parent_div = link.find_parent('div')
                    if parent_div:
                        for li in parent_div.find_all('li'):
                            if 'calendar' in str(li) or re.search(r'\d{2}\.\d{2}\.\d{4}', li.get_text()):
                                tarih = li.get_text(strip=True)
                                break
                    
                    # Güncelleme yılını çıkar
                    update_year = extract_update_year(tarih)
                    
                    return {
                        "link": dbf_url,
                        "guncelleme_tarihi": tarih,
                        "update_year": update_year,
                        "meb_alan_id": meb_alan_id
                    }
        
        return None
        
    except requests.RequestException as e:
        print(f"DBF Hata: {alan_adi} ({sinif_kodu}. sınıf) sayfası çekilemedi: {e}")
        return None

def get_dbf_data(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için DBF (Ders Bilgi Formu) verilerini eşzamanlı olarak çeker.
    COP'daki yöntemle aynı prensip: önce MEB alan ID'lerini al, sonra her alan+sınıf için spesifik sayfa.
    """
    # Önce MEB alan ID'lerini çek (cache'den)
    print("📋 MEB Alan ID'leri çekiliyor...")
    meb_alan_ids = get_meb_alan_ids_cached()
    
    if not meb_alan_ids:
        print("❌ MEB Alan ID'leri çekilemedi!")
        return {}
    
    print(f"🔍 {len(meb_alan_ids)} alan için DBF linkleri çekiliyor...")
    
    # Tüm alan+sınıf kombinasyonları için task listesi oluştur
    tasks = []
    for alan_adi, meb_alan_id in meb_alan_ids.items():
        for sinif in siniflar:
            tasks.append((alan_adi, meb_alan_id, sinif))
    
    # Sonuçları organize et
    all_dbf_data = {}
    
    # Paralel işleme
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        # Future'ları submit et
        future_to_task = {
            executor.submit(get_dbf_data_for_alan_and_sinif, alan_adi, meb_alan_id, sinif): (alan_adi, meb_alan_id, sinif)
            for alan_adi, meb_alan_id, sinif in tasks
        }
        
        # Sonuçları topla
        for future in as_completed(future_to_task):
            alan_adi, meb_alan_id, sinif = future_to_task[future]
            
            try:
                dbf_data = future.result()
                
                if dbf_data:
                    # Sınıf bazında organize et
                    if sinif not in all_dbf_data:
                        all_dbf_data[sinif] = {}
                    
                    all_dbf_data[sinif][alan_adi] = dbf_data
                    print(f"📋 {alan_adi} ({sinif}. sınıf) -> DBF bulundu (ID: {meb_alan_id})")
                else:
                    print(f"❌ {alan_adi} ({sinif}. sınıf) -> DBF bulunamadı")
                    
            except Exception as e:
                print(f"❌ {alan_adi} ({sinif}. sınıf) DBF işleme hatası: {e}")
    
    return all_dbf_data

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

def is_protocol_area(alan_adi):
    """
    Alan adının protokol alan olup olmadığını kontrol eder.
    
    Args:
        alan_adi: Kontrol edilecek alan adı
        
    Returns:
        bool: Protokol alan ise True, değilse False
    """
    if not alan_adi:
        return False
    return "protokol" in alan_adi.lower()

def get_base_area_name(protocol_name):
    """
    Protokol alan adından temel alan adını çıkarır.
    
    Args:
        protocol_name: Protokol alan adı
        
    Returns:
        str: Temel alan adı
    """
    if not protocol_name:
        return ""
    
    # Farklı protokol formatlarını kaldır
    # Örnek: "Muhasebe ve Finansman - Protokol" -> "Muhasebe ve Finansman"
    # Örnek: "Denizcilik - protokol" -> "Denizcilik"
    # Örnek: "Gazetecilik Protokol" -> "Gazetecilik"
    
    base_name = protocol_name
    
    # " - Protokol" formatını kaldır (büyük/küçük harf farketmez)
    import re
    base_name = re.sub(r'\s*-\s*protokol\s*$', '', base_name, flags=re.IGNORECASE)
    
    # Sadece "protokol" kelimesini kaldır (space'li veya space'siz)
    base_name = re.sub(r'\s*protokol\s*$', '', base_name, flags=re.IGNORECASE)
    base_name = re.sub(r'\s*protokol\s+', ' ', base_name, flags=re.IGNORECASE)
    
    # Boşlukları temizle
    base_name = base_name.strip()
    
    # Normalize et
    return normalize_to_title_case_tr(base_name)

def link_courses_to_protocol_area(cursor, base_area_id, protocol_area_id):
    """
    Temel alandan protokol alana dersleri kopyalar.
    
    Args:
        cursor: Database cursor
        base_area_id: Temel alan ID'si
        protocol_area_id: Protokol alan ID'si
    """
    try:
        # Temel alanın dallarını al
        cursor.execute("""
            SELECT id FROM temel_plan_dal 
            WHERE alan_id = ?
        """, (base_area_id,))
        base_dallar = cursor.fetchall()
        
        if not base_dallar:
            print(f"⚠️ Temel alan {base_area_id} için dal bulunamadı")
            return
        
        # Protokol alan için dalları oluştur
        protocol_dallar = []
        for dal_row in base_dallar:
            base_dal_id = dal_row['id']
            
            # Dal adını al
            cursor.execute("SELECT dal_adi FROM temel_plan_dal WHERE id = ?", (base_dal_id,))
            dal_result = cursor.fetchone()
            if dal_result:
                dal_adi = dal_result['dal_adi']
                
                # Protokol alan için dal oluştur (duplicate check)
                cursor.execute("SELECT id FROM temel_plan_dal WHERE dal_adi = ? AND alan_id = ?", (dal_adi, protocol_area_id))
                existing_dal = cursor.fetchone()
                
                if existing_dal:
                    protocol_dal_id = existing_dal['id']
                else:
                    cursor.execute("""
                        INSERT INTO temel_plan_dal (dal_adi, alan_id, created_at, updated_at)
                        VALUES (?, ?, datetime('now'), datetime('now'))
                    """, (dal_adi, protocol_area_id))
                    protocol_dal_id = cursor.lastrowid
                protocol_dallar.append((base_dal_id, protocol_dal_id))
        
        # Ders-dal ilişkilerini kopyala
        linked_courses = 0
        for base_dal_id, protocol_dal_id in protocol_dallar:
            cursor.execute("""
                SELECT DISTINCT ders_id FROM temel_plan_ders_dal 
                WHERE dal_id = ?
            """, (base_dal_id,))
            
            ders_ids = cursor.fetchall()
            
            for ders_row in ders_ids:
                ders_id = ders_row['ders_id']
                
                # Duplicate kontrolü
                cursor.execute("""
                    SELECT COUNT(*) as count FROM temel_plan_ders_dal 
                    WHERE ders_id = ? AND dal_id = ?
                """, (ders_id, protocol_dal_id))
                
                if cursor.fetchone()['count'] == 0:
                    cursor.execute("""
                        INSERT INTO temel_plan_ders_dal (ders_id, dal_id, created_at)
                        VALUES (?, ?, datetime('now'))
                    """, (ders_id, protocol_dal_id))
                    linked_courses += 1
        
        print(f"✅ Protokol alan {protocol_area_id} için {linked_courses} ders bağlantısı oluşturuldu")
        
    except Exception as e:
        print(f"❌ Protokol alan ders bağlantısı hatası: {e}")

def handle_protocol_area(cursor, alan_adi, alan_id):
    """
    Protokol alan işlemlerini yönetir.
    
    Args:
        cursor: Database cursor
        alan_adi: Alan adı
        alan_id: Oluşturulan alan ID'si
    """
    if not is_protocol_area(alan_adi):
        return
    
    try:
        # Temel alan adını bul
        base_area_name = get_base_area_name(alan_adi)
        
        if not base_area_name:
            print(f"⚠️ Protokol alan '{alan_adi}' için temel alan adı bulunamadı")
            return
        
        # Temel alanı bul
        cursor.execute("""
            SELECT id FROM temel_plan_alan 
            WHERE alan_adi = ?
        """, (base_area_name,))
        
        base_area_result = cursor.fetchone()
        if base_area_result:
            base_area_id = base_area_result['id']
            print(f"🔗 Protokol alan '{alan_adi}' temel alan '{base_area_name}' ile bağlanıyor...")
            
            # Dersleri kopyala
            link_courses_to_protocol_area(cursor, base_area_id, alan_id)
        else:
            print(f"⚠️ Protokol alan '{alan_adi}' için temel alan '{base_area_name}' bulunamadı")
            
    except Exception as e:
        print(f"❌ Protokol alan işleme hatası: {e}")

def get_or_create_area_for_download(cursor, alan_adi, meb_alan_ids=None):
    """
    İndirme işlemi için alan ID'sini alır veya oluşturur.
    
    Args:
        cursor: Database cursor
        alan_adi: Alan adı
        meb_alan_ids: MEB alan ID'leri dict'i (opsiyonel)
    
    Returns:
        tuple: (alan_id, meb_alan_id, matched_name)
    """
    # Önce mevcut alanları kontrol et
    db_areas = get_areas_from_db()
    area_id, matched_name = find_matching_area_id(alan_adi, db_areas)
    
    if area_id:
        # Alan bulundu, MEB ID'sini al
        db_areas_with_meb = get_areas_from_db_with_meb_id()
        meb_alan_id = db_areas_with_meb.get(matched_name, {}).get('meb_alan_id')
        return area_id, meb_alan_id, matched_name
    
    # Alan bulunamadı, oluştur
    print(f"🆕 Yeni alan oluşturuluyor: {alan_adi}")
    
    # MEB Alan ID'sini al
    meb_alan_id = None
    if meb_alan_ids:
        meb_alan_id = meb_alan_ids.get(alan_adi)
    
    # Alan oluştur
    alan_id = get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id)
    
    # Protokol alan ise işle
    if is_protocol_area(alan_adi):
        handle_protocol_area(cursor, alan_adi, alan_id)
    
    return alan_id, meb_alan_id, alan_adi

# Bu fonksiyon kaldırıldı - unrar işlemleri artık yapılmıyor
# Sadece get_dbf() fonksiyonu kullanılacak (indirme + URL kaydetme)

@with_database
def get_dbf(cursor, dbf_data=None):
    """
    DBF (Ders Bilgi Formu) linklerini çeker ve işler.
    HTML parsing ile yeni alanları kontrol eder.
    URL'leri JSON formatında gruplar ve veritabanına kaydeder.
    RAR/ZIP dosyalarını indirir (açmaz).
    data/get_dbf.json çıktı dosyası üretir.
    Progress mesajları yield eder.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    # DBF verilerini çek (eğer geçilmemişse)
    if dbf_data is None:
        yield {'type': 'status', 'message': 'DBF linkleri çekiliyor...'}
        dbf_data = get_dbf_data()
        if not dbf_data:
            yield {'type': 'error', 'message': 'DBF verileri çekilemedi!'}
            return

    # MEB alan ID'lerini al (cache'den)
    meb_alan_ids = get_meb_alan_ids_cached()

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            try:
                # MEB ID'yi çoklu kaynak stratejisi ile al
                data_meb_id = info.get("meb_alan_id")
                meb_alan_id, source = get_meb_alan_id_with_fallback(alan_adi, data_meb_id)
                
                # Alan ID'sini al veya oluştur
                area_id, _, matched_name = get_or_create_area_for_download(cursor, alan_adi, meb_alan_ids)
                
                # Klasör adını yeni strateji ile belirle
                folder_name = get_folder_name_for_download(matched_name or alan_adi, meb_alan_id, area_id)
                alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                
                if meb_alan_id:
                    yield {"type": "status", "message": f"[{alan_adi}] Klasör: {folder_name} (MEB ID: {meb_alan_id}, kaynak: {source})"}
                else:
                    yield {"type": "warning", "message": f"[{alan_adi}] MEB ID bulunamadı, alan adı kullanılıyor: {folder_name}"}
                
            except Exception as e:
                # Hata durumunda eski sistemi kullan
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
                yield {"type": "error", "message": f"[{alan_adi}] Alan işleme hatası: {e}, eski format kullanılıyor"}
            
            if not os.path.exists(alan_dir):
                os.makedirs(alan_dir)
            archive_filename = os.path.basename(link)
            archive_path = os.path.join(alan_dir, archive_filename)

            # Dosya zaten varsa atla
            if os.path.exists(archive_path):
                file_size = os.path.getsize(archive_path)
                yield {"type": "info", "message": f"📁 {alan_adi} -> {archive_filename} zaten mevcut ({file_size // (1024*1024)}MB)"}
                continue

            # İndir - hata durumunda devam et
            yield {"type": "status", "message": f"⬇️ {alan_adi} -> {archive_filename} indiriliyor..."}
            
            try:
                # Önce HEAD request ile dosya varlığını kontrol et
                head_response = requests.head(link, timeout=10)
                if head_response.status_code == 404:
                    yield {"type": "warning", "message": f"⚠️ {alan_adi} -> {archive_filename} dosya bulunamadı (404) - atlanıyor"}
                    continue
                elif head_response.status_code >= 400:
                    yield {"type": "warning", "message": f"⚠️ {alan_adi} -> {archive_filename} erişim hatası ({head_response.status_code}) - atlanıyor"}
                    continue
                
                # Dosya indirme
                with requests.get(link, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    
                    # Content-Length header'dan dosya boyutunu al
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(archive_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                
                # Başarılı indirme
                yield {"type": "success", "message": f"📁 {alan_adi} -> {archive_filename} indirildi ({downloaded_size // (1024*1024)}MB)"}
                
            except requests.exceptions.Timeout:
                yield {"type": "error", "message": f"❌ {alan_adi} -> {archive_filename} indirme timeout (60s) - atlanıyor"}
                # Yarıda kalan dosyayı sil
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                continue
                
            except requests.exceptions.HTTPError as e:
                yield {"type": "error", "message": f"❌ {alan_adi} -> {archive_filename} HTTP hatası: {e} - atlanıyor"}
                # Yarıda kalan dosyayı sil
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                continue
                
            except requests.exceptions.RequestException as e:
                yield {"type": "error", "message": f"❌ {alan_adi} -> {archive_filename} bağlantı hatası: {e} - atlanıyor"}
                # Yarıda kalan dosyayı sil
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                continue
                
            except Exception as e:
                yield {"type": "error", "message": f"❌ {alan_adi} -> {archive_filename} genel hata: {e} - atlanıyor"}
                # Yarıda kalan dosyayı sil
                if os.path.exists(archive_path):
                    os.remove(archive_path)
                continue

            # AÇMA İŞLEMİ GEÇİCİ OLARAK KAPAT
            # msg = f"[{alan_adi}] {archive_filename} açılıyor..."
            # print(msg)
            # yield {"type": "status", "message": msg}
            # try:
            #     extract_archive(archive_path, alan_dir)
            #     msg = f"[{alan_adi}] {archive_filename} başarıyla açıldı."
            #     print(msg)
            #     yield {"type": "status", "message": msg}
            # except Exception as e:
            #     msg = f"[{alan_adi}] {archive_filename} açılamadı: {e}"
            #     print(msg)
            #     yield {"type": "error", "message": msg}

    # DBF URL'lerini JSON formatında veritabanına kaydet
    yield {'type': 'status', 'message': 'DBF URL\'leri veritabanına kaydediliyor...'}
    try:
        # Alan bazında URL'leri grupla
        alan_dbf_urls = {}
        for sinif, alanlar in dbf_data.items():
            for alan_adi, info in alanlar.items():
                if alan_adi not in alan_dbf_urls:
                    alan_dbf_urls[alan_adi] = {}
                alan_dbf_urls[alan_adi][str(sinif)] = info['link']
        
        # Her alan için URL'leri JSON formatında veritabanına kaydet
        import json
        saved_alan_count = 0
        for alan_adi, alan_urls in alan_dbf_urls.items():
            try:
                # MEB alan ID'sini al (eğer varsa)
                meb_alan_id = meb_alan_ids.get(alan_adi) if meb_alan_ids else None
                
                # Alan ID'sini al veya oluştur (ORJİNAL ALAN ADI ile)
                alan_id = with_database(lambda c: get_or_create_alan(c, alan_adi, meb_alan_id=meb_alan_id, dbf_urls=alan_urls))()
                
                # Protokol alan ise işle (ders bağlantıları için)
                if is_protocol_area(alan_adi):
                    handle_protocol_area(cursor, alan_adi, alan_id)
                
                saved_alan_count += 1
                sınıf_sayısı = len(alan_urls)
                yield {'type': 'success', 'message': f'📋 {alan_adi} -> URL kaydedildi ({sınıf_sayısı} sınıf)'}
                
            except Exception as e:
                yield {'type': 'error', 'message': f'URL kaydetme hatası ({alan_adi}): {e}'}
        
        yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için URL\'ler veritabanına kaydedildi.'}
        
        # Merkezi istatistik fonksiyonunu kullan (CLAUDE.md kuralları)
        try:
            from .utils_database import get_database_statistics, format_database_statistics_message
            stats = get_database_statistics()
            stats_message = format_database_statistics_message(stats)
            yield {'type': 'info', 'message': stats_message}
        except Exception as e:
            yield {'type': 'warning', 'message': f'İstatistik alınamadı: {e}'}
        
        # JSON çıktı dosyası oluştur
        output_filename = "data/get_dbf.json"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(alan_dbf_urls, f, ensure_ascii=False, indent=2)
            yield {'type': 'success', 'message': f'DBF verileri kaydedildi: {output_filename}'}
        except Exception as e:
            yield {'type': 'error', 'message': f'JSON dosyası kaydedilemedi: {e}'}
        
    except Exception as e:
        yield {'type': 'error', 'message': f'DBF URL kaydetme hatası: {e}'}
    
    yield {'type': 'done', 'message': f'Tüm DBF dosyaları işlendi. {len(alan_dbf_urls) if "alan_dbf_urls" in locals() else 0} alan için URL\'ler veritabanına kaydedildi.'}

# Bu fonksiyon kaldırıldı - unrar işlemleri artık yapılmıyor
# Sadece get_dbf() fonksiyonu kullanılacak (indirme + URL kaydetme)

# Bu fonksiyon kaldırıldı - unrar işlemleri artık yapılmıyor

# Bu fonksiyon kaldırıldı - unrar işlemleri artık yapılmıyor

# Bu fonksiyon kaldırıldı - unrar işlemleri artık yapılmıyor

def extract_course_name_from_dbf(dbf_file_path):
    """
    DBF dosyasından ders adını çıkarır
    """
    try:
        if os.path.exists(dbf_file_path) and dbf_file_path.lower().endswith(('.pdf', '.docx')):
            ders_adi = extract_ders_adi(dbf_file_path)
            return ders_adi.strip() if ders_adi else None
    except Exception as e:
        print(f"DBF dosyası okuma hatası ({dbf_file_path}): {e}")
    return None

def match_dbf_to_course_by_content(dbf_file_path, course_name):
    """
    DBF dosya içeriğinden çıkarılan ders adı ile veritabanındaki ders adını eşleştirir
    """
    extracted_course_name = extract_course_name_from_dbf(dbf_file_path)
    
    if not extracted_course_name:
        return False, 0
    
    extracted_clean = extracted_course_name.lower().strip()
    course_clean = course_name.lower().strip()
    
    # Tam eşleşme
    if extracted_clean == course_clean:
        return True, 100
    
    # Kısmi eşleşme
    if extracted_clean in course_clean or course_clean in extracted_clean:
        return True, 90
    
    # Kelime bazlı eşleşme
    extracted_words = set(extracted_clean.split())
    course_words = set(course_clean.split())
    common_words = extracted_words.intersection(course_words)
    
    if len(common_words) > 0:
        similarity = (len(common_words) * 2) / (len(extracted_words) + len(course_words)) * 100
        if similarity > 70:
            return True, similarity
    
    return False, 0

def scan_dbf_files_and_extract_courses(alan_adi=None):
    """
    DBF klasörlerini tarar ve her dosyadan ders adını çıkarır
    """
    results = {}
    
    if not os.path.exists(DBF_ROOT_DIR):
        return results
    
    alan_klasorleri = [d for d in os.listdir(DBF_ROOT_DIR) 
                       if os.path.isdir(os.path.join(DBF_ROOT_DIR, d))]
    
    if alan_adi:
        alan_klasorleri = [alan_adi] if alan_adi in alan_klasorleri else []
    
    for alan_klasor in alan_klasorleri:
        alan_dir = os.path.join(DBF_ROOT_DIR, alan_klasor)
        results[alan_klasor] = {}
        
        # Alan klasörü altındaki tüm klasörleri ve dosyaları tara
        for root, dirs, files in os.walk(alan_dir):
            for file in files:
                if file.lower().endswith(('.pdf', '.docx')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, alan_dir)
                    
                    ders_adi = extract_course_name_from_dbf(file_path)
                    if ders_adi:
                        results[alan_klasor][relative_path] = {
                            'ders_adi': ders_adi,
                            'dosya_adi': file,
                            'tam_yol': file_path
                        }
    
    return results

@with_database
def save_dbf_urls_to_database(cursor):
    """
    DBF URL'lerini veritabanına JSON formatında kaydeder.
    Eksik alanları otomatik oluşturur ve protokol alanlarını işler.
    """
    import json
    
    # DBF verilerini çek
    print("📋 DBF linkleri çekiliyor...")
    dbf_data = getir_dbf()
    
    if not dbf_data:
        print("❌ DBF verileri çekilemedi!")
        return {"success": False, "error": "DBF verileri çekilemedi"}
    
    # Alan bazında URL'leri grupla
    alan_dbf_urls = {}
    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            if alan_adi not in alan_dbf_urls:
                alan_dbf_urls[alan_adi] = {}
            alan_dbf_urls[alan_adi][str(sinif)] = info['link']
    
    print(f"🔍 {len(alan_dbf_urls)} alan için URL'ler veritabanına kaydediliyor...")
    
    # MEB alan ID'lerini güncelle (cache'den)
    meb_alan_ids = get_meb_alan_ids_cached()
    
    saved_count = 0
    protocol_areas = []
    
    for alan_adi, dbf_urls in alan_dbf_urls.items():
        try:
            # MEB Alan ID'sini al
            meb_alan_id = meb_alan_ids.get(alan_adi)
            
            # JSON formatında kaydet
            dbf_urls_json = json.dumps(dbf_urls)
            
            # Alan oluştur veya güncelle (otomatik oluşturma)
            alan_id = get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id, dbf_urls=dbf_urls_json)
            
            # Protokol alan ise listeye ekle
            if is_protocol_area(alan_adi):
                protocol_areas.append((alan_adi, alan_id))
                print(f"🔗 Protokol alan tespit edildi: {alan_adi}")
            
            saved_count += 1
            print(f"✅ {alan_adi}: {len(dbf_urls)} sınıf URL'si kaydedildi (MEB ID: {meb_alan_id})")
            
        except Exception as e:
            print(f"❌ {alan_adi} kaydetme hatası: {e}")
            continue
    
    # Protokol alanlarını işle
    if protocol_areas:
        print(f"🔗 {len(protocol_areas)} protokol alan işleniyor...")
        for alan_adi, alan_id in protocol_areas:
            try:
                handle_protocol_area(cursor, alan_adi, alan_id)
            except Exception as e:
                print(f"❌ Protokol alan işleme hatası ({alan_adi}): {e}")
    
    print(f"🎯 Toplam {saved_count} alan için DBF URL'leri veritabanına kaydedildi!")
    return {"success": True, "count": saved_count, "protocol_areas": len(protocol_areas)}

def main():
    """
    DBF işlemleri ana menüsü
    """
    print("Ders Bilgi Formu (DBF) Getirici")
    print("1. Veri Çek (9, 10, 11, 12. sınıflar)")
    print("2. DBF İndir (Sadece İndirme - Açma Yok)")
    print("3. DBF Dosyalarından Ders Adlarını Çıkar")
    print("4. DBF URL'lerini Veritabanına Kaydet")
    
    choice = input("Seçiminizi yapın (1-4): ").strip()
    
    if choice == "1":
        print("DBF verileri çekiliyor...")
        dbf_data = get_dbf_data()
        if dbf_data:
            print("✅ DBF verileri başarıyla çekildi!")
            print(f"Toplam {sum(len(alanlar) for alanlar in dbf_data.values())} alan bulundu.")
        else:
            print("❌ DBF verileri çekilemedi!")
    
    elif choice == "2":
        print("DBF verileri çekiliyor ve indiriliyor...")
        for message in get_dbf():
            msg_type = message.get("type", "info")
            msg_text = message.get("message", "")
            
            if msg_type == "error":
                print(f"❌ {msg_text}")
            elif msg_type == "warning":
                print(f"⚠️ {msg_text}")
            elif msg_type == "success":
                print(f"✅ {msg_text}")
            elif msg_type == "done":
                print(f"🎉 {msg_text}")
                break
            else:
                print(f"ℹ️ {msg_text}")
    
    elif choice == "3":
        print("DBF dosyalarından ders adları çıkarılıyor...")
        results = scan_dbf_files_and_extract_courses()
        
        if not results:
            print("❌ DBF dosyası bulunamadı!")
            return
        
        toplam_dosya = 0
        basarili_dosya = 0
        
        for alan_adi, dosyalar in results.items():
            print(f"\n📁 {alan_adi}:")
            for dosya_yolu, bilgi in dosyalar.items():
                toplam_dosya += 1
                if bilgi['ders_adi']:
                    basarili_dosya += 1
                    print(f"  ✅ {bilgi['dosya_adi']} → {bilgi['ders_adi']}")
                else:
                    print(f"  ❌ {bilgi['dosya_adi']} → Ders adı çıkarılamadı")
        
        print(f"\n📊 Özet: {basarili_dosya}/{toplam_dosya} dosyadan ders adı çıkarıldı (%{basarili_dosya/toplam_dosya*100:.1f})")
    
    elif choice == "4":
        print("DBF URL'leri veritabanına kaydediliyor...")
        result = save_dbf_urls_to_database()
        if result and result.get("success"):
            print(f"✅ İşlem tamamlandı! {result.get('count', 0)} alan kaydedildi.")
        else:
            print("❌ İşlem başarısız!")
    
    else:
        print("Geçersiz seçim!")

if __name__ == "__main__":
    main()
