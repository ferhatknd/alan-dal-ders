import React, { useState, useEffect } from 'react';
import './CourseEditor.css';

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

// Document Viewer Component - supports both PDF and DOCX with enhanced debugging
const DocumentViewer = ({ url, title, onLoad, onError, loading, error }) => {
  const [viewerType, setViewerType] = useState(null);
  const [internalLoading, setInternalLoading] = useState(true);
  const [debugInfo, setDebugInfo] = useState('');
  const [loadTimer, setLoadTimer] = useState(null);
  
  // Detect file type from URL
  const detectFileType = (fileUrl) => {
    if (!fileUrl) return 'unknown';
    const cleanUrl = fileUrl.split('?')[0].toLowerCase();
    console.log('🔍 Debug - File URL:', fileUrl);
    console.log('🔍 Debug - Clean URL:', cleanUrl);
    
    if (cleanUrl.endsWith('.pdf')) return 'pdf';
    if (cleanUrl.endsWith('.docx') || cleanUrl.endsWith('.doc')) return 'docx';
    return 'unknown';
  };

  useEffect(() => {
    console.log('📄 DocumentViewer - URL değişti:', url);
    
    if (!url) {
      setDebugInfo('URL boş');
      return;
    }
    
    const fileType = detectFileType(url);
    setViewerType(fileType);
    setInternalLoading(true);
    setDebugInfo(`Dosya tipi: ${fileType}, URL: ${url}`);
    
    console.log('📄 DocumentViewer - Dosya tipi:', fileType);
    
    // Clear any existing timer
    if (loadTimer) {
      clearTimeout(loadTimer);
    }
    
    // Auto-hide loading after timeout based on file type
    const timeout = fileType === 'docx' ? 8000 : 3000; // DOCX longer timeout
    const timer = setTimeout(() => {
      console.log('⏰ Loading timeout reached, showing content anyway');
      setInternalLoading(false);
      setDebugInfo(prev => prev + ' | Timeout reached');
    }, timeout);
    
    setLoadTimer(timer);
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [url]);

  const handleLoad = () => {
    console.log('✅ Document loaded successfully');
    setInternalLoading(false);
    setDebugInfo(prev => prev + ' | Loaded');
    if (loadTimer) clearTimeout(loadTimer);
    onLoad && onLoad();
  };

  const handleError = (e) => {
    console.log('❌ Document loading error:', e);
    setInternalLoading(false);
    setDebugInfo(prev => prev + ' | Error');
    if (loadTimer) clearTimeout(loadTimer);
    onError && onError();
  };

  const renderViewer = () => {
    // Show loading only if explicitly loading from parent OR internal loading is true
    const showLoading = loading || internalLoading;
    
    if (showLoading) {
      return (
        <div className="document-viewer-loading">
          <div className="loading-spinner"></div>
          <p>Belge yükleniyor...</p>
          <p className="loading-timeout-info">
            {viewerType && `Dosya tipi: ${viewerType.toUpperCase()}`}
          </p>
          <p className="debug-info" style={{fontSize: '11px', color: '#999', marginTop: '8px'}}>
            Debug: {debugInfo}
          </p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="document-viewer-error">
          <div className="error-icon">⚠️</div>
          <p>{error}</p>
          <p className="debug-info" style={{fontSize: '11px', color: '#666'}}>
            Debug: {debugInfo}
          </p>
          <button onClick={() => window.open(url, '_blank')} className="open-external-btn">
            Harici Olarak Aç
          </button>
        </div>
      );
    }

    console.log('🎯 Rendering viewer for type:', viewerType);

    switch (viewerType) {
      case 'pdf':
        return (
          <object
            data={url}
            type="application/pdf"
            className="document-viewer-frame"
            onLoad={handleLoad}
            onError={handleError}
            title={title}
            style={{ width: '100%', height: '100%' }}
          >
            <div style={{padding: '20px', textAlign: 'center'}}>
              <p>PDF görüntülenemiyor.</p>
              <p style={{fontSize: '12px', color: '#666', marginBottom: '16px'}}>
                URL: {url}
              </p>
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
        // DOCX dosyaları için yerel dosya desteği - Google Docs Viewer kullan
        const viewerUrl = `https://docs.google.com/gview?url=${encodeURIComponent(url)}&embedded=true`;
        console.log('📊 DOCX Viewer URL:', viewerUrl);
        
        return (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '8px', background: '#f0f0f0', fontSize: '12px', color: '#666' }}>
              DOCX Viewer | URL: {url}
            </div>
            <iframe
              src={viewerUrl}
              className="document-viewer-frame"
              onLoad={handleLoad}
              onError={handleError}
              title={title}
              style={{ flex: 1, border: 'none' }}
            />
          </div>
        );
      
      default:
        return (
          <div className="document-viewer-unknown">
            <div className="unknown-file-icon">📄</div>
            <p>Bu dosya türü önizlenemiyor</p>
            <p className="file-type-info">Desteklenen: PDF, DOCX</p>
            <p style={{fontSize: '11px', color: '#666', margin: '8px 0'}}>
              Debug: {debugInfo}
            </p>
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
        <div className="document-title-section">
          <span className="document-title">{title}</span>
          <div className="debug-panel" style={{fontSize: '10px', color: '#666', marginTop: '2px'}}>
            Type: {viewerType || 'detecting...'} | Loading: {internalLoading ? 'yes' : 'no'} | {debugInfo}
          </div>
        </div>
        <div className="document-actions">
          <button 
            onClick={() => console.log('🔗 Full URL:', url)} 
            className="external-link-btn"
            title="URL'yi konsola yazdır"
            style={{marginRight: '4px'}}
          >
            🔍
          </button>
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

const CourseEditor = ({ course, isOpen, onClose, onSave, onShowPDF, pdfUrl, pdfTitle }) => {
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
                onChange={handleAlanChange}
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
                onChange={handleAlanChange}
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

export default CourseEditor;