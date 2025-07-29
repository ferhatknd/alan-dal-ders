import React, { useState, useEffect } from 'react';
import './CourseEditor.css';

// COP Dropdown Bileşeni - DBF ile aynı yapıda
const CopDropdown = ({ copUrls, onSelectCop }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  console.log('🔍 CopDropdown render - copUrls:', copUrls);
  console.log('🔍 CopDropdown - copUrls type:', typeof copUrls);
  console.log('🔍 CopDropdown - keys:', copUrls ? Object.keys(copUrls) : 'null');
  
  if (!copUrls || Object.keys(copUrls).length === 0) {
    console.log('❌ CopDropdown: COP URL\'leri bulunamadı veya boş');
    return (
      <div className="dropdown-container disabled">
        <button className="dropdown-toggle disabled" disabled>
          ÇÖP Yok ❌
        </button>
      </div>
    );
  }
  
  const copList = Object.entries(copUrls).map(([key, urlData]) => {
    // URL data can be string or object
    const actualUrl = typeof urlData === 'object' && urlData.url ? urlData.url : urlData;
    const updateYear = typeof urlData === 'object' && urlData.update_year ? urlData.update_year : '';
    
    return {
      label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : /^\d+$/.test(key) ? `${key}. Sınıf` : key,
      url: actualUrl,
      updateYear: updateYear,
      key: key
    };
  });
  
  console.log('CopDropdown: COP listesi oluşturuldu:', copList);
  
  return (
    <div className="dropdown-container">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="dropdown-toggle"
      >
        ÇÖP {isOpen ? '▲' : '▼'}
      </button>
      {isOpen && (
        <div className="dropdown-menu">
          {copList.map(item => (
            <button
              key={item.key}
              onClick={() => {
                console.log('🔗 COP seçildi:', item.url);
                onSelectCop(item.url, `ÇÖP - ${item.label}`);
                setIsOpen(false);
              }}
              className="dropdown-item"
            >
              {item.label} {item.updateYear && `(${item.updateYear})`}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// DBF Dropdown Bileşeni - COP ile aynı yapıda
const DbfDropdown = ({ dbfUrls, onSelectDbf }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  console.log('🔍 DbfDropdown render - dbfUrls:', dbfUrls);
  console.log('🔍 DbfDropdown - dbfUrls type:', typeof dbfUrls);
  console.log('🔍 DbfDropdown - keys:', dbfUrls ? Object.keys(dbfUrls) : 'null');
  
  if (!dbfUrls || Object.keys(dbfUrls).length === 0) {
    console.log('❌ DbfDropdown: DBF URL\'leri bulunamadı veya boş');
    return (
      <div className="dropdown-container disabled">
        <button className="dropdown-toggle disabled" disabled>
          DBF Yok ❌
        </button>
      </div>
    );
  }
  
  const dbfList = Object.entries(dbfUrls).map(([key, url]) => ({
    label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : /^\d+$/.test(key) ? `${key}. Sınıf` : key,
    url: url,
    key: key
  }));
  
  console.log('DbfDropdown: DBF listesi oluşturuldu:', dbfList);
  
  return (
    <div className="dropdown-container">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="dropdown-toggle"
      >
        DBF {isOpen ? '▲' : '▼'}
      </button>
      {isOpen && (
        <div className="dropdown-menu">
          {dbfList.map(item => (
            <button
              key={item.key}
              onClick={() => {
                window.open(item.url, '_blank');
                setIsOpen(false);
              }}
              className="dropdown-item"
            >
              {item.label} (RAR)
            </button>
          ))}
        </div>
      )}
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

// DOCX to PDF Converter Component - CLAUDE.md prensibi: cache-aware conversion
const DocxToPdfViewer = ({ url, title, onLoad, onError }) => {
  const [conversionState, setConversionState] = useState('idle'); // idle, converting, success, error, fallback
  const [pdfUrl, setPdfUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [cacheStatus, setCacheStatus] = useState(false);

  const convertToPdf = async () => {
    try {
      setConversionState('converting');
      
      // URL'den relative path'i çıkar (localhost:5001/api/files/ kısmını kaldır)
      const relativePath = url.replace('http://localhost:5001/api/files/', '');
      const decodedPath = decodeURIComponent(relativePath);
      
      console.log('🔄 Converting DOCX to PDF:', decodedPath);
      
      const response = await fetch('http://localhost:5001/api/convert-docx-to-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: decodedPath
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setPdfUrl(result.pdf_url);
        setCacheStatus(result.cached);
        setConversionState('success');
        
        // LibreOffice vs PyMuPDF feedback
        if (result.message && result.message.includes('Warning')) {
          console.log('⚠️ DOCX to PDF (PyMuPDF fallback):', result.pdf_url);
          setErrorMessage(result.message); // Show warning about image quality
        } else {
          console.log('✅ DOCX to PDF (LibreOffice):', result.pdf_url);
        }
        
        onLoad && onLoad();
      } else {
        console.error('❌ DOCX to PDF conversion failed:', result.error);
        setErrorMessage(result.error);
        setConversionState('fallback'); // Fallback to download interface
      }
      
    } catch (error) {
      console.error('❌ DOCX to PDF request failed:', error);
      setErrorMessage(error.message);
      setConversionState('fallback'); // Fallback to download interface
    }
  };

  useEffect(() => {
    if (url && conversionState === 'idle') {
      convertToPdf();
    }
  }, [url]);

  // Render based on conversion state
  switch (conversionState) {
    case 'converting':
      return (
        <div style={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center', 
          justifyContent: 'center',
          padding: '40px',
          textAlign: 'center',
          background: '#f8f9fa'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔄</div>
          <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>DOCX → PDF Dönüştürülüyor</h3>
          <p style={{ margin: '0 0 20px 0', color: '#666', fontSize: '14px' }}>
            Lütfen bekleyin, belge PDF formatına çevriliyor...
          </p>
          <div className="loading-spinner"></div>
        </div>
      );
      
    case 'success':
      // PDF başarıyla oluşturuldu, PDF viewer'ı göster
      return (
        <div style={{ height: '100%', width: '100%', position: 'relative' }}>
          <div style={{ 
            position: 'absolute', 
            top: '5px', 
            right: '10px', 
            background: 'rgba(0,0,0,0.7)', 
            color: 'white', 
            padding: '4px 8px', 
            borderRadius: '4px', 
            fontSize: '12px',
            zIndex: 10
          }}>
            {cacheStatus ? '💾 Cache' : '🔄 Yeni'}
            {errorMessage && errorMessage.includes('Warning') && ' ⚠️'}
          </div>
          {errorMessage && errorMessage.includes('Warning') && (
            <div style={{ 
              position: 'absolute', 
              bottom: '10px', 
              left: '10px', 
              right: '10px',
              background: 'rgba(255,193,7,0.9)', 
              color: '#856404',
              padding: '8px', 
              borderRadius: '4px', 
              fontSize: '12px',
              zIndex: 10
            }}>
              ⚠️ LibreOffice bulunamadı, görüntü kalitesi düşük olabilir
            </div>
          )}
          <iframe
            src={pdfUrl}
            style={{ width: '100%', height: '100%', border: 'none' }}
            title={`${title} (PDF)`}
            onLoad={() => {
              console.log('✅ Converted PDF loaded successfully');
              onLoad && onLoad();
            }}
            onError={(e) => {
              console.log('❌ Converted PDF loading error:', e);
              setConversionState('fallback');
              onError && onError();
            }}
          />
        </div>
      );
      
    case 'fallback':
    case 'error':
    default:
      // Conversion başarısız, download interface'e fallback
      return (
        <div style={{ 
          height: '100%', 
          width: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px',
          textAlign: 'center',
          background: '#f8f9fa'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>📄</div>
          <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>DOCX Dosyası</h3>
          <p style={{ margin: '0 0 10px 0', color: '#666', fontSize: '14px' }}>
            PDF dönüştürme başarısız oldu
          </p>
          {errorMessage && (
            <p style={{ margin: '0 0 20px 0', color: '#e74c3c', fontSize: '12px' }}>
              Hata: {errorMessage}
            </p>
          )}
          <div style={{ display: 'flex', gap: '12px', flexDirection: 'column' }}>
            <button 
              onClick={convertToPdf}
              style={{
                padding: '12px 24px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: '500',
                fontSize: '14px',
                cursor: 'pointer'
              }}
            >
              🔄 Tekrar Dönüştür
            </button>
            <a 
              href={url} 
              download
              style={{
                display: 'inline-block',
                padding: '12px 24px',
                backgroundColor: '#007bff',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '6px',
                fontWeight: '500',
                fontSize: '14px'
              }}
            >
              📥 Dosyayı İndir
            </a>
            <button 
              onClick={() => window.open(url, '_blank')}
              style={{
                padding: '10px 20px',
                backgroundColor: 'transparent',
                color: '#007bff',
                border: '1px solid #007bff',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              🔗 Yeni Sekmede Aç
            </button>
          </div>
          <p style={{ 
            fontSize: '12px', 
            color: '#999', 
            marginTop: '20px',
            lineHeight: '1.4'
          }}>
            {url.split('/').pop()}
          </p>
        </div>
      );
  }
};

// Document Viewer Component - supports both PDF and DOCX with enhanced debugging
const DocumentViewer = ({ url, title, onLoad, onError, loading, error }) => {
  const [viewerType, setViewerType] = useState(null);
  const [internalLoading, setInternalLoading] = useState(true);
  const [debugInfo, setDebugInfo] = useState('');
  const [loadTimer, setLoadTimer] = useState(null);
  
  // Detect file type from URL
  const detectFileType = (fileUrl) => {
    if (!fileUrl || typeof fileUrl !== 'string') {
      console.log('⚠️ detectFileType: Invalid URL:', fileUrl, typeof fileUrl);
      return 'unknown';
    }
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
    
    // For PDF, never show loading since server is confirmed working
    if (fileType === 'pdf') {
      setInternalLoading(false);
    } else {
      setInternalLoading(true);
    }
    
    setDebugInfo(`Dosya tipi: ${fileType}, URL: ${url}`);
    
    console.log('📄 DocumentViewer - Dosya tipi:', fileType);
    
    // Clear any existing timer
    if (loadTimer) {
      clearTimeout(loadTimer);
    }
    
    // Only set timeout for non-PDF files
    let timer = null;
    if (fileType !== 'pdf') {
      const timeout = fileType === 'docx' ? 8000 : 3000;
      timer = setTimeout(() => {
        console.log('⏰ Loading timeout reached, showing content anyway');
        setInternalLoading(false);
        setDebugInfo(prev => prev + ' | Timeout reached');
      }, timeout);
      
      setLoadTimer(timer);
    }
    
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
    setDebugInfo(prev => prev + ' | Error: ' + (e?.message || 'Unknown'));
    if (loadTimer) clearTimeout(loadTimer);
    onError && onError();
  };

  // Debug loading states
  useEffect(() => {
    console.log('🔍 LOADING STATE DEBUG:');
    console.log('  URL:', url);
    console.log('  viewerType:', viewerType);
    console.log('  internalLoading:', internalLoading);
    console.log('  loading prop:', loading);
    console.log('  showLoading will be:', loading || internalLoading);
    
    if (url && viewerType === 'pdf') {
      console.log('🚀 PDF detected - disabling loading state completely');
      setInternalLoading(false);
      setDebugInfo(prev => prev + ' | No loading');
    }
  }, [url, viewerType, internalLoading, loading]);

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
        // Clean PDF viewer - no headers, just the content
        return (
          <div style={{ height: '100%', width: '100%' }}>
            {showLoading ? (
              <div style={{ 
                height: '100%',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                flexDirection: 'column',
                background: '#f8f9fa'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '10px' }}>🔄</div>
                <div>Belge yükleniyor...</div>
              </div>
            ) : (
              <iframe
                src={url}
                className="document-viewer-frame"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title={title}
                onLoad={() => {
                  console.log('✅ IFRAME LOADED successfully');
                  handleLoad();
                }}
                onError={(e) => {
                  console.log('❌ IFRAME ERROR:', e);
                  handleError(e);
                }}
              />
            )}
          </div>
        );
      
      case 'docx':
        // DOCX to PDF conversion with cache checking (CLAUDE.md prensibi)
        return <DocxToPdfViewer url={url} title={title} onLoad={handleLoad} onError={handleError} />;
      
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
    <div className="document-viewer-container" style={{ height: '100%' }}>
      {renderViewer()}
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
  const [dbfUrls, setDbfUrls] = useState({});
  
  // Split pane için state'ler
  const [leftWidth, setLeftWidth] = useState(50); // Percentage
  const [isResizing, setIsResizing] = useState(false);
  
  // PDF loading states
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState(null);
  
  // Save feedback states
  const [saveStatus, setSaveStatus] = useState('idle'); // 'idle', 'saving', 'success', 'error'
  const [saveMessage, setSaveMessage] = useState('');
  
  // Split screen mode - PDF açık mı?
  const isSplitMode = Boolean(pdfUrl);
  
  // Flexible sidebar width - max 50% of viewport width
  const calculateFlexibleSidebarStyle = () => {
    const courseName = editData.ders_adi || 'Ders Adı';
    const charCount = courseName.length;
    
    // Base width calculation
    const baseWidth = Math.max(400, Math.min(charCount * 8 + 200, 800));
    
    console.log(`📏 Flexible sidebar for course "${courseName}" (${charCount} chars), base: ${baseWidth}px`);
    
    return {
      width: `min(${baseWidth}px, 50vw)`, // Never exceed 50% of viewport
      maxWidth: '50vw'
    };
  };
  
  const sidebarStyle = calculateFlexibleSidebarStyle();

  // Fresh ders data'yı yükle - DB'den en güncel veriyi al
  useEffect(() => {
    if (course && course.ders_id && isOpen) {
      console.log(`🔄 Loading fresh data for ders_id: ${course.ders_id}`);
      
      fetch(`http://localhost:5001/api/load?type=ders&id=${course.ders_id}`)
        .then(response => response.json())
        .then(result => {
          if (result.success && result.data) {
            console.log('✅ Fresh ders data loaded:', result.data);
            console.log('🎯 AMAC DEBUG - Raw amac from DB:', result.data.amac);
            console.log('🎯 AMAC DEBUG - Type:', typeof result.data.amac);
            console.log('🎯 AMAC DEBUG - Length:', result.data.amac ? result.data.amac.length : 'null/undefined');
            
            setEditData({
              ders_id: result.data.ders_id || '',
              ders_adi: result.data.ders_adi || '',
              sinif: result.data.sinif || '',
              ders_saati: result.data.ders_saati || '',
              alan_id: result.data.alan_id || '',
              dal_id: result.data.dal_id || '',
              dm_url: result.data.dm_url || '',
              dbf_url: result.data.dbf_url || '',
              bom_url: result.data.bom_url || '',
              amac: result.data.amac || ''
            });
          } else {
            console.error('❌ Fresh data loading failed:', result.error);
            // Fallback to passed course data
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
        })
        .catch(error => {
          console.error('❌ Fresh data loading error:', error);
          // Fallback to passed course data
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
        });
    }
  }, [course, isOpen]);

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


  // COP ve DBF URL'lerini alan_id değiştiğinde güncelle
  useEffect(() => {
    if (editData.alan_id && alanDalOptions.alanlar.length > 0) {
      console.log('🔄 COP ve DBF URL\'leri güncelleniyor, alan_id:', editData.alan_id);
      
      const selectedAlan = alanDalOptions.alanlar.find(alan => alan.id === parseInt(editData.alan_id));
      console.log('🔍 selectedAlan bulundu:', selectedAlan);
      
      // COP URL'lerini güncelle
      if (selectedAlan && selectedAlan.cop_url) {
        try {
          const copData = JSON.parse(selectedAlan.cop_url);
          console.log('✅ COP verisi parse edildi:', copData);
          setCopUrls(copData);
        } catch (e) {
          console.log('⚠️ COP verisi JSON değil, string olarak işleniyor:', selectedAlan.cop_url);
          setCopUrls({ 'cop_url': selectedAlan.cop_url });
        }
      } else {
        console.log('❌ Seçilen alan için COP verisi bulunamadı');
        setCopUrls({});
      }
      
      // DBF URL'lerini güncelle (Alan bazlı RAR linkleri)
      if (selectedAlan && selectedAlan.dbf_urls) {
        try {
          const dbfData = JSON.parse(selectedAlan.dbf_urls);
          console.log('✅ DBF verisi parse edildi:', dbfData);
          setDbfUrls(dbfData);
        } catch (e) {
          console.log('⚠️ DBF verisi JSON değil, string olarak işleniyor:', selectedAlan.dbf_urls);
          setDbfUrls({ 'dbf_urls': selectedAlan.dbf_urls });
        }
      } else {
        console.log('❌ Seçilen alan için DBF verisi bulunamadı');
        setDbfUrls({});
      }
    }
  }, [editData.alan_id, alanDalOptions.alanlar]);

  // PDF URL değiştiğinde loading state'ini sıfırla - PDF için loading disable
  useEffect(() => {
    if (pdfUrl) {
      console.log('🔧 PDF URL changed, disabling loading for PDF');
      setPdfLoading(false); // PDF için loading disable
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

  const handleSave = async () => {
    setSaveStatus('saving');
    setSaveMessage('Kaydediliyor...');
    
    try {
      // Call the parent's onSave function and wait for it to complete
      await new Promise((resolve, reject) => {
        // Since onSave might not return a promise, we simulate an async operation
        const result = onSave(editData);
        
        // If onSave returns a promise, wait for it
        if (result && typeof result.then === 'function') {
          result.then(resolve).catch(reject);
        } else {
          // Simulate a brief delay for better UX
          setTimeout(resolve, 500);
        }
      });
      
      setSaveStatus('success');
      setSaveMessage('✅ Başarıyla kaydedildi!');
      
      // Auto-hide success message and close sidebar after 1.5 seconds
      setTimeout(() => {
        setSaveStatus('idle');
        setSaveMessage('');
        onClose();
      }, 1500);
      
    } catch (error) {
      setSaveStatus('error');
      setSaveMessage(`❌ Kaydetme hatası: ${error.message || 'Bilinmeyen hata'}`);
      
      // Auto-hide error message after 3 seconds
      setTimeout(() => {
        setSaveStatus('idle');
        setSaveMessage('');
      }, 3000);
    }
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
    console.log('🔗 DBF PDF seçildi:', pdfUrl, title);
    onShowPDF(pdfUrl, title);
  };

  if (!isOpen) return null;

  // Normal sidebar mode (no PDF) - Yeni layout ile uyumlu
  if (!isSplitMode) {
    return (
      <div 
        className="edit-sidebar-container"
        style={sidebarStyle}
      >
        {/* Header - Split screen ile aynı */}
        <div className="edit-sidebar-header">
          <div className="header-left">
            <h3 className="course-title">{editData.ders_adi || 'Ders Adı'}</h3>
            {editData.dbf_url && (
              <button 
                onClick={() => handleDbfSelect(editData.dbf_url, 'DBF')}
                className="header-dbf-button"
                title="PDF'i aç"
              >
                DBF:{editData.dbf_url.toLowerCase().endsWith('.pdf') ? 'PDF' : 
                     editData.dbf_url.toLowerCase().endsWith('.docx') ? 'DOCX' : 'DBF'}
              </button>
            )}
          </div>
          <button 
            onClick={onClose}
            className="edit-sidebar-close-button"
          >
            ×
          </button>
        </div>

        {/* Form Content - Split screen ile aynı */}
        <div className="edit-sidebar-content">
          {/* Alan-Dal Seçimi - Yeni Layout */}
          <div className="alan-dal-selection-section">
            {/* Alan ve Dal aynı satırda */}
            <div className="alan-dal-row">
              <div className="alan-field">
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
              </div>
              
              <div className="dal-field">
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
            </div>
            
            {/* COP ve DBF Dropdowns - Simetrik */}
            <div className="dropdown-buttons-row">
              <div className="cop-dropdown-wrapper">
                <CopDropdown 
                  copUrls={copUrls} 
                  onSelectCop={handleCopSelect}
                />
              </div>
              
              <div className="dbf-dropdown-wrapper">
                <DbfDropdown 
                  dbfUrls={dbfUrls} 
                  onSelectDbf={() => {}} // Disabled for now
                />
              </div>
            </div>
          </div>

          {/* Ders Bilgileri - Genişletilmiş */}
          <div className="form-section ders-bilgileri-section">
            <MaterialTextField
              label="Ders Adı"
              value={editData.ders_adi}
              onChange={(value) => handleInputChange('ders_adi', value)}
            />
            
            <div className="inline-fields">
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

            <MaterialTextField
              label="Ders Amacı"
              value={editData.amac}
              onChange={(value) => handleInputChange('amac', value)}
              multiline={true}
              rows={3}
            />

            <MaterialTextField
              label="DM URL"
              value={editData.dm_url}
              onChange={(value) => handleInputChange('dm_url', value)}
            />

            <MaterialTextField
              label="BOM URL" 
              value={editData.bom_url}
              onChange={(value) => handleInputChange('bom_url', value)}
            />
          </div>

          {/* Save Feedback */}
          {saveMessage && (
            <div className={`save-feedback ${saveStatus}`}>
              {saveMessage}
            </div>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button 
              onClick={handleSave} 
              className={`save-button ${saveStatus}`}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Kaydediliyor...' : 
               saveStatus === 'success' ? '✅ Kaydedildi' : 'Kaydet'}
            </button>
            <button onClick={handleCopy} className="copy-button">
              Kopyala
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Split screen mode - PDF açık
  return (
    <div className="edit-sidebar-split-screen">
      {/* Sol Panel - Document Viewer (PDF) */}
      <div 
        className="split-left-panel" 
        style={{ width: `${leftWidth}%` }}
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

      {/* Resize Handle */}
      <div 
        className="resize-handle"
        onMouseDown={handleMouseDown}
        style={{ cursor: isResizing ? 'col-resize' : 'col-resize' }}
      >
        <div className="resize-line"></div>
      </div>

      {/* Sağ Panel - İşlemler (Course Editor) */}
      <div 
        className="split-right-panel" 
        style={{ width: `${100 - leftWidth}%` }}
      >
        {/* Header */}
        <div className="edit-sidebar-header">
          <div className="header-left">
            <h3 className="course-title">{editData.ders_adi || 'Ders Adı'}</h3>
            {editData.dbf_url && (
              <button 
                onClick={() => {
                  if (pdfUrl) {
                    onClose(); // PDF açıksa kapat
                  } else {
                    handleDbfSelect(editData.dbf_url, 'DBF'); // PDF kapalıysa aç
                  }
                }}
                className="header-dbf-button"
                title={pdfUrl ? "PDF'i kapat" : "PDF'i aç"}
              >
                DBF:{editData.dbf_url.toLowerCase().endsWith('.pdf') ? 'PDF' : 
                     editData.dbf_url.toLowerCase().endsWith('.docx') ? 'DOCX' : 'DBF'}
              </button>
            )}
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
          {/* Alan-Dal Seçimi - Yeni Layout */}
          <div className="alan-dal-selection-section">
            {/* Alan ve Dal aynı satırda */}
            <div className="alan-dal-row">
              <div className="alan-field">
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
              </div>
              
              <div className="dal-field">
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
            </div>
            
            {/* COP ve DBF Dropdowns - Simetrik */}
            <div className="dropdown-buttons-row">
              <div className="cop-dropdown-wrapper">
                <CopDropdown 
                  copUrls={copUrls} 
                  onSelectCop={handleCopSelect}
                />
              </div>
              
              <div className="dbf-dropdown-wrapper">
                <DbfDropdown 
                  dbfUrls={dbfUrls} 
                  onSelectDbf={() => {}} // Disabled for now
                />
              </div>
            </div>
          </div>

          {/* Ders Bilgileri - Genişletilmiş */}
          <div className="form-section ders-bilgileri-section">
            <MaterialTextField
              label="Ders Adı"
              value={editData.ders_adi}
              onChange={(value) => handleInputChange('ders_adi', value)}
            />
            
            <div className="inline-fields">
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

            <MaterialTextField
              label="Ders Amacı"
              value={editData.amac}
              onChange={(value) => handleInputChange('amac', value)}
              multiline={true}
              rows={3}
            />

            <MaterialTextField
              label="DM URL"
              value={editData.dm_url}
              onChange={(value) => handleInputChange('dm_url', value)}
            />

            <MaterialTextField
              label="BOM URL" 
              value={editData.bom_url}
              onChange={(value) => handleInputChange('bom_url', value)}
            />
          </div>

          {/* Save Feedback */}
          {saveMessage && (
            <div className={`save-feedback ${saveStatus}`}>
              {saveMessage}
            </div>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button 
              onClick={handleSave} 
              className={`save-button ${saveStatus}`}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Kaydediliyor...' : 
               saveStatus === 'success' ? '✅ Kaydedildi' : 'Kaydet'}
            </button>
            <button onClick={handleCopy} className="copy-button">
              Kopyala
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CourseEditor;