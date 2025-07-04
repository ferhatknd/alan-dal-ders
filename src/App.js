import React, { useState } from 'react';
import data from './data/dersler.json';
import TreeView from './TreeView';
import SelectedInfo from './SelectedInfo';

function App() {
  const [selectedDers, setSelectedDers] = useState(null);

  const handleSelectDers = (ders) => {
    setSelectedDers(ders);
  };

  return (
    <div className="App">
      <TreeView data={data} onSelect={handleSelectDers} />
      {selectedDers && <SelectedInfo ders={selectedDers} />}
    </div>
  );
}

export default App;