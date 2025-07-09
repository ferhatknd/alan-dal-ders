from flask import Flask, Response, jsonify
import json

# alanlar_ve_dersler3.py dosyasındaki scrape_data fonksiyonunu import et
from alanlar_ve_dersler3 import scrape_data

app = Flask(__name__)

@app.route('/api/scrape-stream')
def scrape_stream():
    """
    Veri çekme işlemini başlatır ve ilerlemeyi Server-Sent Events (SSE)
    olarak tarayıcıya stream eder.
    """
    def generate():
        # scrape_data artık bir generator. Her yield ettiğinde bir olay gönderir.
        for event in scrape_data():
            # SSE formatı: "data: <json_string>\n\n"
            yield f"data: {json.dumps(event)}\n\n"
    
    # Tarayıcının bunun bir event stream olduğunu anlaması için mimetype önemlidir.
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # React genellikle 3000 portunda çalışır, çakışmayı önlemek için farklı bir port kullanalım.
    app.run(debug=True, port=5001)
