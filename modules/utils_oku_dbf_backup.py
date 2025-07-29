"""
modules/utils_oku_dbf.py
========================
Bu modül extract_olcme.py'den kopyalanan stabil DBF okuma fonksiyonlarını içerir.
"""

import fitz  # PyMuPDF
import re
import os
import glob
import unicodedata

def ex_temel_bilgiler(text):
    """
    extract_olcme.py'den kopyalandi - DBF'den temel ders bilgilerini cikarir
    
    Args:
        text (str): PDF/DOCX'den çıkarılan tam metin
        
    Returns:
        dict: Temel ders bilgileri
    """
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
    """full_text'ten KAZANIM SAYISI VE SÜRE TABLOSU'nu çıkarır ve formatlı string ile yapılandırılmış veri döndürür"""
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
            r'KAZANIM(?:.|\\n)*?ORAN\s*\(\s*%\s*\)',  # geniş eşleşme, tüm başlık bloğunu kaldırır
            r'KAZANIM SAYISI VE\s*SURE TABLOSU\s*OGRENME BIRIMI\s*KAZANIM\s*SAYISI\s*DERS SAATI\s*ORAN\s*\(\s*%\s*\)',  # tam uyumlu eşleşme
            r'OGRENME(?:.|\\n)*?ORAN(?:.|\\n)*?\(\s*%\s*\)'  # geniş pattern
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
            result = "KAZANIM SAYISI VE SÜRE TABLOSU:\\n"
            for idx, line in enumerate(lines, 1):
                result += f"{idx}-{line}\\n"
            return result.strip(), structured_data
        else:
            return "KAZANIM SAYISI VE SÜRE TABLOSU - Veri bulunamadı", []
                
    except Exception as e:
        return f"KAZANIM SAYISI VE SÜRE TABLOSU - HATA: {str(e)}", []

def ex_ob_tablosu(full_text):
    """
    extract_olcme.py'den kopyalandi - PDF'den Öğrenme Birimi Alanını çıkarır - Sadece başlangıç ve bitiş sınırları arasındaki metni
    
    Args:
        full_text (str): PDF/DOCX'den çıkarılan tam metin
        
    Returns:
        tuple: (öğrenme_birimi_analiz_sonucu_string, structured_konu_data)
    """
    try:

        full_text_normalized_for_search = normalize_turkish_text(full_text)
        toplam_idx = full_text_normalized_for_search.find(normalize_turkish_text("TOPLAM"))
        if toplam_idx == -1:
            # Backup plan for TOPLAM
            pass

        table_headers = [
            "ÖĞRENME BİRİMİ", "KONULAR", "ÖĞRENME BİRİMİ KAZANIMLARI",
            "KAZANIM AÇIKLAMLARI", "AÇIKLAMALARI", "ÖĞRENME BİRİMİ/ÜNİTE"
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
            word_pattern = r'\\b' + re.escape(stop_word) + r'\\b'
            match = re.search(word_pattern, full_text[table_start_idx:])  # case-sensitive, olduğu gibi arar
            if match:
                stop_idx = table_start_idx + match.start()
                if stop_idx < table_end_idx:
                    table_end_idx = stop_idx
        
        ogrenme_birimi_alani = full_text[table_start_idx:table_end_idx].strip()
        ogrenme_birimi_alani = re.sub(r'\s+', ' ', ogrenme_birimi_alani).strip()

        header_match_info = ""
        formatted_content = ""
        structured_konu_data = []  # YENİ: Structured data için

        if kazanim_tablosu_data:
            header_match_info = "\\n"
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
                                pos = after_baslik[:1500].find(pattern)
                                if pos != -1:
                                    # Context-aware validation: gerçek madde başlığı mı?
                                    if is_valid_madde_baslik(after_baslik[:1500], pos, rakam):
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
                            patterns = [f"{rakam}. ", f"{rakam} "]
                            pattern_found = False
                            for pattern in patterns:
                                pos = after_baslik[:1500].find(pattern)
                                if pos != -1:
                                    # Context-aware validation: gerçek madde başlığı mı?
                                    if is_valid_madde_baslik(after_baslik[:1500], pos, rakam):
                                        pattern_found = True
                                        break
                            if pattern_found:
                                found_numbers += 1
                        if found_numbers == konu_sayisi_int:
                            gecerli_eslesme += 1
                    start_pos = idx + 1
                
                header_match_info += f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> {gecerli_eslesme} eşleşme\\n"

                if gecerli_eslesme == 0 and konu_sayisi_int > 0:
                    alternative_match = ex_ob_tablosu_konu_bulma_yedek_plan(
                        ogrenme_birimi_alani, baslik_for_matching, konu_sayisi_int
                    )
                    if alternative_match:
                        gecerli_eslesme = 1
                        header_match_info = header_match_info.replace(
                            f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> 0 eşleşme\\n",
                            f"{i}-{baslik_for_display} ({konu_sayisi_str}) -> 1 eşleşme (alternatif)\\n"
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
                                    pos = after_baslik[:1500].find(pattern)
                                    if pos != -1:
                                        # Context-aware validation: gerçek madde başlığı mı?
                                        if is_valid_madde_baslik(after_baslik[:1500], pos, rakam):
                                            pattern_found = True
                                            break
                                if pattern_found:
                                    found_numbers += 1
                            is_valid_match = (found_numbers == konu_sayisi_int)
                        
                        if is_valid_match and not first_valid_match_found:
                            first_valid_match_found = True
                            validation_result, konu_listesi = ex_ob_tablosu_konu_sinirli_arama(
                                ogrenme_birimi_alani, idx, baslik_for_matching, konu_sayisi_int, all_matched_headers
                            )
                            formatted_content_parts.append(
                                f"{i}-{baslik_for_display} ({konu_sayisi_int}) -> 1. Eşleşme\\n"
                                f"{validation_result}\\n"
                            )
                            
                            # YENİ: Structured data'ya ekle
                            structured_konu_data.append({
                                'ogrenme_birimi': baslik_for_display,
                                'sira': i,
                                'konu_sayisi': konu_sayisi_int,
                                'konular': konu_listesi
                            })
                            break
                        start_pos = idx + 1
            
            if formatted_content_parts:
                formatted_content = "\\n".join(formatted_content_parts)
            else:
                if len(ogrenme_birimi_alani) <= 400:
                    formatted_content = ogrenme_birimi_alani
                else:
                    formatted_content = f"{ogrenme_birimi_alani[:200]}\\n...\\n{ogrenme_birimi_alani[-200:]}"
        else:
            if len(ogrenme_birimi_alani) <= 400:
                formatted_content = ogrenme_birimi_alani
            else:
                formatted_content = f"{ogrenme_birimi_alani[:200]}\\n...\\n{ogrenme_birimi_alani[-200:]}"

        result = f"{'--'*25}\\nÖğrenme Birimi Alanı:{header_match_info}{'--'*25}\\n{formatted_content}"
        return result, structured_konu_data
            
    except Exception as e:
        return f"Hata: {str(e)}", []

def extract_kazanimlar_from_konu_content(konu_content):
    """
    Konu içeriğinden kazanımları çıkarır
    
    Args:
        konu_content (str): Tek konu metnin içeriği
        
    Returns:
        list: Kazanım listesi [{'kazanim_adi': str, 'sira': int}, ...]
    """
    import re
    
    if not konu_content or len(konu_content.strip()) < 10:
        return []
    
    content = konu_content.strip()
    kazanimlar = []
    
    # Kazanım pattern'leri (öncelik sırasında)
    kazanim_patterns = [
        # Alt numaralı maddeler: 1.1., 1.2., 2.1., 2.2. vb.
        r'(\d+\.\d+\.)\s*(.+?)(?=\n\d+\.\d+\.|\n[A-Z]|\n•|\n-|\n[a-z]\)|\n\d+\.|\Z)',
        # Nokta ile başlayan maddeler: • text, - text
        r'([•-])\s*(.+?)(?=\n[•-]|\n\d+\.|\n[A-Z]|\n[a-z]\)|\Z)',
        # Harf ile numaralanmış: a) text, b) text, c) text
        r'([a-z]\))\s*(.+?)(?=\n[a-z]\)|\n\d+\.|\n[A-Z]|\n[•-]|\Z)',
        # Parantez içi rakam: (1) text, (2) text
        r'(\(\d+\))\s*(.+?)(?=\n\(\d+\)|\n\d+\.|\n[A-Z]|\n[•-]|\n[a-z]\)|\Z)',
    ]
    
    # Her pattern'i dene
    for pattern in kazanim_patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        if matches:
            sira = 1
            for match in matches:
                marker = match[0].strip()
                kazanim_text = match[1].strip()
                
                # Çok kısa kazanımları atla
                if len(kazanim_text) < 5:
                    continue
                    
                # Çok uzun kazanımları kısalt (200 karakter limit)
                if len(kazanim_text) > 200:
                    kazanim_text = kazanim_text[:197] + "..."
                
                # Temizlik: Yeni satır karakterlerini boşluk yap
                kazanim_text = re.sub(r'\s+', ' ', kazanim_text).strip()
                
                # Validasyon: Gerçek kazanım mı yoksa başka bir şey mi?
                if is_valid_kazanim_text(kazanim_text):
                    kazanimlar.append({
                        'kazanim_adi': kazanim_text,
                        'sira': sira,
                        'marker': marker  # Debug için
                    })
                    sira += 1
            
            # Eğer kazanım bulunduysa bu pattern'i kullan, diğerlerini deneme
            if kazanimlar:
                break
    
    return kazanimlar

def is_valid_kazanim_text(text):
    """
    Bir metnin gerçek kazanım metni olup olmadığını kontrol eder
    
    Args:
        text (str): Kontrol edilecek metin
        
    Returns:
        bool: Geçerli kazanım metni ise True
    """
    if not text or len(text.strip()) < 5:
        return False
    
    text_upper = text.upper()
    
    # Geçersiz pattern'ler
    invalid_patterns = [
        'DERS ', 'HAFTA', 'SAAT', 'TOPLAM', 'UYGULAMA', 'FAALİYET', 
        'TEMRİN', 'DEĞERLEND', 'SINAMA', 'ÖLÇME', 'TEST', 'ÖRNEK',
        'AÇIKLAMA', 'NOT:', 'UYARI:', 'DİKKAT:', 'ÖNEMLİ:'
    ]
    
    for invalid in invalid_patterns:
        if invalid in text_upper:
            return False
    
    # Çok kısa veya sadece rakam/sembol içeren metinler
    if len(text.strip()) < 10 and not any(c.isalpha() for c in text):
        return False
    
    return True

def ex_ob_tablosu_konu_sinirli_arama(text, baslik_idx, baslik, konu_sayisi, all_matched_headers=None):
    """
    Başlık eşleşmesinden sonra konu yapısını sıralı rakamlarla doğrular - 2 döngü
    
    ⭐ YENİ: Artık her konu için kazanımları da çıkarır
    
    Returns:
        tuple: (formatted_text, structured_konu_data_with_kazanimlar)
    """
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
            r'\\n[A-ZÜĞIŞÖÇ][A-ZÜĞIŞÖÇ\\s]{10,}',
            r'\\n\\d+\\.\\s*[A-ZÜĞIŞÖÇ]', 
            r'DERSİN|DERSĠN',
            r'UYGULAMA|FAALİYET|TEMRİN'
        ]
        
        for pattern in next_header_patterns:
            match = re.search(pattern, after_baslik)
            if match and match.start() < next_matched_header_pos:
                next_matched_header_pos = match.start()
    
    work_area = after_baslik[:next_matched_header_pos]
    validation_info = []  # String çıktı için (backward compatibility)
    structured_konu_data = []  # ⭐ YENİ: Structured data için
    
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
                # Context-aware validation: gerçek madde başlığı mı?
                if is_valid_madde_baslik(work_area, pos, konu_no):
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
                        # Context-aware validation: gerçek madde başlığı mı?
                        if is_valid_madde_baslik(work_area, pos, konu_no + 1):
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
                konu_title_and_content = cleaned_content.strip()
            elif cleaned_content.startswith(f"{konu_no} "):
                cleaned_content = cleaned_content.replace(f"{konu_no} ", "", 1)
                konu_title_and_content = cleaned_content.strip()
            else:
                konu_title_and_content = cleaned_content.strip()
            
            # Konu başlığını content'ten ayır (ilk satır genelde başlık)
            lines = konu_title_and_content.split('\n')
            konu_adi = lines[0].strip() if lines else konu_title_and_content[:50].strip()
            konu_full_content = konu_title_and_content
            
            # ⭐ YENİ: Konu içeriğinden kazanımları çıkar
            kazanimlar = extract_kazanimlar_from_konu_content(konu_full_content)
            
            # Structured data'ya ekle
            structured_konu_data.append({
                'konu_adi': konu_adi,
                'sira': konu_no,
                'content': konu_full_content,  # Debug için tam içerik
                'kazanimlar': kazanimlar  # ⭐ YENİ: Kazanım listesi
            })
            
            # Backward compatibility: String çıktı
            kazanim_count = len(kazanimlar)
            kazanim_preview = f" ({kazanim_count} kazanım)" if kazanim_count > 0 else ""
            validation_info.append(f"{konu_no}. {konu_adi}{kazanim_preview}")
            
            current_pos = found_pos + 1
        else:
            current_pos += 1
    
    return "\\n".join(validation_info), structured_konu_data

def ex_ob_tablosu_konu_bulma_yedek_plan(text, original_baslik, konu_sayisi):
    """Son eşleşen başlıktan sonra '1' rakamını bulup alternatif eşleşme arar"""
    import re
    
    # "1" rakamını ara - daha basit pattern
    one_pattern = r'1\\.'
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
                patterns = [f"{rakam}. ", f"{rakam} "]
                pattern_found = False
                for pattern in patterns:
                    pos = after_one[:500].find(pattern)  # İlk 500 karakterde ara
                    if pos != -1:
                        # Context-aware validation: gerçek madde başlığı mı?
                        if is_valid_madde_baslik(after_one[:500], pos, rakam):
                            pattern_found = True
                            break
                if pattern_found:
                    found_numbers += 1
            
            # Tüm rakamlar bulunduysa alternatif eşleşme geçerli
            if found_numbers == konu_sayisi:
                return {
                    'title': potential_title,
                    'position': one_pos,
                    'numbers_found': found_numbers
                }
    
    return None

def get_all_dbf_files(validate_files=True):
    """
    DBF PDF ve DOCX dosyalarını bulma ve yönetme fonksiyonu - API sistemine optimize edildi
    
    Args:
        validate_files (bool): Dosya bütünlüğü kontrolü yap (varsayılan: True)
    
    Returns:
        list: PDF ve DOCX dosya yolları listesi (sadece geçerli dosyalar)
    """
    import os
    
    # utils_env modülünü kullan
    try:
        from .utils_env import get_data_path, get_project_root
    except ImportError:
        from modules.utils_env import get_data_path, get_project_root
    
    project_root = get_project_root()
    base_path = get_data_path("dbf")
    
    # Debug: base_path'i konsola yazdır
    print(f"📍 PROJECT_ROOT: {project_root}")
    print(f"📍 DBF tarama yolu: {base_path}")
    print(f"📍 Klasör mevcut mu: {os.path.exists(base_path)}")
    
    def is_valid_document(file_path):
        """Dosyanın geçerli bir PDF veya DOCX dosyası olup olmadığını kontrol eder"""
        if not validate_files:
            return True
            
        try:
            # PyMuPDF ile dosyayı açmayı dene
            doc = fitz.open(file_path)
            
            # Dosya açılabildi, temel kontroller yap
            page_count = len(doc)
            if page_count == 0:
                doc.close()
                return False
            
            # İlk sayfayı okumayı dene
            page = doc.load_page(0)
            text = page.get_text()
            doc.close()
            
            # Eğer hiç metin yoksa ve sayfa sayısı 1'den azsa bozuk olabilir
            if not text.strip() and page_count <= 1:
                return False
                
            return True
            
        except Exception as e:
            # Dosya açılamıyorsa veya hata varsa geçersiz
            print(f"⚠️  Bozuk dosya atlandı: {os.path.basename(file_path)} - {str(e)}")
            return False
    
    # Tüm PDF ve DOCX dosyalarını bul ve validate et
    all_files = []
    supported_extensions = ('.pdf', '.docx')
    skipped_files = 0
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(supported_extensions):
                file_path = os.path.join(root, file)
                
                # Dosya bütünlüğü kontrolü
                if is_valid_document(file_path):
                    all_files.append(file_path)
                else:
                    skipped_files += 1
    
    # Sonuç bilgilerini yazdır
    print(f"📊 Toplam {len(all_files)} geçerli dosya bulundu")
    if validate_files and skipped_files > 0:
        print(f"📊 Toplam {skipped_files} bozuk dosya işleme alınmadı.")
    
    return all_files

def read_full_text_from_file(file_path):
    """
    PDF veya DOCX dosyasından tam metni okur (PyMuPDF ile unified processing)
    
    Args:
        file_path (str): Dosya yolu
        
    Returns:
        str: Dosyadan çıkarılan tam metin
    """
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\\n"
        doc.close()
        
        # Metni normalize et
        full_text = re.sub(r'\s+', ' ', full_text)
        return full_text
        
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return ""

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

def is_valid_madde_baslik(text, pos, rakam):
    """
    Bulunan rakam pattern'inin gerçek madde numarası mı yoksa tarih/yüzyıl mı olduğunu kontrol eder.
    
    Args:
        text (str): Aranacak metin
        pos (int): Bulunan pattern pozisyonu
        rakam (int): Aranan rakam (1, 2, 3...)
        
    Returns:
        bool: True = gerçek madde başlığı, False = tarih/yüzyıl
    """
    import re
    
    # Pattern'den sonraki metni al
    pattern_len = len(f"{rakam}. ")
    after_pattern = text[pos + pattern_len:] if pos + pattern_len < len(text) else ""
    
    if not after_pattern.strip():
        return False
    
    # İlk kelimeyi bul
    words = after_pattern.strip().split()
    if not words:
        return False
        
    first_word = words[0].lower()
    
    # Zaman belirten kelimeler listesi
    time_words = [
        "yüzyıl", "yüzyılda", "yüzyıldan", "yüzyılın", "yüzyıla", 
        "asır", "asırda", "asırdan", "asırın", "asıra",
        "dönem", "dönemde", "dönemden", "dönemin", "döneme",
        "yıl", "yılda", "yıldan", "yılın", "yıla",
        "sene", "senede", "seneden", "senenin", "seneye"
    ]
    
    # Eğer ilk kelime zaman belirtiyorsa madde başlığı değil
    if first_word in time_words:
        return False
    
    # Satır başında mı kontrol et (madde başlıkları genelde satır başında olur)
    if pos > 0:
        char_before = text[pos - 1]
        # Öncesinde yeni satır, boşluk veya tab olmalı
        if char_before not in ['\n', '\r', ' ', '\t']:
            return False
    
    # İlk kelime büyük harfle başlıyor mu? (madde başlıkları büyük harfle başlar)
    if not (words[0] and words[0][0].isupper()):
        return False
        
    return True

# ===========================
# MAIN PROCESSING FUNCTIONS  
# ===========================

def process_dbf_file(file_path):
    """
    Tek DBF dosyasını işler ve sonuçları döndürür
    
    Args:
        file_path (str): İşlenecek dosya yolu
        
    Returns:
        dict: İşlem sonucu
    """
    try:
        # Dosyadan tam metni oku
        full_text = read_full_text_from_file(file_path)
        
        if not full_text.strip():
            return {"success": False, "error": "Dosya içeriği boş", "file_path": file_path}
        
        # Temel bilgileri çıkar
        temel_bilgiler = ex_temel_bilgiler(full_text)
        
        # Kazanım tablosunu çıkar
        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text)
        
        # Öğrenme birimi analizini yap
        ob_analiz = ex_ob_tablosu(full_text)
        
        return {
            "success": True,
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "temel_bilgiler": temel_bilgiler,
            "kazanim_tablosu_data": kazanim_tablosu_data,
            "ogrenme_birimi_analizi": ob_analiz
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path,
            "filename": os.path.basename(file_path)
        }

def process_multiple_dbf_files(file_paths):
    """
    Birden fazla DBF dosyasını işler
    
    Args:
        file_paths (list): İşlenecek dosya yolları
        
    Returns:
        dict: Toplu işlem sonucu
    """
    results = []
    success_count = 0
    error_count = 0
    
    for file_path in file_paths:
        result = process_dbf_file(file_path)
        results.append(result)
        
        if result["success"]:
            success_count += 1
        else:
            error_count += 1
    
    return {
        "results": results,
        "total_files": len(file_paths),
        "success_count": success_count,
        "error_count": error_count
    }

