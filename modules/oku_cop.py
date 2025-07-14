"""
ÇÖP PDF Okuma ve Analiz Modülü

Bu modül ÇÖP (Çerçeve Öğretim Programı) PDF dosyalarından alan, dal ve ders bilgilerini çıkarır.
Hem yerel dosyalar hem de URL'ler desteklenir.

Sorumluluklar:
- PDF içerik çıkarma (text extraction)
- Alan/dal/ders algoritmaları  
- İçindekiler analizi
- Tablo parsing ve ders listesi çıkarma
- Geliştirilmiş algoritma implementasyonları

Bu modül getir_cop_oku_local.py'deki geliştirilmiş algoritmaları kullanır.
"""

import os
import re
import json
import requests
import tempfile
from typing import Dict, List, Any, Optional, Tuple

import pdfplumber

try:
    from .utils import normalize_to_title_case_tr, get_temp_pdf_path
except ImportError:
    # Stand-alone çalışma durumunda
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from modules.utils import normalize_to_title_case_tr, get_temp_pdf_path


# ------------- ORTAK YARDIMCI FONKSİYONLAR ------------- #

def clean_text(text: str) -> str:
    """
    Gereksiz karakterleri ve çoklu boşlukları temizler.
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.replace("\x00", "").replace("\ufffd", "")
    return text.strip()


def extract_alan_from_url(pdf_url: str) -> Optional[str]:
    """
    PDF URL'sinden alan adını tahmin et
    Örnek: https://meslek.meb.gov.tr/upload/cop12/adalet_12.pdf -> Adalet
    """
    if not pdf_url:
        return None
        
    try:
        # URL'den dosya adını çıkar
        filename = pdf_url.split('/')[-1]
        
        # Alan adı mapping'i - getir_cop_oku_local.py'den uyarlandı
        alan_mapping = {
            'adalet': 'Adalet',
            'aile': 'Aile ve Tüketici Hizmetleri',
            'bilisim': 'Bilişim Teknolojileri',
            'biyomedikal': 'Biyomedikal Cihaz Teknolojileri',
            'buro': 'Büro Yönetimi ve Yönetici Asistanlığı',
            'cocukgelisimi': 'Çocuk Gelişimi ve Eğitimi',
            'denizcilik': 'Denizcilik',
            'elektrik': 'Elektrik-Elektronik Teknolojisi',
            'gida': 'Gıda Teknolojisi',
            'saglik': 'Sağlık Hizmetleri',
            'makine': 'Makine ve Tasarım Teknolojisi',
            'motorluarac': 'Motorlu Araçlar Teknolojisi',
            'tekstil': 'Tekstil Teknolojisi',
            'insaat': 'İnşaat Teknolojisi',
            'muhasebepro': 'Muhasebe ve Finansman',
            'pazarlama': 'Pazarlama ve Perakende',
            'ayakkabipro': 'Ayakkabı ve Saraciye',
            'kimya': 'Kimya Teknolojisi',
            'turizm': 'Konaklama ve Seyahat Hizmetleri',
        }
        
        # Dosya adından alan kısmını çıkar
        for key, value in alan_mapping.items():
            if key in filename.lower():
                return value
                
        # Mapping'de yoksa dosya adından tahmin et
        base_name = filename.replace('.pdf', '').split('_')[0]
        return normalize_to_title_case_tr(base_name)
        
    except:
        return None


# ------------- ALAN ADI ÇIKARMA ------------- #

def find_alan_name_in_text(text: str, pdf_url: str = "") -> Optional[str]:
    """
    PDF metninden alan adını çıkar - geliştirilmiş versiyon
    getir_cop_oku_local.py'den uyarlandı
    """
    # 1. Önce URL'den alan adını tahmin etmeye çalış (eğer URL varsa)
    url_alan = None
    if pdf_url:
        url_alan = extract_alan_from_url(pdf_url)
    
    # 2. Metinden alan adını bulmaya çalış
    lines = text.split('\n')
    found_alan = None
    
    for i, line in enumerate(lines[:100]):  # İlk 100 satırda ara
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        # Pattern 1: "XXX ALANI" biçimindeki başlıklar
        if line_upper.endswith(' ALANI') and len(line_clean) > 10:
            alan_adi = line_upper.replace(' ALANI', '').strip()
            # Gereksiz kelimeler içermiyorsa ve rakam ile başlamıyorsa
            if (not any(bad in alan_adi for bad in ["ÇERÇEVE", "ÖĞRETİM", "PROGRAM", "AMAÇLAR", "5."]) 
                and not alan_adi[0].isdigit()):
                found_alan = normalize_to_title_case_tr(alan_adi)
                break
        
        # Pattern 2: "ALAN ADI" sonrası
        if 'ALAN' in line_upper and ('ADI' in line_upper or 'ALANI' in line_upper):
            # Sonraki satırları kontrol et
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = clean_text(lines[j]).strip()
                if (len(next_line) > 5 and not next_line.upper().startswith('T.C.') 
                    and not any(bad in next_line.upper() for bad in ["ÇERÇEVE", "ÖĞRETİM", "PROGRAM", "AMAÇLAR", "5."])):
                    found_alan = normalize_to_title_case_tr(next_line)
                    break
    
    # 3. PDF'den bulunan alan adı geçerliyse kullan, değilse URL'den fallback
    if found_alan and len(found_alan) > 3:
        if (len(found_alan) < 100 and  # Çok uzun değil
            not any(bad in found_alan.upper() for bad in ["AMAÇLARI", "ÜRETIMIN", "KADEMESINDE", "5.1.", "5.2.", "5.3."])):
            return found_alan
    
    # 4. Hiçbir şey bulunamazsa URL'den tahmin edilen alan adını kullan
    if url_alan:
        print(f"⚠️  PDF'den alan adı bulunamadı, URL'den tahmin ediliyor: {url_alan}")
        return url_alan
    
    return None


def find_alan_from_icindekiler(text: str, debug: bool = False) -> Optional[str]:
    """
    PDF'in içindekiler kısmından alan adını çıkarır.
    getir_cop_oku_local.py'den uyarlandı
    """
    if debug:
        print("\\n🔍 İçindekiler'den alan adı arama...")
    
    # İçindekiler bölümünü bul
    icindekiler_text = extract_icindekiler_section(text)
    if not icindekiler_text:
        if debug:
            print("❌ İçindekiler bölümü bulunamadı")
        return None
    
    if debug:
        print(f"📄 İçindekiler metni ({len(icindekiler_text)} karakter):")
        print(icindekiler_text[:500] + "..." if len(icindekiler_text) > 500 else icindekiler_text)
    
    lines = icindekiler_text.split('\n')
    
    for i, line in enumerate(lines):
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        # "ALANI" ile biten satırları bul
        if line_upper.endswith(' ALANI') and len(line_clean) > 10:
            alan_adi = line_upper.replace(' ALANI', '').strip()
            # Gereksiz kelimeler içermiyorsa
            if not any(bad in alan_adi for bad in ["ÇERÇEVE", "ÖĞRETİM", "PROGRAM", "AMAÇLAR"]):
                result = normalize_to_title_case_tr(alan_adi)
                if debug:
                    print(f"✅ Alan adı bulundu: {result}")
                return result
    
    if debug:
        print("❌ İçindekiler'de alan adı bulunamadı")
    return None


# ------------- DAL ÇIKARMA ------------- #

def find_dallar_from_icindekiler(text: str, debug: bool = False) -> List[str]:
    """
    PDF'in içindekiler kısmından dal adlarını çıkarır.
    Basit yaklaşım: "DALI" kelimesini bulduğumuzda öncesindeki kısmı alırız.
    getir_cop_oku_local.py'den uyarlandı ve basitleştirildi
    """
    if debug:
        print("\\n🔍 İçindekiler'den dal arama...")
    
    # İçindekiler bölümünü bul
    icindekiler_text = extract_icindekiler_section(text)
    if not icindekiler_text:
        if debug:
            print("❌ İçindekiler bölümü bulunamadı")
        return []
    
    lines = icindekiler_text.split('\n')
    dallar = []
    
    for i, line in enumerate(lines):
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        if ('DALI' in line_upper and 
            len(line_clean) > 10 and
            not any(bad in line_upper for bad in ['ANADOLU MESLEK PROGRAMI', 'TEKNİK PROGRAMI'])):
            
            # "DALI" öncesindeki kısmı al
            dal_text = re.sub(r'\s*DALI.*', '', line_clean, flags=re.IGNORECASE)
            dal_text = dal_text.strip()
            
            if (len(dal_text) > 3 and 
                not any(bad in dal_text.upper() for bad in ['ANADOLU', 'MESLEK', 'TEKNİK', 'PROGRAM'])):
                dallar.append(normalize_to_title_case_tr(dal_text))
                if debug:
                    print(f"✅ Dal bulundu: {dal_text}")
    
    # Tekrarları kaldır
    dallar = list(set(dallar))
    
    if debug:
        print(f"📋 Toplam {len(dallar)} dal bulundu: {dallar}")
    
    return dallar


def extract_icindekiler_section(text: str) -> str:
    """
    PDF metninden içindekiler bölümünü çıkarır.
    getir_cop_oku_local.py'den uyarlandı
    """
    lines = text.split('\n')
    icindekiler_start = -1
    icindekiler_end = -1
    
    # İçindekiler başlangıcını bul
    for i, line in enumerate(lines):
        line_upper = line.upper().strip()
        if 'İÇİNDEKİLER' in line_upper and len(line_upper) < 50:
            icindekiler_start = i
            break
    
    if icindekiler_start == -1:
        return ""
    
    # İçindekiler bitişini bul
    for i in range(icindekiler_start + 1, min(icindekiler_start + 100, len(lines))):
        line_upper = lines[i].upper().strip()
        
        # Çerçeve öğretim programının amaçları veya benzeri bölüm başladığında dur
        if (any(keyword in line_upper for keyword in [
            'ÇERÇEVE ÖĞRETİM PROGRAMININ AMAÇLARI',
            'PROGRAMIN AMAÇLARI', 
            'GENEL AMAÇLAR',
            'ÖZEL AMAÇLAR',
            'TEMEL BECERİLER'
        ]) and len(line_upper) > 10):
            icindekiler_end = i
            break
    
    # Eğer bitiş bulunamazsa, makul bir limit koy
    if icindekiler_end == -1:
        icindekiler_end = min(icindekiler_start + 50, len(lines))
    
    # İçindekiler kısmını birleştir
    icindekiler_lines = lines[icindekiler_start:icindekiler_end]
    return '\\n'.join(icindekiler_lines)


# ------------- DERS ÇIKARMA ------------- #

def find_lessons_in_cop_pdf(pdf, alan_adi: str, debug: bool = False) -> Dict[str, List[str]]:
    """
    COP PDF'sinden dal ve ders bilgilerini çıkar.
    HAFTALIK DERS ÇİZELGELERİ bölümünden dal-ders eşleştirmesi yapar.
    getir_cop_oku.py'den uyarlandı ve geliştirildi
    """
    dal_ders_map = {}
    current_dal = None
    
    try:
        for page_num, page in enumerate(pdf.pages, 1):
            if debug and page_num <= 3:
                print(f"\\n📄 Sayfa {page_num} işleniyor...")
            
            page_text = page.extract_text()
            if not page_text:
                continue
            
            # HAFTALIK DERS ÇİZELGESİ veya dal adı arama
            if 'HAFTALIK DERS ÇİZELGESİ' in page_text.upper():
                # Dal adını bul
                dal_name = extract_dal_from_page_title(page_text)
                if dal_name:
                    current_dal = dal_name
                    if current_dal not in dal_ders_map:
                        dal_ders_map[current_dal] = []
                    
                    if debug:
                        print(f"🎯 Dal bulundu: {current_dal}")
                
                # Bu sayfadaki dersleri çıkar
                lessons = extract_lessons_from_page(page, page_num, debug)
                if current_dal and lessons:
                    # Mevcut derslere ekle (tekrar kontrolü ile)
                    for lesson in lessons:
                        if lesson not in dal_ders_map[current_dal]:
                            dal_ders_map[current_dal].append(lesson)
                    
                    if debug:
                        print(f"📚 {len(lessons)} ders eklendi: {lessons}")
    
    except Exception as e:
        if debug:
            print(f"❌ PDF işleme hatası: {e}")
    
    # Sonuçları temizle
    for dal in dal_ders_map:
        dal_ders_map[dal] = list(set(dal_ders_map[dal]))  # Tekrarları kaldır
        dal_ders_map[dal].sort()  # Alfabetik sırala
    
    if debug:
        print(f"\\n📊 Toplam sonuç: {len(dal_ders_map)} dal")
        for dal, dersler in dal_ders_map.items():
            print(f"  - {dal}: {len(dersler)} ders")
    
    return dal_ders_map


def extract_dal_from_page_title(page_text: str) -> Optional[str]:
    """
    Sayfa metninden dal adını çıkar.
    "HAFTALIK DERS ÇİZELGESİ" öncesindeki satırlardan dal adını bul.
    """
    lines = page_text.split('\n')
    
    for i, line in enumerate(lines):
        line_upper = line.upper().strip()
        
        if 'HAFTALIK DERS ÇİZELGESİ' in line_upper:
            # Önceki 5 satıra bak
            for j in range(max(0, i-5), i):
                prev_line = clean_text(lines[j]).strip()
                prev_upper = prev_line.upper()
                
                # Dal adı pattern'leri
                if (('DALI' in prev_upper or 'PROGRAMI' in prev_upper) and 
                    len(prev_line) > 5 and len(prev_line) < 100 and
                    not any(bad in prev_upper for bad in ['ÇERÇEVE', 'ÖĞRETİM', 'AMAÇLAR', 'SINIF'])):
                    
                    # "DALI" veya "PROGRAMI" kelimesini temizle
                    dal_name = re.sub(r'\s+(DALI|PROGRAMI).*', '', prev_line, flags=re.IGNORECASE).strip()
                    if len(dal_name) > 3:
                        return normalize_to_title_case_tr(dal_name)
    
    return None


def extract_lessons_from_page(page, page_num: int, debug: bool = False) -> List[str]:
    """
    Sayfadan ders listesini çıkar.
    Geliştirilmiş algoritma - dinamik sütun algılama.
    getir_cop_oku_local.py'den uyarlandı
    """
    lessons = []
    
    try:
        # Önce tabloları dene
        tables = page.extract_tables()
        
        for table_idx, table in enumerate(tables):
            if not table:
                continue
            
            # MESLEK DERSLERİ bölümünü bul
            meslek_dersleri_row = find_meslek_dersleri_section_in_table(table)
            if meslek_dersleri_row is None:
                continue
            
            # Kategori sütununu dinamik olarak bul
            category_col = find_category_column_dynamic(table, debug)
            if category_col is None:
                continue
            
            if debug:
                print(f"  📊 Tablo {table_idx}: MESLEK DERSLERİ satır {meslek_dersleri_row}, kategori sütun {category_col}")
            
            # MESLEK DERSLERİ satırından sonraki dersleri çıkar
            for row_idx in range(meslek_dersleri_row + 1, len(table)):
                row = table[row_idx]
                
                if category_col < len(row):
                    ders_adi = row[category_col]
                    
                    if ders_adi and isinstance(ders_adi, str):
                        ders_clean = clean_text(ders_adi).strip()
                        
                        # Dipnot & artık temizliği
                        ders_clean = re.sub(r"\(\*+\)", "", ders_clean)          # dipnot (*)
                        ders_clean = re.sub(r"-+\s*\d+\s*-", "", ders_clean)    # --2-, -3-
                        ders_clean = re.sub(r"\s{2,}", " ", ders_clean).strip()
                        
                        # Geçerli ders adı kontrolü
                        if (len(ders_clean) > 3 and 
                            not ders_clean.upper().startswith(('TOPLAM', 'HAFTALIK', 'GENEL')) and
                            not ders_clean.isdigit() and
                            not any(bad in ders_clean.upper() for bad in ['TOPLAM', 'HAFTALIK', 'GENEL'])):
                            lessons.append(normalize_to_title_case_tr(ders_clean))
                
                # Eğer başka bir bölüm başladıysa dur
                if any(cell and isinstance(cell, str) and 
                      ('ALAN' in str(cell).upper() or 'BÖLÜM' in str(cell).upper()) 
                      for cell in row):
                    break
        
        # Tablo bulunamazsa metin bazlı analiz
        if not lessons:
            page_text = page.extract_text() or ""
            lessons = extract_lessons_from_text(page_text, debug)
    
    except Exception as e:
        if debug:
            print(f"  ❌ Sayfa {page_num} ders çıkarma hatası: {e}")
    
    return lessons


def find_meslek_dersleri_section_in_table(table: List[List[str]]) -> Optional[int]:
    """
    Tabloda MESLEK DERSLERİ bölümünün satır numarasını bul.
    """
    for row_idx, row in enumerate(table):
        for cell in row:
            if cell and isinstance(cell, str):
                cell_upper = str(cell).upper()
                if 'MESLEK DERSLERİ' in cell_upper or 'MESLEK ALAN DERSLERİ' in cell_upper:
                    return row_idx
    return None


def find_category_column_dynamic(table: List[List[str]], debug: bool = False) -> Optional[int]:
    """
    Tabloda kategori sütununu dinamik olarak bul.
    "MESLEK" kelimesini içeren sütunu arar.
    getir_cop_oku_local.py'den uyarlandı
    """
    if not table:
        return None
    
    # İlk birkaç satırda "MESLEK" kelimesini ara
    for row_idx in range(min(5, len(table))):
        row = table[row_idx]
        for col_idx, cell in enumerate(row):
            if cell and isinstance(cell, str):
                cell_upper = str(cell).upper()
                if 'MESLEK' in cell_upper:
                    if debug:
                        print(f"    🎯 Kategori sütunu bulundu: {col_idx} ('{cell}')")
                    return col_idx
    
    # Bulunamazsa varsayılan olarak 0. sütun
    if debug:
        print("    ⚠️ Kategori sütunu bulunamadı, 0. sütun kullanılıyor")
    return 0


def extract_lessons_from_text(page_text: str, debug: bool = False) -> List[str]:
    """
    Sayfa metninden ders listesini çıkar (tablo alternatifi).
    """
    lessons = []
    lines = page_text.split("\n")
    
    for idx, line in enumerate(lines):
        line_upper = line.upper()
        
        if "MESLEK DERSLERİ" in line_upper or "MESLEK ALAN DERSLERİ" in line_upper:
            # Bu satırdan sonraki 20 satırda ders isimlerini ara
            for i in range(idx + 1, min(idx + 21, len(lines))):
                lesson_line = clean_text(lines[i]).strip()
                
                if (len(lesson_line) > 3 and 
                    not lesson_line.upper().startswith(('TOPLAM', 'HAFTALIK', 'GENEL')) and
                    not lesson_line.isdigit()):
                    lessons.append(normalize_to_title_case_tr(lesson_line))
            
            break
    
    return lessons


# ------------- ANA FONKSİYONLAR ------------- #

def extract_alan_dal_ders_from_pdf(pdf_source: str, debug: bool = False) -> Tuple[Optional[str], List[str], Dict[str, List[str]]]:
    """
    PDF dosyasından alan, dal ve ders bilgilerini çıkar.
    
    Args:
        pdf_source: PDF dosya yolu veya URL
        debug: Debug modunu aktifleştir
    
    Returns:
        Tuple[alan_adi, dallar, dal_ders_map]: (alan adı, dal listesi, {dal: [dersler]})
    """
    if debug:
        print(f"\\n🔍 PDF analiz ediliyor: {pdf_source}")
    
    alan_adi = None
    dallar = []
    dal_ders_map = {}
    
    try:
        # PDF'yi aç (yerel dosya veya URL)
        if pdf_source.startswith('http'):
            # URL ise geçici indir
            response = requests.get(pdf_source, timeout=30)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(response.content)
                pdf_path = tmp_file.name
        else:
            # Yerel dosya
            pdf_path = pdf_source
        
        with pdfplumber.open(pdf_path) as pdf:
            # Tüm metni çıkar
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            if debug:
                print(f"📄 Toplam {len(pdf.pages)} sayfa, {len(full_text)} karakter")
            
            # 1. Alan adını bul
            alan_adi = find_alan_name_in_text(full_text, pdf_source if pdf_source.startswith('http') else "")
            if not alan_adi:
                alan_adi = find_alan_from_icindekiler(full_text, debug)
            
            # 2. Dalları bul
            dallar = find_dallar_from_icindekiler(full_text, debug)
            
            # 3. Ders listesini çıkar
            dal_ders_map = find_lessons_in_cop_pdf(pdf, alan_adi or "Bilinmiyor", debug)
        
        # Geçici dosyayı temizle
        if pdf_source.startswith('http'):
            try:
                os.unlink(pdf_path)
            except:
                pass
    
    except Exception as e:
        if debug:
            print(f"❌ PDF okuma hatası: {e}")
        return None, [], {}
    
    if debug:
        print(f"\\n📊 Sonuç:")
        print(f"  🏢 Alan: {alan_adi}")
        print(f"  🔧 Dallar ({len(dallar)}): {dallar}")
        print(f"  📚 Dal-Ders Eşleştirmesi ({len(dal_ders_map)} dal):")
        for dal, dersler in dal_ders_map.items():
            print(f"    - {dal}: {len(dersler)} ders")
    
    return alan_adi, dallar, dal_ders_map


def oku_cop_pdf(pdf_source: str, debug: bool = False) -> Dict[str, Any]:
    """
    ÇÖP PDF'sini okur ve JSON formatında sonuç döndürür.
    
    Args:
        pdf_source: PDF dosya yolu veya URL
        debug: Debug modunu aktifleştir
    
    Returns:
        Dict: {
            "alan_adi": str,
            "dallar": List[str],
            "dal_ders_map": Dict[str, List[str]],
            "success": bool,
            "error": Optional[str]
        }
    """
    try:
        alan_adi, dallar, dal_ders_map = extract_alan_dal_ders_from_pdf(pdf_source, debug)
        
        return {
            "alan_adi": alan_adi,
            "dallar": dallar,
            "dal_ders_map": dal_ders_map,
            "success": True,
            "error": None
        }
    
    except Exception as e:
        error_msg = f"PDF okuma hatası: {str(e)}"
        if debug:
            print(f"❌ {error_msg}")
        
        return {
            "alan_adi": None,
            "dallar": [],
            "dal_ders_map": {},
            "success": False,
            "error": error_msg
        }


def validate_pdf_content(pdf_source: str) -> Dict[str, Any]:
    """
    PDF içeriğinin geçerliliğini kontrol eder.
    
    Args:
        pdf_source: PDF dosya yolu veya URL
    
    Returns:
        Dict: Validation sonuçları
    """
    try:
        result = oku_cop_pdf(pdf_source, debug=False)
        
        validation = {
            "is_valid": False,
            "has_alan": bool(result["alan_adi"]),
            "has_dallar": len(result["dallar"]) > 0,
            "has_dersler": len(result["dal_ders_map"]) > 0,
            "total_dersler": sum(len(dersler) for dersler in result["dal_ders_map"].values()),
            "error": result["error"]
        }
        
        # Geçerlilik kriterleri
        validation["is_valid"] = (
            validation["has_alan"] and 
            (validation["has_dallar"] or validation["has_dersler"])
        )
        
        return validation
    
    except Exception as e:
        return {
            "is_valid": False,
            "has_alan": False,
            "has_dallar": False,
            "has_dersler": False,
            "total_dersler": 0,
            "error": str(e)
        }


# ------------- YEREL DOSYA İŞLEMLERİ ------------- #

def oku_cop_pdf_file(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    """
    Yerel PDF dosyasını okur.
    
    Args:
        pdf_path: PDF dosyasının yerel yolu
        debug: Debug modunu aktifleştir
    
    Returns:
        Dict: oku_cop_pdf() ile aynı format
    """
    if not os.path.exists(pdf_path):
        return {
            "alan_adi": None,
            "dallar": [],
            "dal_ders_map": {},
            "success": False,
            "error": f"Dosya bulunamadı: {pdf_path}"
        }
    
    return oku_cop_pdf(pdf_path, debug)


def oku_folder_pdfler(folder_path: str, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Klasördeki tüm PDF dosyalarını okur.
    
    Args:
        folder_path: Klasör yolu
        debug: Debug modunu aktifleştir
    
    Returns:
        Dict: {dosya_adi: oku_cop_pdf_sonucu}
    """
    if not os.path.exists(folder_path):
        print(f"❌ Klasör bulunamadı: {folder_path}")
        return {}
    
    results = {}
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"⚠️ Klasörde PDF dosyası bulunamadı: {folder_path}")
        return {}
    
    print(f"📁 {folder_path} klasöründe {len(pdf_files)} PDF bulundu")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        print(f"\\n🔄 İşleniyor: {pdf_file}")
        
        result = oku_cop_pdf_file(pdf_path, debug)
        results[pdf_file] = result
        
        if result["success"]:
            print(f"✅ Başarılı: Alan={result['alan_adi']}, Dal={len(result['dallar'])}, Ders={sum(len(d) for d in result['dal_ders_map'].values())}")
        else:
            print(f"❌ Başarısız: {result['error']}")
    
    return results


if __name__ == "__main__":
    # Test amaçlı çalıştırma
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        
        if os.path.isdir(pdf_path):
            # Klasör testi
            print(f"🚀 Klasör testi: {pdf_path}")
            results = oku_folder_pdfler(pdf_path, debug=True)
            
            print(f"\\n📊 Özet: {len(results)} dosya işlendi")
            successful = sum(1 for r in results.values() if r["success"])
            print(f"✅ Başarılı: {successful}")
            print(f"❌ Başarısız: {len(results) - successful}")
        
        else:
            # Tek dosya testi
            print(f"🚀 PDF testi: {pdf_path}")
            result = oku_cop_pdf_file(pdf_path, debug=True)
            
            if result["success"]:
                print("\\n✅ Test başarılı!")
            else:
                print(f"\\n❌ Test başarısız: {result['error']}")
    
    else:
        print("Kullanım: python oku_cop.py <pdf_dosyasi_veya_klasor>")
        print("Örnek: python oku_cop.py gida_12_cop_program.pdf")
        print("Örnek: python oku_cop.py data/cop/gida_12/")