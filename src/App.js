import React, { useState, useEffect, useCallback, useMemo } from 'react';

const OrtakAlanlarCell = ({ dersLink, currentAlanId, ortakAlanIndeksi, allAlans }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const ortakAlanIds = (ortakAlanIndeksi[dersLink] || []).filter(id => id !== currentAlanId);

  if (ortakAlanIds.length === 0) {
    return <td>-</td>;
  }

  const ortakAlanNames = ortakAlanIds.map(id => allAlans[id]?.isim || `ID: ${id}`);
  const displayLimit = 2;
  const needsTruncation = ortakAlanNames.length > displayLimit;
  const displayedNames = isExpanded ? ortakAlanNames : ortakAlanNames.slice(0, displayLimit);

  return (
    <td className="ortak-alanlar-cell">
      {displayedNames.join(', ')}
      {needsTruncation && !isExpanded && (
        <>
          ... <button onClick={() => setIsExpanded(true)} className="expand-button">&gt;&gt;</button>
        </>
      )}
    </td>
  );
};

const AlanItem = ({ alan, ortakAlanIndeksi, allAlans, searchTerm }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const sortedDersler = useMemo(() => {
    if (!alan.dersler) return [];
    return Object.entries(alan.dersler).sort(([, a], [, b]) => a.isim.localeCompare(b.isim, 'tr'));
  }, [alan.dersler]);

  const renderHighlightedText = (text, highlight) => {
    if (!highlight.trim()) {
      return text;
    }
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return (
      <>
        {parts.map((part, i) =>
          part.toLowerCase() === highlight.toLowerCase() ? (
            <mark key={i}>{part}</mark>
          ) : (
            part
          )
        )}
      </>
    );
  };

  return (
    <div className="alan-item">
      <div className="alan-header" onClick={() => setIsExpanded(!isExpanded)}>
        <h3>
          {renderHighlightedText(alan.isim, searchTerm)}
          <span className="ders-sayisi">
            ({Object.keys(alan.dersler || {}).length} ders)
          </span>
        </h3>
        <span>{isExpanded ? '−' : '+'}</span>
      </div>
      {isExpanded && (
        <div className="alan-details">
          {sortedDersler.length > 0 ? (
            <table className="ders-tablosu">
              <thead>
                <tr>
                  <th>Alan</th>
                  <th>Ders Adı</th>
                  <th>Sınıfı</th>
                  <th>Ders Materyali</th>
                  <th>Okutulduğu Diğer Alanlar</th>
                </tr>
              </thead>
              <tbody>
                {sortedDersler.map(([link, ders]) => (
                  <tr key={link}>
                    <td>{alan.isim}</td>
                    <td>{ders.isim}</td>
                    <td>{ders.siniflar.join('-')}</td>
                    <td><a href={link} target="_blank" rel="noopener noreferrer" className="ders-link">PDF</a></td>
                    <OrtakAlanlarCell
                      dersLink={link}
                      currentAlanId={alan.id}
                      ortakAlanIndeksi={ortakAlanIndeksi}
                      allAlans={allAlans}
                    />
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Bu alan için ders (Çerçeve Öğretim Programı) bulunamadı.</p>
          )}

          <div className="info-section">
            {alan.dbf_bilgileri && Object.keys(alan.dbf_bilgileri).length > 0 && (
              <ul>
                <strong>Ders Bilgi Formları (DBF):</strong>
                {Object.entries(alan.dbf_bilgileri).sort(([a], [b]) => parseInt(a) - parseInt(b)).map(([sinif, info]) => (
                  <li key={`dbf-${sinif}`}>{sinif}. Sınıf: <a href={info.link} target="_blank" rel="noopener noreferrer">{info.link.split('/').pop()}</a> {info.guncelleme_tarihi && <small>({info.guncelleme_tarihi})</small>}</li>
                ))}
              </ul>
            )}
            {alan.cop_bilgileri && Object.keys(alan.cop_bilgileri).length > 0 && (
              <ul>
                <strong>Çerçeve Öğretim Programları (ÇÖP):</strong>
                {Object.entries(alan.cop_bilgileri).sort(([a], [b]) => parseInt(a) - parseInt(b)).map(([sinif, info]) => (
                  <li key={`cop-${sinif}`}>{sinif}. Sınıf: <a href={info.link} target="_blank" rel="noopener noreferrer">{info.link.split('/').pop()}</a> {info.guncelleme_yili && <small>(Yıl: {info.guncelleme_yili})</small>}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

function App() {  
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
  }, []);

  // Veri çekme fonksiyonu (eski startScraping)
  const handleScrape = useCallback(() => {
    // Eğer veri zaten varsa, kullanıcıya yeniden çekmek isteyip istemediğini sor
    if (data && !window.confirm('Veriler zaten mevcut. En güncel verileri çekmek için yeniden başlatmak istediğinize emin misiniz? Bu işlem biraz zaman alabilir.')) {
      return; // Kullanıcı iptal ederse işlemi durdur
    }

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
    // Alanları ID'ye göre değil, isme göre sırala
    return Object.entries(alanlar).sort(([, a], [, b]) => a.isim.localeCompare(b.isim, 'tr'));
  }, []); 

  // Arama terimine göre alanları filtrele
  const filteredAlanlar = useMemo(() => {
    if (!data || !data.alanlar) {
      return [];
    }
    const term = debouncedTerm.trim().toLocaleLowerCase('tr');
    const sorted = getSortedAlans(data.alanlar);
    if (!term) {
      return sorted;
    }
    return sorted.filter(([, alanData]) => alanData.isim.toLocaleLowerCase('tr').includes(term));
  }, [debouncedTerm, data, getSortedAlans]);
  
  return (
    <div className="App">
      <h1>meslek.meb (alan-dal-ders) dosyalar</h1>
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
        <div className="data-display">
          <h2>Alınan Veriler ({filteredAlanlar.length} alan bulundu)</h2>
          {filteredAlanlar.length > 0 ? (
            filteredAlanlar.map(([alanId, alanData]) => (
              <AlanItem
                key={alanId}
                alan={{ ...alanData, id: alanId }}
                ortakAlanIndeksi={data.ortak_alan_indeksi || {}}
                allAlans={data.alanlar}
                searchTerm={debouncedTerm}
              />
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
