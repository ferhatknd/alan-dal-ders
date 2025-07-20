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
            
            # ÖLÇME VE DEĞERLENDİRME bölümünü doğrudan metinde ara
            if "ÖLÇME VE DEĞERLENDİRME" in full_text.upper():
                # ÖLÇME VE DEĞERLENDİRME'nin pozisyonunu bul
                olcme_pos = full_text.upper().find("ÖLÇME VE DEĞERLENDİRME")
                
                # Bu bölümden sonraki metni al (1000 karakter - daha fazla alan)
                after_olcme = full_text[olcme_pos + len("ÖLÇME VE DEĞERLENDİRME"):olcme_pos + 1000]
                
                # "Bu derste" pattern'ini ara
                if "bu derste" in after_olcme.lower():
                    bu_derste_pos = after_olcme.lower().find("bu derste")
                    
                    # "Bu derste"den önceki 20 karakteri de al (cümle başını yakalamak için)
                    start_pos = max(0, bu_derste_pos - 20)
                    result_text = after_olcme[start_pos:]
                                      
                    # Önce tüm tablo başlıklarını kaldır
                    end_patterns = [
                        "KAZANIM",
                        "SÜRE", 
                        "DERSİN", 
                        "ÖĞRENME",
                        "UYGULAMA", 
                    ]
                    
                    # Tablo başlıklarını kaldır (büyük/küçük harf duyarlı)
                    for pattern in end_patterns:
                        if pattern in result_text:
                            pattern_pos = result_text.find(pattern)
                            result_text = result_text[:pattern_pos].strip()
                            break
                    
                    # Sonra "sağlanabilir" ile bitir (varsa)
                    if "sağlanabilir." in result_text.lower():
                        saglanabilir_pos = result_text.lower().find("sağlanabilir.")
                        result_text = result_text[:saglanabilir_pos + len("sağlanabilir.")]
                    elif "sağlanabilir" in result_text.lower():
                        saglanabilir_pos = result_text.lower().find("sağlanabilir")
                        # "sağlanabilir" kelimesinin sonuna kadar al ve nokta ekle
                        result_text = result_text[:saglanabilir_pos + len("sağlanabilir")] + "."
                    else:
                        # "sağlanabilir" yoksa son nokta ile bitir
                        # Son tam cümleyi bul
                        sentences = result_text.split('.')
                        if len(sentences) > 1:
                            # Son boş olmayan cümleyi al
                            complete_sentences = [s.strip() for s in sentences if s.strip()]
                            if complete_sentences:
                                result_text = '. '.join(complete_sentences) + "."
                    
                    # Temizlik (karakter kısıtı yok)
                    result_text = re.sub(r'\s+', ' ', result_text).strip()
                    
                    return result_text
                else:
                    # "Bu derste" bulamazsa tüm metni al
                    result_text = after_olcme
                    
                    # Bu durumda da tablo başlıklarını kaldır
                    end_patterns = [
                        "KAZANIM",
                        "SÜRE", 
                        "DERSİN", 
                        "ÖĞRENME",
                        "UYGULAMA"
                    ]
                    
                    result_text_upper = result_text.upper()
                    for pattern in end_patterns:
                        if pattern in result_text_upper:
                            pattern_pos = result_text_upper.find(pattern)
                            result_text = result_text[:pattern_pos].strip()
                            break
                    
                    # "sağlanabilir" ile bitir (varsa)
                    if "sağlanabilir." in result_text.lower():
                        saglanabilir_pos = result_text.lower().find("sağlanabilir.")
                        result_text = result_text[:saglanabilir_pos + len("sağlanabilir.")]
                    elif "sağlanabilir" in result_text.lower():
                        saglanabilir_pos = result_text.lower().find("sağlanabilir")
                        result_text = result_text[:saglanabilir_pos + len("sağlanabilir")] + "."
                    else:
                        # Son tam cümleyi bul
                        sentences = result_text.split('.')
                        if len(sentences) > 1:
                            complete_sentences = [s.strip() for s in sentences if s.strip()]
                            if complete_sentences:
                                result_text = '. '.join(complete_sentences) + "."
                    
                    result_text = re.sub(r'\s+', ' ', result_text).strip()
                    return result_text
                
            return "ÖLÇME VE DEĞERLENDİRME bölümü bulunamadı"
    except Exception as e:
        return f"Hata: {str(e)}"

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
        
        # 3. Sadece metin (karakter kısıtı yok)
        olcme_text = extract_olcme_degerlendirme_from_pdf(pdf_path)
        print(olcme_text)
        print()  # Boş satır ayırıcı

if __name__ == "__main__":
    main()