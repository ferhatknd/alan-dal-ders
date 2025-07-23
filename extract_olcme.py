import PyPDF2
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
                "TABLOS U",
                "TABLO SU",
                "TABL OSU",
                "TAB LOSU",
                "TA BLOSU"
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

def extract_ob_tablosu(pdf_path):
    """PDF'den Öğrenme Birimi Alanını çıkarır - Sadece başlangıç ve bitiş sınırları arasındaki metni"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Normalizasyon
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = normalize_turkish_chars(full_text)
            
            # BERT-based Turkish text correction
            try:
                from modules.nlp_bert import correct_turkish_text_with_bert
                full_text = correct_turkish_text_with_bert(full_text)
            except ImportError:
                print("Warning: BERT text correction module not available. Using original text.")
            
            # TOPLAM metnini bul (ana başlangıç noktası) - case insensitive
            toplam_idx = full_text.upper().find("TOPLAM")
            
            if toplam_idx == -1:
                return "Öğrenme Birimi Alanı - TOPLAM metni bulunamadı"
            
            # TOPLAM'dan sonra başlangıç kelimeleri ara
            table_headers = [
                "ÖĞRENME BİRİMİ",
                "KONULAR", 
                "ÖĞRENME BİRİMİ KAZANIMLARI",
                "KAZANIM AÇIKLAMLARI",
                "AÇIKLAMALARI"
            ]
            
            # TOPLAM'dan sonra başlangıç pozisyonunu bul (en son bulunan başlığın sonundan itibaren)
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
            
            # Bitiş kelimeleri - herhangi birini bulduğunda bitir
            stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
            table_end_idx = len(full_text)
            
            for stop_word in stop_words:
                stop_idx = full_text.find(stop_word, table_start_idx)
                if stop_idx != -1 and stop_idx < table_end_idx:
                    table_end_idx = stop_idx
            
            # Belirlenen alan içindeki metni al
            ogrenme_birimi_alani = full_text[table_start_idx:table_end_idx].strip()
            
            # Kazanım tablosundaki başlıkları çıkar ve eşleşme sayısını bul
            kazanim_tablosu_result = extract_kazanim_sayisi_sure_tablosu(pdf_path)
            header_match_info = ""
            formatted_content = ""
            
            if "KAZANIM SAYISI VE SÜRE TABLOSU:" in kazanim_tablosu_result:
                # Tablo satırlarını al
                lines = kazanim_tablosu_result.split('\n')[1:]  # İlk satır başlık, onu atla
                
                header_match_info = "\n"
                formatted_content_parts = []
                all_matched_headers = []  # Tüm eşleşen başlıkların pozisyon bilgileri
                
                # Önce tüm eşleşen başlıkları topla
                for line in lines:
                    if line.strip() and '-' in line:
                        parts = line.split('-', 1)[1].split(',')
                        if parts:
                            baslik = parts[0].strip()
                            try:
                                konu_sayisi_int = int(parts[1].strip())
                            except (ValueError, IndexError):
                                konu_sayisi_int = 0
                            
                            # Bu başlığın geçerli eşleşmelerini bul - Doğrudan semantic matching
                            start_pos = 0
                            
                            while True:
                                # Use semantic matching directly
                                semantic_idx = semantic_find(baslik, ogrenme_birimi_alani[start_pos:], threshold=70)
                                if semantic_idx >= 0:
                                    idx = start_pos + semantic_idx
                                else:
                                    break
                                
                                after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                                if konu_sayisi_int > 0:
                                    found_numbers = 0
                                    for rakam in range(1, konu_sayisi_int + 1):
                                        if str(rakam) in after_baslik[:500]:
                                            found_numbers += 1
                                    
                                    if found_numbers == konu_sayisi_int:
                                        all_matched_headers.append({
                                            'title': baslik,
                                            'position': idx,
                                            'konu_sayisi': konu_sayisi_int
                                        })
                                        break  # İlk geçerli eşleşmeyi bulduk
                                
                                start_pos = idx + 1
                
                # Şimdi başlıkları tekrar işle, bu sefer pozisyon bilgilerini kullanarak
                for line in lines:
                    if line.strip() and '-' in line:
                        # Satır formatı: "1-Başlık, kazanim_sayisi, ders_saati, oran"
                        parts = line.split('-', 1)[1].split(',')
                        if parts:
                            baslik = parts[0].strip()
                            # Konu sayısını al
                            konu_sayisi_str = parts[1].strip() if len(parts) > 1 else "?"
                            
                            # Geçerli eşleşmeleri kontrol et
                            try:
                                konu_sayisi_int = int(konu_sayisi_str)
                            except ValueError:
                                konu_sayisi_int = 0
                            
                            gecerli_eslesme = 0
                            
                            # Her potansiyel eşleşmeyi kontrol et - Doğrudan semantic matching
                            start_pos = 0
                            while True:
                                # Use semantic matching directly
                                semantic_idx = semantic_find(baslik, ogrenme_birimi_alani[start_pos:], threshold=70)
                                if semantic_idx >= 0:
                                    idx = start_pos + semantic_idx
                                else:
                                    break
                                
                                # Başlıktan sonraki metni al
                                after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                                
                                # Konu sayısı kadar rakamı kontrol et
                                if konu_sayisi_int > 0:
                                    found_numbers = 0
                                    for rakam in range(1, konu_sayisi_int + 1):
                                        if str(rakam) in after_baslik[:500]:  # İlk 500 karakterde ara
                                            found_numbers += 1
                                    
                                    # Tüm rakamlar bulunduysa geçerli eşleşme
                                    if found_numbers == konu_sayisi_int:
                                        gecerli_eslesme += 1
                                
                                start_pos = idx + 1
                            
                            header_match_info += f"{baslik}: {konu_sayisi_str} Konu -> {gecerli_eslesme} eşleşme\n"
                            
                            # Eğer geçerli eşleşme yoksa alternatif arama yap
                            if gecerli_eslesme == 0 and konu_sayisi_int > 0:
                                # Son eşleşen başlıktan sonra "1" rakamını ara
                                alternative_match = extract_ob_tablosu_konu_bulma_yedek_plan(
                                    ogrenme_birimi_alani, baslik, konu_sayisi_int
                                )
                                if alternative_match:
                                    gecerli_eslesme = 1
                                    header_match_info = header_match_info.replace(
                                        f"{baslik}: {konu_sayisi_str} Konu -> 0 eşleşme\n",
                                        f"{baslik}: {konu_sayisi_str} Konu -> 1 eşleşme (alternatif)\n"
                                    )
                            
                            # Geçerli eşleşme varsa, detaylı doğrulama yap
                            if gecerli_eslesme > 0:
                                # Kazanım tablosundan konu sayısını al
                                konu_sayisi = None
                                if len(parts) > 1:
                                    try:
                                        konu_sayisi = int(parts[1].strip())
                                    except ValueError:
                                        konu_sayisi = None
                                
                                # İlk geçerli eşleşmeyi bul - Doğrudan semantic matching
                                start_pos = 0
                                first_valid_match_found = False
                                
                                while True:
                                    # Use semantic matching directly
                                    semantic_idx = semantic_find(baslik, ogrenme_birimi_alani[start_pos:], threshold=70)
                                    if semantic_idx >= 0:
                                        idx = start_pos + semantic_idx
                                    else:
                                        break
                                    
                                    # Başlıktan sonraki metni al ve geçerlilik kontrol et
                                    after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                                    
                                    # Konu sayısı kadar rakamı kontrol et
                                    is_valid_match = True
                                    if konu_sayisi and konu_sayisi > 0:
                                        found_numbers = 0
                                        for rakam in range(1, konu_sayisi + 1):
                                            if str(rakam) in after_baslik[:500]:  # İlk 500 karakterde ara
                                                found_numbers += 1
                                        is_valid_match = (found_numbers == konu_sayisi)
                                    
                                    # Sadece ilk geçerli eşleşmeyi işle
                                    if is_valid_match and not first_valid_match_found:
                                        first_valid_match_found = True
                                        
                                        # Detaylı doğrulama yap
                                        validation_result = ""
                                        if konu_sayisi:
                                            validation_result = extract_ob_tablosu_konu_sinirli_arama(
                                                ogrenme_birimi_alani, idx, baslik, konu_sayisi, all_matched_headers
                                            )
                                        
                                        formatted_content_parts.append(
                                            f"{baslik} -> 1. Eşleşme\n"
                                            f"{validation_result}\n"
                                        )
                                        break  # İlk geçerli eşleşmeyi bulduk, çık
                                    
                                    start_pos = idx + 1
                
                # Eğer eşleşmeler varsa onları göster, yoksa eski formatı kullan
                if formatted_content_parts:
                    formatted_content = "\n".join(formatted_content_parts)
                else:
                    # Hiç eşleşme yoksa eski formatı kullan
                    if len(ogrenme_birimi_alani) <= 400:
                        formatted_content = ogrenme_birimi_alani
                    else:
                        first_200 = ogrenme_birimi_alani[:200]
                        last_200 = ogrenme_birimi_alani[-200:]
                        formatted_content = f"{first_200}\n...\n{last_200}"
            else:
                # Kazanım tablosu bulunamadıysa eski formatı kullan
                if len(ogrenme_birimi_alani) <= 400:
                    formatted_content = ogrenme_birimi_alani
                else:
                    first_200 = ogrenme_birimi_alani[:200]
                    last_200 = ogrenme_birimi_alani[-200:]
                    formatted_content = f"{first_200}\n...\n{last_200}"
            
            return f"{'-'*50}\nÖğrenme Birimi Alanı:{header_match_info}{'-'*50}\n{formatted_content}"
            
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

# modules.nlp_bert çalışmaz ise basit büyük/küçük harf arama yapar.
def semantic_find(needle, haystack, threshold=70):
    """Semantic similarity ile string arama yapar - BERT tabanlı"""
    try:
        from modules.nlp_bert import semantic_find as bert_semantic_find
        return bert_semantic_find(needle, haystack, threshold / 100.0)
    except ImportError:
        # Fallback to simple case-insensitive search if BERT not available
        needle_norm = needle.upper()
        haystack_norm = haystack.upper()
        return haystack_norm.find(needle_norm)

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
        #print_full_pdf_text(pdf_path)  # tüm PDF metni burada görünür
        
        # Ardından tüm metin üzerinden başlıkları çıkart
        #extracted_fields = extract_fields_from_text(full_text)
        #for key, value in extracted_fields.items():
        #    title = key.split("_", 1)[-1].capitalize()
        #    print(f"\n{title}: {value}")
        #print()

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