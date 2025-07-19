"""
modules/utils_file_management.py - Dosya İşlemleri Modülü

Bu modül dosya indirme, arşiv işlemleri, duplicate yönetimi ve
ortak alan dosya sistemi işlemlerini içerir.

"""

import os
import shutil
import requests
import zipfile
import tempfile
from typing import List, Dict, Optional
try:
    from .utils_normalize import sanitize_filename_tr
except ImportError:
    from utils_normalize import sanitize_filename_tr


def extract_archive(archive_path: str, extract_to: str):
    """
    RAR veya ZIP arşivini açar.
    
    Args:
        archive_path: Arşiv dosyasının yolu
        extract_to: Çıkarılacak klasör
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Arşiv dosyası bulunamadı: {archive_path}")
    
    os.makedirs(extract_to, exist_ok=True)
    
    if archive_path.lower().endswith('.zip'):
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            print(f"📦 ZIP açıldı: {archive_path}")
    elif archive_path.lower().endswith('.rar'):
        # RAR desteği için rarfile kütüphanesi gerekir
        try:
            import rarfile
            with rarfile.RarFile(archive_path) as rar_ref:
                rar_ref.extractall(extract_to)
                print(f"📦 RAR açıldı: {archive_path}")
        except ImportError:
            print(f"⚠️ RAR desteği yok, rarfile kütüphanesi gerekir: {archive_path}")
            raise
    else:
        raise ValueError(f"Desteklenmeyen arşiv formatı: {archive_path}")


def check_existing_file_in_all_areas(filename: str, cache_type: str, current_folder: str) -> Optional[str]:
    """
    Dosyanın diğer alan klasörlerinde olup olmadığını kontrol eder.
    
    Args:
        filename: Aranacak dosya adı
        cache_type: Cache tipi (cop, dbf, dm, bom)
        current_folder: Şu anki klasör (dahil edilmez)
        
    Returns:
        Bulunan dosyanın tam yolu veya None
    """
    cache_root = os.path.join("data", cache_type)
    if not os.path.exists(cache_root):
        return None
    
    for item in os.listdir(cache_root):
        item_path = os.path.join(cache_root, item)
        if not os.path.isdir(item_path) or item == current_folder:
            continue
            
        file_path = os.path.join(item_path, filename)
        if os.path.exists(file_path):
            return file_path
    
    return None


def move_file_to_shared_folder(source_path: str, cache_type: str, filename: str) -> Optional[str]:
    """
    Duplicate dosyayı ortak alana taşır.
    NOT: 00_Ortak_Alan_Dersleri sistemi kaldırıldı.
    
    Args:
        source_path: Kaynak dosya yolu
        cache_type: Cache tipi
        filename: Dosya adı
    
    Returns:
        Taşınan dosyanın yeni yolu veya None
    """
    try:
        # 00_Ortak_Alan_Dersleri sistemi kaldırıldı - dosyalar kendi klasörlerinde kalır
        print(f"🔄 Duplicate dosya tespit edildi ancak taşınmayacak: {filename}")
        return None  # Shared folder sistemi kaldırıldı
        
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
        
        # 00_Ortak_Alan_Dersleri sistemi kaldırıldı - bu kontrol artık yapılmıyor
        
        # PDF'yi indir
        print(f"⬇️ İndiriliyor: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ İndirildi: {file_path}")
        return file_path
        
    except requests.RequestException as e:
        print(f"❌ İndirme hatası ({url}): {e}")
        return None
    except Exception as e:
        print(f"❌ Genel hata ({url}): {e}")
        return None


def check_duplicate_files_in_cache(cache_type: str = 'cop') -> Dict:
    """
    Cache klasörlerindaki duplicate dosyaları kontrol eder.
    Ortak alan sistemi kaldırıldığı için sadece bilgi amaçlı.
    
    Args:
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
    
    Returns:
        Dict: Duplicate dosya bilgileri
    """
    cache_root = os.path.join("data", cache_type)
    if not os.path.exists(cache_root):
        return {"error": f"Cache dizini bulunamadı: {cache_root}"}
    
    # Dosya analizi
    files_by_name = {}
    folder_stats = {}
    
    for item in os.listdir(cache_root):
        item_path = os.path.join(cache_root, item)
        if not os.path.isdir(item_path):
            continue
        
        folder_name = item
        files = [f for f in os.listdir(item_path) if f.lower().endswith(('.pdf', '.rar', '.zip'))]
        folder_stats[folder_name] = len(files)
        
        # Dosya adlarını kaydet
        if folder_name not in files_by_name:
            files_by_name[folder_name] = {}
        
        for file in files:
            files_by_name[folder_name][file] = True
        
        # 00_Ortak_Alan_Dersleri sistemi kaldırıldı
        # Duplicate dosyalar artık sadece log ile takip edilir
        duplicate_count = 0
        for file in files:
            if any(file in files_by_name.get(other_folder, {}) for other_folder in files_by_name if other_folder != folder_name):
                duplicate_count += 1
        
        if duplicate_count > 0:
            print(f"      🔄 Duplicate tespit edildi: {duplicate_count} dosya (artık taşınmıyor)")
    
    return {
        "folder_stats": folder_stats,
        "shared_folders": []  # Ortak klasör sistemi kaldırıldı
    }


def scan_directory_for_pdfs(root_dir: str) -> List[Dict]:
    """
    Belirtilen dizin altındaki tüm PDF dosyalarını tarar.
    
    Args:
        root_dir: Taranacak kök dizin
        
    Returns:
        List[Dict]: PDF dosya bilgileri
    """
    pdfs = []
    
    if not os.path.exists(root_dir):
        return pdfs
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                
                pdfs.append({
                    "path": file_path,
                    "name": file,
                    "relative_path": relative_path
                })
    
    return pdfs


def scan_directory_for_archives(root_dir: str) -> List[Dict]:
    """
    Belirtilen dizin altındaki tüm arşiv dosyalarını (RAR, ZIP) tarar.
    
    Args:
        root_dir: Taranacak kök dizin
        
    Returns:
        List[Dict]: Arşiv dosya bilgileri
    """
    archives = []
    
    if not os.path.exists(root_dir):
        return archives
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.rar', '.zip')):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                
                archives.append({
                    "path": file_path,
                    "name": file,
                    "relative_path": relative_path
                })
    
    return archives

def log_duplicate_files_info(cache_type: str = 'cop'):
    """
    Duplicate dosyaları konsola loglar. 
    00_Ortak_Alan_Dersleri sistemi kaldırıldı, sadece bilgi amaçlı.
    
    Args:
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
    """
    cache_root = os.path.join("data", cache_type)
    if not os.path.exists(cache_root):
        print(f"Cache dizini bulunamadı: {cache_root}")
        return
    
    # Dosya adı -> klasör listesi mapping
    file_locations = {}
    
    for item in os.listdir(cache_root):
        item_path = os.path.join(cache_root, item)
        if not os.path.isdir(item_path) or item.startswith('00_'):
            continue
            
        for file in os.listdir(item_path):
            if file.lower().endswith(('.pdf', '.rar', '.zip')):
                if file not in file_locations:
                    file_locations[file] = []
                file_locations[file].append(item)
    
    # Duplicate dosyaları listele
    duplicates = {file: locations for file, locations in file_locations.items() if len(locations) > 1}
    
    if duplicates:
        print(f"\n🔄 {cache_type.upper()} duplicate dosyalar tespit edildi:")
        for file, locations in duplicates.items():
            print(f"  📄 {file} -> {len(locations)} klasörde: {', '.join(locations)}")
    else:
        print(f"\n✅ {cache_type.upper()} duplicate dosya bulunamadı")