import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './App.css';

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
          ... <button onClick={() => setIsExpanded(true)} className="expand-button">{'>>'}</button>
        </>
      )}
    </td>
  );
};

const PDFViewerSidebar = ({ pdfUrl, isOpen, onClose, courseTitle }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && pdfUrl) {
      setLoading(true);
      setError(null);
    }
  }, [isOpen, pdfUrl]);

  const handleIframeLoad = () => {
    setLoading(false);
  };

  const handleIframeError = () => {
    setLoading(false);
    setError('PDF yüklenemedi. URL erişilebilir değil veya dosya bulunamadı.');
  };

  if (!isOpen) return null;

  return (
    <div className="pdf-viewer-sidebar">
      <div className="pdf-sidebar-overlay" onClick={onClose}></div>
      <div className="pdf-sidebar-content">
        <div className="pdf-sidebar-header">
          <h3>Ders Materyali (DM)</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="pdf-course-info">
          <strong>{courseTitle}</strong>
          <div className="pdf-url">
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="external-link">
              🔗 Yeni sekmede aç
            </a>
          </div>
        </div>
        <div className="pdf-viewer-container">
          {loading && (
            <div className="pdf-loading">
              <div className="loading-spinner"></div>
              <p>PDF yükleniyor...</p>
            </div>
          )}
          {error && (
            <div className="pdf-error">
              <p>❌ {error}</p>
              <button onClick={() => window.open(pdfUrl, '_blank')} className="retry-btn">
                Yeni Sekmede Aç
              </button>
            </div>
          )}
          <iframe
            src={pdfUrl}
            width="100%"
            height="100%"
            title="Ders Materyali PDF Viewer"
            frameBorder="0"
            onLoad={handleIframeLoad}
            onError={handleIframeError}
            style={{ display: loading ? 'none' : 'block' }}
          />
        </div>
      </div>
    </div>
  );
};

const CourseEditSidebar = ({ course, isOpen, onClose, onSave, onShowPDF }) => {
  const [editData, setEditData] = useState({
    ders_adi: '',
    sinif: '',
    tum_siniflar: [],
    haftalik_ders_saati: '',
    amaç: '',
    alan_adi: '',
    dal_adi: '',
    ders_amaclari: [],
    arac_gerec: [],
    olcme_degerlendirme: [],
    ogrenme_birimleri: [],
    dbf_url: ''
  });

  useEffect(() => {
    if (course && isOpen) {
      setEditData({
        ders_adi: course.dersIsim || '',
        sinif: course.sinif || '', // Tek seçilen sınıf
        tum_siniflar: course.siniflar || [], // Tüm sınıflar referans için
        haftalik_ders_saati: '',
        amaç: '',
        alan_adi: course.alanIsim || '',
        dal_adi: '',
        ders_amaclari: [],
        arac_gerec: [],
        olcme_degerlendirme: [],
        ogrenme_birimleri: [],
        dbf_url: course.dersLink || '' // Bu aslında DM URL'si, ama mevcut yapı için koruyoruz
      });
    }
  }, [course, isOpen]);

  const handleInputChange = (field, value) => {
    setEditData(prev => ({ ...prev, [field]: value }));
  };

  const handleArrayAdd = (field, value) => {
    if (value.trim()) {
      setEditData(prev => ({
        ...prev,
        [field]: [...prev[field], value.trim()]
      }));
    }
  };

  const handleArrayRemove = (field, index) => {
    setEditData(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const handleSave = () => {
    onSave(editData);
    onClose();
  };

  console.log('CourseEditSidebar render:', { isOpen, course });
  
  if (!isOpen) return null;

  return (
    <div className="course-edit-sidebar">
      <div className="sidebar-overlay" onClick={onClose}></div>
      <div className="sidebar-content">
        <div className="sidebar-header">
          <h3>Ders Bilgilerini Düzenle</h3>
          <div className="header-buttons">
            {editData.dbf_url && (
              <button 
                className="pdf-view-btn" 
                onClick={() => onShowPDF && onShowPDF(editData.dbf_url, editData.ders_adi)}
                title="Ders Materyali PDF'i görüntüle"
              >
                📄 PDF Görüntüle
              </button>
            )}
            <button className="close-btn" onClick={onClose}>×</button>
          </div>
        </div>
        
        <div className="sidebar-body">
          <div className="form-section">
            <h4>Temel Bilgiler</h4>
            <div className="form-group">
              <label>Ders Adı:</label>
              <input
                type="text"
                value={editData.ders_adi}
                onChange={(e) => handleInputChange('ders_adi', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Sınıf:</label>
              <div className="sinif-selection">
                {editData.tum_siniflar.length > 1 ? (
                  <div className="sinif-buttons">
                    <p className="sinif-info">Bu ders {editData.tum_siniflar.join(', ')}. sınıflarda okutulmaktadır. Hangi sınıf için düzenliyorsunuz?</p>
                    {editData.tum_siniflar.map(sinif => (
                      <button
                        key={sinif}
                        type="button"
                        className={`sinif-btn ${editData.sinif === sinif ? 'active' : ''}`}
                        onClick={() => handleInputChange('sinif', sinif)}
                      >
                        {sinif}. Sınıf
                      </button>
                    ))}
                  </div>
                ) : (
                  <input
                    type="number"
                    value={editData.sinif}
                    onChange={(e) => handleInputChange('sinif', e.target.value)}
                    min="9"
                    max="12"
                    placeholder="Sınıf (örn: 10)"
                  />
                )}
              </div>
            </div>
            <div className="form-group">
              <label>Haftalık Ders Saati:</label>
              <input
                type="number"
                value={editData.haftalik_ders_saati}
                onChange={(e) => handleInputChange('haftalik_ders_saati', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Alan Adı:</label>
              <input
                type="text"
                value={editData.alan_adi}
                onChange={(e) => handleInputChange('alan_adi', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Dal Adı:</label>
              <input
                type="text"
                value={editData.dal_adi}
                onChange={(e) => handleInputChange('dal_adi', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Dersin Amacı:</label>
              <textarea
                value={editData.amaç}
                onChange={(e) => handleInputChange('amaç', e.target.value)}
                rows={4}
              />
            </div>
          </div>

          <div className="form-section">
            <h4>Araç-Gereç</h4>
            <ArrayInput
              items={editData.arac_gerec}
              onAdd={(value) => handleArrayAdd('arac_gerec', value)}
              onRemove={(index) => handleArrayRemove('arac_gerec', index)}
              placeholder="Araç-gereç ekle..."
            />
          </div>

          <div className="form-section">
            <h4>Ders Amaçları</h4>
            <ArrayInput
              items={editData.ders_amaclari}
              onAdd={(value) => handleArrayAdd('ders_amaclari', value)}
              onRemove={(index) => handleArrayRemove('ders_amaclari', index)}
              placeholder="Ders amacı ekle..."
            />
          </div>

          <div className="form-section">
            <h4>Ölçme ve Değerlendirme</h4>
            <ArrayInput
              items={editData.olcme_degerlendirme}
              onAdd={(value) => handleArrayAdd('olcme_degerlendirme', value)}
              onRemove={(index) => handleArrayRemove('olcme_degerlendirme', index)}
              placeholder="Ölçme yöntemi ekle..."
            />
          </div>

          <div className="form-section">
            <h4>Öğrenme Birimleri (Üniteler)</h4>
            <OgrenmeBirimiInput
              ogrenme_birimleri={editData.ogrenme_birimleri}
              onChange={(value) => handleInputChange('ogrenme_birimleri', value)}
            />
          </div>

          <div className="form-section">
            <h4>Ders Materyali URL</h4>
            <div className="form-group">
              <label>DM URL (Ders Materyali PDF):</label>
              <input
                type="url"
                value={editData.dbf_url}
                onChange={(e) => handleInputChange('dbf_url', e.target.value)}
                placeholder="Ders Materyali PDF URL'si (dmgoster.aspx'den)"
              />
              <small style={{color: '#666', fontSize: '12px'}}>
                Not: Bu alan şu an "dbf_url" adında ama aslında Ders Materyali URL'sini içeriyor
              </small>
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="btn-cancel" onClick={onClose}>İptal</button>
          <button className="btn-save" onClick={handleSave}>Kaydet</button>
        </div>
      </div>
    </div>
  );
};

const ArrayInput = ({ items, onAdd, onRemove, placeholder }) => {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = () => {
    if (inputValue.trim()) {
      onAdd(inputValue);
      setInputValue('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAdd();
    }
  };

  return (
    <div className="array-input">
      <div className="input-with-button">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
        />
        <button type="button" onClick={handleAdd}>+</button>
      </div>
      <div className="items-list">
        {items.map((item, index) => (
          <div key={index} className="item-tag">
            <span>{item}</span>
            <button onClick={() => onRemove(index)}>×</button>
          </div>
        ))}
      </div>
    </div>
  );
};

const OgrenmeBirimiInput = ({ ogrenme_birimleri, onChange }) => {
  const handleAddUnit = () => {
    const newUnit = {
      id: Date.now(),
      ogrenme_birimi: '',
      ders_saati: '',
      konular: []
    };
    onChange([...ogrenme_birimleri, newUnit]);
  };

  const handleRemoveUnit = (index) => {
    const updated = ogrenme_birimleri.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleUnitChange = (index, field, value) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === index ? { ...unit, [field]: value } : unit
    );
    onChange(updated);
  };

  const handleAddKonu = (unitIndex) => {
    const newKonu = {
      id: Date.now(),
      konu: '',
      kazanimlar: []
    };
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { ...unit, konular: [...unit.konular, newKonu] } : unit
    );
    onChange(updated);
  };

  const handleRemoveKonu = (unitIndex, konuIndex) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { 
        ...unit, 
        konular: unit.konular.filter((_, ki) => ki !== konuIndex) 
      } : unit
    );
    onChange(updated);
  };

  const handleKonuChange = (unitIndex, konuIndex, value) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { 
        ...unit, 
        konular: unit.konular.map((konu, ki) => 
          ki === konuIndex ? { ...konu, konu: value } : konu
        ) 
      } : unit
    );
    onChange(updated);
  };

  const handleAddKazanim = (unitIndex, konuIndex) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { 
        ...unit, 
        konular: unit.konular.map((konu, ki) => 
          ki === konuIndex ? { 
            ...konu, 
            kazanimlar: [...konu.kazanimlar, ''] 
          } : konu
        ) 
      } : unit
    );
    onChange(updated);
  };

  const handleRemoveKazanim = (unitIndex, konuIndex, kazanimIndex) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { 
        ...unit, 
        konular: unit.konular.map((konu, ki) => 
          ki === konuIndex ? { 
            ...konu, 
            kazanimlar: konu.kazanimlar.filter((_, kzi) => kzi !== kazanimIndex) 
          } : konu
        ) 
      } : unit
    );
    onChange(updated);
  };

  const handleKazanimChange = (unitIndex, konuIndex, kazanimIndex, value) => {
    const updated = ogrenme_birimleri.map((unit, i) => 
      i === unitIndex ? { 
        ...unit, 
        konular: unit.konular.map((konu, ki) => 
          ki === konuIndex ? { 
            ...konu, 
            kazanimlar: konu.kazanimlar.map((kazanim, kzi) => 
              kzi === kazanimIndex ? value : kazanim
            ) 
          } : konu
        ) 
      } : unit
    );
    onChange(updated);
  };

  return (
    <div className="ogrenme-birimi-input">
      <button type="button" onClick={handleAddUnit} className="add-unit-btn">
        + Öğrenme Birimi Ekle
      </button>
      
      {ogrenme_birimleri.map((unit, unitIndex) => (
        <div key={unit.id} className="unit-card">
          <div className="unit-header">
            <h5>Öğrenme Birimi {unitIndex + 1}</h5>
            <button 
              type="button" 
              onClick={() => handleRemoveUnit(unitIndex)}
              className="remove-btn"
            >
              ×
            </button>
          </div>
          
          <div className="unit-content">
            <div className="form-row">
              <div className="form-group">
                <label>Öğrenme Birimi Adı:</label>
                <input
                  type="text"
                  value={unit.ogrenme_birimi}
                  onChange={(e) => handleUnitChange(unitIndex, 'ogrenme_birimi', e.target.value)}
                  placeholder="Örn: Kuruma Giriş ve Çıkış İşlemleri"
                />
              </div>
              <div className="form-group">
                <label>Ders Saati:</label>
                <input
                  type="number"
                  value={unit.ders_saati}
                  onChange={(e) => handleUnitChange(unitIndex, 'ders_saati', e.target.value)}
                  placeholder="Örn: 36"
                />
              </div>
            </div>

            <div className="konular-section">
              <div className="section-header">
                <h6>Konular</h6>
                <button 
                  type="button" 
                  onClick={() => handleAddKonu(unitIndex)}
                  className="add-konu-btn"
                >
                  + Konu Ekle
                </button>
              </div>

              {unit.konular.map((konu, konuIndex) => (
                <div key={konu.id} className="konu-card">
                  <div className="konu-header">
                    <label>Konu {konuIndex + 1}:</label>
                    <button 
                      type="button" 
                      onClick={() => handleRemoveKonu(unitIndex, konuIndex)}
                      className="remove-btn"
                    >
                      ×
                    </button>
                  </div>
                  <input
                    type="text"
                    value={konu.konu}
                    onChange={(e) => handleKonuChange(unitIndex, konuIndex, e.target.value)}
                    placeholder="Örn: Güvenlik Standartları Bakımından Ceza İnfaz Kurumları"
                  />

                  <div className="kazanimlar-section">
                    <div className="section-header">
                      <label>Kazanımlar</label>
                      <button 
                        type="button" 
                        onClick={() => handleAddKazanim(unitIndex, konuIndex)}
                        className="add-kazanim-btn"
                      >
                        + Kazanım Ekle
                      </button>
                    </div>

                    {konu.kazanimlar.map((kazanim, kazanimIndex) => (
                      <div key={kazanimIndex} className="kazanim-input">
                        <textarea
                          value={kazanim}
                          onChange={(e) => handleKazanimChange(unitIndex, konuIndex, kazanimIndex, e.target.value)}
                          placeholder="Örn: Güvenlik standartları bakımından ceza infaz kurumlarını sınıflandırarak bunların ayrımını yapar."
                          rows={2}
                        />
                        <button 
                          type="button" 
                          onClick={() => handleRemoveKazanim(unitIndex, konuIndex, kazanimIndex)}
                          className="remove-btn"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const DataTable = ({ data, searchTerm, onCourseEdit }) => {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const flattenedData = useMemo(() => {
    if (!data || !data.alanlar) return [];
    
    const rows = [];
    Object.entries(data.alanlar).forEach(([alanId, alan]) => {
      if (alan.dersler) {
        Object.entries(alan.dersler).forEach(([dersLink, ders]) => {
          const ortakAlanIds = (data.ortak_alan_indeksi?.[dersLink] || []).filter(id => id !== alanId);
          const ortakAlanNames = ortakAlanIds.map(id => data.alanlar[id]?.isim || `ID: ${id}`);
          
          // Her sınıf için ayrı satır oluştur
          ders.siniflar.forEach(sinif => {
            rows.push({
              alanId,
              alanIsim: alan.isim,
              dersIsim: ders.isim,
              sinif: sinif, // Tek sınıf olarak
              siniflar: ders.siniflar, // Orijinal tüm sınıflar array'i
              dersLink,
              dbfPdfPath: ders.dbf_pdf_path,
              ortakAlanlar: ortakAlanNames.join(', ') || '-',
              ortakAlanSayisi: ortakAlanNames.length,
              uniqueKey: `${alanId}-${dersLink}-${sinif}` // Unique key for React
            });
          });
        });
      }
    });
    return rows;
  }, [data]);

  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return flattenedData;
    const term = searchTerm.trim().toLowerCase();
    return flattenedData.filter(row => 
      row.alanIsim.toLowerCase().includes(term) ||
      row.dersIsim.toLowerCase().includes(term)
    );
  }, [flattenedData, searchTerm]);

  const sortedData = useMemo(() => {
    if (!sortConfig.key) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) return '↕️';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  return (
    <div className="data-table-container">
      <div style={{ marginBottom: '10px' }}>
        <strong>Toplam: {sortedData.length} ders</strong>
      </div>
      <table className="comprehensive-data-table">
        <thead>
          <tr>
            <th onClick={() => handleSort('alanIsim')} style={{ cursor: 'pointer' }}>
              Alan {getSortIcon('alanIsim')}
            </th>
            <th onClick={() => handleSort('dersIsim')} style={{ cursor: 'pointer' }}>
              Ders Adı {getSortIcon('dersIsim')}
            </th>
            <th onClick={() => handleSort('sinif')} style={{ cursor: 'pointer' }}>
              Sınıfı {getSortIcon('sinif')}
            </th>
            <th>Ders Materyali (DM)</th>
            <th>DBF PDF</th>
            <th onClick={() => handleSort('ortakAlanSayisi')} style={{ cursor: 'pointer' }}>
              Okutulduğu Diğer Alanlar {getSortIcon('ortakAlanSayisi')}
            </th>
            <th>İşlemler</th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row) => (
            <tr key={row.uniqueKey}>
              <td>{row.alanIsim}</td>
              <td>{row.dersIsim}</td>
              <td>
                <span className="sinif-badge">{row.sinif}. Sınıf</span>
                {row.siniflar.length > 1 && (
                  <small className="other-classes">
                    (Ayrıca: {row.siniflar.filter(s => s !== row.sinif).join(', ')})
                  </small>
                )}
              </td>
              <td>
                <a href={row.dersLink} target="_blank" rel="noopener noreferrer" className="ders-link">
                  DM PDF
                </a>
              </td>
              <td>
                {row.dbfPdfPath ? (
                  <a
                    href={`file://${row.dbfPdfPath}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="dbf-link"
                  >
                    {row.dbfPdfPath.split('/').pop()}
                  </a>
                ) : (
                  "-"
                )}
              </td>
              <td className="ortak-alanlar-cell">
                {row.ortakAlanlar}
              </td>
              <td>
                <button 
                  className="edit-btn" 
                  onClick={() => onCourseEdit && onCourseEdit(row)}
                  title="Düzenle"
                >
                  ✏️
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
                  <th>Ders Materyali (DM)</th>
                  <th>DBF PDF</th>
                  <th>Okutulduğu Diğer Alanlar</th>
                </tr>
              </thead>
              <tbody>
                {sortedDersler.map(([link, ders]) => (
                  <tr key={link}>
                    <td>{alan.isim}</td>
                    <td>{ders.isim}</td>
                    <td>{ders.siniflar.join('-')}</td>
                    <td><a href={link} target="_blank" rel="noopener noreferrer" className="ders-link">DM PDF</a></td>
                    <td>
                      {ders.dbf_pdf_path ? (
                        <a
                          href={`file://${ders.dbf_pdf_path}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="dbf-link"
                        >
                          {ders.dbf_pdf_path.split('/').pop()}
                        </a>
                      ) : (
                        "-"
                      )}
                    </td>
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
  const [viewMode, setViewMode] = useState('card'); // 'card' or 'table'
  const [editingSidebar, setEditingSidebar] = useState({ isOpen: false, course: null });
  const [editedCourses, setEditedCourses] = useState(new Map()); // Store edited course data
  const [pdfSidebar, setPdfSidebar] = useState({ isOpen: false, url: '', title: '' });

  // Kategorik veri state'leri
  const [dbfData, setDbfData] = useState(null);
  const [copData, setCopData] = useState(null);
  const [dmData, setDmData] = useState(null);
  const [bomData, setBomData] = useState(null);
  const [catLoading, setCatLoading] = useState(""); // "dbf", "cop", "dm", "bom"
  const [catError, setCatError] = useState("");

  // DBF rar indir/aç state'leri
  const [dbfUnrarLoading, setDbfUnrarLoading] = useState(false);
  const [dbfUnrarError, setDbfUnrarError] = useState("");

  // Debouncing efekti: Kullanıcı yazmayı bıraktıktan 300ms sonra arama terimini günceller.
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

  // Veri çekme fonksiyonu - artık direkt veritabanına kaydediyor
  const handleScrape = useCallback(() => {
    if (data && !window.confirm('Veriler zaten mevcut. En güncel verileri çekmek ve veritabanına kaydetmek istediğinize emin misiniz? Bu işlem biraz zaman alabilir.')) {
      return;
    }
    setData(null);
    setProgress([]);
    setError(null);
    setLoading(true);

    const eventSource = new EventSource('http://localhost:5001/api/scrape-to-db');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);

      if (eventData.type === 'done') {
        // Veri çekme tamamlandı, önbellekten tekrar yükle
        fetchCachedData();
        setProgress(prev => [...prev, eventData]);
        eventSource.close();
        setLoading(false);
      } else {
        setProgress(prev => [...prev, eventData]);
      }
    };

    eventSource.onerror = () => {
      setError("Veri akışı sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      eventSource.close();
      setLoading(false);
    };

    return () => {
      eventSource.close();
    };
  }, [data]);

  const fetchCachedData = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/get-cached-data');
      if (!response.ok) {
        throw new Error(`Önbellek sunucusundan yanıt alınamadı: ${response.statusText}`);
      }
      const cachedData = await response.json();
      if (cachedData && cachedData.alanlar && Object.keys(cachedData.alanlar).length > 0) {
        setData(cachedData);
        setProgress(prev => [...prev, { message: "Önbellekten veriler başarıyla yüklendi.", type: 'done' }]);
      }
    } catch (e) {
      console.error("Önbellek verisi çekme hatası:", e);
      setError(`Önbellek verisi çekilemedi. Backend sunucusunun çalıştığından emin olun. Hata: ${e.message}`);
    }
  };

  // DBF Dosyalarını indirip açan fonksiyon
  const handleDbfUnrar = useCallback(() => {
    setDbfUnrarLoading(true);
    setDbfUnrarError("");
    setProgress([]);
    setError(null);

    const eventSource = new EventSource("http://localhost:5001/api/dbf-download-extract");

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        setProgress(prev => [...prev, eventData]);
        if (eventData.type === "done") {
          setDbfUnrarLoading(false);
          eventSource.close();
        }
        if (eventData.type === "error") {
          setDbfUnrarError(eventData.message || "Bilinmeyen hata");
        }
      } catch (e) {
        setDbfUnrarError("Veri işlenemedi: " + e.message);
      }
    };

    eventSource.onerror = (err) => {
      setDbfUnrarError("Bağlantı hatası veya sunucu yanıt vermiyor.");
      setDbfUnrarLoading(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // Kategori veri çekme fonksiyonları
  const fetchDbf = async () => {
    setCatLoading("dbf");
    setCatError("");
    try {
      const res = await fetch("http://localhost:5001/api/get-dbf");
      if (!res.ok) throw new Error("DBF verisi alınamadı");
      const json = await res.json();
      setDbfData(json);
    } catch (e) {
      setCatError("DBF: " + e.message);
    } finally {
      setCatLoading("");
    }
  };
  const fetchCop = async () => {
    setCatLoading("cop");
    setCatError("");
    try {
      const res = await fetch("http://localhost:5001/api/get-cop");
      if (!res.ok) throw new Error("ÇÖP verisi alınamadı");
      const json = await res.json();
      setCopData(json);
    } catch (e) {
      setCatError("ÇÖP: " + e.message);
    } finally {
      setCatLoading("");
    }
  };
  const fetchDm = async () => {
    setCatLoading("dm");
    setCatError("");
    try {
      const res = await fetch("http://localhost:5001/api/get-dm");
      if (!res.ok) throw new Error("Ders Materyali verisi alınamadı");
      const json = await res.json();
      setDmData(json);
    } catch (e) {
      setCatError("DM: " + e.message);
    } finally {
      setCatLoading("");
    }
  };
  const fetchBom = async () => {
    setCatLoading("bom");
    setCatError("");
    try {
      const res = await fetch("http://localhost:5001/api/get-bom");
      if (!res.ok) throw new Error("BOM verisi alınamadı");
      const json = await res.json();
      setBomData(json);
    } catch (e) {
      setCatError("BOM: " + e.message);
    } finally {
      setCatLoading("");
    }
  };

  // Alanları isme göre sıralamak için bir yardımcı fonksiyon
  const getSortedAlans = useCallback((alanlar) => {
    if (!alanlar) return [];
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

  // Course editing functions
  const handleCourseEdit = useCallback((course) => {
    console.log('handleCourseEdit called with:', course);
    setEditingSidebar({ isOpen: true, course });
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setEditingSidebar({ isOpen: false, course: null });
  }, []);

  const handleShowPDF = useCallback((url, title) => {
    setPdfSidebar({ isOpen: true, url, title });
  }, []);

  const handleClosePDFSidebar = useCallback(() => {
    setPdfSidebar({ isOpen: false, url: '', title: '' });
  }, []);

  const handleSaveCourse = useCallback((editedData) => {
    const courseKey = `${editedData.alan_adi}-${editedData.ders_adi}-${editedData.sinif}`;
    setEditedCourses(prev => new Map(prev.set(courseKey, editedData)));
    
    // Show success message
    setProgress(prev => [...prev, { 
      type: 'success', 
      message: `"${editedData.ders_adi}" dersi düzenlendi ve kaydedildi.` 
    }]);
  }, []);

  const handleExportToDatabase = useCallback(async () => {
    if (editedCourses.size === 0) {
      setProgress(prev => [...prev, { 
        type: 'warning', 
        message: 'Veritabanına aktarılacak düzenlenmiş ders bulunamadı.' 
      }]);
      return;
    }

    try {
      const exportData = Array.from(editedCourses.values());
      
      setProgress(prev => [...prev, { 
        type: 'status', 
        message: `${exportData.length} ders veritabanına aktarılıyor...` 
      }]);
      
      // Gerçek API çağrısı
      const response = await fetch('http://localhost:5001/api/save-courses-to-db', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          courses: exportData
        })
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || 'Sunucu hatası');
      }
      
      // Başarı mesajı
      setProgress(prev => [...prev, { 
        type: 'done', 
        message: result.message || `${result.success} ders başarıyla kaydedildi!`
      }]);
      
      // Detaylı sonuçları göster
      if (result.results && result.results.length > 0) {
        result.results.forEach(res => {
          if (res.status === 'error') {
            setProgress(prev => [...prev, { 
              type: 'error', 
              message: `❌ ${res.course}: ${res.message}` 
            }]);
          } else {
            setProgress(prev => [...prev, { 
              type: 'success', 
              message: `✅ ${res.course}: Başarıyla kaydedildi (ID: ${res.ders_id})` 
            }]);
          }
        });
      }
      
      // Başarılı kayıtları temizle
      if (result.success > 0) {
        const successfulCourses = result.results
          .filter(r => r.status === 'success')
          .map(r => r.course);
        
        setEditedCourses(prev => {
          const newMap = new Map(prev);
          for (const [key, course] of newMap.entries()) {
            if (successfulCourses.includes(course.ders_adi)) {
              newMap.delete(key);
            }
          }
          return newMap;
        });
      }
      
    } catch (error) {
      setProgress(prev => [...prev, { 
        type: 'error', 
        message: `Veritabanına aktarım hatası: ${error.message}` 
      }]);
    }
  }, [editedCourses]);
  
  return (
    <div className="App">
      <h1>meslek.meb (alan-dal-ders) dosyalar</h1>
      <button onClick={handleScrape} disabled={loading || initialLoading}>
        {loading
          ? 'Veriler Çekiliyor ve Veritabanına Kaydediliyor...'
          : data
            ? 'Verileri Yeniden Çek ve Veritabanına Kaydet'
            : 'Verileri Çek ve Veritabanına Kaydet'}
      </button>

      {/* Kategorik veri çekme butonları */}
      <div style={{ margin: "20px 0" }}>
        <button onClick={fetchDbf} disabled={catLoading === "dbf"}>Ders Bilgi Formu (DBF) Getir</button>{" "}
        <button onClick={fetchCop} disabled={catLoading === "cop"}>Çerçeve Öğretim Programı (ÇÖP) Getir</button>{" "}
        <button onClick={fetchDm} disabled={catLoading === "dm"}>Ders Materyali (DM) Getir</button>{" "}
        <button onClick={fetchBom} disabled={catLoading === "bom"}>Bireysel Öğrenme Materyali (BOM) Getir</button>{" "}
        <button onClick={handleDbfUnrar} disabled={dbfUnrarLoading} style={{ background: "#e67e22", color: "white" }}>
          {dbfUnrarLoading ? "DBF Dosyaları İndiriliyor/Açılıyor..." : "DBF Dosyalarını İndir ve Aç"}
        </button>{" "}
        <button
          onClick={async () => {
            setProgress(prev => [...prev, { type: "status", message: "DBF eşleştirmesi başlatıldı..." }]);
            try {
              const res = await fetch("http://localhost:5001/api/dbf-match-refresh", { method: "POST" });
              const result = await res.json();
              setProgress(prev => [...prev, result]);
            } catch (e) {
              setProgress(prev => [...prev, { type: "error", message: "Eşleştirme isteği başarısız: " + e.message }]);
            }
          }}
          style={{ background: "#16a085", color: "white" }}
        >
          DBF Eşleştirmesini Güncelle
        </button>{" "}
        <button
          onClick={() => {
            setProgress([]);
            setError(null);
            const eventSource = new EventSource("http://localhost:5001/api/dbf-retry-extract-all");
            eventSource.onmessage = (event) => {
              try {
                const eventData = JSON.parse(event.data);
                setProgress(prev => [...prev, eventData]);
                if (eventData.type === "done") {
                  eventSource.close();
                }
              } catch (e) {
                setProgress(prev => [...prev, { type: "error", message: "Veri işlenemedi: " + e.message }]);
              }
            };
            eventSource.onerror = (err) => {
              setProgress(prev => [...prev, { type: "error", message: "Bağlantı hatası veya sunucu yanıt vermiyor." }]);
              eventSource.close();
            };
          }}
          style={{ background: "#2980b9", color: "white" }}
        >
          Tüm İndirilenleri Tekrar Aç
        </button>{" "}
        <button
          onClick={async () => {
            setProgress(prev => [...prev, { type: "status", message: "DBF eşleştirmesi başlatıldı..." }]);
            try {
              const res = await fetch("http://localhost:5001/api/dbf-match-refresh", { method: "POST" });
              const result = await res.json();
              setProgress(prev => [...prev, result]);
            } catch (e) {
              setProgress(prev => [...prev, { type: "error", message: "Eşleştirme isteği başarısız: " + e.message }]);
            }
          }}
          style={{ background: "#16a085", color: "white" }}
        >
          DBF Eşleştirmesini Güncelle
        </button>
        <button
          onClick={handleExportToDatabase}
          disabled={editedCourses.size === 0}
          style={{ 
            background: editedCourses.size > 0 ? "#e74c3c" : "#bdc3c7", 
            color: "white",
            marginLeft: "10px"
          }}
          title={`${editedCourses.size} düzenlenmiş ders veritabanına aktar`}
        >
          Veritabanına Aktar ({editedCourses.size})
        </button>
        {(catLoading || dbfUnrarLoading) && <span style={{ marginLeft: 10 }}>Yükleniyor...</span>}
        {catError && <span style={{ color: "red", marginLeft: 10 }}>{catError}</span>}
        {dbfUnrarError && <span style={{ color: "red", marginLeft: 10 }}>{dbfUnrarError}</span>}
      </div>

      {/* Arama Kutusu ve Görünüm Seçenekleri */}
      {!initialLoading && data && (
        <div className="search-and-view-controls" style={{ marginBottom: '20px' }}>
          <div className="search-bar" style={{ marginBottom: '10px' }}>
            <input
              type="text"
              placeholder="Filtrelemek için alan adı girin..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="view-mode-toggle">
            <button 
              onClick={() => setViewMode('card')} 
              className={viewMode === 'card' ? 'active' : ''}
              style={{ 
                marginRight: '10px', 
                backgroundColor: viewMode === 'card' ? '#007bff' : '#f8f9fa',
                color: viewMode === 'card' ? 'white' : 'black',
                border: '1px solid #ccc',
                padding: '8px 16px',
                cursor: 'pointer'
              }}
            >
              Kart Görünümü
            </button>
            <button 
              onClick={() => setViewMode('table')} 
              className={viewMode === 'table' ? 'active' : ''}
              style={{ 
                backgroundColor: viewMode === 'table' ? '#007bff' : '#f8f9fa',
                color: viewMode === 'table' ? 'white' : 'black',
                border: '1px solid #ccc',
                padding: '8px 16px',
                cursor: 'pointer'
              }}
            >
              Tablo Görünümü
            </button>
          </div>
        </div>
      )}

      {/* İlerleme ve Hata Mesajları Alanı */}
      {(loading || progress.length > 0 || error) && (
        <div id="progress-container" style={{ border: '1px solid #ccc', padding: '10px', marginTop: '10px', height: '300px', overflowY: 'scroll', backgroundColor: '#f8f9fa' }}>
          {initialLoading && <p>Önbellek kontrol ediliyor...</p>}
          {error && <p style={{ color: 'red', fontWeight: 'bold' }}>HATA: {error}</p>}
          {progress.map((p, index) => {
            // Hata mesajından alan_adi ve rar_filename çıkarılabiliyorsa buton ekle
            let retryButton = null;
            if (p.type === 'error' && p.message) {
              // [ALAN] dosyaadı.rar ... şeklinde başlıyor mu?
              const match = p.message.match(/^\[([^\]]+)\].*?([^\s\/]+\.rar|[^\s\/]+\.zip)/i);
              if (match) {
                const alan_adi = match[1];
                const rar_filename = match[2];
                retryButton = (
                  <button
                    style={{ marginLeft: 8, fontSize: 12, padding: "2px 6px" }}
                    onClick={async () => {
                      try {
                        const res = await fetch("http://localhost:5001/api/dbf-retry-extract", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ alan_adi, rar_filename })
                        });
                        const result = await res.json();
                        // Sonucu progress'e ekle
                        setProgress(prev => [...prev, result]);
                      } catch (e) {
                        setProgress(prev => [...prev, { type: "error", message: "Tekrar deneme isteği başarısız: " + e.message }]);
                      }
                    }}
                  >
                    Tekrar Dene
                  </button>
                );
              }
            }
            return (
              <div key={index} style={{ color: p.type === 'error' ? 'red' : p.type === 'warning' ? '#e67e22' : 'black' }}>
                <p style={{ margin: '2px 0' }}>
                  {p.message}
                  {retryButton}
                </p>
                {p.estimation && <small><i>{p.estimation}</i></small>}
              </div>
            );
          })}
        </div>
      )}

      {/* Kategorik veri görüntüleme alanları */}
      <div style={{ margin: "20px 0" }}>
        {dbfData && (
          <div>
            <h2>Ders Bilgi Formu (DBF) Verisi</h2>
            <pre style={{ maxHeight: 300, overflow: "auto", background: "#f4f4f4", padding: 10 }}>{JSON.stringify(dbfData, null, 2)}</pre>
          </div>
        )}
        {copData && (
          <div>
            <h2>Çerçeve Öğretim Programı (ÇÖP) Verisi</h2>
            <pre style={{ maxHeight: 300, overflow: "auto", background: "#f4f4f4", padding: 10 }}>{JSON.stringify(copData, null, 2)}</pre>
          </div>
        )}
        {dmData && (
          <div>
            <h2>Ders Materyali (DM) Verisi</h2>
            <pre style={{ maxHeight: 300, overflow: "auto", background: "#f4f4f4", padding: 10 }}>{JSON.stringify(dmData, null, 2)}</pre>
          </div>
        )}
        {bomData && (
          <div>
            <h2>Bireysel Öğrenme Materyali (BOM) Verisi</h2>
            <pre style={{ maxHeight: 300, overflow: "auto", background: "#f4f4f4", padding: 10 }}>{JSON.stringify(bomData, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Veri görüntüleme alanı */}
      {!initialLoading && data && (
        <div className="data-display">
          {viewMode === 'table' ? (
            <div>
              <h2>Tablo Görünümü</h2>
              <DataTable data={data} searchTerm={debouncedTerm} onCourseEdit={handleCourseEdit} />
            </div>
          ) : (
            <div>
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
      )}

      {/* Course Edit Sidebar */}
      <CourseEditSidebar
        course={editingSidebar.course}
        isOpen={editingSidebar.isOpen}
        onClose={handleCloseSidebar}
        onSave={handleSaveCourse}
        onShowPDF={handleShowPDF}
      />

      {/* PDF Viewer Sidebar */}
      <PDFViewerSidebar
        pdfUrl={pdfSidebar.url}
        isOpen={pdfSidebar.isOpen}
        onClose={handleClosePDFSidebar}
        courseTitle={pdfSidebar.title}
      />
    </div>
  );
}

export default App;
