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
    from .oku import extract_ders_adi
    from .utils import normalize_to_title_case_tr
except ImportError:
    from oku import extract_ders_adi
    from utils import normalize_to_title_case_tr

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

DBF_ROOT_DIR = "data/dbf"

def get_areas_from_db():
    """
    Veritabanından alan ID ve adlarını çeker.
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

def normalize_dbf_area_name(html_area_name):
    """
    HTML'den gelen alan adını utils.py standardına göre normalize eder.
    """
    return normalize_to_title_case_tr(html_area_name)

def find_matching_area_id(html_area_name, db_areas):
    """
    HTML'den gelen alan adını veritabanındaki alanlarla eşleştirir.
    Returns: (alan_id, matched_name) veya (None, None)
    """
    normalized_html_name = normalize_dbf_area_name(html_area_name)
    
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
                    class_dbf_data[alan_adi] = {
                        "link": dbf_link,
                        "guncelleme_tarihi": tarih
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

def sanitize_filename(name):
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir.
    """
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w\-_.()]", "", name)
    return name

def download_and_extract_dbf(dbf_data):
    """
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/{ID}-{ALAN_ADI}/ klasörüne açar.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    # Veritabanından alan bilgilerini al
    db_areas = get_areas_from_db()
    
    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            # Alan ID'sini bul
            area_id, matched_name = find_matching_area_id(alan_adi, db_areas)
            
            if area_id:
                # Klasör adını ID + alan adı formatında oluştur
                folder_name = f"{area_id:02d} - {matched_name}"
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(folder_name))
                print(f"[{alan_adi}] Klasör: {folder_name}")
            else:
                # ID bulunamazsa eski sistemi kullan
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
                print(f"[{alan_adi}] ID bulunamadı, eski format kullanılıyor")
            
            if not os.path.exists(alan_dir):
                os.makedirs(alan_dir)
            archive_filename = os.path.basename(link)
            archive_path = os.path.join(alan_dir, archive_filename)

            # İndir
            print(f"[{alan_adi}] {sinif}. sınıf: {archive_filename} indiriliyor...")
            try:
                with requests.get(link, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(archive_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
                print(f"[{alan_adi}] {archive_filename} indirildi.")
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

def download_and_extract_dbf_with_progress(dbf_data):
    """
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/{ID}-{ALAN_ADI}/ klasörüne açar.
    Her adımda yield ile ilerleme mesajı döndürür.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    # Veritabanından alan bilgilerini al
    db_areas = get_areas_from_db()

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            
            # Alan ID'sini bul
            area_id, matched_name = find_matching_area_id(alan_adi, db_areas)
            
            if area_id:
                # Klasör adını ID + alan adı formatında oluştur
                folder_name = f"{area_id:02d} - {matched_name}"
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(folder_name))
                yield {"type": "status", "message": f"[{alan_adi}] Klasör: {folder_name}"}
            else:
                # ID bulunamazsa eski sistemi kullan
                alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
                yield {"type": "warning", "message": f"[{alan_adi}] ID bulunamadı, eski format kullanılıyor"}
            
            if not os.path.exists(alan_dir):
                os.makedirs(alan_dir)
            archive_filename = os.path.basename(link)
            archive_path = os.path.join(alan_dir, archive_filename)

            # İndir
            msg = f"[{alan_adi}] {sinif}. sınıf: {archive_filename} indiriliyor..."
            print(msg)
            yield {"type": "status", "message": msg}
            try:
                with requests.get(link, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(archive_path, "wb") as f:
                        shutil.copyfileobj(r.raw, f)
                msg = f"[{alan_adi}] {archive_filename} indirildi."
                print(msg)
                yield {"type": "status", "message": msg}
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

def main():
    """
    DBF işlemleri ana menüsü
    """
    print("Ders Bilgi Formu (DBF) Getirici")
    print("1. Veri Çek (9, 10, 11, 12. sınıflar)")
    print("2. İndir ve Aç")
    print("3. Yeniden Aç (Retry)")
    print("4. DBF Dosyalarından Ders Adlarını Çıkar")
    
    choice = input("Seçiminizi yapın (1-4): ").strip()
    
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
    
    else:
        print("Geçersiz seçim!")

if __name__ == "__main__":
    main()
