from flask import Flask, jsonify
import sys

# alanlar_ve_dersler3.py dosyasındaki scrape_data fonksiyonunu import et
from alanlar_ve_dersler3 import scrape_data

app = Flask(__name__)
# Geliştirme sırasında proxy (setupProxy.js) kullanıldığı için CORS'a gerek yoktur.
# Proxy, tarayıcının farklı bir origin'e (localhost:5000) istekte bulunduğunu görmesini engeller.

import json

@app.route('/api/scrape')
def get_scraped_data():
    """Veri çekme işlemini başlatan ve sonucu JSON olarak döndüren API endpoint'i."""
    try:
        print("Backend: Scraping işlemi başlatıldı...", file=sys.stderr)
        data = scrape_data()
        print("Backend: Scraping işlemi tamamlandı.", file=sys.stderr)
        
        # Büyük veri yazdırma işlemi sunucuyu çökerttiği için kaldırıldı.
        # Sadece işlemin başarılı olduğunu belirten bir log bırakalım.
        if data and "alanlar" in data:
            print(f"Backend: {len(data['alanlar'])} adet alan başarıyla çekildi.", file=sys.stderr)
        else:
            print("Backend: Veri çekildi ancak format beklenildiği gibi değil veya boş.", file=sys.stderr)

        return jsonify(data)
    except Exception as e:
        print(f"Backend Hata: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
