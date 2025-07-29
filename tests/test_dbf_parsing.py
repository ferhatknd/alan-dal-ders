import os
import pytest

# Skip entire module if PyMuPDF is unavailable
pytest.importorskip('fitz')

from modules.utils_dbf1 import ex_temel_bilgiler, ex_kazanim_tablosu

TEST_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(TEST_DIR, '..', 'data', 'dbf')
SAMPLE_FILE = os.path.join(DATA_DIR, 'sample.txt')


def load_sample_text():
    with open(SAMPLE_FILE, encoding='utf-8') as f:
        return f.read()


def test_kazanim_tablosu_parsing():
    text = load_sample_text()
    _result_str, data = ex_kazanim_tablosu(text)
    assert len(data) == 2
    assert data[0]['title'] == 'Donanım Temelleri'
    assert data[1]['count'] == 6


def test_temel_bilgiler_parsing():
    text = load_sample_text()
    info = ex_temel_bilgiler(text)
    # Only check that DERSİN ADI was extracted correctly
    ders_adi = info.get('Case1_DERSİN ADI')
    assert ders_adi == 'Bilgisayar Donanımı'

