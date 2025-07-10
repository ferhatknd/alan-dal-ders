import React, { useState, useMemo, useEffect } from 'react';

import './DataDisplay.css';

function DataDisplay({ scrapedData }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
  const [expandedRows, setExpandedRows] = useState(new Set());

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
    const term = debouncedTerm.trim().toLowerCase();
    if (!term) {
      return []; // Arama yoksa, özel başlık gösterme
    }
    return sortedAlanlar.filter(([, alanData]) =>
      alanData.isim.toLowerCase().includes(term)
    );
  }, [debouncedTerm, sortedAlanlar]);

  // Tüm benzersiz dersleri tek bir listede topla
  const allUniqueDersler = useMemo(() => {
    if (!alanlar) return [];
    const dersMap = new Map();
    Object.values(alanlar).forEach(alanData => {
      Object.entries(alanData.dersler).forEach(([dersLink, dersDetay]) => {
        if (!dersMap.has(dersLink)) {
          dersMap.set(dersLink, {
            ...dersDetay,
            link: dersLink,
            alanlar: new Set()
          });
        }
        dersMap.get(dersLink).alanlar.add(alanData.isim);
      });
    });
    return Array.from(dersMap.values()).sort((a, b) => a.isim.localeCompare(b.isim, 'tr'));
  }, [alanlar]);

  // Arama sonucuna göre dersleri filtrele
  const filteredDersler = useMemo(() => {
    if (filteredAlanlar.length !== 1) {
      return allUniqueDersler; // Arama yoksa veya birden çok sonuç varsa tüm dersleri göster
    }
    const [alanId] = filteredAlanlar[0];
    const alanDersLinkleri = new Set(Object.keys(alanlar[alanId].dersler));
    return allUniqueDersler.filter(ders => alanDersLinkleri.has(ders.link));
  }, [filteredAlanlar, allUniqueDersler, alanlar]);

  if (!alanlar) {
    return <p>Görüntülenecek veri yok.</p>;
  }

  const renderAlanBaslik = () => {
    if (filteredAlanlar.length !== 1) return null;
    const [alanId, alanData] = filteredAlanlar[0];
    const dersSayisi = Object.keys(alanData.dersler).length;
    return (
      <div className="alan-baslik">
        <strong>{alanData.isim}</strong>
        <span className="separator">|</span>
        <span>Kod: {alanId}</span>
        <span className="separator">|</span>
        <span>Ders Sayısı: {dersSayisi}</span>
        <span className="separator">|</span>
        <span>DBF: </span>
        {alanData.dbf_links && Object.keys(alanData.dbf_links).length > 0
          ? Object.entries(alanData.dbf_links)
              .sort(([sinifA], [sinifB]) => parseInt(sinifA) - parseInt(sinifB))
              .map(([sinif, link]) => (
                <a key={sinif} href={link} target="_blank" rel="noopener noreferrer" className="dbf-link">
                  {sinif}
                </a>
              ))
          : 'N/A'}
      </div>
    );
  };

  return (
    <div className="data-container">
      <h2>Alan ve Ders Kataloğu</h2>
      <div className="search-bar">
        <input type="text" placeholder="Filtrelemek için alan adı girin..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
      </div>
      
      {renderAlanBaslik()}

      {filteredDersler.length > 0 ? (
        <table className="ders-table">
          <thead>
            <tr>
              <th>Ders Adı</th>
              <th>Okutulduğu Yıl(lar)</th>
              <th>Ait Olduğu Alan(lar)</th>
              <th>PDF</th>
            </tr>
          </thead>
          <tbody>
            {filteredDersler.map((ders) => {
              const siniflarSorted = [...ders.siniflar].sort((a, b) => a - b);
              const sinifStr = siniflarSorted.join('-');
              const alanlarStr = [...ders.alanlar].join(', ');
              const isExpanded = expandedRows.has(ders.link);
              const isLong = alanlarStr.length > 30;

              const toggleExpand = () => {
                setExpandedRows(prev => {
                  const newSet = new Set(prev);
                  if (newSet.has(ders.link)) {
                    newSet.delete(ders.link);
                  } else {
                    newSet.add(ders.link);
                  }
                  return newSet;
                });
              };

              return (
                <tr key={ders.link}>
                  <td>{ders.isim}</td>
                  <td>{sinifStr}. Sınıf</td>
                  <td>
                    {isLong && !isExpanded
                      ? `${alanlarStr.substring(0, 30)}... `
                      : `${alanlarStr} `}
                    {isLong && (
                      <button onClick={toggleExpand} className="expand-btn">
                        {isExpanded ? '<<' : '>>'}
                      </button>
                    )}
                  </td>
                  <td>
                    <a href={ders.link} target="_blank" rel="noopener noreferrer" className="ders-link">
                      İndir
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p>Arama kriterlerinize uygun alan bulunamadı.</p>
      )}
    </div>
  );
}

export default DataDisplay;
