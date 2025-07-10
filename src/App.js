import React, { useState, useEffect } from 'react';
import './App.css';
import DataDisplay from './DataDisplay';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true); // Sayfa ilk yüklenirken
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState([]);
  const [estimation, setEstimation] = useState(null); // Tahmin süresi için yeni state

  // Uygulama ilk yüklendiğinde önbellekteki veriyi çekmeyi dene
  useEffect(() => {
    const fetchCachedData = async () => {
      try {
        const response = await fetch('/api/get-cached-data');
        if (!response.ok) {
          throw new Error('Önbellek verisi alınamadı.');
        }
        const cachedData = await response.json();
        // Eğer önbellek boş değilse (anahtar içeriyorsa) veriyi ayarla
        if (Object.keys(cachedData).length > 0) {
          setData(cachedData);
        }
      } catch (e) {
        console.error("Önbellek verisi çekme hatası:", e);
      } finally {
        setInitialLoading(false); // İlk yükleme tamamlandı
      }
    };
    fetchCachedData();
  }, []); // Boş dizi, bu effect'in sadece component mount edildiğinde çalışmasını sağlar

  const handleScrape = () => {
    setLoading(true);
    setData(null);
    setError(null);
    setProgress([]);
    setEstimation(null); // Yeni işlemde tahmini sıfırla

    // SSE için EventSource kullanıyoruz
    // Proxy bazen EventSource ile sorun çıkarabildiği için tam URL'i kullanmak daha güvenilirdir.
    const eventSource = new EventSource('http://localhost:5001/api/scrape-stream');

    // Sunucudan her yeni mesaj geldiğinde bu fonksiyon çalışır
    eventSource.onmessage = (event) => {
      const parsedData = JSON.parse(event.data);

      if (parsedData.type === 'progress' || parsedData.type === 'warning') {
        // İlerleme mesajlarını listeye ekle
        setProgress(prev => [parsedData.message, ...prev]); // Yeni mesajı başa ekle
        // Tahmin verisi varsa state'i güncelle
        if (parsedData.estimation) {
          setEstimation(parsedData.estimation);
        }
      } else if (parsedData.type === 'done') {
        // İşlem bittiğinde, nihai veriyi state'e ata
        setData(parsedData.data);
        setEstimation(null); // İşlem bitince tahmini temizle
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
        <button onClick={handleScrape} disabled={loading || initialLoading}>
          {loading 
            ? 'Veriler Çekiliyor...' 
            : data 
              ? 'Verileri Yeniden Çek' 
              : 'Verileri Çek'
          }
        </button>
      </header>
      <main>
        {initialLoading && <p>Önbellek kontrol ediliyor...</p>}
        {loading && (
          <div className="progress-container">
            {estimation && <p className="estimation">{estimation}</p>}
            <h3>İlerleme Durumu:</h3>
            <ul className="progress-list">
              {progress.slice(0, 10).map((msg, index) => ( // Sadece son 10 mesajı göster
                <li key={index}>{msg}</li>
              ))}
            </ul>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        {!initialLoading && data && <DataDisplay scrapedData={data} />}
      </main>
    </div>
  );
}

export default App;
