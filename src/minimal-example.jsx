import React, { useState } from 'react';
import PDFProcessor from './components/PDFProcessor';
import './styles/pdf-processor-styles.css';
// Eğer Tailwind kullanmıyorsanız:
// import './styles/alternative-styles.css';

function MinimalPDFApp() {
  const [selectedPDF, setSelectedPDF] = useState(null);
  
  // Örnek PDF listesi - kendi verilerinizle değiştirin
  const samplePDFs = [
    {
      filename: "LABORATUVAR_TEKNIGI.pdf",
      url: "https://meslek.meb.gov.tr/moduller/dbf/LABORATUVAR_TEKNIGI_DBF_9.pdf"
    },
    {
      filename: "TEMEL_TASARIM.pdf", 
      url: "https://meslek.meb.gov.tr/moduller/dbf/TEMEL_TASARIM.pdf"
    }
  ];

  const handleProcessPDF = (pdf) => {
    setSelectedPDF(pdf);
  };

  const closePDFProcessor = () => {
    setSelectedPDF(null);
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>PDF İşleme Sistemi</h1>
      
      <div>
        {samplePDFs.map((pdf, index) => (
          <div key={index} style={{ 
            margin: '10px 0', 
            padding: '15px', 
            border: '1px solid #ddd', 
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>{pdf.filename}</span>
            <div>
              <a 
                href={pdf.url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ 
                  marginRight: '10px',
                  padding: '8px 16px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '4px'
                }}
              >
                İndir
              </a>
              <button
                onClick={() => handleProcessPDF(pdf)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                İşle
              </button>
            </div>
          </div>
        ))}
      </div>

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

export default MinimalPDFApp;