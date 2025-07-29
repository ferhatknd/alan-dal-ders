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

# ===========================
# UTILITY CLASSES & HELPERS
# ===========================

# Metin işleme sınıfı - Normalizasyon işlemlerini önbelleğe alarak performansı artırır
# PDF'den çıkarılan metinleri normalize eder ve arama işlemlerini hızlandırır
class TextProcessor:
    """
    Text processing utility with caching to avoid repeated normalization
    """
    def __init__(self, text):
        self.original = text
        self.normalized = normalize_turkish_text(text) if text else ""
        self._cache = {}
    
    def find_normalized(self, pattern, start=0):
        """Find pattern in normalized text"""
        cache_key = f"{pattern}_{start}"
        if cache_key not in self._cache:
            pattern_norm = normalize_turkish_text(pattern) if pattern else ""
            self._cache[cache_key] = self.normalized.find(pattern_norm, start)
        return self._cache[cache_key]
    
    def normalize_text(self, text):
        """Normalize text using cached normalization function"""
        import re
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def get_section(self, start_idx, end_idx=None):
        """Get text section, returns both original and normalized"""
        if end_idx is None:
            end_idx = len(self.original)
        return {
            'original': self.original[start_idx:end_idx],
            'normalized': self.normalized[start_idx:end_idx]
        }

# Konu numarası pattern'lerini doğrular ("1. ", "2. " gibi)
# Metinde beklenen sayıda sıralı konu numarası olup olmadığını kontrol eder
def validate_konu_patterns(text, konu_sayisi, start_pos=0, search_limit=1500):
    """
    Centralized pattern validation logic - eliminates code duplication
    
    Args:
        text (str): Text to search in
        konu_sayisi (int): Expected number of topics
        start_pos (int): Starting position
        search_limit (int): Limit search area
        
    Returns:
        int: Number of valid patterns found
    """
    found_numbers = 0
    search_area = text[start_pos:start_pos + search_limit] if start_pos + search_limit < len(text) else text[start_pos:]
    
    for rakam in range(1, konu_sayisi + 1):
        patterns = [f"{rakam}. ", f"{rakam} "]
        pattern_found = False
        
        for pattern in patterns:
            pos = search_area.find(pattern)
            if pos != -1:
                # Context-aware validation: gerçek madde başlığı mı?
                if is_valid_madde_baslik(search_area, pos, rakam):
                    pattern_found = True
                    break
        
        if pattern_found:
            found_numbers += 1
    
    return found_numbers

# Başlık eşleştirme fonksiyonu - Normalize edilmiş metinde başlık pozisyonlarını bulur
# Türkçe karakter sorunlarını çözmek için normalizasyon kullanır
def find_baslik_matches(baslik, content_processor, start_pos=0):
    """
    Find all matches of a header in content with normalized search
    
    Args:
        baslik (str): Header to search for
        content_processor (TextProcessor): Content with cached normalization
        start_pos (int): Starting position
        
    Returns:
        list: List of match positions
    """
    matches = []
    current_pos = start_pos
    baslik_normalized = normalize_turkish_text(baslik)
    
    while True:
        match_idx = content_processor.normalized.find(baslik_normalized, current_pos)
        if match_idx == -1:
            break
        matches.append(match_idx)
        current_pos = match_idx + 1
    
    return matches

# Tablo sınırlarını belirler - öğrenme birimi tablosunun başlangıç ve bitiş noktalarını bulur
# TOPLAM kelimesinden başlayarak uygun başlıkları arar ve stop kelimelerinde durdurur
def extract_table_boundaries(full_text):
    """
    Extract table start and end boundaries - centralized logic
    
    Returns:
        dict: Contains start_idx, end_idx, and content section
    """
    processor = TextProcessor(full_text)
    
    # Find TOPLAM reference point
    toplam_idx = processor.find_normalized("TOPLAM")
    if toplam_idx == -1:
        toplam_idx = 0
    
    # Find table headers
    table_headers = [
        "ÖĞRENME BİRİMİ", "KONULAR", "ÖĞRENME BİRİMİ KAZANIMLARI",
        "KAZANIM AÇIKLAMLARI", "AÇIKLAMALARI", "ÖĞRENME BİRİMİ/ÜNİTE"
    ]
    
    table_start_idx = None
    last_header_end = None
    
    for header in table_headers:
        idx = processor.find_normalized(header, toplam_idx)
        if idx != -1:
            header_end = idx + len(normalize_turkish_text(header))
            if last_header_end is None or header_end > last_header_end:
                last_header_end = header_end
                table_start_idx = header_end
    
    if table_start_idx is None:
        return None
    
    # Find table end using stop words
    stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
    table_end_idx = len(full_text)
    
    for stop_word in stop_words:
        word_pattern = r'\\b' + re.escape(stop_word) + r'\\b'
        match = re.search(word_pattern, full_text[table_start_idx:])
        if match:
            stop_idx = table_start_idx + match.start()
            if stop_idx < table_end_idx:
                table_end_idx = stop_idx
    
    content = full_text[table_start_idx:table_end_idx].strip()
    content = re.sub(r'\\s+', ' ', content).strip()
    
    return {
        'start_idx': table_start_idx,
        'end_idx': table_end_idx,
        'content': content,
        'processor': TextProcessor(content)
    }

# Başlık eşleşmelerini bulur ve doğrular - her başlık için geçerli pozisyonları tespit eder
# Kazanm tablosundaki başlıkları metinde bulur ve pattern doğrulaması yapar
def find_header_matches_with_validation(boundaries, kazanim_data):
    """
    Find and validate header matches in content
    
    Returns:
        dict: Contains all_matched_headers and match statistics
    """
    all_matched_headers = []
    content_processor = boundaries['processor']
    
    for item in kazanim_data:
        baslik = item['title']
        konu_sayisi_int = item['count']
        baslik_cleaned = re.sub(r'\\s+', ' ', baslik.strip())
        
        # CONSOLIDATED: Use unified validation logic
        valid_matches = _validate_single_header_match(boundaries, baslik_cleaned, konu_sayisi_int, return_first_only=False)
        
        # Take first valid match if any found
        if valid_matches:
            all_matched_headers.append({
                'title': baslik,
                'position': valid_matches[0],  # Use first valid match
                'konu_sayisi': konu_sayisi_int
            })
    
    return all_matched_headers

# Başlık eşleşmelerini işler ve içerik çıkarır - structured data formatında sonuç üretir
# Her başlık için konu listesini ve kazanımları çıkarır
def process_header_matches(boundaries, kazanim_data, all_matched_headers):
    """
    Process each header and extract content with structured data
    
    Returns:
        tuple: (header_match_info, formatted_content_parts, structured_konu_data)
    """
    header_match_info = "\\n"
    formatted_content_parts = []
    structured_konu_data = []
    content_processor = boundaries['processor']
    
    for i, item in enumerate(kazanim_data, 1):
        baslik = item['title']
        konu_sayisi_int = item['count']
        baslik_cleaned = re.sub(r'\\s+', ' ', baslik.strip())
        
        # Count valid matches for this header
        valid_matches = 0
        matches = find_baslik_matches(baslik_cleaned, content_processor)
        
        for match_idx in matches:
            after_baslik_pos = match_idx + len(baslik_cleaned)
            after_baslik = boundaries['content'][after_baslik_pos:]
            
            if konu_sayisi_int > 0:
                found_numbers = validate_konu_patterns(after_baslik, konu_sayisi_int)
                if found_numbers == konu_sayisi_int:
                    valid_matches += 1
        
        header_match_info += f"{i}-{baslik} ({konu_sayisi_int}) -> {valid_matches} eşleşme\\n"
        
        # Try alternative method if no matches found
        if valid_matches == 0 and konu_sayisi_int > 0:
            alternative_match = ex_ob_tablosu_konu_bulma_yedek_plan(
                boundaries['content'], baslik_cleaned, konu_sayisi_int
            )
            if alternative_match:
                valid_matches = 1
                header_match_info = header_match_info.replace(
                    f"{i}-{baslik} ({konu_sayisi_int}) -> 0 eşleşme\\n",
                    f"{i}-{baslik} ({konu_sayisi_int}) -> 1 eşleşme (alternatif)\\n"
                )
        
        # Process first valid match for content extraction
        if valid_matches > 0:
            first_match = find_first_valid_match(boundaries, baslik_cleaned, konu_sayisi_int)
            if first_match is not None:
                validation_result, konu_listesi = ex_ob_tablosu_konu_sinirli_arama(
                    boundaries['content'], first_match, baslik_cleaned, konu_sayisi_int, all_matched_headers
                )
                
                formatted_content_parts.append(
                    f"{i}-{baslik} ({konu_sayisi_int}) -> 1. Eşleşme\\n"
                    f"{validation_result}\\n"
                )
                
                structured_konu_data.append({
                    'ogrenme_birimi': baslik,
                    'sira': i,
                    'konu_sayisi': konu_sayisi_int,
                    'konular': konu_listesi
                })
    
    return header_match_info, formatted_content_parts, structured_konu_data

# CONSOLIDATED: Merged with find_header_matches_with_validation logic
def _validate_single_header_match(boundaries, baslik_cleaned, konu_sayisi_int, return_first_only=False):
    """Unified header validation - can return first match or all matches"""
    content_processor = boundaries['processor']
    matches = find_baslik_matches(baslik_cleaned, content_processor)
    valid_matches = []
    
    for match_idx in matches:
        after_baslik_pos = match_idx + len(baslik_cleaned)
        after_baslik = boundaries['content'][after_baslik_pos:]
        
        if konu_sayisi_int > 0:
            found_numbers = validate_konu_patterns(after_baslik, konu_sayisi_int)
            if found_numbers == konu_sayisi_int:
                if return_first_only:
                    return match_idx
                valid_matches.append(match_idx)
    
    return None if return_first_only else valid_matches

def find_first_valid_match(boundaries, baslik_cleaned, konu_sayisi_int):
    """Find the first valid match position for a header"""
    return _validate_single_header_match(boundaries, baslik_cleaned, konu_sayisi_int, return_first_only=True)

# DBF PDF'den temel ders bilgilerini çıkarır - ders adı, sınıf, süre, amaç gibi bilgileri parse eder
# Pattern matching ile "DERSİN ADI:", "DERSİN SINIFI:" gibi alanları bulur ve içeriklerini çıkarır
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

# Kazanım sayısı ve süre tablosunu parse eder - her öğrenme birimi için kazanım sayısı ve ders saati bilgilerini çıkarır
# "KAZANIM SAYISI VE SÜRE TABLOSU" başlığını bulur ve altındaki tabloyu structured data formatına çevirir
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
            
            # Use cached normalization instead of calling twice
            if ogrenme_birimi.upper().strip() != "TOPLAM":
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

# PDF'den öğrenme birimi alanını çıkarır - en karmaşık ve ana fonksiyon
# Kazanım tablosundaki başlıkları metinde bulur, konu listelerini çıkarır ve structured data formatında döndürür
def ex_ob_tablosu(full_text):
    """
    REFACTORED - PDF'den Öğrenme Birimi Alanını çıkarır
    
    Args:
        full_text (str): PDF/DOCX'den çıkarılan tam metin
        
    Returns:
        tuple: (öğrenme_birimi_analiz_sonucu_string, structured_konu_data)
    """
    try:
        # Extract table boundaries using centralized logic
        boundaries = extract_table_boundaries(full_text)
        if boundaries is None:
            return "Öğrenme Birimi Alanı - Başlangıç kelimeleri bulunamadı", []
        
        # Get kazanim data
        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text)
        
        if not kazanim_tablosu_data:
            # Return raw content if no structured data available
            content = boundaries['content']
            if len(content) <= 400:
                formatted_content = content
            else:
                formatted_content = f"{content[:200]}\\n...\\n{content[-200:]}"
            
            result = f"{'--'*25}\\nÖğrenme Birimi Alanı:\\n{'--'*25}\\n{formatted_content}"
            return result, []
        
        # Adjust table start if first title is found
        if kazanim_tablosu_data:
            first_title = kazanim_tablosu_data[0]['title']
            processor = TextProcessor(full_text)
            first_title_idx = processor.find_normalized(first_title, boundaries['start_idx'])
            if first_title_idx != -1:
                # Recalculate boundaries with new start position
                new_content = full_text[first_title_idx:boundaries['end_idx']].strip()
                new_content = re.sub(r'\\s+', ' ', new_content).strip()
                boundaries['content'] = new_content
                boundaries['processor'] = TextProcessor(new_content)
                boundaries['start_idx'] = first_title_idx
        
        # Find and validate header matches
        all_matched_headers = find_header_matches_with_validation(boundaries, kazanim_tablosu_data)
        
        # Process headers and extract content
        header_match_info, formatted_content_parts, structured_konu_data = process_header_matches(
            boundaries, kazanim_tablosu_data, all_matched_headers
        )
        
        # Format final result
        if formatted_content_parts:
            formatted_content = "\\n".join(formatted_content_parts)
        else:
            content = boundaries['content']
            if len(content) <= 400:
                formatted_content = content
            else:
                formatted_content = f"{content[:200]}\\n...\\n{content[-200:]}"
        
        result = f"{'--'*25}\\nÖğrenme Birimi Alanı:{header_match_info}{'--'*25}\\n{formatted_content}"
        return result, structured_konu_data
        
    except Exception as e:
        return f"Hata: {str(e)}", []

# Konu içeriğinden kazanım listesini çıkarır - "1.1.", "•", "a)" gibi pattern'leri tespit eder
# Her konu metnindeki alt maddeleri bulur ve structured data formatında kazanım listesi döndürür
def extract_kazanimlar_from_konu_content(konu_content, text_processor=None):
    """
    OPTIMIZED - Konu içeriğinden kazanımları çıkarır
    """
    import re
    
    if not konu_content or len(konu_content.strip()) < 10:
        return []
    
    # Use cached text processor if available
    if text_processor is None:
        text_processor = TextProcessor(konu_content)
    
    kazanimlar = []
    
    # Consolidated kazanım patterns
    patterns = [
        r'(\d+\.\d+\.)\s*(.+?)(?=\n\d+\.\d+\.|\n[A-Z]|\n•|\n-|\n[a-z]\)|\n\d+\.|\Z)',
        r'([•-])\s*(.+?)(?=\n[•-]|\n\d+\.|\n[A-Z]|\n[a-z]\)|\Z)',
        r'([a-z]\))\s*(.+?)(?=\n[a-z]\)|\n\d+\.|\n[A-Z]|\n[•-]|\Z)',
        r'(\(\d+\))\s*(.+?)(?=\n\(\d+\)|\n\d+\.|\n[A-Z]|\n[•-]|\n[a-z]\)|\Z)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_processor.original, re.MULTILINE | re.DOTALL)
        if matches:
            sira = 1
            for marker, text in matches:
                cleaned_text = text_processor.normalize_text(text)
                
                if 5 <= len(cleaned_text) <= 200 and _is_valid_kazanim(cleaned_text):
                    kazanimlar.append({
                        'kazanim_adi': cleaned_text[:197] + "..." if len(cleaned_text) > 200 else cleaned_text,
                        'sira': sira,
                        'marker': marker.strip()
                    })
                    sira += 1
            
            if kazanimlar:
                break
    
    return kazanimlar

# Kazanım metninin geçerli olup olmadığını kontrol eder - geçersiz kelimeler varsa reddeder
# "DERS", "HAFTA", "SAAT" gibi başlık kelimelerini içeren metinleri kazanım olarak kabul etmez
def _is_valid_kazanim(text):
    """
    OPTIMIZED - Simplified kazanim validation
    """
    if not text or len(text) < 5:
        return False
    
    # Quick check for invalid patterns
    text_upper = text.upper()
    invalid_keywords = ['DERS ', 'HAFTA', 'SAAT', 'TOPLAM', 'UYGULAMA', 'FAALİYET', 
                       'TEMRİN', 'DEĞERLEND', 'SINAMA', 'ÖLÇME', 'TEST', 'ÖRNEK']
    
    return not any(keyword in text_upper for keyword in invalid_keywords) and \
           (len(text) >= 10 or any(c.isalpha() for c in text))

# Çalışma alanı sınırlarını belirler - başlıktan sonra hangi kısım işlenecek
# Diğer başlıkları ve stop kelimeleri kullanarak alan sınırlarını çizer
def _find_work_area_boundaries(after_baslik, all_matched_headers, baslik_idx, baslik):
    """OPTIMIZED - Helper: Find work area boundaries for content extraction"""
    import re
    
    next_pos = len(after_baslik)
    
    # Check matched headers
    if all_matched_headers:
        current_pos_in_text = baslik_idx + len(baslik)
        for header_info in all_matched_headers:
            other_pos = header_info.get('position', -1)
            if other_pos > current_pos_in_text:
                relative_pos = other_pos - current_pos_in_text
                if relative_pos < next_pos:
                    next_pos = relative_pos
    
    # Check general patterns
    if next_pos == len(after_baslik):
        patterns = [r'\\n[A-ZÜĞIŞÖÇ][A-ZÜĞIŞÖÇ\\s]{10,}', r'\\n\\d+\\.\\s*[A-ZÜĞIŞÖÇ]', 
                   r'DERSİN|DERSĠN', r'UYGULAMA|FAALİYET|TEMRİN']
        
        for pattern in patterns:
            match = re.search(pattern, after_baslik)
            if match and match.start() < next_pos:
                next_pos = match.start()
    
    return after_baslik[:next_pos]

# Belirli bir konu numarası için içerik çıkarır - "1. ", "2. " pattern'leri ile sınırlar bulur
# Konu başlığı ve içeriğini ayırarak temizlenmiş metin döndürür
def _extract_konu_content(work_area, konu_no, konu_sayisi, current_pos):
    """OPTIMIZED - Helper: Extract content for a specific konu number"""
    patterns = [f"{konu_no}. ", f"{konu_no} "]
    
    for pattern in patterns:
        pos = work_area.find(pattern, current_pos)
        if pos != -1 and is_valid_madde_baslik(work_area, pos, konu_no):
            # Find end position
            end_pos = len(work_area)
            if konu_no < konu_sayisi:
                next_patterns = [f"{konu_no + 1}. ", f"{konu_no + 1} "]
                for next_pattern in next_patterns:
                    next_pos = work_area.find(next_pattern, pos + 1)
                    if next_pos != -1 and is_valid_madde_baslik(work_area, next_pos, konu_no + 1):
                        end_pos = next_pos
                        break
            
            content = work_area[pos:end_pos].strip()
            # Clean the number prefix
            for p in patterns:
                if content.startswith(p):
                    content = content[len(p):].strip()
                    break
            
            return content, pos + 1
    
    return None, current_pos + 1

# Başlık eşleşmesinden sonra konu yapısını sıralı rakamlarla parse eder ve kazanımları çıkarır
# "1. Konu Adı", "2. Diğer Konu" şeklindeki yapıyı tespit eder ve her konu için kazanım listesi oluşturur
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
    
    # CONSOLIDATED: Use helper function instead of duplicate code
    work_area = _find_work_area_boundaries(after_baslik, all_matched_headers, baslik_idx, baslik)
    validation_info = []  # String çıktı için (backward compatibility)
    structured_konu_data = []  # ⭐ YENİ: Structured data için
    
    # CONSOLIDATED: Use optimized helper function with cached text processor
    text_processor = TextProcessor(work_area)  # Cache normalization
    current_pos = 0
    
    for konu_no in range(1, konu_sayisi + 1):
        content, current_pos = _extract_konu_content(work_area, konu_no, konu_sayisi, current_pos)
        
        if content:
            lines = content.split('\n')
            konu_adi = lines[0].strip() if lines else content[:50].strip()
            
            # Extract kazanimlar with cached text processor
            kazanimlar = extract_kazanimlar_from_konu_content(content, text_processor)
            
            structured_konu_data.append({
                'konu_adi': konu_adi,
                'sira': konu_no,
                'content': content,
                'kazanimlar': kazanimlar
            })
            
            kazanim_preview = f" ({len(kazanimlar)} kazanım)" if kazanimlar else ""
            validation_info.append(f"{konu_no}. {konu_adi}{kazanim_preview}")
    
    return "\\n".join(validation_info), structured_konu_data

# Yedek plan fonksiyonu - normal başlık eşleştirme başarısız olduğunda alternatif yöntem dener
# "1" rakamını arayarak potansiyel başlık pozisyonlarını bulur ve doğrular
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

# DBF klasöründeki tüm PDF/DOCX dosyalarını tarar ve geçerli dosyaları listeler
# Dosya bütünlüğü kontrolü yapar ve sadece okuttirilebilir dosyaları döndürür
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

# Türkçe karakter normalizasyon fonksiyonu - çıkış, öğrenme gibi kelimelerdeki özel karakterleri ASCII'ye çevirir
# Case-insensitive eşleştirme için tüm karakterleri büyük harfe çevirir ve whitespace normalize eder
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

# Madde başlığı doğrulama fonksiyonu - "15-20. yüzyıl" gibi tarih ifadelerini madde numarası olarak algılamaz
# Context-aware validation ile gerçek "1. ", "2. " madde başlıklarını tespit eder
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

# Tek DBF dosyasını tam olarak işler - temel bilgiler, kazanım tablosu ve öğrenme birimi analizi yapar
# API endpoint'leri tarafından çağrılan ana processing fonksiyonu
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

# Çoklu DBF dosyası işleme fonksiyonu - dosya listesini alır ve her birini sırasıyla işler
# Başarı ve hata istatistiklerini tutar, toplu sonuç raporu üretir
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

