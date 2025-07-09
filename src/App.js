import React, { useState } from 'react';
import './App.css';
import DataDisplay from './DataDisplay';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleScrape = async () => {
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const response = await fetch('/api/scrape');
      if (!response.ok) {
        throw new Error(`HTTP hatası! Durum: ${response.status}`);
      }
      const result = await response.json();
      setData(result);
    } catch (e) {
      console.error("Veri çekme hatası:", e);
      setError(e.message || "Bilinmeyen bir hata oluştu. Lütfen backend sunucusunu kontrol edin.");
    } finally {
      setLoading(false);
    }
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
        {error && <p className="error">{error}</p>}
        {data && <DataDisplay scrapedData={data} />}
      </main>
    </div>
  );
}

export default App;