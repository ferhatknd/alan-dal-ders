import os
import sys
import glob
import random
import json
from modules.oku_dbf import oku_dbf

def get_subdirectories(base_path):
    """Belirtilen yol altındaki tüm alt dizinleri döndürür."""
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

def find_pdf_files_recursive(directory):
    """Belirtilen dizin ve alt dizinlerindeki tüm PDF dosyalarını bulur."""
    pdf_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

if __name__ == "__main__":
    dbf_base_path = "data/dbf"

    if not os.path.exists(dbf_base_path):
        print(f"Hata: '{dbf_base_path}' dizini bulunamadı.")
        sys.exit(1)

    subdirs = get_subdirectories(dbf_base_path)

    if not subdirs:
        print(f"'{dbf_base_path}' altında alt dizin bulunamadı.")
        sys.exit(0)

    target_dir = None
    if len(sys.argv) > 1 and sys.argv[1].lower() == "random":
        target_dir_name = random.choice(subdirs)
        target_dir = os.path.join(dbf_base_path, target_dir_name)
        print(f"Rasgele seçilen dizin: {target_dir_name}")
    elif len(sys.argv) > 1:
        # Kullanıcı belirli bir dizin adı verdiyse
        specified_dir_name = sys.argv[1]
        if specified_dir_name in subdirs:
            target_dir = os.path.join(dbf_base_path, specified_dir_name)
            print(f"Belirtilen dizin: {specified_dir_name}")
        else:
            print(f"Hata: '{specified_dir_name}' dizini '{dbf_base_path}' altında bulunamadı.")
            sys.exit(1)
    else:
        print("Kullanım: python test.py [random | <dizin_adı>]")
        print(f"Mevcut dizinler: {', '.join(subdirs)}")
        sys.exit(1)

    if target_dir:
        pdf_files_to_process = find_pdf_files_recursive(target_dir)

        if not pdf_files_to_process:
            print(f"'{target_dir}' dizininde PDF dosyası bulunamadı.")
        else:
            print(f"'{target_dir}' dizininde bulunan {len(pdf_files_to_process)} PDF dosyası işleniyor...")
            for pdf_file in pdf_files_to_process:
                print(f"\n--- {os.path.basename(pdf_file)} işleniyor ---")
                try:
                    result = oku_dbf(pdf_file)
                    # oku.oku zaten terminale çıktı veriyor, burada sadece JSON çıktısını basabiliriz
                    # print(json.dumps(result, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(f"Hata: '{os.path.basename(pdf_file)}' işlenirken bir hata oluştu: {e}")
    else:
        print("İşlenecek bir dizin seçilemedi.")
