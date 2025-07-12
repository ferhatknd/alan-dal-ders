import React, { useState, useEffect } from 'react';
import './styles/pdf-processor-styles.css';
import PDFProcessor from './components/pdf-processor-component';

function App() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedPDF, setSelectedPDF] = useState(null);
  const [scrapingInProgress, setScrapingInProgress] = useState(false);

  useEffect(() => {
    fetchCachedData();
  }, []);

  const fetchCachedData = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/get-cached-data');
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Veri yüklenirken hata:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessPDF = (pdfInfo, alanAdi, dersAdi) => {
    setSelectedPDF({
      url: pdfInfo.url,
      filename: pdfInfo.filename,
      alanAdi,
      dersAdi
    });
  };

  const closePDFProcessor = () => {
    setSelectedPDF(null);
  };

  const startScraping = () => {
    setScrapingInProgress(true);
    // Mevcut scraping fonksiyonunuz burada olacak
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="loading-spinner"></div>
        <span className="ml-4">Veriler yükleniyor...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-800">
              Meslek Liseleri PDF İşleme Sistemi
            </h1>
            <button
              onClick={startScraping}
              disabled={scrapingInProgress}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {scrapingInProgress ? 'Scraping Devam Ediyor...' : 'Yeni Veri Çek'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {Object.keys(data).length === 0 ? (
          <div className="text-center py-16">
            <h2 className="text-xl text-gray-600 mb-4">Henüz veri yok</h2>
            <p className="text-gray-500">Veri çekmek için yukarıdaki butona tıklayın</p>
          </div>
        ) : (
          /* PDF Listesi */
          Object.entries(data).map(([alanAdi, alanData]) => (
            <div key={alanAdi} className="mb-8 bg-white rounded-lg shadow-md overflow-hidden">
              {/* Alan Başlığı */}
              <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4">
                <h2 className="text-xl font-semibold">{alanAdi}</h2>
                <p className="text-blue-100 text-sm">
                  {Object.keys(alanData.dersler || {}).length} ders bulundu
                </p>
              </div>
              
              {/* Dersler */}
              <div className="p-6">
                {Object.entries(alanData.dersler || {}).map(([dersAdi, dersData]) => (
                  <div key={dersAdi} className="mb-6 border-l-4 border-blue-200 pl-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                      📚 {dersAdi}
                    </h3>
                    
                    {/* DBF Dosyaları */}
                    {dersData.dbf_files && dersData.dbf_files.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-md font-medium text-gray-700 mb-3 flex items-center">
                          📄 DBF Dosyaları 
                          <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                            {dersData.dbf_files.length}
                          </span>
                        </h4>
                        <div className="grid gap-3">
                          {dersData.dbf_files.map((dbf, index) => (
                            <div 
                              key={index} 
                              className="pdf-card bg-gray-50 p-4 rounded-lg border border-gray-200"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-gray-800 mb-1">
                                    {dbf.filename}
                                  </div>
                                  <div className="text-xs text-gray-500 truncate">
                                    {dbf.url}
                                  </div>
                                </div>
                                
                                <div className="flex gap-2 ml-4 flex-shrink-0">
                                  <a
                                    href={dbf.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>📥</span> İndir
                                  </a>
                                  <button
                                    onClick={() => handleProcessPDF(dbf, alanAdi, dersAdi)}
                                    className="process-btn px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>⚙️</span> İşle
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* BOM Dosyaları */}
                    {dersData.bom_files && dersData.bom_files.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-md font-medium text-gray-700 mb-3 flex items-center">
                          📋 BOM Dosyaları 
                          <span className="ml-2 px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                            {dersData.bom_files.length}
                          </span>
                        </h4>
                        <div className="grid gap-3">
                          {dersData.bom_files.map((bom, index) => (
                            <div 
                              key={index} 
                              className="pdf-card bg-purple-50 p-4 rounded-lg border border-purple-200"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-gray-800 mb-1">
                                    {bom.filename}
                                  </div>
                                  <div className="text-xs text-gray-500 truncate">
                                    {bom.url}
                                  </div>
                                </div>
                                
                                <div className="flex gap-2 ml-4 flex-shrink-0">
                                  <a
                                    href={bom.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>📥</span> İndir
                                  </a>
                                  <button
                                    onClick={() => handleProcessPDF(bom, alanAdi, dersAdi)}
                                    className="process-btn px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>⚙️</span> İşle
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Ders Programı */}
                    {dersData.ders_programi && dersData.ders_programi.length > 0 && (
                      <div className="mb-4">
                        <h4 className="text-md font-medium text-gray-700 mb-3 flex items-center">
                          📚 Ders Programı 
                          <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                            {dersData.ders_programi.length}
                          </span>
                        </h4>
                        <div className="grid gap-3">
                          {dersData.ders_programi.map((program, index) => (
                            <div 
                              key={index} 
                              className="pdf-card bg-yellow-50 p-4 rounded-lg border border-yellow-200"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-gray-800 mb-1">
                                    {program.filename}
                                  </div>
                                  <div className="text-xs text-gray-500 truncate">
                                    {program.url}
                                  </div>
                                </div>
                                
                                <div className="flex gap-2 ml-4 flex-shrink-0">
                                  <a
                                    href={program.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>📥</span> İndir
                                  </a>
                                  <button
                                    onClick={() => handleProcessPDF(program, alanAdi, dersAdi)}
                                    className="process-btn px-4 py-2 bg-yellow-600 text-white text-sm rounded-lg hover:bg-yellow-700 transition-all duration-200 flex items-center gap-1"
                                  >
                                    <span>⚙️</span> İşle
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </main>

      {/* PDF Processor Modal */}
      {selectedPDF && (
        <PDFProcessor
          pdfUrl={selectedPDF.url}
          filename={selectedPDF.filename}
          onClose={closePDFProcessor}
        />
      )}
    </div>
  );
}

export default App;