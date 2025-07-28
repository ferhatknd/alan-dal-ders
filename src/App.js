import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './App.css';

const OrtakAlanlarCell = ({ dersLink, currentAlanId, ortakAlanIndeksi, allAlans }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const ortakAlanIds = (ortakAlanIndeksi[dersLink] || []).filter(id => id !== currentAlanId);

  if (ortakAlanIds.length === 0) {
    return <td>-</td>;
  }

  const ortakAlanNames = ortakAlanIds.map(id => (allAlans[id] && allAlans[id].isim) || `ID: ${id}`);
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


// COP Dropdown Bileşeni
const CopDropdown = ({ copUrls, onSelectCop }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  console.log('CopDropdown render - copUrls:', copUrls);
  
  if (!copUrls || Object.keys(copUrls).length === 0) {
    console.log('CopDropdown: COP URL\'leri bulunamadı veya boş');
    return null;
  }
  
  const copList = Object.entries(copUrls).map(([key, url]) => ({
    label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : /^\d+$/.test(key) ? `${key}. Sınıf` : key,
    url: url,
    key: key
  }));
  
  console.log('CopDropdown: COP listesi oluşturuldu:', copList);
  
  return (
    <div className="cop-dropdown-container">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="cop-dropdown-toggle"
      >
        ÇÖP {isOpen ? '▲' : '▼'}
      </button>
      {isOpen && (
        <div className="cop-dropdown-menu">
          {copList.map(item => (
            <button
              key={item.key}
              onClick={() => {
                onSelectCop(item.url, `ÇÖP - ${item.label}`);
                setIsOpen(false);
              }}
              className="cop-dropdown-item"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// DBF Dropdown Bileşeni - Ders Bazlı Sistem
const DbfDropdown = ({ courseDbfUrl, onSelectDbf }) => {
  console.log('DbfDropdown render - courseDbfUrl:', courseDbfUrl);
  console.log('DbfDropdown - courseDbfUrl type:', typeof courseDbfUrl);
  
  // Eğer ders için DBF dosyası yoksa gösterme
  if (!courseDbfUrl || courseDbfUrl.trim() === '') {
    console.log('DbfDropdown: Bu ders için DBF dosyası bulunamadı');
    return (
      <div className="dbf-dropdown-container disabled">
        <button className="dbf-dropdown-toggle disabled" type="button" disabled>
          DBF Dosyası Yok ❌
        </button>
      </div>
    );
  }
  
  // Dosya adını path'den çıkar
  const fileName = courseDbfUrl.split('/').pop() || courseDbfUrl;
  const fileExtension = fileName.split('.').pop()?.toUpperCase() || 'Dosya';
  
  console.log('DbfDropdown: DBF dosyası mevcut:', fileName);
  
  return (
    <div className="dbf-dropdown-container">
      <button 
        onClick={() => {
          console.log('DBF dosyası açılıyor:', courseDbfUrl);
          onSelectDbf(courseDbfUrl, `DBF - ${fileName}`);
        }}
        className="dbf-dropdown-toggle"
      >
        📄 {fileExtension} Dosyasını Aç
      </button>
    </div>
  );
};

// Button Group Bileşeni
const ButtonGroup = ({ label, options, value, onChange, maxPerRow = 4 }) => {
  return (
    <div className="button-group-section">
      <div className="button-group-container">
        <label className="button-group-label">
          {label}:
        </label>
        <div className="button-group-buttons">
          {options.map((option, index) => (
            <button
              key={option.value}
              onClick={() => onChange(option.value)}
              className={`button-group-button ${value === option.value ? 'active' : ''}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const CourseEditSidebar = ({ course, isOpen, onClose, onSave, onShowPDF, pdfUrl, pdfTitle }) => {
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
  const [copUrls, setCopUrls] = useState({});
  
  // Split pane için state'ler
  const [leftWidth, setLeftWidth] = useState(50); // Percentage
  const [isResizing, setIsResizing] = useState(false);
  
  // PDF loading states
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState(null);
  
  // Split screen mode - PDF açık mı?
  const isSplitMode = Boolean(pdfUrl);

  // Alan-Dal seçeneklerini yükle
  useEffect(() => {
    if (isOpen) {
      fetch('http://localhost:5001/api/alan-dal-options')
        .then(res => res.json())
        .then(data => {
          console.log('Alan-Dal seçenekleri yüklendi:', data);
          setAlanDalOptions(data);
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

  // COP ve DBF URL'lerini alan_id değiştiğinde güncelle
  useEffect(() => {
    if (editData.alan_id && alanDalOptions.alanlar.length > 0) {
      console.log('COP ve DBF URL\'leri güncelleniyor, alan_id:', editData.alan_id);
      
      const selectedAlan = alanDalOptions.alanlar.find(alan => alan.id === parseInt(editData.alan_id));
      console.log('selectedAlan bulundu:', selectedAlan);
      
      // COP URL'lerini güncelle
      if (selectedAlan && selectedAlan.cop_url) {
        try {
          const copData = JSON.parse(selectedAlan.cop_url);
          console.log('COP verisi parse edildi:', copData);
          setCopUrls(copData);
        } catch (e) {
          console.log('COP verisi JSON değil, string olarak işleniyor:', selectedAlan.cop_url);
          setCopUrls({ 'cop_url': selectedAlan.cop_url });
        }
      } else {
        console.log('Seçilen alan için COP verisi bulunamadı');
        setCopUrls({});
      }
      
      // DBF artık ders bazlı olduğu için alan bazlı DBF URL'leri kaldırıldı
    }
  }, [editData.alan_id, alanDalOptions.alanlar]);

  // PDF URL değiştiğinde loading state'ini sıfırla
  useEffect(() => {
    if (pdfUrl) {
      setPdfLoading(true);
      setPdfError(null);
    }
  }, [pdfUrl]);

  // Resize functionality
  const handleMouseDown = (e) => {
    setIsResizing(true);
    e.preventDefault();
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizing) {
        const containerWidth = window.innerWidth;
        const newLeftWidth = (e.clientX / containerWidth) * 100;
        if (newLeftWidth >= 20 && newLeftWidth <= 80) { // Min %20, Max %80
          setLeftWidth(newLeftWidth);
        }
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handlePdfLoad = () => {
    setPdfLoading(false);
  };

  const handlePdfError = () => {
    setPdfLoading(false);
    setPdfError('PDF yüklenemedi. URL erişilebilir değil veya dosya bulunamadı.');
  };

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



  // Alan değiştiğinde dal listesini güncelle (COP URLs'leri useEffect ile hallonuyor)
  const handleAlanChange = (alanId) => {
    console.log('Alan değişti:', alanId);
    setEditData(prev => ({ ...prev, alan_id: alanId, dal_id: '' }));
  };

  // Handle COP PDF selection
  const handleCopSelect = (pdfUrl, title) => {
    onShowPDF(pdfUrl, title);
  };
  
  // Handle DBF PDF selection
  const handleDbfSelect = (pdfUrl, title) => {
    onShowPDF(pdfUrl, title);
  };
  
  // Handle PDF button clicks
  const handlePdfButtonClick = (url, title) => {
    onShowPDF(url, title);
  };

  
  if (!isOpen) return null;

  // Normal sidebar mode (no PDF)
  if (!isSplitMode) {
    return (
      <div className="edit-sidebar-container">
        {/* Header */}
        <div className="edit-sidebar-header">
          <div>
            <h3>{editData.ders_adi || 'Ders Adı'}</h3>
            <div className="edit-sidebar-pdf-links">
              {editData.dm_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dm_url, 'DM')}
                  className="edit-sidebar-pdf-button dm"
                >
                  DM
                </button>
              )}
              {editData.dbf_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dbf_url, 'DBF')}
                  className="edit-sidebar-pdf-button dbf"
                >
                  DBF
                </button>
              )}
              {editData.bom_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.bom_url, 'BOM')}
                  className="edit-sidebar-pdf-button bom"
                >
                  BOM
                </button>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="edit-sidebar-close-button"
          >
            ×
          </button>
        </div>

        {/* Form Content - Scrollable */}
        <div className="edit-sidebar-content">
          {/* Alan-Dal Seçimi */}
          <div className="alan-dal-selection-section">
            <div className="alan-dal-selection-container">
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
              
              <DbfDropdown 
                courseDbfUrl={editData.dbf_url} 
                onSelectDbf={handleDbfSelect}
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

          {/* Ders Bilgileri */}
          <div className="form-section ders-bilgileri-section">
            {/* Form içeriği buraya eklenebilir */}
          </div>
        </div>
      </div>
    );
  }

  // Split screen mode - PDF açık
  return (
    <div className="edit-sidebar-split-screen">
      {/* Sol Panel - İşlemler */}
      <div 
        className="split-left-panel" 
        style={{ width: `${leftWidth}%` }}
      >
        {/* Header */}
        <div className="edit-sidebar-header">
          <div>
            <h3>{editData.ders_adi || 'Ders Adı'}</h3>
            <div className="current-document-info">
              <span className="document-title">{pdfTitle}</span>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="edit-sidebar-close-button"
          >
            ×
          </button>
        </div>

        {/* Form Content - Scrollable */}
        <div className="edit-sidebar-content">
          {/* Alan-Dal Seçimi */}
          <div className="alan-dal-selection-section">
            <div className="alan-dal-selection-container">
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
              
              <DbfDropdown 
                courseDbfUrl={editData.dbf_url} 
                onSelectDbf={handleDbfSelect}
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

          {/* Ders Bilgileri */}
          <div className="form-section ders-bilgileri-section">
            <MaterialTextField
              label="Ders Adı"
              value={editData.ders_adi}
              onChange={(value) => handleInputChange('ders_adi', value)}
            />
            
            <MaterialTextField
              label="Sınıf"
              value={editData.sinif}
              onChange={(value) => handleInputChange('sinif', value)}
              type="number"
            />
            
            <MaterialTextField
              label="Ders Saati"
              value={editData.ders_saati}
              onChange={(value) => handleInputChange('ders_saati', value)}
              type="number"
            />
          </div>

          {/* Action Buttons */}
          <div className="form-actions">
            <button onClick={handleSave} className="save-button">
              Kaydet
            </button>
            <button onClick={handleCopy} className="copy-button">
              Kopyala
            </button>
          </div>
        </div>
      </div>

      {/* Resize Handle */}
      <div 
        className="resize-handle"
        onMouseDown={handleMouseDown}
        style={{ cursor: isResizing ? 'col-resize' : 'col-resize' }}
      >
        <div className="resize-line"></div>
      </div>

      {/* Sağ Panel - Document Viewer */}
      <div 
        className="split-right-panel" 
        style={{ width: `${100 - leftWidth}%` }}
      >
        {pdfUrl && (
          <DocumentViewer 
            url={pdfUrl} 
            title={pdfTitle}
            onLoad={handlePdfLoad}
            onError={handlePdfError}
            loading={pdfLoading}
            error={pdfError}
          />
        )}
      </div>
    </div>
  );
};

// Document Viewer Component - supports both PDF and DOCX
const DocumentViewer = ({ url, title, onLoad, onError, loading, error }) => {
  const [viewerType, setViewerType] = useState(null);
  const [internalLoading, setInternalLoading] = useState(true);
  
  // Detect file type from URL
  const detectFileType = (fileUrl) => {
    if (!fileUrl) return 'unknown';
    const cleanUrl = fileUrl.split('?')[0].toLowerCase();
    if (cleanUrl.endsWith('.pdf')) return 'pdf';
    if (cleanUrl.endsWith('.docx') || cleanUrl.endsWith('.doc')) return 'docx';
    return 'unknown';
  };

  useEffect(() => {
    const fileType = detectFileType(url);
    setViewerType(fileType);
    setInternalLoading(true);
    
    // Auto-hide loading after 5 seconds as fallback
    const timer = setTimeout(() => {
      setInternalLoading(false);
      console.log('Loading timeout reached, showing content anyway');
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [url]);

  const handleLoad = () => {
    console.log('Document loaded successfully');
    setInternalLoading(false);
    onLoad && onLoad();
  };

  const handleError = () => {
    console.log('Document loading error');
    setInternalLoading(false);
    onError && onError();
  };

  const renderViewer = () => {
    // Show loading only if explicitly loading from parent OR internal loading is true
    const showLoading = loading || (internalLoading && viewerType !== null);
    
    if (showLoading) {
      return (
        <div className="document-viewer-loading">
          <div className="loading-spinner"></div>
          <p>Belge yükleniyor...</p>
          <p className="loading-timeout-info">
            {internalLoading ? 'İçerik yükleniyor...' : 'Yükleme tamamlanıyor...'}
          </p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="document-viewer-error">
          <div className="error-icon">⚠️</div>
          <p>{error}</p>
          <button onClick={() => window.open(url, '_blank')} className="open-external-btn">
            Harici Olarak Aç
          </button>
        </div>
      );
    }

    switch (viewerType) {
      case 'pdf':
        // For PDF, hide loading immediately after render
        setTimeout(() => {
          if (internalLoading) {
            setInternalLoading(false);
            console.log('PDF object rendered, hiding loading');
          }
        }, 1000);
        
        return (
          <object
            data={url}
            type="application/pdf"
            className="document-viewer-frame"
            onLoad={handleLoad}
            onError={(e) => {
              console.error('PDF object load error:', e);
              handleError(e);
            }}
            title={title}
          >
            <div style={{padding: '20px', textAlign: 'center'}}>
              <p>PDF görüntülenemiyor.</p>
              <a 
                href={url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block',
                  padding: '10px 20px',
                  backgroundColor: '#007bff',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  marginTop: '10px'
                }}
              >
                📄 Dosyayı Yeni Sekmede Aç
              </a>
            </div>
          </object>
        );
      
      case 'docx':
        // For DOCX files, we'll use ViewerJS or Office Online Viewer
        const viewerUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
        
        // For DOCX, hide loading after 2 seconds (Office Online takes longer)
        setTimeout(() => {
          if (internalLoading) {
            setInternalLoading(false);
            console.log('DOCX iframe rendered, hiding loading');
          }
        }, 2000);
        
        return (
          <iframe
            src={viewerUrl}
            className="document-viewer-frame"
            onLoad={handleLoad}
            onError={handleError}
            title={title}
          />
        );
      
      default:
        return (
          <div className="document-viewer-unknown">
            <div className="unknown-file-icon">📄</div>
            <p>Bu dosya türü önizlenemiyor</p>
            <p className="file-type-info">Desteklenen: PDF, DOCX</p>
            <button onClick={() => window.open(url, '_blank')} className="open-external-btn">
              Dosyayı İndir/Aç
            </button>
          </div>
        );
    }
  };

  return (
    <div className="document-viewer-container">
      <div className="document-viewer-header">
        <span className="document-title">{title}</span>
        <div className="document-actions">
          <button 
            onClick={() => window.open(url, '_blank')} 
            className="external-link-btn"
            title="Yeni sekmede aç"
          >
            ↗️
          </button>
        </div>
      </div>
      <div className={`document-viewer-content ${(loading || internalLoading) ? 'loading' : ''}`}>
        {renderViewer()}
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
    <div className="filter-dropdown">
      <div className="filter-dropdown-header">
        <strong>{displayName} Filtresi</strong>
        <div>
          <button 
            onClick={onClear}
            className="filter-clear-btn"
          >
            Temizle
          </button>
          <button 
            onClick={onToggle}
            className="filter-close-btn"
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
        className="filter-search-input"
        autoFocus
        onClick={(e) => e.stopPropagation()}
      />
      
      {filteredItems.map(([value, count]) => (
        <div key={value} className="filter-item">
          <label className="filter-item-label">
            <input
              type="checkbox"
              checked={selectedValues.includes(String(value))}
              onChange={(e) => onFilterChange(String(value), e.target.checked)}
              className="filter-item-checkbox"
            />
            <span>{value || 'Boş'} ({count})</span>
          </label>
        </div>
      ))}
    </div>
  );
};

const DataTable = ({ tableData, searchTerm, onCourseEdit, onDocumentView }) => {
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
    if (!columnStats[column] || !columnStats[column].items) return [];
    
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
      <div className="table-summary">
        <strong>Toplam: {sortedData.length} ders</strong>
      </div>
      <table className="comprehensive-data-table">
        <thead>
          <tr>
            {['alan_adi', 'dal_adi', 'ders_adi', 'sinif', 'ders_saati'].map(column => (
              <th key={column} onClick={() => handleSort(column)} className="sortable-header">
                <div className="header-content">
                  <span>
                    {getColumnDisplayName(column)} {getSortIcon(column)}
                    <span className="column-count">
                      ({columnStats[column] && columnStats[column].uniqueCount || 0})
                    </span>
                  </span>
                  <button 
                    onClick={(e) => { e.stopPropagation(); toggleFilter(column); }}
                    className="filter-toggle-btn"
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
                ) : ("-")}
              </td>
              <td>
                {row.dbf_url ? (
                  <button 
                    onClick={() => onDocumentView && onDocumentView(row, row.dbf_url, 'DBF')}
                    className="dbf-link-btn"
                    title="DBF dosyasını görüntüle"
                  >
                    📄 DBF
                  </button>
                ) : ("-")}
              </td>
              <td>
                {row.bom_url ? (
                  <a href={row.bom_url} target="_blank" rel="noopener noreferrer" className="bom-link">
                    📄 BOM
                  </a>
                ) : ("-")}
              </td>
              <td>
                {row.ders_id && row.dbf_url && row.dbf_url.trim() !== '' ? (
                  <button 
                    className="edit-btn" 
                    onClick={() => onCourseEdit && onCourseEdit(row)}
                    title="Düzenle"
                  >
                    ✏️
                  </button>
                ) : ("-")}
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
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
  // viewMode removed - only table view now
  const [editingSidebar, setEditingSidebar] = useState({ isOpen: false, course: null });
  const [editedCourses, setEditedCourses] = useState(new Map()); // Store edited course data
  const [pdfSidebar, setPdfSidebar] = useState({ isOpen: false, url: '', title: '' });

  // Kategorik veri state'leri
  const [copData, setCopData] = useState(null);
  const [catLoading, setCatLoading] = useState(""); // "dbf", "cop", "dm", "bom"
  const [catError, setCatError] = useState("");

  // İstatistik state'leri
  const [stats, setStats] = useState({
    total_alan: 0,
    cop_url_count: 0,
    dbf_url_count: 0,
    ders_count: 0,
    dal_count: 0,
    ders_dal_relations: 0,
    ogrenme_birimi_count: 0,
    konu_count: 0,
    kazanim_count: 0,
    cop_pdf: 0,
    dbf_rar: 0,
    dbf_pdf: 0,
    dbf_docx: 0,
    dm_pdf: 0,
    bom_pdf: 0,
    summary_message: ""
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
        console.log(`${tableDataResponse.length} ders veritabanından yüklendi.`);
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
        console.log(message);
      } else if (isInitialLoad) {
        console.log("Önbellek boş. Verileri çekmek için butona tıklayın.");
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
        console.log(eventData.message || eventData);
        eventSource.close();
        setLoading(false);
      } else {
        console.log(eventData.message || eventData);
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

  // Kategori veri çekme fonksiyonları
  const fetchDbf = useCallback(() => {
    if (loading || catLoading) return;

    setCatLoading("dbf");
    setCatError("");
    console.log('DBF verileri çekiliyor...');

    const eventSource = new EventSource("http://localhost:5001/api/get-dbf");

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        console.log(eventData.message || eventData);
        if (eventData.type === "done" || eventData.type === "error") {
          setCatLoading("");
          loadStatistics(); // İstatistikleri yeniden yükle
          eventSource.close();
        }
      } catch (e) {
        const errorMsg = "Gelen DBF verisi işlenemedi: " + e.message;
        setCatError(errorMsg);
        console.error(errorMsg);
        setCatLoading("");
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      const errorMsg = "DBF indirme bağlantı hatası veya sunucu yanıt vermiyor.";
      setCatError(errorMsg);
      console.error(errorMsg);
      setCatLoading("");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [loading, catLoading, loadStatistics]);
  const fetchCop = useCallback(() => {
    if (loading || catLoading) return;

    setCatLoading("cop");
    setCatError("");
    console.log('ÇÖP linkleri çekiliyor...');

    const eventSource = new EventSource("http://localhost:5001/api/get-cop");

    eventSource.onmessage = (event) => {
            try {
                const eventData = JSON.parse(event.data);
                
                if (eventData.type === "area_processing") {
                    console.log(`Alan işleniyor: ${eventData.area_name} ${eventData.area_progress}`);
                } else if (eventData.type === "branches_processing") {
                    console.log(`Dallar işleniyor: ${eventData.branches_count}/${eventData.total_branches}`);
                } else if (eventData.type === "done" || eventData.type === "error") {
                    setCatLoading("");
                    loadStatistics(); // İstatistikleri yeniden yükle
                    eventSource.close();
                    if (eventData.type === "error") {
                        setCatError("Alan-Dal hatası: " + eventData.message);
                    } else {
                        console.log(eventData.message || "Alan-Dal işlemi tamamlandı.");
                    }
                } else {
                    console.log(eventData.message || eventData);
                }
            } catch (e) {
                const errorMsg = "Gelen Alan-Dal verisi işlenemedi: " + e.message;
                setCatError(errorMsg);
                console.error(errorMsg, "Raw data:", event.data);
                setCatLoading("");
                eventSource.close();
            }
        };

    eventSource.onerror = (err) => {
      const errorMsg = "ÇÖP indirme bağlantı hatası veya sunucu yanıt vermiyor.";
      setCatError(errorMsg);
console.error(errorMsg);
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
    console.log('DM verileri çekiliyor...');
    
    try {
      const eventSource = new EventSource("http://localhost:5001/api/get-dm");
      
      eventSource.onmessage = function(event) {
        try {
          const data = JSON.parse(event.data);
          console.log(`DM: ${data.message || JSON.stringify(data)}`);
          
          // İşlem tamamlandığında
          if (data.type === 'done' || data.type === 'error') {
            eventSource.close();
            setCatLoading("");
            
            if (data.type === 'error') {
              setCatError("DM: " + data.message);
            } else {
              // Disk dosyalarından gerçek istatistikleri yükle
              loadStatistics();
            }
          }
        } catch (e) {
          console.error('DM JSON parse hatası:', e);
          setCatError("DM: JSON parse hatası");
          eventSource.close();
          setCatLoading("");
        }
      };
      
      eventSource.onerror = function(event) {
        console.error('DM SSE hatası:', event);
        setCatError("DM: Bağlantı hatası");
        eventSource.close();
        setCatLoading("");
      };
      
    } catch (e) {
      setCatError("DM: " + e.message);
      console.error('DM hatası: ' + e.message);
    } finally {
      setCatLoading("");
    }
  };
  const fetchBom = useCallback(() => {
    if (loading || catLoading) return;

    setCatLoading("bom");
    setCatError("");
    console.log('BOM verileri çekiliyor...');

    const eventSource = new EventSource("http://localhost:5001/api/get-bom");

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        console.log(eventData.message || eventData);
        
        if (eventData.type === "done" || eventData.type === "error") {
          setCatLoading("");
          loadStatistics(); // İstatistikleri yeniden yükle
          eventSource.close();
          if (eventData.type === "error") {
            setCatError("BOM hatası: " + eventData.message);
          }
        }
      } catch (e) {
        const errorMsg = "Gelen BOM verisi işlenemedi: " + e.message;
        setCatError(errorMsg);
        console.error(errorMsg, "Raw data:", event.data);
        setCatLoading("");
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      const errorMsg = "BOM indirme bağlantı hatası veya sunucu yanıt vermiyor.";
      setCatError(errorMsg);
      console.error(errorMsg);
      setCatLoading("");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [loading, catLoading, loadStatistics]);

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
    return createCopMapping(copData && copData.data);
  }, [copData, createCopMapping]);

  // Course editing functions
  const handleCourseEdit = useCallback((course) => {
    console.log('handleCourseEdit called with:', course);
    setEditingSidebar({ isOpen: true, course });
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setEditingSidebar({ isOpen: false, course: null });
    setPdfSidebar({ isOpen: false, url: '', title: '' }); // PDF sidebar'ı da kapat
  }, []);

  const handleShowPDF = useCallback((url, title) => {
    setPdfSidebar({ isOpen: true, url, title });
  }, []);

  // DBF document viewer handler
  const handleDocumentView = useCallback((course, url, title) => {
    // Open the course editor and show the document
    setEditingSidebar({ isOpen: true, course });
    setPdfSidebar({ isOpen: true, url, title });
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
      console.log(`"${editedData.ders_adi}" dersi başarıyla güncellendi.`);

      // Reload table data to reflect changes
      await loadTableData();
      
    } catch (error) {
      console.error(`Ders güncelleme hatası: ${error.message}`);
    }
  }, [loadTableData]);

  const handleExportToDatabase = useCallback(async () => {
    if (editedCourses.size === 0) {
      console.warn('Veritabanına aktarılacak düzenlenmiş ders bulunamadı.');
      return;
    }

    try {
      const exportData = Array.from(editedCourses.values());
      
      console.log(`${exportData.length} ders veritabanına aktarılıyor...`);
      
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
      console.log(result.message || `${result.success} ders başarıyla kaydedildi!`);
      
      // Detaylı sonuçları göster
      if (result.results && result.results.length > 0) {
        result.results.forEach(res => {
          if (res.status === 'error') {
            console.error(`❌ ${res.course}: ${res.message}`);
          } else {
            console.log(`✅ ${res.course}: Başarıyla kaydedildi (ID: ${res.ders_id})`);
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
      console.error(`Veritabanına aktarım hatası: ${error.message}`);
    }
  }, [editedCourses]);

  // ÇÖP PDF işleme fonksiyonu
  const handleProcessCopPdfs = useCallback(() => {
    if (!window.confirm('ÇÖP PDF\'lerini işleyip alan-dal-ders ilişkilerini çıkararak veritabanına kaydetmek istediğinize emin misiniz? Bu işlem uzun sürebilir.')) {
      return;
    }

    setError(null);
    setCopProcessing(true);
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
      
      console.log(eventData.message || eventData);

      if (eventData.type === 'done') {
        setCopProcessing(false);
        eventSource.close();
        console.log('ÇÖP işleme tamamlandı. Tablo güncelleniyor...');
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

    setError(null);
    setDbfProcessing(true);
    // Reset DBF read count
    setStats(prev => ({ ...prev, dbf_okunan: 0 }));

    const eventSource = new EventSource('http://localhost:5001/api/oku-dbf');

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
      
      console.log(eventData.message || eventData);

      if (eventData.type === 'done') {
        setDbfProcessing(false);
        eventSource.close();
        console.log('DBF işleme tamamlandı. Tablo güncelleniyor...');
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

    setError(null);
    setLoading(true);

    const eventSource = new EventSource('http://localhost:5001/api/get-dal');

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        
        // Format console output based on message type
        if (eventData.type === 'province_summary') {
          const { province_name, province_progress, alan_sayisi_province, alan_sayisi_total_province, 
                  dal_sayisi_province, dal_sayisi_total_so_far } = eventData;
          
          // Tek satır: Şehir adı (sıra/toplam), toplam Alan/Dal sayısı -> veritabanına eklenen Alan/Dal sayısı
          console.log(`${province_name} ${province_progress}, Alan/Dal Sayısı (${alan_sayisi_total_province}/${dal_sayisi_province}) -> (${alan_sayisi_province}/${dal_sayisi_province})`)
        } else if (eventData.type === 'area_processing') {
          // Alan işleme mesajlarını gizle - çok fazla detay
          // const { area_name, area_progress } = eventData;
          // console.log(`📋 ${area_name} ${area_progress} işleniyor...`);
        } else if (eventData.type === 'branches_processing') {
          // Dal işleme mesajlarını gizle - çok fazla detay
          // const { branches_count, total_branches } = eventData;
          // console.log(`🌿 ${branches_count} dal bulundu (Toplam: ${total_branches})`);
        } else if (eventData.type === 'success') {
          console.log(`✅ ${eventData.message}`);
        } else if (eventData.type === 'status') {
          console.log(`ℹ️ ${eventData.message}`);
        } else if (eventData.type === 'warning') {
          console.log(`⚠️ ${eventData.message}`);
        } else if (eventData.type === 'error') {
          console.log(`❌ HATA: ${eventData.message}`);
          setError(eventData.message || "Bilinmeyen bir hata oluştu.");
          setLoading(false);
          eventSource.close();
          return;
        } else if (eventData.type === 'done') {
          console.log(`✅ ${eventData.message}`);
          loadStatistics(); // Son ve en doğru istatistikleri veritabanından çek
          loadTableData(); // Tabloyu yeniden yükle
          eventSource.close();
          setLoading(false);
          return;
        } else {
          // Fallback for any other message types
          console.log(eventData.message || eventData);
        }

        // Anlık istatistik güncellemesi için yeni eklenen bölüm
        if (eventData.type === 'progress' && eventData.total_areas !== undefined && eventData.total_branches !== undefined) {
          setStats(prevStats => ({
            ...prevStats,
            alan: eventData.total_areas,
            dal: eventData.total_branches
          }));
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
          <div className="app-header">
            <h1>meslek.meb (alan-dal-ders) dosyalar</h1>
          </div>
          
          {/* Yeni Tek Satır İş Akışı */}
          <div className="workflow-container">
            
            {/* Tek Satır Buton Dizisi */}
            <div className="workflow-buttons">
              {/* 1. Getir Alan ve Dal */}
              <button
                onClick={handleGetirAlanDal}
                disabled={loading}
                className="workflow-button getir-alan-dal"
              >
                <div>Getir Alan/Dal</div>
                <div>({(stats.alan_count || stats.alan)}/{(stats.dal_count || stats.dal)})</div>
              </button>

              {/* 2. Getir COP */}
              <button
                onClick={fetchCop}
                disabled={loading || catLoading === "cop"}
                className="workflow-button getir-cop"
              >
                <div>Getir ÇÖP</div>
                <div>({stats.cop_pdf} Dosya)</div>
              </button>

              {/* 3. Getir DBF */}
              <button
                onClick={fetchDbf}
                disabled={loading || catLoading === "dbf"}
                className="workflow-button getir-dbf"
              >
                <div>Getir DBF</div>
                <div>({stats.dbf_total || (stats.dbf_rar + stats.dbf_pdf + stats.dbf_docx)} Dosya)</div>
              </button>

              {/* 4. Getir DM */}
              <button
                onClick={fetchDm}
                disabled={loading || catLoading === "dm"}
                className="workflow-button getir-dm"
              >
                <div>Getir DM</div>
                <div>({stats.dm_pdf} Dosya)</div>
              </button>

              {/* 5. Getir BOM */}
              <button
                onClick={fetchBom}
                disabled={loading || catLoading === "bom"}
                className="workflow-button getir-bom"
              >
                <div>Getir BOM</div>
                <div>({stats.bom_total || stats.bom_pdf} Dosya)</div>
              </button>

              {/* 6. Oku COP */}
              <button
                onClick={handleProcessCopPdfs}
                disabled={loading || copProcessing}
                className="workflow-button oku-cop"
              >
                <div>Oku COP</div>
                <div>({stats.ders_count} Ders)</div>
              </button>

              {/* 7. Oku DBF */}
              <button
                onClick={handleUpdateDersSaatleri}
                disabled={loading || dbfProcessing}
                className="workflow-button oku-dbf"
              >
                <div>Oku DBF</div>
                <div>({stats.ders_count} Ders)</div>
              </button>
            </div>

            {/* Durum Göstergeleri */}
            <div className="workflow-status">
              {(catLoading || loading || copProcessing || dbfProcessing) && (
                <div className="workflow-status loading">
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
              {catError && <div className="workflow-status error">❌ Hata: {catError}</div>}
            </div>
          </div>

          {/* Arama Kutusu */}
          {!initialLoading && tableData.length > 0 && (
            <div className="search-bar-container">
              <input
                type="text"
                placeholder="Alan, dal veya ders adına göre filtrele..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="search-input"
              />
            </div>
          )}


          {initialLoading ? (
            <div className="initial-loading">
              Yükleniyor...
            </div>
          ) : (
            <>
              {/* Ana İçerik */}
              <div className="main-content">
                {initialLoading ? (
                  <p>Veriler yükleniyor...</p>
                ) : error ? (
                  <p className="error-message">{error}</p>
                ) : (
                  <DataTable 
                    tableData={tableData}
                    searchTerm={debouncedTerm}
                    onCourseEdit={handleCourseEdit}
                    onDocumentView={handleDocumentView}
                  />
                )}
              </div>

              {/* Düzenleme Kenar Çubuğu - Birleşik Split Screen */}
              <CourseEditSidebar
                course={editingSidebar.course}
                isOpen={editingSidebar.isOpen}
                onClose={handleCloseSidebar}
                onSave={handleSaveCourse}
                onShowPDF={handleShowPDF}
                pdfUrl={pdfSidebar.url}
                pdfTitle={pdfSidebar.title}
              />
            </>
          )}
    </div>
  );
}

export default App;