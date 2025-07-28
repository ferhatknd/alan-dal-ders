import React, { useState, useMemo } from 'react';
import './DataTable.css';

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
    <div className="filter-dropdown">
      <div className="filter-dropdown-header">
        <strong>{displayName} Filtresi</strong>
        <div>
          <button 
            onClick={onClear}
            className="filter-clear-btn"
          >
            Temizle
          </button>
          <button 
            onClick={onToggle}
            className="filter-close-btn"
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
        className="filter-search-input"
        autoFocus
        onClick={(e) => e.stopPropagation()}
      />
      
      {filteredItems.map(([value, count]) => (
        <div key={value} className="filter-item">
          <label className="filter-item-label">
            <input
              type="checkbox"
              checked={selectedValues.includes(String(value))}
              onChange={(e) => onFilterChange(String(value), e.target.checked)}
              className="filter-item-checkbox"
            />
            <span>{value || 'Boş'} ({count})</span>
          </label>
        </div>
      ))}
    </div>
  );
};

const DataTable = ({ tableData, searchTerm, onCourseEdit, onDocumentView }) => {
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
        ((row.alan_adi && row.alan_adi.toLowerCase().includes(term)) ||
        (row.dal_adi && row.dal_adi.toLowerCase().includes(term)) ||
        (row.ders_adi && row.ders_adi.toLowerCase().includes(term)))
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
    if (!columnStats[column] || !columnStats[column].items) return [];
    
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
      <div className="table-summary">
        <strong>Toplam: {sortedData.length} ders</strong>
      </div>
      <table className="comprehensive-data-table">
        <thead>
          <tr>
            {['alan_adi', 'dal_adi', 'ders_adi', 'sinif', 'ders_saati'].map(column => (
              <th key={column} onClick={() => handleSort(column)} className="sortable-header">
                <div className="header-content">
                  <span>
                    {getColumnDisplayName(column)} {getSortIcon(column)}
                    <span className="column-count">
                      ({columnStats[column] && columnStats[column].uniqueCount || 0})
                    </span>
                  </span>
                  <button 
                    onClick={(e) => { e.stopPropagation(); toggleFilter(column); }}
                    className="filter-toggle-btn"
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
            <tr key={`${row.alan_id}-${row.dal_id}-${row.ders_id || 'empty'}-${index}`}>
              <td>{row.alan_adi || '-'}</td>
              <td>{row.dal_adi || '-'}</td>
              <td>{row.ders_adi || '-'}</td>
              <td>{row.sinif || '-'}</td>
              <td>{row.ders_saati || 0}</td>
              <td>
                {row.dm_url ? (
                  <a href={row.dm_url} target="_blank" rel="noopener noreferrer" className="ders-link">
                    📄 DM
                  </a>
                ) : ("-")}
              </td>
              <td>
                {row.dbf_url ? (
                  <button 
                    onClick={() => onDocumentView && onDocumentView(row, row.dbf_url, 'DBF')}
                    className="dbf-link-btn"
                    title="DBF dosyasını görüntüle"
                  >
                    📄 {row.dbf_url.toLowerCase().endsWith('.pdf') ? 'PDF' : 
                        row.dbf_url.toLowerCase().endsWith('.docx') ? 'DOCX' : 'DBF'}
                  </button>
                ) : ("-")}
              </td>
              <td>
                {row.bom_url ? (
                  <a href={row.bom_url} target="_blank" rel="noopener noreferrer" className="bom-link">
                    📄 BOM
                  </a>
                ) : ("-")}
              </td>
              <td>
                {row.ders_id && row.dbf_url && row.dbf_url.trim() !== '' ? (
                  <button 
                    className="edit-btn" 
                    onClick={() => onCourseEdit && onCourseEdit(row)}
                    title="Düzenle"
                  >
                    ✏️
                  </button>
                ) : ("-")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;