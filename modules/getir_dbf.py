import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import rarfile
import zipfile
import re
import sqlite3
try:
    from .oku_dbf import extract_ders_adi
    from .utils import normalize_to_title_case_tr, with_database, download_and_cache_pdf, get_or_create_alan, find_or_create_database, sanitize_filename_tr
except ImportError:
    from oku_dbf import extract_ders_adi
    from utils import normalize_to_title_case_tr, with_database, download_and_cache_pdf, get_or_create_alan, find_or_create_database, sanitize_filename_tr

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
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

def getir_dbf(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için DBF (Ders Bilgi Formu) verilerini eşzamanlı olarak çeker.
    """
    def get_dbf_data_for_class(sinif_kodu):
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        class_dbf_data = {}
        try:
            response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            alan_columns = soup.find_all('div', class_='col-lg-3')
            for column in alan_columns:
                ul_tag = column.find('ul', class_='list-group')
                if not ul_tag: continue

                link_tag = ul_tag.find_parent('a', href=True)
                if not link_tag or not (link_tag['href'].endswith('.rar') or link_tag['href'].endswith('.zip')):
                    continue

                dbf_link = requests.compat.urljoin(response.url, link_tag['href'])
                
                alan_adi = ""
                tarih = ""

                b_tag = ul_tag.find('b')
                if b_tag:
                    alan_adi = b_tag.get_text(strip=True)

                for item in ul_tag.find_all('li'):
                    if item.find('i', class_='fa-calendar'):
                        tarih = item.get_text(strip=True)
                        break

                if alan_adi and dbf_link:
                    # Güncelleme yılını çıkar
                    update_year = extract_update_year(tarih)
                    
                    class_dbf_data[alan_adi] = {
                        "link": dbf_link,
                        "guncelleme_tarihi": tarih,
                        "update_year": update_year
                    }
        except requests.RequestException as e:
            print(f"DBF Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
        return sinif_kodu, class_dbf_data

    all_dbf_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_dbf_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_dbf_data[sinif] = data
            except Exception as exc:
                print(f"DBF verisi işlenirken hata: {exc}")
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

@with_database
def download_and_extract_dbf(cursor, dbf_data):
    """
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/{meb_alan_id}_{alan_adi}/ klasörüne açar.
    Eksik alanları otomatik oluşturur.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    # MEB alan ID'lerini al
    try:
        from .getir_cop import update_meb_alan_ids
    except ImportError:
        from getir_cop import update_meb_alan_ids
    
    meb_alan_ids = update_meb_alan_ids()
    
    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            try:
                # Alan ID'sini al veya oluştur
                area_id, meb_alan_id, matched_name = get_or_create_area_for_download(cursor, alan_adi, meb_alan_ids)
                
                if meb_alan_id:
                    # MEB ID bazlı klasör yapısı: {meb_alan_id}_{alan_adi}
                    folder_name = f"{meb_alan_id}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    print(f"[{alan_adi}] Klasör: {folder_name}")
                else:
                    # MEB ID yoksa database ID kullan
                    folder_name = f"{area_id:02d}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    print(f"[{alan_adi}] MEB ID yok, database ID kullanılıyor: {folder_name}")
                
            except Exception as e:
                # Hata durumunda eski sistemi kullan
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
                print(f"[{alan_adi}] Alan işleme hatası: {e}, eski format kullanılıyor")
            
            if not os.path.exists(alan_dir):
                os.makedirs(alan_dir)
            archive_filename = os.path.basename(link)
            archive_path = os.path.join(alan_dir, archive_filename)

            # Dosya zaten varsa atla
            if os.path.exists(archive_path):
                file_size = os.path.getsize(archive_path)
                print(f"[{alan_adi}] {archive_filename} zaten mevcut ({file_size // (1024*1024)}MB) - ATLANIYOR")
                continue

            # İndir
            print(f"[{alan_adi}] {sinif}. sınıf: {archive_filename} indiriliyor...")
            try:
                # Chunk-based download with timeout handling
                with requests.get(link, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(archive_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                
                print(f"[{alan_adi}] {archive_filename} indirildi ({downloaded_size // (1024*1024)}MB).")
            except requests.exceptions.Timeout:
                print(f"[{alan_adi}] {archive_filename} indirme timeout (120s) - dosya çok büyük olabilir")
                continue
            except Exception as e:
                print(f"[{alan_adi}] {archive_filename} indirilemedi: {e}")
                continue

            # Aç
            try:
                print(f"[{alan_adi}] {archive_filename} açılıyor...")
                extract_archive(archive_path, alan_dir)
                print(f"[{alan_adi}] {archive_filename} başarıyla açıldı.")
            except Exception as e:
                print(f"[{alan_adi}] {archive_filename} açılamadı: {e}")

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
        dbf_data = getir_dbf()
        if not dbf_data:
            yield {'type': 'error', 'message': 'DBF verileri çekilemedi!'}
            return

    # MEB alan ID'lerini al
    try:
        from .getir_cop import update_meb_alan_ids
    except ImportError:
        from getir_cop import update_meb_alan_ids
    
    meb_alan_ids = update_meb_alan_ids()

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            try:
                # Alan ID'sini al veya oluştur
                area_id, meb_alan_id, matched_name = get_or_create_area_for_download(cursor, alan_adi, meb_alan_ids)
                
                if meb_alan_id:
                    # MEB ID bazlı klasör yapısı: {meb_alan_id}_{alan_adi}
                    folder_name = f"{meb_alan_id}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    yield {"type": "status", "message": f"[{alan_adi}] Klasör: {folder_name}"}
                else:
                    # MEB ID yoksa database ID kullan
                    folder_name = f"{area_id:02d}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    yield {"type": "warning", "message": f"[{alan_adi}] MEB ID yok, database ID kullanılıyor: {folder_name}"}
                
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
                msg = f"[{alan_adi}] {archive_filename} zaten mevcut ({file_size // (1024*1024)}MB) - ATLANIYOR"
                print(msg)
                yield {"type": "info", "message": msg}
                continue

            # İndir
            msg = f"[{alan_adi}] {sinif}. sınıf: {archive_filename} indiriliyor..."
            print(msg)
            yield {"type": "status", "message": msg}
            try:
                # Chunk-based download with progress feedback
                with requests.get(link, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    
                    # Content-Length header'dan dosya boyutunu al
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(archive_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # Progress mesajı (her 1MB'de bir)
                                if downloaded_size % (1024 * 1024) == 0 or downloaded_size == total_size:
                                    if total_size > 0:
                                        progress = (downloaded_size / total_size) * 100
                                        progress_msg = f"[{alan_adi}] {archive_filename} indiriliyor... {progress:.1f}% ({downloaded_size // (1024*1024)}MB/{total_size // (1024*1024)}MB)"
                                    else:
                                        progress_msg = f"[{alan_adi}] {archive_filename} indiriliyor... {downloaded_size // (1024*1024)}MB"
                                    
                                    yield {"type": "progress", "message": progress_msg}
                
                msg = f"[{alan_adi}] {archive_filename} indirildi ({downloaded_size // (1024*1024)}MB) - AÇMA İŞLEMİ ATLAND!"
                print(msg)
                yield {"type": "status", "message": msg}
            except requests.exceptions.Timeout:
                msg = f"[{alan_adi}] {archive_filename} indirme timeout (120s) - dosya çok büyük olabilir"
                print(msg)
                yield {"type": "error", "message": msg}
                continue
            except requests.exceptions.RequestException as e:
                msg = f"[{alan_adi}] {archive_filename} indirme hatası: {e}"
                print(msg)
                yield {"type": "error", "message": msg}
                continue
            except Exception as e:
                msg = f"[{alan_adi}] {archive_filename} indirilemedi: {e}"
                print(msg)
                yield {"type": "error", "message": msg}
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
                alan_id = get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id, dbf_urls=alan_urls)
                
                # Protokol alan ise işle (ders bağlantıları için)
                if is_protocol_area(alan_adi):
                    handle_protocol_area(cursor, alan_adi, alan_id)
                
                saved_alan_count += 1
                yield {'type': 'progress', 'message': f'URL kaydedildi: {alan_adi} ({len(alan_urls)} sınıf)'}
                
            except Exception as e:
                yield {'type': 'error', 'message': f'URL kaydetme hatası ({alan_adi}): {e}'}
        
        yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için URL\'ler veritabanına kaydedildi.'}
        
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
    
    yield {'type': 'done', 'message': f'Tüm DBF dosyaları işlendi. {len(alan_dbf_urls)} alan için URL\'ler veritabanına kaydedildi.'}

@with_database
def download_and_extract_dbf_with_progress(cursor, dbf_data):
    """
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/{meb_alan_id}_{alan_adi}/ klasörüne açar.
    Mevcut dosyaları kontrol eder ve varsa atlar.
    Eksik alanları otomatik oluşturur.
    Her adımda yield ile ilerleme mesajı döndürür.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    # MEB alan ID'lerini al
    try:
        from .getir_cop import update_meb_alan_ids
    except ImportError:
        from getir_cop import update_meb_alan_ids
    
    meb_alan_ids = update_meb_alan_ids()

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            try:
                # Alan ID'sini al veya oluştur
                area_id, meb_alan_id, matched_name = get_or_create_area_for_download(cursor, alan_adi, meb_alan_ids)
                
                if meb_alan_id:
                    # MEB ID bazlı klasör yapısı: {meb_alan_id}_{alan_adi}
                    folder_name = f"{meb_alan_id}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    yield {"type": "status", "message": f"[{alan_adi}] Klasör: {folder_name}"}
                else:
                    # MEB ID yoksa database ID kullan
                    folder_name = f"{area_id:02d}_{sanitize_filename(matched_name)}"
                    alan_dir = os.path.join(DBF_ROOT_DIR, folder_name)
                    yield {"type": "warning", "message": f"[{alan_adi}] MEB ID yok, database ID kullanılıyor: {folder_name}"}
                
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
                msg = f"[{alan_adi}] {archive_filename} zaten mevcut ({file_size // (1024*1024)}MB) - ATLANIYOR"
                print(msg)
                yield {"type": "info", "message": msg}
                continue

            # İndir
            msg = f"[{alan_adi}] {sinif}. sınıf: {archive_filename} indiriliyor..."
            print(msg)
            yield {"type": "status", "message": msg}
            try:
                # Chunk-based download with progress feedback
                with requests.get(link, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    
                    # Content-Length header'dan dosya boyutunu al
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded_size = 0
                    
                    with open(archive_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                
                                # Progress mesajı (her 1MB'de bir)
                                if downloaded_size % (1024 * 1024) == 0 or downloaded_size == total_size:
                                    if total_size > 0:
                                        progress = (downloaded_size / total_size) * 100
                                        progress_msg = f"[{alan_adi}] {archive_filename} indiriliyor... {progress:.1f}% ({downloaded_size // (1024*1024)}MB/{total_size // (1024*1024)}MB)"
                                    else:
                                        progress_msg = f"[{alan_adi}] {archive_filename} indiriliyor... {downloaded_size // (1024*1024)}MB"
                                    
                                    yield {"type": "progress", "message": progress_msg}
                
                msg = f"[{alan_adi}] {archive_filename} indirildi ({downloaded_size // (1024*1024)}MB)."
                print(msg)
                yield {"type": "status", "message": msg}
            except requests.exceptions.Timeout:
                msg = f"[{alan_adi}] {archive_filename} indirme timeout (120s) - dosya çok büyük olabilir"
                print(msg)
                yield {"type": "error", "message": msg}
                continue
            except requests.exceptions.RequestException as e:
                msg = f"[{alan_adi}] {archive_filename} indirme hatası: {e}"
                print(msg)
                yield {"type": "error", "message": msg}
                continue
            except Exception as e:
                msg = f"[{alan_adi}] {archive_filename} indirilemedi: {e}"
                print(msg)
                yield {"type": "error", "message": msg}
                continue

            # Aç
            msg = f"[{alan_adi}] {archive_filename} açılıyor..."
            print(msg)
            yield {"type": "status", "message": msg}
            try:
                extract_archive(archive_path, alan_dir)
                msg = f"[{alan_adi}] {archive_filename} başarıyla açıldı."
                print(msg)
                yield {"type": "status", "message": msg}
            except Exception as e:
                msg = f"[{alan_adi}] {archive_filename} açılamadı: {e}"
                print(msg)
                yield {"type": "error", "message": msg}

def extract_archive(archive_path, extract_dir):
    """
    RAR veya ZIP dosyasını açar. Dosya tipini otomatik algılar.
    """
    try:
        with open(archive_path, "rb") as f:
            magic = f.read(4)
        
        is_rar = magic == b"Rar!"
        is_zip = magic == b"PK\x03\x04"
        
        if is_rar:
            with rarfile.RarFile(archive_path) as rf:
                rf.extractall(extract_dir)
        elif is_zip:
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_dir)
        else:
            raise Exception(f"Desteklenmeyen dosya formatı (magic: {magic})")
    except Exception as e:
        raise Exception(f"Arşiv açılırken hata: {e}")

def retry_extract_file(alan_adi, archive_filename):
    """
    Belirli bir dosya için tekrar açma işlemi (hem RAR hem ZIP destekler).
    """
    alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
    archive_path = os.path.join(alan_dir, archive_filename)
    
    msg = f"[{alan_adi}] {archive_filename} tekrar açılıyor..."
    print(msg)
    try:
        extract_archive(archive_path, alan_dir)
        msg = f"[{alan_adi}] {archive_filename} başarıyla tekrar açıldı."
        print(msg)
        return {"type": "status", "message": msg}
    except Exception as e:
        msg = f"[{alan_adi}] {archive_filename} tekrar açılamadı: {e}"
        print(msg)
        return {"type": "error", "message": msg}

def retry_extract_all_files_with_progress():
    """
    dbf/ altındaki tüm alan klasörlerindeki .rar ve .zip dosyalarını tekrar açar.
    Her adımda yield ile ilerleme mesajı döndürür.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        yield {"type": "error", "message": "dbf/ dizini bulunamadı."}
        return

    for alan_klasor in os.listdir(DBF_ROOT_DIR):
        alan_dir = os.path.join(DBF_ROOT_DIR, alan_klasor)
        if not os.path.isdir(alan_dir):
            continue
        
        for fname in os.listdir(alan_dir):
            if fname.lower().endswith((".rar", ".zip")):
                archive_path = os.path.join(alan_dir, fname)
                alan_adi = alan_klasor
                
                msg = f"[{alan_adi}] {fname} tekrar açılıyor..."
                print(msg)
                yield {"type": "status", "message": msg}
                try:
                    extract_archive(archive_path, alan_dir)
                    msg = f"[{alan_adi}] {fname} başarıyla tekrar açıldı."
                    print(msg)
                    yield {"type": "status", "message": msg}
                except Exception as e:
                    msg = f"[{alan_adi}] {fname} tekrar açılamadı: {e}"
                    print(msg)
                    yield {"type": "error", "message": msg}

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
    
    # MEB alan ID'lerini güncelle (getir_cop.py'den)
    try:
        from .getir_cop import update_meb_alan_ids
    except ImportError:
        from getir_cop import update_meb_alan_ids
    
    meb_alan_ids = update_meb_alan_ids()
    
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
    print("2. İndir ve Aç")
    print("3. Yeniden Aç (Retry)")
    print("4. DBF Dosyalarından Ders Adlarını Çıkar")
    print("5. DBF URL'lerini Veritabanına Kaydet")
    
    choice = input("Seçiminizi yapın (1-5): ").strip()
    
    if choice == "1":
        print("DBF verileri çekiliyor...")
        dbf_data = getir_dbf()
        if dbf_data:
            print("✅ DBF verileri başarıyla çekildi!")
            print(f"Toplam {sum(len(alanlar) for alanlar in dbf_data.values())} alan bulundu.")
        else:
            print("❌ DBF verileri çekilemedi!")
    
    elif choice == "2":
        print("DBF verileri çekiliyor...")
        dbf_data = getir_dbf()
        if dbf_data:
            print("✅ DBF verileri çekildi, indirme ve açma başlıyor...")
            for message in download_and_extract_dbf_with_progress(dbf_data):
                print(message["message"])
        else:
            print("❌ DBF verileri çekilemedi!")
    
    elif choice == "3":
        print("Dosyalar yeniden açılıyor...")
        for message in retry_extract_all_files_with_progress():
            if message["type"] == "error":
                print(f"🔴 {message['message']}")
            else:
                print(message["message"])
    
    elif choice == "4":
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
    
    elif choice == "5":
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
