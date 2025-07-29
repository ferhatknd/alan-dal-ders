"""
modules/utils_dbf2.py
=====================
PDF'nin 2. sayfa ve sonrasındaki öğrenme birimi işlemleri
- ex_ob_tablosu(): Ana öğrenme birimi çıkarma fonksiyonu
- ex_ob_tablosu_konu_sinirli_arama(): Konu içeriklerini çıkarma
- ex_ob_tablosu_konu_bulma_yedek_plan(): Alternatif eşleştirme
- Yardımcı fonksiyonlar: pattern validation, boundary extraction vb.

NOT: Bu modül fitz kullanmaz, metin utils_dbf1'den alır.
"""

import re
import os

# Modüler import'lar
try:
    from .utils_database import with_database
except ImportError:
    from utils_database import with_database

try:
    from .utils_dbf1 import normalize_turkish_text, TextProcessor
except ImportError:
    from utils_dbf1 import normalize_turkish_text, TextProcessor


# ===========================
# UTILITY FUNCTIONS FOR DBF2
# ===========================

# Konu pattern'lerini doğrulama fonksiyonu - her konu için "1. ", "2. " gibi pattern'lerin varlığını kontrol eder
# 1500 karakter sınırı ile hızlı arama yapar ve sıralı konu numaralarının bulunup bulunmadığını test eder
def validate_konu_patterns(text, konu_sayisi, start_pos=0, search_limit=4000):
    """
    Belirtilen pozisyondan itibaren sıralı konu numaralarının varlığını kontrol eder
    
    Args:
        text (str): Aranacak metin
        konu_sayisi (int): Beklenen konu sayısı
        start_pos (int): Arama başlangıç pozisyonu
        search_limit (int): Arama sınırı (performans için)
        
    Returns:
        bool: Tüm konu numaraları bulunduysa True
    """
    end_pos = min(len(text), start_pos + search_limit)
    search_area = text[start_pos:end_pos]
    
    found_patterns = 0
    for rakam in range(1, konu_sayisi + 1):
        # Gelişmiş pattern listesi - daha fazla varyasyon
        patterns = [
            f"{rakam}. ",     # "1. Konu"
            f"{rakam} ",      # "1 Konu"  
            f"{rakam}.",      # "1.Konu" (boşluksuz)
            f" {rakam}. ",    # " 1. Konu"
            f" {rakam} ",     # " 1 Konu"
            f" {rakam}.",     # " 1.Konu"
            f"\n{rakam}. ",   # Satır başında
            f"\n{rakam} ",    # Satır başında
            f"\n{rakam}."     # Satır başında boşluksuz
        ]
        
        found = False
        for pattern in patterns:
            if pattern in search_area:
                found = True
                break
        
        if found:
            found_patterns += 1
    
    return found_patterns == konu_sayisi


# Başlık eşleştirme fonksiyonu - normalize edilmiş metinde belirtilen başlığın tüm pozisyonlarını bulur
# TextProcessor cache sistemi kullanarak hızlı arama yapar ve eşleştirme pozisyonlarını döndürür
def find_baslik_matches(baslik, content_processor, start_pos=0):
    """
    Başlığın metindeki tüm eşleştirme pozisyonlarını bulur
    
    Args:
        baslik (str): Aranacak başlık
        content_processor (TextProcessor): Metin işleme nesnesi
        start_pos (int): Arama başlangıç pozisyonu
        
    Returns:
        list: Eşleştirme pozisyonları listesi
    """
    matches = []
    current_pos = start_pos
    
    while True:
        match_pos = content_processor.find_normalized(baslik, current_pos)
        if match_pos == -1:
            break
        matches.append(match_pos)
        current_pos = match_pos + 1
    
    return matches


# Tablo sınırlarını çıkarma fonksiyonu - TOPLAM kelimesinden başlayarak öğrenme birimi tablosunun başlangıç/bitiş pozisyonlarını belirler
# Multiple header pattern'leri destekler ve stop word'lerde durarak tablo alanını sınırlandırır
def extract_table_boundaries(full_text, kazanim_data=None):
    """
    TOPLAM kelimesinden başlayarak öğrenme birimi tablosunun sınırlarını belirler
    
    Args:
        full_text (str): Tam PDF metni
        kazanim_data (list): Kazanım tablosu verisi (opsiyonel, daha akıllı sınır tespiti için)
        
    Returns:
        dict: {'start': int, 'end': int, 'content': str} tablo sınır bilgileri
    """
    # Türkçe karakterleri normalize et
    full_text_normalized_for_search = normalize_turkish_text(full_text)
    
    # TOPLAM kelimesini bul
    toplam_normalized = normalize_turkish_text("TOPLAM")
    toplam_idx = full_text_normalized_for_search.find(toplam_normalized)
    
    if toplam_idx == -1:
        return {'start': 0, 'end': len(full_text), 'content': full_text}
    
    # Tablo başlangıcını belirle (TOPLAM'dan sonra)
    table_start = toplam_idx + len("TOPLAM")
    
    # Tablo başlık pattern'lerini ara
    table_headers = [
        "ÖĞRENME BİRİMİ", "KONULAR", "ÖĞRENME BİRİMİ KAZANIMLARI",
        "KAZANIM AÇIKLAMLARI", "AÇIKLAMALARI"
    ]
    
    earliest_header_idx = len(full_text_normalized_for_search)
    for header in table_headers:
        header_normalized = normalize_turkish_text(header)
        header_idx = full_text_normalized_for_search.find(header_normalized, table_start)
        if header_idx != -1 and header_idx < earliest_header_idx:
            earliest_header_idx = header_idx
    
    if earliest_header_idx < len(full_text_normalized_for_search):
        table_start = earliest_header_idx
    
    # Tablo sonunu belirle
    table_end = len(full_text_normalized_for_search)
    
    # Stop word'leri ara (sınırsız arama - tablo başlangıcından sonra)
    stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
    
    for stop_word in stop_words:
        stop_word_normalized = normalize_turkish_text(stop_word)
        stop_idx = full_text_normalized_for_search.find(stop_word_normalized, table_start)
        if stop_idx != -1 and stop_idx < table_end:
            table_end = stop_idx
    
    # Orijinal metinden tablo alanını çıkar
    ogrenme_birimi_alani = full_text[table_start:table_end]
    
    return {
        'start': table_start,
        'end': table_end,
        'content': ogrenme_birimi_alani
    }


# Header eşleştirme ve doğrulama fonksiyonu - kazanım tablosundaki her başlık için öğrenme birimi tablosunda eşleştirme arar
# Pattern validation ile gerçek eşleştirmeleri sahte eşleştirmelerden ayırır ve geçerli pozisyonları döndürür
def find_header_matches_with_validation(boundaries, kazanim_data):
    """
    Kazanım tablosundaki başlıkları öğrenme birimi alanında arar ve doğrular
    
    Args:
        boundaries (dict): Tablo sınır bilgileri
        kazanim_data (list): Kazanım tablosu verisi
        
    Returns:
        list: Doğrulanmış eşleştirme bilgileri
    """
    results = []
    content_processor = TextProcessor(boundaries['content'])
    
    for item in kazanim_data:
        baslik_for_matching = item['title']
        konu_sayisi_int = int(item['count'])
        
        # Başlık eşleştirmelerini bul
        matches = find_baslik_matches(baslik_for_matching, content_processor)
        
        # Her eşleştirmeyi doğrula
        valid_matches = []
        for match_pos in matches:
            if validate_konu_patterns(boundaries['content'], konu_sayisi_int, match_pos):
                valid_matches.append(match_pos)
        
        results.append({
            'baslik': baslik_for_matching,
            'konu_sayisi': konu_sayisi_int,
            'total_matches': len(matches),
            'valid_matches': len(valid_matches),
            'positions': valid_matches
        })
    
    return results


# Header eşleştirme işleme fonksiyonu - doğrulanmış eşleştirmelerden all_matched_headers listesi oluşturur
# Çoklu geçerli eşleştirme durumlarını yönetir ve sadece ilk geçerli eşleştirmeyi aktif olarak işaretler
def process_header_matches(boundaries, kazanim_data, all_matched_headers):
    """
    Header eşleştirmelerini işler ve all_matched_headers listesini oluşturur
    
    Args:
        boundaries (dict): Tablo sınır bilgileri
        kazanim_data (list): Kazanım tablosu verisi
        all_matched_headers (list): Çıktı listesi (referans olarak güncellenir)
        
    Returns:
        dict: İşlem sonucu ve istatistikler
    """
    validation_results = find_header_matches_with_validation(boundaries, kazanim_data)
    
    stats = {
        'total_headers': len(kazanim_data),
        'valid_headers': 0,
        'total_valid_matches': 0
    }
    
    for result in validation_results:
        baslik_cleaned = result['baslik']
        konu_sayisi_int = result['konu_sayisi']
        valid_match_count = result['valid_matches']
        positions = result['positions']
        
        if valid_match_count > 0:
            stats['valid_headers'] += 1
            stats['total_valid_matches'] += valid_match_count
            
            # İlk geçerli pozisyonu kullan
            first_valid_pos = positions[0]
            
            all_matched_headers.append({
                'title': baslik_cleaned,
                'position': boundaries['start'] + first_valid_pos,
                'count': konu_sayisi_int,
                'valid_matches': valid_match_count
            })
    
    return stats


# İlk geçerli eşleştirmeyi bulma fonksiyonu - çoklu eşleştirme durumlarında sadece ilk geçerli olanı döndürür
# İçerik çıkarma işlemi için kullanılır ve duplicate eşleştirmeleri engeller
def find_first_valid_match(boundaries, baslik_cleaned, konu_sayisi_int):
    """
    Belirtilen başlık için ilk geçerli eşleştirmeyi bulur
    
    Args:
        boundaries (dict): Tablo sınır bilgileri
        baslik_cleaned (str): Temizlenmiş başlık
        konu_sayisi_int (int): Beklenen konu sayısı
        
    Returns:
        dict: İlk geçerli eşleştirme bilgisi veya None
    """
    content_processor = TextProcessor(boundaries['content'])
    matches = find_baslik_matches(baslik_cleaned, content_processor)
    
    for match_pos in matches:
        if validate_konu_patterns(boundaries['content'], konu_sayisi_int, match_pos):
            return {
                'position': match_pos,
                'content_start': boundaries['start'] + match_pos
            }
    
    return None


# ===========================
# MAIN PROCESSING FUNCTIONS
# ===========================

# Ana öğrenme birimi çıkarma fonksiyonu - DBF PDF'den hiyerarşik öğrenme birimi yapısını çıkarır
# Kazanım tablosu ile cross-reference yaparak structured data formatında öğrenme birimlerini döndürür
def ex_ob_tablosu(full_text):
    """
    PDF'den öğrenme birimi alanını çıkarır ve yapılandırılmış içerik döndürür
    
    Args:
        full_text (str): utils_dbf1'den alınan tam PDF metni
        
    Returns:
        str: Formatlı çıktı metni
    """
    try:
        # Import here to avoid circular dependency
        try:
            from .utils_dbf1 import ex_kazanim_tablosu
        except ImportError:
            from utils_dbf1 import ex_kazanim_tablosu
        
        # Kazanım tablosundan veri al
        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text=full_text)
        
        if not kazanim_tablosu_data:
            return "Kazanım tablosu bulunamadı - Öğrenme birimi çıkarma yapılamıyor"
        
        # Tablo sınırlarını belirle (kazanım data ile akıllı sınır tespiti)
        boundaries = extract_table_boundaries(full_text, kazanim_tablosu_data)
        
        if not boundaries['content'].strip():
            return "Öğrenme birimi alanı bulunamadı"
        
        # Header eşleştirmelerini işle
        all_matched_headers = []
        stats = process_header_matches(boundaries, kazanim_tablosu_data, all_matched_headers)
        
        if stats['valid_headers'] == 0:
            return "Geçerli header eşleştirmesi bulunamadı"
        
        # Çıktı oluştur
        output_lines = []
        output_lines.append("-" * 50)
        output_lines.append("Öğrenme Birimi Alanı:")
        
        # Header özeti
        for i, header in enumerate(all_matched_headers, 1):
            line = f"{i}-{header['title']} ({header['count']}) -> {header['valid_matches']} eşleşme"
            output_lines.append(line)
        
        output_lines.append("-" * 50)
        
        # İçerik çıkarma (sadece ilk geçerli eşleştirme)
        for i, header in enumerate(all_matched_headers, 1):
            baslik_cleaned = header['title']
            konu_sayisi_int = header['count']
            
            # İlk geçerli eşleştirmeyi bul
            first_match = find_first_valid_match(boundaries, baslik_cleaned, konu_sayisi_int)
            
            if first_match:
                output_lines.append(f"{i}-{baslik_cleaned} ({konu_sayisi_int}) -> 1. Eşleşme")
                
                # İçerik çıkarma
                validation_result = ex_ob_tablosu_konu_sinirli_arama(
                    text=full_text,
                    baslik_idx=first_match['content_start'],
                    baslik=baslik_cleaned,
                    konu_sayisi=konu_sayisi_int,
                    all_matched_headers=all_matched_headers
                )
                
                if validation_result and 'content_lines' in validation_result:
                    output_lines.extend(validation_result['content_lines'])
                
                output_lines.append("")  # Boş satır ekle
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"Hata: ex_ob_tablosu fonksiyonunda - {str(e)}"


# Konu içeriklerini sınırlı arama ile çıkarma fonksiyonu - doğrulanmış başlık pozisyonundan sonra sıralı konu yapısını parse eder
# Her konunun tam içeriğini çıkarır ve structured data formatında döndürür
def ex_ob_tablosu_konu_sinirli_arama(text, baslik_idx, baslik, konu_sayisi, all_matched_headers=None):
    """
    Doğrulanmış başlık pozisyonundan sonra sıralı konu yapısını çıkarır
    
    Args:
        text (str): Tam PDF metni
        baslik_idx (int): Başlık pozisyonu
        baslik (str): Başlık metni
        konu_sayisi (int): Beklenen konu sayısı
        all_matched_headers (list): Tüm eşleşen başlıklar
        
    Returns:
        dict: İçerik ve konu listesi
    """
    try:
        # Başlıktan sonraki metni al
        after_baslik = text[baslik_idx + len(baslik):]
        
        # Sonraki başlığın pozisyonunu bul
        next_matched_header_pos = len(after_baslik)  # Varsayılan: sona kadar
        
        if all_matched_headers:
            for header in all_matched_headers:
                if header['position'] > baslik_idx:
                    relative_pos = header['position'] - (baslik_idx + len(baslik))
                    if 0 < relative_pos < next_matched_header_pos:
                        next_matched_header_pos = relative_pos
        
        # Genel pattern'lerle sonraki başlığı ara
        next_header_patterns = [
            r'\n[A-ZÜĞIŞÖÇ][A-ZÜĞIŞÖÇ\s]{10,}',  # Büyük harfle başlayan uzun satır
            r'\n\d+\.\s*[A-ZÜĞIŞÖÇ]',            # Numaralı başlık
            r'DERSİN|DERSĠN',                    # Ders kelimesi
            r'UYGULAMA|FAALİYET|TEMRİN'          # Stop words
        ]
        
        for pattern in next_header_patterns:
            match = re.search(pattern, after_baslik)
            if match and match.start() < next_matched_header_pos:
                next_matched_header_pos = match.start()
        
        # Çalışma alanını sınırla
        work_area = after_baslik[:next_matched_header_pos]
        
        # Sıralı konu çıkarma
        konu_contents = []
        content_lines = []
        current_pos = 0
        
        for konu_no in range(1, konu_sayisi + 1):
            konu_str = str(konu_no)
            patterns = [
                f"{konu_str}. ",     # "1. Konu"
                f"{konu_str} ",      # "1 Konu"  
                f"{konu_str}.",      # "1.Konu" (boşluksuz)
                f" {konu_str}. ",    # " 1. Konu"
                f" {konu_str} ",     # " 1 Konu"
                f" {konu_str}.",     # " 1.Konu"
                f"\n{konu_str}. ",   # Satır başında
                f"\n{konu_str} ",    # Satır başında
                f"\n{konu_str}."     # Satır başında boşluksuz
            ]
            
            found_pos = -1
            used_pattern = ""
            
            for pattern in patterns:
                pos = work_area.find(pattern, current_pos)
                if pos != -1:
                    found_pos = pos
                    used_pattern = pattern
                    break
            
            if found_pos == -1:
                content_lines.append(f"{konu_no}. [Konu bulunamadı]")
                continue
            
            # Sonraki konu numarasına kadar olan metni al
            if konu_no < konu_sayisi:
                next_konu_str = str(konu_no + 1)
                next_patterns = [
                    f"{next_konu_str}. ",     # "2. Konu"
                    f"{next_konu_str} ",      # "2 Konu"  
                    f"{next_konu_str}.",      # "2.Konu" (boşluksuz)
                    f" {next_konu_str}. ",    # " 2. Konu"
                    f" {next_konu_str} ",     # " 2 Konu"
                    f" {next_konu_str}.",     # " 2.Konu"
                    f"\n{next_konu_str}. ",   # Satır başında
                    f"\n{next_konu_str} ",    # Satır başında
                    f"\n{next_konu_str}."     # Satır başında boşluksuz
                ]
                
                next_found_pos = len(work_area)
                for next_pattern in next_patterns:
                    next_pos = work_area.find(next_pattern, found_pos + 1)
                    if next_pos != -1 and next_pos < next_found_pos:
                        next_found_pos = next_pos
                
                konu_content = work_area[found_pos:next_found_pos]
            else:
                # Son konu - sona kadar al
                konu_content = work_area[found_pos:]
            
            # İçeriği temizle
            cleaned_content = konu_content.strip()
            
            # Konu numarasını temizle (sadece gerçek konu numaralarını)
            if cleaned_content.startswith(f"{konu_no}. "):
                cleaned_content = cleaned_content.replace(f"{konu_no}. ", "", 1)
            elif cleaned_content.startswith(f"{konu_no} "):
                cleaned_content = cleaned_content.replace(f"{konu_no} ", "", 1)
            
            # Whitespace normalize et
            cleaned_content = re.sub(r'\s+', ' ', cleaned_content.strip())
            
            # İçeriği kaydet
            konu_contents.append({
                'konu_no': konu_no,
                'konu_adi': cleaned_content.split('\n')[0].strip() if cleaned_content else f"Konu {konu_no}",
                'konu_icerigi': cleaned_content
            })
            
            content_lines.append(f"{konu_no}. {cleaned_content}")
            current_pos = found_pos + len(used_pattern)
        
        return {
            'success': True,
            'content_lines': content_lines,
            'konu_contents': konu_contents,
            'baslik': baslik,
            'konu_sayisi': konu_sayisi
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'content_lines': [f"Hata: {str(e)}"],
            'konu_contents': []
        }


# Yedek plan fonksiyonu - ana string matching başarısız olduğunda alternatif yöntemlerle başlık pozisyonu bulur
# "1" rakamı tabanlı pattern matching ile potansiyel başlıkları tespit eder ve doğrular
def ex_ob_tablosu_konu_bulma_yedek_plan(text, original_baslik, konu_sayisi):
    """
    Ana eşleştirme başarısız olduğunda alternatif yöntemlerle başlık arar
    
    Args:
        text (str): Aranacak metin
        original_baslik (str): Orijinal başlık
        konu_sayisi (int): Beklenen konu sayısı
        
    Returns:
        dict: Alternatif eşleştirme bilgisi veya None
    """
    try:
        # "1" rakamını cümle başında veya nokta sonrası ara
        one_pattern = r'(?:^|\.|\\n|\\s)1(?:\.|\\s)'
        matches = list(re.finditer(one_pattern, text))
        
        for match in matches:
            one_pos = match.start()
            
            # "1" den önceki cümleyi bul (maksimum 100 karakter geriye git)
            start_search = max(0, one_pos - 100)
            before_one = text[start_search:one_pos]
            
            # Cümle sınırlarını bul
            sentences = re.split(r'[.!?]', before_one)
            potential_title = sentences[-1].strip()
            
            # Başlık çok kısaysa atla
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
        
    except Exception as e:
        print(f"Yedek plan hatası: {str(e)}")
        return None


# ===========================
# DATABASE INTEGRATION (Future)
# ===========================

# Database kayıt fonksiyonu (gelecekte implement edilecek)
@with_database  
def save_ogrenme_birimi_to_database(cursor, ders_id, structured_data):
    """
    Structured data'yı database tablolarına kaydeder
    
    Args:
        cursor: Database cursor
        ders_id: temel_plan_ders.id
        structured_data: ex_ob_tablosu() çıktısı
        
    Returns:
        dict: {'success': bool, 'stats': {...}, 'error': str}
    """
    # TODO: Implement database saving logic
    return {'success': False, 'error': 'Not implemented yet'}