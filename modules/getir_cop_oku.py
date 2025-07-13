import pdfplumber
import requests
import re
import os
import json
from typing import Dict, List, Any, Optional
from .utils import normalize_to_title_case_tr, download_and_cache_pdf, get_temp_pdf_path


def clean_text(text: str) -> str:
    """
    Clean text by removing unnecessary characters and spaces
    """
    if not text:
        return ""
    
    # Çoklu boşlukları tek boşluğa dönüştür
    text = re.sub(r'\s+', ' ', text)
    
    # Gereksiz karakterleri temizle
    text = text.replace('\x00', '').replace('\ufffd', '')
    
    # Baş ve sondaki boşlukları temizle
    return text.strip()


def find_alan_name_in_text(text: str, pdf_url: str) -> Optional[str]:
    """
    PDF metninden alan adını çıkar
    """
    # Metinden alan adını bulmaya çalış
    lines = text.split('\n')
    for i, line in enumerate(lines[:50]):  # İlk 50 satırda ara
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        # "ALAN ADI" pattern'ini ara
        if 'ALAN' in line_upper and ('ADI' in line_upper or 'ALANI' in line_upper):
            # Sonraki satırları kontrol et
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = clean_text(lines[j]).strip()
                if len(next_line) > 5 and not next_line.upper().startswith('T.C.'):
                    return normalize_to_title_case_tr(next_line)
    
    return None


def find_dallar_in_text(text: str) -> List[str]:
    """
    PDF metninden dal listesini çıkar
    """
    dallar = []
    lines = text.split('\n')
    
    for line in lines:
        line_clean = clean_text(line).strip()
        line_upper = line_clean.upper()
        
        # "DALI" ile biten satırları bul
        if line_upper.endswith(' DALI'):
            dal_name = line_upper.replace(' DALI', '').strip()
            if len(dal_name) > 3:
                dallar.append(normalize_to_title_case_tr(dal_name))
        
        # "(XXXX DALI)" formatındaki dalları bul
        dal_match = re.search(r'\(([^)]+)\s+DALI\)', line_upper)
        if dal_match:
            dal_name = dal_match.group(1).strip()
            if len(dal_name) > 3:
                dallar.append(normalize_to_title_case_tr(dal_name))
    
    return list(set(dallar))


def find_lessons_in_cop_pdf(pdf, alan_adi: str) -> Dict[str, List[str]]:
    """
    COP PDF'sinden dal ve ders bilgilerini çıkar
    HAFTALIK DERS ÇİZELGELERİ bölümünden dal-ders eşleştirmesi yapar
    """
    dal_ders_mapping = {}
    
    try:
        # Tüm sayfaları tara
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            # Dal ve ders çizelgesi bulmak için anahtar kelimeleri ara
            for i, line in enumerate(lines):
                line_clean = clean_text(line).strip()
                
                # HAFTALIK DERS ÇİZELGESİ içeren bölümleri bul
                if 'HAFTALIK DERS ÇİZELGESİ' in line_clean.upper():
                    # Bu bölümde dal adını bul
                    dal_adi = find_dal_name_from_schedule_section(lines, i, alan_adi)
                    
                    if dal_adi:
                        # Bu sayfa ve sonraki sayfalarda ders listesini ara
                        dersler = extract_lessons_from_schedule_table(page, pdf, page_num)
                        
                        # Dal adını temizle ve ekle
                        dal_adi_clean = clean_text(dal_adi)
                        if dal_adi_clean not in dal_ders_mapping:
                            dal_ders_mapping[dal_adi_clean] = []
                        
                        # Dersleri ekle (mevcut derslerle birleştir)
                        existing_dersler = dal_ders_mapping[dal_adi_clean]
                        dal_ders_mapping[dal_adi_clean] = merge_lesson_dicts(
                            existing_dersler, dersler
                        )
    
    except Exception as e:
        print(f"Ders çıkarma hatası: {e}")
    
    return dal_ders_mapping


def find_dal_name_from_schedule_section(lines: List[str], schedule_line_index: int, alan_adi: str) -> Optional[str]:
    """
    HAFTALIK DERS ÇİZELGESİ bölümünden dal adını çıkar
    """
    # Schedule satırından önceki ve sonraki satırları kontrol et
    search_range = range(max(0, schedule_line_index - 15), min(len(lines), schedule_line_index + 5))
    
    for i in search_range:
        line = clean_text(lines[i]).strip()
        line_upper = line.upper()
        
        # Dal adını belirten pattern'leri ara
        # "ZABIT KÂTİPLİĞİ DALI" veya sadece "DALI" ile biten satırlar
        if line_upper.endswith(' DALI'):
            # "DALI" kelimesini kaldır ve dal adını al
            dal_name = line_upper.replace(' DALI', '').strip()
            if len(dal_name) > 3 and dal_name != alan_adi:
                return dal_name
        
        # Alternatif: "(XXXX DALI)" formatında dal adı
        dal_match = re.search(r'\(([^)]+)\s+DALI\)', line_upper)
        if dal_match:
            dal_name = dal_match.group(1).strip()
            if len(dal_name) > 3:
                return dal_name
        
        # Yeni pattern: Alan adından sonra gelen dal adları için
        # Örnek: "ZABIT KÂTİPLİĞİ DALI ANADOLU MESLEK PROGRAMI"
        if 'DALI' in line_upper and ('ANADOLU' in line_upper or 'PROGRAMI' in line_upper):
            # DALI'den önceki kısmı al
            dali_pos = line_upper.find(' DALI')
            if dali_pos > 0:
                potential_dal = line_upper[:dali_pos].strip()
                # Alan adı değilse ve yeterince uzunsa
                if potential_dal != alan_adi and len(potential_dal) > 3:
                    return potential_dal
    
    return None


# --------------------------------------------------------
# Yedek Metin-Satır Analizi
# --------------------------------------------------------
def parse_lessons_from_text_lines(lines: List[str], start_index: int) -> List[str]:
    """
    'MESLEK DERSLERİ' başlığından itibaren satırlardan ders adlarını çıkarır.
    Tablo çıkarılamadığında kullanılır.
    """
    dersler: List[str] = []
    stop_keywords = (
        "TOPLAM",
        "SEÇMELİ",
        "AKADEMİK",
        "REHBER",
        "DERS SAATİ",
        "KATEGORİLERİ",
    )

    for idx in range(start_index + 1, len(lines)):
        raw = clean_text(lines[idx]).strip()
        if not raw:
            continue

        upper = raw.upper()
        # Durdurucu anahtar kelimelerden biri geldiyse bölümü bitir
        if any(kw in upper for kw in stop_keywords):
            break

        # Sadece rakamlardan oluşan satırları / kısa ifadeleri atla
        if raw.isdigit() or len(raw) < 3:
            continue

        # Satırda çift boşluk / tab ile ayrılan sütunlar olabilir; ilk parça genelde ders adı
        ders_adi = re.split(r"\s{2,}|\t", raw)[0]
        ders_adi_clean = clean_text(ders_adi)

        # Dipnot atıflarını ve tablo artıkları temizle ─  (*), (**), (***),  --2-, --5- vb.
        ders_adi_clean = re.sub(r"\(\*+\)", "", ders_adi_clean)          # parantez içi yıldız
        ders_adi_clean = re.sub(r"-+\s*\d+\s*-", "", ders_adi_clean)    # -- 2 --, --2-, -3-
        ders_adi_clean = re.sub(r"\s{2,}", " ", ders_adi_clean).strip()

        if ders_adi_clean and len(ders_adi_clean) > 3:
            dersler.append(normalize_to_title_case_tr(ders_adi_clean))

    return list(set(dersler))


def extract_lessons_from_schedule_table(page, pdf, page_num: int) -> List[Dict[str, Any]]:
    """
    Sayfa tablolarından MESLEK DERSLERİ bölümündeki dersleri çıkarır ve
    her ders için 9-10-11-12 sınıf saatlerini döndürür.
    Örnek çıktı:
    [
        {
            "adi": "Klavye Teknikleri",
            "saatler": {"9": 4, "10": 0, "11": 0, "12": 0}
        },
        ...
    ]
    """
    lessons: List[Dict[str, Any]] = []

    try:
        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if not table:
                continue

            # MESLEK DERSLERİ bölümünün satırını bul
            meslek_row = find_meslek_dersleri_section(table)
            if meslek_row is None:
                continue

            # Ders adı sütununu bul
            ders_adi_col = find_ders_adi_column(table)
            if ders_adi_col is None:
                continue

            # Header satırı ve sınıf sütunlarını tespit et
            header_idx = meslek_row + 1 if meslek_row + 1 < len(table) else meslek_row
            header_row = table[header_idx]
            grade_cols = find_grade_columns(header_row)

            # Header satırında sınıf sütunları bulunamadıysa varsayılan olarak
            # ders adı sütunundan sonraki 4 sütunu 9-10-11-12 olarak ata
            if not grade_cols:
                grade_cols = {str(9 + i): ders_adi_col + 1 + i for i in range(4)}

            # Ders satırlarını işle
            for row_idx in range(header_idx + 1, len(table)):
                row = table[row_idx]

                # Başka bir bölüm başladıysa dur
                if any(
                    cell and isinstance(cell, str) and
                    ("ALAN" in cell.upper() or "BÖLÜM" in cell.upper())
                    for cell in row
                ):
                    break

                if ders_adi_col >= len(row):
                    continue

                ders_adi_raw = row[ders_adi_col] or ""
                ders_clean = clean_text(str(ders_adi_raw))
                ders_clean = re.sub(r"\(\*+\)", "", ders_clean)
                ders_clean = re.sub(r"-+\s*\d+\s*-", "", ders_clean)
                ders_clean = re.sub(r"\s{2,}", " ", ders_clean).strip()

                # Geçerli ders adı kontrolü
                if not (
                    ders_clean
                    and len(ders_clean) > 3
                    and not ders_clean.isdigit()
                    and not ders_clean.upper().startswith(("TOPLAM", "HAFTALIK", "GENEL"))
                ):
                    continue

                # Saatleri oku
                saatler = {"9": 0, "10": 0, "11": 0, "12": 0}
                for grade, col_idx in grade_cols.items():
                    if col_idx < len(row):
                        val_text = str(row[col_idx]).strip() if row[col_idx] else ""
                        match = re.search(r"\d+", val_text)
                        if match:
                            saatler[grade] = int(match.group())

                # Eğer tablo sütunlarında saat bulunamadıysa, ders adının sonundaki rakamları yakala (örn: "Klavye Teknikleri 4--")
                if all(v == 0 for v in saatler.values()):
                    tail = re.search(r"(\d{1,2})(?:\s*-*)?\s*$", ders_clean)
                    if tail:
                        saatler["9"] = int(tail.group(1))
                        # Rakam ve olası tireleri ders adından temizle
                        ders_clean = re.sub(r"(\d{1,2})(?:\s*-*)?\s*$", "", ders_clean).strip()

                lessons.append(
                    {
                        "adi": normalize_to_title_case_tr(ders_clean),
                        "saatler": saatler,
                    }
                )

    except Exception as e:
        print(f"Tablo ders çıkarma hatası (sayfa {page_num}): {e}")

    # Tabloda sonuç yoksa fallback: satır-bazlı analiz
    if not lessons:
        page_text = page.extract_text() or ""
        text_lines = page_text.split("\n")
        for idx, l in enumerate(text_lines):
            l_upper = l.upper()
            if (
                "MESLEK DERSLERİ" in l_upper
                or "MESLEK ALAN DERSLERİ" in l_upper
                or (
                    l_upper.strip() == "MESLEK"
                    and idx + 1 < len(text_lines)
                    and "DERSLERİ" in text_lines[idx + 1].upper()
                )
            ):
                basic_names = parse_lessons_from_text_lines(text_lines, idx)
                for name in basic_names:
                    lessons.append(
                        {
                            "adi": name,
                            "saatler": {"9": 0, "10": 0, "11": 0, "12": 0},
                        }
                    )
                break

    # Tekrarları birleştir
    return merge_lesson_dicts([], lessons)

    dersler = []
    
    try:
        # Mevcut sayfadaki tabloları al
        tables = page.extract_tables()
        
        for table_idx, table in enumerate(tables):
            if not table:
                continue
            
            # MESLEK DERSLERİ bölümünü bul
            meslek_dersleri_row = find_meslek_dersleri_section(table)
            if meslek_dersleri_row is None:
                continue
            
            # Ders adı sütununu bul
            ders_adi_col = find_ders_adi_column(table)
            if ders_adi_col is None:
                continue
            
            # MESLEK DERSLERİ satırından sonraki dersleri çıkar
            for row_idx in range(meslek_dersleri_row + 1, len(table)):
                row = table[row_idx]
                
                if row_idx < len(row) and ders_adi_col < len(row):
                    ders_adi = row[ders_adi_col]
                    
                    if ders_adi and isinstance(ders_adi, str):
                        ders_clean = clean_text(ders_adi).strip()

                        # Dipnot & artık temizliği (tablo satırı)
                        ders_clean = re.sub(r"\(\*+\)", "", ders_clean)          # dipnot (*)
                        ders_clean = re.sub(r"-+\s*\d+\s*-", "", ders_clean)    # --2-, -3-
                        ders_clean = re.sub(r"\s{2,}", " ", ders_clean).strip()
                        
                        # Geçerli ders adı kontrolü
                        if (len(ders_clean) > 3 and 
                            not ders_clean.upper().startswith(('TOPLAM', 'HAFTALIK', 'GENEL')) and
                            not ders_clean.isdigit()):
                            dersler.append(normalize_to_title_case_tr(ders_clean))
                
                # Eğer başka bir bölüm başladıysa dur
                if any(cell and isinstance(cell, str) and 
                      ('ALAN' in str(cell).upper() or 'BÖLÜM' in str(cell).upper()) 
                      for cell in row):
                    break
    
    except Exception as e:
        print(f"Tablo ders çıkarma hatası (sayfa {page_num}): {e}")

    # Tablo bulunamadıysa veya boş döndüyse satır-tabanlı yedek analiz
    if not dersler:
        page_text = page.extract_text() or ""
        text_lines = page_text.split("\n")
        for idx, l in enumerate(text_lines):
            l_upper = l.upper()
            # Başlık satırı tek satırda veya iki satır ardışık olabilir
            if (
                "MESLEK DERSLERİ" in l_upper
                or "MESLEK ALAN DERSLERİ" in l_upper
                or (
                    l_upper.strip() == "MESLEK"
                    and idx + 1 < len(text_lines)
                    and "DERSLERİ" in text_lines[idx + 1].upper()
                )
            ):
                # İki satırlı başlık durumunda start_index'i ilk satıra ayarla
                dersler.extend(parse_lessons_from_text_lines(text_lines, idx))
                break

    return list(set(dersler))


def find_meslek_dersleri_section(table: List[List[str]]) -> Optional[int]:
    """
    Tabloda MESLEK DERSLERİ bölümünün satır numarasını bul
    """
    for row_idx, row in enumerate(table):
        for cell in row:
            if cell and isinstance(cell, str):
                cell_upper = str(cell).upper()
                if 'MESLEK DERSLERİ' in cell_upper or 'MESLEK ALAN DERSLERİ' in cell_upper:
                    return row_idx
    return None


def find_ders_adi_column(table: List[List[str]]) -> Optional[int]:
    """
    Tabloda ders adı sütununu bul
    """
    # İlk birkaç satırda ders adı sütununu ara
    for row in table[:5]:
        for col_idx, cell in enumerate(row):
            if cell:
                cell_upper = str(cell).upper()
                if 'DERSLER' in cell_upper or 'DERS ADI' in cell_upper:
                    return col_idx
    
    return None


def find_grade_columns(header_row: List[str]) -> Dict[str, int]:
    """
    Header satırından '9', '10', '11', '12' sınıf sütunlarının indekslerini döndürür.
    Küçük varyasyonlar (9.SINIF, 10 SINIF vb.) da desteklenir.
    Returns: {"9": idx9, "10": idx10, ...}
    """
    grade_cols: Dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        if not cell:
            continue
        text = str(cell).strip().upper()
        if text.startswith("9"):
            grade_cols["9"] = idx
        elif text.startswith("10"):
            grade_cols["10"] = idx
        elif text.startswith("11"):
            grade_cols["11"] = idx
        elif text.startswith("12"):
            grade_cols["12"] = idx
    return grade_cols


def merge_lesson_dicts(list1: List[Dict[str, Any]], list2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    İki ders listesinde (adi + saatler) tekrarları birleştirir.
    Saatler birleşiminde 0 olmayan değer önceliklidir.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for lesson in list1 + list2:
        key = lesson.get("adi")
        if not key:
            continue
        if key in merged:
            # Saatleri birleştir
            for grade, val in lesson.get("saatler", {}).items():
                if val and merged[key]["saatler"].get(grade, 0) == 0:
                    merged[key]["saatler"][grade] = val
        else:
            merged[key] = {
                "adi": key,
                "saatler": {g: int(v) for g, v in lesson.get("saatler", {}).items()}
            }
    return list(merged.values())


def extract_alan_and_dallar_from_cop_pdf(pdf_url: str) -> tuple[Optional[str], List[str]]:
    """
    COP PDF'sinden alan adı ve dal listesini çıkar
    """
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        
        temp_pdf_path = "temp_cop.pdf"
        with open(temp_pdf_path, 'wb') as f:
            f.write(response.content)
        
        alan_adi = None
        dallar = []
        
        with pdfplumber.open(temp_pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            alan_adi = find_alan_name_in_text(full_text, pdf_url)
            dallar = find_dallar_in_text(full_text)
            dallar = list(set([clean_text(dal) for dal in dallar if dal and len(dal.strip()) > 3]))
        
        try:
            os.remove(temp_pdf_path)
        except:
            pass
        
        return alan_adi, dallar
        
    except Exception as e:
        print(f"COP PDF okuma hatası: {e}")
        return None, []


def extract_alan_dal_ders_from_cop_pdf(pdf_url: str, cache: bool = True) -> tuple[Optional[str], List[str], Dict[str, List[str]]]:
    """
    COP PDF'sinden alan, dal ve ders bilgilerini çıkar
    
    Args:
        pdf_url: PDF URL'si  
        cache: True ise PDF'yi kalıcı olarak cache'le, False ise geçici kullan
    """
    try:
        # Önce alan adını tahmin et (cache için)
        estimated_alan = pdf_url.split('/')[-1].replace('.pdf', '').replace('_cop', '')
        
        # PDF'yi indir (cache veya geçici)
        if cache:
            pdf_path = download_and_cache_pdf(pdf_url, 'cop', estimated_alan, 'cop_program')
            temp_file = False
        else:
            pdf_path = get_temp_pdf_path(pdf_url)
            response = requests.get(pdf_url)
            response.raise_for_status()
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            temp_file = True
        
        if not pdf_path:
            return None, [], {}
        
        alan_adi = None
        dallar = []
        dal_ders_mapping = {}
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            # Alan adını bul
            alan_adi = find_alan_name_in_text(full_text, pdf_url)
            
            # Dalları bul
            dallar = find_dallar_in_text(full_text)
            dallar = list(set([clean_text(dal) for dal in dallar if dal and len(dal.strip()) > 3]))
            
            # Dal-ders eşleştirmesini bul
            dal_ders_mapping = find_lessons_in_cop_pdf(pdf, alan_adi)
        
        # Geçici dosyayı temizle
        if temp_file:
            try:
                os.remove(pdf_path)
            except:
                pass
        
        return alan_adi, dallar, dal_ders_mapping
        
    except Exception as e:
        print(f"COP PDF okuma hatası: {e}")
        return None, [], {}


def oku_cop_pdf(pdf_url: str) -> Dict[str, Any]:
    """
    COP PDF'sinden alan, dal ve ders bilgilerini çıkar ve JSON formatında döndür
    """
    try:
        alan_adi, dallar, dal_ders_mapping = extract_alan_dal_ders_from_cop_pdf(pdf_url)
        
        # Dal-ders yapısını oluştur
        dal_ders_listesi = []
        
        for dal in dallar:
            # Dal adını eşleştirmek için çeşitli formatlarda dene
            matched_dersler = []
            
            # Tam eşleşme
            if dal in dal_ders_mapping:
                matched_dersler = dal_ders_mapping[dal]
            else:
                # Kısmi eşleşme ara
                for mapping_dal, dersler in dal_ders_mapping.items():
                    if dal.upper() in mapping_dal.upper() or mapping_dal.upper() in dal.upper():
                        matched_dersler = dersler
                        break
            
            dal_info = {
                'dal_adi': dal,
                'dersler': matched_dersler,
                'ders_sayisi': len(matched_dersler)
            }
            dal_ders_listesi.append(dal_info)
        
        # Toplam ders sayısını hesapla
        toplam_ders_sayisi = sum(len(info['dersler']) for info in dal_ders_listesi)
        
        # Sonuç yapısını oluştur
        result = {
            'alan_bilgileri': {
                'alan_adi': alan_adi,
                'dal_sayisi': len(dallar),
                'toplam_ders_sayisi': toplam_ders_sayisi,
                'dal_ders_listesi': dal_ders_listesi
            },
            'metadata': {
                'pdf_url': pdf_url,
                'status': 'success' if alan_adi else 'partial',
                'extraction_date': json.dumps(dict(), default=str)  # Placeholder for date
            }
        }
        
        return result
        
    except Exception as e:
        return {
            'alan_bilgileri': {},
            'metadata': {
                'pdf_url': pdf_url,
                'status': 'error',
                'error_message': str(e)
            }
        }


def is_cop_pdf_url(url: str) -> bool:
    """
    Verilen URL'nin COP PDF URL'si olup olmadığını kontrol et
    """
    return 'meslek.meb.gov.tr' in url and 'cop' in url and url.endswith('.pdf')


def normalize_cop_area_name(html_area_name: str) -> str:
    """
    HTML'den gelen alan adını utils.py standardına göre normalize eder.
    """
    return normalize_to_title_case_tr(html_area_name)


def find_matching_area_id_for_cop(html_area_name: str, db_areas: Dict[str, int]) -> tuple[Optional[int], Optional[str]]:
    """
    HTML'den gelen alan adını veritabanındaki alanlarla eşleştirir (COP için).
    Returns: (alan_id, matched_name) veya (None, None)
    """
    normalized_html_name = normalize_cop_area_name(html_area_name)
    
    # Tam eşleşme kontrolü
    if normalized_html_name in db_areas:
        return db_areas[normalized_html_name], normalized_html_name
    
    # Kısıtlı benzerlik kontrolü
    normalized_html = normalized_html_name.lower().strip()
    for db_name, area_id in db_areas.items():
        db_normalized = db_name.lower().strip()
        
        # Sadece uzunluk farkı ±2 karakter olan durumlar
        if (abs(len(normalized_html) - len(db_normalized)) <= 2 and
            (normalized_html in db_normalized or db_normalized in normalized_html)):
            print(f"COP Sınırlı eşleşme: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
            return area_id, db_name
    
    print(f"COP Eşleşme bulunamadı: '{html_area_name}' (normalize: '{normalized_html_name}')")
    return None, None


def get_areas_from_db_for_cop(db_path: str) -> Dict[str, int]:
    """
    Veritabanından alan ID ve adlarını çeker (COP için).
    Returns: dict {alan_adi: alan_id}
    """
    import sqlite3
    
    if not os.path.exists(db_path):
        print(f"Veritabanı bulunamadı: {db_path}")
        return {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, alan_adi FROM temel_plan_alan ORDER BY alan_adi")
            results = cursor.fetchall()
            return {alan_adi: alan_id for alan_id, alan_adi in results}
    except Exception as e:
        print(f"Veritabanı okuma hatası: {e}")
        return {}


def save_cop_results_to_db(cop_results: Dict[str, Any], db_path: str, meb_alan_id: str = None) -> bool:
    """
    COP okuma sonuçlarını veritabanına kaydet
    
    Args:
        cop_results: COP PDF okuma sonuçları
        db_path: Veritabanı dosya yolu
        meb_alan_id: MEB'in standart alan ID'si (örn: "04")
    """
    import sqlite3
    
    try:
        alan_bilgileri = cop_results.get('alan_bilgileri', {})
        alan_adi = alan_bilgileri.get('alan_adi')
        dal_ders_listesi = alan_bilgileri.get('dal_ders_listesi', [])
        
        if not alan_adi or not dal_ders_listesi:
            print("COP sonuçları eksik, veritabanına kaydedilemiyor")
            return False
        
        # Veritabanından alan bilgilerini al
        db_areas = get_areas_from_db_for_cop(db_path)
        if not db_areas:
            print("Veritabanından alan bilgileri alınamadı")
            return False
        
        # Alan ID'sini bul (fuzzy matching ile)
        area_id, matched_name = find_matching_area_id_for_cop(alan_adi, db_areas)
        
        if not area_id:
            print(f"Alan '{alan_adi}' veritabanında bulunamadı - önce Adım 1'ı çalıştırın")
            return False
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # MEB alan ID'sini güncelle (eğer sağlandıysa)
            if meb_alan_id:
                cursor.execute(
                    "UPDATE temel_plan_alan SET meb_alan_id = ? WHERE id = ?",
                    (meb_alan_id, area_id)
                )
                print(f"✅ MEB alan ID güncellendi: {alan_adi} -> {meb_alan_id}")
            
            # Dal-ders ilişkilerini kaydet
            for dal_info in dal_ders_listesi:
                dal_adi = dal_info.get('dal_adi')
                dersler = dal_info.get('dersler', [])
                
                # Dal ID'sini bul veya oluştur
                cursor.execute(
                    "SELECT id FROM temel_plan_dal WHERE dal_adi = ? AND alan_id = ?",
                    (dal_adi, area_id)
                )
                dal_result = cursor.fetchone()
                
                if dal_result:
                    dal_id = dal_result[0]
                else:
                    cursor.execute(
                        "INSERT INTO temel_plan_dal (dal_adi, alan_id) VALUES (?, ?)",
                        (dal_adi, area_id)
                    )
                    dal_id = cursor.lastrowid
                
                # Dersleri kaydet
                for ders_adi in dersler:
                    if ders_adi.strip():
                        # Ders var mı kontrol et
                        cursor.execute(
                            "SELECT id FROM temel_plan_ders WHERE ders_adi = ?",
                            (ders_adi,)
                        )
                        ders_result = cursor.fetchone()
                        
                        if ders_result:
                            ders_id = ders_result[0]
                        else:
                            cursor.execute(
                                "INSERT INTO temel_plan_ders (ders_adi) VALUES (?)",
                                (ders_adi,)
                            )
                            ders_id = cursor.lastrowid
                        
                        # Ders-dal ilişkisini kaydet
                        cursor.execute(
                            "INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) VALUES (?, ?)",
                            (ders_id, dal_id)
                        )
            
            conn.commit()
            print(f"COP sonuçları başarıyla veritabanına kaydedildi: {alan_adi}")
            return True
            
    except Exception as e:
        print(f"COP veritabanı kaydetme hatası: {e}")
        return False


def get_alan_ids(sinif_kodu="9"):
    """
    MEB sitesinden alan ID'lerini çeker (ÇÖP için).
    getir_dm.py'deki mantığı kullanır.
    
    Args:
        sinif_kodu (str): Sınıf kodu (default: "9")
    
    Returns:
        list: [{"id": "04", "isim": "Bilişim Teknolojileri"}, ...]
    """
    try:
        url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Alan dropdown'ını bul (getir_dm.py'deki mantığı kullan)
        select_element = soup.find('select', id="ContentPlaceHolder1_drpalansec")
        if not select_element:
            print(f"Alan dropdown bulunamadı (sınıf {sinif_kodu})")
            return []
        
        alanlar = []
        for option in select_element.find_all('option'):
            alan_id = option.get('value', '').strip()
            alan_adi = option.text.strip()
            
            # Geçerli alan ID'lerini filtrele
            if alan_id and alan_id not in ("00", "0"):
                alanlar.append({"id": alan_id, "isim": alan_adi})
        
        print(f"✅ {sinif_kodu}. sınıf için {len(alanlar)} alan ID'si çekildi")
        return alanlar
        
    except Exception as e:
        print(f"Alan ID çekme hatası (sınıf {sinif_kodu}): {e}")
        return []


def getir_cop(siniflar=["9", "10", "11", "12"]):
    """
    MEB sitesinden ÇÖP (Çerçeve Öğretim Programı) verilerini çeker.
    Alan ID'lerini de döndürür.
    
    Args:
        siniflar (list): Çekilecek sınıf seviyeleri (default: ["9", "10", "11", "12"])
    
    Returns:
        dict: {
            "cop_data": {sınıf: {alan_adi: {link, guncelleme_yili}}},
            "alan_ids": {sınıf: [{id, isim}]}
        }
    """
    import requests
    from bs4 import BeautifulSoup
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def get_cop_data_for_class(sinif_kodu):
        """Belirli bir sınıf için ÇÖP verilerini çek"""
        try:
            url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
            params = {
                'sinif_kodu': sinif_kodu,
                'kurum_id': '1'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            alanlar = {}
            
            # Alan kartlarını bul
            alan_columns = soup.find_all('div', class_='col-lg-3')
            
            for column in alan_columns:
                try:
                    # Link ve alan bilgisini çıkar
                    link_tag = column.find('a', href=True)
                    if not link_tag:
                        continue
                    
                    # Alan adını img alt attribute'ından al
                    img_tag = link_tag.find('img', alt=True)
                    if not img_tag:
                        continue
                    
                    alan_adi = img_tag.get('alt', '').strip()
                    if not alan_adi:
                        continue

                    # Hatalı "alan adı" olarak algılanan metinleri filtrele
                    invalid_keywords = [
                        "ÇERÇEVE ÖĞRETİM PROGRAMI",
                        "ÖĞRETİM PROGRAMININ AMAÇLARI",
                        "LOGO",
                        "MEB"
                    ]
                    # Çok uzun veya anlamsız metinleri de filtrele (örn: ... içerenler)
                    if any(keyword in alan_adi.upper() for keyword in invalid_keywords) or "..." in alan_adi or len(alan_adi) > 100:
                        continue # Bu geçerli bir alan adı değil, atla.

                    
                    # ÇÖP PDF linkini al
                    href = link_tag.get('href', '').strip()
                    if not href.endswith('.pdf') or 'upload/cop' not in href:
                        continue
                    
                    full_link = requests.compat.urljoin(response.url, href)
                    
                    # Güncelleme yılını ribbon'dan al
                    guncelleme_yili = None
                    ribbon = column.find('div', class_='ribbon')
                    if ribbon:
                        span_tag = ribbon.find('span')
                        if span_tag:
                            guncelleme_yili = span_tag.get_text(strip=True)
                    
                    alanlar[alan_adi] = {
                        'link': full_link,
                        'guncelleme_yili': guncelleme_yili or 'Bilinmiyor'
                    }
                    
                except Exception as e:
                    print(f"Alan işleme hatası (sınıf {sinif_kodu}): {e}")
                    continue
            
            return sinif_kodu, alanlar
            
        except Exception as e:
            print(f"ÇÖP çekme hatası (sınıf {sinif_kodu}): {e}")
            return sinif_kodu, {}
    
    # Ana işleme
    cop_data = {}
    alan_ids_data = {}
    
    # Paralel olarak tüm sınıfları işle
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        # Her sınıf için ÇÖP verilerini başlat
        cop_futures = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        # Her sınıf için alan ID'lerini başlat
        alan_id_futures = {executor.submit(get_alan_ids, sinif): sinif for sinif in siniflar}
        
        # ÇÖP sonuçlarını topla
        for future in as_completed(cop_futures):
            sinif_kodu, alanlar = future.result()
            if alanlar:
                cop_data[sinif_kodu] = alanlar
                print(f"✅ {sinif_kodu}. sınıf ÇÖP verileri çekildi: {len(alanlar)} alan")
            else:
                print(f"❌ {sinif_kodu}. sınıf ÇÖP verileri çekilemedi")
        
        # Alan ID sonuçlarını topla
        for future in as_completed(alan_id_futures):
            sinif_kodu = alan_id_futures[future]
            alan_ids = future.result()
            if alan_ids:
                alan_ids_data[sinif_kodu] = alan_ids
                print(f"✅ {sinif_kodu}. sınıf alan ID'leri çekildi: {len(alan_ids)} alan")
            else:
                print(f"❌ {sinif_kodu}. sınıf alan ID'leri çekilemedi")
    
    return {
        "cop_data": cop_data,
        "alan_ids": alan_ids_data
    }


def getir_cop_with_db_integration():
    """
    ÇÖP verilerini çeker ve doğrudan veritabanına entegre eder.
    Alan ID'lerini de işler ve veritabanına kaydeder.
    SSE mesajları ile progress tracking sağlar.
    """
    try:
        yield {"type": "status", "message": "ÇÖP verileri çekiliyor..."}
        
        # ÇÖP verilerini çek (alan ID'leri dahil)
        from modules.getir_cop_oku import getir_cop
        cop_and_ids = getir_cop()
        
        if not cop_and_ids or not cop_and_ids.get('cop_data'):
            yield {"type": "error", "message": "ÇÖP verileri çekilemedi"}
            return
        
        cop_data = cop_and_ids.get('cop_data', {})
        alan_ids_data = cop_and_ids.get('alan_ids', {})
        
        yield {"type": "status", "message": f"ÇÖP verileri çekildi: {len(cop_data)} sınıf"}
        yield {"type": "status", "message": f"Alan ID'leri çekildi: {len(alan_ids_data)} sınıf"}
        
        # Veritabanı yolunu bul
        import os
        db_path = "data/temel_plan.db"
        if not os.path.exists(db_path):
            yield {"type": "error", "message": "Veritabanı bulunamadı"}
            return
        
        # Alan ID eşleştirme haritası oluştur
        alan_id_mapping = {}
        for sinif, alan_list in alan_ids_data.items():
            for alan_info in alan_list:
                alan_adi = alan_info.get('isim', '').strip()
                alan_id = alan_info.get('id', '').strip()
                if alan_adi and alan_id:
                    # Normalize et
                    normalized_name = normalize_cop_area_name(alan_adi)
                    alan_id_mapping[normalized_name] = alan_id
        
        yield {"type": "status", "message": f"Alan ID eşleştirme haritası oluşturuldu: {len(alan_id_mapping)} alan"}
        
        # Her sınıf için ÇÖP verilerini işle
        total_processed = 0
        for sinif, alanlar in cop_data.items():
            yield {"type": "status", "message": f"{sinif}. sınıf ÇÖP verileri işleniyor..."}
            
            for alan_adi, info in alanlar.items():
                cop_url = info.get('link', '')
                if cop_url:
                    yield {"type": "status", "message": f"İşleniyor: {alan_adi} ({sinif}. sınıf)"}
                    
                    # Alan ID'sini bul
                    normalized_alan_adi = normalize_cop_area_name(alan_adi)
                    meb_alan_id = alan_id_mapping.get(normalized_alan_adi)
                    
                    # ÇÖP PDF'sini işle ve veritabanına kaydet
                    try:
                        cop_result = oku_cop_pdf(cop_url)
                        if cop_result and cop_result.get('metadata', {}).get('status') == 'success':
                            # Veritabanına kaydet (meb_alan_id ile birlikte)
                            saved = save_cop_results_to_db(cop_result, db_path, meb_alan_id)
                            if saved:
                                status_msg = f"✅ {alan_adi} başarıyla kaydedildi"
                                if meb_alan_id:
                                    status_msg += f" (MEB ID: {meb_alan_id})"
                                yield {"type": "status", "message": status_msg}
                                total_processed += 1
                            else:
                                yield {"type": "error", "message": f"❌ {alan_adi} kaydedilemedi"}
                        else:
                            yield {"type": "error", "message": f"❌ {alan_adi} PDF'si işlenemedi"}
                    except Exception as e:
                        yield {"type": "error", "message": f"❌ {alan_adi} hatası: {str(e)}"}
        
        yield {"type": "status", "message": f"ÇÖP işleme tamamlandı. {total_processed} alan başarıyla işlendi."}
        yield {"type": "done", "message": "ÇÖP veritabanı entegrasyonu tamamlandı"}
        
    except Exception as e:
        yield {"type": "error", "message": f"ÇÖP entegrasyon hatası: {str(e)}"}