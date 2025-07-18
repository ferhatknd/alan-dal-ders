import os
import sys
import random
from modules.oku_dbf import oku_dbf

def get_subdirectories(base_path):
    """Belirtilen yol altındaki tüm alt dizinleri döndürür."""
    if not os.path.exists(base_path):
        return []
    return [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

def find_document_files_recursive(directory):
    """Belirtilen dizin ve alt dizinlerindeki tüm PDF ve DOCX dosyalarını bulur."""
    doc_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            # Hem .pdf hem de .docx uzantılı dosyaları kontrol et
            if file.lower().endswith(('.pdf', '.docx')):
                doc_files.append(os.path.join(root, file))
    return doc_files

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
            print(f"Mevcut dizinler: {', '.join(subdirs)}")
            sys.exit(1)
    else:
        print("Kullanım: python test-dbf.py [random | <dizin_adı>]")
        print(f"Mevcut dizinler: {', '.join(subdirs)}")
        sys.exit(1)

    if target_dir:
        doc_files_to_process = find_document_files_recursive(target_dir)

        if not doc_files_to_process:
            print(f"'{target_dir}' dizininde PDF veya DOCX dosyası bulunamadı.")
        else:
            print(f"'{target_dir}' dizininde bulunan {len(doc_files_to_process)} dosya işleniyor...")
            for doc_file in doc_files_to_process:
                print(f"\n--- {os.path.basename(doc_file)} işleniyor ---")
                try:
                    # oku_dbf fonksiyonu zaten sonuçları ekrana yazdırıyor
                    result = oku_dbf(doc_file)
                except Exception as e:
                    print(f"Hata: '{os.path.basename(doc_file)}' işlenirken bir hata oluştu: {e}")
    else:
        print("İşlenecek bir dizin seçilemedi.")