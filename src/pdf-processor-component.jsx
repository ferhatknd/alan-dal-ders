import React, { useState, useRef, useEffect } from 'react';

const PDFProcessor = ({ pdfUrl, filename, onClose }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [output, setOutput] = useState([]);
  const [result, setResult] = useState(null);
  const eventSourceRef = useRef(null);
  const outputRef = useRef(null);

  const processPDF = async () => {
    setIsProcessing(true);
    setOutput([]);
    setResult(null);

    try {
      // EventSource ile streaming bağlantısı kur
      eventSourceRef.current = new EventSource(`http://localhost:5001/api/process-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pdf_url: pdfUrl })
      });

      // Alternatif olarak fetch ile streaming
      const response = await fetch('http://localhost:5001/api/process-pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pdf_url: pdfUrl })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'status') {
                setOutput(prev => [...prev, { type: 'status', message: data.message, timestamp: new Date() }]);
              } else if (data.type === 'output') {
                setOutput(prev => [...prev, { type: 'output', message: data.message, timestamp: new Date() }]);
              } else if (data.type === 'result') {
                setResult(data.data);
              } else if (data.type === 'complete') {
                setOutput(prev => [...prev, { type: 'success', message: data.message, timestamp: new Date() }]);
                setIsProcessing(false);
              } else if (data.type === 'error') {
                setOutput(prev => [...prev, { type: 'error', message: data.message, timestamp: new Date() }]);
                setIsProcessing(false);
              }
            } catch (e) {
              console.error('JSON parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      setOutput(prev => [...prev, { type: 'error', message: `Bağlantı hatası: ${error.message}`, timestamp: new Date() }]);
      setIsProcessing(false);
    }
  };

  // Otomatik scroll
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const formatMessage = (message) => {
    // İstatistik satırlarını formatla
    if (message.includes('='.repeat(60))) {
      return <div className="border-b border-gray-300 my-2"></div>;
    }
    
    if (message.includes('İşlenen Dosya') || 
        message.includes('Dersin Adı') || 
        message.includes('Sınıf') ||
        message.includes('Dersin Süresi') ||
        message.includes('Dersin Amacı') ||
        message.includes('Dersin Kazanımları') ||
        message.includes('EÖ Ortam ve Donanımı') ||
        message.includes('Ölçme Değerlendirme') ||
        message.includes('Dersin Kazanım Tablosu')) {
      
      const [label, value] = message.split(':');
      return (
        <div className="flex justify-between py-1">
          <span className="font-medium text-gray-700">{label.trim()}:</span>
          <span className="text-gray-900">{value?.trim()}</span>
        </div>
      );
    }
    
    return <span>{message}</span>;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-11/12 h-5/6 max-w-4xl flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-800">
            PDF İşleme - {filename}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col p-6">
          {/* Control Buttons */}
          <div className="mb-4">
            <button
              onClick={processPDF}
              disabled={isProcessing}
              className={`px-6 py-3 rounded-lg font-medium ${
                isProcessing
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isProcessing ? 'İşleniyor...' : 'PDF\'yi İşle'}
            </button>
          </div>

          {/* Output Terminal */}
          <div className="flex-1 bg-gray-900 rounded-lg p-4 overflow-hidden flex flex-col">
            <div className="text-green-400 mb-2 font-mono text-sm">
              === PDF İşleme Çıktısı ===
            </div>
            
            <div 
              ref={outputRef}
              className="flex-1 overflow-y-auto font-mono text-sm"
            >
              {output.map((item, index) => (
                <div key={index} className="mb-1">
                  <span className="text-gray-500 text-xs">
                    [{item.timestamp.toLocaleTimeString()}]
                  </span>
                  <span 
                    className={`ml-2 ${
                      item.type === 'error' ? 'text-red-400' :
                      item.type === 'success' ? 'text-green-400' :
                      item.type === 'status' ? 'text-yellow-400' :
                      'text-white'
                    }`}
                  >
                    {formatMessage(item.message)}
                  </span>
                </div>
              ))}
              
              {isProcessing && (
                <div className="text-yellow-400 animate-pulse">
                  <span className="text-gray-500 text-xs">
                    [{new Date().toLocaleTimeString()}]
                  </span>
                  <span className="ml-2">⏳ İşlem devam ediyor...</span>
                </div>
              )}
            </div>
          </div>

          {/* Results */}
          {result && (
            <div className="mt-4 bg-gray-50 rounded-lg p-4">
              <h3 className="font-semibold text-gray-800 mb-2">İşlem Sonucu:</h3>
              <div className="text-sm text-gray-600">
                <div>Ders Adı: <span className="font-medium">{result.ders_bilgileri?.ders_adi || 'Bulunamadı'}</span></div>
                <div>Sınıf: <span className="font-medium">{result.ders_bilgileri?.ders_sinifi || 'Bulunamadı'}</span></div>
                <div>Ders Saati: <span className="font-medium">{result.ders_bilgileri?.haftalik_ders_saati || 'Bulunamadı'}</span></div>
                <div>Durum: <span className={`font-medium ${result.metadata?.status === 'success' ? 'text-green-600' : 'text-yellow-600'}`}>
                  {result.metadata?.status === 'success' ? 'Başarılı' : 'Kısmi'}
                </span></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PDFProcessor;