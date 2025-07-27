"""
modules/utils-database.py - Database Operations Module

This module contains all database-related functions separated from utils.py.
Includes database connection management, CRUD operations, MEB ID management,
and statistics functions.
"""

import os
import requests
import sqlite3
import functools
from typing import Optional, Callable
import json
import re
import time
from bs4 import BeautifulSoup


def find_or_create_database() -> Optional[str]:
    """
    Veritabanı dosyasını bulur veya oluşturur.
    
    Returns:
        Veritabanı dosyasının yolu veya None
    """
    import os
    
    db_path = "data/temel_plan.db"
    
    # data klasörü yoksa oluştur
    os.makedirs("data", exist_ok=True)
    
    # Database dosyası yoksa oluştur
    if not os.path.exists(db_path):
        try:
            # Schema dosyasından tabloları oluştur
            schema_path = "data/schema.sql"
            if os.path.exists(schema_path):
                with sqlite3.connect(db_path, timeout=30.0) as conn:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        conn.executescript(f.read())
                print(f"✅ Database initialized: {db_path}")
            else:
                # Boş database oluştur
                sqlite3.connect(db_path, timeout=30.0).close()
                print(f"⚠️ Database created without schema: {db_path}")
        except Exception as e:
            print(f"❌ Database creation failed: {e}")
            return None
    
    return db_path

def with_database(func: Callable) -> Callable:
    """
    Database connection decorator.
    
    Fonksiyonu database cursor'ı ile wrap eder.
    İlk parametre olarak cursor geçer.
    
    Usage:
        @with_database
        def my_function(cursor, other_params):
            cursor.execute("SELECT * FROM table")
            return cursor.fetchall()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        db_path = find_or_create_database()
        if not db_path:
            return {"error": "Database not found", "success": False}
        
        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                # Row factory ile dict-style access
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # İlk parametre olarak cursor'ı geç
                result = func(cursor, *args, **kwargs)
                conn.commit() # Değişiklikleri kaydet
                return result
                
        except Exception as e:
            print(f"❌ Database error in {func.__name__}: {e}")
            return {"error": str(e), "success": False}
    
    return wrapper

def with_database_json(func: Callable) -> Callable:
    """
    Database connection decorator for Flask endpoints.
    
    Hata durumunda JSON response döner.
    
    Usage:
        @app.route('/api/endpoint')
        @with_database_json
        def my_endpoint(cursor):
            # cursor kullan
            return {"data": result, "success": True}
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from flask import jsonify
        
        db_path = find_or_create_database()
        if not db_path:
            return jsonify({"error": "Database not found", "success": False}), 500
        
        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                result = func(cursor, *args, **kwargs)
                
                # Tuple response durumu (Flask endpoint'leri için)
                if isinstance(result, tuple):
                    return result
                # Dict response'u jsonify et
                elif isinstance(result, dict):
                    return jsonify(result)
                else:
                    return result
                    
        except Exception as e:
            import datetime
            error_response = {
                "success": False,
                "error": str(e),
                "error_type": "database",
                "timestamp": datetime.datetime.now().isoformat()
            }
            print(f"❌ Database error in {func.__name__}: {e}")
            return jsonify(error_response), 500
    
    return wrapper

def extract_meb_id_from_urls(cop_url=None, dbf_urls=None):
    """
    URL'lerden MEB ID'sini çıkarır.
    ÇÖP ve DBF URL'lerini tarar ve ID'yi bulur.
    
    Args:
        cop_url: ÇÖP URL'si (JSON veya string)
        dbf_urls: DBF URL'leri (JSON veya dict)
        
    Returns:
        str: MEB ID'si ("01", "02", vb.) veya None
    """
    urls_to_check = []
    
    # ÇÖP URL'lerini ekle
    if cop_url:
        try:
            if isinstance(cop_url, str) and cop_url.startswith('{'):
                cop_data = json.loads(cop_url)
                if isinstance(cop_data, dict):
                    urls_to_check.extend(cop_data.values())
            else:
                urls_to_check.append(cop_url)
        except (json.JSONDecodeError, AttributeError):
            urls_to_check.append(cop_url)
    
    # DBF URL'lerini ekle
    if dbf_urls:
        try:
            if isinstance(dbf_urls, str):
                dbf_data = json.loads(dbf_urls)
            else:
                dbf_data = dbf_urls
                
            if isinstance(dbf_data, dict):
                urls_to_check.extend(dbf_data.values())
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    
    # URL'lerden MEB ID'sini çıkar
    for url in urls_to_check:
        if isinstance(url, str):
            # ÇÖP URL'lerinden: cop9, cop10, cop11, cop12
            cop_match = re.search(r'cop(\d+)', url)
            if cop_match:
                continue  # ÇÖP'te sınıf bilgisi var, MEB ID yok
            
            # DBF URL'lerinden: dbf9, dbf10, dbf11, dbf12
            dbf_match = re.search(r'dbf(\d+)', url)
            if dbf_match:
                continue  # DBF'te sınıf bilgisi var, MEB ID yok
            
            # Genel URL pattern'i: alan_id parameter'i
            alan_id_match = re.search(r'alan_id=(\d+)', url)
            if alan_id_match:
                meb_id = alan_id_match.group(1)
                # 2 haneli format'a çevir
                return f"{int(meb_id):02d}"
            
            # Dosya adından çıkarma: /upload/dbf9/01_adalet.rar
            file_match = re.search(r'/(\d{2})_[^/]+\.(rar|zip|pdf)$', url)
            if file_match:
                return file_match.group(1)
    
    return None

def merge_cop_urls(existing_cop_url, new_cop_url):
    """
    Mevcut ÇÖP URL'leri ile yeni URL'i birleştirir.
    JSON formatında saklar.
    """
    try:
        # Mevcut URL'leri parse et
        if existing_cop_url:
            if existing_cop_url.startswith('{'):
                # Zaten JSON formatında
                existing_urls = json.loads(existing_cop_url)
            else:
                # Eski format (string), JSON'a çevir
                existing_urls = {"default": existing_cop_url}
        else:
            existing_urls = {}
        
        # Yeni URL'i ekle (sınıf bazında unique key oluştur)
        if new_cop_url:
            # URL'den sınıf bilgisini çıkarmaya çalış
            sinif_match = re.search(r'cop(\d+)', new_cop_url)
            if sinif_match:
                sinif = sinif_match.group(1)
                existing_urls[str(sinif)] = new_cop_url
            else:
                # Sınıf bulunamazsa generic key kullan
                existing_urls[f"url_{len(existing_urls) + 1}"] = new_cop_url
        
        return json.dumps(existing_urls)
        
    except Exception as e:
        print(f"ÇÖP URL merge hatası: {e}")
        # Hata durumunda yeni URL'i kullan
        return json.dumps({"default": new_cop_url}) if new_cop_url else "{}"

def get_or_create_alan(cursor, alan_adi, meb_alan_id=None, cop_url=None, dbf_urls=None):
    """
    Alan kaydı bulur veya oluşturur. 
    ÇÖP URL'leri JSON formatında birleştirir.
    Alan adını normalize eder.
    MEB ID yoksa URL'lerden çıkarmaya çalışır.
    """
    # Import normalize_alan_adi from utils
    from .utils_normalize import normalize_to_title_case_tr
    
    normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
    
    cursor.execute("SELECT id, cop_url, meb_alan_id FROM temel_plan_alan WHERE alan_adi = ?", (normalized_alan_adi,))
    result = cursor.fetchone()
    
    if result:
        alan_id, existing_cop_url, existing_meb_alan_id = result
        
        # Mevcut ÇÖP URL'leri ile yeni URL'i birleştir
        updated_cop_urls = existing_cop_url
        if cop_url:
            # Eğer cop_url zaten JSON string ise direkt kullan
            try:
                if cop_url.startswith('{') and cop_url.endswith('}'):
                    json.loads(cop_url)  # Geçerli JSON mu kontrolü
                    updated_cop_urls = cop_url  # Yeni JSON'u direkt kullan
                else:
                    # Tek URL ise merge fonksiyonunu kullan
                    updated_cop_urls = merge_cop_urls(existing_cop_url, cop_url)
            except (json.JSONDecodeError, AttributeError):
                # JSON değilse normal merge işlemi
                updated_cop_urls = merge_cop_urls(existing_cop_url, cop_url)
            
        # MEB Alan ID'sini güncelle (eğer yoksa veya farklıysa)
        updated_meb_alan_id = existing_meb_alan_id
        if meb_alan_id:
            if not updated_meb_alan_id:
                updated_meb_alan_id = meb_alan_id
                print(f"      📝 MEB ID parametre ile eklendi: {alan_adi} -> {meb_alan_id}")
            elif updated_meb_alan_id != meb_alan_id:
                updated_meb_alan_id = meb_alan_id
                print(f"      🔄 MEB ID güncellendi: {alan_adi} -> {existing_meb_alan_id} → {meb_alan_id}")
        
        # Eğer hala MEB ID yoksa, URL'lerden çıkarmaya çalış
        if not updated_meb_alan_id:
            extracted_id = extract_meb_id_from_urls(updated_cop_urls, dbf_urls)
            if extracted_id:
                updated_meb_alan_id = extracted_id
                print(f"      🔍 MEB ID URL'den çıkarıldı: {alan_adi} -> {extracted_id}")
        
        # Sadece verilen parametreleri güncelle (diğerlerini koruyarak)
        update_parts = []
        update_values = []
        
        if cop_url is not None:
            update_parts.append("cop_url = ?")
            update_values.append(updated_cop_urls)
        
        if dbf_urls is not None:
            update_parts.append("dbf_urls = ?")
            dbf_urls_json = json.dumps(dbf_urls)
            update_values.append(dbf_urls_json)
        
        if updated_meb_alan_id is not None:
            update_parts.append("meb_alan_id = ?")
            update_values.append(updated_meb_alan_id)
        
        if update_parts:
            update_query = f"""
                UPDATE temel_plan_alan 
                SET {', '.join(update_parts)}
                WHERE id = ?
            """
            update_values.append(alan_id)
            cursor.execute(update_query, tuple(update_values))
        
        return alan_id
    else:
        # DBF URLs'i JSON string olarak sakla
        dbf_urls_json = json.dumps(dbf_urls) if dbf_urls else None
        
        # ÇÖP URL'ini JSON formatında sakla
        if not cop_url:
            cop_url_json = json.dumps({})
        else:
            # Eğer cop_url zaten JSON string ise direkt kullan
            try:
                # JSON string olup olmadığını kontrol et
                if cop_url.startswith('{') and cop_url.endswith('}'):
                    json.loads(cop_url)  # Geçerli JSON mu kontrolü
                    cop_url_json = cop_url
                else:
                    # Tek URL ise JSON'a çevir
                    cop_url_json = json.dumps({"default": cop_url})
            except (json.JSONDecodeError, AttributeError):
                # JSON değilse tek URL olarak kaydet
                cop_url_json = json.dumps({"default": cop_url})
        
        # MEB ID yoksa URL'lerden çıkarmaya çalış
        if not meb_alan_id:
            extracted_id = extract_meb_id_from_urls(cop_url_json, dbf_urls_json)
            if extracted_id:
                meb_alan_id = extracted_id
                print(f"      🔍 MEB ID URL'den çıkarıldı: {alan_adi} -> {extracted_id}")
        
        cursor.execute("""
            INSERT INTO temel_plan_alan (alan_adi, meb_alan_id, cop_url, dbf_urls) 
            VALUES (?, ?, ?, ?)
        """, (normalized_alan_adi, meb_alan_id, cop_url_json, dbf_urls_json))
        return cursor.lastrowid

# Geriye uyumluluk için eski fonksiyonları yeni fonksiyonlara yönlendiren wrapper'lar
def get_meb_alan_ids_cached():
    """Geriye uyumluluk wrapper'ı - get_meb_alan_ids() kullanın"""
    return get_meb_alan_ids()

def get_meb_alan_id_with_fallback(alan_adi, data_meb_id=None):
    """Geriye uyumluluk wrapper'ı - get_meb_alan_id() kullanın"""
    return get_meb_alan_id(alan_adi, data_meb_id)

def invalidate_meb_alan_ids_cache():
    """Geriye uyumluluk wrapper'ı - get_meb_alan_ids(force_refresh=True) kullanın"""
    get_meb_alan_ids(force_refresh=True)
    return None

def get_cache_info():
    """Geriye uyumluluk wrapper'ı - get_meb_alan_ids(info_only=True) kullanın"""
    return get_meb_alan_ids(info_only=True)

def update_all_meb_alan_ids_from_cache():
    """Geriye uyumluluk wrapper'ı - update_database_from_cache() kullanın"""
    return update_database_from_cache()

def update_all_meb_alan_ids_from_cache_impl(cursor):
    """Geriye uyumluluk wrapper'ı - update_database_from_cache() kullanın"""
    # Bu fonksiyonu doğrudan çağırma, wrapper kullan
    return update_database_from_cache()

def get_folder_name_for_download(alan_adi, meb_alan_id, area_id):
    """
    Dosya klasörü adını belirler:
    - MEB ID varsa: "{meb_alan_id}_{alan_adi}"
    - MEB ID yoksa: "{alan_adi}" (direkt alan adı, ID yok)
    
    Args:
        alan_adi: Alan adı
        meb_alan_id: MEB alan ID'si (opsiyonel)
        area_id: Veritabanı alan ID'si (kullanılmıyor)
    
    Returns:
        str: Klasör adı
    """
    # Import sanitize_filename_tr from utils
    from .utils_normalize import sanitize_filename_tr
    
    if meb_alan_id:
        # MEB ID varsa: 08_Denizcilik formatında
        return f"{meb_alan_id}_{sanitize_filename_tr(alan_adi)}"
    else:
        # MEB ID yoksa: Direkt alan adı (ID yok)
        return sanitize_filename_tr(alan_adi)

# ====== MEB Alan ID Cache Management ======
# Global cache değişkenleri
_meb_alan_ids_cache = None
_cache_timestamp = None
_cache_duration = 3600  # 1 saat cache süresi

def get_meb_alan_ids(force_refresh=False, info_only=False):
    """
    MEB Alan ID'lerini cache ile çeker.
    
    Args:
        force_refresh: Cache'i yenile (varsayılan: False)
        info_only: Sadece cache bilgisi döndür (varsayılan: False)
    
    Returns:
        dict: {alan_adi: meb_alan_id} formatında alan ID'leri
              veya info_only=True ise cache bilgisi
    """
    global _meb_alan_ids_cache, _cache_timestamp
    
    # Sadece cache bilgisi isteniyorsa
    if info_only:
        if _meb_alan_ids_cache is None:
            return {"status": "empty", "count": 0, "age": 0, "remaining": 0}
        
        current_time = time.time()
        age = current_time - _cache_timestamp if _cache_timestamp else 0
        remaining = max(0, _cache_duration - age)
        
        return {
            "status": "active",
            "count": len(_meb_alan_ids_cache),
            "age": age,
            "remaining": remaining,
            "cache_duration": _cache_duration
        }
    
    # Cache temizleme isteniyorsa
    if force_refresh:
        _meb_alan_ids_cache = None
        _cache_timestamp = None
        print("🔄 MEB Alan ID cache'i temizlendi")
    
    current_time = time.time()
    
    # Cache kontrol et
    if (_meb_alan_ids_cache is not None and 
        _cache_timestamp is not None and 
        current_time - _cache_timestamp < _cache_duration):
        
        print(f"📋 MEB Alan ID'leri cache'den alındı ({len(_meb_alan_ids_cache)} alan)")
        return _meb_alan_ids_cache
    
    # Cache yoksa veya süresi dolmuşsa MEB'den çek
    print("📋 MEB Alan ID'leri çekiliyor...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        alan_id_map = {}
        
        # cercevelistele.aspx sayfasından alan dropdown'unu çek
        url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
        params = {"sinif_kodu": "9", "kurum_id": "1"}
        
        response = requests.get(url, params=params, headers=headers, timeout=45)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Select dropdown'daki option'ları bul
        # Örnek: <option value="01">Adalet</option>
        select = soup.find('select', {'name': re.compile(r'.*drpalansec.*')})
        if select:
            options = select.find_all('option')
            for option in options:
                value = option.get('value', '').strip()
                text = option.get_text(strip=True)
                # Boş option'ları ve "Alanlar" başlığını atla
                if value and text and value != '' and text != 'Alanlar' and value != '00':
                    alan_id_map[text] = value
                    print(f"📋 {text} -> MEB ID: {value}")
        
        # Cache'i güncelle
        _meb_alan_ids_cache = alan_id_map
        _cache_timestamp = current_time
        
        print(f"✅ MEB Alan ID'leri cache'lendi ({len(alan_id_map)} alan)")
        
        # Otomatik database güncelleme
        try:
            # Import normalize_alan_adi from utils
            from .utils_normalize import normalize_to_title_case_tr
            
            print("🔄 Otomatik database güncelleme başlatılıyor...")
            db_path = find_or_create_database()
            if db_path:
                with sqlite3.connect(db_path, timeout=30.0) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Sadece eksik olanları güncelle
                    updated_count = 0
                    for alan_adi, meb_alan_id in alan_id_map.items():
                        try:
                            normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
                            
                            # Mevcut MEB ID'yi kontrol et
                            cursor.execute("SELECT meb_alan_id FROM temel_plan_alan WHERE alan_adi = ?", (normalized_alan_adi,))
                            result = cursor.fetchone()
                            
                            if result:
                                existing_meb_id = result['meb_alan_id']
                                if existing_meb_id != meb_alan_id:
                                    # Güncelle
                                    cursor.execute("UPDATE temel_plan_alan SET meb_alan_id = ? WHERE alan_adi = ?", (meb_alan_id, normalized_alan_adi))
                                    updated_count += 1
                                    print(f"🔄 Güncellendi: {alan_adi} -> {meb_alan_id}")
                            else:
                                # Yeni alan oluştur
                                cursor.execute("""
                                    INSERT INTO temel_plan_alan (alan_adi, meb_alan_id, created_at, updated_at) 
                                    VALUES (?, ?, datetime('now'), datetime('now'))
                                """, (normalized_alan_adi, meb_alan_id))
                                updated_count += 1
                                print(f"🆕 Yeni alan: {alan_adi} -> {meb_alan_id}")
                        except Exception as e:
                            print(f"❌ Alan güncelleme hatası ({alan_adi}): {e}")
                            continue
                    
                    if updated_count > 0:
                        print(f"✅ {updated_count} alan database'de güncellendi")
                    else:
                        print("✅ Tüm alanlar zaten güncel")
                        
        except Exception as e:
            print(f"❌ Otomatik database güncelleme hatası: {e}")
        
        return alan_id_map
        
    except Exception as e:
        print(f"❌ MEB Alan ID çekme hatası: {e}")
        
        # Hata durumunda eski cache'i döndür (varsa)
        if _meb_alan_ids_cache is not None:
            print("⚠️ Eski cache kullanılıyor")
            return _meb_alan_ids_cache
        
        return {}

def get_meb_alan_id(alan_adi, data_meb_id=None):
    """
    Tek bir alan için MEB ID'yi bulur.
    
    Strateji:
    1. Verilen data'dan MEB ID'yi kontrol et
    2. Veritabanındaki meb_alan_id'yi kontrol et  
    3. Cache'den MEB ID'leri al ve eşleştir
    4. Hiçbiri yoksa None döndür
    
    Args:
        alan_adi: Alan adı
        data_meb_id: Data'dan gelen MEB ID (opsiyonel)
    
    Returns:
        tuple: (meb_alan_id, source) - source: 'data', 'db', 'cache', 'none'
    """
    # Import normalize_alan_adi from utils
    from .utils_normalize import normalize_to_title_case_tr
    
    # 1. Önce verilen data'dan kontrol et
    if data_meb_id:
        return data_meb_id, 'data'
    
    # 2. Veritabanından kontrol et
    db_path = find_or_create_database()
    if db_path:
        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
                cursor.execute("SELECT meb_alan_id FROM temel_plan_alan WHERE alan_adi = ?", (normalized_alan_adi,))
                result = cursor.fetchone()
                
                if result and result['meb_alan_id']:
                    return result['meb_alan_id'], 'db'
        except Exception as e:
            print(f"DB MEB ID kontrol hatası: {e}")
    
    # 3. Cache'den MEB ID'leri al ve eşleştir
    try:
        meb_alan_ids = get_meb_alan_ids()
        
        # Tam eşleşme ara
        if alan_adi in meb_alan_ids:
            meb_alan_id = meb_alan_ids[alan_adi]
            
            # Veritabanını güncelle
            if db_path:
                try:
                    with sqlite3.connect(db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
                        cursor.execute("""
                            UPDATE temel_plan_alan 
                            SET meb_alan_id = ?, updated_at = datetime('now')
                            WHERE alan_adi = ?
                        """, (meb_alan_id, normalized_alan_adi))
                        print(f"📋 MEB ID güncellendi: {alan_adi} -> {meb_alan_id}")
                except Exception as e:
                    print(f"MEB ID güncelleme hatası: {e}")
            
            return meb_alan_id, 'cache'
        
        # Normalize edilmiş adla ara
        normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
        if normalized_alan_adi in meb_alan_ids:
            meb_alan_id = meb_alan_ids[normalized_alan_adi]
            
            # Veritabanını güncelle
            if db_path:
                try:
                    with sqlite3.connect(db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE temel_plan_alan 
                            SET meb_alan_id = ?, updated_at = datetime('now')
                            WHERE alan_adi = ?
                        """, (meb_alan_id, normalized_alan_adi))
                        print(f"📋 MEB ID güncellendi (normalize): {alan_adi} -> {meb_alan_id}")
                except Exception as e:
                    print(f"MEB ID güncelleme hatası: {e}")
            
            return meb_alan_id, 'cache'
        
        # Protokol alanlar için özel arama
        # "Alan - Protokol" -> "Alan" şeklinde arama yap
        if alan_adi and (" - Protokol" in alan_adi or " - protokol" in alan_adi):
            import re
            base_alan_adi = re.sub(r'\s*-\s*[Pp]rotokol\s*$', '', alan_adi).strip()
            base_alan_adi = normalize_to_title_case_tr(base_alan_adi)
            
            if base_alan_adi in meb_alan_ids:
                meb_alan_id = meb_alan_ids[base_alan_adi]
                print(f"🔗 Protokol alan MEB ID bulundu: {alan_adi} -> {base_alan_adi} -> {meb_alan_id}")
                
                # Veritabanını güncelle (protokol alan adı ile)
                if db_path:
                    try:
                        with sqlite3.connect(db_path, timeout=30.0) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE temel_plan_alan 
                                SET meb_alan_id = ?, updated_at = datetime('now')
                                WHERE alan_adi = ?
                            """, (meb_alan_id, normalized_alan_adi))
                            print(f"📋 Protokol alan MEB ID güncellendi: {alan_adi} -> {meb_alan_id}")
                    except Exception as e:
                        print(f"Protokol alan MEB ID güncelleme hatası: {e}")
                
                return meb_alan_id, 'cache_protokol'
        
    except Exception as e:
        print(f"Cache'den MEB ID çekme hatası: {e}")
    
    # 4. Hiçbiri yoksa None döndür
    return None, 'none'

@with_database
def update_database_from_cache(cursor):
    """
    Cache'deki tüm MEB Alan ID'lerini database'e toplu olarak günceller.
    
    Returns:
        dict: {"updated": int, "skipped": int, "errors": list}
    """
    # Import normalize_alan_adi from utils
    from .utils_normalize import normalize_to_title_case_tr
    
    # Cache'den MEB ID'leri al
    meb_alan_ids = get_meb_alan_ids()
    
    if not meb_alan_ids:
        return {"updated": 0, "skipped": 0, "errors": ["Cache boş veya erişilemiyor"]}
    
    updated_count = 0
    skipped_count = 0
    errors = []
    
    print(f"🔄 {len(meb_alan_ids)} MEB ID'si database'e güncelleniyor...")
    
    for alan_adi, meb_alan_id in meb_alan_ids.items():
        try:
            # Alan adını normalize et
            normalized_alan_adi = normalize_to_title_case_tr(alan_adi.strip()) if alan_adi else "Belirtilmemiş"
            
            # Alanın database'de olup olmadığını kontrol et
            cursor.execute("SELECT id, meb_alan_id FROM temel_plan_alan WHERE alan_adi = ?", (normalized_alan_adi,))
            result = cursor.fetchone()
            
            if result:
                existing_id = result['id']
                existing_meb_id = result['meb_alan_id']
                
                # MEB ID güncelleme gerekiyor mu?
                if existing_meb_id != meb_alan_id:
                    # Güncelle
                    cursor.execute("UPDATE temel_plan_alan SET meb_alan_id = ? WHERE id = ?", (meb_alan_id, existing_id))
                    updated_count += 1
                    
                    if existing_meb_id:
                        print(f"🔄 Güncellendi: {alan_adi} -> {existing_meb_id} → {meb_alan_id}")
                    else:
                        print(f"➕ Eklendi: {alan_adi} -> {meb_alan_id}")
                else:
                    # Zaten doğru MEB ID var
                    skipped_count += 1
                    print(f"✅ Zaten güncel: {alan_adi} -> {meb_alan_id}")
            else:
                # Alan database'de yok, yeni oluştur
                cursor.execute("""
                    INSERT INTO temel_plan_alan (alan_adi, meb_alan_id, created_at, updated_at) 
                    VALUES (?, ?, datetime('now'), datetime('now'))
                """, (normalized_alan_adi, meb_alan_id))
                updated_count += 1
                print(f"🆕 Yeni alan oluşturuldu: {alan_adi} -> {meb_alan_id}")
                
        except Exception as e:
            error_msg = f"Hata ({alan_adi}): {e}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
            continue
    
    print(f"✅ Toplu güncelleme tamamlandı: {updated_count} güncellendi, {skipped_count} atlandı, {len(errors)} hata")
    
    return {
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors
    }

# ====== Ders Management Utilities ======
def create_or_get_ders(cursor, ders_adi, sinif, ders_saati=0, amac='', dm_url='', dbf_url='', bom_url='', cop_url=''):
    """
    Merkezi ders kaydetme fonksiyonu.
    
    ÖNEMLI: Aynı ders adı için farklı sınıflar varsa, sadece en düşük sınıfı saklar.
    Örnek: "Ahilik Kültürü ve Girişimcilik" hem 11 hem 12'de varsa, sadece 11 kaydedilir.
    
    Args:
        cursor: Database cursor
        ders_adi: Ders adı
        sinif: Sınıf seviyesi (9, 10, 11, 12)
        ders_saati: Haftalık ders saati (varsayılan: 0)
        amac: Ders amacı (opsiyonel)
        dm_url: Ders materyali URL'si (opsiyonel)
        dbf_url: DBF dosya URL'si (opsiyonel)
        bom_url: BOM URL'si (opsiyonel)
        cop_url: ÇÖP URL'si (opsiyonel)
        
    Returns:
        int: Ders ID'si
    """
    if not ders_adi or not sinif:
        return None
    
    # Sınıf değerini integer'a çevir
    try:
        sinif = int(sinif)
    except (ValueError, TypeError):
        print(f"❌ Geçersiz sınıf değeri: {sinif}")
        return None
    
    # Ders saati değerini integer'a çevir
    try:
        ders_saati = int(ders_saati) if ders_saati else 0
    except (ValueError, TypeError):
        ders_saati = 0
    
    # Önce aynı ders adı ile mevcut kayıtları kontrol et
    cursor.execute("""
        SELECT id, sinif, ders_saati FROM temel_plan_ders 
        WHERE ders_adi = ?
        ORDER BY sinif ASC
    """, (ders_adi,))
    
    existing_records = cursor.fetchall()
    
    if existing_records:
        # Mevcut kayıtlar var
        existing_lowest_sinif = existing_records[0]['sinif']  # En düşük sınıf
        existing_lowest_id = existing_records[0]['id']
        
        if sinif >= existing_lowest_sinif:
            # Yeni sınıf daha büyük veya eşit, mevcut kaydı kullan
            # Ders saati güncelle (0 ise veya yeni değer daha büyükse)
            if ders_saati > 0:
                cursor.execute("""
                    UPDATE temel_plan_ders 
                    SET ders_saati = ? 
                    WHERE id = ? AND (ders_saati = 0 OR ders_saati < ?)
                """, (ders_saati, existing_lowest_id, ders_saati))
            
            print(f"      ↻ Duplicate ders atlandı: {ders_adi} ({sinif}. sınıf) - Mevcut: {existing_lowest_sinif}. sınıf")
            return existing_lowest_id
        else:
            # Yeni sınıf daha düşük, mevcut kayıtları sil ve yeni kayıt oluştur
            print(f"      ↻ Daha düşük sınıf bulundu: {ders_adi} ({sinif}. sınıf) - Eski kayıtlar siliniyor")
            
            # Mevcut kayıtları sil (cascade'e güvenmek yerine manuel temizlik)
            for existing_record in existing_records:
                existing_id = existing_record['id']
                existing_sinif = existing_record['sinif']
                # İlişkili kayıtları sil
                cursor.execute("DELETE FROM temel_plan_ders_dal WHERE ders_id = ?", (existing_id,))
                cursor.execute("DELETE FROM temel_plan_ders WHERE id = ?", (existing_id,))
                print(f"      ↻ Silindi: {ders_adi} ({existing_sinif}. sınıf)")
    
    # Yeni ders oluştur
    cursor.execute("""
        INSERT INTO temel_plan_ders (
            ders_adi, sinif, ders_saati, amac, dm_url, dbf_url, bom_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        ders_adi,
        sinif,
        ders_saati,
        amac,
        dm_url,
        dbf_url,
        bom_url
    ))
    
    ders_id = cursor.lastrowid
    print(f"      ➕ Yeni ders eklendi: {ders_adi} ({sinif}. sınıf, {ders_saati} saat)")
    return ders_id

def create_ders_dal_relation(cursor, ders_id, dal_id):
    """
    Ders-Dal ilişkisi oluşturur.
    
    Args:
        cursor: Database cursor
        ders_id: Ders ID'si
        dal_id: Dal ID'si
    """
    if not ders_id or not dal_id:
        return False
    
    cursor.execute("""
        INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id, created_at) 
        VALUES (?, ?, datetime('now'))
    """, (ders_id, dal_id))
    
    return True
