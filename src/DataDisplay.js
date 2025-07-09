import React from 'react';
import './DataDisplay.css';

function DataDisplay({ scrapedData }) {
  if (!scrapedData || !scrapedData.alanlar) {
    return <p>Görüntülenecek veri yok.</p>;
  }

  const { alanlar, ortak_alan_indeksi } = scrapedData;

  // Alanları isme göre sıralamak için bir diziye dönüştür
  const sortedAlanlar = Object.entries(alanlar).sort(([, a], [, b]) =>
    a.isim.localeCompare(b.isim, 'tr')
  );

  return (
    <div className="data-container">
      <h2>Çekilen Veriler</h2>
      {sortedAlanlar.map(([alanId, alanData]) => {
        // Dersleri isme göre sırala
        const sortedDersler = Object.entries(alanData.dersler).sort(([, a], [, b]) =>
          a.isim.localeCompare(b.isim, 'tr')
        );

        return (
          <div key={alanId} className="alan-block">
            <h3>{alanData.isim} ({alanId})</h3>
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
      })}
    </div>
  );
}

export default DataDisplay;