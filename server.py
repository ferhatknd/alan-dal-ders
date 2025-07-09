from flask import Flask, Response
import json
import os

# alanlar_ve_dersler3.py dosyasındaki scrape_data fonksiyonunu import et
from alanlar_ve_dersler3 import scrape_data

app = Flask(__name__)

# Önbellek dosyasının yolu
CACHE_FILE = "data/scraped_data.json"

@app.route('/api/scrape-stream')
def scrape_stream():
    """
    Veri çekme işlemini başlatır ve ilerlemeyi Server-Sent Events (SSE)
    olarak tarayıcıya stream eder. Eğer veri önbellekte varsa, oradan okur.
    """
    def generate():
        # Önbellek dosyasını kontrol et
        if os.path.exists(CACHE_FILE):
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Veriler önbellekten okunuyor...'})}\n\n"
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            # Önbellekteki veriyi 'done' olayı olarak gönder
            yield f"data: {json.dumps({'type': 'done', 'data': cached_data})}\n\n"
            return # Fonksiyonu sonlandır

        # Önbellek yoksa, veriyi web'den çek
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
                print(f"Veri başarıyla {CACHE_FILE} dosyasına önbelleklendi.")
            except IOError as e:
                print(f"HATA: Önbellek dosyası yazılamadı: {e}")
    
    # Tarayıcının bunun bir event stream olduğunu anlaması için mimetype önemlidir.
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # React genellikle 3000 portunda çalışır, çakışmayı önlemek için farklı bir port kullanalım.
    app.run(debug=True, port=5001)
