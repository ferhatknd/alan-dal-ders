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

app = Flask(__name__)
# CORS'u etkinleştirerek localhost:3000 gibi farklı bir porttan gelen
# istekleri kabul etmesini sağlıyoruz.
CORS(app)

CACHE_FILE = "data/scraped_data.json"

@app.route('/api/get-cached-data')
def get_cached_data():
    """
    Önbelleğe alınmış veri dosyasını okur ve içeriğini JSON olarak döndürür.
    """
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)