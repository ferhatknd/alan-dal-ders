
import React, { useState } from 'react';
import './NLPPage.css';

const NLPPage = () => {
  const [mode, setMode] = useState('correction'); // 'correction' or 'similarity'
  const [inputText1, setInputText1] = useState('');
  const [inputText2, setInputText2] = useState('');
  const [outputText, setOutputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [statistics, setStatistics] = useState(null);
  const [nlpStatistics, setNlpStatistics] = useState(null);
  const [highlightedOutput, setHighlightedOutput] = useState('');

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setInputText1('');
    setInputText2('');
    setOutputText('');
    setHighlightedOutput('');
  };

  const fetchStatistics = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/get-statistics');
      const data = await response.json();
      if (response.ok) {
        setStatistics(data);
      }
    } catch (error) {
      console.error('İstatistik alınırken hata:', error);
    }
  };

  const fetchNlpStatistics = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/nlp/statistics');
      const data = await response.json();
      if (response.ok) {
        setNlpStatistics(data);
      }
    } catch (error) {
      console.error('NLP istatistik alınırken hata:', error);
    }
  };

  const highlightDifferences = (original, corrected) => {
    const words1 = original.split(' ');
    const words2 = corrected.split(' ');
    let result = [];
    
    const maxLength = Math.max(words1.length, words2.length);
    
    for (let i = 0; i < maxLength; i++) {
      const word1 = words1[i] || '';
      const word2 = words2[i] || '';
      
      if (word1 !== word2) {
        if (word2) {
          result.push(`<span class="highlight-correction">${word2}</span>`);
        }
      } else {
        result.push(word2);
      }
    }
    
    return result.join(' ');
  };

  const highlightMatch = (content, query, index) => {
    if (index === -1) return content;
    
    const before = content.substring(0, index);
    const match = content.substring(index, index + query.length);
    const after = content.substring(index + query.length);
    
    return `${before}<span class="highlight-match">${match}</span>${after}`;
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setOutputText('');
    setHighlightedOutput('');

    const url = mode === 'correction' ? '/api/nlp/bert-correction' : '/api/nlp/semantic-similarity';
    const payload = mode === 'correction' 
      ? { text: inputText1 } 
      : { query: inputText1, content: inputText2 };

    try {
      const response = await fetch(`http://localhost:5001${url}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        if (mode === 'correction') {
          setOutputText(data.corrected_text);
          if (data.changed) {
            const highlighted = highlightDifferences(inputText1, data.corrected_text);
            setHighlightedOutput(highlighted);
          }
        } else {
          setOutputText(`Benzerlik bulundu. Index: ${data.result_index}`);
          if (data.found) {
            const highlighted = highlightMatch(inputText2, inputText1, data.result_index);
            setHighlightedOutput(highlighted);
          }
        }
        await fetchStatistics();
        await fetchNlpStatistics();
      } else {
        setOutputText(`Hata: ${data.error}`);
      }
    } catch (error) {
      setOutputText(`İstek gönderilirken bir hata oluştu: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="nlp-page">
      <div className="nlp-header">
        <h2>NLP Araçları</h2>
        <div className="mode-switcher">
          <button 
            className={mode === 'correction' ? 'active' : ''}
            onClick={() => handleModeChange('correction')}
          >
            BERT Metin Düzeltme
          </button>
          <button 
            className={mode === 'similarity' ? 'active' : ''}
            onClick={() => handleModeChange('similarity')}
          >
            Semantik Benzerlik
          </button>
        </div>
      </div>
      <div className="nlp-content">
        <div className="nlp-panel input-panel">
          <h3>Giriş</h3>
          <textarea
            className="nlp-textarea"
            value={inputText1}
            onChange={(e) => setInputText1(e.target.value)}
            placeholder={mode === 'correction' ? 'Düzeltilecek metni girin...' : 'Aranacak metni girin (query)...'}
          />
          {mode === 'similarity' && (
            <textarea
              className="nlp-textarea"
              value={inputText2}
              onChange={(e) => setInputText2(e.target.value)}
              placeholder="İçinde aranacak metni girin (content)..."
            />
          )}
          <button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'İşleniyor...' : 'Gönder'}
          </button>
        </div>
        <div className="nlp-panel output-panel">
          <h3>Çıktı</h3>
          <div className="nlp-output">
            {outputText}
          </div>
          {highlightedOutput && (
            <div className="nlp-highlighted-output">
              <h4>Vurgulanan Sonuç:</h4>
              <div 
                className="highlighted-content"
                dangerouslySetInnerHTML={{ __html: highlightedOutput }}
              />
            </div>
          )}
          {nlpStatistics && (
            <div className="statistics-section">
              <h4>NLP İşlem İstatistikleri</h4>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">Semantik Benzerlik İstekleri:</span>
                  <span className="stat-value">{nlpStatistics.semantic_similarity.total_requests}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Başarı Oranı:</span>
                  <span className="stat-value">{nlpStatistics.semantic_similarity.success_rate}%</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Ortalama Query Uzunluğu:</span>
                  <span className="stat-value">{nlpStatistics.semantic_similarity.avg_query_length}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">BERT Düzeltme İstekleri:</span>
                  <span className="stat-value">{nlpStatistics.bert_correction.total_requests}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Değişiklik Oranı:</span>
                  <span className="stat-value">{nlpStatistics.bert_correction.change_rate}%</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Ortalama Metin Uzunluğu:</span>
                  <span className="stat-value">{nlpStatistics.bert_correction.avg_original_length}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NLPPage;
