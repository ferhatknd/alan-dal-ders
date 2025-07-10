from flask import Flask, Response, jsonify
from flask_cors import CORS
import json
import time
import os

# alanlar_ve_dersler3.py dosyasından scrape_data fonksiyonunu import ediyoruz
from alanlar_ve_dersler3 import scrape_data

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)