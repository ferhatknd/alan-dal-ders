import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import DataTable from './components/DataTable';
import CourseEditor from './components/CourseEditor';

function App() {  
  const [data, setData] = useState(null);
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState(searchTerm);
  const [editingSidebar, setEditingSidebar] = useState({ isOpen: false, course: null });
  const [pdfSidebar, setPdfSidebar] = useState({ isOpen: false, url: '', title: '' });

  // Kategorik veri state'leri
  const [catLoading, setCatLoading] = useState("");
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

  const handleCourseEdit = useCallback((course) => {
    console.log('handleCourseEdit called with:', course);
    setEditingSidebar({ isOpen: true, course });
  }, []);

  const handleCloseSidebar = useCallback(() => {
    setEditingSidebar({ isOpen: false, course: null });
    setPdfSidebar({ isOpen: false, url: '', title: '' });
  }, []);

  const handleShowPDF = useCallback((url, title) => {
    setPdfSidebar({ isOpen: true, url, title });
  }, []);

  const handleDocumentView = useCallback((course, url, title) => {
    setEditingSidebar({ isOpen: true, course });
    setPdfSidebar({ isOpen: true, url, title });
  }, []);

  const handleSaveCourse = useCallback(async (editedData) => {
    try {
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

      console.log(`"${editedData.ders_adi}" dersi başarıyla güncellendi.`);
      await loadTableData();
      
    } catch (error) {
      console.error(`Ders güncelleme hatası: ${error.message}`);
    }
  }, [loadTableData]);

  // ÇÖP PDF işleme fonksiyonu
  const handleProcessCopPdfs = useCallback(() => {
    if (!window.confirm('ÇÖP PDF\'lerini işleyip alan-dal-ders ilişkilerini çıkararak veritabanına kaydetmek istediğinize emin misiniz? Bu işlem uzun sürebilir.')) {
      return;
    }

    setError(null);
    setCopProcessing(true);

    const eventSource = new EventSource('http://localhost:5001/api/oku-cop');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      
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
  }, [loadTableData]);

  // DBF'lerden ders saatlerini güncelleme fonksiyonu
  const handleUpdateDersSaatleri = useCallback(() => {
    if (!window.confirm('DBF dosyalarından ders saati bilgilerini çıkarıp mevcut dersleri güncellemek istediğinize emin misiniz? Bu işlem uzun sürebilir.')) {
      return;
    }

    setError(null);
    setDbfProcessing(true);

    const eventSource = new EventSource('http://localhost:5001/api/oku-dbf');

    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      
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
  }, [loadTableData]);

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
                  dal_sayisi_province } = eventData;
          
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

              {/* Course Editor */}
              <CourseEditor
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