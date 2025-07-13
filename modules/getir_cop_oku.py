import pdfplumber
import requests
import re
import os
import json
from typing import Dict, List, Any, Optional
from .utils import normalize_to_title_case_tr


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
    # URL'den alan adını çıkarmaya çalış
    if 'meslek.meb.gov.tr' in pdf_url:
        # URL pattern: .../cop9/alan_adi_9.pdf
        url_match = re.search(r'/cop\d+/([^/]+)_\d+\.pdf$', pdf_url)
        if url_match:
            url_alan = url_match.group(1).replace('_', ' ')
            return normalize_to_title_case_tr(url_alan)
    
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
                        combined_dersler = list(set(existing_dersler + dersler))
                        dal_ders_mapping[dal_adi_clean] = combined_dersler
    
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


def extract_lessons_from_schedule_table(page, pdf, page_num: int) -> List[str]:
    """
    Sayfa tablolarından sadece MESLEK DERSLERİ bölümündeki dersleri çıkar
    """
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


def extract_alan_dal_ders_from_cop_pdf(pdf_url: str) -> tuple[Optional[str], List[str], Dict[str, List[str]]]:
    """
    COP PDF'sinden alan, dal ve ders bilgilerini çıkar
    """
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        
        temp_pdf_path = "temp_cop.pdf"
        with open(temp_pdf_path, 'wb') as f:
            f.write(response.content)
        
        alan_adi = None
        dallar = []
        dal_ders_mapping = {}
        
        with pdfplumber.open(temp_pdf_path) as pdf:
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
        
        try:
            os.remove(temp_pdf_path)
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
        toplam_ders_sayisi = sum(len(set(info['dersler'])) for info in dal_ders_listesi)
        
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
    
    # Kısmi eşleşme kontrolü
    for db_name, area_id in db_areas.items():
        if normalized_html_name.lower() in db_name.lower() or db_name.lower() in normalized_html_name.lower():
            print(f"COP Kısmi eşleşme bulundu: '{html_area_name}' -> '{db_name}' (ID: {area_id})")
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


def save_cop_results_to_db(cop_results: Dict[str, Any], db_path: str) -> bool:
    """
    COP okuma sonuçlarını veritabanına kaydet
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


def getir_cop(siniflar=["9", "10", "11", "12"]):
    """
    MEB sitesinden ÇÖP (Çerçeve Öğretim Programı) verilerini çeker.
    
    Args:
        siniflar (list): Çekilecek sınıf seviyeleri (default: ["9", "10", "11", "12"])
    
    Returns:
        dict: Sınıf bazında alan ve ÇÖP URL'leri
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
    
    # Paralel olarak tüm sınıfları işle
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        # Her sınıf için görevi başlat
        futures = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        
        # Sonuçları topla
        for future in as_completed(futures):
            sinif_kodu, alanlar = future.result()
            if alanlar:
                cop_data[sinif_kodu] = alanlar
                print(f"✅ {sinif_kodu}. sınıf ÇÖP verileri çekildi: {len(alanlar)} alan")
            else:
                print(f"❌ {sinif_kodu}. sınıf ÇÖP verileri çekilemedi")
    
    return cop_data


def getir_cop_with_db_integration():
    """
    ÇÖP verilerini çeker ve doğrudan veritabanına entegre eder.
    SSE mesajları ile progress tracking sağlar.
    """
    try:
        yield {"type": "status", "message": "ÇÖP verileri çekiliyor..."}
        
        # ÇÖP verilerini çek
        from modules.getir_cop_oku import getir_cop
        cop_data = getir_cop()
        
        if not cop_data:
            yield {"type": "error", "message": "ÇÖP verileri çekilemedi"}
            return
        
        yield {"type": "status", "message": f"ÇÖP verileri çekildi: {len(cop_data)} sınıf"}
        
        # Veritabanı yolunu bul
        import os
        db_path = "data/temel_plan.db"
        if not os.path.exists(db_path):
            yield {"type": "error", "message": "Veritabanı bulunamadı"}
            return
        
        # Her sınıf için ÇÖP verilerini işle
        total_processed = 0
        for sinif, alanlar in cop_data.items():
            yield {"type": "status", "message": f"{sinif}. sınıf ÇÖP verileri işleniyor..."}
            
            for alan_adi, info in alanlar.items():
                cop_url = info.get('link', '')
                if cop_url:
                    yield {"type": "status", "message": f"İşleniyor: {alan_adi} ({sinif}. sınıf)"}
                    
                    # ÇÖP PDF'sini işle ve veritabanına kaydet
                    try:
                        cop_result = oku_cop_pdf(cop_url)
                        if cop_result and cop_result.get('metadata', {}).get('status') == 'success':
                            # Veritabanına kaydet
                            saved = save_cop_results_to_db(cop_result, db_path)
                            if saved:
                                yield {"type": "status", "message": f"✅ {alan_adi} başarıyla kaydedildi"}
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