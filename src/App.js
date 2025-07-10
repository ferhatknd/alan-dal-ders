import React, { useState, useEffect, useCallback, useMemo } from 'react';

function App() {
  // State'leri birleştirelim ve genişletelim
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false); // isScraping yerine
  const [initialLoading, setInitialLoading] = useState(true); // Sayfa ilk yüklenirken
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);

  // Debouncing efekti: Kullanıcı yazmayı bıraktıktan 300ms sonra
  // arama terimini günceller.
  useEffect(() => {
    const timerId = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, 300);
    return () => {
      clearTimeout(timerId);
    };
  }, [searchTerm]);

  // Sayfa ilk yüklendiğinde önbellekteki veriyi çek
  useEffect(() => {
    const fetchCachedData = async () => {
      try {
        const response = await fetch('http://localhost:5001/api/get-cached-data');
        if (!response.ok) {
          throw new Error(`Önbellek sunucusundan yanıt alınamadı: ${response.statusText}`);
        }
        const cachedData = await response.json();
        if (cachedData && cachedData.alanlar && Object.keys(cachedData.alanlar).length > 0) {
          setData(cachedData);
          setProgress([{ message: "Önbellekten veriler başarıyla yüklendi.", type: 'done' }]);
        } else {
          setProgress([{ message: "Önbellek boş. Verileri çekmek için butona tıklayın.", type: 'info' }]);
        }
      } catch (e) {
        console.error("Önbellek verisi çekme hatası:", e);
        setError(`Önbellek verisi çekilemedi. Backend sunucusunun çalıştığından emin olun. Hata: ${e.message}`);
      } finally {
        setInitialLoading(false);
      }
    };

    fetchCachedData();
  }, []); // Boş bağımlılık dizisi, sadece component mount edildiğinde çalışır

  // Veri çekme fonksiyonu (eski startScraping)
  const handleScrape = useCallback(() => {
    // Tüm state'leri sıfırla
    setData(null);
    setProgress([]);
    setError(null);
    setLoading(true);

    const eventSource = new EventSource('http://localhost:5001/api/scrape-stream');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);

      if (eventData.type === 'done') {
        setData(eventData.data);
        setProgress(prev => [...prev, { message: "Tüm veriler başarıyla çekildi!", type: 'done' }]);
        eventSource.close();
        setLoading(false);
      } else {
        setProgress(prev => [...prev, eventData]);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      setError("Veri akışı sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      eventSource.close();
      setLoading(false);
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Alanları isme göre sıralamak için bir yardımcı fonksiyon
  const getSortedAlans = useCallback((alanlar) => {
    if (!alanlar) return [];
    return Object.values(alanlar).sort((a, b) => a.isim.localeCompare(b.isim, 'tr'));
  }, []);

  // Arama terimine göre alanları filtrele
  const filteredAlanlar = useMemo(() => {
    if (!data || !data.alanlar) {
      return [];
    }
    const term = debouncedTerm.trim().toLowerCase();
    const sorted = getSortedAlans(data.alanlar);
    if (!term) {
      return sorted;
    }
    return sorted.filter(alanData => alanData.isim.toLowerCase().includes(term));
  }, [debouncedTerm, data, getSortedAlans]);
  
  return (
    <div className="App">
      <h1>MEB Ders ve DBF Veri Çekici</h1>
      <button onClick={handleScrape} disabled={loading || initialLoading}>
        {loading
          ? 'Veriler Çekiliyor...'
          : data
            ? 'Verileri Yeniden Çek'
            : 'Verileri Çek'}
      </button>

      {/* Arama Kutusu */}
      {!initialLoading && data && (
        <div className="search-bar">
          <input
            type="text"
            placeholder="Filtrelemek için alan adı girin..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      )}

      {/* İlerleme ve Hata Mesajları Alanı */}
      {(loading || progress.length > 0 || error) && (
        <div id="progress-container" style={{ border: '1px solid #ccc', padding: '10px', marginTop: '10px', height: '300px', overflowY: 'scroll', backgroundColor: '#f8f9fa' }}>
          {initialLoading && <p>Önbellek kontrol ediliyor...</p>}
          {error && <p style={{ color: 'red', fontWeight: 'bold' }}>HATA: {error}</p>}
          {progress.map((p, index) => (
            <div key={index} style={{ color: p.type === 'error' ? 'red' : p.type === 'warning' ? '#e67e22' : 'black' }}>
              <p style={{ margin: '2px 0' }}>{p.message}</p>
              {p.estimation && <small><i>{p.estimation}</i></small>}
            </div>
          ))}
        </div>
      )}

      {/* Veri Görüntüleme Alanı */}
      {!initialLoading && data && (
        <div className="data-display" style={{ marginTop: '10px', textAlign: 'left' }}>
          <h2>Alınan Veriler ({filteredAlanlar.length} alan bulundu)</h2>
          {filteredAlanlar.length > 0 ? (
            filteredAlanlar.map((alan, index) => (
              <div key={index} style={{ border: '1px solid #eee', padding: '10px', marginBottom: '10px', borderRadius: '5px' }}>
                <h3 style={{ marginTop: 0 }}>
                  {debouncedTerm.trim()
                    ? alan.isim.split(new RegExp(`(${debouncedTerm})`, 'gi')).map((part, i) =>
                        part.toLowerCase() === debouncedTerm.toLowerCase().trim() ? (
                          <mark key={i}>{part}</mark>
                        ) : (
                          part
                        )
                      )
                    : alan.isim}
                </h3>
                {alan.dbf_bilgileri && Object.keys(alan.dbf_bilgileri).length > 0 ? (
                  <div>
                    <strong>Ders Bilgi Formları (DBF):</strong>
                    <ul>
                      {Object.entries(alan.dbf_bilgileri)
                        .sort(([sinifA], [sinifB]) => parseInt(sinifA) - parseInt(sinifB)) // Sınıfa göre sırala
                        .map(([sinif, info]) => (
                          <li key={sinif}>
                            {sinif}. Sınıf: <a href={info.link} target="_blank" rel="noopener noreferrer">{info.link.split('/').pop()}</a>
                            {info.guncelleme_tarihi && <small> ({info.guncelleme_tarihi})</small>}
                          </li>
                        ))}
                    </ul>
                  </div>
                ) : (
                  <p><small>Bu alan için DBF linki bulunamadı.</small></p>
                )}

              {/* Çerçeve Öğretim Programları (ÇÖP) */}
              {alan.cop_bilgileri && Object.keys(alan.cop_bilgileri).length > 0 ? (
                <div className="cop-listesi">
                  <strong>Çerçeve Öğretim Programları (ÇÖP):</strong>
                  <ul>
                    {Object.entries(alan.cop_bilgileri)
                      .sort(([sinifA], [sinifB]) => parseInt(sinifA) - parseInt(sinifB)) // Sınıfa göre sırala
                      .map(([sinif, info]) => (
                        <li key={sinif}>
                          {sinif}. Sınıf: <a href={info.link} target="_blank" rel="noopener noreferrer">{info.link.split('/').pop()}</a>
                          {info.guncelleme_yili && <small> (Yıl: {info.guncelleme_yili})</small>}
                        </li>
                      ))}
                  </ul>
                </div>
              ) : null}

              {/* Dersler (Çerçeve Öğretim Programları) */}
              {alan.dersler && Object.keys(alan.dersler).length > 0 ? (
                <div className="ders-listesi">
                  <strong>Çerçeve Öğretim Programları (Dersler):</strong>
                  <ul>
                    {Object.entries(alan.dersler)
                      .sort(([, dersA], [, dersB]) => dersA.isim.localeCompare(dersB.isim, 'tr'))
                      .map(([link, ders]) => (
                        <li key={link}>
                          <span>
                            {ders.isim}
                            <small> ({ders.siniflar.join('-')}. Sınıf)</small>
                          </span>
                          <a href={link} target="_blank" rel="noopener noreferrer" className="ders-link">
                            PDF
                          </a>
                        </li>
                      ))}
                  </ul>
                </div>
              ) : null}
              </div>
            ))
          ) : (
            <p>Arama kriterlerinize uygun alan bulunamadı.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
