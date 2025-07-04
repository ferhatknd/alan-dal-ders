import React from 'react';

function TreeView({ data, onSelect }) {
  const renderDersler = (dersler) => {
    return dersler.map((ders, index) => (
      <li key={index} onClick={() => onSelect(ders)}>
        {ders.ad}
      </li>
    ));
  };

  const renderDallar = (dallar) => {
    return dallar.map((dal, index) => (
      <li key={index}>
        {dal.dal}
        <ul>{renderDersler(dal.dersler)}</ul>
      </li>
    ));
  };

  const renderAlanlar = () => {
    return data.map((alan, index) => (
      <li key={index}>
        {alan.alan}
        <ul>{renderDallar(alan.dallar)}</ul>
      </li>
    ));
  };

  return <ul>{renderAlanlar()}</ul>;
}

export default TreeView;