import React, { useState, useMemo, useEffect } from 'react';

import './DataDisplay.css';

function DataDisplay({ scrapedData }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);

  // Debouncing efekti: Kullanıcı yazmayı bıraktıktan 300ms sonra
  // arama terimini günceller.
  useEffect(() => {
    const timerId = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, 300);

    // Kullanıcı yeni bir tuşa basarsa, önceki zamanlayıcıyı temizle.
    return () => {
      clearTimeout(timerId);
    };
  }, [searchTerm]);

  const { alanlar, ortak_alan_indeksi } = scrapedData || {};

  // Alanları isme göre sıralamak için bir diziye dönüştür
  const sortedAlanlar = useMemo(() => {
    if (!alanlar) return [];
    return Object.entries(alanlar).sort(([, a], [, b]) =>
      a.isim.localeCompare(b.isim, 'tr')
    );
  }, [alanlar]);

  // Arama terimine göre alanları filtrele.
  const filteredAlanlar = useMemo(() => {
    const term = debouncedTerm.trim();
    if (!term) {
      return sortedAlanlar;
    }
    return sortedAlanlar.filter(([, alanData]) =>
      alanData.isim.toLowerCase().includes(term.toLowerCase())
    );
  }, [debouncedTerm, sortedAlanlar]);
  
  if (!alanlar) {
    return <p>Görüntülenecek veri yok.</p>;
  }

  return (
    <div className="data-container">
      <h2>Çekilen Veriler ({filteredAlanlar.length} alan bulundu)</h2>
      <div className="search-bar">
        <input type="text" placeholder="Alan adı ile ara..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
      </div>
      {filteredAlanlar.length > 0 ? (
        filteredAlanlar.map(([alanId, alanData]) => {
        // Dersleri isme göre sırala
        const sortedDersler = Object.entries(alanData.dersler).sort(([, a], [, b]) =>
          a.isim.localeCompare(b.isim, 'tr')
        );

        return (
          <div key={alanId} className="alan-block">
            <h3>
              {debouncedTerm.trim()
                ? alanData.isim.split(new RegExp(`(${debouncedTerm})`, 'gi')).map((part, index) =>
                    part.toLowerCase() === debouncedTerm.toLowerCase().trim() ? (
                      <mark key={index}>{part}</mark>
                    ) : (
                      part
                    )
                  )
                : alanData.isim
              }
              {' '}({alanId})
            </h3>

            {alanData.dbf_links && Object.keys(alanData.dbf_links).length > 0 && (
              <div className="dbf-section">
                <h4>Ders Bilgi Formları (DBF)</h4>
                <ul>
                  {Object.entries(alanData.dbf_links)
                    .sort(([sinifA], [sinifB]) => parseInt(sinifA) - parseInt(sinifB))
                    .map(([sinif, link]) => (
                      <li key={sinif}>
                        {sinif}. Sınıf: <a href={link} target="_blank" rel="noopener noreferrer">{link.split('/').pop()}</a>
                      </li>
                    ))}
                </ul>
              </div>
            )}
            
            {sortedDersler.length > 0 && <h4>Çerçeve Öğretim Programları</h4>}
            <ul>
              {sortedDersler.map(([dersLink, dersData]) => {
                const siniflarSorted = [...dersData.siniflar].sort((a, b) => a - b);
                const sinifStr = siniflarSorted.join('-');
                const sinifDisplayStr = `(${sinifStr}. Sınıf)`;

                const ortakAlanlar = ortak_alan_indeksi[dersLink] || [];
                let ortakStr = '';
                if (ortakAlanlar.length > 1) {
                  ortakStr = ` (${ortakAlanlar.length} ortak alan)`;
                }

                return (
                  <li key={dersLink}>
                    {dersData.isim} <span className="sinif">{sinifDisplayStr}</span>
                    {ortakStr && <span className="ortak-alan">{ortakStr}</span>}
                    <a href={dersLink} target="_blank" rel="noopener noreferrer" className="ders-link">(Link)</a>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })
      ) : (
        <p>Arama kriterlerinize uygun alan bulunamadı.</p>
      )}
    </div>
  );
}

export default DataDisplay;
