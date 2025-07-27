import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from .utils_normalize import normalize_to_title_case_tr, sanitize_filename_tr
from .utils_database import with_database, get_or_create_alan, get_meb_alan_id_with_fallback, get_folder_name_for_download, get_meb_alan_ids_cached

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
    Protokol alanları için öncelik mantığı vardır.
    Returns: (alan_id, matched_name) veya (None, None)
    """
    normalized_html_name = normalize_to_title_case_tr(html_area_name)
    
    # Tam eşleşme kontrolü
    if normalized_html_name in db_areas:
        return db_areas[normalized_html_name], normalized_html_name
    
    # Protokol alan kontrolü - önce protokol eşleşmelerini ara
    is_protocol_search = "- Protokol" in normalized_html_name or "protokol" in normalized_html_name.lower()
    
    if is_protocol_search:
        # Protokol alanı arıyoruz - önce protokol eşleşmelerini kontrol et
        for db_name, area_id in db_areas.items():
            if "- Protokol" in db_name and (normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower()):
                print(f"Protokol eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
                return area_id, db_name
    else:
        # Normal alan arıyoruz - önce protokol olmayan eşleşmeleri kontrol et  
        for db_name, area_id in db_areas.items():
            if "- Protokol" not in db_name and (normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower()):
                print(f"Normal eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
                return area_id, db_name
    
    # Genel kısmi eşleşme kontrolü (eski mantık - fallback)
    for db_name, area_id in db_areas.items():
        if normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower():
            print(f"Genel eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
            return area_id, db_name
    
    print(f"Eşleşme bulunamadı: '{html_area_name}' (normalize: '{normalized_html_name}')")
    return None, None

def get_dbf_data_for_alan_and_sinif(alan_adi, meb_alan_id, sinif_kodu):
    """
    Belirli bir alan ve sınıf için DBF verilerini çeker.
    Hem normal hem protokol dosyalarını tespit eder (dosya adından).
    """
    params = {"kurum_id": "1", "sinif_kodu": sinif_kodu, "alan_id": meb_alan_id}
    
    try:
        response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # DBF linklerini bul (RAR/ZIP dosyası)
        dbf_links = soup.find_all('a', href=lambda x: x and (x.endswith('.rar') or x.endswith('.zip')))
        
        found_files = {}  # {alan_type: data}
        
        if dbf_links:
            for link in dbf_links:
                href = link.get('href', '')
                if href:
                    # Bozuk URL'leri filtrele (cop9/upload içeren linkler)
                    if '/cop9/upload/' in href:
                        print(f"🚫 Bozuk URL atlandı: {href}")
                        continue
                    
                    # Tam URL'yi oluştur
                    if href.startswith('http'):
                        dbf_url = href
                    else:
                        dbf_url = requests.compat.urljoin(response.url, href)
                    
                    # Dosya adından protokol tespiti yap
                    filename = href.split('/')[-1].lower()
                    is_protokol = any(x in filename for x in ['pro', 'protokol'])
                    
                    # Tarih bilgisini bul
                    tarih = ""
                    parent_div = link.find_parent('div')
                    if parent_div:
                        for li in parent_div.find_all('li'):
                            if 'calendar' in str(li) or re.search(r'\d{2}\.\d{2}\.\d{4}', li.get_text()):
                                tarih = li.get_text(strip=True)
                                break
                    
                    # Güncelleme yılını çıkar
                    update_year = None
                    if tarih:
                        year_match = re.search(r'(\d{4})', tarih)
                        if year_match:
                            year = int(year_match.group(1))
                            if 2000 <= year <= 2030:
                                update_year = str(year)
                    
                    # Alan tipini belirle
                    if is_protokol:
                        file_alan_adi = f"{alan_adi} - Protokol" if not alan_adi.endswith(" - Protokol") else alan_adi
                    else:
                        file_alan_adi = alan_adi.replace(" - Protokol", "") if " - Protokol" in alan_adi else alan_adi
                    
                    # İlk geçerli URL'yi kullan (daha önceden bu alan için URL kaydedilmemişse)
                    if file_alan_adi not in found_files:
                        found_files[file_alan_adi] = {
                            "link": dbf_url,
                            "guncelleme_tarihi": tarih,
                            "update_year": update_year,
                            "meb_alan_id": meb_alan_id,
                            "filename": filename,
                            "is_protokol": is_protokol
                        }
                        
                        print(f"📋 DBF Dosya tespit edildi: {file_alan_adi} -> {filename} {'(Protokol)' if is_protokol else '(Normal)'}")
        
        # Çağıran tarafın istediği alan tipini döndür
        return found_files.get(alan_adi)
        
    except requests.RequestException as e:
        print(f"DBF Hata: {alan_adi} ({sinif_kodu}. sınıf) sayfası çekilemedi: {e}")
        return None

def get_all_dbf_files_for_alan_and_sinif(alan_adi, meb_alan_id, sinif_kodu):
    """
    Belirli bir MEB alan ID ve sınıf için tüm DBF dosyalarını (normal + protokol) çeker.
    """
    params = {"kurum_id": "1", "sinif_kodu": sinif_kodu, "alan_id": meb_alan_id}
    
    try:
        response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # DBF linklerini bul (RAR/ZIP dosyası)
        dbf_links = soup.find_all('a', href=lambda x: x and (x.endswith('.rar') or x.endswith('.zip')))
        
        found_files = []  # [{"alan_adi": ..., "data": ...}]
        
        if dbf_links:
            # Tüm linkleri topla ve URL kalitesine göre sırala
            all_links = []
            for link in dbf_links:
                href = link.get('href', '')
                if href:
                    # Tam URL'yi oluştur
                    if href.startswith('http'):
                        dbf_url = href
                    else:
                        dbf_url = requests.compat.urljoin(response.url, href)
                    
                    # Bozuk URL'leri filtrele (cop9/upload içeren linkler)
                    if '/cop9/upload/' in href:
                        print(f"🚫 Bozuk URL atlandı: {href}")
                        continue
                    
                    # URL kalitesi kontrolü - doğru pattern olmalı (upload/dbf{grade}/)
                    url_quality = 0
                    if f'/upload/dbf{sinif_kodu}/' in href:
                        url_quality = 10  # En iyi - doğru pattern
                    elif '/upload/' in href and 'dbf' in href:
                        url_quality = 5   # Orta - upload var ama pattern tam değil
                    elif not ('cop' in href and 'upload' in href):
                        url_quality = 1   # Düşük - bozuk pattern değil ama ideal değil
                    else:
                        continue  # Bozuk pattern, atla
                    
                    # Dosya adından protokol tespiti yap
                    filename = href.split('/')[-1].lower()
                    is_protokol = any(x in filename for x in ['pro', 'protokol'])
                    
                    # Tarih bilgisini bul
                    tarih = ""
                    parent_div = link.find_parent('div')
                    if parent_div:
                        for li in parent_div.find_all('li'):
                            if 'calendar' in str(li) or re.search(r'\d{2}\.\d{2}\.\d{4}', li.get_text()):
                                tarih = li.get_text(strip=True)
                                break
                    
                    # Güncelleme yılını çıkar
                    update_year = None
                    if tarih:
                        year_match = re.search(r'(\d{4})', tarih)
                        if year_match:
                            year = int(year_match.group(1))
                            if 2000 <= year <= 2030:
                                update_year = str(year)
                    
                    # Alan adını belirle
                    if is_protokol:
                        file_alan_adi = f"{alan_adi} - Protokol"
                    else:
                        file_alan_adi = alan_adi
                    
                    all_links.append({
                        "alan_adi": file_alan_adi,
                        "link": dbf_url,
                        "guncelleme_tarihi": tarih,
                        "update_year": update_year,
                        "meb_alan_id": meb_alan_id,
                        "filename": filename,
                        "is_protokol": is_protokol,
                        "url_quality": url_quality,
                        "href": href
                    })
            
            # En kaliteli linkleri seç (alan adına göre grupla ve en iyi kaliteli olanı al)
            found_files_dict = {}
            for link_data in sorted(all_links, key=lambda x: x["url_quality"], reverse=True):
                alan_adi_key = link_data["alan_adi"]
                
                # Eğer bu alan için daha iyi bir link yoksa, bu linki kullan
                if alan_adi_key not in found_files_dict or found_files_dict[alan_adi_key]["url_quality"] < link_data["url_quality"]:
                    found_files_dict[alan_adi_key] = {
                        "link": link_data["link"],
                        "guncelleme_tarihi": link_data["guncelleme_tarihi"],
                        "update_year": link_data["update_year"],
                        "meb_alan_id": link_data["meb_alan_id"],
                        "filename": link_data["filename"],
                        "is_protokol": link_data["is_protokol"],
                        "url_quality": link_data["url_quality"]
                    }
                    
                    quality_text = "✅ EN İYİ" if link_data["url_quality"] == 10 else "⚠️ ORTA" if link_data["url_quality"] == 5 else "❓ DÜŞÜK"
                    print(f"📋 DBF Dosya tespit edildi: {alan_adi_key} -> {link_data['filename']} {'(Protokol)' if link_data['is_protokol'] else '(Normal)'} [{quality_text}]")
            
            # Convert to required format
            for alan_adi_key, data in found_files_dict.items():
                found_files.append({
                    "alan_adi": alan_adi_key,
                    "data": data
                })
        
        return found_files
        
    except requests.RequestException as e:
        print(f"DBF Hata: {alan_adi} ({sinif_kodu}. sınıf) sayfası çekilemedi: {e}")
        return []

def get_dbf_data(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için DBF (Ders Bilgi Formu) verilerini eşzamanlı olarak çeker.
    Her MEB alan ID sayfasından hem normal hem protokol dosyalarını tespit eder.
    """
    # Önce MEB alan ID'lerini çek (cache'den)
    print("📋 MEB Alan ID'leri çekiliyor...")
    meb_alan_ids = get_meb_alan_ids_cached()
    
    if not meb_alan_ids:
        print("❌ MEB Alan ID'leri çekilemedi!")
        return {}
    
    print(f"🔍 {len(meb_alan_ids)} alan için DBF linkleri çekiliyor (akıllı tespit)...")
    
    # Tüm alan+sınıf kombinasyonları için task listesi oluştur (sadece temel alanlar)
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
            executor.submit(get_all_dbf_files_for_alan_and_sinif, alan_adi, meb_alan_id, sinif): (alan_adi, meb_alan_id, sinif)
            for alan_adi, meb_alan_id, sinif in tasks
        }
        
        # Sonuçları topla
        for future in as_completed(future_to_task):
            base_alan_adi, meb_alan_id, sinif = future_to_task[future]
            
            try:
                found_files = future.result()
                
                if found_files:
                    # Sınıf bazında organize et
                    if sinif not in all_dbf_data:
                        all_dbf_data[sinif] = {}
                    
                    # Her bulunan dosyayı ekle
                    for file_info in found_files:
                        alan_adi = file_info["alan_adi"]
                        dbf_data = file_info["data"]
                        
                        all_dbf_data[sinif][alan_adi] = dbf_data
                        
                        if dbf_data["is_protokol"]:
                            print(f"✅ {alan_adi} ({sinif}. sınıf) -> DBF bulundu (Protokol, ID: {meb_alan_id})")
                        else:
                            print(f"✅ {alan_adi} ({sinif}. sınıf) -> DBF bulundu (Normal, ID: {meb_alan_id})")
                else:
                    print(f"❌ {base_alan_adi} ({sinif}. sınıf) -> DBF bulunamadı")
                    
            except Exception as e:
                print(f"❌ {base_alan_adi} ({sinif}. sınıf) DBF işleme hatası: {e}")
    
    return all_dbf_data


def sanitize_filename(name):
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir.
    utils.py'deki merkezi sanitize_filename_tr fonksiyonunu kullanır.
    """
    return sanitize_filename_tr(name)

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
            is_protokol = info.get("is_protokol", False)
            
            try:
                # MEB ID'yi çoklu kaynak stratejisi ile al
                data_meb_id = info.get("meb_alan_id")
                meb_alan_id, source = get_meb_alan_id_with_fallback(alan_adi, data_meb_id)
                
                # Alan ID'sini al veya oluştur - protokol durumunu kontrol et
                # Protokol dosyalar için protokol alan adını kullan
                search_alan_adi = alan_adi
                if is_protokol and not alan_adi.endswith("- Protokol"):
                    search_alan_adi = f"{alan_adi} - Protokol"
                
                area_id, _, matched_name = get_or_create_area_for_download(cursor, search_alan_adi, meb_alan_ids)
                
                # Klasör adını yeni strateji ile belirle
                folder_name = get_folder_name_for_download(matched_name or search_alan_adi, meb_alan_id, area_id)
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
                                
                saved_alan_count += 1
                sınıf_sayısı = len(alan_urls)
                
                # Standardize edilmiş konsol çıktısı - alan bazlı toplam
                yield {'type': 'progress', 'message': f'{meb_alan_id} - {alan_adi} ({saved_alan_count}/{len(alan_dbf_urls)}) Toplam {sınıf_sayısı} DBF indi.', 'progress': saved_alan_count / len(alan_dbf_urls)}
                
            except Exception as e:
                yield {'type': 'error', 'message': f'URL kaydetme hatası ({alan_adi}): {e}'}
        
        yield {'type': 'success', 'message': f'✅ {saved_alan_count} alan için URL\'ler veritabanına kaydedildi.'}
        
        # Merkezi istatistik fonksiyonunu kullan (CLAUDE.md kuralları)
        try:
            from .utils_stats import get_database_statistics, format_database_statistics_message
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
            # extract_ders_adi importu kaldırıldı, burada fonksiyon çağrısı eksik olabilir
            # Ancak legacy uyumluluk için alias eklenecek
            from .oku_dbf import extract_ders_adi
            ders_adi = extract_ders_adi(dbf_file_path)
            return ders_adi.strip() if ders_adi else None
    except Exception as e:
        print(f"DBF dosyası okuma hatası ({dbf_file_path}): {e}")
    return None

# Alias for legacy compatibility
extract_ders_adi = extract_course_name_from_dbf

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
    """
    import json
    
    # DBF verilerini çek
    print("📋 DBF linkleri çekiliyor...")
    dbf_data = get_dbf_data()
    
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
    
    for alan_adi, dbf_urls in alan_dbf_urls.items():
        try:
            # MEB Alan ID'sini al
            meb_alan_id = meb_alan_ids.get(alan_adi)
            
            # JSON formatında kaydet
            dbf_urls_json = json.dumps(dbf_urls)
            
            # Alan oluştur veya güncelle (otomatik oluşturma)
            alan_id = get_or_create_alan(cursor, alan_adi, meb_alan_id=meb_alan_id, dbf_urls=dbf_urls_json)
                        
            saved_count += 1
            print(f"✅ {alan_adi}: {len(dbf_urls)} sınıf URL'si kaydedildi (MEB ID: {meb_alan_id})")
            
        except Exception as e:
            print(f"❌ {alan_adi} kaydetme hatası: {e}")
            continue
        
    print(f"🎯 Toplam {saved_count} alan için DBF URL'leri veritabanına kaydedildi!")
    return {"success": True, "count": saved_count}

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
