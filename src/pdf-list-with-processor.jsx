import React, { useState, useEffect } from 'react';
import PDFProcessor from './pdf-processor-component';

const PDFListWithProcessor = () => {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedPDF, setSelectedPDF] = useState(null);

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

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">
        Meslek Liseleri Ders Bilgileri ve PDF İşleme
      </h1>

      {Object.entries(data).map(([alanAdi, alanData]) => (
        <div key={alanAdi} className="mb-8 bg-white rounded-lg shadow-md">
          <div className="bg-blue-600 text-white px-6 py-4 rounded-t-lg">
            <h2 className="text-xl font-semibold">{alanAdi}</h2>
          </div>
          
          <div className="p-6">
            {Object.entries(alanData.dersler || {}).map(([dersAdi, dersData]) => (
              <div key={dersAdi} className="mb-6 border-l-4 border-blue-200 pl-4">
                <h3 className="text-lg font-medium text-gray-800 mb-3">{dersAdi}</h3>
                
                {/* DBF Dosyaları */}
                {dersData.dbf_files && dersData.dbf_files.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-md font-medium text-gray-700 mb-2">
                      📄 DBF Dosyaları ({dersData.dbf_files.length} adet)
                    </h4>
                    <div className="grid gap-2">
                      {dersData.dbf_files.map((dbf, index) => (
                        <div 
                          key={index} 
                          className="flex items-center justify-between bg-gray-50 p-3 rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-800">
                              {dbf.filename}
                            </div>
                            <div className="text-xs text-gray-500">
                              {dbf.url}
                            </div>
                          </div>
                          
                          <div className="flex gap-2 ml-4">
                            <a
                              href={dbf.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                            >
                              İndir
                            </a>
                            <button
                              onClick={() => handleProcessPDF(dbf, alanAdi, dersAdi)}
                              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                            >
                              İşle
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* BOM Dosyaları */}
                {dersData.bom_files && dersData.bom_files.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-md font-medium text-gray-700 mb-2">
                      📋 BOM Dosyaları ({dersData.bom_files.length} adet)
                    </h4>
                    <div className="grid gap-2">
                      {dersData.bom_files.map((bom, index) => (
                        <div 
                          key={index} 
                          className="flex items-center justify-between bg-gray-50 p-3 rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-800">
                              {bom.filename}
                            </div>
                            <div className="text-xs text-gray-500">
                              {bom.url}
                            </div>
                          </div>
                          
                          <div className="flex gap-2 ml-4">
                            <a
                              href={bom.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                            >
                              İndir
                            </a>
                            <button
                              onClick={() => handleProcessPDF(bom, alanAdi, dersAdi)}
                              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                            >
                              İşle
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Ders Programı */}
                {dersData.ders_programi && dersData.ders_programi.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-md font-medium text-gray-700 mb-2">
                      📚 Ders Programı ({dersData.ders_programi.length} adet)
                    </h4>
                    <div className="grid gap-2">
                      {dersData.ders_programi.map((program, index) => (
                        <div 
                          key={index} 
                          className="flex items-center justify-between bg-gray-50 p-3 rounded-lg"
                        >
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-800">
                              {program.filename}
                            </div>
                            <div className="text-xs text-gray-500">
                              {program.url}
                            </div>
                          </div>
                          
                          <div className="flex gap-2 ml-4">
                            <a
                              href={program.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                            >
                              İndir
                            </a>
                            <button
                              onClick={() => handleProcessPDF(program, alanAdi, dersAdi)}
                              className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                            >
                              İşle
                            </button>
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
      ))}

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
};

export default PDFListWithProcessor;