"""
modules/utils_file_management.py - Dosya İşlemleri Yönetimi

Bu modül, dosya indirme, dizin yönetimi, arşiv işlemleri gibi
tüm dosya işlemlerini yönetir.

Taşınan fonksiyonlar:
- check_existing_file_in_all_areas
- move_file_to_shared_folder
- download_and_cache_pdf
- get_temp_pdf_path
- extract_archive
- scan_directory_for_archives
- scan_directory_for_pdfs
"""

import os
import requests
import hashlib
from typing import Optional
import shutil

try:
    from .utils import sanitize_filename_tr
except ImportError:
    from utils import sanitize_filename_tr


def check_existing_file_in_all_areas(filename: str, cache_type: str, current_folder: str = None) -> Optional[str]:
    """
    Bir dosyanın tüm alan klasörlerinde mevcut olup olmadığını kontrol eder.
    
    Args:
        filename: Kontrol edilecek dosya adı
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
        current_folder: Mevcut alan klasörü (bu klasörde atlanır)
    
    Returns:
        Dosyanın bulunduğu ilk yol veya None
    """
    cache_root = os.path.join("data", cache_type)
    if not os.path.exists(cache_root):
        return None
    
    # Tüm alan klasörlerini tara
    for item in os.listdir(cache_root):
        item_path = os.path.join(cache_root, item)
        if not os.path.isdir(item_path):
            continue
        
        # Mevcut klasörse atla
        if current_folder and item == current_folder:
            continue
        
        # Dosya bu klasörde var mı?
        file_path = os.path.join(item_path, filename)
        if os.path.exists(file_path):
            return file_path
    
    return None


def move_file_to_shared_folder(source_path: str, cache_type: str, filename: str) -> Optional[str]:
    """
    Dosyayı ortak alan klasörüne taşır.
    
    Args:
        source_path: Kaynak dosya yolu
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
        filename: Dosya adı
    
    Returns:
        Taşınan dosyanın yeni yolu veya None
    """
    try:
        shared_folder = os.path.join("data", cache_type, "00_Ortak_Alan_Dersleri")
        os.makedirs(shared_folder, exist_ok=True)
        
        destination_path = os.path.join(shared_folder, filename)
        
        # Dosyayı taşı
        shutil.move(source_path, destination_path)
        
        print(f"📁 Ortak alana taşındı: {filename}")
        return destination_path
        
    except Exception as e:
        print(f"❌ Dosya taşıma hatası ({filename}): {e}")
        return None


def download_and_cache_pdf(url: str, cache_type: str, alan_adi: str = None, additional_info: str = None, alan_id: str = None, alan_db_id: int = None, meb_alan_id: str = None) -> Optional[str]:
    """
    PDF'yi indirir ve organize şekilde cache'ler.
    Duplicate dosyalar için ortak alan klasörü kullanır.
    
    Args:
        url: PDF URL'si
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
        alan_adi: Alan adı (klasör adı için)
        additional_info: Ek bilgi (sınıf, dal vb.)
        alan_id: Alan ID'si (organizasyon için, opsiyonel)
        alan_db_id: Veritabanı alan ID'si (klasör yapısı için)
        meb_alan_id: MEB alan ID'si (02, 08 gibi - klasör yapısı için)
    
    Returns:
        İndirilen dosyanın yolu veya None
    """
    if not url or not cache_type:
        return None
    
    try:
        # Alan adı yoksa, URL'den bir parça alarak geçici bir isim oluştur
        if not alan_adi:
            safe_alan_adi = url.split('/')[-2] if len(url.split('/')) > 1 else "bilinmeyen_alan"
        else:
            # Merkezi sanitize fonksiyonunu kullan
            safe_alan_adi = sanitize_filename_tr(alan_adi)
        
        # Klasör yapısı belirleme
        if meb_alan_id and cache_type in ['cop', 'dbf', 'dm', 'bom']:
            # MEB ID bazlı organizasyon: {meb_alan_id}_{alan_adi}
            folder_name = f"{meb_alan_id}_{safe_alan_adi}"
        elif alan_db_id and cache_type in ['cop', 'dbf', 'dm', 'bom']:
            # DB ID bazlı organizasyon: {ID:02d}_{alan_adi}
            folder_name = f"{int(alan_db_id):02d}_{safe_alan_adi}"
        else:
            # Eski format: {alan_adi}
            folder_name = safe_alan_adi
            
        cache_dir = os.path.join("data", cache_type, folder_name)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Dosya adını URL'den çıkar
        filename = url.split('/')[-1]
        if not filename.lower().endswith(('.pdf', '.rar', '.zip')):
            filename += '.pdf' # Varsayılan
        
        # Ek bilgi varsa dosya adına ekle
        if additional_info:
            name_part, ext = os.path.splitext(filename)
            filename = f"{name_part}_{additional_info}{ext}"
        
        file_path = os.path.join(cache_dir, filename)
        
        # Dosya zaten varsa indirme
        if os.path.exists(file_path):
            print(f"📁 Cache'den alınıyor: {file_path}")
            return file_path
        
        # Dosyanın başka alan klasörlerinde olup olmadığını kontrol et
        existing_file_path = check_existing_file_in_all_areas(filename, cache_type, folder_name)
        if existing_file_path:
            # Dosya başka bir alanda mevcut - ortak alana taşı
            shared_path = move_file_to_shared_folder(existing_file_path, cache_type, filename)
            if shared_path:
                print(f"📁 Ortak alandan kullanılıyor: {shared_path}")
                return shared_path
        
        # Ortak alan klasöründe var mı kontrol et
        shared_file_path = os.path.join("data", cache_type, "00_Ortak_Alan_Dersleri", filename)
        if os.path.exists(shared_file_path):
            print(f"📁 Ortak alandan alınıyor: {shared_file_path}")
            return shared_file_path
        
        # PDF'yi indir
        print(f"⬇️ İndiriliyor: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Kaydedildi: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ Dosya indirme hatası ({url}): {e}")
        return None


def get_temp_pdf_path(url: str) -> str:
    """
    Geçici PDF dosyası için güvenli yol oluştur
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"temp_pdf_{url_hash}.pdf"


def extract_archive(archive_path, extract_dir):
    """
    RAR veya ZIP dosyasını açar. Dosya tipini otomatik algılar.
    Merkezi arşiv açma fonksiyonu.
    
    Args:
        archive_path: Açılacak arşiv dosyasının yolu
        extract_dir: Dosyaların çıkarılacağı dizin
        
    Raises:
        Exception: Arşiv açılamadığında hata fırlatır
    """
    import rarfile
    import zipfile
    
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


def scan_directory_for_archives(root_dir, file_extensions=('.rar', '.zip')):
    """
    Belirtilen dizinde arşiv dosyalarını tarar.
    
    Args:
        root_dir: Taranacak ana dizin
        file_extensions: Aranacak dosya uzantıları
        
    Returns:
        List[Dict]: Bulunan arşiv dosyaları listesi
        Format: [{"path": "dosya_yolu", "name": "dosya_adi", "dir": "klasor_adi"}]
    """
    archives = []
    
    if not os.path.exists(root_dir):
        return archives
    
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if not os.path.isdir(item_path):
            continue
        
        for fname in os.listdir(item_path):
            if fname.lower().endswith(file_extensions):
                archive_path = os.path.join(item_path, fname)
                archives.append({
                    "path": archive_path,
                    "name": fname,
                    "dir": item
                })
    
    return archives


def scan_directory_for_pdfs(root_dir, file_extensions=('.pdf', '.docx')):
    """
    Belirtilen dizinde PDF/DOCX dosyalarını tarar.
    
    Args:
        root_dir: Taranacak ana dizin  
        file_extensions: Aranacak dosya uzantıları
        
    Returns:
        List[Dict]: Bulunan PDF dosyaları listesi
        Format: [{"path": "dosya_yolu", "name": "dosya_adi", "relative_path": "relative_yol"}]
    """
    pdfs = []
    
    if not os.path.exists(root_dir):
        return pdfs
    
    # Recursive search
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(file_extensions):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                
                pdfs.append({
                    "path": file_path,
                    "name": file,
                    "relative_path": relative_path
                })
    
    return pdfs