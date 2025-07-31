import React, { useState, useEffect } from 'react';
import './CourseEditor.css'; // Same CSS file for consistent styling

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
    // DocumentViewer URL changed
    
    if (!url) {
      setDebugInfo('URL boş');
      return;
    }
    
    const fileType = detectFileType(url);
    setViewerType(fileType);
    
    // For PDF, never show loading since server is confirmed working
    if (fileType === 'pdf') {
      console.log('🔍 PDF detected - setting internalLoading to false');
      setInternalLoading(false);
    } else {
      console.log('🔍 Non-PDF file - setting internalLoading to true');
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
    // Document loaded
    setInternalLoading(false);
    setDebugInfo(prev => prev + ' | Loaded');
    if (loadTimer) clearTimeout(loadTimer);
    onLoad && onLoad();
  };

  const handleError = (e) => {
    console.log('❌ Document loading error');
    setInternalLoading(false);
    setDebugInfo(prev => prev + ' | Error: ' + (e?.message || 'Unknown'));
    if (loadTimer) clearTimeout(loadTimer);
    onError && onError();
  };

  // Debug loading states
  useEffect(() => {
    // Loading state debug (reduced)
    
    if (url && viewerType === 'pdf') {
      // PDF loading disabled
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

    // Rendering viewer

    switch (viewerType) {
      case 'pdf':
        // Clean PDF viewer - no loading for PDFs, direct display
        const pdfUrl = url.startsWith('http') ? url : `http://localhost:5001/api/files/${encodeURIComponent(url)}`;
        // PDF URL ready
        
        return (
          <div style={{ height: '100%', width: '100%' }}>
            <iframe
              src={pdfUrl}
              className="document-viewer-frame"
              style={{ width: '100%', height: '100%', border: 'none' }}
              title={title}
              onLoad={() => {
                // PDF loaded
                handleLoad();
              }}
              onError={(e) => {
                console.log('❌ PDF loading error');
                handleError(e);
              }}
            />
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

// Main CourseSideViewer Component - Split-screen layout with document viewer
const CourseSideViewer = ({ 
  isOpen, 
  pdfUrl, 
  pdfTitle, 
  children, 
  onClose, 
  sidebarStyle 
}) => {
  // Split pane için state'ler
  const [leftWidth, setLeftWidth] = useState(50); // Percentage
  const [isResizing, setIsResizing] = useState(false);
  
  // PDF loading states
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState(null);
  
  // Split screen mode - PDF açık mı?
  const isSplitMode = Boolean(pdfUrl);

  // PDF URL değiştiğinde loading state'ini sıfırla - PDF için loading disable
  useEffect(() => {
    if (pdfUrl) {
      // PDF URL changed - disabling loading
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

  if (!isOpen) return null;

  // Normal sidebar mode (no PDF)
  if (!isSplitMode) {
    return (
      <div 
        className="edit-sidebar-container"
        style={sidebarStyle}
      >
        {children}
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
        {children}
      </div>
    </div>
  );
};

export default CourseSideViewer;