from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import json
import time
import os
import requests
import subprocess
import io
import sys
import sqlite3
from contextlib import redirect_stdout, redirect_stderr

# artık alanlar_ve_dersler3.py kullanmıyoruz, getir_* modülleri kullanıyoruz

# oku.py'den fonksiyonları import ediyoruz
from oku import oku

# Yeni modülleri import et
from getir_dbf import getir_dbf
from getir_cop import getir_cop
from getir_dm import getir_dm
from getir_bom import getir_bom

app = Flask(__name__)
# CORS'u etkinleştirerek localhost:3000 gibi farklı bir porttan gelen
# istekleri kabul etmesini sağlıyoruz.
CORS(app)

CACHE_FILE = "data/scraped_data.json"
CACHE_FILE_DBF = "data/scraped_data_with_dbf.json"

@app.route('/api/get-cached-data')
def get_cached_data():
    """
    Önbelleğe alınmış veri dosyasını okur ve içeriğini JSON olarak döndürür.
    scraped_data_with_dbf.json varsa onu, yoksa scraped_data.json'u döndürür.
    """
    if os.path.exists(CACHE_FILE_DBF):
        try:
            with open(CACHE_FILE_DBF, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except (IOError, json.JSONDecodeError):
            return jsonify({"error": "Cache file is corrupted (with dbf)"}), 500
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except (IOError, json.JSONDecodeError):
            return jsonify({"error": "Cache file is corrupted"}), 500
    return jsonify({}) # Dosya yoksa boş nesne döndür

@app.route('/api/scrape-stream')
def scrape_stream():
    """
    Veri çekme işlemini başlatır ve sonuçları Server-Sent Events (SSE)
    protokolü üzerinden anlık olarak istemciye gönderir.
    """
    def generate():
        # scrape_data bir generator olduğu için, her yield edilen veriyi alıp
        # SSE formatına uygun şekilde istemciye gönderiyoruz.
        for data_chunk in scrape_data():
            # Format: "data: <json_verisi>\n\n"
            yield f"data: {json.dumps(data_chunk)}\n\n"
            time.sleep(0.05) # İstemcinin veriyi işlemesi için küçük bir bekleme

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    """
    PDF dosyasını işler ve sonuçları SSE ile istemciye gönderir.
    """
    data = request.get_json()
    pdf_url = data.get('pdf_url')
    
    if not pdf_url:
        return jsonify({"error": "PDF URL is required"}), 400
    
    def generate():
        try:
            # PDF'yi geçici olarak indir
            yield f"data: {json.dumps({'type': 'status', 'message': 'PDF indiriliyor...'})}\n\n"
            
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Geçici dosya oluştur
            temp_filename = f"temp_{int(time.time())}.pdf"
            with open(temp_filename, 'wb') as f:
                f.write(response.content)
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'PDF işleniyor...'})}\n\n"
            
            # Çıktıyı yakalamak için StringIO kullan
            output_buffer = io.StringIO()
            
            try:
                # stdout'u yakalayarak oku() fonksiyonunun çıktısını al
                with redirect_stdout(output_buffer):
                    result = oku(temp_filename)
                
                # Yakalanan çıktıyı satır satır gönder
                output_lines = output_buffer.getvalue().split('\n')
                for line in output_lines:
                    if line.strip():
                        yield f"data: {json.dumps({'type': 'output', 'message': line})}\n\n"
                        time.sleep(0.1)  # UI'nin güncellenebilmesi için küçük gecikme
                
                # Son olarak JSON sonucunu gönder
                yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'message': 'İşlem tamamlandı!'})}\n\n"
                
            finally:
                # Geçici dosyayı sil
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                    
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Hata: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

# DBF rar dosyalarını indirip açan ve ilerleme mesajı gönderen yeni endpoint
@app.route('/api/dbf-download-extract')
def api_dbf_download_extract():
    """
    DBF rar dosyalarını indirir, açar ve adım adım ilerleme mesajı gönderir (SSE).
    """
    from getir_dbf_unrar import get_dbf_links, download_and_extract_dbf_with_progress

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': 'DBF linkleri toplanıyor...'})}\n\n"
        dbf_data = get_dbf_links()
        yield f"data: {json.dumps({'type': 'status', 'message': 'İndirme ve açma işlemi başlıyor...'})}\n\n"
        for msg in download_and_extract_dbf_with_progress(dbf_data):
            yield f"data: {json.dumps(msg)}\n\n"
            time.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done', 'message': 'Tüm işlemler tamamlandı.'})}\n\n"

        # DBF eşleştirme scriptini otomatik çalıştır
        import subprocess
        try:
            subprocess.Popen(["python", "dbf_bom_eslestir.py"])
        except Exception as e:
            print("dbf_bom_eslestir.py otomatik çalıştırılamadı:", e)

    return Response(generate(), mimetype='text/event-stream')

# Tüm indirilen DBF dosyalarını tekrar açmak için endpoint
@app.route('/api/dbf-retry-extract-all')
def api_dbf_retry_extract_all():
    """
    dbf/ altındaki tüm alan klasörlerindeki .rar ve .zip dosyalarını tekrar açar (SSE).
    """
    from getir_dbf_unrar import retry_extract_all_files_with_progress

    def generate():
        for msg in retry_extract_all_files_with_progress():
            yield f"data: {json.dumps(msg)}\n\n"
            time.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done', 'message': 'Tüm indirilen dosyalar için tekrar açma işlemi tamamlandı.'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

# Belirli bir DBF dosyasını tekrar açmak için endpoint
@app.route('/api/dbf-retry-extract', methods=['POST'])
def api_dbf_retry_extract():
    """
    Belirli bir DBF dosyasını tekrar açar (hem rar hem zip destekler).
    """
    data = request.get_json()
    alan_adi = data.get("alan_adi")
    rar_filename = data.get("rar_filename")
    if not alan_adi or not rar_filename:
        return jsonify({"type": "error", "message": "alan_adi ve rar_filename zorunlu"}), 400
    from getir_dbf_unrar import retry_extract_file
    result = retry_extract_file(alan_adi, rar_filename)
    return jsonify(result)

# DBF eşleştirme işlemini manuel tetikleyen endpoint
@app.route('/api/dbf-match-refresh', methods=['POST'])
def api_dbf_match_refresh():
    """
    DBF ve BOM eşleştirme scriptini (dbf_bom_eslestir.py) çalıştırır.
    """
    import subprocess
    try:
        result = subprocess.run(["python", "dbf_bom_eslestir.py"], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return jsonify({"type": "done", "message": "Eşleştirme işlemi başarıyla tamamlandı."})
        else:
            return jsonify({"type": "error", "message": f"Eşleştirme hatası: {result.stderr}"}), 500
    except Exception as e:
        return jsonify({"type": "error", "message": f"Eşleştirme başlatılamadı: {e}"}), 500

# Yeni API endpointleri
@app.route('/api/get-dbf')
def api_get_dbf():
    """
    DBF (Ders Bilgi Formu) verilerini çeker ve veritabanına kaydeder.
    """
    try:
        result = getir_dbf()
        
        # Veritabanına kaydet
        db_path = find_or_create_database()
        if db_path:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                updated_count = save_dbf_data_to_db(cursor, result)
                conn.commit()
                
            return jsonify({
                "data": result,
                "message": f"{updated_count} alan DBF bilgisi güncellendi",
                "updated_count": updated_count
            })
        else:
            return jsonify({"data": result, "message": "Veritabanına kaydedilemedi"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-cop')
def api_get_cop():
    """
    ÇÖP (Çerçeve Öğretim Programı) verilerini çeker ve veritabanına kaydeder.
    """
    try:
        result = getir_cop()
        
        # Veritabanına kaydet
        db_path = find_or_create_database()
        if db_path:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                updated_count = save_cop_data_to_db(cursor, result)
                conn.commit()
                
            return jsonify({
                "data": result,
                "message": f"{updated_count} alan ÇÖP bilgisi güncellendi",
                "updated_count": updated_count
            })
        else:
            return jsonify({"data": result, "message": "Veritabanına kaydedilemedi"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-dm')
def api_get_dm():
    """
    Ders Materyali (PDF) verilerini çeker ve veritabanına kaydeder.
    """
    try:
        result = getir_dm()
        
        # Veritabanına kaydet
        db_path = find_or_create_database()
        if db_path:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                saved_count = save_dm_data_to_db(cursor, result)
                conn.commit()
                
            return jsonify({
                "data": result,
                "message": f"{saved_count} ders kaydedildi",
                "saved_count": saved_count
            })
        else:
            return jsonify({"data": result, "message": "Veritabanına kaydedilemedi"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-bom')
def api_get_bom():
    """
    Bireysel Öğrenme Materyali (BÖM) verilerini çeker ve veritabanına kaydeder.
    """
    try:
        result = getir_bom()
        
        # Veritabanına kaydet
        db_path = find_or_create_database()
        if db_path:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                updated_count = save_bom_data_to_db(cursor, result)
                conn.commit()
                
            return jsonify({
                "data": result,
                "message": f"{updated_count} ders BOM bilgisi güncellendi",
                "updated_count": updated_count
            })
        else:
            return jsonify({"data": result, "message": "Veritabanına kaydedilemedi"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scrape-to-db')
def scrape_to_db():
    """
    Tüm veri kaynaklarını (DM, DBF, COP, BOM) çekip veritabanına kaydeder.
    """
    def generate():
        try:
            # Veritabanını bul/oluştur
            db_path = find_or_create_database()
            if not db_path:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Veritabanı bulunamadı veya oluşturulamadı'})}\n\n"
                return
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                total_saved = 0
                
                # 1. Ders Materyali verilerini çek ve kaydet
                yield f"data: {json.dumps({'type': 'status', 'message': '1/4: Ders Materyali (DM) verileri çekiliyor...'})}\n\n"
                dm_data = getir_dm()
                dm_saved = save_dm_data_to_db(cursor, dm_data)
                total_saved += dm_saved
                yield f"data: {json.dumps({'type': 'status', 'message': f'DM: {dm_saved} ders kaydedildi'})}\n\n"
                
                # 2. DBF verilerini çek ve kaydet
                yield f"data: {json.dumps({'type': 'status', 'message': '2/4: DBF verileri çekiliyor...'})}\n\n"
                dbf_data = getir_dbf()
                dbf_saved = save_dbf_data_to_db(cursor, dbf_data)
                yield f"data: {json.dumps({'type': 'status', 'message': f'DBF: {dbf_saved} alan güncellendi'})}\n\n"
                
                # 3. ÇÖP verilerini çek ve kaydet
                yield f"data: {json.dumps({'type': 'status', 'message': '3/4: ÇÖP verileri çekiliyor...'})}\n\n"
                cop_data = getir_cop()
                cop_saved = save_cop_data_to_db(cursor, cop_data)
                yield f"data: {json.dumps({'type': 'status', 'message': f'ÇÖP: {cop_saved} alan güncellendi'})}\n\n"
                
                # 4. BOM verilerini çek ve kaydet
                yield f"data: {json.dumps({'type': 'status', 'message': '4/4: BOM verileri çekiliyor...'})}\n\n"
                bom_data = getir_bom()
                bom_saved = save_bom_data_to_db(cursor, bom_data)
                yield f"data: {json.dumps({'type': 'status', 'message': f'BOM: {bom_saved} ders güncellendi'})}\n\n"
                
                conn.commit()
                yield f"data: {json.dumps({'type': 'done', 'message': f'Toplam {total_saved} ders veritabanına kaydedildi!'})}\n\n"
                        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Hata: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/save-courses-to-db', methods=['POST'])
def save_courses_to_db():
    """
    Düzenlenmiş ders verilerini temel_plan_* tablolarına kaydeder.
    """
    try:
        data = request.get_json()
        if not data or 'courses' not in data:
            return jsonify({"error": "Geçersiz veri formatı"}), 400
        
        courses = data['courses']
        if not courses:
            return jsonify({"error": "Kaydedilecek ders bulunamadı"}), 400
            
        # SQLite veritabanını bul/oluştur
        db_path = find_or_create_database()
        if not db_path:
            return jsonify({"error": "Veritabanı bulunamadı veya oluşturulamadı"}), 500
            
        results = []
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for course in courses:
                try:
                    result = save_single_course(cursor, course)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "course": course.get('ders_adi', 'Bilinmeyen'),
                        "status": "error",
                        "message": str(e)
                    })
            
            conn.commit()
        
        # Başarı raporu
        success_count = len([r for r in results if r.get('status') == 'success'])
        error_count = len(results) - success_count
        
        return jsonify({
            "message": f"{success_count} ders başarıyla kaydedildi, {error_count} hatada oluştu",
            "results": results,
            "total": len(results),
            "success": success_count,
            "errors": error_count
        })
        
    except Exception as e:
        return jsonify({"error": f"Veritabanı hatası: {str(e)}"}), 500

def find_or_create_database():
    """
    Veritabanını bulur veya oluşturur.
    """
    # Olası veritabanı dosya yolları
    possible_paths = [
        "database.db",
        "data/database.db", 
        "temel_plan.db",
        "data/temel_plan.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Hiçbiri yoksa varsayılan yolu oluştur
    os.makedirs("data", exist_ok=True)
    return "data/temel_plan.db"

def save_single_course(cursor, course):
    """
    Tek bir dersi veritabanına kaydeder.
    """
    try:
        # 1. Alan kaydı/bulma
        alan_id = get_or_create_alan(
            cursor, 
            course.get('alan_adi', ''),
            course.get('meb_alan_id'),
            course.get('cop_url'),
            course.get('dbf_urls')
        )
        
        # 2. Dal kaydı/bulma (varsa)
        dal_id = None
        if course.get('dal_adi'):
            dal_id = get_or_create_dal(cursor, course.get('dal_adi', ''), alan_id)
        
        # 3. Ders kaydı
        ders_id = create_ders(cursor, course)
        
        # 4. Ders-Dal ilişkisi (varsa)
        if dal_id:
            create_ders_dal_relation(cursor, ders_id, dal_id)
        
        # 5. Ders amaçları kayıtları
        for amac in course.get('ders_amaclari', []):
            if amac.strip():
                create_ders_amac(cursor, ders_id, amac)
        
        # 6. Araç-gereç kayıtları
        for arac in course.get('arac_gerec', []):
            arac_id = get_or_create_arac(cursor, arac)
            create_ders_arac_relation(cursor, ders_id, arac_id)
        
        # 7. Ölçme-değerlendirme kayıtları
        for olcme in course.get('olcme_degerlendirme', []):
            olcme_id = get_or_create_olcme(cursor, olcme)
            create_ders_olcme_relation(cursor, ders_id, olcme_id)
        
        # 8. Öğrenme birimleri (üniteler) kayıtları
        for unit in course.get('ogrenme_birimleri', []):
            if unit.get('ogrenme_birimi', '').strip():
                unit_id = create_ogrenme_birimi(cursor, ders_id, unit)
                
                # 8.1. Konular kayıtları
                for konu_data in unit.get('konular', []):
                    if konu_data.get('konu', '').strip():
                        konu_id = create_konu(cursor, unit_id, konu_data['konu'])
                        
                        # 8.2. Kazanımlar kayıtları
                        for kazanim in konu_data.get('kazanimlar', []):
                            if kazanim.strip():
                                create_kazanim(cursor, konu_id, kazanim)
        
        return {
            "course": course.get('ders_adi', 'Bilinmeyen'),
            "status": "success",
            "ders_id": ders_id,
            "message": "Başarıyla kaydedildi"
        }
        
    except Exception as e:
        raise Exception(f"Ders kaydı hatası: {str(e)}")

def get_or_create_alan(cursor, alan_adi, meb_alan_id=None, cop_url=None, dbf_urls=None):
    """Alan kaydı bulur veya oluşturur."""
    if not alan_adi:
        alan_adi = "Belirtilmemiş"
    
    cursor.execute("SELECT id FROM temel_plan_alan WHERE alan_adi = ?", (alan_adi,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        # DBF URLs'i JSON string olarak sakla
        dbf_urls_json = json.dumps(dbf_urls) if dbf_urls else None
        cursor.execute("""
            INSERT INTO temel_plan_alan (alan_adi, meb_alan_id, cop_url, dbf_urls) 
            VALUES (?, ?, ?, ?)
        """, (alan_adi, meb_alan_id, cop_url, dbf_urls_json))
        return cursor.lastrowid

def get_or_create_dal(cursor, dal_adi, alan_id):
    """Dal kaydı bulur veya oluşturur."""
    cursor.execute("SELECT id FROM temel_plan_dal WHERE dal_adi = ?", (dal_adi,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO temel_plan_dal (dal_adi, alan_id) VALUES (?, ?)", (dal_adi, alan_id))
        return cursor.lastrowid

def create_ders(cursor, course):
    """Ders kaydı oluşturur."""
    cursor.execute("""
        INSERT INTO temel_plan_ders (
            ders_adi, sinif, ders_saati, amac, dm_url, dbf_url, bom_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        course.get('ders_adi', ''),
        int(course.get('sinif', 0)) if course.get('sinif') else None,
        int(course.get('haftalik_ders_saati', 0)) if course.get('haftalik_ders_saati') else None,
        course.get('amaç', ''),
        course.get('dm_url', ''),  # Ders Materyali URL'si
        course.get('dbf_url', ''), # DBF PDF URL'si (yerel path)
        course.get('bom_url', '')  # BOM URL'si
    ))
    return cursor.lastrowid

def create_ders_dal_relation(cursor, ders_id, dal_id):
    """Ders-Dal ilişkisi oluşturur."""
    cursor.execute("""
        INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) VALUES (?, ?)
    """, (ders_id, dal_id))

def get_or_create_arac(cursor, arac_gerec):
    """Araç-gereç kaydı bulur veya oluşturur."""
    cursor.execute("SELECT id FROM temel_plan_arac WHERE arac_gerec = ?", (arac_gerec,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO temel_plan_arac (arac_gerec) VALUES (?)", (arac_gerec,))
        return cursor.lastrowid

def create_ders_arac_relation(cursor, ders_id, arac_id):
    """Ders-Araç ilişkisi oluşturur."""
    cursor.execute("""
        INSERT OR IGNORE INTO temel_plan_ders_arac (ders_id, arac_id) VALUES (?, ?)
    """, (ders_id, arac_id))

def get_or_create_olcme(cursor, olcme_degerlendirme):
    """Ölçme-değerlendirme kaydı bulur veya oluşturur."""
    cursor.execute("SELECT id FROM temel_plan_olcme WHERE olcme_degerlendirme = ?", (olcme_degerlendirme,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        cursor.execute("INSERT INTO temel_plan_olcme (olcme_degerlendirme) VALUES (?)", (olcme_degerlendirme,))
        return cursor.lastrowid

def create_ders_olcme_relation(cursor, ders_id, olcme_id):
    """Ders-Ölçme ilişkisi oluşturur."""
    cursor.execute("""
        INSERT OR IGNORE INTO temel_plan_ders_olcme (ders_id, olcme_id) VALUES (?, ?)
    """, (ders_id, olcme_id))

def create_ders_amac(cursor, ders_id, amac):
    """Ders amacı oluşturur."""
    cursor.execute("""
        INSERT INTO temel_plan_ders_amac (ders_id, amac) VALUES (?, ?)
    """, (ders_id, amac))

def create_ogrenme_birimi(cursor, ders_id, unit):
    """Öğrenme birimi oluşturur."""
    cursor.execute("""
        INSERT INTO temel_plan_ders_ogrenme_birimi (ders_id, ogrenme_birimi, ders_saati) VALUES (?, ?, ?)
    """, (
        ders_id, 
        unit.get('ogrenme_birimi', ''),
        int(unit.get('ders_saati', 0)) if unit.get('ders_saati') else None
    ))
    return cursor.lastrowid

def create_konu(cursor, ogrenme_birimi_id, konu):
    """Konu oluşturur."""
    cursor.execute("""
        INSERT INTO temel_plan_ders_ob_konu (ogrenme_birimi_id, konu) VALUES (?, ?)
    """, (ogrenme_birimi_id, konu))
    return cursor.lastrowid

def create_kazanim(cursor, konu_id, kazanim):
    """Kazanım oluşturur."""
    cursor.execute("""
        INSERT INTO temel_plan_ders_ob_konu_kazanim (konu_id, kazanim) VALUES (?, ?)
    """, (konu_id, kazanim))

def save_dm_data_to_db(cursor, dm_data):
    """Ders Materyali verilerini veritabanına kaydeder."""
    saved_count = 0
    
    if not dm_data:
        return saved_count
    
    # Yeni DM veri formatı: {sinif: {alan_adi: [ders_listesi]}}
    for sinif, sinif_data in dm_data.items():
        for alan_adi, ders_listesi in sinif_data.items():
            try:
                # Alan kaydet/güncelle (meb_alan_id yok bu yapıda)
                alan_id = get_or_create_alan(cursor, alan_adi, None)
                
                # Her ders için
                for ders_data in ders_listesi:
                    ders_adi = ders_data.get('isim', '')
                    dm_url = ders_data.get('link', '')
                    ders_sinif = ders_data.get('sinif', sinif)
                    
                    if ders_adi and dm_url:
                        # Sınıf bilgisini temizle (sadece rakam al)
                        sinif_no = ders_sinif.replace('.Sınıf', '').replace('Sınıf', '').strip()
                        
                        course_data = {
                            'ders_adi': ders_adi,
                            'sinif': sinif_no,
                            'alan_adi': alan_adi,
                            'dm_url': dm_url
                        }
                        
                        try:
                            save_single_course(cursor, course_data)
                            saved_count += 1
                        except Exception as e:
                            print(f"DM Ders kaydı hatası: {ders_adi} - {str(e)}")
                        
            except Exception as e:
                print(f"DM Alan kaydı hatası: {alan_adi} - {str(e)}")
    
    return saved_count

def save_dbf_data_to_db(cursor, dbf_data):
    """DBF verilerini veritabanına kaydeder."""
    updated_count = 0
    
    if not dbf_data:
        return updated_count
    
    for sinif, sinif_data in dbf_data.items():
        for alan_adi, alan_info in sinif_data.items():
            try:
                # Alanı bul ve DBF URL'lerini güncelle
                cursor.execute("SELECT id, dbf_urls FROM temel_plan_alan WHERE alan_adi = ?", (alan_adi,))
                result = cursor.fetchone()
                
                if result:
                    alan_id, existing_dbf_urls = result
                    # Mevcut DBF URLs'i JSON olarak parse et
                    current_urls = json.loads(existing_dbf_urls) if existing_dbf_urls else {}
                    # Yeni sınıf bilgisini ekle
                    current_urls[sinif] = alan_info.get('link', '')
                    
                    # Güncelle
                    cursor.execute("""
                        UPDATE temel_plan_alan 
                        SET dbf_urls = ? 
                        WHERE id = ?
                    """, (json.dumps(current_urls), alan_id))
                    updated_count += 1
                    
            except Exception as e:
                print(f"DBF güncelleme hatası: {alan_adi} - {str(e)}")
    
    return updated_count

def save_cop_data_to_db(cursor, cop_data):
    """ÇÖP verilerini veritabanına kaydeder."""
    updated_count = 0
    
    if not cop_data:
        return updated_count
    
    # COP data format: {"9": {"alan_adi": {"link": "url", "guncelleme_yili": "2024"}}}
    for sinif, sinif_data in cop_data.items():
        for alan_adi, cop_info in sinif_data.items():
            try:
                cop_url = cop_info.get('link', '')
                if cop_url:
                    cursor.execute("""
                        UPDATE temel_plan_alan 
                        SET cop_url = ? 
                        WHERE alan_adi = ?
                    """, (cop_url, alan_adi))
                    if cursor.rowcount > 0:
                        updated_count += 1
                        print(f"ÇÖP güncellendi: {alan_adi} -> {cop_url}")
                        
            except Exception as e:
                print(f"ÇÖP güncelleme hatası: {alan_adi} - {str(e)}")
    
    return updated_count

def save_bom_data_to_db(cursor, bom_data):
    """BOM verilerini veritabanına kaydeder."""
    updated_count = 0
    
    if not bom_data or 'dersler' not in bom_data:
        return updated_count
    
    for ders_info in bom_data['dersler']:
        try:
            ders_adi = ders_info.get('ders_adi', '')
            moduller = ders_info.get('moduller', [])
            
            # BOM URL'lerini birleştir (virgülle ayrılmış)
            bom_urls = [modul.get('link', '') for modul in moduller if modul.get('link')]
            bom_url_string = ', '.join(bom_urls) if bom_urls else ''
            
            if bom_url_string:
                cursor.execute("""
                    UPDATE temel_plan_ders 
                    SET bom_url = ? 
                    WHERE ders_adi = ?
                """, (bom_url_string, ders_adi))
                if cursor.rowcount > 0:
                    updated_count += 1
                    
        except Exception as e:
            print(f"BOM güncelleme hatası: {ders_adi} - {str(e)}")
    
    return updated_count

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
