import fitz  # PyMuPDF
import re
import os
import sys
import random
import glob
import unicodedata

def ex_temel_bilgiler(text):
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
    
    # Normalize edilmiş metin sadece eşleştirme için
    text_normalized = normalize_turkish_text(text)

    for i, (start_keys, end_keys) in enumerate(patterns, 1):
        start_index = None
        start_match = ""
        start_original_idx = None
        
        for sk in start_keys:
            sk_normalized = normalize_turkish_text(sk)
            idx = text_normalized.find(sk_normalized)
            if idx != -1 and (start_index is None or idx < start_index):
                start_index = idx + len(sk_normalized)
                start_match = sk
                # Orijinal metinde karşılık gelen pozisyonu bul
                start_original_idx = text.upper().find(sk.upper())
                if start_original_idx != -1:
                    start_original_idx += len(sk)
        
        if start_index is None or start_original_idx is None:
            continue
            
        end_index = None
        end_original_idx = None
        
        for ek in end_keys:
            ek_normalized = normalize_turkish_text(ek)
            idx = text_normalized.find(ek_normalized, start_index)
            if idx != -1 and (end_index is None or idx < end_index):
                end_index = idx
                # Orijinal metinde karşılık gelen pozisyonu bul
                end_original_idx = text.upper().find(ek.upper(), start_original_idx)
                
        if end_original_idx is not None:
            section = text[start_original_idx:end_original_idx].strip()
        else:
            section = text[start_original_idx:].strip()
            
        section = re.sub(r'\s+', ' ', section)
        result[f"Case{i}_{start_match}"] = section
    return result

def ex_kazanim_tablosu(full_text):
    """PDF'den KAZANIM SAYISI VE SÜRE TABLOSU'nu çıkarır ve formatlı string ile yapılandırılmış veri döndürür"""
    try:

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
        
        # Türkçe karakterleri normalize ederek ara
        full_text_normalized = normalize_turkish_text(full_text)
        
        earliest_start = None
        earliest_idx = len(full_text_normalized)
        table_start = None
        for pattern in table_start_patterns:
            pattern_normalized = normalize_turkish_text(pattern)
            idx = full_text_normalized.find(pattern_normalized)
            if idx != -1 and idx < earliest_idx:
                earliest_idx = idx
                earliest_start = idx + len(pattern_normalized)
                table_start = pattern
        
        start_idx = earliest_start
        if table_start is None:
            return "KAZANIM SAYISI VE SÜRE TABLOSU bulunamadı", []

        end_markers = ["TOPLAM", "ÖĞRENME BİRİMİ"]
        end_idx = len(full_text_normalized)
        for marker in end_markers:
            marker_normalized = normalize_turkish_text(marker)
            idx = full_text_normalized.find(marker_normalized, start_idx + 50)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        
        # Orijinal metinden section al ama pozisyonları normalize edilmiş metinden bul
        table_section_original = full_text[start_idx:end_idx].strip()
        table_section_normalized = full_text_normalized[start_idx:end_idx].strip()

        toplam_normalized = normalize_turkish_text("TOPLAM")
        if toplam_normalized in table_section_normalized:
            toplam_idx = table_section_normalized.find(toplam_normalized)
            after_toplam = table_section_normalized[toplam_idx:]
            toplam_end = re.search(r'TOPLAM.*?100', after_toplam, re.IGNORECASE)
            if toplam_end:
                table_section_original = table_section_original[:toplam_idx + toplam_end.end()]
                table_section_normalized = table_section_normalized[:toplam_idx + toplam_end.end()]

        # Başlık satırını kaldır (ÖĞRENME BİRİMİ KAZANIM SAYISI DERS SAATİ ORAN) - Normalize edilmiş karakterlerle
        header_patterns = [
            # NORMALIZE EDİLMİŞ KARAKTERLER - table_section_normalized için
            r'OGRENME.*?\(\s*%\s*\)',
            r'OGRENME.*?\(%\)',
            r'OGRENME.*?ORAN.*?\(\s*%\s*\)',
            r'OGRENME.*?ORAN.*?\(%\)',
            r'KAZANIM(?:.|\n)*?ORAN\s*\(\s*%\s*\)',  # geniş eşleşme, tüm başlık bloğunu kaldırır
            r'KAZANIM SAYISI VE\s*SURE TABLOSU\s*OGRENME BIRIMI\s*KAZANIM\s*SAYISI\s*DERS SAATI\s*ORAN\s*\(\s*%\s*\)',  # tam uyumlu eşleşme
            r'OGRENME(?:.|\n)*?ORAN(?:.|\n)*?\(\s*%\s*\)'  # geniş pattern
        ]
        
        for header_pattern in header_patterns:
            new_table_section_normalized = re.sub(header_pattern, '', table_section_normalized, flags=re.IGNORECASE | re.DOTALL).strip()
            if len(new_table_section_normalized) < len(table_section_normalized):
                table_section_normalized = new_table_section_normalized
                # Aynı pattern'i orijinal metne de uygula (Türkçe karakterlerle)
                original_pattern = header_pattern.replace('OGRENME', 'ÖĞRENME').replace('SURE', 'SÜRE').replace('BIRIMI', 'BİRİMİ').replace('SAATI', 'SAATİ')
                table_section_original = re.sub(original_pattern, '', table_section_original, flags=re.IGNORECASE | re.DOTALL).strip()
                break
        
        # Çıktı için orijinal metni kullan (header kaldırılmış hali)
        table_section = table_section_original

        lines = []
        structured_data = []
        
        # Her satır: İsim + sayılar + % pattern'i - Git geçmişinden gelişmiş versiyonlar
        patterns = [
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+)\s+(\d+(?:[,\.]\d+)?)',  # Kesirli format + oran (18/36)
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)',              # Normal format + oran 
            r'([^0-9]+?)\s+(\d+)\s+(\d+)(?:\s|$)',                           # Sadece 2 sütun (oran yok)
            r'([^0-9]+?)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)\s*%?',                 # Yüzde işareti opsiyonel
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)',      # 5 sütun format
            r'([^0-9]+?)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)',                      # Basit 2 sütun format
        ]

        matches = []
        for pattern in patterns:
            # Normalize edilmiş metinde pattern ara ama orijinal metinden değerleri al
            normalized_matches = re.findall(pattern, table_section_normalized)
            if normalized_matches:
                # Orijinal metinde de aynı pattern'i ara
                original_matches = re.findall(pattern, table_section_original)
                if original_matches:
                    matches = original_matches
                    break
        
        for match in matches:
            ogrenme_birimi = re.sub(r'\s+', ' ', match[0].strip()).strip()
            kazanim_sayisi = match[1]
            
            # Gelişmiş pattern matching: 2-6 grup desteği
            if len(match) == 2:
                # Sadece isim + kazanım sayısı
                ders_saati = "-"
                oran = "-"
            elif len(match) == 3:
                # İsim + kazanım + ders saati/oran
                ders_saati = match[2]
                oran = "-"
                # Eğer 3. alan % içeriyorsa oran olabilir
                if '%' in str(match[2]) or ',' in str(match[2]) or '.' in str(match[2]):
                    oran = match[2]
                    ders_saati = "-"
            elif len(match) == 4:
                # İsim + kazanım + ders saati + oran
                ders_saati = match[2]
                oran = match[3]
            elif len(match) == 5:
                # İsim + kazanım + ders saati + kesir + oran veya 5 sütun format
                if '/' in str(match[3]):
                    # Kesirli format: isim + kazanım + ders saati + kesir + oran
                    ders_saati = f"{match[2]}/{match[3]}"
                    oran = match[4]
                else:
                    # 5 sütun format: isim + kazanım + sütun3 + ders saati + oran
                    ders_saati = match[3]
                    oran = match[4]
            elif len(match) == 6:
                # Tam format: isim + kazanım + sütun3 + sütun4 + ders saati + oran
                ders_saati = match[4]
                oran = match[5]
            
            if normalize_turkish_text(ogrenme_birimi) != normalize_turkish_text("TOPLAM"):
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

def extract_ob_tablosu(full_text):
    """PDF'den Öğrenme Birimi Alanını çıkarır - Sadece başlangıç ve bitiş sınırları arasındaki metni"""
    try:

        full_text_normalized_for_search = normalize_turkish_text(full_text)
        toplam_idx = full_text_normalized_for_search.find(normalize_turkish_text("TOPLAM"))
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
            header_normalized = normalize_turkish_text(header)
            idx = full_text_normalized_for_search.find(header_normalized, toplam_idx)
            if idx != -1:
                header_end = idx + len(header_normalized)
                if last_header_end is None or header_end > last_header_end:
                    last_header_end = header_end
                    table_start_idx = header_end
        
        if table_start_idx is None:
            return "Öğrenme Birimi Alanı - Başlangıç kelimeleri bulunamadı"

        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text=full_text)
        
        # İlk başlığın (örn. Programlama Yapıları) gerçek pozisyonunu bul
        if kazanim_tablosu_data:
            first_title = kazanim_tablosu_data[0]['title']
            first_title_normalized = normalize_turkish_text(first_title)
            first_title_idx = full_text_normalized_for_search.find(first_title_normalized, table_start_idx)
            if first_title_idx != -1:
                table_start_idx = first_title_idx

        stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"] #her zaman büyük harf ile eşleşmeli.
        table_end_idx = len(full_text_normalized_for_search)
        search_area = full_text[table_start_idx:].upper()
        for stop_word in stop_words:
            word_pattern = r'\b' + re.escape(stop_word) + r'\b'
            match = re.search(word_pattern, full_text[table_start_idx:])  # case-sensitive, olduğu gibi arar
            if match:
                stop_idx = table_start_idx + match.start()
                if stop_idx < table_end_idx:
                    table_end_idx = stop_idx
        
        ogrenme_birimi_alani = full_text[table_start_idx:table_end_idx].strip()
        ogrenme_birimi_alani = re.sub(r'\s+', ' ', ogrenme_birimi_alani).strip()

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
                    baslik_normalized = normalize_turkish_text(baslik_for_matching)
                    content_normalized = normalize_turkish_text(ogrenme_birimi_alani[start_pos:])
                    string_idx = content_normalized.find(baslik_normalized)
                    if string_idx >= 0:
                        idx = start_pos + string_idx
                    else:
                        break
                    
                    after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
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
                    baslik_normalized = normalize_turkish_text(baslik_for_matching)
                    content_normalized = normalize_turkish_text(ogrenme_birimi_alani[start_pos:])
                    string_idx = content_normalized.find(baslik_normalized)
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
                        baslik_normalized = normalize_turkish_text(baslik_for_matching)
                        content_section = ogrenme_birimi_alani[start_pos:]
                        content_normalized = normalize_turkish_text(content_section)
                        string_idx = content_normalized.find(baslik_normalized)
                        if string_idx >= 0:
                            idx = start_pos + string_idx
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
def komutlar(param=None):
    """
    DBF PDF ve DOCX dosyalarını bulma ve yönetme fonksiyonu
    
    Args:
        param (str/int/None): 
            - None: Tüm dosyaları listele
            - int: Rastgele N dosya seç
            - str: İsme göre dosya ara
    
    Returns:
        list: PDF ve DOCX dosya yolları listesi
    """
    base_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf"
    
    # Tüm PDF ve DOCX dosyalarını bul
    all_files = []
    supported_extensions = ('.pdf', '.docx')
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(supported_extensions):
                all_files.append(os.path.join(root, file))
    
    # Parametre yoksa tüm dosyaları döndür
    if param is None:
        return all_files
    
    # Sayı ise rastgele seçim yap
    if isinstance(param, int) or (isinstance(param, str) and param.isdigit()):
        sample_count = int(param)
        if sample_count <= 0:
            return []
        if sample_count >= len(all_files):
            return all_files
        import random
        return random.sample(all_files, sample_count)
    
    # String ise isim arama yap
    if isinstance(param, str):
        matching_files = []
        for file_path in all_files:
            filename = os.path.basename(file_path)
            if param.lower() in filename.lower():
                matching_files.append(file_path)
        return matching_files
    
    return all_files

def normalize_turkish_text(text):
    """Türkçe karakterleri normalize eder ve case-insensitive karşılaştırma için hazırlar"""
    if not text:
        return ""
    
    # Türkçe karakterleri ASCII'ye dönüştür ve büyük harfe çevir
    # İ -> I, i -> i, ğ -> g, ü -> u, ş -> s, ö -> o, ç -> c
    char_map = {
        'İ': 'I', 
        'ı': 'i', 
        'Ğ': 'G', 
        'ğ': 'g',
        'Ü': 'U', 
        'ü': 'u', 
        'Ş': 'S', 
        'ş': 's', 
        'Ö': 'O', 
        'ö': 'o', 
        'Ç': 'C', 
        'ç': 'c'
    }
    
    # Karakterleri değiştir
    normalized = text
    for turkish_char, ascii_char in char_map.items():
        normalized = normalized.replace(turkish_char, ascii_char)
    
    # Büyük harfe çevir ve whitespace normalize et
    normalized = re.sub(r'\s+', ' ', normalized.upper().strip())
    
    return normalized

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
        
        all_files = komutlar()
        
        if not all_files:
            print("data/dbf dizininde hiç PDF/DOCX dosyası bulunamadı.")
            sys.exit(1)
           
        # Rastgele örnekleme yap
        selected_files = komutlar(sample_count)
        if len(selected_files) < sample_count:
            print(f"Uyarı: İstenen sayı ({sample_count}) toplam dosya sayısından ({len(all_files)}) büyük. {len(selected_files)} dosya işlenecek.")
    except ValueError:
        # Dosya adı ise
        selected_files = komutlar(param)
        if selected_files:
            all_files = komutlar()  # Toplam sayı için
        else:
            print(f"'{param}' adında dosya data/dbf dizininde bulunamadı.")
            sys.exit(1)
    
    print(f"Seçilen {len(selected_files)}/{len(all_files)} dosya işleniyor...\n")
    
    # Her dosyayı işle
    for i, file_path in enumerate(selected_files, 1):
        # 1. Dizin ve dosya adı satırı
        print(file_path)
        
        # 2. Çizgi
        print("-" * 80)

        # Dosyadan tüm metni alalım (PDF veya DOCX)
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # normalize et
        full_text = re.sub(r'\s+', ' ', full_text)

        # Tüm sayfa ekrana yaz.
        #print(full_text)
        
        # Ardından tüm metin üzerinden başlıkları çıkart
        #extracted_fields = ex_temel_bilgiler(full_text)
        #for key, value in extracted_fields.items():
        #    title = key.split("_", 1)[-1].capitalize()
        #    print(f"\n{title}: {value}")
        #print()

        # KAZANIM SAYISI VE SÜRE TABLOSU
        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text=full_text)
        print(kazanim_tablosu_str)
        
        # ÖĞRENİM BİRİMLERİ TABLOSU
        result2 = extract_ob_tablosu(full_text=full_text)
        print(result2)
        print("-"*80)
        print(file_path)

if __name__ == "__main__":
    main()