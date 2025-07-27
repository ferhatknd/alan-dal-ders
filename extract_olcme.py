import fitz  # PyMuPDF
import re
import os
import sys
import random
import glob

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

def extract_kazanim_sayisi_sure_tablosu(pdf_path):
    """PDF'den KAZANIM SAYISI VE SÜRE TABLOSU'nu çıkarır ve formatlı string ile yapılandırılmış veri döndürür"""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        full_text = re.sub(r'\s+', ' ', full_text)

        table_start_patterns = [
            "KAZANIM SAYISI VE SÜRE TABLOSU", "DERSİN KAZANIM TABLOSU", "TABLOSU",
            "TABLOS U", "TABLO SU", "TABL OSU", "TAB LOSU", "TA BLOSU"
        ]
        
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
            return "KAZANIM SAYISI VE SÜRE TABLOSU bulunamadı", []

        end_markers = ["TOPLAM", "ÖĞRENME BİRİMİ"]
        end_idx = len(full_text)
        for marker in end_markers:
            idx = full_text.find(marker, start_idx + 50)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        
        table_section = full_text[start_idx:end_idx].strip()

        if "TOPLAM" in table_section:
            toplam_idx = table_section.find("TOPLAM")
            after_toplam = table_section[toplam_idx:]
            toplam_end = re.search(r'TOPLAM.*?100', after_toplam)
            if toplam_end:
                table_section = table_section[:toplam_idx + toplam_end.end()]

        header_pattern = r'ÖĞRENME BİRİMİ.*?ORAN.*?\(\s*%\s*\)' 
        table_section = re.sub(header_pattern, '', table_section).strip()

        lines = []
        structured_data = []
        
        patterns = [
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+)\s+(\d+(?:[,.]\d+)?)',
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+(?:[,.]\d+)?)',
            r'([^0-9]+?)\s+(\d+)\s+(\d+)(?:\s|$)'
        ]

        matches = []
        for pattern in patterns:
            matches = re.findall(pattern, table_section)
            if matches:
                break
        
        for match in matches:
            ogrenme_birimi = re.sub(r'\s+', ' ', match[0].strip()).strip()
            kazanim_sayisi = match[1]

            if len(match) == 3:
                ders_saati = match[2]
                oran = "-"
            elif len(match) == 4:
                ders_saati = match[2]
                oran = match[3]
            elif len(match) == 5:
                ders_saati = match[3]
                oran = match[4]
            
            if ogrenme_birimi.upper() != "TOPLAM":
                lines.append(f"{ogrenme_birimi}, {kazanim_sayisi}, {ders_saati}, {oran}")
                structured_data.append({
                    'title': ogrenme_birimi,
                    'count': int(kazanim_sayisi),
                    'duration': ders_saati,
                    'percentage': oran
                })
        
        if lines:
            result = "KAZANIM SAYISI VE SÜRE TABLOSU:\n"
            for idx, line in enumerate(lines, 1):
                result += f"{idx}-{line}\n"
            return result.strip(), structured_data
        else:
            return "Tablo verileri parse edilemedi", []
                
    except Exception as e:
        return f"Hata: {str(e)}", []

def extract_ob_tablosu(pdf_path):
    """PDF'den Öğrenme Birimi Alanını çıkarır - Sadece başlangıç ve bitiş sınırları arasındaki metni"""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        full_text = re.sub(r'\s+', ' ', full_text)

        toplam_idx = full_text.upper().find("TOPLAM")
        if toplam_idx == -1:
            # Backup plan for TOPLAM
            pass

        table_headers = [
            "ÖĞRENME BİRİMİ", "KONULAR", "ÖĞRENME BİRİMİ KAZANIMLARI",
            "KAZANIM AÇIKLAMLARI", "AÇIKLAMALARI"
        ]
        table_start_idx = None
        last_header_end = None
        for header in table_headers:
            idx = full_text.find(header, toplam_idx)
            if idx != -1:
                header_end = idx + len(header)
                if last_header_end is None or header_end > last_header_end:
                    last_header_end = header_end
                    table_start_idx = header_end
        
        if table_start_idx is None:
            return "Öğrenme Birimi Alanı - Başlangıç kelimeleri bulunamadı"

        stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
        table_end_idx = len(full_text)
        for stop_word in stop_words:
            stop_idx = full_text.find(stop_word, table_start_idx)
            if stop_idx != -1 and stop_idx < table_end_idx:
                table_end_idx = stop_idx
        
        ogrenme_birimi_alani = full_text[table_start_idx:table_end_idx].strip()
        ogrenme_birimi_alani = re.sub(r'\s+', ' ', ogrenme_birimi_alani).strip()

        kazanim_tablosu_str, kazanim_tablosu_data = extract_kazanim_sayisi_sure_tablosu(pdf_path)

        header_match_info = ""
        formatted_content = ""

        if kazanim_tablosu_data:
            header_match_info = "\n"
            formatted_content_parts = []
            all_matched_headers = []

            for item in kazanim_tablosu_data:
                baslik = item['title']
                konu_sayisi_int = item['count']
                baslik_for_matching = re.sub(r'\s+', ' ', baslik.strip())
                
                start_pos = 0
                while True:
                    baslik_upper = baslik_for_matching.upper()
                    content_upper = ogrenme_birimi_alani[start_pos:].upper()
                    string_idx = content_upper.find(baslik_upper)
                    if string_idx >= 0:
                        idx = start_pos + string_idx
                    else:
                        break
                    
                    after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                    if konu_sayisi_int > 0:
                        found_numbers = 0
                        for rakam in range(1, konu_sayisi_int + 1):
                            if str(rakam) in after_baslik[:1500]:
                                found_numbers += 1
                        
                        if found_numbers == konu_sayisi_int:
                            all_matched_headers.append({
                                'title': baslik,
                                'position': idx,
                                'konu_sayisi': konu_sayisi_int
                            })
                            break
                    start_pos = idx + 1

            for i, item in enumerate(kazanim_tablosu_data, 1):
                baslik = item['title']
                konu_sayisi_int = item['count']
                baslik_for_display = baslik
                baslik_for_matching = re.sub(r'\s+', ' ', baslik.strip())
                konu_sayisi_str = str(konu_sayisi_int)

                gecerli_eslesme = 0
                start_pos = 0
                while True:
                    baslik_upper = baslik_for_matching.upper()
                    content_upper = ogrenme_birimi_alani[start_pos:].upper()
                    string_idx = content_upper.find(baslik_upper)
                    if string_idx >= 0:
                        idx = start_pos + string_idx
                    else:
                        break
                    
                    after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                    if konu_sayisi_int > 0:
                        found_numbers = 0
                        for rakam in range(1, konu_sayisi_int + 1):
                            if str(rakam) in after_baslik[:1500]:
                                found_numbers += 1
                        if found_numbers == konu_sayisi_int:
                            gecerli_eslesme += 1
                    start_pos = idx + 1
                
                header_match_info += f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> {gecerli_eslesme} eşleşme\n"

                if gecerli_eslesme == 0 and konu_sayisi_int > 0:
                    alternative_match = extract_ob_tablosu_konu_bulma_yedek_plan(
                        ogrenme_birimi_alani, baslik_for_matching, konu_sayisi_int
                    )
                    if alternative_match:
                        gecerli_eslesme = 1
                        header_match_info = header_match_info.replace(
                            f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> 0 eşleşme\n",
                            f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> 1 eşleşme (alternatif)\n"
                        )

                if gecerli_eslesme > 0:
                    start_pos = 0
                    first_valid_match_found = False
                    while True:
                        baslik_normalized = re.sub(r'\s+', ' ', baslik_for_matching.strip().upper())
                        content_section = ogrenme_birimi_alani[start_pos:]
                        content_normalized = re.sub(r'\s+', ' ', content_section.strip().upper())
                        string_idx = content_normalized.find(baslik_normalized)
                        if string_idx >= 0:
                            idx = start_pos + content_section.upper().find(baslik_for_matching.upper())
                        else:
                            break
                        
                        after_baslik = ogrenme_birimi_alani[idx + len(baslik_for_matching):]
                        is_valid_match = True
                        if konu_sayisi_int > 0:
                            found_numbers = 0
                            for rakam in range(1, konu_sayisi_int + 1):
                                patterns = [f"{rakam}. ", f"{rakam} "]
                                pattern_found = False
                                for pattern in patterns:
                                    if pattern in after_baslik[:1500]:
                                        pattern_found = True
                                        break
                                if pattern_found:
                                    found_numbers += 1
                            is_valid_match = (found_numbers == konu_sayisi_int)
                        
                        if is_valid_match and not first_valid_match_found:
                            first_valid_match_found = True
                            validation_result = extract_ob_tablosu_konu_sinirli_arama(
                                ogrenme_birimi_alani, idx, baslik_for_matching, konu_sayisi_int, all_matched_headers
                            )
                            formatted_content_parts.append(
                                f"{i}-{baslik_for_display} ({konu_sayisi_int}) -> 1. Eşleşme\n"
                                f"{validation_result}\n"
                            )
                            break
                        start_pos = idx + 1
            
            if formatted_content_parts:
                formatted_content = "\n".join(formatted_content_parts)
            else:
                if len(ogrenme_birimi_alani) <= 400:
                    formatted_content = ogrenme_birimi_alani
                else:
                    formatted_content = f"{ogrenme_birimi_alani[:200]}\n...\n{ogrenme_birimi_alani[-200:]}"
        else:
            if len(ogrenme_birimi_alani) <= 400:
                formatted_content = ogrenme_birimi_alani
            else:
                formatted_content = f"{ogrenme_birimi_alani[:200]}\n...\n{ogrenme_birimi_alani[-200:]}"

        result = f"{'--'*25}\nÖğrenme Birimi Alanı:{header_match_info}{'--'*25}\n{formatted_content}"
        return result
            
    except Exception as e:
        return f"Hata: {str(e)}"

def extract_ob_tablosu_konu_sinirli_arama(text, baslik_idx, baslik, konu_sayisi, all_matched_headers=None):
    """Başlık eşleşmesinden sonra konu yapısını sıralı rakamlarla doğrular - 2 döngü"""
    import re
    
    # Başlık eşleşmesinden sonraki tüm metni al
    after_baslik = text[baslik_idx + len(baslik):]
    
    # Sonraki eşleşen başlığın pozisyonunu bul (eğer varsa)
    next_matched_header_pos = len(after_baslik)
    
    if all_matched_headers:
        current_pos_in_text = baslik_idx + len(baslik)
        
        for other_header_info in all_matched_headers:
            other_pos = other_header_info.get('position', -1)
            # Bu başlıktan sonra gelen eşleşen başlıkları ara
            if other_pos > current_pos_in_text:
                relative_pos = other_pos - current_pos_in_text
                if relative_pos < next_matched_header_pos:
                    next_matched_header_pos = relative_pos
    
    # Eğer sonraki eşleşen başlık yoksa, genel pattern'leri ara
    if next_matched_header_pos == len(after_baslik):
        next_header_patterns = [
            r'\n[A-ZÜĞIŞÖÇ][A-ZÜĞIŞÖÇ\s]{10,}',
            r'\n\d+\.\s*[A-ZÜĞIŞÖÇ]', 
            r'DERSİN|DERSĠN',
            r'UYGULAMA|FAALİYET|TEMRİN'
        ]
        
        for pattern in next_header_patterns:
            match = re.search(pattern, after_baslik)
            if match and match.start() < next_matched_header_pos:
                next_matched_header_pos = match.start()
    
    work_area = after_baslik[:next_matched_header_pos]
    validation_info = []
    
    # TEK DÖNGÜ ÇALISTIR
    current_pos = 0
    for konu_no in range(1, konu_sayisi + 1):
        konu_str = str(konu_no)
        
        # Madde numarası pattern'lerini dene: "1. " veya "1 "
        patterns = [f"{konu_str}. ", f"{konu_str} "]
        found_pos = -1
        for pattern in patterns:
            pos = work_area.find(pattern, current_pos)
            if pos != -1:
                found_pos = pos
                break
        
        if found_pos != -1:
            # Sonraki rakama kadar olan metni al
            if konu_no < konu_sayisi:
                next_konu_str = str(konu_no + 1)
                # Sonraki madde numarasını da pattern ile ara
                next_patterns = [f"{next_konu_str}. ", f"{next_konu_str} "]
                next_found_pos = -1
                for next_pattern in next_patterns:
                    pos = work_area.find(next_pattern, found_pos + 1)
                    if pos != -1:
                        next_found_pos = pos
                        break
                if next_found_pos != -1:
                    konu_content = work_area[found_pos:next_found_pos].strip()
                else:
                    konu_content = work_area[found_pos:].strip()
            else:
                konu_content = work_area[found_pos:].strip()
            
            # Sadece gerçek konu numarasını temizle (tarihleri koruyarak)
            cleaned_content = konu_content.strip()
            
            # Pattern ile bulduğumuz madde numarasını temizle
            if cleaned_content.startswith(f"{konu_no}. "):
                cleaned_content = cleaned_content.replace(f"{konu_no}. ", "", 1)
            elif cleaned_content.startswith(f"{konu_no} "):
                cleaned_content = cleaned_content.replace(f"{konu_no} ", "", 1)
            
            validation_info.append(f"{konu_no}. {cleaned_content.strip()}")
            current_pos = found_pos + 1
        else:
            current_pos += 1
    
    return "\n".join(validation_info)

def extract_ob_tablosu_konu_bulma_yedek_plan(text, original_baslik, konu_sayisi):
    """Son eşleşen başlıktan sonra '1' rakamını bulup alternatif eşleşme arar"""
    import re
    
    # "1" rakamını ara (cümle başında veya nokta sonrası)
    one_pattern = r'(?:^|\.|\\n|\\s)1(?:\.|\\s)'
    matches = list(re.finditer(one_pattern, text))
    
    if not matches:
        return None
    
    # Her "1" pozisyonu için kontrol et
    for match in matches:
        one_pos = match.start()
        
        # "1" den önceki cümleyi bul (maksimum 100 karakter geriye git)
        start_search = max(0, one_pos - 100)
        before_one = text[start_search:one_pos]
        
        # Cümle başlangıcını bul (büyük harf ile başlayan kelimeler)
        sentences = re.split(r'[.!?]', before_one)
        if sentences:
            potential_title = sentences[-1].strip()
            
            # Potansiyel başlık çok kısaysa atla
            if len(potential_title) < 10:
                continue
                
            # "1" den sonra konu sayısı kadar rakamı kontrol et
            after_one = text[one_pos:]
            found_numbers = 0
            for rakam in range(1, konu_sayisi + 1):
                if str(rakam) in after_one[:500]:  # İlk 500 karakterde ara
                    found_numbers += 1
            
            # Tüm rakamlar bulunduysa alternatif eşleşme geçerli
            if found_numbers == konu_sayisi:
                return {
                    'title': potential_title,
                    'position': one_pos,
                    'numbers_found': found_numbers
                }
    
    return None

## Yardımcı fonksiyonlar ##
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
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
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
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # normalize et
        full_text = re.sub(r'\s+', ' ', full_text)

        # Tüm sayfa ekrana yaz.
        # print(full_text)
        
        # Ardından tüm metin üzerinden başlıkları çıkart
        extracted_fields = extract_fields_from_text(full_text)
        for key, value in extracted_fields.items():
            title = key.split("_", 1)[-1].capitalize()
            print(f"\n{title}: {value}")
        print()

        # KAZANIM SAYISI VE SÜRE TABLOSU
        result1 = extract_kazanim_sayisi_sure_tablosu(pdf_path)
        print(result1)
        
        # ÖĞRENİM BİRİMLERİ TABLOSU
        result2 = extract_ob_tablosu(pdf_path)
        print(result2)
        print("-"*80)
        print(pdf_path)

if __name__ == "__main__":
    main()