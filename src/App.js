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

const DataTable = ({ data, searchTerm, onCourseEdit, copData }) => {
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
              <td>
                {row.alanIsim}
                {copData && copData[row.alanIsim] && (
                  <a
                    href={copData[row.alanIsim]}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Çerçeve Öğretim Programı (ÇÖP) PDF"
                    style={{ marginLeft: 6, fontSize: 16, verticalAlign: 'middle' }}
                  >
                    📄 ÇÖP
                  </a>
                )}
              </td>
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

// AlanItem component removed - only table view is used now

function App() {  
  const [data, setData] = useState(null);
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
  const [dbfData, setDbfData] = useState(null);
  const [copData, setCopData] = useState(null);
  const [dmData, setDmData] = useState(null);
  const [bomData, setBomData] = useState(null);
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
        // İstatistikleri yükle
        await loadStatistics();
      } catch (e) {
        console.error("Önbellek verisi çekme hatası:", e);
        setError(`Önbellek verisi çekilemedi. Backend sunucusunun çalıştığından emin olun. Hata: ${e.message}`);
      } finally {
        setInitialLoading(false);
      }
    };

    fetchCachedData();
  }, [loadStatistics]);

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
      
      // DBF istatistiklerini hesapla
      let rarCount = 0, pdfCount = 0, docxCount = 0;
      Object.values(json).forEach(sinifData => {
        Object.values(sinifData).forEach(alanData => {
          if (alanData.link) {
            if (alanData.link.endsWith('.rar') || alanData.link.endsWith('.zip')) {
              rarCount++;
            }
          }
        });
      });
      
      setStats(prev => ({ 
        ...prev, 
        dbf_rar: rarCount,
        dbf_pdf: pdfCount,
        dbf_docx: docxCount 
      }));
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
      
      // COP PDF sayısını hesapla
      let pdfCount = 0;
      if (json.data) {
        Object.values(json.data).forEach(sinifData => {
          Object.values(sinifData).forEach(alanData => {
            if (alanData.link) {
              pdfCount++;
            }
          });
        });
      }
      
      setStats(prev => ({ ...prev, cop_pdf: pdfCount }));
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
      
      // DM PDF sayısını hesapla
      let pdfCount = 0;
      Object.values(json).forEach(sinifData => {
        Object.values(sinifData).forEach(alanData => {
          if (alanData && Array.isArray(alanData)) {
            pdfCount += alanData.length;
          }
        });
      });
      
      setStats(prev => ({ ...prev, dm_pdf: pdfCount }));
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
      
      // BOM PDF sayısını hesapla
      let pdfCount = 0;
      Object.values(json).forEach(alanData => {
        if (alanData.dersler && Array.isArray(alanData.dersler)) {
          alanData.dersler.forEach(ders => {
            if (ders.moduller && Array.isArray(ders.moduller)) {
              pdfCount += ders.moduller.length;
            }
          });
        }
      });
      
      setStats(prev => ({ ...prev, bom_pdf: pdfCount }));
    } catch (e) {
      setCatError("BOM: " + e.message);
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

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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
            <div>Getir COP</div>
            <div style={{ fontSize: "10px", marginTop: "5px" }}>({stats.cop_pdf} PDF)</div>
          </button>

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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
              fontSize: "9px",
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
            <div style={{ fontSize: "8px", marginTop: "5px" }}>
              Ders({stats.ders}) ({stats.dbf_rar} RAR, {stats.dbf_pdf} PDF, {stats.dbf_docx} DOCX)
            </div>
          </button>

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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

          {/* Bağlantı Oku */}
          <div style={{ display: "flex", alignItems: "center", fontSize: "16px", color: "#6c757d" }}>➤</div>

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
      {!initialLoading && data && (
        <div className="search-bar" style={{ marginBottom: '20px', textAlign: 'center' }}>
          <input
            type="text"
            placeholder="Filtrelemek için alan adı girin..."
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

      {/* Veri görüntüleme alanı - Sadece Tablo Görünümü */}
      {!initialLoading && data && (
        <div className="data-display">
          <DataTable data={data} searchTerm={debouncedTerm} onCourseEdit={handleCourseEdit} copData={copMapping} />
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
