from flask import Flask, jsonify
from flask_cors import CORS
import sys

# alanlar_ve_dersler3.py dosyasındaki scrape_data fonksiyonunu import et
from alanlar_ve_dersler3 import scrape_data

app = Flask(__name__)
# React uygulamasından (localhost:3000) gelen isteklere izin ver
CORS(app)

@app.route('/api/scrape')
def get_scraped_data():
    """Veri çekme işlemini başlatan ve sonucu JSON olarak döndüren API endpoint'i."""
    try:
        print("Backend: Scraping işlemi başlatıldı...", file=sys.stderr)
        data = scrape_data()
        print("Backend: Scraping işlemi tamamlandı.", file=sys.stderr)
        return jsonify(data)
    except Exception as e:
        print(f"Backend Hata: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)