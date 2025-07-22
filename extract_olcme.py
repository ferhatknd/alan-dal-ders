import PyPDF2
import re
import os
import sys
import random
import glob

def normalize_turkish_chars(text):
    """PDF'den gelen bozuk Türkçe karakterleri düzeltir"""
    replacements = {
        'Ġ': 'İ',
        'ġ': 'ı', 
        'Ş': 'Ş',
        'ş': 'ş',
        'Ğ': 'Ğ',
        'ğ': 'ğ',
        'Ü': 'Ü',
        'ü': 'ü',
        'Ö': 'Ö',
        'ö': 'ö',
        'Ç': 'Ç',
        'ç': 'ç'
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text

def extract_fields_from_text(text):
    # Varyasyonlarla case-sensitive yapı
    patterns = [
        (["DERSİN ADI", "ADI"], ["DERSİN", "DERSĠN"]),                                  # Dersin Adı
        (["DERSİN SINIFI", "SINIFI"], ["DERSİN", "DERSĠN"]),                            # Sinifi (metin olarak)!!
        (["DERSİN SÜRESİ", "SÜRESİ"], ["DERSİN", "DERSĠN"]),                            # Süre/Ders saati (metin olarak)!!
        (["DERSİN AMACI", "AMACI"], ["DERSİN", "DERSĠN"]),                              # Dersin Amacı
        (["DERSİN KAZANIMLARI", "KAZANIMLARI"], ["EĞİTİM", "EĞĠTĠM", "EĞ", "DONAT"]),   # Kazanım -> Madde yapılmalı
        (["DONANIMI"], ["ÖLÇ", "DEĞERLENDİRME"]),                                       # Ortam/Donanım
        (["DEĞERLENDİRME"], ["DERSİN", "DERSĠN", "KAZANIM", "ÖĞRENME"]),                # Ölçme-Değerlendirme
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

def extract_ob_tablosu(pdf_path):
    """PDF'den Öğrenme Birimlerini ve 3 sütunlu tablo yapısını çıkarır"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Normalizasyon
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = normalize_turkish_chars(full_text)
            
            # extract_kazanim_sayisi_sure_tablosu'ndan OB başlıklarını al
            kazanim_result = extract_kazanim_sayisi_sure_tablosu(pdf_path)
            
            if "KAZANIM SAYISI VE SÜRE TABLOSU:" not in kazanim_result:
                return "Öğrenme Birimleri bulunamadı"
            
            # OB başlıklarını parse et
            ob_basliklar = []
            lines = kazanim_result.split('\n')[1:]  # İlk satır başlık
            for line in lines:
                if line.strip() and '-' in line:
                    # Format: "1-Başlık, sayı, sayı, oran"
                    parts = line.split('-', 1)[1].split(',')[0].strip()
                    ob_basliklar.append(parts)
            
            if not ob_basliklar:
                return "Öğrenme Birimi başlıkları parse edilemedi"
            
            # 3 sütunlu tablo başlıklarını sırayla bul
            table_headers = [
                "ÖĞRENME BİRİMİ",
                "KONULAR", 
                "ÖĞRENME BİRİMİ KAZANIMLARI",
                "KAZANIM AÇIKLAMLAARI"
            ]
            
            # Her başlığı regex pattern ile ara
            table_start_idx = None
            last_found_end = 0
            
            for header in table_headers:
                # Başlığı regex pattern'e çevir
                header_pattern = ""
                for char in header:
                    if char.isalnum() or char in "ÇĞİÖŞÜ":
                        header_pattern += char + r"\s*"
                    elif char == " ":
                        header_pattern += r"\s+"
                    else:
                        header_pattern += re.escape(char) + r"\s*"
                header_pattern = header_pattern.rstrip(r"\s*")
                
                # Son bulunan yerden sonra ara
                match = re.search(header_pattern, full_text[last_found_end:], re.IGNORECASE)
                if match:
                    actual_start = last_found_end + match.start()
                    actual_end = last_found_end + match.end()
                    last_found_end = actual_end
                    table_start_idx = actual_end  # Son başlığın bittiği yer
            
            if table_start_idx is None:
                return "Tablo başlıkları bulunamadı"
            
            # Durma kelimelerinden en erken olanını bul (case sensitive)
            stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN"]
            table_end_idx = len(full_text)
            
            for stop_word in stop_words:
                stop_idx = full_text.find(stop_word, table_start_idx)
                if stop_idx != -1 and stop_idx < table_end_idx:
                    table_end_idx = stop_idx
            
            # Regex ile esnek eşleştirme yaklaşımı
            result_content = ""
            current_search_pos = table_start_idx
            
            for i, ob_baslik in enumerate(ob_basliklar):
                # OB başlığını regex pattern'e çevir - her karakterin arasına \s* ekle
                ob_pattern = ""
                for char in ob_baslik.upper():
                    if char.isalnum() or char in "ÇĞİÖŞÜ":
                        ob_pattern += char + r"\s*"
                    elif char == " ":
                        ob_pattern += r"\s+"  # Boşluklar için en az bir boşluk
                    else:
                        ob_pattern += re.escape(char) + r"\s*"
                
                # Son fazla \s* kaldır
                ob_pattern = ob_pattern.rstrip(r"\s*")
                
                # Mevcut pozisyondan itibaren ara (sıralı arama)
                match = re.search(ob_pattern, full_text[current_search_pos:], re.IGNORECASE)
                
                if not match:
                    continue
                
                # Gerçek pozisyonu hesapla
                ob_start_idx = current_search_pos + match.start()
                ob_end_idx = current_search_pos + match.end()
                
                # Bir sonraki OB başlığını bul (bitiş noktası için)
                next_ob_idx = len(full_text)
                if i + 1 < len(ob_basliklar):
                    # Bir sonraki OB için pattern oluştur
                    next_ob_baslik = ob_basliklar[i + 1]
                    next_pattern = ""
                    for char in next_ob_baslik.upper():
                        if char.isalnum() or char in "ÇĞİÖŞÜ":
                            next_pattern += char + r"\s*"
                        elif char == " ":
                            next_pattern += r"\s+"
                        else:
                            next_pattern += re.escape(char) + r"\s*"
                    next_pattern = next_pattern.rstrip(r"\s*")
                    
                    next_match = re.search(next_pattern, full_text[ob_end_idx:], re.IGNORECASE)
                    if next_match:
                        next_ob_idx = ob_end_idx + next_match.start()
                else:
                    # Son OB için durma kelimelerini kontrol et
                    stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN"]
                    for stop_word in stop_words:
                        stop_idx = full_text.find(stop_word, ob_end_idx)
                        if stop_idx != -1 and stop_idx < next_ob_idx:
                            next_ob_idx = stop_idx
                
                # Bu OB'nin içeriğini al
                ob_content_original = full_text[ob_start_idx:next_ob_idx].strip()
                
                result_content += f"\n{'='*50}\n"
                result_content += f"ÖĞRENİM BİRİMİ {i+1}: {ob_baslik}\n"
                result_content += f"{'='*50}\n"
                result_content += ob_content_original + "\n"
                
                # Bir sonraki arama için pozisyonu güncelle (sıralı işlem)
                current_search_pos = next_ob_idx
            
            if result_content:
                return f"ÖĞRENİM BİRİMLERİ TABLOSU:{result_content}"
            else:
                return "Öğrenım Birimleri metinde bulunamadı"
            
    except Exception as e:
        return f"Hata: {str(e)}"

def extract_kazanim_sayisi_sure_tablosu(pdf_path):
    """PDF'den KAZANIM SAYISI VE SÜRE TABLOSU'nu çıkarır ve formatlı string döndürür"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Normalizasyon
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = normalize_turkish_chars(full_text)  # Türkçe karakter düzeltme
            
            # KAZANIM SAYISI VE SÜRE TABLOSU bölümünü bul (varyasyonlarla)
            table_start_patterns = [
                "KAZANIM SAYISI VE SÜRE TABLOSU",
                "DERSİN KAZANIM TABLOSU",
                "TABLOSU",
                "TABLO SU",
                "TAB LOSU"
            ]
            
            # Tüm pattern'leri kontrol et ve en erken başlayanı bul
            earliest_start = None
            earliest_idx = len(full_text)
            table_start = None
            
            for pattern in table_start_patterns:
                if pattern in full_text:
                    idx = full_text.find(pattern)
                    if idx < earliest_idx:
                        earliest_idx = idx
                        earliest_start = idx + len(pattern)
                        table_start = pattern
            
            start_idx = earliest_start
            
            if table_start is None:
                return "KAZANIM SAYISI VE SÜRE TABLOSU bulunamadı"
            
            # Bitiş noktasını bul
            end_markers = ["TOPLAM", "ÖĞRENME BİRİMİ"]
            end_idx = len(full_text)
            for marker in end_markers:
                idx = full_text.find(marker, start_idx + 50)
                if idx != -1 and idx < end_idx:
                    end_idx = idx
            
            table_section = full_text[start_idx:end_idx].strip()
            
            # TOPLAM satırını bul ve sonrasını kes
            if "TOPLAM" in table_section:
                toplam_idx = table_section.find("TOPLAM")
                # TOPLAM'dan sonra sayıları bul ve ondan sonrasını kes
                after_toplam = table_section[toplam_idx:]
                # TOPLAM satırının sonunu bul (genelde 100 ile biter)
                toplam_end = re.search(r'TOPLAM.*?100', after_toplam)
                if toplam_end:
                    table_section = table_section[:toplam_idx + toplam_end.end()]
            
            # Başlık satırını kaldır (ÖĞRENME BİRİMİ KAZANIM SAYISI DERS SAATİ ORAN)
            header_pattern = r'ÖĞRENME BİRİMİ.*?ORAN.*?\(\s*%\s*\)'
            table_section = re.sub(header_pattern, '', table_section).strip()
            
            # Satırları ayır ve parse et
            lines = []
            
            # Her satır: İsim + 2 sayı + 1 sayı veya % pattern'i
            patterns = [
                r'([^0-9]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+)\s+(\d+(?:[,\.]\d+)?)', # Kesirli format + oran
                r'([^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)',             # Normal format + oran
                r'([^0-9]+?)\s+(\d+)\s+(\d+)(?:\s|$)'                           # Sadece 2 sütun (oran yok)
            ]

            matches = []
            for pattern in patterns:
                matches = re.findall(pattern, table_section)
                if matches:
                    break
            
            for match in matches:
                ogrenme_birimi = match[0].strip()
                kazanim_sayisi = match[1]

                # Pattern'e göre ders saati ve oran belirleme
                if len(match) == 3:  # Oran yok
                    ders_saati = match[2]
                    oran = "-"  # Boş oran için
                elif len(match) == 4:  # Normal format
                    ders_saati = match[2]
                    oran = match[3]
                elif len(match) == 5:  # Kesirli format
                    ders_saati = match[3]  # / sonrası sayı
                    oran = match[4]
                
                # Öğrenme birimi adını temizle
                ogrenme_birimi = re.sub(r'\s+', ' ', ogrenme_birimi).strip()
                
                # TOPLAM satırını atla
                if ogrenme_birimi.upper() != "TOPLAM":
                    line = f"{ogrenme_birimi}, {kazanim_sayisi}, {ders_saati}, {oran}"
                    lines.append(line)
            
            if lines:
                result = "KAZANIM SAYISI VE SÜRE TABLOSU:\n"
                for idx, line in enumerate(lines, 1):
                    result += f"{idx}-{line}\n"
                return result.strip()
            else:
                return "Tablo verileri parse edilemedi"
                
    except Exception as e:
        return f"Hata: {str(e)}"

# Yardımcı fonksiyonlar
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

def find_pdf_by_name(filename):
    """data/dbf dizininde dosya adına göre ilk eşleşen PDF'i bulur"""
    base_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf"
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.pdf') and filename.lower() in file.lower():
                return os.path.join(root, file)
    return None

# Debug için full text body verir.
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
        print("Kullanım:")
        print("  python extract_olcme.py <sayı>        # Rastgele N dosya")
        print("  python extract_olcme.py \"dosya_adi\"   # Belirli dosya")
        sys.exit(1)
    
    param = sys.argv[1]
    
    try:
        sample_count = int(param)
        # Sayı ise rastgele seçim
        if sample_count <= 0:
            print("Hata: Sayı parametresi pozitif bir tam sayı olmalıdır.")
            sys.exit(1)
        
        all_pdfs = find_all_pdfs_in_dbf_directory()
        
        if not all_pdfs:
            print("data/dbf dizininde hiç PDF dosyası bulunamadı.")
            sys.exit(1)
           
        # Rastgele örnekleme yap
        if sample_count > len(all_pdfs):
            print(f"Uyarı: İstenen sayı ({sample_count}) toplam dosya sayısından ({len(all_pdfs)}) büyük. Tüm dosyalar işlenecek.")
            selected_pdfs = all_pdfs
        else:
            selected_pdfs = random.sample(all_pdfs, sample_count)
    except ValueError:
        # Dosya adı ise
        found_pdf = find_pdf_by_name(param)
        if found_pdf:
            selected_pdfs = [found_pdf]
            all_pdfs = find_all_pdfs_in_dbf_directory()  # Toplam sayı için
        else:
            print(f"'{param}' adında dosya data/dbf dizininde bulunamadı.")
            sys.exit(1)
    
    print(f"Seçilen {len(selected_pdfs)}/{len(all_pdfs)} dosya işleniyor...\n")
    
    # Her dosyayı işle
    for i, pdf_path in enumerate(selected_pdfs, 1):
        # 1. Dizin ve dosya adı satırı
        print(pdf_path)
        
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

        # Tüm sayfa ekrana yaz.
        print_full_pdf_text(pdf_path)  # tüm PDF metni burada görünür
        
        # Ardından tüm metin üzerinden başlıkları çıkart
        #extracted_fields = extract_fields_from_text(full_text)
        #for key, value in extracted_fields.items():
        #    title = key.split("_", 1)[-1].capitalize()
        #    print(f"\n{title}: {value}")
        #print()

        # KAZANIM SAYISI VE SÜRE TABLOSU
        result1 = extract_kazanim_sayisi_sure_tablosu(pdf_path)
        print(result1)
        print("\n" + "="*80 + "\n")
        
        # ÖĞRENİM BİRİMLERİ TABLOSU
        result2 = extract_ob_tablosu(pdf_path)
        print(result2)
        print("\n" + "="*80 + "\n")
        print(pdf_path)

if __name__ == "__main__":
    main()