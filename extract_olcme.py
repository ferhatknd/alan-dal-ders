import PyPDF2
import re
import os
import sys
import random
import glob

def extract_olcme_degerlendirme_from_pdf(pdf_path):
    """PDF dosyasından ÖLÇME VE DEĞERLENDİRME bölümünü çıkarır %95 civarında başarı"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            # Tüm sayfaları oku
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Normalizasyon: fazla boşlukları temizle
            full_text = re.sub(r'\s+', ' ', full_text)

            start_patterns_case_sensitive = [
                "DEĞERLENDİRME",
                "ÖLÇME VE DEĞER", 
                "ÖLÇME & DEĞERLENDİRME", 
                "OLCME VE DEGERLENDIRME"  # varyasyonlar
            ]

            end_patterns_case_sensitive = [
                "KAZANIM",
                "SÜRE",
                "DERSİN",
                "ÖĞRENME",
                "UYGULAMA",
            ]
            
            try:
                for start_marker in start_patterns_case_sensitive:
                    if start_marker in full_text:
                        start_index = full_text.index(start_marker) + len(start_marker)
                        # En erken gelen end_marker'ı bul
                        earliest_end_index = None
                        for end_marker in end_patterns_case_sensitive:
                            index = full_text.find(end_marker, start_index)
                            if index != -1 and (earliest_end_index is None or index < earliest_end_index):
                                earliest_end_index = index
                        if earliest_end_index is not None:
                            result_text = full_text[start_index:earliest_end_index].strip()
                        else:
                            result_text = full_text[start_index:].strip()
                        result_text = re.sub(r'\s+', ' ', result_text)
                        return result_text
            except ValueError:
                pass  # Eğer ikisi de case-sensitive bulunamazsa aşağıdaki genel işleme geçsin

        return "ÖLÇME VE DEĞERLENDİRME bölümü bulunamadı"
    except Exception as e:
        return f"Hata: {str(e)}"


# New function for extracting structured fields from text
def extract_fields_from_text(text):
    # Varyasyonlarla case-sensitive yapı
    patterns = [
        (["DERSİN ADI", "ADI"], ["DERSİN", "DERSĠN"]), # Dersin Adı
        (["DERSİN SINIFI", "SINIFI"], ["DERSİN", "DERSĠN"]), # Sinifi (metin olarak)!!
        (["DERSİN SÜRESİ", "SÜRESİ"], ["DERSİN", "DERSĠN"]), # Süre/Ders saati (metin olarak)!!
        (["DERSİN AMACI", "AMACI"], ["DERSİN", "DERSĠN"]), # Dersin Amacı
        (["DERSİN KAZANIMLARI", "KAZANIMLARI"], ["EĞİTİM", "EĞĠTĠM", "EĞ", "DONAT"]), # Kazanım -> Madde yapılmalı
        (["DONANIMI"], ["ÖLÇ", "DEĞERLENDİRME"]), # Ortam/Donanım
        (["DEĞERLENDİRME"], ["DERSİN", "DERSĠN", "KAZANIM", "ÖĞRENME"]), # Ölçme-Değerlendirme
    ]
    result = {}

    for i, (start_keys, end_keys) in enumerate(patterns, 1):
        start_index = None
        start_match = ""
        for sk in start_keys:
            idx = text.find(sk)
            if idx != -1 and (start_index is None or idx < start_index):
                start_index = idx + len(sk)
                start_match = sk
        if start_index is None:
            continue
        end_index = None
        for ek in end_keys:
            idx = text.find(ek, start_index)
            if idx != -1 and (end_index is None or idx < end_index):
                end_index = idx
        if end_index is not None:
            section = text[start_index:end_index].strip()
        else:
            section = text[start_index:].strip()
        section = re.sub(r'\s+', ' ', section)
        result[f"Case{i}_{start_match}"] = section
    return result

def find_all_pdfs_in_dbf_directory():
    """data/dbf dizinindeki tüm PDF dosyalarını bulur"""
    base_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf"
    
    # Tüm PDF dosyalarını bul
    pdf_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    return pdf_files

def print_full_pdf_text(pdf_path):
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"
        print(full_text)

def main():
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) != 2:
        print("Kullanım: python extract_olcme.py <sayı>")
        print("Örnek: python extract_olcme.py 10")
        sys.exit(1)
    
    try:
        sample_count = int(sys.argv[1])
    except ValueError:
        print("Hata: Sayı parametresi geçerli bir tam sayı olmalıdır.")
        sys.exit(1)
    
    if sample_count <= 0:
        print("Hata: Sayı parametresi pozitif bir tam sayı olmalıdır.")
        sys.exit(1)
    
    # data/dbf dizinindeki tüm PDF'leri bul
    all_pdfs = find_all_pdfs_in_dbf_directory()
    
    if not all_pdfs:
        print("data/dbf dizininde hiç PDF dosyası bulunamadı.")
        sys.exit(1)
    
    print(f"data/dbf dizininde toplam {len(all_pdfs)} PDF dosyası bulundu.")
    
    # Rastgele örnekleme yap
    if sample_count > len(all_pdfs):
        print(f"Uyarı: İstenen sayı ({sample_count}) toplam dosya sayısından ({len(all_pdfs)}) büyük. Tüm dosyalar işlenecek.")
        selected_pdfs = all_pdfs
    else:
        selected_pdfs = random.sample(all_pdfs, sample_count)
    
    print(f"Rastgele seçilen {len(selected_pdfs)} dosya işleniyor...\n")
    
    # Her dosyayı işle
    for i, pdf_path in enumerate(selected_pdfs, 1):
        # 1. Dizin ve dosya adı satırı
        print(f"{os.path.dirname(pdf_path).replace('/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/', '')} / {os.path.basename(pdf_path)}")
        
        # 2. Çizgi
        print("-" * 80)
        
        # PDF'ten tüm metni alalım
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"

        # normalize et
        full_text = re.sub(r'\s+', ' ', full_text)

        # Ardından tüm metin üzerinden başlıkları çıkart
        extracted_fields = extract_fields_from_text(full_text)
        for key, value in extracted_fields.items():
            title = key.split("_", 1)[-1].capitalize()
            print(f"\n{title}: {value}")
        print()

        # 4. Tüm sayfa
        # print_full_pdf_text(pdf_path)  # tüm PDF metni burada görünür
        # print(pdf_path)

if __name__ == "__main__":
    main()