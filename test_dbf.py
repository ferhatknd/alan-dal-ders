#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_dbf.py
===========
Bu script, `modules/utils_oku_dbf.py` içerisindeki fonksiyonları test etmek için kullanılır.
Komut satırından argüman alarak `data/dbf` klasörü altındaki PDF/DOCX dosyalarını işler.

Kullanım:
  python test_dbf.py <dosya_adı_parçası>  # Belirtilen metni içeren dosyayı arar ve işler.
  python test_dbf.py <sayı>                # Rastgele 'sayı' kadar dosyayı seçer ve işler.
  python test_dbf.py 1                     # Rastgele 1 dosya seçer ve işler.
"""

import os
import sys
import random
import json

# Proje kök dizinini path'e ekleyerek modülün içe aktarılmasını sağlıyoruz
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from modules.utils_dbf1 import (
    read_full_text_from_file,
    ex_temel_bilgiler,
    ex_kazanim_tablosu
)
from modules.utils_dbf2 import ex_ob_tablosu

def find_files(search_term=None):
    """
    data/dbf dizini ve alt dizinlerindeki tüm .pdf ve .docx dosyalarını bulur.
    Eğer bir arama terimi verilirse, listeyi bu terime göre filtreler.
    """
    dbf_path = os.path.join(project_root, 'data', 'dbf')
    if not os.path.exists(dbf_path):
        print(f"Hata: 'data/dbf' dizini bulunamadı. Beklenen yol: {dbf_path}")
        return []

    all_files = []
    for root, _, files in os.walk(dbf_path):
        for file in files:
            # Geçici Word dosyalarını atla
            if file.lower().endswith(('.pdf', '.docx')) and not file.startswith('~$'):
                all_files.append(os.path.join(root, file))

    if not search_term:
        return all_files

    # Arama terimine göre filtrele
    try:
        # Eğer sayı ise, arama terimi olarak değil, rastgele dosya sayısı olarak ele al
        num_files = int(search_term)
        if num_files > len(all_files):
            print(f"Uyarı: Sadece {len(all_files)} dosya bulundu, {num_files} istendi. Bulunan tüm dosyalar işlenecek.")
            return all_files
        return random.sample(all_files, num_files)
    except ValueError:
        # Sayı değilse, dosya adında arama yap
        matching_files = [f for f in all_files if search_term.lower() in os.path.basename(f).lower()]
        return matching_files

def main():
    """
    Komut satırı argümanlarını işleyen ve DBF çıkarma işlemini çalıştıran ana fonksiyon.
    """
    if len(sys.argv) < 2:
        print(__doc__) # Scriptin docstring'ini yazdır
        sys.exit(1)

    arg = sys.argv[1]
    
    files_to_process = find_files(arg)
    
    if not files_to_process:
        print(f"'{arg}' ile eşleşen veya rastgele seçilebilecek dosya bulunamadı.")
        return

    for file_path in files_to_process:
        print(file_path)
        print(f"-"*60)
        
        try:
            full_text = read_full_text_from_file(file_path)
            if not full_text or not full_text.strip():
                print("❌ Hata: Dosya içeriği boş veya okunamadı.")
                continue

            # 2. Kazanım Tablosu
            kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text)
            print(kazanim_tablosu_str)
            
            # 3. Öğrenme Birimi Tablosu
            ob_tablosu_result = ex_ob_tablosu(full_text)
            print(ob_tablosu_result)

            # tüm metni bas amk
            #print(full_text)
            
        except Exception as e:
            import traceback
            print(f"\n❌ İşlem sırasında bir hata oluştu: {e}")
            traceback.print_exc()
            print(f"\n--- ❌ Hata ile Bitti: {os.path.basename(file_path)} ---\n")

if __name__ == "__main__":
    main()
