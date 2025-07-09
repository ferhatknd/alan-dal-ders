from flask import Flask, Response, jsonify
import json
import os

# alanlar_ve_dersler3.py dosyasındaki scrape_data fonksiyonunu import et
from alanlar_ve_dersler3 import scrape_data

app = Flask(__name__)

# Önbellek dosyasının yolu
CACHE_FILE = "data/scraped_data.json"

@app.route('/api/get-cached-data')
def get_cached_data():
    """
    Önbellekteki JSON dosyasını okur ve içeriğini döndürür.
    Dosya yoksa boş bir nesne döndürür.
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except (IOError, json.JSONDecodeError) as e:
            print(f"HATA: Önbellek dosyası okunamadı: {e}")
            return jsonify({"error": "Cache file is corrupted or unreadable"}), 500
    else:
        # Dosya yoksa, istemcinin hata almaması için boş bir nesne döndür
        return jsonify({})

@app.route('/api/scrape-stream')
def scrape_stream():
    """
    Veri çekme işlemini başlatır, ilerlemeyi SSE olarak stream eder
    ve sonuçları önbellek dosyasına kaydeder/günceller.
    """
    def generate():
        # Bu endpoint her zaman web'den veri çeker.
        final_data = None
        for event in scrape_data():
            # Eğer 'done' tipinde bir olay gelirse, içindeki veriyi daha sonra kaydetmek üzere sakla
            if event.get("type") == "done":
                final_data = event.get("data")

            # Her olayı anında istemciye stream et
            yield f"data: {json.dumps(event)}\n\n"

        # İşlem bittikten ve son veri alındıktan sonra dosyaya kaydet
        if final_data:
            try:
                # 'data' dizininin var olduğundan emin ol
                os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f, ensure_ascii=False, indent=2)
                print(f"Veri başarıyla {CACHE_FILE} dosyasına kaydedildi/güncellendi.")
            except IOError as e:
                print(f"HATA: Önbellek dosyası yazılamadı: {e}")

    # Tarayıcının bunun bir event stream olduğunu anlaması için mimetype önemlidir.
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # React genellikle 3000 portunda çalışır, çakışmayı önlemek için farklı bir port kullanalım.
    app.run(debug=True, port=5001)
