import os
import requests
import sqlite3
import functools
from typing import Optional, Callable
import json
import re

def download_and_cache_pdf(url: str, cache_type: str, alan_adi: str = None, additional_info: str = None, alan_id: str = None, alan_db_id: int = None, meb_alan_id: str = None) -> Optional[str]:
    """
    PDF'yi indirir ve organize şekilde cache'ler.
    
    Args:
        url: PDF URL'si
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
        alan_adi: Alan adı (klasör adı için)
        additional_info: Ek bilgi (sınıf, dal vb.)
        alan_id: Alan ID'si (organizasyon için, opsiyonel)
        alan_db_id: Veritabanı alan ID'si (klasör yapısı için)
        meb_alan_id: MEB alan ID'si (02, 08 gibi - klasör yapısı için)
    
    Returns:
        İndirilen dosyanın yolu veya None
    """
    if not url or not cache_type:
        return None
    
    try:
        # Alan adı yoksa, URL'den bir parça alarak geçici bir isim oluştur
        if not alan_adi:
            safe_alan_adi = url.split('/')[-2] if len(url.split('/')) > 1 else "bilinmeyen_alan"
        else:
            # Merkezi sanitize fonksiyonunu kullan
            safe_alan_adi = sanitize_filename_tr(alan_adi)
        
        # Klasör yapısı belirleme
        if meb_alan_id and cache_type in ['cop', 'dbf', 'dm', 'bom']:
            # MEB ID bazlı organizasyon: {meb_alan_id}_{alan_adi}
            folder_name = f"{meb_alan_id}_{safe_alan_adi}"
        elif alan_db_id and cache_type in ['cop', 'dbf', 'dm', 'bom']:
            # DB ID bazlı organizasyon: {ID:02d}_{alan_adi}
            folder_name = f"{int(alan_db_id):02d}_{safe_alan_adi}"
        else:
            # Eski format: {alan_adi}
            folder_name = safe_alan_adi
            
        cache_dir = os.path.join("data", cache_type, folder_name)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Dosya adını URL'den çıkar
        filename = url.split('/')[-1]
        if not filename.lower().endswith(('.pdf', '.rar', '.zip')):
            filename += '.pdf' # Varsayılan
        
        # Ek bilgi varsa dosya adına ekle
        if additional_info:
            name_part, ext = os.path.splitext(filename)
            filename = f"{name_part}_{additional_info}{ext}"
        
        file_path = os.path.join(cache_dir, filename)
        
        # Dosya zaten varsa indirme
        if os.path.exists(file_path):
            print(f"📁 Cache'den alınıyor: {file_path}")
            return file_path
        
        # PDF'yi indir
        print(f"⬇️ İndiriliyor: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Kaydedildi: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ Dosya indirme hatası ({url}): {e}")
        return None


def sanitize_filename_tr(name: str) -> str:
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir.
    Türkçe karakterleri normalize eder ve dosya sistemi uyumlu yapar.
    
    Args:
        name: Normalize edilecek dosya/klasör adı
        
    Returns:
        Güvenli dosya/klasör adı
    """
    if not name:
        return "bilinmeyen_alan"
    
    # Normalize alan adı (klasör adı için)
    safe_name = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Türkçe karakterleri düzelt
    safe_name = safe_name.replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    safe_name = safe_name.replace('Ç', 'C').replace('Ğ', 'G').replace('İ', 'I').replace('Ö', 'O').replace('Ş', 'S').replace('Ü', 'U')
    
    return safe_name


def get_temp_pdf_path(url: str) -> str:
    """
    Geçici PDF dosyası için güvenli yol oluştur
    """
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"temp_pdf_{url_hash}.pdf"


def normalize_to_title_case_tr(name: str) -> str:
    """
    Bir metni, Türkçe karakterleri ve dil kurallarını dikkate alarak
    "Başlık Biçimine" (Title Case) dönüştürür.

    Örnekler:
    - "BİLİŞİM TEKNOLOJİLERİ" -> "Bilişim Teknolojileri"
    - "gıda ve içecek hizmetleri" -> "Gıda ve İçecek Hizmetleri"
    - "ELEKTRİK-ELEKTRONİK TEKNOLOJİSİ" -> "Elektrik-Elektronik Teknolojisi"
    - "elektrik-elektronik teknolojisi" -> "Elektrik-Elektronik Teknolojisi"

    Args:
        name: Standartlaştırılacak metin.

    Returns:
        Başlık biçimine dönüştürülmüş metin.
    """
    if not name:
        return ""

    # Tireyi geçici olarak özel karakter ile değiştir (tire öncesi/sonrası boşlukları da temizle)
    name = name.replace(' - ', '-').replace('- ', '-').replace(' -', '-')
    name = name.replace('-', ' __tire__ ')
    
    # Metni temizle: baştaki/sondaki boşluklar, çoklu boşlukları tek boşluğa indirge
    # ve tamamını küçük harfe çevirerek başla.
    # Türkçe'ye özgü 'İ' -> 'i' ve 'I' -> 'ı' dönüşümü için replace kullanılır.
    cleaned_name = ' '.join(name.strip().split()).replace('İ', 'i').replace('I', 'ı').lower()

    # Bağlaçlar gibi küçük kalması gereken kelimeler.
    lowercase_words = ["ve", "ile", "için", "de", "da", "ki"]

    words = cleaned_name.split(' ')
    final_words = []

    for word in words:
        if not word:
            continue

        if word == '__tire__':
            # Tire durumunda bir önceki kelime ile birleştir
            if final_words:
                final_words[-1] += '-'
            continue  # Bu kelimeyi atlayıp sonraki kelimeyi bekle
        elif word in lowercase_words and len(final_words) > 0:  # İlk kelime asla küçük olmasın
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += word
            else:
                final_words.append(word)
        else:
            capitalized = 'İ' + word[1:] if word.startswith('i') else word.capitalize()
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += capitalized
            else:
                final_words.append(capitalized)

    return ' '.join(final_words)

def normalize_alan_adi(alan_adi):
    """
    Alan adını normalize eder - büyük/küçük harf sorununu çözer.
    """
    if not alan_adi:
        return "Belirtilmemiş"
    
    # Normalize edilmiş alan adı: İlk harf büyük, geri kalan kelimeler ilk harfi büyük
    normalized = alan_adi.strip()
    
    # Yaygın normalizations
    replacements = {
        'AİLE VE TÜKETİCİ HİZMETLERİ': 'Aile ve Tüketici Hizmetleri',
        'ADALET': 'Adalet',
        'BİLİŞİM TEKNOLOJİLERİ': 'Bilişim Teknolojileri',
        'METAL TEKNOLOJİSİ': 'Metal Teknolojisi',
        'ELEKTRİK ELEKTRONİK TEKNOLOJİSİ': 'Elektrik Elektronik Teknolojisi',
        'MAKİNE TEKNOLOJİSİ': 'Makine Teknolojisi',
        'İNŞAAT TEKNOLOJİSİ': 'İnşaat Teknolojisi',
        'ULAŞTIRMA': 'Ulaştırma',
        'ENERJİ': 'Enerji',
        'ÇEVRE': 'Çevre',
        'TARIM': 'Tarım',
        'HAYVANCILIK': 'Hayvancılık',
        'GIDA': 'Gıda',
        'TEKSTİL GİYİM AYAKKABI': 'Tekstil Giyim Ayakkabı',
        'KIMYA': 'Kimya',
        'CAM SERAMIK': 'Cam Seramik',
        'AĞAÇ': 'Ağaç',
        'KAĞIT MATBAA': 'Kağıt Matbaa',
        'DERİ': 'Deri',
        'FİNANS SİGORTACILIK': 'Finans Sigortacılık',
        'PAZARLAMA VE SATIŞ': 'Pazarlama ve Satış',
        'LOJİSTİK': 'Lojistik',
        'TURİZM': 'Turizm',
        'SPOR': 'Spor',
        'SANAT VE TASARIM': 'Sanat ve Tasarım',
        'İLETİŞİM': 'İletişim',
        'DİN HİZMETLERİ': 'Din Hizmetleri'
    }
    
    # Önce exact match kontrol et
    if normalized.upper() in replacements:
        return replacements[normalized.upper()]
    
    # Manuel replacement yoksa, normalize_to_title_case_tr kullan
    return normalize_to_title_case_tr(normalized)

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


def get_or_create_alan(cursor, alan_adi, meb_alan_id=None, cop_url=None, dbf_urls=None):
    """
    Alan kaydı bulur veya oluşturur. 
    ÇÖP URL'leri JSON formatında birleştirir.
    Alan adını normalize eder.
    MEB ID yoksa URL'lerden çıkarmaya çalışır.
    """
    normalized_alan_adi = normalize_alan_adi(alan_adi)
    
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
            
        # MEB Alan ID'sini güncelle (eğer yoksa)
        updated_meb_alan_id = existing_meb_alan_id or meb_alan_id
        
        # Eğer hala MEB ID yoksa, URL'lerden çıkarmaya çalış
        if not updated_meb_alan_id:
            extracted_id = extract_meb_id_from_urls(updated_cop_urls, dbf_urls)
            if extracted_id:
                updated_meb_alan_id = extracted_id
                print(f"      🔍 MEB ID URL'den çıkarıldı: {alan_adi} -> {extracted_id}")
        
        cursor.execute("""
            UPDATE temel_plan_alan 
            SET cop_url = ?, meb_alan_id = ?
            WHERE id = ?
        """, (updated_cop_urls, updated_meb_alan_id, alan_id))
        
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

# ====== Database Connection Utilities ======

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
                with sqlite3.connect(db_path) as conn:
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        conn.executescript(f.read())
                print(f"✅ Database initialized: {db_path}")
            else:
                # Boş database oluştur
                sqlite3.connect(db_path).close()
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
            with sqlite3.connect(db_path) as conn:
                # Row factory ile dict-style access
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # İlk parametre olarak cursor'ı geç
                return func(cursor, *args, **kwargs)
                
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
            with sqlite3.connect(db_path) as conn:
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


# ====== Archive Extraction Utilities ======

def extract_archive(archive_path, extract_dir):
    """
    RAR veya ZIP dosyasını açar. Dosya tipini otomatik algılar.
    Merkezi arşiv açma fonksiyonu.
    
    Args:
        archive_path: Açılacak arşiv dosyasının yolu
        extract_dir: Dosyaların çıkarılacağı dizin
        
    Raises:
        Exception: Arşiv açılamadığında hata fırlatır
    """
    import rarfile
    import zipfile
    
    try:
        with open(archive_path, "rb") as f:
            magic = f.read(4)
        
        is_rar = magic == b"Rar!"
        is_zip = magic == b"PK\x03\x04"
        
        if is_rar:
            with rarfile.RarFile(archive_path) as rf:
                rf.extractall(extract_dir)
        elif is_zip:
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_dir)
        else:
            raise Exception(f"Desteklenmeyen dosya formatı (magic: {magic})")
    except Exception as e:
        raise Exception(f"Arşiv açılırken hata: {e}")


def scan_directory_for_archives(root_dir, file_extensions=('.rar', '.zip')):
    """
    Belirtilen dizinde arşiv dosyalarını tarar.
    
    Args:
        root_dir: Taranacak ana dizin
        file_extensions: Aranacak dosya uzantıları
        
    Returns:
        List[Dict]: Bulunan arşiv dosyaları listesi
        Format: [{"path": "dosya_yolu", "name": "dosya_adi", "dir": "klasor_adi"}]
    """
    archives = []
    
    if not os.path.exists(root_dir):
        return archives
    
    for item in os.listdir(root_dir):
        item_path = os.path.join(root_dir, item)
        if not os.path.isdir(item_path):
            continue
        
        for fname in os.listdir(item_path):
            if fname.lower().endswith(file_extensions):
                archive_path = os.path.join(item_path, fname)
                archives.append({
                    "path": archive_path,
                    "name": fname,
                    "dir": item
                })
    
    return archives


def scan_directory_for_pdfs(root_dir, file_extensions=('.pdf', '.docx')):
    """
    Belirtilen dizinde PDF/DOCX dosyalarını tarar.
    
    Args:
        root_dir: Taranacak ana dizin  
        file_extensions: Aranacak dosya uzantıları
        
    Returns:
        List[Dict]: Bulunan PDF dosyaları listesi
        Format: [{"path": "dosya_yolu", "name": "dosya_adi", "relative_path": "relative_yol"}]
    """
    pdfs = []
    
    if not os.path.exists(root_dir):
        return pdfs
    
    # Recursive search
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(file_extensions):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                
                pdfs.append({
                    "path": file_path,
                    "name": file,
                    "relative_path": relative_path
                })
    
    return pdfs
