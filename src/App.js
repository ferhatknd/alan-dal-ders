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
    <div className="pdf-viewer-sidebar-independent">
      <div className="pdf-sidebar-overlay" onClick={onClose}></div>
      <div className="pdf-sidebar-content">
        <div className="pdf-sidebar-header">
          <h3>PDF Viewer</h3>
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
            title="PDF Viewer"
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

// COP Dropdown Bileşeni
const CopDropdown = ({ copUrls, onSelectCop }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  if (!copUrls || Object.keys(copUrls).length === 0) {
    return null;
  }
  
  const copList = Object.entries(copUrls).map(([key, url]) => ({
    label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : key,
    url: url,
    key: key
  }));
  
  return (
    <div className="cop-dropdown" style={{ position: 'relative', display: 'inline-block' }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '8px 12px',
          background: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '12px',
          fontWeight: 'bold'
        }}
      >
        ÇÖP PDF ({copList.length}) {isOpen ? '▲' : '▼'}
      </button>
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          background: 'white',
          border: '1px solid #ccc',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          zIndex: 1000,
          minWidth: '140px'
        }}>
          {copList.map(item => (
            <button
              key={item.key}
              onClick={() => {
                onSelectCop(item.url, `ÇÖP - ${item.label}`);
                setIsOpen(false);
              }}
              style={{
                display: 'block',
                width: '100%',
                padding: '8px 12px',
                background: 'none',
                border: 'none',
                textAlign: 'left',
                cursor: 'pointer',
                fontSize: '12px',
                borderBottom: '1px solid #f0f0f0'
              }}
              onMouseOver={(e) => e.target.style.background = '#f8f9fa'}
              onMouseOut={(e) => e.target.style.background = 'none'}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const CourseEditSidebar = ({ course, isOpen, onClose, onSave, onShowPDF }) => {
  const [editData, setEditData] = useState({
    ders_id: '',
    ders_adi: '',
    sinif: '',
    ders_saati: '',
    alan_id: '',
    dal_id: '',
    dm_url: '',
    dbf_url: '',
    bom_url: '',
    amac: ''
  });
  
  const [alanDalOptions, setAlanDalOptions] = useState({ alanlar: [], dallar: {} });
  const [pdfPreview, setPdfPreview] = useState({ isOpen: false, url: '', title: '' });
  const [copUrls, setCopUrls] = useState({});

  // Alan-Dal seçeneklerini yükle
  useEffect(() => {
    if (isOpen) {
      fetch('http://localhost:5001/api/alan-dal-options')
        .then(res => res.json())
        .then(data => {
          setAlanDalOptions(data);
          // Parse all COP URLs when data is loaded
          if (data.alanlar) {
            const allCopUrls = parseAllCopUrls(data.alanlar);
            // Set initial COP URLs based on current alan_id
            if (editData.alan_id && allCopUrls[editData.alan_id]) {
              setCopUrls(allCopUrls[editData.alan_id]);
            }
          }
        })
        .catch(err => console.error('Alan-Dal seçenekleri yüklenirken hata:', err));
    }
  }, [isOpen]);

  useEffect(() => {
    if (course && isOpen) {
      setEditData({
        ders_id: course.ders_id || '',
        ders_adi: course.ders_adi || '',
        sinif: course.sinif || '',
        ders_saati: course.ders_saati || '',
        alan_id: course.alan_id || '',
        dal_id: course.dal_id || '',
        dm_url: course.dm_url || '',
        dbf_url: course.dbf_url || '',
        bom_url: course.bom_url || '',
        amac: course.amac || ''
      });
    }
  }, [course, isOpen]);

  const handleInputChange = (field, value) => {
    setEditData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(editData);
    onClose();
  };

  const handleCopy = async () => {
    if (!editData.alan_id || !editData.dal_id) {
      alert('Kopyalamak için hedef alan ve dal seçiniz');
      return;
    }

    try {
      const response = await fetch('http://localhost:5001/api/copy-course', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_ders_id: course.ders_id,
          target_alan_id: editData.alan_id,
          target_dal_id: editData.dal_id,
          ders_data: editData
        })
      });

      const result = await response.json();
      if (response.ok) {
        alert('Ders başarıyla kopyalandı!');
        onClose();
      } else {
        alert('Hata: ' + result.error);
      }
    } catch (error) {
      alert('Kopyalama hatası: ' + error.message);
    }
  };

  const openPdfPreview = (url, title) => {
    setPdfPreview({ isOpen: true, url, title });
  };

  const closePdfPreview = () => {
    setPdfPreview({ isOpen: false, url: '', title: '' });
  };

  // Parse all COP URLs from alanlar data
  const parseAllCopUrls = (alanlarData) => {
    const copUrlsMap = {};
    alanlarData.forEach(alan => {
      if (alan.cop_url) {
        try {
          const copData = JSON.parse(alan.cop_url);
          copUrlsMap[alan.id] = copData;
        } catch (e) {
          // If not JSON, treat as single URL
          copUrlsMap[alan.id] = { 'cop_url': alan.cop_url };
        }
      }
    });
    return copUrlsMap;
  };

  // Alan değiştiğinde dal listesini güncelle ve COP URLs'leri parse et
  const handleAlanChange = (alanId) => {
    setEditData(prev => ({ ...prev, alan_id: alanId, dal_id: '' }));
    
    // Parse COP URLs for the selected alan
    const selectedAlan = alanDalOptions.alanlar.find(alan => alan.id === parseInt(alanId));
    if (selectedAlan && selectedAlan.cop_url) {
      try {
        const copData = JSON.parse(selectedAlan.cop_url);
        setCopUrls(copData);
      } catch (e) {
        // If not JSON, treat as single URL
        setCopUrls({ 'cop_url': selectedAlan.cop_url });
      }
    } else {
      setCopUrls({});
    }
  };

  // Handle COP PDF selection
  const handleCopSelect = (pdfUrl, title) => {
    onShowPDF(pdfUrl, title);
  };

  console.log('CourseEditSidebar render:', { isOpen, course });
  
  if (!isOpen) return null;

  return (
    <>
      <div className="course-edit-sidebar">
        <div className="sidebar-overlay" onClick={onClose}></div>
        <div className="sidebar-content">
          <div className="sidebar-header">
            <div className="header-title">
              <h3>{editData.ders_adi || 'Ders Adı'}</h3>
              <div className="pdf-links">
                {editData.dm_url && (
                  <button onClick={() => openPdfPreview(editData.dm_url, 'DM')}>DM</button>
                )}
                {editData.dbf_url && (
                  <button onClick={() => openPdfPreview(editData.dbf_url, 'DBF')}>DBF</button>
                )}
                {editData.bom_url && (
                  <button onClick={() => openPdfPreview(editData.bom_url, 'BOM')}>BOM</button>
                )}
              </div>
            </div>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>
          
          <div className="sidebar-body">
            {/* Alan-Dal Seçimi */}
            <div className="form-section">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <MaterialTextField
                  label="Alan"
                  value={editData.alan_id}
                  onChange={(value) => handleAlanChange(value)}
                  select={true}
                  options={alanDalOptions.alanlar.map(alan => ({
                    value: alan.id,
                    label: alan.adi
                  }))}
                />
                
                <CopDropdown 
                  copUrls={copUrls} 
                  onSelectCop={handleCopSelect}
                />
              </div>
              
              <MaterialTextField
                label="Dal"
                value={editData.dal_id}
                onChange={(value) => handleInputChange('dal_id', value)}
                select={true}
                disabled={!editData.alan_id}
                options={editData.alan_id ? (alanDalOptions.dallar[editData.alan_id] || []).map(dal => ({
                  value: dal.id,
                  label: dal.adi
                })) : []}
              />
            </div>

            {/* Ders Adı */}
            <div className="form-section">
              <MaterialTextField
                label="Ders Adı"
                value={editData.ders_adi}
                onChange={(value) => handleInputChange('ders_adi', value)}
                type="text"
              />
            </div>

            {/* Sınıf Seçimi */}
            <div className="form-section">
              <MaterialTextField
                label="Sınıf"
                value={editData.sinif}
                onChange={(value) => handleInputChange('sinif', parseInt(value))}
                select={true}
                options={[9, 10, 11, 12].map(sinif => ({
                  value: sinif,
                  label: `${sinif}. Sınıf`
                }))}
              />
            </div>

            {/* Ders Saati Seçimi */}
            <div className="form-section">
              <MaterialTextField
                label="Ders Saati (Haftalık)"
                value={editData.ders_saati}
                onChange={(value) => handleInputChange('ders_saati', parseInt(value))}
                select={true}
                options={[1, 2, 3, 4, 5, 6, 7, 8].map(saat => ({
                  value: saat,
                  label: `${saat} Saat`
                }))}
              />
            </div>

            {/* Dersin Amacı */}
            <div className="form-section">
              <MaterialTextField
                label="Dersin Amacı"
                value={editData.amac}
                onChange={(value) => handleInputChange('amac', value)}
                multiline={true}
                rows={4}
              />
            </div>
          </div>

          <div className="sidebar-footer">
            <button className="btn-cancel" onClick={onClose}>İptal</button>
            <button className="btn-copy" onClick={handleCopy}>Kopyala</button>
            <button className="btn-save" onClick={handleSave}>Kaydet</button>
          </div>
        </div>
      </div>

      {/* PDF Preview Sidebar */}
      {pdfPreview.isOpen && (
        <div className="pdf-preview-sidebar">
          <div className="pdf-preview-content">
            <div className="pdf-preview-header">
              <h4>{pdfPreview.title} Preview</h4>
              <button onClick={closePdfPreview}>×</button>
            </div>
            <iframe
              src={pdfPreview.url}
              width="100%"
              height="100%"
              title="PDF Preview"
            />
          </div>
        </div>
      )}
    </>
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

// Material UI TextField komponenti
const MaterialTextField = ({ 
  label, 
  value, 
  onChange, 
  multiline = false, 
  rows = 1, 
  type = 'text',
  error = false,
  disabled = false,
  select = false,
  options = []
}) => {
  const [focused, setFocused] = useState(false);
  // Material UI'da label her zaman üstte olmalı - sadece focus durumuna göre stil değişir
  const hasValue = true; // Label her zaman üstte kalacak
  
  const handleFocus = () => setFocused(true);
  const handleBlur = () => setFocused(false);
  
  const classes = [
    'material-textfield',
    'always-floating', // Yeni class - label her zaman üstte
    hasValue ? 'has-value' : '',
    focused ? 'focused' : '',
    error ? 'error' : '',
    disabled ? 'disabled' : '',
    select ? 'select' : ''
  ].filter(Boolean).join(' ');

  return (
    <div className={classes}>
      {select ? (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          disabled={disabled}
        >
          <option value="" disabled hidden></option>
          {options.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          rows={rows}
          disabled={disabled}
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          disabled={disabled}
        />
      )}
      <label>{label}</label>
    </div>
  );
};

// Filtre dropdown komponenti
const FilterDropdown = ({ 
  column, 
  isOpen, 
  onToggle, 
  onClear, 
  searchTerm, 
  onSearchChange, 
  filteredItems, 
  selectedValues, 
  onFilterChange, 
  displayName 
}) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute',
      top: '100%',
      left: '0',
      right: '0',
      background: 'white',
      border: '1px solid #ddd',
      borderRadius: '4px',
      zIndex: 1000,
      maxHeight: '300px',
      overflowY: 'auto',
      padding: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
    }}>
      <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong style={{ fontSize: '12px' }}>{displayName} Filtresi</strong>
        <div>
          <button 
            onClick={onClear}
            style={{ fontSize: '10px', padding: '2px 4px', marginRight: '4px', background: '#f8f9fa', border: '1px solid #ddd', cursor: 'pointer' }}
          >
            Temizle
          </button>
          <button 
            onClick={onToggle}
            style={{ fontSize: '10px', padding: '2px 4px', background: '#f8f9fa', border: '1px solid #ddd', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
      </div>
      
      {/* Arama kutusu */}
      <input
        type="text"
        placeholder={`${displayName} ara...`}
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          width: '100%',
          padding: '4px 8px',
          fontSize: '11px',
          border: '1px solid #ddd',
          borderRadius: '3px',
          marginBottom: '8px'
        }}
        autoFocus
        onClick={(e) => e.stopPropagation()}
      />
      
      {filteredItems.map(([value, count]) => (
        <div key={value} style={{ marginBottom: '4px', fontSize: '11px' }}>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selectedValues.includes(String(value))}
              onChange={(e) => onFilterChange(String(value), e.target.checked)}
              style={{ marginRight: '6px' }}
            />
            <span>{value || 'Boş'} ({count})</span>
          </label>
        </div>
      ))}
    </div>
  );
};

const DataTable = ({ tableData, searchTerm, onCourseEdit }) => {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [selectedFilters, setSelectedFilters] = useState({
    alan_adi: [],
    dal_adi: [],
    ders_adi: [],
    sinif: [],
    ders_saati: []
  });
  const [showFilters, setShowFilters] = useState({
    alan_adi: false,
    dal_adi: false,
    ders_adi: false,
    sinif: false,
    ders_saati: false
  });
  const [filterSearchTerms, setFilterSearchTerms] = useState({
    alan_adi: '',
    dal_adi: '',
    ders_adi: '',
    sinif: '',
    ders_saati: ''
  });

  // Sütun değerlerini ve sayılarını hesapla
  const columnStats = useMemo(() => {
    if (!tableData || !Array.isArray(tableData)) return {};
    
    const stats = {};
    ['alan_adi', 'dal_adi', 'ders_adi', 'sinif', 'ders_saati'].forEach(column => {
      const counts = {};
      const uniqueValues = new Set();
      
      tableData.forEach(row => {
        const value = row[column];
        if (value !== null && value !== undefined && value !== '') {
          counts[value] = (counts[value] || 0) + 1;
          uniqueValues.add(value);
        }
      });
      
      stats[column] = {
        uniqueCount: uniqueValues.size,
        items: Object.entries(counts)
          .sort((a, b) => b[1] - a[1]) // Sayıya göre sırala
          // 20 limit kaldırıldı - tümü gösterilecek
      };
    });
    
    return stats;
  }, [tableData]);

  const filteredData = useMemo(() => {
    if (!tableData || !Array.isArray(tableData)) return [];
    
    let filtered = tableData;
    
    // Metin arama filtresi
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      filtered = filtered.filter(row => 
        (row.alan_adi && row.alan_adi.toLowerCase().includes(term)) ||
        (row.dal_adi && row.dal_adi.toLowerCase().includes(term)) ||
        (row.ders_adi && row.ders_adi.toLowerCase().includes(term))
      );
    }
    
    // Çoklu seçim filtreleri
    Object.entries(selectedFilters).forEach(([column, selectedValues]) => {
      if (selectedValues.length > 0) {
        filtered = filtered.filter(row => 
          selectedValues.includes(String(row[column]))
        );
      }
    });
    
    return filtered;
  }, [tableData, searchTerm, selectedFilters]);

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

  const toggleFilter = (column) => {
    setShowFilters(prev => ({
      ...prev,
      [column]: !prev[column]
    }));
    // Açılırken arama terimini temizle
    if (!showFilters[column]) {
      setFilterSearchTerms(prev => ({
        ...prev,
        [column]: ''
      }));
    }
  };

  const handleFilterChange = (column, value, checked) => {
    setSelectedFilters(prev => ({
      ...prev,
      [column]: checked 
        ? [...prev[column], value]
        : prev[column].filter(v => v !== value)
    }));
  };

  const clearFilters = (column) => {
    setSelectedFilters(prev => ({
      ...prev,
      [column]: []
    }));
  };

  const handleFilterSearch = (column, searchTerm) => {
    setFilterSearchTerms(prev => ({
      ...prev,
      [column]: searchTerm
    }));
  };

  // Filtrelenmiş dropdown öğelerini hesapla
  const getFilteredItems = (column) => {
    if (!columnStats[column]?.items) return [];
    
    const searchTerm = filterSearchTerms[column].toLowerCase();
    if (!searchTerm) return columnStats[column].items;
    
    return columnStats[column].items.filter(([value]) => 
      value.toString().toLowerCase().includes(searchTerm)
    );
  };

  const getColumnDisplayName = (column) => {
    const names = {
      alan_adi: 'Alan',
      dal_adi: 'Dal', 
      ders_adi: 'Ders',
      sinif: 'Sınıf',
      ders_saati: 'Saat'
    };
    return names[column] || column;
  };

  return (
    <div className="data-table-container">
      <div style={{ marginBottom: '10px' }}>
        <strong>Toplam: {sortedData.length} ders</strong>
      </div>
      <table className="comprehensive-data-table">
        <thead>
          <tr>
            {['alan_adi', 'dal_adi', 'ders_adi', 'sinif', 'ders_saati'].map(column => (
              <th key={column} onClick={() => handleSort(column)} style={{ cursor: 'pointer', position: 'relative' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>
                    {getColumnDisplayName(column)} {getSortIcon(column)}
                    <span style={{ fontSize: '11px', color: '#666', marginLeft: '4px' }}>
                      ({columnStats[column]?.uniqueCount || 0})
                    </span>
                  </span>
                  <button 
                    onClick={(e) => { e.stopPropagation(); toggleFilter(column); }}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px' }}
                    title="Filtrele"
                  >
                    🔽
                  </button>
                </div>
                <FilterDropdown
                  column={column}
                  isOpen={showFilters[column]}
                  onToggle={() => toggleFilter(column)}
                  onClear={() => clearFilters(column)}
                  searchTerm={filterSearchTerms[column]}
                  onSearchChange={(term) => handleFilterSearch(column, term)}
                  filteredItems={getFilteredItems(column)}
                  selectedValues={selectedFilters[column]}
                  onFilterChange={(value, checked) => handleFilterChange(column, value, checked)}
                  displayName={getColumnDisplayName(column)}
                />
              </th>
            ))}
            <th>DM</th>
            <th>DBF</th>
            <th>BOM</th>
            <th>İşlemler</th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, index) => (
            <tr key={`${row.alan_id}-${row.dal_id}-${row.ders_id || 'empty'}-${index}`}><td>{row.alan_adi || '-'}</td><td>{row.dal_adi || '-'}</td><td>{row.ders_adi || '-'}</td><td>{row.sinif || '-'}</td><td>{row.ders_saati || 0}</td><td>{row.dm_url ? (<a href={row.dm_url} target="_blank" rel="noopener noreferrer" className="ders-link">📄 DM</a>) : ("-")}</td><td>{row.dbf_url ? (<a href={row.dbf_url} target="_blank" rel="noopener noreferrer" className="dbf-link">📄 DBF</a>) : ("-")}</td><td>{row.bom_url ? (<a href={row.bom_url} target="_blank" rel="noopener noreferrer" className="bom-link">📄 BOM</a>) : ("-")}</td><td>{row.ders_id ? (<button className="edit-btn" onClick={() => onCourseEdit && onCourseEdit(row)}title="Düzenle">✏️</button>) : ("-")}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// AlanItem component removed - only table view is used now

function App() {  
  const [data, setData] = useState(null);
  const [tableData, setTableData] = useState([]); // ⭐ New: Database table data
  const [loading, setLoading] = useState(false); // isScraping yerine
  const [initialLoading, setInitialLoading] = useState(true); // Sayfa ilk yüklenirken
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
  // viewMode removed - only table view now
  const [editingSidebar, setEditingSidebar] = useState({ isOpen: false, course: null });
  const [editedCourses, setEditedCourses] = useState(new Map()); // Store edited course data
  const [pdfSidebar, setPdfSidebar] = useState({ isOpen: false, url: '', title: '' });
  const [consoleOpen, setConsoleOpen] = useState(false);

  // Kategorik veri state'leri
  const [copData, setCopData] = useState(null);
  const [catLoading, setCatLoading] = useState(""); // "dbf", "cop", "dm", "bom"
  const [catError, setCatError] = useState("");

  // İstatistik state'leri
  const [stats, setStats] = useState({
    alan: 0,
    dal: 0,
    ders: 0,
    cop_pdf: 0,
    dbf_rar: 0,
    dbf_pdf: 0,
    dbf_docx: 0,
    dm_pdf: 0,
    bom_pdf: 0,
    cop_okunan: 0,
    dbf_okunan: 0
  });

  // DBF rar indir/aç state'leri
  const [dbfUnrarLoading, setDbfUnrarLoading] = useState(false);
  const [dbfUnrarError, setDbfUnrarError] = useState("");
  
  // COP ve DBF okuma state'leri
  const [copProcessing, setCopProcessing] = useState(false);
  const [dbfProcessing, setDbfProcessing] = useState(false);

  // Debouncing efekti: Kullanıcı yazmayı bıraktıktan 300ms sonra arama terimini günceller.
  useEffect(() => {
    const timerId = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, 300);
    return () => {
      clearTimeout(timerId);
    };
  }, [searchTerm]); 

  // İstatistikleri yükle
  const loadStatistics = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:5001/api/get-statistics');
      if (response.ok) {
        const statisticsData = await response.json();
        setStats(statisticsData);
      }
    } catch (e) {
      console.error("İstatistik yükleme hatası:", e);
    }
  }, []);

  // ⭐ New: Veritabanından tablo verilerini yükle
  const loadTableData = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:5001/api/table-data');
      if (response.ok) {
        const tableDataResponse = await response.json();
        setTableData(tableDataResponse);
        setProgress(prev => [...prev, { 
          message: `${tableDataResponse.length} ders veritabanından yüklendi.`,
          type: 'done' 
        }]);
      } else {
        console.error("Tablo verisi yüklenemedi:", response.statusText);
      }
    } catch (e) {
      console.error("Tablo verisi yükleme hatası:", e);
      setError(`Tablo verisi yüklenemedi: ${e.message}`);
    }
  }, []);

  // Önbellekteki veriyi ve istatistikleri çeken birleşik fonksiyon
  const fetchCachedData = useCallback(async (isInitialLoad = false) => {
    if (isInitialLoad) setInitialLoading(true);
    try {
      const response = await fetch('http://localhost:5001/api/get-cached-data');
      if (!response.ok) throw new Error(`Önbellek sunucusundan yanıt alınamadı: ${response.statusText}`);
      
      const cachedData = await response.json();
      if (cachedData && cachedData.alanlar && Object.keys(cachedData.alanlar).length > 0) {
        setData(cachedData);
        const message = isInitialLoad ? "Önbellekten veriler başarıyla yüklendi." : "Veriler başarıyla yeniden yüklendi.";
        setProgress(prev => isInitialLoad ? [{ message, type: 'done' }] : [...prev, { message, type: 'done' }]);
      } else if (isInitialLoad) {
        setProgress([{ message: "Önbellek boş. Verileri çekmek için butona tıklayın.", type: 'info' }]);
      }
      // Her zaman istatistikleri ve tablo verilerini yükle
      await loadStatistics();
      await loadTableData();
    } catch (e) {
      console.error("Önbellek verisi çekme hatası:", e);
      setError(`Önbellek verisi çekilemedi. Backend sunucusunun çalıştığından emin olun. Hata: ${e.message}`);
    } finally {
      if (isInitialLoad) setInitialLoading(false);
    }
  }, [loadStatistics, loadTableData]);

  // Sayfa ilk yüklendiğinde veriyi çek
  useEffect(() => {
    fetchCachedData(true);
  }, [fetchCachedData]);

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

      // İstatistikleri güncelle
      if (eventData.stats) {
        setStats(prev => ({ ...prev, ...eventData.stats }));
      }

      if (eventData.type === 'done') {
        // Veri çekme tamamlandı, önbellekten tekrar yükle
        fetchCachedData(false);
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
  }, [data, fetchCachedData]);

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
    
    // Console'u aç ve mesaj yazdır
    setConsoleOpen(true);
    setProgress(prev => [...prev, { type: 'status', message: 'DBF verileri çekiliyor...' }]);
    
    try {
      const res = await fetch("http://localhost:5001/api/get-dbf");
      if (!res.ok) throw new Error("DBF verisi alınamadı");
      const json = await res.json();
      
      setProgress(prev => [...prev, { type: 'success', message: `DBF: ${json.updated_count || 0} alan güncellendi` }]);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("DBF: " + e.message);
      setProgress(prev => [...prev, { type: 'error', message: 'DBF hatası: ' + e.message }]);
    } finally {
      setCatLoading("");
    }
  };
  const fetchCop = useCallback(() => {
    if (loading || catLoading) return;

    setCatLoading("cop");
    setCatError("");
    setConsoleOpen(true);
    setProgress(prev => [...prev, { type: 'status', message: 'ÇÖP linkleri çekiliyor...' }]);

    const eventSource = new EventSource("http://localhost:5001/api/get-cop");

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        setProgress(prev => [...prev, eventData]);
        if (eventData.type === "done" || eventData.type === "error") {
          setCatLoading("");
          loadStatistics(); // İstatistikleri yeniden yükle
          eventSource.close();
        }
      } catch (e) {
        const errorMsg = "Gelen indirme verisi işlenemedi: " + e.message;
        setCatError(errorMsg);
        setProgress(prev => [...prev, { type: 'error', message: errorMsg }]);
        setCatLoading("");
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      const errorMsg = "ÇÖP indirme bağlantı hatası veya sunucu yanıt vermiyor.";
      setCatError(errorMsg);
setProgress(prev => [...prev, { type: 'error', message: errorMsg }]);
      setCatLoading("");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [loading, catLoading, loadStatistics]);
  const fetchDm = async () => {
    setCatLoading("dm");
    setCatError("");
    
    // Console'u aç ve mesaj yazdır
    setConsoleOpen(true);
    setProgress(prev => [...prev, { type: 'status', message: 'DM verileri çekiliyor...' }]);
    
    try {
      const res = await fetch("http://localhost:5001/api/get-dm");
      if (!res.ok) throw new Error("Ders Materyali verisi alınamadı");
      const json = await res.json();
      
      setProgress(prev => [...prev, { type: 'success', message: `DM: ${json.saved_count || 0} ders kaydedildi` }]);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("DM: " + e.message);
      setProgress(prev => [...prev, { type: 'error', message: 'DM hatası: ' + e.message }]);
    } finally {
      setCatLoading("");
    }
  };
  const fetchBom = async () => {
    setCatLoading("bom");
    setCatError("");
    
    // Console'u aç ve mesaj yazdır
    setConsoleOpen(true);
    setProgress(prev => [...prev, { type: 'status', message: 'BOM verileri çekiliyor...' }]);
    
    try {
      const res = await fetch("http://localhost:5001/api/get-bom");
      if (!res.ok) throw new Error("BOM verisi alınamadı");
      const json = await res.json();
      
      setProgress(prev => [...prev, { type: 'success', message: `BOM: ${json.updated_count || 0} ders güncellendi` }]);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("BOM: " + e.message);
      setProgress(prev => [...prev, { type: 'error', message: 'BOM hatası: ' + e.message }]);
    } finally {
      setCatLoading("");
    }
  };

  // COP verilerini alan adına göre basit bir harita haline getir
  const createCopMapping = useCallback((copData) => {
    if (!copData) return {};
    const mapping = {};
    
    // Tüm sınıfları kontrol et ve her alan için bir URL bul
    Object.values(copData).forEach(sinifData => {
      Object.entries(sinifData).forEach(([alanAdi, copInfo]) => {
        if (!mapping[alanAdi] && copInfo.link) {
          mapping[alanAdi] = copInfo.link;
        }
      });
    });
    
    return mapping;
  }, []);

  // Veritabanından gelen JSON cop_url'lerini parse et
  const parseCopUrl = useCallback((copUrlJson) => {
    if (!copUrlJson) return null;
    
    try {
      if (copUrlJson.startsWith('{')) {
        // JSON formatında
        const copUrls = JSON.parse(copUrlJson);
        // İlk URL'i döndür
        const firstKey = Object.keys(copUrls)[0];
        return firstKey ? copUrls[firstKey] : null;
      } else {
        // Eski format (string)
        return copUrlJson;
      }
    } catch (e) {
      return copUrlJson; // Parse edilemezse original'i döndür
    }
  }, []);

  // COP verilerini basit harita haline getir
  const copMapping = useMemo(() => {
    return createCopMapping(copData?.data);
  }, [copData, createCopMapping]);

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

  // Workflow step handler removed - using individual module functions now

  const handleSaveCourse = useCallback(async (editedData) => {
    try {
      // ⭐ New: Save directly to database via API
      const response = await fetch('http://localhost:5001/api/update-table-row', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ders_id: editedData.ders_id,
          updates: {
            ders_adi: editedData.ders_adi,
            sinif: editedData.sinif,
            ders_saati: editedData.ders_saati || 0,
            amac: editedData.amac,
            dm_url: editedData.dm_url,
            dbf_url: editedData.dbf_url,
            bom_url: editedData.bom_url
          }
        })
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || 'Sunucu hatası');
      }

      // Show success message
      setProgress(prev => [...prev, { 
        type: 'success', 
        message: `"${editedData.ders_adi}" dersi başarıyla güncellendi.` 
      }]);

      // Reload table data to reflect changes
      await loadTableData();
      
    } catch (error) {
      setProgress(prev => [...prev, { 
        type: 'error', 
        message: `Ders güncelleme hatası: ${error.message}` 
      }]);
    }
  }, [loadTableData]);

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

  // ÇÖP PDF işleme fonksiyonu
  const handleProcessCopPdfs = useCallback(() => {
    if (!window.confirm('ÇÖP PDF\'lerini işleyip alan-dal-ders ilişkilerini çıkararak veritabanına kaydetmek istediğinize emin misiniz? Bu işlem uzun sürebilir.')) {
      return;
    }

    setProgress([]);
    setError(null);
    setCopProcessing(true);
    setConsoleOpen(true);
    // Reset COP read count
    setStats(prev => ({ ...prev, cop_okunan: 0 }));

    const eventSource = new EventSource('http://localhost:5001/api/oku-cop');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      
      // Update read count from progress messages
      if (eventData.message && eventData.message.includes('ders bilgisi çıkarıldı')) {
        setStats(prev => ({ ...prev, cop_okunan: prev.cop_okunan + 1 }));
      }
      
      // İstatistikleri güncelle
      if (eventData.stats) {
        setStats(prev => ({ ...prev, ...eventData.stats }));
      }
      
      setProgress(prev => [...prev, eventData]);

      if (eventData.type === 'done') {
        setCopProcessing(false);
        eventSource.close();
        setProgress(prev => [...prev, { type: 'success', message: 'ÇÖP işleme tamamlandı. Tablo güncelleniyor...' }]);
        loadTableData(); // Tabloyu yeniden yükle
      }
    };

    eventSource.onerror = () => {
      setError("ÇÖP PDF işleme sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      setCopProcessing(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  // DBF'lerden ders saatlerini güncelleme fonksiyonu
  const handleUpdateDersSaatleri = useCallback(() => {
    if (!window.confirm('DBF dosyalarından ders saati bilgilerini çıkarıp mevcut dersleri güncellemek istediğinize emin misiniz? Bu işlem uzun sürebilir.')) {
      return;
    }

    setProgress([]);
    setError(null);
    setDbfProcessing(true);
    setConsoleOpen(true);
    // Reset DBF read count
    setStats(prev => ({ ...prev, dbf_okunan: 0 }));

    const eventSource = new EventSource('http://localhost:5001/api/update-ders-saatleri-from-dbf');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      
      // Update read count from progress messages
      if (eventData.message && (eventData.message.includes('işlendi') || eventData.message.includes('okundu'))) {
        setStats(prev => ({ ...prev, dbf_okunan: prev.dbf_okunan + 1 }));
      }
      
      // İstatistikleri güncelle
      if (eventData.stats) {
        setStats(prev => ({ ...prev, ...eventData.stats }));
      }
      
      setProgress(prev => [...prev, eventData]);

      if (eventData.type === 'done') {
        setDbfProcessing(false);
        eventSource.close();
        setProgress(prev => [...prev, { type: 'success', message: 'DBF işleme tamamlandı. Tablo güncelleniyor...' }]);
        loadTableData(); // Tabloyu yeniden yükle
      }
    };

    eventSource.onerror = () => {
      setError("DBF ders saati güncelleme sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      setDbfProcessing(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleGetirAlanDal = useCallback(() => {
    if (loading) return;
    
    if (stats.alan > 0 && !window.confirm('Veritabanında zaten alan/dal verisi mevcut. Yine de yeniden çekmek ve mevcut verileri güncellemek istiyor musunuz?')) {
      return;
    }

    setConsoleOpen(true);
    setProgress([]);
    setError(null);
    setLoading(true);

    const eventSource = new EventSource('http://localhost:5001/api/scrape-alan-dal');

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        setProgress(prev => [...prev, eventData]);

        // Anlık istatistik güncellemesi için yeni eklenen bölüm
        if (eventData.type === 'progress' && eventData.total_areas !== undefined && eventData.total_branches !== undefined) {
          setStats(prevStats => ({
            ...prevStats,
            alan: eventData.total_areas,
            dal: eventData.total_branches
          }));
        }

        if (eventData.type === 'done') {
          loadStatistics(); // Son ve en doğru istatistikleri veritabanından çek
          loadTableData(); // Tabloyu yeniden yükle
          eventSource.close();
          setLoading(false);
        }
        if (eventData.type === 'error') {
          setError(eventData.message || "Bilinmeyen bir hata oluştu.");
          setLoading(false);
          eventSource.close();
        }
      } catch (e) {
          setError("Gelen veri işlenemedi: " + e.message);
          setLoading(false);
          eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      setError("Veri akışı sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      eventSource.close();
      setLoading(false);
    };

    return () => {
      eventSource.close();
    };
  }, [loading, stats.alan, loadStatistics, loadTableData]);
  
  return (
    <div className="App">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h1>meslek.meb (alan-dal-ders) dosyalar</h1>
        
        {/* Console Toggle Button */}
        <button
          onClick={() => setConsoleOpen(!consoleOpen)}
          style={{
            padding: "10px 20px",
            background: "#343a40",
            color: "white",
            border: "none",
            borderRadius: "5px",
            fontSize: "14px",
            fontWeight: "bold",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <span style={{ fontSize: "16px" }}>⚡</span>
          Console
        </button>
      </div>
      
      {/* Yeni Tek Satır İş Akışı */}
      <div className="workflow-container" style={{ 
        background: "#f8f9fa", 
        padding: "20px", 
        borderRadius: "8px", 
        margin: "20px 0",
        border: "1px solid #dee2e6"
      }}>
        
        {/* Tek Satır Buton Dizisi */}
        <div style={{ 
          display: "flex", 
          justifyContent: "center", 
          gap: "15px", 
          flexWrap: "wrap",
          marginBottom: "20px"
        }}>
          {/* 1. Getir Alan ve Dal */}
          <button
            onClick={handleGetirAlanDal}
            disabled={loading}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #87ceeb 0%, #4da6ff 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Getir Alan ve Dal</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.alan}) ve ({stats.dal})</div>
          </button>

          {/* 2. Getir COP */}
          <button
            onClick={fetchCop}
            disabled={loading || catLoading === "cop"}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #7bb3f0 0%, #337ab7 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: (loading || catLoading === "cop") ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Getir ÇÖP</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.cop_pdf} PDF)</div>
          </button>

          {/* 3. Getir DBF */}
          <button
            onClick={fetchDbf}
            disabled={loading || catLoading === "dbf"}
            style={{
              width: "160px",
              height: "80px",
              background: "linear-gradient(135deg, #74a9d8 0%, #4285c9 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "10px",
              fontWeight: "bold",
              cursor: (loading || catLoading === "dbf") ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Getir DBF</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>
              Ders({stats.ders})<br />({stats.dbf_rar} RAR, {stats.dbf_pdf} PDF, {stats.dbf_docx} DOCX)
            </div>
          </button>

          {/* 4. Getir DM */}
          <button
            onClick={fetchDm}
            disabled={loading || catLoading === "dm"}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #6fa8dc 0%, #2e5c8a 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: (loading || catLoading === "dm") ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Getir DM</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.dm_pdf} PDF)</div>
          </button>

          {/* 5. Getir BOM */}
          <button
            onClick={fetchBom}
            disabled={loading || catLoading === "bom"}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #5f9bcc 0%, #1f4e79 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: (loading || catLoading === "bom") ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Getir BOM</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.bom_pdf} PDF)</div>
          </button>

          {/* 6. Oku COP */}
          <button
            onClick={handleProcessCopPdfs}
            disabled={loading || copProcessing}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #4f8fc0 0%, #1a4a6b 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: (loading || copProcessing) ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Oku COP</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.cop_okunan} Ders)</div>
          </button>

          {/* 7. Oku DBF */}
          <button
            onClick={handleUpdateDersSaatleri}
            disabled={loading || dbfProcessing}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #3f7fb3 0%, #164058 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "11px",
              fontWeight: "bold",
              cursor: (loading || dbfProcessing) ? "not-allowed" : "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px"
            }}
          >
            <div>Oku DBF</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.dbf_okunan} Ders)</div>
          </button>
        </div>

        {/* Durum Göstergeleri */}
        <div style={{ textAlign: "center", padding: "10px", background: "#e9ecef", borderRadius: "5px" }}>
          {(catLoading || loading || copProcessing || dbfProcessing) && (
            <div style={{ color: "#007bff", fontWeight: "bold" }}>
              ⏳ İşlem devam ediyor: {
                catLoading === "dbf" ? "DBF verileri çekiliyor" :
                catLoading === "cop" ? "ÇÖP PDF'leri indiriliyor" :
                catLoading === "dm" ? "DM verileri çekiliyor" :
                catLoading === "bom" ? "BOM verileri çekiliyor" :
                copProcessing ? "ÇÖP PDF'leri okunuyor" :
                dbfProcessing ? "DBF dosyaları okunuyor" :
                loading ? "Alan-Dal verileri çekiliyor" :
                "İşlem"
              }...
            </div>
          )}
          {catError && <div style={{ color: "#dc3545", fontWeight: "bold" }}>❌ Hata: {catError}</div>}
        </div>
      </div>

      {/* Arama Kutusu */}
      {!initialLoading && tableData.length > 0 && (
        <div className="search-bar" style={{ marginBottom: '20px', textAlign: 'center' }}>
          <input
            type="text"
            placeholder="Alan, dal veya ders adına göre filtrele..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '10px 15px',
              fontSize: '16px',
              border: '1px solid #ccc',
              borderRadius: '8px',
              width: '400px',
              maxWidth: '90%'
            }}
          />
        </div>
      )}

      {/* Sliding Console Panel */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: consoleOpen ? "0" : "-400px",
          width: "400px",
          height: "100vh",
          background: "#1e1e1e",
          color: "#ffffff",
          transition: "right 0.3s ease",
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          boxShadow: consoleOpen ? "-5px 0 15px rgba(0,0,0,0.3)" : "none"
        }}
      >
        {/* Console Header */}
        <div style={{
          padding: "15px 20px",
          background: "#2d2d2d",
          borderBottom: "1px solid #444",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "16px" }}>⚡</span>
            <h3 style={{ margin: 0, color: "#ffffff" }}>Console</h3>
          </div>
          <button
            onClick={() => setConsoleOpen(false)}
            style={{
              background: "transparent",
              border: "none",
              color: "#ffffff",
              fontSize: "18px",
              cursor: "pointer",
              padding: "5px"
            }}
          >
            ×
          </button>
        </div>

        {/* Console Content */}
        <div style={{
          flex: 1,
          padding: "10px",
          overflowY: "auto",
          fontFamily: "Consolas, 'Courier New', monospace",
          fontSize: "12px",
          lineHeight: "1.4"
        }}>
          {initialLoading && (
            <div style={{ color: "#00ff00", marginBottom: "5px" }}>
              › Önbellek kontrol ediliyor...
            </div>
          )}
          {error && (
            <div style={{ color: "#ff4444", fontWeight: "bold", marginBottom: "5px" }}>
              ✗ HATA: {error}
            </div>
          )}
          {progress.map((p, index) => {
            // Hata mesajından alan_adi ve rar_filename çıkarılabiliyorsa buton ekle
            let retryButton = null;
            if (p.type === 'error' && p.message) {
              const match = p.message.match(/^\[([^\]]+)\].+?([^\s]+\.rar|[^\s]+\.zip)/i);
              if (match) {
                const alan_adi = match[1];
                const rar_filename = match[2];
                retryButton = (
                  <button
                    style={{
                      marginLeft: 8,
                      fontSize: 10,
                      padding: "2px 6px",
                      background: "#444",
                      color: "#fff",
                      border: "1px solid #666",
                      borderRadius: "3px",
                      cursor: "pointer"
                    }}
                    onClick={async () => {
                      try {
                        const res = await fetch("http://localhost:5001/api/dbf-retry-extract", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ alan_adi, rar_filename })
                        });
                        const result = await res.json();
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

            const messageColor = p.type === 'error' ? '#ff4444' :
                               p.type === 'warning' ? '#ffbb33' :
                               p.type === 'success' ? '#00C851' :
                               p.type === 'done' ? '#00C851' :
                               '#00BFFF';

            if (p.type === 'province_summary') {
              return (
                <div key={index} style={{ marginBottom: '10px', whiteSpace: 'pre-wrap', color: messageColor }}>
                  <div>{`İl      : ${p.province_name} ${p.province_progress}`}</div>
                  <div>{`Alan Sayısı: ${p.alan_sayisi_province}/${p.alan_sayisi_total_province}`}</div>
                  <div>{`Dal Sayısı : ${p.dal_sayisi_province} (Toplam: ${p.dal_sayisi_total_so_far})`}</div>
                </div>
              )
            }

            return (
              <div key={index} style={{ color: messageColor, marginBottom: '5px', whiteSpace: 'pre-wrap' }}>
                <span style={{ marginRight: '5px' }}>›</span>
                {p.message}
                {retryButton}
              </div>
            );
          })}
        </div>
      </div>

      {initialLoading ? (
        <div style={{ textAlign: 'center', padding: '50px', fontSize: '18px' }}>
          Yükleniyor...
        </div>
      ) : (
        <>
          {/* Ana İçerik */}
          <div className="main-content">
            {/* Sadece DataTable gösterilecek */}
            <DataTable 
              tableData={tableData}
              searchTerm={debouncedTerm}
              onCourseEdit={handleCourseEdit}
            />
          </div>

          {/* Düzenleme Kenar Çubuğu */}
          <CourseEditSidebar
            course={editingSidebar.course}
            isOpen={editingSidebar.isOpen}
            onClose={handleCloseSidebar}
            onSave={handleSaveCourse}
            onShowPDF={handleShowPDF}
          />

          {/* PDF Görüntüleyici Kenar Çubuğu - Bağımsız */}
          <PDFViewerSidebar
            pdfUrl={pdfSidebar.url}
            isOpen={pdfSidebar.isOpen}
            onClose={handleClosePDFSidebar}
            courseTitle={pdfSidebar.title}
          />
        </>
      )}
    </div>
  );
}

export default App;
