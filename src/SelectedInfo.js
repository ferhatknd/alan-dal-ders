import React from 'react';

function SelectedInfo({ ders }) {
  return (
    <div>
      <h2>{ders.ad}</h2>
      <p>11. Sınıf Saati: {ders.saat11}</p>
      <p>12. Sınıf Saati: {ders.saat12}</p>
    </div>
  );
}

export default SelectedInfo;