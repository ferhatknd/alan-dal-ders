"""
ÇÖP PDF Okuma ve Analiz Modülü (Kural Tabanlı)

Bu modül, ÇÖP PDF'lerinden alan, dal ve ders bilgilerini,
kullanıcı tarafından belirtilen kesin kurallara göre çıkarır.

İş Akışı:
1. Alan/Dal: Sadece "İÇİNDEKİLER" bölümünden "... Alanı" ve "... Dalı" kalıplarıyla çıkarılır.
2. Ders/Saat/Sınıf: Sadece "HAFTALIK DERS ÇİZELGESİ" tablolarındaki "MESLEK DERSLERİ"
   bölümünden, sınıf sütunlarındaki saatlerle birlikte çıkarılır.
3. Eşleştirme: Bulunan tüm dallar, bulunan tüm meslek dersleriyle eşleştirilir.
"""

import os
import re
import requests
import tempfile
from typing import Dict, List, Any, Optional, Tuple

import pdfplumber

try:
    from .utils import normalize_to_title_case_tr
except ImportError:
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from modules.utils import normalize_to_title_case_tr

# ------------- YARDIMCI FONKSİYONLAR ------------- #

def clean_text(text: str) -> str:
    if not text: return ""
    return re.sub(r"\s+", " ", text).strip()

def find_grade_columns(header_row: List[str]) -> Dict[str, int]:
    grade_cols: Dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        if not cell: continue
        text = str(cell).strip().upper()
        if text.startswith("9"): grade_cols["9"] = idx
        elif text.startswith("10"): grade_cols["10"] = idx
        elif text.startswith("11"): grade_cols["11"] = idx
        elif text.startswith("12"): grade_cols["12"] = idx
    return grade_cols

def merge_lesson_dicts(list1: List[Dict[str, Any]], list2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for lesson in list1 + list2:
        key = lesson.get("adi")
        if not key: continue
        if key in merged:
            for grade, val in lesson.get("saatler", {}).items():
                if val and merged[key]["saatler"].get(grade, 0) == 0:
                    merged[key]["saatler"][grade] = val
        else:
            merged[key] = {"adi": key, "saatler": lesson.get("saatler", {})}
    return list(merged.values())

# ------------- KURAL 1: ALAN VE DAL ÇIKARIMI (SADECE İÇİNDEKİLER) ------------- #

def extract_icindekiler_section(full_text: str) -> str:
    """PDF metninden sadece 'İÇİNDEKİLER' bölümünü çıkarır."""
    lines = full_text.split('\n')
    start_idx, end_idx = -1, -1
    for i, line in enumerate(lines):
        if 'İÇİNDEKİLER' in line.upper().strip() and len(line.strip()) < 30:
            start_idx = i
            break
    if start_idx == -1: return ""

    stop_keywords = [
        'ÇERÇEVE ÖĞRETİM PROGRAMININ AMAÇLARI', 'PROGRAMIN AMAÇLARI',
        'GENEL AMAÇLAR', 'GİRİŞ', '1. GİRİŞ'
    ]
    for i in range(start_idx + 1, len(lines)):
        line_upper = lines[i].upper().strip()
        if any(keyword in line_upper for keyword in stop_keywords):
            end_idx = i
            break
    
    if end_idx == -1: end_idx = start_idx + 100 # Makul bir limit
    
    return "\n".join(lines[start_idx:end_idx])

def extract_alan_dal_from_icindekiler(icindekiler_text: str) -> Tuple[Optional[str], List[str]]:
    """'İçindekiler' metninden Alan ve Dal adlarını çıkarır."""
    alan_adi, dallar = None, []
    lines = icindekiler_text.split('\n')
    
    for line in lines:
        line_clean = clean_text(line)
        line_upper = line_clean.upper()
        
        # Alan Adı
        if not alan_adi and " ALANI" in line_upper:
            # "ALANI" kelimesinden önceki kısmı al (sondakini bul)
            potential_alan = line_clean[:line_upper.rfind(" ALANI")].strip()
            # Sayfa numarası ve liste işaretleri gibi artıkları temizle
            potential_alan = re.sub(r'\s+\.\.\..*$', '', potential_alan).strip()
            potential_alan = re.sub(r'^\d+\.?\s*', '', potential_alan).strip()
            if len(potential_alan) > 3:
                alan_adi = normalize_to_title_case_tr(potential_alan)

        # Dal Adı
        if " DALI" in line_upper:
            potential_dal = line_clean[:line_upper.rfind(" DALI")].strip()
            potential_dal = re.sub(r'\s+\.\.\..*$', '', potential_dal).strip()
            potential_dal = re.sub(r'^\d+\.\d+\.?\s*', '', potential_dal).strip()
            if len(potential_dal) > 3:
                dallar.append(normalize_to_title_case_tr(potential_dal))

    # Dalların içinde alan adı olabilir, onu temizleyelim.
    if alan_adi:
        dallar = [dal for dal in dallar if dal.upper() != alan_adi.upper()]

    return alan_adi, list(set(dallar))


# ------------- KURAL 2: DERS/SAAT/SINIF ÇIKARIMI (SADECE HAFTALIK DERS ÇİZELGELERİ) ------------- #

def extract_all_meslek_dersleri(pdf: pdfplumber.PDF) -> List[Dict[str, Any]]:
    """
    PDF'teki tüm 'Haftalık Ders Çizelgesi' tablolarından 'Meslek Dersleri'ni ve saatlerini çıkarır.
    """
    all_lessons: List[Dict[str, Any]] = []
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text or 'HAFTALIK DERS ÇİZELGESİ' not in text.upper():
            continue

        tables = page.extract_tables()
        for table in tables:
            if not table: continue

            # Meslek Dersleri bölümünün başlangıç satırını bul
            meslek_row_idx = -1
            for i, row in enumerate(table):
                for cell in row:
                    if cell and 'MESLEK DERSLERİ' in str(cell).upper():
                        meslek_row_idx = i
                        break
                if meslek_row_idx != -1: break
            
            if meslek_row_idx == -1: continue

            # Ders adı ve sınıf sütunlarını bul
            header_row = table[meslek_row_idx + 1] if meslek_row_idx + 1 < len(table) else table[meslek_row_idx]
            ders_adi_col = next((i for i, c in enumerate(header_row) if c and 'DERS' in c.upper()), 0)
            grade_cols = find_grade_columns(header_row)

            # Dersleri işle
            for row_idx in range(meslek_row_idx + 1, len(table)):
                row = table[row_idx]
                if ders_adi_col >= len(row): continue
                
                # Başka bir ana bölüm başladıysa dur
                if row[0] and any(kw in str(row[0]).upper() for kw in ['TOPLAM', 'SEÇMELİ', 'REHBERLİK']):
                    break

                ders_adi_raw = row[ders_adi_col]
                ders_clean = clean_text(str(ders_adi_raw))
                ders_clean = re.sub(r"\(\*+\)", "", ders_clean).strip()

                if not (ders_clean and len(ders_clean) > 3 and not ders_clean.isdigit()):
                    continue

                saatler = {"9": 0, "10": 0, "11": 0, "12": 0}
                for grade, col_idx in grade_cols.items():
                    if col_idx < len(row) and row[col_idx]:
                        match = re.search(r"\d+", str(row[col_idx]))
                        if match: saatler[grade] = int(match.group())
                
                all_lessons.append({
                    "adi": normalize_to_title_case_tr(ders_clean),
                    "saatler": saatler
                })

    return merge_lesson_dicts([], all_lessons)


# ------------- ANA FONKSİYONLAR ------------- #

def oku_cop_pdf(pdf_source: str, debug: bool = False) -> Dict[str, Any]:
    """
    ÇÖP PDF'sini okur ve belirtilen kurallara göre JSON formatında sonuç döndürür.
    """
    pdf_path = None
    try:
        if pdf_source.startswith('http'):
            response = requests.get(pdf_source, timeout=30)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(response.content)
                pdf_path = tmp_file.name
        else:
            pdf_path = pdf_source

        with pdfplumber.open(pdf_path) as pdf:
            # 1. Adım: Tüm metni ve "İçindekiler" bölümünü çıkar
            full_text = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())
            icindekiler_text = extract_icindekiler_section(full_text)
            if not icindekiler_text:
                raise ValueError("PDF içinde 'İÇİNDEKİLER' bölümü bulunamadı.")

            # 2. Adım: Alan ve Dalları SADECE içindekilerden çıkar
            alan_adi, dallar = extract_alan_dal_from_icindekiler(icindekiler_text)
            if not alan_adi:
                raise ValueError("'İÇİNDEKİLER' bölümünden alan adı çıkarılamadı.")

            # 3. Adım: Tüm meslek derslerini ve saatlerini çıkar
            meslek_dersleri = extract_all_meslek_dersleri(pdf)
            if not meslek_dersleri:
                print(f"⚠️ Uyarı: '{alan_adi}' için meslek dersi bulunamadı.")

            # 4. Adım: Veriyi birleştir (her dal tüm dersleri alır)
            dal_ders_map = {dal: meslek_dersleri for dal in dallar} if dallar else {"Tüm Alan Dersleri": meslek_dersleri}

            return {
                "alan_adi": alan_adi,
                "dallar": dallar,
                "dal_ders_map": dal_ders_map,
                "success": True,
                "error": None
            }

    except Exception as e:
        error_msg = f"PDF işleme hatası: {str(e)}"
        if debug: print(error_msg)
        return {"alan_adi": None, "dallar": [], "dal_ders_map": {}, "success": False, "error": error_msg}
    finally:
        if pdf_source.startswith('http') and pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)

def oku_cop_pdf_file(pdf_path: str, debug: bool = False) -> Dict[str, Any]:
    if not os.path.exists(pdf_path):
        return {"success": False, "error": f"Dosya bulunamadı: {pdf_path}"}
    return oku_cop_pdf(pdf_path, debug)

def oku_folder_pdfler(folder_path: str, debug: bool = False) -> Dict[str, Dict[str, Any]]:
    if not os.path.isdir(folder_path):
        print(f"❌ Klasör bulunamadı: {folder_path}")
        return {}
    
    results = {}
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    print(f"📁 {folder_path} klasöründe {len(pdf_files)} PDF bulundu")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        if debug: print(f"\n🔄 İşleniyor: {pdf_file}")
        results[pdf_file] = oku_cop_pdf_file(pdf_path, debug)
    
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        is_debug = '--debug' in sys.argv
        if os.path.isdir(path_arg):
            oku_folder_pdfler(path_arg, debug=is_debug)
        else:
            oku_cop_pdf_file(path_arg, debug=is_debug)
    else:
        print("Kullanım: python oku_cop.py <pdf_dosyasi_veya_klasor> [--debug]")
