import React, { useState } from 'react';
import './App.css';
import DataDisplay from './DataDisplay';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState([]);

  const handleScrape = () => {
    setLoading(true);
    setData(null);
    setError(null);
    setProgress([]);

    // SSE için EventSource kullanıyoruz
    const eventSource = new EventSource('/api/scrape-stream');

    // Sunucudan her yeni mesaj geldiğinde bu fonksiyon çalışır
    eventSource.onmessage = (event) => {
      const parsedData = JSON.parse(event.data);

      if (parsedData.type === 'progress' || parsedData.type === 'warning') {
        // İlerleme mesajlarını listeye ekle
        setProgress(prev => [...prev, parsedData.message]);
      } else if (parsedData.type === 'done') {
        // İşlem bittiğinde, nihai veriyi state'e ata
        setData(parsedData.data);
        setLoading(false);
        eventSource.close(); // Bağlantıyı kapat
      }
    };

    // Bağlantı hatası durumunda bu fonksiyon çalışır
    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      setError("Veri akışı sırasında bir hata oluştu. Sunucu bağlantısını kontrol edin.");
      setLoading(false);
      eventSource.close();
    };
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>MEB Alan/Ders Veri Çekme Aracı</h1>
        <button onClick={handleScrape} disabled={loading}>
          {loading ? 'Veriler Çekiliyor...' : 'Verileri Çek'}
        </button>
      </header>
      <main>
        {loading && (
          <div className="progress-container">
            <h3>İlerleme Durumu:</h3>
            <ul className="progress-list">
              {progress.map((msg, index) => (
                <li key={index}>{msg}</li>
              ))}
            </ul>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        {data && <DataDisplay scrapedData={data} />}
      </main>
    </div>
  );
}

export default App;