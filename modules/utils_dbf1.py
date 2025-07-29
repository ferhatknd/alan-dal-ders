"""
modules/utils_dbf1.py
=====================
PDF'nin 1. sayfasındaki temel bilgiler ve kazanım tablosu işlemleri
- ex_temel_bilgiler(): Ders adı, sınıf, süre, amaç çıkarma
- ex_kazanim_tablosu(): Kazanım sayısı ve süre tablosu parse etme
- read_full_text_from_file(): PDF/DOCX okuma (fitz kullanılan tek yer)
"""

import fitz  # PyMuPDF
import re
import os

# Modüler import'lar (read_full_text_from_file locally defined below)


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


# ===========================
# PAGE 1 PROCESSING FUNCTIONS
# ===========================

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
            result = "KAZANIM SAYISI VE SÜRE TABLOSU:\n"
            for idx, line in enumerate(lines, 1):
                result += f"{idx}-{line}\n"
            return result.strip(), structured_data
        else:
            return "KAZANIM SAYISI VE SÜRE TABLOSU - Veri bulunamadı", []
                
    except Exception as e:
        return f"KAZANIM SAYISI VE SÜRE TABLOSU - HATA: {str(e)}", []


# ===========================
# FILE I/O FUNCTIONS
# ===========================

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
            full_text += page.get_text() + "\n"
        doc.close()
        
        # Metni normalize et
        full_text = re.sub(r'\s+', ' ', full_text)
        return full_text
        
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return ""


def get_all_dbf_files(validate_files=True):
    """
    DBF PDF ve DOCX dosyalarını bulma ve yönetme fonksiyonu - API sistemine optimize edildi
    
    Args:
        validate_files (bool): Dosya bütünlüğü kontrolü yap (varsayılan: True)
    
    Returns:
        list: PDF ve DOCX dosya yolları listesi (sadece geçerli dosyalar)
    """
    # utils_env modülünü kullan
    try:
        from .utils_env import get_data_path, get_project_root
    except ImportError:
        from utils_env import get_data_path, get_project_root
    
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


def process_dbf_file(file_path):
    """
    Tek DBF dosyasını işler ve sonuçları döndürür
    
    Args:
        file_path (str): İşlenecek dosya yolu
        
    Returns:
        dict: İşlem sonucu
    """
    try:
        # Import dbf2 functions here to avoid circular dependency
        try:
            from .utils_dbf2 import ex_ob_tablosu
        except ImportError:
            from utils_dbf2 import ex_ob_tablosu
        
        # Dosyadan tam metni oku
        full_text = read_full_text_from_file(file_path)
        
        if not full_text.strip():
            return {"success": False, "error": "Dosya içeriği boş", "file_path": file_path}
        
        # Temel bilgileri çıkar (dbf1)
        temel_bilgiler = ex_temel_bilgiler(full_text)
        
        # Kazanım tablosunu çıkar (dbf1)
        kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text)
        
        # Öğrenme birimi analizini yap (dbf2 - text pass edilir, fitz kullanılmaz)
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
        "success": success_count > 0,
        "total_files": len(file_paths),
        "success_count": success_count,
        "error_count": error_count,
        "results": results
    }