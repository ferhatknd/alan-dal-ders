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
    ders_id: '',
    ders_adi: '',
    sinif: '',
    ders_saati: '',
    alan_adi: '',
    dal_adi: '',
    dm_url: '',
    dbf_url: '',
    bom_url: ''
  });

  useEffect(() => {
    if (course && isOpen) {
      setEditData({
        ders_id: course.ders_id || '',
        ders_adi: course.ders_adi || '',
        sinif: course.sinif || '',
        ders_saati: course.ders_saati || '',
        alan_adi: course.alan_adi || '',
        dal_adi: course.dal_adi || '',
        dm_url: course.dm_url || '',
        dbf_url: course.dbf_url || '',
        bom_url: course.bom_url || ''
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
            {editData.dm_url && (
              <button 
                className="pdf-view-btn" 
                onClick={() => onShowPDF && onShowPDF(editData.dm_url, editData.ders_adi)}
                title="Ders Materyali PDF'i görüntüle"
              >
                📄 DM Görüntüle
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
              <input
                type="number"
                value={editData.sinif}
                onChange={(e) => handleInputChange('sinif', e.target.value)}
                min="9"
                max="12"
                placeholder="Sınıf (örn: 10)"
              />
            </div>
            <div className="form-group">
              <label>Ders Saati (Haftalık):</label>
              <input
                type="number"
                value={editData.ders_saati}
                onChange={(e) => handleInputChange('ders_saati', e.target.value)}
                min="0"
                placeholder="Ders saati (örn: 4)"
              />
            </div>
            <div className="form-group">
              <label>Alan Adı:</label>
              <input
                type="text"
                value={editData.alan_adi}
                readOnly
                style={{backgroundColor: '#f8f9fa'}}
                title="Alan adı değiştirilemez"
              />
            </div>
            <div className="form-group">
              <label>Dal Adı:</label>
              <input
                type="text"
                value={editData.dal_adi}
                readOnly
                style={{backgroundColor: '#f8f9fa'}}
                title="Dal adı değiştirilemez"
              />
            </div>
          </div>

          <div className="form-section">
            <h4>Dosya URL'leri</h4>
            <div className="form-group">
              <label>DM URL (Ders Materyali):</label>
              <input
                type="url"
                value={editData.dm_url}
                onChange={(e) => handleInputChange('dm_url', e.target.value)}
                placeholder="Ders Materyali PDF URL'si"
              />
            </div>
            <div className="form-group">
              <label>DBF URL (Ders Bilgi Formu):</label>
              <input
                type="url"
                value={editData.dbf_url}
                onChange={(e) => handleInputChange('dbf_url', e.target.value)}
                placeholder="DBF PDF URL'si"
              />
            </div>
            <div className="form-group">
              <label>BOM URL (Bireysel Öğrenme Materyali):</label>
              <input
                type="url"
                value={editData.bom_url}
                onChange={(e) => handleInputChange('bom_url', e.target.value)}
                placeholder="BOM PDF URL'si"
              />
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
            <tr key={`${row.alan_id}-${row.dal_id}-${row.ders_id || 'empty'}-${index}`}>
              <td>{row.alan_adi || '-'}</td>
              <td>{row.dal_adi || '-'}</td>
              <td>{row.ders_adi || '-'}</td>
              <td>{row.sinif || '-'}</td>
              <td>{row.ders_saati || 0}</td>
              <td>
                {row.dm_url ? (
                  <a href={row.dm_url} target="_blank" rel="noopener noreferrer" className="ders-link">
                    📄 DM
                  </a>
                ) : (
                  "-"
                )}
              </td>
              <td>
                {row.dbf_url ? (
                  <a href={row.dbf_url} target="_blank" rel="noopener noreferrer" className="dbf-link">
                    📄 DBF
                  </a>
                ) : (
                  "-"
                )}
              </td>
              <td>
                {row.bom_url ? (
                  <a href={row.bom_url} target="_blank" rel="noopener noreferrer" className="bom-link">
                    📄 BOM
                  </a>
                ) : (
                  "-"
                )}
              </td>
              <td>
                {row.ders_id ? (
                  <button 
                    className="edit-btn" 
                    onClick={() => onCourseEdit && onCourseEdit(row)}
                    title="Düzenle"
                  >
                    ✏️
                  </button>
                ) : (
                  "-"
                )}
              </td>
            </tr>
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
  const fetchCop = async () => {
    setCatLoading("cop");
    setCatError("");
    
    // Console'u aç ve mesaj yazdır
    setConsoleOpen(true);
    setProgress(prev => [...prev, { type: 'status', message: 'ÇÖP verileri çekiliyor...' }]);
    
    try {
      const res = await fetch("http://localhost:5001/api/get-cop");
      if (!res.ok) throw new Error("ÇÖP verisi alınamadı");
      const json = await res.json();
      setCopData(json);
      
      setProgress(prev => [...prev, { type: 'success', message: `ÇÖP: ${json.updated_count || 0} alan güncellendi` }]);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("ÇÖP: " + e.message);
      setProgress(prev => [...prev, { type: 'error', message: 'ÇÖP hatası: ' + e.message }]);
    } finally {
      setCatLoading("");
    }
  };
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
    // Reset COP read count
    setStats(prev => ({ ...prev, cop_okunan: 0 }));

    const eventSource = new EventSource('http://localhost:5001/api/process-cop-pdfs');

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
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setError("ÇÖP PDF işleme sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
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
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setError("DBF ders saati güncelleme sırasında bir hata oluştu. Sunucu bağlantısı kesilmiş olabilir.");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);
  
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
            onClick={async () => {
              setProgress([]);
              setError(null);
              setLoading(true);
              try {
                const response = await fetch('http://localhost:5001/api/get-dal');
                const result = await response.json();
                
                // İstatistikleri güncelle
                if (result.alanlar && result.dallar) {
                  setStats(prev => ({ 
                    ...prev, 
                    alan: result.alanlar.length || 0,
                    dal: result.dallar.length || 0
                  }));
                }
                
                setProgress(prev => [...prev, { type: 'done', message: 'Alan-Dal verileri başarıyla çekildi' }]);
                await loadStatistics(); // Veritabanından güncel istatistikleri yükle
              } catch (e) {
                setProgress(prev => [...prev, { type: 'error', message: 'Alan-Dal çekme hatası: ' + e.message }]);
              } finally {
                setLoading(false);
              }
            }}
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
            disabled={loading}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #4f8fc0 0%, #1a4a6b 100%)",
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
            <div>Oku COP</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.cop_okunan} Ders)</div>
          </button>

          {/* 7. Oku DBF */}
          <button
            onClick={handleUpdateDersSaatleri}
            disabled={loading}
            style={{
              width: "140px",
              height: "80px",
              background: "linear-gradient(135deg, #3f7fb3 0%, #164058 100%)",
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
            <div>Oku DBF</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.dbf_okunan} Ders)</div>
          </button>
        </div>

        {/* Durum Göstergeleri */}
        <div style={{ textAlign: "center", padding: "10px", background: "#e9ecef", borderRadius: "5px" }}>
          {(catLoading || loading) && (
            <div style={{ color: "#007bff", fontWeight: "bold" }}>
              ⏳ İşlem devam ediyor: {catLoading || "genel işlem"}...
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
              const match = p.message.match(/^\[([^\]]+)\].*?([^\s\/]+\.rar|[^\s\/]+\.zip)/i);
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
                    Retry
                  </button>
                );
              }
            }

            const timestamp = new Date().toLocaleTimeString();
            const getColor = () => {
              switch(p.type) {
                case 'error': return '#ff4444';
                case 'warning': return '#ffaa00';
                case 'done': return '#00ff00';
                case 'success': return '#00ff00';
                default: return '#cccccc';
              }
            };

            const getPrefix = () => {
              switch(p.type) {
                case 'error': return '✗';
                case 'warning': return '⚠';
                case 'done': return '✓';
                case 'success': return '✓';
                default: return '›';
              }
            };

            return (
              <div key={index} style={{
                color: getColor(),
                marginBottom: "3px",
                wordWrap: "break-word"
              }}>
                <span style={{ color: "#888", fontSize: "10px" }}>[{timestamp}] </span>
                <span>{getPrefix()} {p.message}</span>
                {retryButton}
                {p.estimation && (
                  <div style={{ color: "#888", fontSize: "10px", marginLeft: "60px" }}>
                    └ {p.estimation}
                  </div>
                )}
              </div>
            );
          })}
          
          {progress.length === 0 && !initialLoading && !error && (
            <div style={{ color: "#888", fontStyle: "italic" }}>
              › Console ready. Run operations to see logs...
            </div>
          )}
        </div>

        {/* Console Footer */}
        <div style={{
          padding: "10px",
          background: "#2d2d2d",
          borderTop: "1px solid #444",
          fontSize: "10px",
          color: "#888"
        }}>
          {progress.length} log entries
        </div>
      </div>


      {/* Veri görüntüleme alanı - Sadece Tablo Görünümü */}
      {!initialLoading && tableData.length > 0 && (
        <div className="data-display">
          <DataTable tableData={tableData} searchTerm={debouncedTerm} onCourseEdit={handleCourseEdit} />
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
