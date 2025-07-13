import os
import re
import json
from typing import Dict, List, Any, Optional

import pdfplumber

try:
    from .utils import normalize_to_title_case_tr
except ImportError:
    # Stand-alone çalışma durumunda modules paketini sys.path'e ekle
    import os
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from modules.utils import normalize_to_title_case_tr


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


def find_alan_name_in_text(text: str) -> Optional[str]:
    """
    PDF metninin ilk satırlarında alan adını arar.
    Geliştirilmiş algoritma ile daha doğru alan adı tespiti.
    """
    lines = text.split("\n")
    
    # Önce direkt "ALANI" ile biten satırları ara
    for line in lines[:100]:  # İlk 100 satırda ara
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        # Pattern 1: "XXXX TEKNOLOJİSİ ALANI", "XXXX HİZMETLERİ ALANI" vb.
        if line_upper.endswith(" ALANI") and len(line_clean) > 10:
            alan_adi = line_upper.replace(" ALANI", "").strip()
            # Gereksiz kelimeler içermiyorsa ve rakam ile başlamıyorsa
            if (not any(bad in alan_adi for bad in ["ÇERÇEVE", "ÖĞRETİM", "PROGRAM", "AMAÇLAR", "5."]) 
                and not alan_adi[0].isdigit()):
                return normalize_to_title_case_tr(alan_adi)
    
    # Pattern 2: "ALAN ADI" sonrası
    for i, line in enumerate(lines[:50]):
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()

        if "ALAN" in line_upper and ("ADI" in line_upper or "ALANI" in line_upper):
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = clean_text(lines[j]).strip()
                if len(next_line) > 5 and not next_line.upper().startswith("T.C."):
                    return normalize_to_title_case_tr(next_line)
    
    return None


def find_dallar_in_text(text: str) -> List[str]:
    """
    Metinden '... DALI' biçimindeki dal adlarını ayıklar.
    """
    dallar = []
    lines = text.split("\n")
    for line in lines:
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()

        # '... DALI'
        if line_upper.endswith(" DALI"):
            dal_name = line_upper.replace(" DALI", "").strip()
            if len(dal_name) > 3:
                dallar.append(normalize_to_title_case_tr(dal_name))

        # '(.... DALI)'
        dal_match = re.search(r"\(([^)]+)\s+DALI\)", line_upper)
        if dal_match:
            dal_name = dal_match.group(1).strip()
            if len(dal_name) > 3:
                dallar.append(normalize_to_title_case_tr(dal_name))
    return list(set(dallar))


# ---------- PDF İÇİN TABLO & DERS ÇIKARIMI ----------- #
def find_dal_name_from_schedule_section(
    lines: List[str], schedule_line_index: int, alan_adi: str
) -> Optional[str]:
    search_range = range(max(0, schedule_line_index - 15), min(len(lines), schedule_line_index + 5))
    for i in search_range:
        line = clean_text(lines[i]).strip()
        line_upper = line.upper()

        if line_upper.endswith(" DALI"):
            dal_name = line_upper.replace(" DALI", "").strip()
            if len(dal_name) > 3 and dal_name != alan_adi:
                return dal_name

        dal_match = re.search(r"\(([^)]+)\s+DALI\)", line_upper)
        if dal_match:
            dal_name = dal_match.group(1).strip()
            if len(dal_name) > 3:
                return dal_name

        if "DALI" in line_upper and ("ANADOLU" in line_upper or "PROGRAMI" in line_upper):
            dali_pos = line_upper.find(" DALI")
            if dali_pos > 0:
                potential_dal = line_upper[:dali_pos].strip()
                if potential_dal != alan_adi and len(potential_dal) > 3:
                    return potential_dal
    return None


def find_meslek_dersleri_section(table: List[List[str]]) -> Optional[int]:
    for row_idx, row in enumerate(table):
        for cell in row:
            if cell and isinstance(cell, str):
                cell_upper = str(cell).upper()
                if "MESLEK DERSLERİ" in cell_upper or "MESLEK ALAN DERSLERİ" in cell_upper:
                    return row_idx
    return None


def find_ders_adi_column(table: List[List[str]]) -> Optional[int]:
    for row in table[:5]:
        for col_idx, cell in enumerate(row):
            if cell:
                cell_upper = str(cell).upper()
                if "DERSLER" in cell_upper or "DERS ADI" in cell_upper:
                    return col_idx
    return None


def extract_lessons_from_schedule_table(page, pdf, page_num: int) -> List[str]:
    dersler = []
    try:
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 3:
                continue
            
            print(f"📊 Sayfa {page_num+1}, Tablo {table_idx+1}: {len(table)} satır analiz ediliyor...")
            
            # Ana ders tablosunu bul (en az 10 satır olmalı)
            if len(table) < 10:
                continue
                
            # Tabloda ders kategori sütununu bul  
            ders_col = None
            header_row = None
            
            # Header satırını bul
            for row_idx, row in enumerate(table[:3]):
                for col_idx, cell in enumerate(row):
                    if cell and isinstance(cell, str):
                        cell_upper = str(cell).upper()
                        if "DERS" in cell_upper and ("KATEGORILER" in cell_upper or "DERSLER" in cell_upper):
                            ders_col = col_idx if "DERSLER" in cell_upper else col_idx + 1
                            header_row = row_idx
                            break
                if ders_col is not None:
                    break
            
            if ders_col is None:
                print(f"   ❌ Ders sütunu bulunamadı")
                continue
                
            print(f"   ✅ Ders sütunu bulundu: {ders_col}")
            
            # Meslek dersleri bölümünü bul
            meslek_started = False
            for row_idx in range(header_row + 1, len(table)):
                row = table[row_idx]
                
                if ders_col >= len(row):
                    continue
                    
                kategori_cell = row[0] if len(row) > 0 else ""
                ders_cell = row[ders_col] if ders_col < len(row) else ""
                
                # Kategori kontrolü
                if kategori_cell and isinstance(kategori_cell, str):
                    kategori_upper = str(kategori_cell).upper().replace('\n', ' ')  # Newline'ları temizle
                    # Meslek dersleri bölümü başlangıcı - tam kelime kontrolü
                    if ("MESLEK" in kategori_upper and "DERS" in kategori_upper) or "MESLEKI" in kategori_upper:
                        meslek_started = True
                        print(f"   🎯 Meslek dersleri başladı: satır {row_idx+1} - {kategori_upper}")
                        # Bu satırdaki dersi de işle, continue yapma
                    elif any(stop_word in kategori_upper for stop_word in ["SEÇMELİ MESLEK", "MESLEK DERS SAATİ TOPLAMI", "TOPLAM DERS SAATİ", "REHBERLİK"]):
                        if meslek_started:
                            print(f"   🛑 Meslek dersleri bitti: {kategori_upper}")
                            break
                
                
                # Ders adını çıkar
                if meslek_started and ders_cell and isinstance(ders_cell, str):
                    ders_clean = clean_text(str(ders_cell)).strip()
                    
                    # Temizleme
                    ders_clean = re.sub(r"\(\*+\)", "", ders_clean)  # (*) dipnotlar
                    ders_clean = re.sub(r"\s{2,}", " ", ders_clean)  # Çoklu boşluk
                    ders_clean = ders_clean.strip()
                    
                    # Geçerlilik kontrolü - daha sıkı filtre
                    if (len(ders_clean) > 3 
                        and not ders_clean.isdigit() 
                        and not any(bad in ders_clean.upper() for bad in [
                            "TOPLAM", "HAFTALIK", "GENEL", "KATEGORI", "TÜRK DİLİ", "DİN KÜLTÜRÜ", 
                            "TARİH", "COĞRAFYA", "MATEMATİK", "FİZİK", "KİMYA", "BİYOLOJİ", 
                            "FELSEFE", "YABANCI DİL", "BEDEN EĞİTİMİ", "SAĞLIK BİLGİSİ"
                        ])):
                        
                        ders_normalized = normalize_to_title_case_tr(ders_clean)
                        dersler.append(ders_normalized)
                        print(f"   📚 Ders bulundu: {ders_normalized}")
            
            if dersler:
                print(f"   ✅ Toplam {len(dersler)} ders bulundu")
                break  # İlk başarılı tabloyu kullan
                
    except Exception as e:
        print(f"❌ Tablo ders çıkarma hatası (sayfa {page_num+1}): {e}")
    
    return list(set(dersler))


def find_lessons_in_cop_pdf(pdf, alan_adi: str) -> Dict[str, List[str]]:
    dal_ders_mapping = {}
    try:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split("\n")
            for i, line in enumerate(lines):
                line_clean = clean_text(line).strip()
                if "HAFTALIK DERS ÇİZELGESİ" in line_clean.upper():
                    dal_adi = find_dal_name_from_schedule_section(lines, i, alan_adi)
                    if dal_adi:
                        dersler = extract_lessons_from_schedule_table(page, pdf, page_num)
                        dal_adi_clean = clean_text(dal_adi)
                        existing = dal_ders_mapping.get(dal_adi_clean, [])
                        dal_ders_mapping[dal_adi_clean] = list(set(existing + dersler))
    except Exception as e:
        print(f"Ders çıkarma hatası: {e}")
    return dal_ders_mapping


# ------------- ANA YEREL PDF OKUMA FONKSİYONLARI ------------- #
def extract_alan_dal_ders_from_cop_file(
    pdf_path: str,
) -> tuple[Optional[str], List[str], Dict[str, List[str]]]:
    """
    Yerel bir COP PDF dosyasından alan, dal ve ders bilgilerini çıkarır.
    """
    alan_adi = None
    dallar: List[str] = []
    dal_ders_mapping: Dict[str, List[str]] = {}

    if not os.path.isfile(pdf_path):
        print(f"PDF bulunamadı: {pdf_path}")
        return alan_adi, dallar, dal_ders_mapping

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

            alan_adi = find_alan_name_in_text(full_text)
            dallar = find_dallar_in_text(full_text)
            dallar = list(set(clean_text(d) for d in dallar if len(d.strip()) > 3))

            dal_ders_mapping = find_lessons_in_cop_pdf(pdf, alan_adi or "")
    except Exception as e:
        print(f"PDF okuma hatası ({pdf_path}): {e}")

    return alan_adi, dallar, dal_ders_mapping


def oku_cop_pdf_file(pdf_path: str) -> Dict[str, Any]:
    """
    Tek bir yerel COP PDF dosyasını okuyup sonuçları sözlük olarak döndürür.
    """
    alan_adi, dallar, dal_ders_mapping = extract_alan_dal_ders_from_cop_file(pdf_path)

    dal_ders_listesi = []
    for dal in dallar:
        matched_dersler: List[str] = []

        if dal in dal_ders_mapping:
            matched_dersler = dal_ders_mapping[dal]
        else:
            for mapping_dal, dersler in dal_ders_mapping.items():
                if dal.upper() in mapping_dal.upper() or mapping_dal.upper() in dal.upper():
                    matched_dersler = dersler
                    break

        dal_ders_listesi.append(
            {
                "dal_adi": dal,
                "dersler": matched_dersler,
                "ders_sayisi": len(matched_dersler),
            }
        )

    toplam_ders_sayisi = sum(len(set(info["dersler"])) for info in dal_ders_listesi)

    return {
        "alan_bilgileri": {
            "alan_adi": alan_adi,
            "dal_sayisi": len(dallar),
            "toplam_ders_sayisi": toplam_ders_sayisi,
            "dal_ders_listesi": dal_ders_listesi,
        },
        "metadata": {
            "pdf_path": pdf_path,
            "status": "success" if alan_adi else "partial",
        },
    }


# ------------- TOPLU PDF OKUMA ARACI ------------- #
def oku_tum_pdfler(root_dir: str = ".") -> None:
    """
    root_dir içindeki tüm .pdf dosyalarını tarar, bilgileri terminale basar.
    """
    pdf_files = [
        os.path.join(root_dir, f)
        for f in os.listdir(root_dir)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print(f"📂 '{root_dir}' dizininde PDF bulunamadı.")
        return

    print(f"📄 {len(pdf_files)} PDF bulundu. İşleniyor...\n")

    for pdf_path in pdf_files:
        print(f"▶︎ {os.path.basename(pdf_path)}")
        result = oku_cop_pdf_file(pdf_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("-" * 80)


# Script olarak çalıştırıldığında ana dizindeki PDF'leri oku
if __name__ == "__main__":
    oku_tum_pdfler(root_dir=".")
