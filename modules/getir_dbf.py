import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import rarfile
import zipfile
import re

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

DBF_ROOT_DIR = "data/dbf"

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
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/ALAN_ADI/ klasörüne açar.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
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
    Her alan için ilgili RAR/ZIP dosyasını indirir ve dbf/ALAN_ADI/ klasörüne açar.
    Her adımda yield ile ilerleme mesajı döndürür.
    """
    if not os.path.exists(DBF_ROOT_DIR):
        os.makedirs(DBF_ROOT_DIR)

    for sinif, alanlar in dbf_data.items():
        for alan_adi, info in alanlar.items():
            link = info["link"]
            alan_dir = os.path.join(DBF_ROOT_DIR, sanitize_filename(alan_adi))
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

def main():
    """
    DBF linklerini çek, indir ve aç.
    """
    print("DBF RAR/ZIP dosyaları toplanıyor...")
    dbf_data = getir_dbf()
    print("Tüm DBF linkleri alındı. İndirme ve açma işlemi başlıyor...")
    download_and_extract_dbf(dbf_data)
    print("Tüm işlemler tamamlandı.")

if __name__ == "__main__":
    main()
