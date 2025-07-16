import os
import re
import json
import pdfplumber
from typing import Dict, List, Any, Optional, Tuple
import sys
import random

try:
    from .utils import normalize_to_title_case_tr, with_database, scan_directory_for_pdfs
except ImportError:
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from modules.utils import normalize_to_title_case_tr, with_database, scan_directory_for_pdfs

# ------------- YARDIMCI FONKSİYONLAR ------------- #

def clean_text(text: str) -> str:
    """Gereksiz karakterleri ve çoklu boşlukları temizler."""
    if not text:
        return ""
    text = str(text).replace('\n', ' ')
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ------------- YENİ İŞ AKIŞI FONKSİYONLARI ------------- #

def extract_alan_dal_from_table_headers(pdf: pdfplumber.PDF) -> Tuple[Optional[str], List[str]]:
    """
    Tablo başlıklarından (HAFTALIK DERS ÇİZELGESİ üstünden) Alan ve Dal adlarını çıkarır.
    """
    alan_adi = None
    dallar = set()

    print("   🔍 Tablo başlıklarından alan ve dal bilgileri aranıyor...")
    
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            if "HAFTALIK DERS ÇİZELGESİ" in line.upper():
                print(f"      📊 Sayfa {page_num+1}: 'Haftalık Ders Çizelgesi' bulundu, üst satırlar kontrol ediliyor...")
                
                # Tablo başlığının üstündeki 10 satırı kontrol et
                search_range = range(max(0, line_idx - 10), line_idx)
                for i in search_range:
                    check_line = clean_text(lines[i]).upper()
                    
                    # Alan adı tespiti: "{ALAN_ADI} ALANI" formatı
                    alan_match = re.search(r'(.+?)\s+ALANI\s*$', check_line)
                    if alan_match:
                        potential_alan = alan_match.group(1).strip()
                        if len(potential_alan) > 5:
                            alan_adi = normalize_to_title_case_tr(potential_alan)
                            print(f"      ✅ Alan Adı (Tablo başlığı) tespit edildi: {alan_adi}")
                    
                    # Dal adı tespiti: "({DAL_ADI} DALI)" formatı
                    dal_match = re.search(r'\((.+?)\s+DALI\)', check_line)
                    if not dal_match:
                        # Alternatif format: "{DAL_ADI} DALI" (parantez olmadan)
                        dal_match = re.search(r'(.+?)\s+DALI\s*$', check_line)
                    
                    if dal_match:
                        potential_dal = dal_match.group(1).strip()
                        if len(potential_dal) > 3:
                            dal_normalized = normalize_to_title_case_tr(potential_dal)
                            dallar.add(dal_normalized)
                            print(f"      ✅ Dal Adı (Tablo başlığı) tespit edildi: {dal_normalized}")

    dallar_list = sorted(list(dallar))
    if dallar_list:
        print(f"   ✅ Toplam Dal Adları (Tablo başlıkları): {dallar_list}")

    return alan_adi, dallar_list

def parse_schedule_table(table: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Bir "Haftalık Ders Çizelgesi" tablosunu analiz ederek ders, sınıf ve saat bilgilerini çıkarır.
    """
    ders_listesi = []
    if not table or len(table) < 5:
        # print("      DEBUG: Tablo çok kısa veya boş.") # Too verbose
        return []

    # print("      DEBUG: parse_schedule_table - Tablo içeriği (ilk 5 satır):")
    # for r_idx, row in enumerate(table[:5]):
    #     print(f"         Row {r_idx}: {row}")

    # Sınıf seviyelerini ve sütun indekslerini bul
    header_rows = table[:3] # Check first 3 rows for headers
    class_level_cols = {}
    ders_col_idx = -1

    # print("      DEBUG: Başlık satırları aranıyor...")
    for h_idx, header_row in enumerate(header_rows):
        # print(f"         DEBUG: Header Row {h_idx}: {header_row}")
        for i, cell in enumerate(header_row):
            if cell:
                cell_text = clean_text(cell)
                # print(f"            DEBUG: Cell ({h_idx},{i}): '{cell_text}'")
                # Multi-row header için "DERSLER" sütunu tespiti öncelikli
                # Only accept exact "DERSLER" match, not "ORTAK DERSLER" etc.
                if cell_text.upper().strip() == "DERSLER":
                    ders_col_idx = i  # DERSLER her zaman öncelikli - override any previous
                    # print(f"               DEBUG: Dersler sütunu bulundu (priority): {ders_col_idx}")
                elif (cell_text.upper().strip() == "DERS" and "KATEGOR" not in cell_text.upper()) and ders_col_idx == -1:
                    ders_col_idx = i
                    # print(f"               DEBUG: Ders sütunu bulundu: {ders_col_idx}")
                elif ("DERSLER" in cell_text.upper() or "DERS" in cell_text.upper()) and ders_col_idx != -1:
                    # print(f"               DEBUG: Ders sütunu zaten bulunmuş ({ders_col_idx}), '{cell_text}' atlanıyor")
                    pass
                match = re.search(r'(\d+)\.\s*SINIF', cell_text.upper())
                if match:
                    class_level_cols[i] = f"{match.group(1)}. Sınıf"
                    # print(f"               DEBUG: Sınıf sütunu bulundu: {class_level_cols[i]} at index {i}")
                elif re.search(r'(\d+)\.', cell_text.upper()):
                    # "9." şeklinde sayı varsa bir sonraki hücreye bak
                    number_match = re.search(r'(\d+)\.', cell_text.upper())
                    # print(f"               DEBUG: Sayı bulundu: {number_match.group(1)}, sınıf aranıyor...")
                    if number_match and i+1 < len(header_row) and header_row[i+1] and "SINIF" in clean_text(header_row[i+1]).upper():
                        class_level_cols[i] = f"{number_match.group(1)}. Sınıf"
                        # print(f"               DEBUG: Sınıf sütunu bulundu (split): {class_level_cols[i]} at index {i}")
                    # Ayrıca bir sonraki header row'da "SINIF" kelimesi varsa kontrol et
                    elif number_match and h_idx + 1 < len(header_rows):
                        next_header_row = header_rows[h_idx + 1]
                        if i < len(next_header_row) and next_header_row[i] and "SINIF" in clean_text(next_header_row[i]).upper():
                            class_level_cols[i] = f"{number_match.group(1)}. Sınıf"
                            # print(f"               DEBUG: Sınıf sütunu bulundu (next row): {class_level_cols[i]} at index {i}")
                    # Ayrıca aynı pozisyondaki farklı satırlarda "SINIF" arıyoruz
                    if number_match:
                        # print(f"               DEBUG: Tüm satırlarda sınıf aranıyor - number_match={number_match.group(1)}")
                        for other_h_idx in range(len(header_rows)):
                            if other_h_idx != h_idx and i < len(header_rows[other_h_idx]) and header_rows[other_h_idx][i]:
                                other_cell_text = clean_text(header_rows[other_h_idx][i])
                                # print(f"               DEBUG: Diğer satırda kontrol: h_idx={other_h_idx}, i={i}, cell='{other_cell_text}'")
                                if "SINIF" in other_cell_text.upper():
                                    class_level_cols[i] = f"{number_match.group(1)}. Sınıf"
                                    # print(f"               DEBUG: Sınıf sütunu bulundu (multi-row): {class_level_cols[i]} at index {i}")
                                    break
        # Don't break early, process all header rows first
        # if ders_col_idx != -1 and class_level_cols: # Found both, no need to check further header rows
        #     # print("         DEBUG: Ders ve Sınıf sütunları başlıkta bulundu, diğer başlık satırları atlanıyor.") # Too verbose
        #     break

    if ders_col_idx == -1 or not class_level_cols:
        print("      ❌ Tablo başlığında Sınıf veya Ders sütunları bulunamadı.")
        return []
    
    # print(f"      DEBUG: Ders sütunu indeksi: {ders_col_idx}") # Too verbose
    # print(f"      DEBUG: Sınıf sütunları: {class_level_cols}") # Too verbose

    # Meslek dersleri bölümünü bul ve dersleri işle
    meslek_dersleri_started = False
    # Start from the row after the last header row found
    start_row_idx = max(header_rows.index(header_row) for header_row in header_rows if header_row in table) + 1 if header_rows else 0
    # print(f"      DEBUG: Ders işleme başlangıç satırı: {start_row_idx}") # Too verbose

    for r_idx, row in enumerate(table[start_row_idx:]):
        current_row_idx = start_row_idx + r_idx
        kategori_cell = clean_text(row[0]).upper() if row and row[0] else ""
        # if "MESLEK" in kategori_cell:
        #     print(f"      DEBUG: Satır {current_row_idx} - Kategori Hücresi: '{kategori_cell}'") # Too verbose

        # Encoding-safe MESLEK DERSLERİ tespiti
        if ("MESLEK DERSLERİ" in kategori_cell or 
            "MESLEKİ DERSLER" in kategori_cell or
            "MESLEK DERSLER" in kategori_cell or  # İ harfi eksik
            "MESLEK" in kategori_cell and ("DERS" in kategori_cell)):  # Genel güvenlik
            meslek_dersleri_started = True
            # print(f"         DEBUG: MESLEK DERSLERİ bölümü başladı. (Satır {current_row_idx})")
            continue

        if "TOPLAM" in kategori_cell or "SEÇMELİ" in kategori_cell:
            if meslek_dersleri_started: # Only break if we were already in meslek dersleri section
                meslek_dersleri_started = False
                # print(f"         DEBUG: MESLEK DERSLERİ bölümü bitti. (Satır {current_row_idx})") # Too verbose
                break

        if meslek_dersleri_started and len(row) > ders_col_idx:
            # print(f"         DEBUG: Full row content: {row}")
            # print(f"         DEBUG: Row length: {len(row)}, ders_col_idx: {ders_col_idx}")
            
            # Try adjacent columns for course name detection too
            ders_adi = ""
            found_course_name = False
            for offset in [0, -1, 1, -2, 2]:
                check_idx = ders_col_idx + offset
                if len(row) > check_idx >= 0 and row[check_idx]:
                    potential_ders_adi = clean_text(row[check_idx])
                    # "Toplam", "TOPLAMI" veya "Rehberlik ve Yönlendirme" içeren satırları ders olarak kabul etme
                    if potential_ders_adi and len(potential_ders_adi) >= 4:
                        potential_upper = potential_ders_adi.upper()
                        if ("TOPLAM" in potential_upper or 
                            "REHBERLİK" in potential_upper and "YÖNLENDİRME" in potential_upper):
                            # print(f"         ⚠️ Ders olmayan satır atlandı: '{potential_ders_adi}'")
                            continue
                        ders_adi = potential_ders_adi
                        # print(f"         DEBUG: Ders adı bulundu: '{ders_adi}' [col_idx={check_idx}, offset={offset}]")
                        found_course_name = True
                        break
                        
            if not found_course_name:
                # print(f"         DEBUG: Geçerli ders adı bulunamadı (ders_col_idx={ders_col_idx} ±2)")
                continue

            # Dipnot işaretlerini temizle (*), (**), (***) vs.
            ders_adi_temizlenmis = re.sub(r'\s*\(\*+\)\s*', '', ders_adi).strip()
            ders_adi_normalized = normalize_to_title_case_tr(ders_adi_temizlenmis)
            # print(f"         DEBUG: Normalize edilmiş ders adı: '{ders_adi_normalized}'") # Too verbose

            for col_idx, sinif in class_level_cols.items():
                # Try the detected column first, then check adjacent columns (±1, ±2)
                found_hour = False
                for offset in [0, -1, 1, -2, 2]:
                    check_idx = col_idx + offset
                    if len(row) > check_idx >= 0 and row[check_idx]:
                        saat_str = clean_text(row[check_idx])
                        if saat_str and saat_str.isdigit() and 1 <= int(saat_str) <= 10:
                            ders_listesi.append({
                                "ders_adi": ders_adi_normalized,
                                "sinif": sinif,
                                "saat": int(saat_str)
                            })
                            # print(f"            ✅ Ders eklendi: {ders_adi_normalized} ({sinif} - {saat_str} saat) [col_idx={check_idx}, offset={offset}]")
                            found_hour = True
                            break
                        elif saat_str:
                            # print(f"            DEBUG: Sınıf '{sinif}' col_idx={check_idx}: '{saat_str}' geçersiz saat")
                            pass
                    
                if not found_hour:
                    # print(f"            DEBUG: Sınıf '{sinif}' için geçerli saat bulunamadı (col_idx={col_idx} ±2)")
                    pass
    
    # print(f"      DEBUG: parse_schedule_table bitişi. Toplam ders: {len(ders_listesi)}") # Too verbose
    return ders_listesi

def find_dal_name_for_schedule(lines: List[str], schedule_line_index: int) -> Optional[str]:
    """
    Ders çizelgesinin hangi dala ait olduğunu bulur.
    """
    # Çizelgenin üstündeki 15 satırı tara
    search_range = range(max(0, schedule_line_index - 15), schedule_line_index)
    for i in search_range:
        line = clean_text(lines[i]).upper()
        dal_match = re.search(r'(.+?)\s+DALI(?:\s*[\.0-9\.]*)*$', line)
        if dal_match:
            dal_name = dal_match.group(1).strip()
            if len(dal_name) > 3:
                return normalize_to_title_case_tr(dal_name)
    return None

def extract_ders_info_from_schedules(pdf: pdfplumber.PDF) -> Dict[str, List[Dict[str, Any]]]:
    """
    Tüm "Haftalık Ders Çizelgesi" tablolarından ders bilgilerini çıkarır ve dala göre gruplar.
    """
    dal_ders_map = {}
    tum_dersler = []

    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if not text:
            continue
        
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            if "HAFTALIK DERS ÇİZELGESİ" in line.upper():
                print(f"\n   📊 Sayfa {i+1}: 'Haftalık Ders Çizelgesi' bulundu.")
                dal_adi = find_dal_name_for_schedule(lines, line_idx)
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    # print(f"      DEBUG: Sayfa {i+1}, Tablo {table_idx+1} işleniyor.") # Too verbose
                    dersler = parse_schedule_table(table)
                    if not dersler:
                        # print(f"      DEBUG: Sayfa {i+1}, Tablo {table_idx+1} için ders bulunamadı.") # Too verbose
                        continue
                    
                    print(f"      ✅ Sayfa {i+1}, Tablo {table_idx+1}: {len(dersler)} ders bulundu.")

                    if dal_adi:
                        print(f"      🔗 Tablo, '{dal_adi}' dalı ile ilişkilendirildi.")
                        if dal_adi not in dal_ders_map:
                            dal_ders_map[dal_adi] = []
                        dal_ders_map[dal_adi].extend(dersler)
                    else:
                        print("      ⚠️ Tablo için spesifik bir dal adı bulunamadı, genel listeye ekleniyor.")
                        tum_dersler.extend(dersler)
                # break # Sayfadaki ilk çizelgeyi işle ve sonraki sayfaya geç - Removed to process all tables on a page

    # Dalsız dersleri ele al - eğer dal_ders_map boş ve tüm dersler varsa, ilk dala ata
    if tum_dersler:
        if len(dal_ders_map) == 0:
            print(f"   ℹ️ Tablolarda dal bulunamadı, dersler genel listede kalıyor.")
            dal_ders_map["Genel"] = tum_dersler
        elif len(dal_ders_map) == 1:
            tek_dal = list(dal_ders_map.keys())[0]
            print(f"   ℹ️ İlişkisiz dersler tek dal olan '{tek_dal}'e atanıyor.")
            dal_ders_map[tek_dal].extend(tum_dersler)
        else:
            # Birden fazla dal var, ilk dala ata
            ilk_dal = list(dal_ders_map.keys())[0]
            print(f"   ℹ️ İlişkisiz dersler çoklu dal olduğu için '{ilk_dal}'e atanıyor.")
            dal_ders_map[ilk_dal].extend(tum_dersler)

    # Dersleri tekilleştir
    for dal, ders_listesi in dal_ders_map.items():
        unique_dersler = {json.dumps(d, sort_keys=True): d for d in ders_listesi}.values()
        dal_ders_map[dal] = sorted(list(unique_dersler), key=lambda x: x['ders_adi'])

    return dal_ders_map

# ------------- ANA PDF OKUMA FONKSİYONU ------------- #

def oku_cop_pdf_file(pdf_path: str) -> Dict[str, Any]:
    """
    Tek bir COP PDF dosyasını yeni kurallara göre okur ve yapılandırır.
    """
    if not os.path.isfile(pdf_path):
        return {"hata": f"PDF bulunamadı: {pdf_path}"}

    alan_adi = None
    dallar = []
    dal_ders_map = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"\n▶︎ {pdf_path} işleniyor...")
            # 1. Alan ve Dalları "Tablo başlıkları"ndan al
            alan_adi, dallar = extract_alan_dal_from_table_headers(pdf)
            # print(f"   DEBUG: oku_cop_pdf_file - extract_alan_dal_from_toc sonrası alan_adi: {alan_adi}") # Too verbose

            if not alan_adi:
                print("   ❌ Devam edilemiyor: Alan adı bulunamadı.")
                return {"hata": "Alan adı 'İçindekiler' bölümünden okunamadı."}

            # 2. Ders, Sınıf ve Saatleri "Haftalık Ders Çizelgesi" tablolarından al
            dal_ders_map = extract_ders_info_from_schedules(pdf)

    except Exception as e:
        print(f"   ❌ PDF işlenirken bir hata oluştu: {e}")
        return {"hata": str(e)}

    # 3. Sonuçları yapılandır
    dal_ders_listesi = []
    toplam_ders_sayisi = 0

    # Genel listede dersler varsa, bunları dallara eşit olarak dağıt
    genel_dersler = dal_ders_map.get("Genel", [])
    if genel_dersler:
        print(f"   🔄 {len(genel_dersler)} ders 'Genel' listede bulundu, dallara dağıtılıyor...")
        dal_ders_map.pop("Genel", None)  # Genel listesini kaldır
        
        if dallar:
            # Dersleri eşit olarak dallara dağıt
            ders_per_dal = len(genel_dersler) // len(dallar)
            kalan_dersler = len(genel_dersler) % len(dallar)
            
            for i, dal in enumerate(dallar):
                baslangic = i * ders_per_dal
                bitis = baslangic + ders_per_dal
                if i < kalan_dersler:
                    bitis += 1
                
                if dal not in dal_ders_map:
                    dal_ders_map[dal] = []
                dal_ders_map[dal].extend(genel_dersler[baslangic:bitis])

    for dal in dallar:
        dersler = dal_ders_map.get(dal, [])
        # Yakın isimli dal adlarını da kontrol et (örn: Bilişim Teknolojileri vs Bilişim Teknolojisi)
        if not dersler:
             for key, value in dal_ders_map.items():
                 # Check for partial matches or similar names
                 if dal.upper() in key.upper() or key.upper() in dal.upper():
                     dersler = value
                     break

        dal_ders_listesi.append({
            "dal_adi": dal,
            "dersler": dersler,
            "ders_sayisi": len(dersler)
        })
        toplam_ders_sayisi += len(dersler)

    # Çıktıyı terminale yazdır
    # Relative path oluştur ki terminal'de tıklanabilir olsun
    try:
        relative_path = os.path.relpath(pdf_path, os.getcwd())
        # Eğer relative path daha uzunsa absolute kullan ama tırnak içinde
        if len(relative_path) > len(pdf_path) or relative_path.startswith('../../../'):
            display_path = f'"{pdf_path}"'
        else:
            display_path = relative_path
    except:
        display_path = f'"{pdf_path}"'
    
    print(f"\n🎯 SONUÇLAR ÖZET:")
    print(f"   📁 PDF: {display_path}")
    print(f"   📚 Alan Adı: {alan_adi}")
    print(f"   🏭 Dal Sayısı: {len(dallar)}")
    print(f"   📖 Toplam Ders Sayısı: {toplam_ders_sayisi}")
    
    print(f"\n📋 DAL VE DERS DETAYLARI:")
    for dal_info in dal_ders_listesi:
        print(f"   🏭 {dal_info['dal_adi']} ({dal_info['ders_sayisi']} ders)")
        for ders in dal_info['dersler']:
            print(f"      📖 {ders['ders_adi']} - {ders['sinif']} ({ders['saat']} saat)")

    return {
        "alan_bilgileri": {
            "alan_adi": alan_adi,
            "dal_sayisi": len(dallar),
            "toplam_ders_sayisi": toplam_ders_sayisi,
            "dal_ders_listesi": dal_ders_listesi,
        },
        "metadata": {
            "pdf_path": os.path.basename(pdf_path),
            "status": "success" if alan_adi and dallar and toplam_ders_sayisi > 0 else "partial",
        },
    }

# ------------- VERİTABANI ENTEGRASYONU ------------- #

@with_database
def save_cop_results_to_db(cursor, result: Dict[str, Any]) -> int:
    """
    oku_cop_pdf_file() sonuçlarını veritabanına kaydeder.
    Returns: Kaydedilen ders sayısı
    """
    print(f"   💾 Veritabanına kaydetme başlatıldı...")
    
    if not result or "alan_bilgileri" not in result:
        print(f"   ❌ Result veya alan_bilgileri eksik")
        return 0
    
    alan_bilgileri = result["alan_bilgileri"]
    alan_adi = alan_bilgileri.get("alan_adi", "")
    dal_ders_listesi = alan_bilgileri.get("dal_ders_listesi", [])
    
    if not alan_adi or not dal_ders_listesi:
        print(f"   ❌ Alan adı veya dal-ders listesi eksik. Alan: {alan_adi}, Dal sayısı: {len(dal_ders_listesi)}")
        return 0
    
    print(f"   📊 Kaydedilecek: Alan='{alan_adi}', Dal sayısı={len(dal_ders_listesi)}")
    saved_count = 0
    
    try:
        # Alan kaydı/bulma (duplicate check)
        cursor.execute("SELECT id FROM temel_plan_alan WHERE alan_adi = ?", (alan_adi,))
        alan_result = cursor.fetchone()
        
        if alan_result:
            alan_id = alan_result['id']
            print(f"  ↻ Mevcut alan kullanılıyor: {alan_adi}")
        else:
            cursor.execute("INSERT INTO temel_plan_alan (alan_adi) VALUES (?)", (alan_adi,))
            alan_id = cursor.lastrowid
            print(f"  ➕ Yeni alan eklendi: {alan_adi}")
        
        # Dal ve ders kayıtları
        for dal_info in dal_ders_listesi:
            dal_adi = dal_info.get("dal_adi", "")
            dersler = dal_info.get("dersler", [])
            
            if not dal_adi or not dersler:
                continue
            
            # Dal kaydı/bulma (duplicate check)
            cursor.execute("SELECT id FROM temel_plan_dal WHERE dal_adi = ? AND alan_id = ?", (dal_adi, alan_id))
            dal_result = cursor.fetchone()
            
            if dal_result:
                dal_id = dal_result['id']
                print(f"    ↻ Mevcut dal kullanılıyor: {dal_adi}")
            else:
                cursor.execute("INSERT INTO temel_plan_dal (dal_adi, alan_id) VALUES (?, ?)", (dal_adi, alan_id))
                dal_id = cursor.lastrowid
                print(f"    ➕ Yeni dal eklendi: {dal_adi}")
            
            # Ders kayıtları
            for ders in dersler:
                ders_adi = ders.get("ders_adi", "")
                sinif_raw = ders.get("sinif", 0)
                saat = ders.get("saat", 0)
                
                # Sınıf bilgisini integer'a çevir
                sinif = 0
                if isinstance(sinif_raw, str):
                    # "11. Sınıf" -> 11
                    import re
                    match = re.search(r'(\d+)', sinif_raw)
                    if match:
                        sinif = int(match.group(1))
                elif isinstance(sinif_raw, int):
                    sinif = sinif_raw
                
                if not ders_adi or sinif <= 0:
                    continue
                
                # Merkezi ders kaydetme fonksiyonunu kullan
                from .utils import create_or_get_ders
                
                ders_id = create_or_get_ders(
                    cursor=cursor,
                    ders_adi=ders_adi,
                    sinif=sinif,
                    ders_saati=saat,
                    amac='',
                    dm_url='',
                    dbf_url='',
                    bom_url='',
                    cop_url=''
                )
                
                # Ders-Dal ilişkisi (sadece ders_id varsa)
                if ders_id:
                    from .utils import create_ders_dal_relation
                    create_ders_dal_relation(cursor, ders_id, dal_id)
                
                saved_count += 1
    
    except Exception as e:
        print(f"   ❌ ÇÖP veri kayıt hatası: {e}")
        return 0
    
    print(f"   ✅ Veritabanı kaydı tamamlandı: {saved_count} ders kaydedildi")
    return saved_count

# ------------- COP PROCESSING WORKFLOW FONKSİYONLARI ------------- #

def process_all_cop_pdfs(cop_root_dir="data/cop"):
    """
    Standalone COP PDF işleme fonksiyonu.
    Tüm COP klasörlerini tarar ve PDF'leri işler.
    
    Args:
        cop_root_dir: COP PDF'lerinin bulunduğu ana dizin
        
    Returns:
        Dict: İşlem sonuçları
    """
    print(f"🔍 COP PDF tarama başlatılıyor: {cop_root_dir}")
    
    if not os.path.exists(cop_root_dir):
        print(f"❌ COP dizini bulunamadı: {cop_root_dir}")
        return {"error": "COP dizini bulunamadı", "processed": 0}
    
    # Merkezi scan_directory_for_pdfs fonksiyonunu kullan
    pdf_files = scan_directory_for_pdfs(cop_root_dir, file_extensions=('.pdf',))
    
    if not pdf_files:
        print(f"📂 '{cop_root_dir}' dizininde PDF bulunamadı.")
        return {"processed": 0, "message": "PDF bulunamadı"}
    
    print(f"📄 {len(pdf_files)} COP PDF bulundu. İşleniyor...")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    for pdf_info in pdf_files:
        try:
            pdf_path = pdf_info["path"]
            print(f"\n🔍 İşleniyor: {pdf_info['relative_path']}")
            
            result = oku_cop_pdf_file(pdf_path)
            
            if result and "hata" not in result:
                # Veritabanına kaydet
                saved_count = save_cop_results_to_db(result)
                if saved_count > 0:
                    success_count += 1
                    print(f"✅ Başarılı: {pdf_info['name']} ({saved_count} ders kaydedildi)")
                else:
                    error_count += 1
                    print(f"⚠️ Veri kaydedilemedi: {pdf_info['name']}")
            else:
                error_count += 1
                error_msg = result.get("hata", "Bilinmeyen hata") if result else "İşleme hatası"
                print(f"❌ Hata: {pdf_info['name']} - {error_msg}")
            
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"❌ İşleme hatası ({pdf_info['name']}): {e}")
    
    print(f"\n🎯 COP İşleme Tamamlandı:")
    print(f"   📊 Toplam işlenen: {processed_count}")
    print(f"   ✅ Başarılı: {success_count}")
    print(f"   ❌ Hatalı: {error_count}")
    
    return {
        "processed": processed_count,
        "success": success_count,
        "errors": error_count,
        "total_pdfs": len(pdf_files)
    }

@with_database
def process_cop_directories_and_read(cursor, cop_root_dir="data/cop"):
    """
    SSE-enabled COP PDF işleme workflow'u.
    Progress mesajları yield eder.
    
    Args:
        cursor: Database cursor (decorator tarafından sağlanır)
        cop_root_dir: COP PDF'lerinin bulunduğu ana dizin
        
    Yields:
        Dict: Progress mesajları
    """
    yield {'type': 'status', 'message': f'COP PDF tarama başlatılıyor: {cop_root_dir}'}
    
    if not os.path.exists(cop_root_dir):
        yield {'type': 'error', 'message': f'COP dizini bulunamadı: {cop_root_dir}'}
        return
    
    # 1. PDF dosyalarını tara
    yield {'type': 'status', 'message': 'COP PDF dosyaları taranıyor...'}
    pdf_files = scan_directory_for_pdfs(cop_root_dir, file_extensions=('.pdf',))
    
    if not pdf_files:
        yield {'type': 'warning', 'message': f'{cop_root_dir} dizininde PDF bulunamadı.'}
        return
    
    yield {'type': 'status', 'message': f'{len(pdf_files)} COP PDF bulundu.'}
    
    # 2. PDF'leri işle
    processed_count = 0
    success_count = 0
    error_count = 0
    total_pdfs = len(pdf_files)
    
    for pdf_info in pdf_files:
        try:
            pdf_path = pdf_info["path"]
            relative_path = pdf_info["relative_path"]
            
            yield {'type': 'progress', 'message': f'İşleniyor: {relative_path}', 'progress': processed_count / total_pdfs}
            
            result = oku_cop_pdf_file(pdf_path)
            
            if result and "hata" not in result:
                # Veritabanına kaydet
                saved_count = save_cop_results_to_db(result)
                if saved_count > 0:
                    success_count += 1
                    yield {'type': 'success', 'message': f'Başarılı: {pdf_info["name"]} ({saved_count} ders kaydedildi)'}
                else:
                    error_count += 1
                    yield {'type': 'warning', 'message': f'Veri kaydedilemedi: {pdf_info["name"]}'}
            else:
                error_count += 1
                error_msg = result.get("hata", "Bilinmeyen hata") if result else "İşleme hatası"
                yield {'type': 'error', 'message': f'Hata: {pdf_info["name"]} - {error_msg}'}
            
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            yield {'type': 'error', 'message': f'İşleme hatası ({pdf_info["name"]}): {e}'}
    
    # 3. Özet rapor
    yield {'type': 'status', 'message': f'COP İşleme Tamamlandı: {processed_count} işlendi, {success_count} başarılı, {error_count} hatalı'}
    yield {'type': 'done', 'message': f'Tüm COP PDF\'leri işlendi. Toplam: {total_pdfs}, Başarılı: {success_count}'}

# ------------- KOMUT SATIRI GİRİŞ NOKTASI ------------- #

def oku_tum_pdfler(root_dir: str = ".") -> None:
    """
    root_dir içindeki tüm .pdf dosyalarını merkezi tarama fonksiyonu ile tarar.
    """
    # Merkezi scan_directory_for_pdfs fonksiyonunu kullan
    pdf_files = scan_directory_for_pdfs(root_dir, file_extensions=('.pdf',))
    
    if not pdf_files:
        print(f"📂 '{root_dir}' dizininde PDF bulunamadı.")
        return

    print(f"📄 {len(pdf_files)} PDF bulundu. İşleniyor...")
    for pdf_info in pdf_files:
        pdf_path = pdf_info["path"]
        print(f"🔍 İşleniyor: {pdf_info['relative_path']}")
        result = oku_cop_pdf_file(pdf_path)
        # JSON çıktısı kaldırıldı - sadece terminal özeti gösteriliyor
        print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        argument = sys.argv[1]
        if argument == 'random':
            base_cop_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'cop')
            try:
                subdirectories = [d for d in os.listdir(base_cop_dir) if os.path.isdir(os.path.join(base_cop_dir, d))]
                subdirectories.sort()  # Alfabetik sıralama
                if not subdirectories:
                    print(f"📂 '{base_cop_dir}' içinde okunacak alt dizin bulunamadı.")
                else:
                    random_dir_name = random.choice(subdirectories)
                    target_dir = os.path.join(base_cop_dir, random_dir_name)
                    print(f"🔍 Rastgele seçilen dizin: {target_dir}")
                    oku_tum_pdfler(root_dir=target_dir)
            except FileNotFoundError:
                print(f"❌ Ana dizin bulunamadı: {base_cop_dir}")
            except Exception as e:
                print(f"Beklenmedik bir hata oluştu: {e}")
        elif os.path.isdir(argument):
            print(f"🔍 Belirtilen dizin işleniyor: {argument}")
            oku_tum_pdfler(root_dir=argument)
        else:
            print(f"❌ Hata: '{argument}' geçerli bir dizin değil veya 'random' komutu değil.")
            print("\nKullanım: python modules/oku_cop.py [random | <dizin_yolu>]")
    else:
        print("Kullanım: python modules/oku_cop.py [random | <dizin_yolu>]")