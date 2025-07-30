import React, { useState, useEffect } from 'react';
import './CourseEditor.css';

// Learning Units Manager Component
const LearningUnitsManager = ({ 
  dersId, 
  learningUnits, 
  onChange, 
  loading, 
  onImportDbf, 
  divideText,
  onDivideTextChange,
  onDivide,
  divideAchievementText,
  onDivideAchievementTextChange,
  onDivideAchievements,
  selectedTopic,
  selectionMode,
  onTopicSelect,
  onAchievementLink,
  getGroupedTopicsAndAchievements
}) => {
  const [expandedUnits, setExpandedUnits] = useState({});
  const toggleUnit = (unitId) => {
    setExpandedUnits(prev => ({
      ...prev,
      [unitId]: !prev[unitId]
    }));
  };

  const addNewUnit = () => {
    const newUnit = {
      id: null, // Yeni kayıt için null
      birim_adi: 'Yeni Öğrenme Birimi',
      sure: 0,
      sira: learningUnits.length + 1,
      konular: []
    };
    onChange([...learningUnits, newUnit]);
  };

  const updateUnit = (unitIndex, field, value) => {
    const updated = [...learningUnits];
    updated[unitIndex] = { ...updated[unitIndex], [field]: value };
    onChange(updated);
  };

  const removeUnit = (unitIndex) => {
    if (window.confirm('Bu öğrenme birimini silmek istediğinizden emin misiniz?')) {
      const updated = learningUnits.filter((_, index) => index !== unitIndex);
      
      // Sıralamayı yeniden düzenle
      const reorderedUnits = updated.map((unit, index) => ({
        ...unit,
        sira: index + 1
      }));
      
      onChange(reorderedUnits);
    }
  };

  const addNewTopic = (unitIndex) => {
    const updated = [...learningUnits];
    const unit = updated[unitIndex];
    const newTopic = {
      id: null,
      konu_adi: 'Yeni Konu',
      sira: (unit.konular || []).length + 1,
      kazanimlar: []
    };
    
    updated[unitIndex] = {
      ...unit,
      konular: [...(unit.konular || []), newTopic]
    };
    onChange(updated);
  };

  const updateTopic = (unitIndex, topicIndex, field, value) => {
    const updated = [...learningUnits];
    updated[unitIndex].konular[topicIndex] = {
      ...updated[unitIndex].konular[topicIndex],
      [field]: value
    };
    onChange(updated);
  };

  const removeTopic = (unitIndex, topicIndex) => {
    if (window.confirm('Bu konuyu silmek istediğinizden emin misiniz?')) {
      const updated = [...learningUnits];
      updated[unitIndex].konular = updated[unitIndex].konular.filter((_, index) => index !== topicIndex);
      
      // Sıralamayı yeniden düzenle
      updated[unitIndex].konular = updated[unitIndex].konular.map((topic, index) => ({
        ...topic,
        sira: index + 1
      }));
      
      onChange(updated);
    }
  };

  const addNewAchievement = (unitIndex, topicIndex) => {
    const updated = [...learningUnits];
    const topic = updated[unitIndex].konular[topicIndex];
    const newAchievement = {
      id: null,
      kazanim_adi: 'Yeni Kazanım',
      sira: (topic.kazanimlar || []).length + 1
    };
    
    updated[unitIndex].konular[topicIndex] = {
      ...topic,
      kazanimlar: [...(topic.kazanimlar || []), newAchievement]
    };
    onChange(updated);
  };

  const updateAchievement = (unitIndex, topicIndex, achievementIndex, field, value) => {
    const updated = [...learningUnits];
    updated[unitIndex].konular[topicIndex].kazanimlar[achievementIndex] = {
      ...updated[unitIndex].konular[topicIndex].kazanimlar[achievementIndex],
      [field]: value
    };
    onChange(updated);
  };


  if (loading) {
    return (
      <div className="learning-units-loading">
        <div className="loading-spinner"></div>
        <p>Öğrenme birimleri yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="learning-units-manager">
      <div className="learning-units-header">
        <div className="learning-units-title">
          <span className="unit-icon">📚</span>
          <h4>Öğrenme Birimleri</h4>
        </div>
        <div className="learning-units-actions">
          <button onClick={addNewUnit} className="add-unit-btn">
            + Yeni Öğrenme Birimi
          </button>
          <button onClick={onImportDbf} className="import-dbf-btn">
            📄 DBF'den Import
          </button>
        </div>
      </div>

      {learningUnits.length === 0 ? (
        <div className="no-learning-units">
          <p>Henüz öğrenme birimi eklenmemiş.</p>
          <button onClick={addNewUnit} className="add-first-unit-btn">
            İlk Öğrenme Birimini Ekle
          </button>
        </div>
      ) : (
        learningUnits.map((unit, unitIndex) => (
          <div key={unit.id || `new-${unitIndex}`} className="learning-unit-card">
            <div className="unit-row">
              <button 
                onClick={() => toggleUnit(unit.id || `new-${unitIndex}`)}
                className="collapse-btn"
                title={expandedUnits[unit.id || `new-${unitIndex}`] ? "Konuları gizle" : "Konuları göster"}
              >
                {expandedUnits[unit.id || `new-${unitIndex}`] ? '▼' : '▶'}
              </button>
              
              <div className="unit-input">
                <MaterialTextField
                  label="Öğrenme Birimi"
                  value={unit.birim_adi}
                  onChange={(e) => {
                    const value = e?.target?.value ?? e;
                    updateUnit(unitIndex, 'birim_adi', value);
                  }}
                  suffix={`${unit.sure} Saat`}
                />
              </div>
              
              <div className="action-buttons">
                <button 
                  onClick={() => addNewUnit()}
                  className="add-btn"
                  title="Yeni öğrenme birimi ekle"
                >
                  +
                </button>
                <button 
                  onClick={() => removeUnit(unitIndex)}
                  className="remove-btn"
                  title="Öğrenme birimini sil"
                >
                  ×
                </button>
              </div>
            </div>

            {expandedUnits[unit.id || `new-${unitIndex}`] && (
              <div className="unit-content">
                <div className="topics-section">
                  <div className="divide-sections-container">
                    {/* Konu Divide Bölümü */}
                    <div className="divide-section">
                      <h6 className="divide-section-title">Konular</h6>
                      <div className="divide-input-container">
                        <MaterialTextField
                          label="Her satıra bir konu yazın"
                          value={divideText[unitIndex] || ''}
                          onChange={(e) => {
                            const value = e?.target?.value ?? e;
                            onDivideTextChange(unitIndex, value);
                          }}
                          multiline={true}
                          rows={4}
                          autoBullets={true}
                        />
                        <button 
                          onClick={() => onDivide(unitIndex)}
                          className="divide-btn"
                        >
                          /
                        </button>
                      </div>
                    </div>

                    {/* Kazanım Divide Bölümü */}
                    <div className="divide-section">
                      <h6 className="divide-section-title">Kazanımlar</h6>
                      <div className="divide-input-container">
                        <MaterialTextField
                          label="Her satıra bir kazanım yazın"
                          value={divideAchievementText[unitIndex] || ''}
                          onChange={(e) => {
                            const value = e?.target?.value ?? e;
                            onDivideAchievementTextChange(unitIndex, value);
                          }}
                          multiline={true}
                          rows={4}
                          autoBullets={true}
                        />
                        <button 
                          onClick={() => onDivideAchievements(unitIndex)}
                          className="divide-btn"
                        >
                          /
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Selection Mode Hint */}
                  {selectionMode && (
                    <div className="selection-mode-hint">
                      <strong>Kazanım Seçim Modu Aktif!</strong> Seçili konuya bağlamak istediğiniz kazanımların yanındaki <strong>+</strong> butonlarına tıklayın. 
                      Bitirmek için seçili konunun yanındaki yeşil <strong>→</strong> butonuna tekrar tıklayın.
                    </div>
                  )}

                  {/* Grouped Konu ve Kazanım Tablosu */}
                  {getGroupedTopicsAndAchievements(unit, unitIndex).map((item, index) => {
                    const isSelected = selectedTopic === item.topicKey;
                    const isLinked = item.type === 'achievement' || 
                      (item.data.linkedAchievements && item.data.linkedAchievements.length > 0);
                    
                    return (
                      <div key={`grouped-${index}`}>
                        {/* Ana Konu Satırı */}
                        {(item.type === 'topic' || item.type === 'unlinked') && (
                          <div 
                            className={`topic-achievement-row ${isSelected ? 'selected-topic' : ''} ${isLinked ? 'linked-topic' : ''}`}
                          >
                            <div className="topic-column">
                              <div className="topic-input-with-button">
                                <MaterialTextField
                                  label="Konu"
                                  value={item.data.konu_adi}
                                  onChange={(e) => {
                                    const value = e?.target?.value ?? e;
                                    updateTopic(item.unitIndex, item.topicIndex, 'konu_adi', value);
                                  }}
                                  multiline={true}
                                  rows={2}
                                  autoBullets={true}
                                />
                                <button 
                                  onClick={() => onTopicSelect(item.unitIndex, item.topicIndex, item.topicKey)}
                                  className={`select-topic-btn inline-btn ${isSelected ? 'selected' : ''}`}
                                  title={isSelected ? "Seçim modunu bitir" : "Konu seçim moduna geç"}
                                >
                                  {isSelected ? '✓' : '→'}
                                </button>
                              </div>
                            </div>
                            
                            <div className="achievement-column">
                              <MaterialTextField
                                label="Kazanım"
                                value={item.data.kazanimlar?.[0]?.kazanim_adi || ''}
                                onChange={(e) => {
                                  const value = e?.target?.value ?? e;
                                  // Eğer kazanım yoksa yeni bir tane oluştur
                                  if (!item.data.kazanimlar || item.data.kazanimlar.length === 0) {
                                    const updated = [...learningUnits];
                                    updated[item.unitIndex].konular[item.topicIndex].kazanimlar = [{
                                      id: null,
                                      kazanim_adi: value,
                                      sira: 1
                                    }];
                                    onChange(updated);
                                  } else {
                                    updateAchievement(item.unitIndex, item.topicIndex, 0, 'kazanim_adi', value);
                                  }
                                }}
                                multiline={true}
                                rows={2}
                                autoBullets={true}
                              />
                            </div>
                            
                            <div className="action-buttons">
                              {selectionMode ? (
                                // Selection mode - achievement linking
                                <button 
                                  onClick={() => onAchievementLink(item.unitIndex, item.topicIndex, item.topicKey)}
                                  className={`link-btn ${isLinked ? 'linked' : ''}`}
                                  title={isLinked ? "Bağlantıyı kaldır" : "Bu kazanımı seçili konuya bağla"}
                                >
                                  {isLinked ? '−' : '+'}
                                </button>
                              ) : (
                                // Normal mode - regular actions
                                <button 
                                  onClick={() => addNewTopic(item.unitIndex)}
                                  className="add-btn"
                                  title="Yeni konu satırı ekle"
                                >
                                  +
                                </button>
                              )}
                              <button 
                                onClick={() => removeTopic(item.unitIndex, item.topicIndex)}
                                className="remove-btn"
                                title="Bu satırı sil"
                              >
                                ×
                              </button>
                            </div>
                          </div>
                        )}
                        
                        {/* Bağlı Kazanımlar */}
                        {item.type === 'topic' && item.linkedAchievements && item.linkedAchievements.map((linkedAch, achIndex) => (
                          <div 
                            key={`linked-${achIndex}`} 
                            className="topic-achievement-row linked-achievement-row"
                          >
                            <div className="topic-column">
                              <div className="linked-achievement-label">└ Bağlı Kazanım:</div>
                            </div>
                            
                            <div className="achievement-column">
                              <MaterialTextField
                                label="Kazanım"
                                value={linkedAch.data.kazanimlar?.[0]?.kazanim_adi || linkedAch.data.konu_adi}
                                onChange={(e) => {
                                  const value = e?.target?.value ?? e;
                                  updateAchievement(linkedAch.unitIndex, linkedAch.topicIndex, 0, 'kazanim_adi', value);
                                }}
                                multiline={true}
                                rows={1}
                                autoBullets={true}
                              />
                            </div>
                            
                            <div className="action-buttons">
                              <button 
                                onClick={() => onAchievementLink(item.unitIndex, item.topicIndex, linkedAch.topicKey)}
                                className="link-btn linked"
                                title="Bağlantıyı kaldır"
                              >
                                −
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
};

// COP Dropdown Bileşeni - DBF ile aynı yapıda
const CopDropdown = ({ copUrls, onSelectCop }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  // COP Dropdown debug (reduced logging)
  
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
  
  // COP list created successfully
  
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
                // COP selected
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
  
  // DBF Dropdown debug (reduced logging)
  
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
  
  // DBF list created successfully
  
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
  options = [],
  suffix = null,
  autoBullets = false // Yeni prop - otomatik madde işaretleri
}) => {
  const [focused, setFocused] = useState(false);
  // Material UI'da label her zaman üstte olmalı - sadece focus durumuna göre stil değişir
  const hasValue = true; // Label her zaman üstte kalacak
  
  const handleFocus = () => setFocused(true);
  const handleBlur = () => setFocused(false);

  // Enter tuşu ile otomatik madde işareti ekleme
  const handleKeyDown = (e) => {
    if (autoBullets && multiline && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      
      const textarea = e.target;
      const currentValue = textarea.value;
      const cursorPosition = textarea.selectionStart;
      
      // Mevcut satırı al
      const beforeCursor = currentValue.substring(0, cursorPosition);
      const afterCursor = currentValue.substring(cursorPosition);
      const lines = beforeCursor.split('\n');
      const currentLine = lines[lines.length - 1];
      
      // Madde numarası pattern'ini kontrol et
      const bulletPattern = /^(\d+)\.\s*/;
      const match = currentLine.match(bulletPattern);
      
      let newText;
      if (match) {
        // Mevcut satırda madde numarası var - bir sonrakini ekle
        const currentNumber = parseInt(match[1]);
        const nextNumber = currentNumber + 1;
        newText = currentValue.substring(0, cursorPosition) + '\n' + nextNumber + '. ' + afterCursor;
        
        // Yeni değeri güncelle
        onChange(newText);
        
        // Cursor pozisyonunu ayarla
        setTimeout(() => {
          const newCursorPos = cursorPosition + ('\n' + nextNumber + '. ').length;
          textarea.setSelectionRange(newCursorPos, newCursorPos);
        }, 0);
      } else {
        // İlk madde için 1. ekle
        if (currentLine.trim() === '' || currentValue.trim() === '') {
          newText = currentValue.substring(0, cursorPosition) + '\n1. ' + afterCursor;
        } else {
          // Mevcut satırı 1. ile başlat
          const lineStart = beforeCursor.lastIndexOf('\n') + 1;
          const lineContent = currentLine.trim();
          if (lineContent) {
            // Mevcut satırı 1. ile başlat ve yeni satır ekle
            newText = currentValue.substring(0, lineStart) + '1. ' + lineContent + '\n2. ' + afterCursor;
          } else {
            newText = currentValue.substring(0, cursorPosition) + '1. ' + afterCursor;
          }
        }
        
        onChange(newText);
        
        // Cursor pozisyonunu ayarla
        setTimeout(() => {
          const newLines = newText.split('\n');
          let newCursorPos = 0;
          for (let i = 0; i < newLines.length; i++) {
            if (newLines[i].match(/^\d+\.\s*$/)) {
              newCursorPos = newText.indexOf(newLines[i]) + newLines[i].length;
              break;
            }
          }
          textarea.setSelectionRange(newCursorPos, newCursorPos);
        }, 0);
      }
    }
  };
  
  const classes = [
    'material-textfield',
    'always-floating', // Yeni class - label her zaman üstte
    hasValue ? 'has-value' : '',
    focused ? 'focused' : '',
    error ? 'error' : '',
    disabled ? 'disabled' : '',
    select ? 'select' : '',
    suffix ? 'has-suffix' : ''
  ].filter(Boolean).join(' ');

  return (
    <div className={classes}>
      <div className="input-wrapper">
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
            onKeyDown={handleKeyDown}
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
        {suffix && (
          <span className="input-suffix">{suffix}</span>
        )}
      </div>
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
  
  // Import feedback states
  const [importStatus, setImportStatus] = useState('idle'); // 'idle', 'importing', 'success', 'error'
  const [importMessage, setImportMessage] = useState('');
  
  // Split screen mode - PDF açık mı?
  const isSplitMode = Boolean(pdfUrl);
  
  // Flexible sidebar width - responsive based on screen size
  const calculateFlexibleSidebarStyle = () => {
    const courseName = editData.ders_adi || 'Ders Adı';
    const charCount = courseName.length;
    
    // Base width calculation - increased minimum width for wider initial sidebar
    const baseWidth = Math.max(600, Math.min(charCount * 8 + 300, 1000));
    
    // Responsive width logic:
    // - If screen > 2000px: 50% of viewport (max 1000px)
    // - If screen <= 2000px: calculated width (max 1000px)
    const screenWidth = window.innerWidth;
    
    if (screenWidth > 2000) {
      return {
        width: `min(50vw, 1000px)`,
        maxWidth: '1000px'
      };
    } else {
      return {
        width: `min(${baseWidth}px, 1000px)`,
        maxWidth: '1000px'
      };
    }
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
            console.log('✅ Fresh ders data loaded for ID:', result.data.ders_id);
            
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
            //  chained call to load learning units after course data is set
            loadLearningUnits(result.data.ders_id);
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
          console.log('Alan-Dal seçenekleri yüklendi - Alanlar:', data.alanlar?.length || 0);
          setAlanDalOptions(data);
        })
        .catch(err => console.error('Alan-Dal seçenekleri yüklenirken hata:', err));
    }
  }, [isOpen]);


  // COP ve DBF URL'lerini alan_id değiştiğinde güncelle
  useEffect(() => {
    if (editData.alan_id && alanDalOptions.alanlar.length > 0) {
      // Updating COP and DBF URLs for alan_id: ${editData.alan_id}
      
      const selectedAlan = alanDalOptions.alanlar.find(alan => alan.id === parseInt(editData.alan_id));
      
      // COP URL'lerini güncelle
      if (selectedAlan && selectedAlan.cop_url) {
        try {
          const copData = JSON.parse(selectedAlan.cop_url);
          // COP data parsed successfully
          setCopUrls(copData);
        } catch (e) {
          console.log('⚠️ COP data is string, not JSON');
          setCopUrls({ 'cop_url': selectedAlan.cop_url });
        }
      } else {
        console.log('❌ No COP data found for selected alan');
        setCopUrls({});
      }
      
      // DBF URL'lerini güncelle (Alan bazlı RAR linkleri)
      if (selectedAlan && selectedAlan.dbf_urls) {
        try {
          const dbfData = JSON.parse(selectedAlan.dbf_urls);
          // DBF data parsed successfully
          setDbfUrls(dbfData);
        } catch (e) {
          console.log('⚠️ DBF data is string, not JSON');
          setDbfUrls({ 'dbf_urls': selectedAlan.dbf_urls });
        }
      } else {
        console.log('❌ No DBF data found for selected alan');
        setDbfUrls({});
      }
    }
  }, [editData.alan_id, alanDalOptions.alanlar]);

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

  const handleInputChange = (field, value) => {
    setEditData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaveStatus('saving');
    setSaveMessage('Kaydediliyor...');
    
    try {
      // Prepare data with learning units (no aciklama field in schema)
      const safeEditData = { ...editData };
      const saveData = {
        ...safeEditData,
        ogrenme_birimleri: learningUnits.map(unit => ({
          ...unit,
          konular: (unit.konular || []).map(topic => ({
            ...topic,
            kazanimlar: topic.kazanimlar || []
          }))
        }))
      };
      
      console.log('💾 Saving data with learning units:', saveData);
      
      // Direct API call instead of parent onSave
      const response = await fetch('http://localhost:5001/api/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(saveData)
      });

      const result = await response.json();
      
      if (result.success) {
        setSaveStatus('success');
        setSaveMessage(`✅ ${result.message}`);
        
        // Reload learning units to get fresh IDs
        if (editData.ders_id) {
          await loadLearningUnits(editData.ders_id);
        }
        
        // Auto-hide success message after 3 seconds (sidebar stays open)
        setTimeout(() => {
          setSaveStatus('idle');
          setSaveMessage('');
        }, 3000);
      } else {
        throw new Error(result.error || 'Kaydetme başarısız');
      }
      
    } catch (error) {
      console.error('💥 Save error:', error);
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

  // Learning Units Management
  const [learningUnits, setLearningUnits] = useState([]);
  const [learningUnitsLoading, setLearningUnitsLoading] = useState(false);
  
  // Divide functionality states
  const [divideText, setDivideText] = useState({}); // Konu divide için
  const [divideAchievementText, setDivideAchievementText] = useState({}); // Kazanım divide için
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [selectionMode, setSelectionMode] = useState(false);

  // Öğrenme birimlerini yükle
  const loadLearningUnits = async (dersId) => {
    if (!dersId) return;
    
    setLearningUnitsLoading(true);
    try {
      const response = await fetch(`http://localhost:5001/api/load?type=ogrenme_birimi&parent_id=${dersId}`);
      const result = await response.json();
      
      if (result.success) {
        console.log('🎯 Learning units loaded count:', result.data?.length || 0);
        setLearningUnits(result.data || []);
      } else {
        console.error('❌ Learning units loading failed:', result.error);
        setLearningUnits([]);
      }
    } catch (error) {
      console.error('❌ Learning units loading error:', error);
      setLearningUnits([]);
    } finally {
      setLearningUnitsLoading(false);
    }
  };

  // Ders ID değiştiğinde öğrenme birimlerini yükle
  useEffect(() => {
    if (editData.ders_id && isOpen) {
      loadLearningUnits(editData.ders_id);
    }
  }, [editData.ders_id, isOpen]);

  // Öğrenme birimlerini kaydet
  const handleLearningUnitsChange = (updatedUnits) => {
    setLearningUnits(updatedUnits);
  };

  // Divide text değişikliği
  const handleDivideTextChange = (unitIndex, text) => {
    setDivideText(prev => ({
      ...prev,
      [unitIndex]: text
    }));
  };

  // Achievement divide text değişikliği
  const handleDivideAchievementTextChange = (unitIndex, text) => {
    setDivideAchievementText(prev => ({
      ...prev,
      [unitIndex]: text
    }));
  };

  // Divide işlemi - metni parse et ve satırlara böl
  const handleDivide = (unitIndex) => {
    const text = divideText[unitIndex];
    if (!text || !text.trim()) {
      setImportStatus('error');
      setImportMessage('❌ Lütfen önce metin girin!');
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);
      return;
    }

    try {
      // Metni parse et - aynı parsing fonksiyonunu kullan
      const parsedItems = parseBulkTopicsText(text);
      
      if (parsedItems.length === 0) {
        setImportStatus('error');
        setImportMessage('❌ Metinde geçerli madde bulunamadı!');
        setTimeout(() => {
          setImportStatus('idle');
          setImportMessage('');
        }, 3000);
        return;
      }

      // Yeni konu-kazanım satırları oluştur
      const updated = [...learningUnits];
      const unit = updated[unitIndex];
      
      const newTopics = parsedItems.map((item, index) => ({
        id: null,
        konu_adi: item.konu_adi,
        sira: (unit.konular || []).length + index + 1,
        kazanimlar: [{
          id: null,
          kazanim_adi: '', // Boş bırak - sadece konu divide ediyor
          sira: 1
        }],
        linkedAchievements: [] // Yeni alan - bağlı kazanımlar için
      }));

      updated[unitIndex] = {
        ...unit,
        konular: [...(unit.konular || []), ...newTopics]
      };

      setLearningUnits(updated);
      
      // Divide text'i temizle
      setDivideText(prev => ({
        ...prev,
        [unitIndex]: ''
      }));

      setImportStatus('success');
      setImportMessage(`✅ ${parsedItems.length} madde başarıyla eklendi!`);
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);

    } catch (error) {
      console.error('Divide parsing hatası:', error);
      setImportStatus('error');
      setImportMessage('❌ Metin işleme hatası! Formatı kontrol edin.');
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);
    }
  };

  // Achievement Divide işlemi - metni parse et ve kazanım olarak ekle
  const handleDivideAchievements = (unitIndex) => {
    const text = divideAchievementText[unitIndex];
    if (!text || !text.trim()) {
      setImportStatus('error');
      setImportMessage('❌ Lütfen önce kazanım metni girin!');
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);
      return;
    }

    try {
      // Metni parse et - aynı parsing fonksiyonunu kullan
      const parsedAchievements = parseBulkTopicsText(text);
      
      if (parsedAchievements.length === 0) {
        setImportStatus('error');
        setImportMessage('❌ Metinde geçerli kazanım bulunamadı!');
        setTimeout(() => {
          setImportStatus('idle');
          setImportMessage('');
        }, 3000);
        return;
      }

      // Yeni kazanım satırları oluştur (sadece kazanım kısmı dolu)
      const updated = [...learningUnits];
      const unit = updated[unitIndex];
      
      const newAchievementTopics = parsedAchievements.map((item, index) => ({
        id: null,
        konu_adi: '', // Konu kısmı boş
        sira: (unit.konular || []).length + index + 1,
        kazanimlar: [{
          id: null,
          kazanim_adi: item.konu_adi, // Parse edilen text kazanım olarak
          sira: 1
        }],
        linkedAchievements: [] // Yeni alan - bağlı kazanımlar için
      }));

      updated[unitIndex] = {
        ...unit,
        konular: [...(unit.konular || []), ...newAchievementTopics]
      };

      setLearningUnits(updated);
      
      // Achievement divide text'i temizle
      setDivideAchievementText(prev => ({
        ...prev,
        [unitIndex]: ''
      }));

      setImportStatus('success');
      setImportMessage(`✅ ${parsedAchievements.length} kazanım başarıyla eklendi!`);
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);

    } catch (error) {
      console.error('Achievement divide parsing hatası:', error);
      setImportStatus('error');
      setImportMessage('❌ Metin işleme hatası! Formatı kontrol edin.');
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 3000);
    }
  };

  // Topic seçim modu
  const handleTopicSelect = (unitIndex, topicIndex, topicKey) => {
    if (selectedTopic === topicKey) {
      // Aynı topic'e tekrar basıldı - seçim modunu kapat
      setSelectedTopic(null);
      setSelectionMode(false);
    } else {
      // Yeni topic seçildi - seçim modunu aç
      setSelectedTopic(topicKey);
      setSelectionMode(true);
    }
  };

  // Achievement linking
  const handleAchievementLink = (unitIndex, topicIndex, achievementKey) => {
    if (!selectedTopic) return;

    const updated = [...learningUnits];
    const [selectedUnitIndex, selectedTopicIndex] = selectedTopic.split('-').map(Number);
    
    // Seçili topic'i al
    const selectedTopicObj = updated[selectedUnitIndex].konular[selectedTopicIndex];
    
    // Bağlantı var mı kontrol et
    if (!selectedTopicObj.linkedAchievements) {
      selectedTopicObj.linkedAchievements = [];
    }
    
    const linkIndex = selectedTopicObj.linkedAchievements.indexOf(achievementKey);
    
    if (linkIndex > -1) {
      // Bağlantı var, kaldır
      selectedTopicObj.linkedAchievements.splice(linkIndex, 1);
    } else {
      // Bağlantı yok, ekle
      selectedTopicObj.linkedAchievements.push(achievementKey);
    }
    
    setLearningUnits(updated);
  };

  // Konuları ve bağlı kazanımları grupla
  const getGroupedTopicsAndAchievements = (unit, unitIndex) => {
    if (!unit.konular) return [];
    
    const grouped = [];
    const processedItems = new Set();
    
    // 1. Önce bağlantısı OLAN konuları işle (linkedAchievements'ı olan)
    unit.konular.forEach((topic, topicIndex) => {
      const topicKey = `${unitIndex}-${topicIndex}`;
      
      // Bu konu başka bir konuya bağlı kazanım olarak kullanılıyor mu kontrol et
      const isUsedAsAchievement = unit.konular.some(otherTopic => 
        otherTopic.linkedAchievements && otherTopic.linkedAchievements.includes(topicKey)
      );
      
      // Eğer bu konu başka bir konuya bağlı değilse ve kendisinin bağlı kazanımları varsa
      if (!isUsedAsAchievement && topic.linkedAchievements && topic.linkedAchievements.length > 0) {
        const topicData = {
          type: 'topic',
          data: topic,
          unitIndex,
          topicIndex,
          topicKey,
          linkedAchievements: []
        };
        
        // Bu konuya bağlı kazanımları ekle
        topic.linkedAchievements.forEach(achievementKey => {
          const [achUnitIndex, achTopicIndex] = achievementKey.split('-').map(Number);
          const achTopic = unit.konular[achTopicIndex];
          
          if (achTopic && !processedItems.has(achievementKey)) {
            topicData.linkedAchievements.push({
              type: 'achievement',
              data: achTopic,
              unitIndex: achUnitIndex,
              topicIndex: achTopicIndex,
              topicKey: achievementKey
            });
            processedItems.add(achievementKey); // Bağlı kazanımı işaretla
          }
        });
        
        grouped.push(topicData);
        processedItems.add(topicKey); // Ana konuyu da işaretla
      }
    });
    
    // 2. Sonra bağlanmamış öğeleri normal konu-kazanım çifti olarak ekle
    unit.konular.forEach((topic, topicIndex) => {
      const topicKey = `${unitIndex}-${topicIndex}`;
      
      // Eğer bu konu henüz işlenmemişse (ne ana konu ne de bağlı kazanım)
      if (!processedItems.has(topicKey)) {
        grouped.push({
          type: 'unlinked',
          data: topic,
          unitIndex,
          topicIndex,
          topicKey
        });
      }
    });
    
    return grouped;
  };

  // PDF'den kopyalanan metni parse et - akıllı satır birleştirme
  const parseBulkTopicsText = (text) => {
    if (!text || typeof text !== 'string') return [];
    
    // Metni satırlara böl
    const lines = text.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    
    const topics = [];
    let currentTopic = null;
    
    for (const line of lines) {
      // Madde numarası pattern'leri: 1., 2., 1.1., 1.2., 2.1., vs.
      const topicPattern = /^(\d+(?:\.\d+)*\.?\s*)/;
      const match = line.match(topicPattern);
      
      if (match) {
        // Yeni konu başlığı bulundu
        if (currentTopic) {
          // Önceki konuyu kaydet
          topics.push({
            konu_adi: currentTopic.trim(),
            id: null,
            sira: topics.length + 1,
            kazanimlar: []
          });
        }
        
        // Yeni konu başlat (madde numarasını kaldır)
        currentTopic = line.replace(topicPattern, '').trim();
      } else {
        // Devam eden satır - önceki konuya ekle
        if (currentTopic) {
          currentTopic += ' ' + line;
        } else {
          // İlk satır madde numarası ile başlamıyorsa yeni konu olarak ekle
          currentTopic = line;
        }
      }
    }
    
    // Son konuyu da ekle
    if (currentTopic) {
      topics.push({
        konu_adi: currentTopic.trim(),
        id: null,
        sira: topics.length + 1,
        kazanimlar: []
      });
    }
    
    return topics;
  };


  // DBF'den öğrenme birimlerini import et
  const handleImportDbfUnits = async () => {
    if (!editData.ders_id || !editData.dbf_url) {
      setImportStatus('error');
      setImportMessage('❌ Ders ID veya DBF dosya yolu bulunamadı. Önce bir DBF dosyası seçin.');
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 4000);
      return;
    }

    if (learningUnits.length > 0) {
      const confirm = window.confirm('Mevcut öğrenme birimleri var. DBF import işlemi bunları değiştirebilir. Devam etmek istiyor musunuz?');
      if (!confirm) return;
    }

    try {
      setImportStatus('importing');
      setImportMessage('🔄 DBF dosyası işleniyor...');
      setLearningUnitsLoading(true);
      
      const response = await fetch('http://localhost:5001/api/import-dbf-learning-units', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ders_id: editData.ders_id,
          dbf_file_path: editData.dbf_url
        })
      });

      const result = await response.json();
      
      if (result.success) {
        console.log('✅ DBF import successful:', result.imported_units);
        setLearningUnits(result.imported_units);
        setImportStatus('success');
        setImportMessage(`✅ ${result.message}`);
        
        // Auto-hide success message after 4 seconds
        setTimeout(() => {
          setImportStatus('idle');
          setImportMessage('');
        }, 4000);
      } else {
        console.error('❌ DBF import failed:', result.error);
        setImportStatus('error');
        setImportMessage(`❌ Import hatası: ${result.error}`);
        
        // Auto-hide error message after 5 seconds
        setTimeout(() => {
          setImportStatus('idle');
          setImportMessage('');
        }, 5000);
      }
    } catch (error) {
      console.error('❌ DBF import request failed:', error);
      setImportStatus('error');
      setImportMessage(`❌ Request hatası: ${error.message}`);
      
      // Auto-hide error message after 5 seconds
      setTimeout(() => {
        setImportStatus('idle');
        setImportMessage('');
      }, 5000);
    } finally {
      setLearningUnitsLoading(false);
    }
  };

  // Common form content component
  const renderFormContent = () => (
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
          onChange={(e) => {
            const value = e?.target?.value ?? e;
            handleInputChange('ders_adi', value);
          }}
        />
        
        <div className="inline-fields">
          <MaterialTextField
            label="Sınıf"
            value={editData.sinif}
            onChange={(e) => {
              const value = e?.target?.value ?? e;
              handleInputChange('sinif', value);
            }}
            type="number"
          />
          
          <MaterialTextField
            label="Ders Saati"
            value={editData.ders_saati}
            onChange={(e) => {
              const value = e?.target?.value ?? e;
              handleInputChange('ders_saati', value);
            }}
            type="number"
          />
        </div>

        <MaterialTextField
          label="Ders Amacı"
          value={editData.amac}
          onChange={(e) => {
            const value = e?.target?.value ?? e;
            handleInputChange('amac', value);
          }}
          multiline={true}
          rows={3}
        />

        <MaterialTextField
          label="DM URL"
          value={editData.dm_url}
          onChange={(e) => {
            const value = e?.target?.value ?? e;
            handleInputChange('dm_url', value);
          }}
        />

        <MaterialTextField
          label="BOM URL" 
          value={editData.bom_url}
          onChange={(e) => {
            const value = e?.target?.value ?? e;
            handleInputChange('bom_url', value);
          }}
        />
      </div>

      {/* Learning Units Management */}
      <div className="form-section learning-units-section">
        <LearningUnitsManager
          dersId={editData.ders_id}
          learningUnits={learningUnits}
          onChange={handleLearningUnitsChange}
          loading={learningUnitsLoading}
          onImportDbf={handleImportDbfUnits}
          divideText={divideText}
          onDivideTextChange={handleDivideTextChange}
          onDivide={handleDivide}
          divideAchievementText={divideAchievementText}
          onDivideAchievementTextChange={handleDivideAchievementTextChange}
          onDivideAchievements={handleDivideAchievements}
          selectedTopic={selectedTopic}
          selectionMode={selectionMode}
          onTopicSelect={handleTopicSelect}
          onAchievementLink={handleAchievementLink}
          getGroupedTopicsAndAchievements={getGroupedTopicsAndAchievements}
        />
      </div>

      {/* Save Feedback */}
      {saveMessage && (
        <div className={`save-feedback ${saveStatus}`}>
          {saveMessage}
        </div>
      )}
      
      {/* Import Feedback */}
      {importMessage && (
        <div className={`import-feedback ${importStatus}`}>
          {importMessage}
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
  );

  // Common header component
  const renderHeader = () => (
    <div className="edit-sidebar-header">
      <div className="header-left">
        <h3 className="course-title">{editData.ders_adi || 'Ders Adı'}</h3>
        {editData.dbf_url && (
          <button 
            onClick={() => {
              if (pdfUrl) {
                onShowPDF(null, ''); // PDF açıksa sadece PDF'i kapat, sidebar açık bırak
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
  );

  if (!isOpen) return null;

  // Normal sidebar mode (no PDF)
  if (!isSplitMode) {
    return (
      <div 
        className="edit-sidebar-container"
        style={sidebarStyle}
      >
        {renderHeader()}
        {renderFormContent()}
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
        {renderHeader()}
        {renderFormContent()}
      </div>
    </div>
  );
};

export default CourseEditor;