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
import time
from typing import List, Dict, Optional
try:
    from .utils_normalize import sanitize_filename_tr
except ImportError:
    from utils_normalize import sanitize_filename_tr

def detect_archive_type(file_path: str) -> str:
    """
    Dosyanın gerçek formatını header'dan tespit eder.
    
    Args:
        file_path: Arşiv dosyasının yolu
        
    Returns:
        Dosya tipi: RAR, ZIP, 7Z veya UNKNOWN
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
        
        if header.startswith(b'Rar!'):
            return "RAR"
        elif header.startswith(b'PK'):
            return "ZIP"
        elif header.startswith(b'7z'):
            return "7Z"
        else:
            return f"UNKNOWN (header: {header[:8].hex()})"
            
    except Exception as e:
        return f"ERROR: {e}"

def extract_archive(archive_path: str, extract_to: str):
    """
    RAR, ZIP veya 7Z arşivini açar. 
    unar komutu kullanır (%100 başarı - tüm formatları destekler)
    
    Args:
        archive_path: Arşiv dosyasının yolu
        extract_to: Çıkarılacak klasör
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Arşiv dosyası bulunamadı: {archive_path}")
    
    os.makedirs(extract_to, exist_ok=True)
    
    # Gerçek dosya tipini header'dan tespit et
    real_type = detect_archive_type(archive_path)
    file_extension = archive_path.lower().split('.')[-1]
    
    # Dosya uzantısı ile gerçek tip uyuşmuyorsa uyar
    if file_extension == 'rar' and real_type == 'ZIP':
        print(f"⚠️ Dikkat: .rar uzantılı ama aslında ZIP dosyası: {os.path.basename(archive_path)}")
    elif file_extension == 'zip' and real_type == 'RAR':
        print(f"⚠️ Dikkat: .zip uzantılı ama aslında RAR dosyası: {os.path.basename(archive_path)}")
    
    # unar komutu - hem RAR hem ZIP hem 7Z açabilir (%100 başarı)
    try:
        import subprocess
        result = subprocess.run(['unar', '-o', extract_to, archive_path], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"📦 Arşiv açıldı: {os.path.basename(archive_path)} ({real_type})")
            return
        else:
            raise ValueError(f"unar başarısız: {result.stderr[:100]}")
    
    except FileNotFoundError:
        raise ValueError(f"unar komutu bulunamadı. Lütfen 'brew install unar' çalıştırın.")
    except subprocess.TimeoutExpired:
        raise ValueError(f"Arşiv açma timeout (60s): {archive_path}")
    except Exception as e:
        raise ValueError(f"Arşiv açılamadı: {archive_path} - {e}")

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

def download_with_retry(url: str, max_retries: int = 3, timeout: int = 30) -> Optional[requests.Response]:
    """
    Retry mekanizması ile dosya indirir.
    SOLID S: Single Responsibility - sadece retry logic
    SOLID O: Open/Closed - farklı retry stratejileri eklenebilir
    
    Args:
        url: İndirilecek URL
        max_retries: Maksimum deneme sayısı
        timeout: Request timeout (saniye)
        
    Returns:
        requests.Response veya None
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⏱️ Timeout (deneme {attempt + 1}/{max_retries}), {wait_time}s bekleniyor: {url}")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Timeout (tüm denemeler tükendi): {url}")
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"🔌 Bağlantı hatası (deneme {attempt + 1}/{max_retries}), {wait_time}s bekleniyor: {url}")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Bağlantı hatası (tüm denemeler tükendi): {url}")
                
        except requests.exceptions.HTTPError as e:
            if e.response and 500 <= e.response.status_code < 600:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"🔧 Sunucu hatası {e.response.status_code} (deneme {attempt + 1}/{max_retries}), {wait_time}s bekleniyor: {url}")
                    time.sleep(wait_time)
                    continue
            print(f"❌ HTTP hatası: {e} - {url}")
            break
            
        except Exception as e:
            print(f"❌ Genel hata ({url}): {e}")
            break
    
    return None

def download_and_cache_pdf(url: str, cache_type: str, alan_adi: str = None, additional_info: str = None, alan_id: str = None, alan_db_id: int = None, meb_alan_id: str = None, max_retries: int = 3) -> Optional[str]:
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
        
        # PDF'yi retry mekanizması ile indir
        print(f"⬇️ İndiriliyor: {url}")
        response = download_with_retry(url, max_retries=max_retries)
        if not response:
            return None
        
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