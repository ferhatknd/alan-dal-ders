from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import json
import time
import os
import requests
import subprocess
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

# alanlar_ve_dersler3.py dosyasından scrape_data fonksiyonunu import ediyoruz
from alanlar_ve_dersler3 import scrape_data

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
    DBF (Ders Bilgi Formu) verilerini döndürür.
    """
    result = getir_dbf()
    return jsonify(result)

@app.route('/api/get-cop')
def api_get_cop():
    """
    ÇÖP (Çerçeve Öğretim Programı) verilerini döndürür.
    """
    result = getir_cop()
    return jsonify(result)

@app.route('/api/get-dm')
def api_get_dm():
    """
    Ders Materyali (PDF) verilerini döndürür.
    """
    result = getir_dm()
    return jsonify(result)

@app.route('/api/get-bom')
def api_get_bom():
    """
    Bireysel Öğrenme Materyali (BÖM) verilerini döndürür.
    """
    result = getir_bom()
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
