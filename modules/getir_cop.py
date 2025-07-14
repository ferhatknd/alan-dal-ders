"""
modules/getir_cop.py - ÇÖP (Çerçeve Öğretim Programları) İndirme ve Veritabanı Entegrasyonu

Bu modül:
1. MEB sitesinden ÇÖP verilerini çeker (getir_cop)
2. PDF'leri indirir ve cache'ler  
3. modules/oku_cop.py ile PDF analizi yapar
4. Sonuçları veritabanına kaydeder

ÖNEMLİ: PDF okuma işlemleri modules/oku_cop.py tarafından yapılır.
"""

import os
import re
import json
import requests
import sqlite3
from typing import Dict, List, Any, Optional
from .utils import normalize_to_title_case_tr, download_and_cache_pdf, get_temp_pdf_path


def extract_alan_dal_ders_from_cop_pdf(pdf_url: str, cache: bool = True) -> tuple[Optional[str], List[str], Dict[str, List[str]]]:
    """
    COP PDF'sinden alan, dal ve ders bilgilerini çıkar - modules/oku_cop.py kullanıyor
    
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
        
        # Yeni oku_cop.py modülünü kullan
        from modules.oku_cop import oku_cop_pdf_file
        result = oku_cop_pdf_file(pdf_path)
        
        # Geçici dosyayı temizle
        if temp_file:
            try:
                os.remove(pdf_path)
            except:
                pass
        
        if not result or 'alan_bilgileri' not in result:
            return None, [], {}
        
        alan_bilgileri = result['alan_bilgileri']
        alan_adi = alan_bilgileri.get('alan_adi')
        dal_ders_listesi = alan_bilgileri.get('dal_ders_listesi', [])
        
        # Eski format için dönüştür
        dallar = [dal_info['dal_adi'] for dal_info in dal_ders_listesi]
        dal_ders_mapping = {dal_info['dal_adi']: dal_info['dersler'] for dal_info in dal_ders_listesi}
        
        return alan_adi, dallar, dal_ders_mapping
        
    except Exception as e:
        print(f"COP PDF okuma hatası: {e}")
        return None, [], {}


def oku_cop_pdf(pdf_url: str) -> Dict[str, Any]:
    """
    COP PDF'sinden alan, dal ve ders bilgilerini çıkar ve JSON formatında döndür - modules/oku_cop.py kullanıyor
    """
    try:
        alan_adi, dallar, dal_ders_mapping = extract_alan_dal_ders_from_cop_pdf(pdf_url)
        
        if not alan_adi:
            return {
                'alan_bilgileri': {},
                'metadata': {
                    'pdf_url': pdf_url,
                    'status': 'error',
                    'error_message': 'Alan adı bulunamadı'
                }
            }
        
        # Dal-ders yapısını oluştur
        dal_ders_listesi = []
        
        for dal in dallar:
            matched_dersler = dal_ders_mapping.get(dal, [])
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
                'status': 'success',
                'extraction_date': json.dumps(dict(), default=str)
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
        area_id, _ = find_matching_area_id_for_cop(alan_adi, db_areas)
        
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
                    if isinstance(ders_adi, str) and ders_adi.strip():
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
        siniflar (list): Çekilecek sınıflar listesi
    
    Returns:
        dict: {"cop_data": {sınıf: {alan: {link, yil}}}, "alan_ids": {sınıf: [alan_id_listesi]}}
    """
    import time
    from bs4 import BeautifulSoup
    
    all_cop_data = {}
    all_alan_ids = {}
    
    for sinif_kodu in siniflar:
        try:
            print(f"📄 {sinif_kodu}. sınıf ÇÖP verileri çekiliyor...")
            
            # HTML sayfasını çek
            url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
            params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Alan ID'lerini çek
            alan_ids = get_alan_ids(sinif_kodu)
            all_alan_ids[sinif_kodu] = alan_ids
            
            # ÇÖP linklerini çek
            cop_data = {}
            table = soup.find('table', {'class': 'cerceve-table'})
            
            if table:
                rows = table.find_all('tr')[1:]  # Header'ı atla
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        alan_cell = cells[0]
                        cop_cell = cells[1] if len(cells) > 1 else None
                        
                        # Alan adı
                        alan_adi = alan_cell.get_text(strip=True)
                        
                        if cop_cell and alan_adi:
                            # ÇÖP linkini bul
                            cop_link = cop_cell.find('a')
                            if cop_link:
                                cop_url = cop_link.get('href', '')
                                if cop_url and cop_url.endswith('.pdf'):
                                    # Tam URL'yi oluştur
                                    if not cop_url.startswith('http'):
                                        cop_url = f"https://meslek.meb.gov.tr{cop_url}"
                                    
                                    # Yıl bilgisini çıkar (URL'den)
                                    year_match = re.search(r'cop(\d{2})', cop_url)
                                    year = f"20{year_match.group(1)}" if year_match else "2023"
                                    
                                    cop_data[alan_adi] = {
                                        'link': cop_url,
                                        'guncelleme_yili': year
                                    }
            
            all_cop_data[sinif_kodu] = cop_data
            print(f"✅ {sinif_kodu}. sınıf ÇÖP verileri çekildi: {len(cop_data)} alan")
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ {sinif_kodu}. sınıf ÇÖP verileri çekilemedi: {e}")
            all_cop_data[sinif_kodu] = {}
            all_alan_ids[sinif_kodu] = []
    
    return {
        "cop_data": all_cop_data,
        "alan_ids": all_alan_ids
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
        cop_and_ids = getir_cop()
        
        if not cop_and_ids or not cop_and_ids.get('cop_data'):
            yield {"type": "error", "message": "ÇÖP verileri çekilemedi"}
            return
        
        cop_data = cop_and_ids.get('cop_data', {})
        alan_ids_data = cop_and_ids.get('alan_ids', {})
        
        yield {"type": "status", "message": f"ÇÖP verileri çekildi: {len(cop_data)} sınıf"}
        yield {"type": "status", "message": f"Alan ID'leri çekildi: {len(alan_ids_data)} sınıf"}
        
        # Veritabanı yolunu bul
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