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


// COP Dropdown Bileşeni
const CopDropdown = ({ copUrls, onSelectCop }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  console.log('CopDropdown render - copUrls:', copUrls);
  
  if (!copUrls || Object.keys(copUrls).length === 0) {
    console.log('CopDropdown: COP URL\'leri bulunamadı veya boş');
    return null;
  }
  
  const copList = Object.entries(copUrls).map(([key, url]) => ({
    label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : key,
    url: url,
    key: key
  }));
  
  console.log('CopDropdown: COP listesi oluşturuldu:', copList);
  
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
        ÇÖP {isOpen ? '▲' : '▼'}
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

// DBF Dropdown Bileşeni
const DbfDropdown = ({ dbfUrls, onSelectDbf }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  console.log('DbfDropdown render - dbfUrls:', dbfUrls);
  console.log('DbfDropdown - dbfUrls type:', typeof dbfUrls);
  console.log('DbfDropdown - dbfUrls keys:', Object.keys(dbfUrls));
  
  if (!dbfUrls || Object.keys(dbfUrls).length === 0) {
    console.log('DbfDropdown: DBF URL\'leri bulunamadı veya boş - return null');
    return null;
  }
  
  const dbfList = Object.entries(dbfUrls).map(([key, url]) => ({
    label: key.includes('sinif_') ? `${key.split('_')[1]}. Sınıf` : `${key}. Sınıf`,
    url: url,
    key: key
  }));
  
  console.log('DbfDropdown: DBF listesi oluşturuldu:', dbfList);
  
  return (
    <div className="dbf-dropdown" style={{ position: 'relative', display: 'inline-block' }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '8px 12px',
          background: '#28a745',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '12px',
          fontWeight: 'bold'
        }}
      >
        DBF {isOpen ? '▲' : '▼'}
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
          {dbfList.map(item => (
            <button
              key={item.key}
              onClick={() => {
                onSelectDbf(item.url, `DBF - ${item.label}`);
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

// Button Group Bileşeni
const ButtonGroup = ({ label, options, value, onChange, maxPerRow = 4 }) => {
  return (
    <div className="form-section" style={{ marginBottom: '20px' }}>
      <div style={{ 
        display: 'flex', 
        flexWrap: 'wrap', 
        gap: '12px',
        alignItems: 'center'
      }}>
        <label style={{ 
          fontSize: '14px', 
          fontWeight: 'bold', 
          color: '#495057',
          minWidth: '60px',
          flexShrink: 0
        }}>
          {label}:
        </label>
        <div style={{ 
          display: 'flex',
          border: '1px solid #dee2e6',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          {options.map((option, index) => (
            <button
              key={option.value}
              onClick={() => onChange(option.value)}
              style={{
                padding: '8px 12px',
                border: 'none',
                backgroundColor: value === option.value ? '#007bff' : '#ffffff',
                color: value === option.value ? '#ffffff' : '#495057',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: value === option.value ? 'bold' : 'normal',
                minWidth: '44px',
                transition: 'all 0.2s ease',
                outline: 'none',
                position: 'relative',
                zIndex: value === option.value ? 2 : 1
              }}
              onMouseOver={(e) => {
                if (value !== option.value) {
                  e.target.style.backgroundColor = '#f8f9fa';
                }
              }}
              onMouseOut={(e) => {
                if (value !== option.value) {
                  e.target.style.backgroundColor = '#ffffff';
                }
              }}
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
  const [dbfUrls, setDbfUrls] = useState({});
  
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
      
      // DBF URL'lerini güncelle
      if (selectedAlan && selectedAlan.dbf_urls) {
        try {
          const dbfData = JSON.parse(selectedAlan.dbf_urls);
          console.log('DBF verisi parse edildi:', dbfData);
          setDbfUrls(dbfData);
        } catch (e) {
          console.log('DBF verisi JSON değil, string olarak işleniyor:', selectedAlan.dbf_urls);
          setDbfUrls({ 'dbf_urls': selectedAlan.dbf_urls });
        }
      } else {
        console.log('Seçilen alan için DBF verisi bulunamadı, selectedAlan:', selectedAlan);
        console.log('selectedAlan.dbf_urls:', selectedAlan?.dbf_urls);
        setDbfUrls({});
      }
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

  console.log('CourseEditSidebar render:', { isOpen, course });
  
  if (!isOpen) return null;

  // Normal sidebar mode (no PDF)
  if (!isSplitMode) {
    return (
      <div 
        className="edit-sidebar"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          width: '600px',
          height: '100vh',
          backgroundColor: '#ffffff',
          borderLeft: '1px solid #dee2e6',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div className="edit-header" style={{
          padding: '20px',
          borderBottom: '1px solid #dee2e6',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h3 style={{ margin: 0, marginBottom: '10px' }}>{editData.ders_adi || 'Ders Adı'}</h3>
            <div className="pdf-links" style={{ display: 'flex', gap: '8px' }}>
              {editData.dm_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dm_url, 'DM')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  DM
                </button>
              )}
              {editData.dbf_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dbf_url, 'DBF')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  DBF
                </button>
              )}
              {editData.bom_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.bom_url, 'BOM')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#ffc107',
                    color: 'black',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  BOM
                </button>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#6c757d'
            }}
          >
            ×
          </button>
        </div>

        {/* Form Content - Scrollable */}
        <div className="edit-content" style={{
          flex: 1,
          padding: '20px',
          overflowY: 'auto'
        }}>
          {/* Alan-Dal Seçimi */}
          <div className="form-section" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
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
                dbfUrls={dbfUrls} 
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
          <div className="form-section" style={{ marginBottom: '20px' }}>
            <MaterialTextField
              label="Ders Adı"
              value={editData.ders_adi}
              onChange={(value) => handleInputChange('ders_adi', value)}
              type="text"
            />
          </div>

          <ButtonGroup
            label="Sınıf"
            value={editData.sinif}
            onChange={(value) => handleInputChange('sinif', value)}
            options={[9, 10, 11, 12].map(sinif => ({
              value: sinif,
              label: `${sinif}`
            }))}
          />

          <ButtonGroup
            label="Saat"
            value={editData.ders_saati}
            onChange={(value) => handleInputChange('ders_saati', value)}
            options={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(saat => ({
              value: saat,
              label: `${saat}`
            }))}
          />

          <div className="form-section" style={{ marginBottom: '20px' }}>
            <MaterialTextField
              label="Dersin Amacı"
              value={editData.amac}
              onChange={(value) => handleInputChange('amac', value)}
              multiline={true}
              rows={4}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="edit-footer" style={{
          padding: '20px',
          borderTop: '1px solid #dee2e6',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          gap: '10px',
          justifyContent: 'flex-end'
        }}>
          <button 
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            İptal
          </button>
          <button 
            onClick={handleCopy}
            style={{
              padding: '8px 16px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Kopyala
          </button>
          <button 
            onClick={handleSave}
            style={{
              padding: '8px 16px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Kaydet
          </button>
        </div>
      </div>
    );
  }

  // Split screen mode (PDF açık)
  return (
    <div 
      className="split-screen-container"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: '#ffffff',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'row'
      }}
    >
      {/* Sol Panel - PDF Viewer */}
      <div 
        className="pdf-panel"
        style={{
          width: `${leftWidth}%`,
          height: '100vh',
          backgroundColor: '#f8f9fa',
          borderRight: '1px solid #dee2e6',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {pdfUrl ? (
          <>
            {pdfLoading && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                color: '#6c757d',
                zIndex: 10
              }}>
                <div style={{ fontSize: '16px' }}>PDF yükleniyor...</div>
              </div>
            )}
            {pdfError && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                color: '#dc3545',
                zIndex: 10
              }}>
                <p>❌ {pdfError}</p>
                <button 
                  onClick={() => window.open(pdfUrl, '_blank')}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
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
              onLoad={handlePdfLoad}
              onError={handlePdfError}
              style={{ 
                display: pdfLoading ? 'none' : 'block',
                border: 'none'
              }}
            />
          </>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#6c757d',
            fontSize: '16px',
            textAlign: 'center'
          }}>
            <div>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
              <div>PDF görüntülemek için DM, DBF, BOM veya ÇÖP butonlarından birine tıklayın</div>
            </div>
          </div>
        )}
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        onMouseDown={handleMouseDown}
        style={{
          width: '8px',
          height: '100vh',
          backgroundColor: '#dee2e6',
          cursor: 'col-resize',
          borderLeft: '1px solid #adb5bd',
          borderRight: '1px solid #adb5bd',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}
      >
        <div style={{
          width: '2px',
          height: '40px',
          backgroundColor: '#6c757d',
          marginRight: '2px'
        }}></div>
        <div style={{
          width: '2px',
          height: '40px',
          backgroundColor: '#6c757d'
        }}></div>
      </div>

      {/* Sağ Panel - Edit Form */}
      <div 
        className="edit-panel"
        style={{
          width: `${100 - leftWidth}%`,
          height: '100vh',
          backgroundColor: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div className="edit-header" style={{
          padding: '20px',
          borderBottom: '1px solid #dee2e6',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h3 style={{ margin: 0, marginBottom: '10px' }}>{editData.ders_adi || 'Ders Adı'}</h3>
            <div className="pdf-links" style={{ display: 'flex', gap: '8px' }}>
              {editData.dm_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dm_url, 'DM')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  DM
                </button>
              )}
              {editData.dbf_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.dbf_url, 'DBF')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  DBF
                </button>
              )}
              {editData.bom_url && (
                <button 
                  onClick={() => handlePdfButtonClick(editData.bom_url, 'BOM')}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    backgroundColor: '#ffc107',
                    color: 'black',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  BOM
                </button>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#6c757d'
            }}
          >
            ×
          </button>
        </div>

        {/* Form Content - Scrollable */}
        <div className="edit-content" style={{
          flex: 1,
          padding: '20px',
          overflowY: 'auto'
        }}>
          {/* Alan-Dal Seçimi */}
          <div className="form-section" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
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
                dbfUrls={dbfUrls} 
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
          <div className="form-section" style={{ marginBottom: '20px' }}>
            <MaterialTextField
              label="Ders Adı"
              value={editData.ders_adi}
              onChange={(value) => handleInputChange('ders_adi', value)}
              type="text"
            />
          </div>

          <ButtonGroup
            label="Sınıf"
            value={editData.sinif}
            onChange={(value) => handleInputChange('sinif', value)}
            options={[9, 10, 11, 12].map(sinif => ({
              value: sinif,
              label: `${sinif}`
            }))}
          />

          <ButtonGroup
            label="Saat"
            value={editData.ders_saati}
            onChange={(value) => handleInputChange('ders_saati', value)}
            options={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(saat => ({
              value: saat,
              label: `${saat}`
            }))}
          />

          <div className="form-section" style={{ marginBottom: '20px' }}>
            <MaterialTextField
              label="Dersin Amacı"
              value={editData.amac}
              onChange={(value) => handleInputChange('amac', value)}
              multiline={true}
              rows={4}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="edit-footer" style={{
          padding: '20px',
          borderTop: '1px solid #dee2e6',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          gap: '10px',
          justifyContent: 'flex-end'
        }}>
          <button 
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            İptal
          </button>
          <button 
            onClick={handleCopy}
            style={{
              padding: '8px 16px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Kopyala
          </button>
          <button 
            onClick={handleSave}
            style={{
              padding: '8px 16px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Kaydet
          </button>
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

  // DBF Dosyalarını indirip açan fonksiyon
  const handleDbfUnrar = useCallback(() => {
    setDbfUnrarLoading(true);
    setDbfUnrarError("");
    setError(null);

    const eventSource = new EventSource("http://localhost:5001/api/dbf-download-extract");

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        console.log(eventData.message || eventData);
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
        console.log(eventData.message || eventData);
        if (eventData.type === "done" || eventData.type === "error") {
          setCatLoading("");
          loadStatistics(); // İstatistikleri yeniden yükle
          eventSource.close();
        }
      } catch (e) {
        const errorMsg = "Gelen indirme verisi işlenemedi: " + e.message;
        setCatError(errorMsg);
        console.error(errorMsg);
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
      const res = await fetch("http://localhost:5001/api/get-dm");
      if (!res.ok) throw new Error("Ders Materyali verisi alınamadı");
      const json = await res.json();
      
      console.log(`DM: ${json.saved_count || 0} ders kaydedildi`);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("DM: " + e.message);
      console.error('DM hatası: ' + e.message);
    } finally {
      setCatLoading("");
    }
  };
  const fetchBom = async () => {
    setCatLoading("bom");
    setCatError("");
    
    // Console'u aç ve mesaj yazdır
    console.log('BOM verileri çekiliyor...');
    
    try {
      const res = await fetch("http://localhost:5001/api/get-bom");
      if (!res.ok) throw new Error("BOM verisi alınamadı");
      const json = await res.json();
      
      console.log(`BOM: ${json.updated_count || 0} ders güncellendi`);
      
      // Disk dosyalarından gerçek istatistikleri yükle
      await loadStatistics();
      
    } catch (e) {
      setCatError("BOM: " + e.message);
      console.error('BOM hatası: ' + e.message);
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
    setPdfSidebar({ isOpen: false, url: '', title: '' }); // PDF sidebar'ı da kapat
  }, []);

  const handleShowPDF = useCallback((url, title) => {
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

    const eventSource = new EventSource('http://localhost:5001/api/scrape-alan-dal');

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        console.log(eventData.message || eventData);

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
