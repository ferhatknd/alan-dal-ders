from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import json
import time
import os
import requests
# import subprocess  # Unused
import io
import sys
import sqlite3
import re
from contextlib import redirect_stdout, redirect_stderr

# artık alanlar_ve_dersler3.py kullanmıyoruz, getir_* modülleri kullanıyoruz

# oku_dbf.py'den fonksiyonları import ediyoruz
from modules.oku_dbf import oku_dbf

# Yeni modülleri import et
from modules.getir_dbf import getir_dbf, download_and_extract_dbf_with_progress, get_dbf
from modules.getir_cop import get_cop
# from modules.oku_cop import oku_cop_pdf as new_oku_cop_pdf, save_cop_results_to_db as new_save_cop_results_to_db
from modules.getir_dm import get_dm
from modules.getir_bom import getir_bom
from modules.getir_dal import getir_dal_with_db_integration

# Database utilities from utils.py
from modules.utils import with_database_json, find_or_create_database, get_or_create_alan, normalize_to_title_case_tr, normalize_alan_adi, merge_cop_urls

app = Flask(__name__)
# CORS'u etkinleştirerek localhost:3000 gibi farklı bir porttan gelen
# istekleri kabul etmesini sağlıyoruz.
CORS(app)

CACHE_FILE = "data/scraped_data.json"

@app.route('/api/get-cached-data')
@with_database_json
def get_cached_data(cursor):
    """
    Veritabanından UI için uygun formatta veri döndürür.
    """
    try:
        # Alanları al
        cursor.execute("""
            SELECT id, alan_adi, cop_url 
            FROM temel_plan_alan 
            ORDER BY alan_adi
        """)
        alanlar_raw = cursor.fetchall()
        
        if not alanlar_raw:
            return {}
        
        # UI formatında alan verisi oluştur
        alanlar = {}
        ortak_alan_indeksi = {}
        
        for row in alanlar_raw:
            alan_id, alan_adi, cop_url = row['id'], row['alan_adi'], row['cop_url']
            
            # Alan için dersleri al (dal üzerinden bağlantı)
            cursor.execute("""
                SELECT DISTINCT d.ders_adi, d.sinif, d.dm_url, d.dbf_url
                FROM temel_plan_ders d
                JOIN temel_plan_ders_dal dd ON d.id = dd.ders_id
                JOIN temel_plan_dal dal ON dd.dal_id = dal.id
                WHERE dal.alan_id = ?
                ORDER BY d.ders_adi, d.sinif
            """, (alan_id,))
            dersler_raw = cursor.fetchall()
            
            # Dersleri UI formatında grupla
            dersler = {}
            for ders_row in dersler_raw:
                ders_adi, sinif, dm_url, dbf_url = ders_row['ders_adi'], ders_row['sinif'], ders_row['dm_url'], ders_row['dbf_url']
                if dm_url and dm_url not in dersler:
                    dersler[dm_url] = {
                        'isim': ders_adi,
                        'siniflar': [],
                        'dbf_pdf_path': dbf_url
                    }
                
                if dm_url and sinif and sinif not in dersler[dm_url]['siniflar']:
                    dersler[dm_url]['siniflar'].append(str(sinif))
            
            # Alan verisini oluştur
            alanlar[str(alan_id)] = {
                'isim': alan_adi,
                'dersler': dersler,
                'cop_bilgileri': {
                    '9': {'link': cop_url, 'guncelleme_yili': '2024'}
                } if cop_url else {},
                'dbf_bilgileri': {}
            }
        
        # UI beklediği format
        result = {
            'alanlar': alanlar,
            'ortak_alan_indeksi': ortak_alan_indeksi
        }
        
        return result
        
    except Exception as e:
        print(f"Cache data error: {e}")
        # Fallback: eski JSON dosyası varsa onu dön
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {}

# DISABLED: scrape_data() fonksiyonu tanımlı değil
# @app.route('/api/scrape-stream')
# def scrape_stream():
#     """
#     Veri çekme işlemini başlatır ve sonuçları Server-Sent Events (SSE)
#     protokolü üzerinden anlık olarak istemciye gönderir.
#     """
#     def generate():
#         # scrape_data bir generator olduğu için, her yield edilen veriyi alıp
#         # SSE formatına uygun şekilde istemciye gönderiyoruz.
#         for data_chunk in scrape_data():
#             # Format: "data: <json_verisi>\n\n"
#             yield f"data: {json.dumps(data_chunk)}\n\n"
#             time.sleep(0.05) # İstemcinin veriyi işlemesi için küçük bir bekleme
# 
#     return Response(generate(), mimetype='text/event-stream')

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
                # stdout'u yakalayarak oku_dbf() fonksiyonunun çıktısını al
                with redirect_stdout(output_buffer):
                    result = oku_dbf(temp_filename)
                
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
@app.route('/api/get-dbf')
def api_get_dbf():
    """
    DBF (Ders Bilgi Formu) verilerini çeker, veritabanına kaydeder ve dosyaları indirir.
    İlerlemeyi SSE ile anlık olarak gönderir.
    """
    def generate():
        try:
            # 1. DBF linklerini çek
            yield f"data: {json.dumps({'type': 'status', 'message': 'DBF linkleri MEB sitesinden çekiliyor...'})}\n\n"
            dbf_data = getir_dbf()
            yield f"data: {json.dumps({'type': 'status', 'message': f'{sum(len(alanlar) for alanlar in dbf_data.values())} alan için DBF linkleri bulundu.'})}\n\n"
            
            # 2. URL'leri veritabanına kaydet
            yield f"data: {json.dumps({'type': 'status', 'message': 'URLler veritabanına kaydediliyor...'})}\n\n"
            try:
                from modules.getir_dbf import save_dbf_urls_to_database
                save_result = save_dbf_urls_to_database()
                if save_result and save_result.get('success'):
                    count = save_result.get('count', 0)
                    yield f"data: {json.dumps({'type': 'success', 'message': f'{count} alan için URLler veritabanına kaydedildi.'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'warning', 'message': 'URL kaydetme işlemi tamamlanamadı.'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'URL kaydetme hatası: {str(e)}'})}\n\n"
            
            # 3. Dosyaları indir (açma işlemi geçici olarak durduruldu)
            yield f"data: {json.dumps({'type': 'status', 'message': 'DBF dosyaları indiriliyor (açma işlemi geçici olarak durduruldu)...'})}\n\n"
            
            # get_dbf fonksiyonu HTML parsing'i dahili olarak yapıyor ve JSON üretiyor
            for msg in get_dbf():
                yield f"data: {json.dumps(msg)}\n\n"
                time.sleep(0.05)
            
            yield f"data: {json.dumps({'type': 'done', 'message': 'DBF işlemleri tamamlandı: Linkler çekildi, veritabanına kaydedildi ve dosyalar indirildi.'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'DBF işlemi hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/get-cop')
def api_get_cop():
    """
    ÇÖP linklerini çeker ve veritabanına kaydeder.
    İlerlemeyi SSE ile anlık olarak gönderir.
    """
    def generate():
        try:
            # get_cop fonksiyonu HTML parsing'i dahili olarak yapıyor ve JSON üretiyor
            for message in get_cop():
                yield f"data: {json.dumps(message)}\n\n"
                time.sleep(0.05)
        except Exception as e:
            error_message = {'type': 'error', 'message': f'ÇÖP linkleri çekilirken hata oluştu: {str(e)}'}
            yield f"data: {json.dumps(error_message)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/get-dm')
def api_get_dm():
    """
    Ders Materyali (PDF) verilerini çeker ve veritabanına kaydeder.
    Server-Sent Events (SSE) ile real-time progress updates.
    """
    def generate():
        try:
            for message in get_dm():
                yield f"data: {json.dumps(message)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

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

@app.route('/api/get-statistics')
@with_database_json
def get_statistics(cursor):
    """
    Veritabanı ve dosya sisteminden istatistikleri toplar ve döndürür.
    """
    stats = {
        "alan": 0, "dal": 0, "ders": 0,
        "cop_pdf": 0, "dbf_rar": 0, "dbf_pdf": 0, "dbf_docx": 0,
        "dm_pdf": 0, "bom_pdf": 0, "cop_okunan": 0, "dbf_okunan": 0
    }

    try:
        # 1. Veritabanından istatistikleri al
        cursor.execute("SELECT COUNT(id) FROM temel_plan_alan")
        stats["alan"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(id) FROM temel_plan_dal")
        stats["dal"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(id) FROM temel_plan_ders")
        stats["ders"] = cursor.fetchone()[0]

        # dbf_okunan: ders saati 0'dan büyük olan dersler
        cursor.execute("SELECT COUNT(id) FROM temel_plan_ders WHERE ders_saati > 0")
        stats["dbf_okunan"] = cursor.fetchone()[0]

        # cop_okunan: bir dala bağlı olan dersler
        cursor.execute("SELECT COUNT(DISTINCT ders_id) FROM temel_plan_ders_dal")
        stats["cop_okunan"] = cursor.fetchone()[0]

        # 2. Dosya sisteminden istatistikleri al
        data_dir = "data"
        if os.path.exists(data_dir):
            
            def count_files_in_dir(directory, extensions):
                count = 0
                if os.path.exists(directory):
                    for _, _, files in os.walk(directory):
                        for file in files:
                            if file.lower().endswith(tuple(extensions)):
                                count += 1
                return count

            stats["cop_pdf"] = count_files_in_dir(os.path.join(data_dir, "cop"), ['.pdf']) + count_files_in_dir(os.path.join(data_dir, "cop_files"), ['.pdf'])
            stats["dbf_rar"] = count_files_in_dir(os.path.join(data_dir, "dbf"), ['.rar', '.zip'])
            stats["dbf_pdf"] = count_files_in_dir(os.path.join(data_dir, "dbf"), ['.pdf'])
            stats["dbf_docx"] = count_files_in_dir(os.path.join(data_dir, "dbf"), ['.docx'])
            stats["dm_pdf"] = count_files_in_dir(os.path.join(data_dir, "dm"), ['.pdf'])
            stats["bom_pdf"] = count_files_in_dir(os.path.join(data_dir, "bom"), ['.pdf'])

        return stats

    except Exception as e:
        print(f"İstatistik alınırken hata oluştu: {e}")
        return {"error": str(e)}

@app.route('/api/alan-dal-options')
@with_database_json
def get_alan_dal_options(cursor):
    """
    Dropdown'lar için alan ve dal seçeneklerini döndürür.
    """
    try:
        # Alanları al (COP URL'leri ile birlikte)
        cursor.execute("SELECT id, alan_adi, cop_url FROM temel_plan_alan ORDER BY alan_adi")
        alanlar = [{"id": row[0], "adi": row[1], "cop_url": row[2]} for row in cursor.fetchall()]
        
        # Her alan için dalları al
        dallar = {}
        for alan in alanlar:
            cursor.execute("""
                SELECT id, dal_adi 
                FROM temel_plan_dal 
                WHERE alan_id = ? 
                ORDER BY dal_adi
            """, (alan["id"],))
            dallar[alan["id"]] = [{"id": row[0], "adi": row[1]} for row in cursor.fetchall()]
        
        return {
            "alanlar": alanlar,
            "dallar": dallar
        }
        
    except Exception as e:
        print(f"Alan-Dal seçenekleri alınırken hata: {e}")
        return {"error": str(e)}

@app.route('/api/table-data')
def get_table_data():
    """
    React frontend için düz tablo verisi döndürür.
    Alan, Dal, Ders, Sınıf, Saat, DM, DBF, BOM sütunları ile.
    """
    try:
        db_path = find_or_create_database()
        if not db_path:
            return jsonify([])
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Sadece dersi olan alan-dal kombinasyonlarını getir
            cursor.execute("""
               SELECT 
                   a.id as alan_id,  -- Ekledik
                   a.alan_adi,
                   d.id as dal_id,  -- Ekledik
                   d.dal_adi,
                   ders.id as ders_id,  -- Ekledik
                   ders.ders_adi,
                   ders.sinif,
                   ders.ders_saati,
                   ders.dm_url,
                   ders.dbf_url,
                   ders.bom_url
                FROM 
                   temel_plan_alan a
                   INNER JOIN temel_plan_dal d ON d.alan_id = a.id
                   INNER JOIN temel_plan_ders_dal dd ON dd.dal_id = d.id
                   INNER JOIN temel_plan_ders ders ON ders.id = dd.ders_id
                ORDER BY 
                   a.alan_adi, 
                   d.dal_adi, 
                   ders.ders_adi, 
                   ders.sinif
            """)
            
            rows = cursor.fetchall()
            
            table_data = []
            for row in rows:
                table_data.append({
                    'alan_id': row[0],    # Sıra numarası güncellendi
                    'alan_adi': row[1],
                    'dal_id': row[2],    # Sıra numarası güncellendi
                    'dal_adi': row[3],
                    'ders_id': row[4],    # Sıra numarası güncellendi
                    'ders_adi': row[5],
                    'sinif': row[6],
                    'ders_saati': row[7],
                    'dm_url': row[8],
                    'dbf_url': row[9],
                    'bom_url': row[10]
                })
            
            return jsonify(table_data)
            
    except Exception as e:
        print(f"Tablo verisi alınırken hata oluştu: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-table-row', methods=['POST'])
def update_table_row():
    """
    Tablodaki bir satırı (ders) günceller.
    """
    try:
        data = request.get_json()
        ders_id = data.get('ders_id')
        updates = data.get('updates', {})
        
        if not ders_id:
            return jsonify({"error": "ders_id gerekli"}), 400
        
        db_path = find_or_create_database()
        if not db_path:
            return jsonify({"error": "Veritabanı bulunamadı"}), 500
        
        # Güncelleme alanlarını hazırla
        allowed_fields = ['ders_adi', 'sinif', 'ders_saati', 'amac', 'dm_url', 'dbf_url', 'bom_url']
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)
        
        if not set_clauses:
            return jsonify({"error": "Güncellenecek geçerli alan bulunamadı"}), 400
        
        values.append(ders_id)  # WHERE koşulu için
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            sql = f"UPDATE temel_plan_ders SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, values)
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Ders bulunamadı"}), 404
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Ders başarıyla güncellendi",
                "updated_count": cursor.rowcount
            })
            
    except Exception as e:
        print(f"Ders güncelleme hatası: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/copy-course', methods=['POST'])
def copy_course():
    """
    Bir dersi farklı alan/dal'a kopyalar.
    """
    try:
        data = request.get_json()
        source_ders_id = data.get('source_ders_id')
        target_alan_id = data.get('target_alan_id')
        target_dal_id = data.get('target_dal_id')
        new_ders_data = data.get('ders_data', {})
        
        if not all([source_ders_id, target_alan_id, target_dal_id]):
            return jsonify({"error": "Kaynak ders, hedef alan ve dal gerekli"}), 400
        
        db_path = find_or_create_database()
        if not db_path:
            return jsonify({"error": "Veritabanı bulunamadı"}), 500
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Kaynak dersi al
            cursor.execute("SELECT * FROM temel_plan_ders WHERE id = ?", (source_ders_id,))
            source_ders = cursor.fetchone()
            
            if not source_ders:
                return jsonify({"error": "Kaynak ders bulunamadı"}), 404
            
            # Yeni ders oluştur
            cursor.execute("""
                INSERT INTO temel_plan_ders (
                    ders_adi, sinif, ders_saati, amac, dm_url, dbf_url, bom_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                new_ders_data.get('ders_adi', source_ders[1]),
                new_ders_data.get('sinif', source_ders[2]),
                new_ders_data.get('ders_saati', source_ders[3]),
                new_ders_data.get('amac', source_ders[4]),
                new_ders_data.get('dm_url', source_ders[5]),
                new_ders_data.get('dbf_url', source_ders[6]),
                new_ders_data.get('bom_url', source_ders[7])
            ))
            
            new_ders_id = cursor.lastrowid
            
            # Yeni ders-dal ilişkisi oluştur
            cursor.execute("""
                INSERT INTO temel_plan_ders_dal (ders_id, dal_id)
                VALUES (?, ?)
            """, (new_ders_id, target_dal_id))
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Ders başarıyla kopyalandı",
                "new_ders_id": new_ders_id
            })
            
    except Exception as e:
        print(f"Ders kopyalama hatası: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/oku-cop')
def api_oku_cop():
    """
    ÇÖP PDF'lerini işleyip alan-dal-ders ilişkilerini çıkararak veritabanına kaydeder.
    """
    def generate():
        try:
            # ÇÖP klasörünü kontrol et
            cop_folder = "data/cop"
            if not os.path.exists(cop_folder):
                yield f"data: {json.dumps({'type': 'error', 'message': 'ÇÖP klasörü bulunamadı. Önce ÇÖP dosyalarını indirin.'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'ÇÖP PDF dosyaları taranıyor...'})}\n\n"
            
            # ÇÖP PDF dosyalarını bul
            cop_files = []
            for root, dirs, files in os.walk(cop_folder):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        cop_files.append(os.path.join(root, file))
            
            if not cop_files:
                yield f"data: {json.dumps({'type': 'error', 'message': 'ÇÖP PDF dosyası bulunamadı.'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'{len(cop_files)} ÇÖP PDF dosyası bulundu. İşleniyor...'})}\n\n"
            
            # oku_cop modülünü import et
            from modules.oku_cop import oku_cop_pdf_file, save_cop_results_to_db
            
            total_processed = 0
            total_courses = 0
            
            # Database işlemleri artık @with_database decorator ile otomatik yönetiliyor
            
            for cop_file in cop_files:
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': f'{os.path.basename(cop_file)} işleniyor...'})}\n\n"
                    
                    # PDF'yi oku_cop.py ile işle
                    result = oku_cop_pdf_file(cop_file)
                    
                    if result:
                        # Sonuçları veritabanına kaydet (@with_database decorator ile)
                        saved_count = save_cop_results_to_db(result)
                        total_courses += saved_count
                        
                        if saved_count > 0:
                            yield f"data: {json.dumps({'type': 'success', 'message': f'{os.path.basename(cop_file)}: {saved_count} ders bilgisi çıkarıldı'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'warning', 'message': f'{os.path.basename(cop_file)}: Ders bilgisi çıkarılamadı'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'warning', 'message': f'{os.path.basename(cop_file)}: İşlenemedi'})}\n\n"
                    
                    total_processed += 1
                    
                    # Progress update
                    if total_processed % 5 == 0:
                        yield f"data: {json.dumps({'type': 'info', 'message': f'{total_processed}/{len(cop_files)} dosya işlendi...'})}\n\n"
                        
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'{os.path.basename(cop_file)} işlenirken hata: {str(e)}'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'message': f'İşlem tamamlandı! {total_processed} ÇÖP PDF dosyası işlendi, {total_courses} ders bilgisi çıkarıldı.'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Genel hata: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/update-ders-saatleri-from-dbf')
def api_update_ders_saatleri_from_dbf():
    """
    DBF dosyalarını işleyip mevcut derslerin ders saatlerini günceller.
    """
    def generate():
        try:
            # Veritabanını bul/oluştur
            db_path = find_or_create_database()
            if not db_path:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Veritabanı bulunamadı veya oluşturulamadı'})}\\n\\n"
                return
            
            # DBF klasörünü kontrol et
            dbf_folder = "dbf"
            if not os.path.exists(dbf_folder):
                yield f"data: {json.dumps({'type': 'error', 'message': 'DBF klasörü bulunamadı. Önce DBF dosyalarını indirin.'})}\\n\\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'DBF dosyaları taranıyor...'})}\\n\\n"
            
            total_updated = 0
            total_processed = 0
            
            # DBF klasöründeki tüm PDF ve DOCX dosyalarını bul
            dbf_files = []
            for root, dirs, files in os.walk(dbf_folder):
                for file in files:
                    if file.lower().endswith(('.pdf', '.docx')):
                        dbf_files.append(os.path.join(root, file))
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'{len(dbf_files)} DBF dosyası bulundu. İşleniyor...'})}\\n\\n"
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                for dbf_file in dbf_files:
                    try:
                        yield f"data: {json.dumps({'type': 'status', 'message': f'{os.path.basename(dbf_file)} işleniyor...'})}\\n\\n"
                        
                        # oku_dbf.py ile DBF dosyasını işle
                        with redirect_stdout(io.StringIO()):
                            parsed_data = oku_dbf(dbf_file)
                        
                        if parsed_data:
                            updated_count = update_ders_saati_from_dbf_data(cursor, parsed_data)
                            total_updated += updated_count
                            
                            if updated_count > 0:
                                yield f"data: {json.dumps({'type': 'success', 'message': f'{os.path.basename(dbf_file)}: {updated_count} ders güncellendi'})}\\n\\n"
                        
                        total_processed += 1
                        
                        # Her 10 dosyada bir commit yap
                        if total_processed % 10 == 0:
                            conn.commit()
                            yield f"data: {json.dumps({'type': 'info', 'message': f'{total_processed}/{len(dbf_files)} dosya işlendi...'})}\\n\\n"
                            
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'{os.path.basename(dbf_file)} işlenirken hata: {str(e)}'})}\\n\\n"
                
                # Final commit
                conn.commit()
            
            yield f"data: {json.dumps({'type': 'done', 'message': f'İşlem tamamlandı! {total_processed} DBF dosyası işlendi, {total_updated} ders saati güncellendi.'})}\\n\\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Genel hata: {str(e)}'})}\\n\\n"
    
    return Response(generate(), mimetype='text/event-stream')

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
                dm_data = get_dm()
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

def init_database():
    """
    Veritabanını başlatır ve gerekli tabloları oluşturur.
    """
    db_path = find_or_create_database()
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Schema dosyasını oku ve çalıştır
            schema_path = os.path.join(os.path.dirname(db_path), "schema.sql")
            
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                # SQL komutlarını çalıştır
                conn.executescript(schema_sql)
                conn.commit()
                print(f"✅ Database initialized successfully: {db_path}")
                
                # Migration versiyonunu kontrol et
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
                version = cursor.fetchone()
                if version:
                    print(f"📊 Current schema version: {version[0]}")
                
            else:
                print(f"⚠️  Warning: Schema file not found at {schema_path}")
                
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e
    
    return db_path

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
    """Ders kaydı oluşturur veya mevcut ders ID'sini döner."""
    # Ders saati değerini düzgün şekilde handle et
    haftalik_ders_saati = course.get('haftalik_ders_saati', '')
    if haftalik_ders_saati and str(haftalik_ders_saati).isdigit():
        ders_saati = int(haftalik_ders_saati)
    else:
        # ÇÖP'te ders saati bilgisi yoksa 0 varsayılan değeri kullan
        ders_saati = 0
    
    ders_adi = course.get('ders_adi', '')
    sinif = int(course.get('sinif', 0)) if course.get('sinif') else None
    
    # Önce mevcut dersi kontrol et
    cursor.execute("""
        SELECT id FROM temel_plan_ders 
        WHERE ders_adi = ? AND sinif = ?
    """, (ders_adi, sinif))
    
    existing = cursor.fetchone()
    if existing:
        return existing[0]  # Mevcut ders ID'sini döner
    
    # Yeni ders oluştur
    cursor.execute("""
        INSERT INTO temel_plan_ders (
            ders_adi, sinif, ders_saati, amac, dm_url, dbf_url, bom_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        ders_adi,
        sinif,
        ders_saati,  # NOT NULL hatası engellemek için 0 kullan
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

def get_or_create_ders(cursor, ders_adi, sinif, amac='', cop_url=''):
    """
    Ders kaydını bulur veya oluşturur. Aynı ders adı + sınıf kombinasyonu için tek kayıt yapar.
    """
    # Önce mevcut dersi ara
    cursor.execute("""
        SELECT id FROM temel_plan_ders 
        WHERE ders_adi = ? AND sinif = ?
    """, (ders_adi, sinif))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Ders yoksa oluştur
    cursor.execute("""
        INSERT INTO temel_plan_ders (
            ders_adi, sinif, ders_saati, amac, dm_url, dbf_url, bom_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ders_adi, sinif, 0, amac, '', '', cop_url))
    
    return cursor.lastrowid

def save_cop_parsed_data_to_db(cursor, parsed_data, alan_adi, sinif, cop_url):
    """
    oku.py ile işlenmiş ÇÖP PDF verilerini temel_plan_* tablolarına kaydeder.
    Ders deduplication mantığı ile güncellenmiştir.
    """
    saved_count = 0
    
    if not parsed_data or not isinstance(parsed_data, dict):
        return saved_count
    
    try:
        # alan_bilgileri bölümünü kontrol et
        alan_bilgileri = parsed_data.get('alan_bilgileri', {})
        if not alan_bilgileri:
            print(f"alan_bilgileri bulunamadı: {alan_adi}")
            return saved_count
        
        # Alan adını oku.py çıktısından al (daha doğru olabilir)
        parsed_alan_adi = alan_bilgileri.get('alan_adi', alan_adi)
        
        # Alan kaydı/bulma
        alan_id = get_or_create_alan(cursor, parsed_alan_adi, None, cop_url, None)
        
        # dal_ders_listesi'ni işle
        dal_ders_listesi = alan_bilgileri.get('dal_ders_listesi', [])
        
        for dal_data in dal_ders_listesi:
            if not isinstance(dal_data, dict):
                continue
                
            dal_adi = dal_data.get('dal_adi', '').strip().rstrip(',')  # Sonundaki virgülü temizle
            if not dal_adi:
                continue
                
            # Dal kaydı/bulma
            dal_id = get_or_create_dal(cursor, dal_adi, alan_id)
            
            # Dersler listesini işle
            dersler = dal_data.get('dersler', [])
            for ders_adi in dersler:
                if isinstance(ders_adi, str) and ders_adi.strip():
                    ders_adi_clean = ders_adi.strip()
                    
                    # Dersi bul veya oluştur (deduplication)
                    ders_id = get_or_create_ders(cursor, ders_adi_clean, sinif, '', cop_url)
                    
                    # Ders-Dal ilişkisini kur
                    cursor.execute("""
                        INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) 
                        VALUES (?, ?)
                    """, (ders_id, dal_id))
                    
                    saved_count += 1
                    print(f"Ders kaydedildi/ilişkilendirildi: {ders_adi_clean} -> {dal_adi}")
        
        # Eğer dal yoksa ve doğrudan dersler varsa (nadiren olabilir)
        if not dal_ders_listesi and 'dersler' in alan_bilgileri:
            dersler = alan_bilgileri.get('dersler', [])
            for ders_adi in dersler:
                if isinstance(ders_adi, str) and ders_adi.strip():
                    ders_adi_clean = ders_adi.strip()
                    
                    # Dersi bul veya oluştur (dal olmadan)
                    ders_id = get_or_create_ders(cursor, ders_adi_clean, sinif, '', cop_url)
                    saved_count += 1
                    print(f"Ders kaydedildi (dal yok): {ders_adi_clean}")
    
    except Exception as e:
        print(f"ÇÖP veri kayıt hatası: {alan_adi} - {str(e)}")
    
    return saved_count


def find_matching_ders(cursor, dbf_ders_adi, sinif=None):
    """
    DBF'teki ders adını veritabanındaki derslerle eşleştirir.
    """
    if not dbf_ders_adi:
        return []
    
    normalized_dbf = normalize_to_title_case_tr(dbf_ders_adi)
    
    # Önce tam eşleşme ara
    if sinif:
        cursor.execute("""
            SELECT id, ders_adi FROM temel_plan_ders 
            WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ders_adi, 'ç', 'c'), 'ğ', 'g'), 'ı', 'i'), 'ö', 'o'), 'ş', 's'), 'ü', 'u')) = ? 
            AND sinif = ?
        """, (normalized_dbf, sinif))
    else:
        cursor.execute("""
            SELECT id, ders_adi FROM temel_plan_ders 
            WHERE UPPER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ders_adi, 'ç', 'c'), 'ğ', 'g'), 'ı', 'i'), 'ö', 'o'), 'ş', 's'), 'ü', 'u')) = ?
        """, (normalized_dbf,))
    
    exact_matches = cursor.fetchall()
    if exact_matches:
        return exact_matches
    
    # Kısmi eşleşme ara (en az 3 kelime ortak)
    dbf_words = set(normalized_dbf.split())
    if len(dbf_words) < 2:
        return []
    
    if sinif:
        cursor.execute("SELECT id, ders_adi FROM temel_plan_ders WHERE sinif = ?", (sinif,))
    else:
        cursor.execute("SELECT id, ders_adi FROM temel_plan_ders")
    
    all_courses = cursor.fetchall()
    partial_matches = []
    
    for course_id, course_name in all_courses:
        normalized_course = normalize_to_title_case_tr(course_name)
        course_words = set(normalized_course.split())
        
        # Ortak kelime sayısı
        common_words = dbf_words.intersection(course_words)
        if len(common_words) >= min(2, len(dbf_words) * 0.6):  # En az %60 ortak
            partial_matches.append((course_id, course_name))
    
    return partial_matches

def update_ders_saati_from_dbf_data(cursor, parsed_data):
    """
    DBF verilerinden ders saatlerini çıkarıp veritabanını günceller.
    """
    updated_count = 0
    
    if not parsed_data or not isinstance(parsed_data, dict):
        return updated_count
    
    try:
        # DBF'ten ders adı ve saat bilgisini çıkar
        ders_adi = parsed_data.get('ders_adi', '')
        haftalik_ders_saati = parsed_data.get('haftalik_ders_saati', 0)
        sinif = parsed_data.get('sinif', None)
        
        if ders_adi and haftalik_ders_saati and str(haftalik_ders_saati).isdigit():
            ders_saati = int(haftalik_ders_saati)
            
            # Eşleşen dersleri bul
            matching_courses = find_matching_ders(cursor, ders_adi, sinif)
            
            for course_id, course_name in matching_courses:
                # Mevcut ders saati 0 ise güncelle
                cursor.execute("SELECT ders_saati FROM temel_plan_ders WHERE id = ?", (course_id,))
                result = cursor.fetchone()
                
                if result and result[0] == 0:  # Sadece 0 olanları güncelle
                    cursor.execute("""
                        UPDATE temel_plan_ders 
                        SET ders_saati = ? 
                        WHERE id = ?
                    """, (ders_saati, course_id))
                    updated_count += 1
                    print(f"Güncellendi: {course_name} -> {ders_saati} saat")
        
        # Öğrenme birimleri ders saatlerini de işle
        ogrenme_birimleri = parsed_data.get('ogrenme_birimleri', [])
        if ogrenme_birimleri and ders_adi:
            # İlgili dersi bul
            matching_courses = find_matching_ders(cursor, ders_adi, sinif)
            
            for course_id, course_name in matching_courses:
                # Bu derse ait öğrenme birimlerini güncelle
                for birim in ogrenme_birimleri:
                    if isinstance(birim, dict):
                        birim_adi = birim.get('ogrenme_birimi', '')
                        birim_saati = birim.get('ders_saati', 0)
                        
                        if birim_adi and birim_saati and str(birim_saati).isdigit():
                            # Öğrenme birimini bul ve güncelle
                            cursor.execute("""
                                UPDATE temel_plan_ders_ogrenme_birimi 
                                SET ders_saati = ? 
                                WHERE ders_id = ? AND ogrenme_birimi LIKE ? AND (ders_saati IS NULL OR ders_saati = 0)
                            """, (int(birim_saati), course_id, f"%{birim_adi.strip()}%"))
    
    except Exception as e:
        print(f"DBF ders saati güncelleme hatası: {str(e)}")
    
    return updated_count

# Yeni 5 Adımlı İş Akışı Endpoints
@app.route('/api/workflow-step-1')
def workflow_step_1():
    """
    Adım 1: Alan-Dal verilerini çekip veritabanına kaydeder.
    """
    def generate():
        try:
            # getir_dal modülünden yeni entegre fonksiyonu kullan
            from modules.getir_dal import getir_dal_with_db_integration
            
            for message in getir_dal_with_db_integration():
                yield f"data: {json.dumps(message)}\n\n"
                time.sleep(0.05)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Adım 1 hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/workflow-step-2')
def workflow_step_2():
    """
    Adım 2: ÇÖP (Çerçeve Öğretim Programı) verilerini çekip organize eder.
    """
    def generate():
        try:
            # getir_cop_oku modülünden yeni entegre fonksiyonu kullan
            from modules.getir_cop import getir_cop_with_db_integration
            
            for message in getir_cop_with_db_integration():
                yield f"data: {json.dumps(message)}\n\n"
                time.sleep(0.05)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Adım 2 hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/workflow-step-3')
def workflow_step_3():
    """
    Adım 3: DBF (Ders Bilgi Formu) verilerini işler.
    """
    def generate():
        try:
            # get_dbf fonksiyonu ile DBF verileri işleniyor
            yield f"data: {json.dumps({'type': 'status', 'message': 'Adım 3: DBF verileri işleniyor...'})}\n\n"
            
            for msg in get_dbf():
                yield f"data: {json.dumps(msg)}\n\n"
                time.sleep(0.05)
                
            yield f"data: {json.dumps({'type': 'done', 'message': 'Adım 3 tamamlandı!'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Adım 3 hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/workflow-step-4')
def workflow_step_4():
    """
    Adım 4: DM (Ders Materyali) verilerini işler.
    """
    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Adım 4: DM (Ders Materyali) verileri işleniyor...'})}\n\n"
            
            # DM verilerini generator olarak işle
            for message in get_dm():
                yield f"data: {json.dumps(message)}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'message': 'Adım 4 tamamlandı!'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Adım 4 hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/workflow-step-5')
def workflow_step_5():
    """
    Adım 5: BOM (Bireysel Öğrenme Materyali) verilerini işler.
    """
    def generate():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Adım 5: BOM (Bireysel Öğrenme Materyali) verileri işleniyor...'})}\n\n"
            bom_data = getir_bom()
            
            # Veritabanına kaydet
            db_path = find_or_create_database()
            if db_path:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    bom_saved = save_bom_data_to_db(cursor, bom_data)
                    yield f"data: {json.dumps({'type': 'success', 'message': f'BOM: {bom_saved} ders güncellendi'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'message': 'Adım 5 tamamlandı!'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Adım 5 hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/workflow-full')
def workflow_full():
    """
    Tüm 5 adımı sıralı olarak çalıştırır.
    """
    def generate():
        try:
            steps = [
                ('Adım 1: Alan-Dal Verileri', '/api/workflow-step-1'),
                ('Adım 2: ÇÖP Verileri', '/api/workflow-step-2'),
                ('Adım 3: DBF Verileri', '/api/workflow-step-3'),
                ('Adım 4: DM Verileri', '/api/workflow-step-4'),
                ('Adım 5: BOM Verileri', '/api/workflow-step-5')
            ]
            
            yield f"data: {json.dumps({'type': 'status', 'message': '5 Adımlı İş Akışı Başlıyor...'})}\n\n"
            
            for step_name, step_endpoint in steps:
                yield f"data: {json.dumps({'type': 'status', 'message': f'{step_name} başlıyor...'})}\n\n"
                
                # Her adımı çalıştır
                if step_endpoint == '/api/workflow-step-1':
                    from modules.getir_dal import getir_dal_with_db_integration
                    for message in getir_dal_with_db_integration():
                        yield f"data: {json.dumps(message)}\n\n"
                        time.sleep(0.05)
                elif step_endpoint == '/api/workflow-step-2':
                    cop_data = getir_cop()
                    cop_count = len(cop_data.get('cop_data', {}))
                    yield f"data: {json.dumps({'type': 'success', 'message': f'ÇÖP verileri çekildi: {cop_count} sınıf'})}\n\n"
                # Diğer adımlar için basitleştirilmiş versiyonlar
                elif step_endpoint == '/api/workflow-step-3':
                    yield f"data: {json.dumps({'type': 'status', 'message': 'DBF verileri işleniyor...'})}\n\n"
                    for msg in get_dbf():
                        yield f"data: {json.dumps(msg)}\n\n"
                        time.sleep(0.05)
                elif step_endpoint == '/api/workflow-step-4':
                    yield f"data: {json.dumps({'type': 'status', 'message': 'DM verileri işleniyor...'})}\n\n"
                    dm_data = get_dm()
                    db_path = find_or_create_database()
                    if db_path:
                        with sqlite3.connect(db_path) as conn:
                            cursor = conn.cursor()
                            dm_saved = save_dm_data_to_db(cursor, dm_data)
                            yield f"data: {json.dumps({'type': 'success', 'message': f'DM: {dm_saved} ders kaydedildi'})}\n\n"
                elif step_endpoint == '/api/workflow-step-5':
                    yield f"data: {json.dumps({'type': 'status', 'message': 'BOM verileri işleniyor...'})}\n\n"
                    bom_data = getir_bom()
                    db_path = find_or_create_database()
                    if db_path:
                        with sqlite3.connect(db_path) as conn:
                            cursor = conn.cursor()
                            bom_saved = save_bom_data_to_db(cursor, bom_data)
                            yield f"data: {json.dumps({'type': 'success', 'message': f'BOM: {bom_saved} ders güncellendi'})}\n\n"
                
                yield f"data: {json.dumps({'type': 'success', 'message': f'{step_name} tamamlandı!'})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'message': '🎉 Tüm 5 adım başarıyla tamamlandı!'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'İş akışı hatası: {str(e)}'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/scrape-alan-dal')
def scrape_alan_dal():
    """
    Veri çekme (scraping) işlemini başlatır ve ilerlemeyi
    Server-Sent Events (SSE) ile anlık olarak gönderir.
    getir_dal.py içerisindeki ana fonksiyonu tetikler.
    """
    def generate():
        try:
            # getir_dal_with_db_integration bir generator'dır.
            # Her yield edilen mesajı alıp SSE formatında gönderiyoruz.
            for message in getir_dal_with_db_integration():
                yield f"data: {json.dumps(message)}\n\n"
                time.sleep(0.05)  # İstemcinin veriyi işlemesi için küçük bir bekleme
        except Exception as e:
            # Hata durumunda istemciye bir hata mesajı gönder
            error_message = {'type': 'error', 'message': f'Bir hata oluştu: {str(e)}'}
            yield f"data: {json.dumps(error_message)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Database'i başlat
    try:
        init_database()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("⚠️  Server will continue, but database operations may fail")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
