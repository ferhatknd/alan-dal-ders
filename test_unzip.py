#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testunzip.py

Verilen dizin ve tüm alt dizinlerdeki RAR ve ZIP dosyalarını açar.
oku_dbf.py'deki extract_archive fonksiyonunu kullanır.

Kullanım:
    python testunzip.py <dizin_yolu>
    
Örnek:
    python testunzip.py data/dbf
"""

import os
import sys
import time
from modules.utils_file_management import extract_archive

def find_archives(directory):
    """
    Verilen dizin ve alt dizinlerdeki tüm RAR ve ZIP dosyalarını bulur.
    """
    archive_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.rar', '.zip')):
                archive_files.append(os.path.join(root, file))
    return archive_files

def detect_archive_type(file_path):
    """
    Dosyanın gerçek formatını header'dan tespit eder.
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

def is_valid_archive(file_path):
    """
    Arşiv dosyasının geçerli olup olmadığını kontrol eder.
    """
    try:
        file_size = os.path.getsize(file_path)
        
        # Çok küçük dosyalar genelde bozuk (minimum 1KB)
        if file_size < 1024:
            return False, f"Dosya çok küçük ({file_size} bytes)"
        
        # Gerçek dosya tipini tespit et
        real_type = detect_archive_type(file_path)
        file_extension = file_path.lower().split('.')[-1]
        
        # Tanımsız formatları reddet
        if real_type.startswith('UNKNOWN') or real_type.startswith('ERROR'):
            return False, f"Tanımsız format: {real_type}"
        
        # Desteklenen format mu?
        if real_type not in ['RAR', 'ZIP', '7Z']:
            return False, f"Desteklenmeyen format: {real_type}"
        
        # Ek kontrol: Dosya ismi şüpheli mi?
        file_name = os.path.basename(file_path).lower()
        suspicious_names = ['temp', 'tmp', 'test', 'broken', 'corrupt']
        if any(name in file_name for name in suspicious_names):
            return False, "Şüpheli dosya ismi"
        
        return True, f"Geçerli {real_type}"
        
    except Exception as e:
        return False, f"Dosya okunamıyor: {e}"

def extract_all_archives(directory_path):
    """
    Dizindeki tüm arşiv dosyalarını açar.
    """
    if not os.path.exists(directory_path):
        print(f"Hata: Dizin bulunamadı - {directory_path}")
        return False
    
    archive_files = find_archives(directory_path)
    
    if not archive_files:
        print(f"Dizinde arşiv dosyası bulunamadı: {directory_path}")
        return True
    
    print(f"Bulunan arşiv sayısı: {len(archive_files)}")
    print("Kontrol ediliyor ve açılıyor...")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for i, archive_file in enumerate(archive_files, 1):
        file_name = os.path.basename(archive_file)
        archive_dir = os.path.dirname(archive_file)
        
        print(f"[{i}/{len(archive_files)}] {file_name}")
        
        # Önce dosyayı kontrol et
        is_valid, reason = is_valid_archive(archive_file)
        
        if not is_valid:
            skipped_count += 1
            print(f"    ⏭️ Atlandı: {reason}")
            continue
        
        try:
            # Gerçek dosya tipini tespit et
            real_type = detect_archive_type(archive_file)
            
            # Dosya uzantısı yanlışsa uyar
            file_extension = archive_file.lower().split('.')[-1]
            if file_extension == 'rar' and real_type == 'ZIP':
                print(f"    ⚠️ Dikkat: .rar uzantılı ama aslında ZIP dosyası!")
            elif file_extension == 'zip' and real_type == 'RAR':
                print(f"    ⚠️ Dikkat: .zip uzantılı ama aslında RAR dosyası!")
            
            extract_archive(archive_file, archive_dir)
            success_count += 1
            print(f"    ✅ Başarılı ({real_type})")
            
            # Arşivler arası kısa bekleme
            time.sleep(0.5)
            
        except Exception as e:
            error_str = str(e)
            if "Hiçbir dosya çıkarılamadı" in error_str:
                skipped_count += 1
                print(f"    ⏭️ Atlandı: Tüm dosyalar bozuk")
            else:
                error_count += 1
                print(f"    ❌ Hata: {e}")
            
            # Hata durumunda da bekleme
            time.sleep(0.5)
    
    print("="*50)
    print(f"📊 Özet:")
    print(f"   Toplam arşiv: {len(archive_files)}")
    print(f"   Başarılı: {success_count}")
    print(f"   Hatalı: {error_count}")
    print(f"   Atlanan: {skipped_count}")
    
    return error_count == 0

def main():
    if len(sys.argv) != 2:
        print("Kullanım: python testunzip.py <dizin_yolu>")
        print("Örnek: python testunzip.py data/dbf")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    print(f"Dizin: {directory_path}")
    print("="*50)
    
    success = extract_all_archives(directory_path)
    
    if success:
        print("✅ Tüm arşivler başarıyla açıldı!")
    else:
        print("⚠️ Bazı arşivler açılamadı!")
        sys.exit(1)

if __name__ == "__main__":
    main()