#!/usr/bin/env python3
import sys
sys.path.append('.')
from oku import extract_kazanim_tablosu, extract_genel_kazanimlar, extract_ortam_donanimi, extract_olcme_degerlendirme

def test_docx():
    docx_path = "SOSYAL MEDYA HESAP İŞLEMLERİ DBF.docx"
    
    print("=== Testing DOCX parsing ===")
    
    # Test kazanım tablosu
    kazanim_tablosu = extract_kazanim_tablosu(docx_path)
    print(f"\nKazanım Tablosu ({len(kazanim_tablosu)} items):")
    for item in kazanim_tablosu:
        print(f"  - {item}")
    
    # Test genel kazanımlar
    genel_kazanimlar = extract_genel_kazanimlar(docx_path)
    print(f"\nGenel Kazanımlar ({len(genel_kazanimlar)} items):")
    for item in genel_kazanimlar:
        print(f"  - {item}")
    
    # Test ortam donanımı
    ortam_donanimi = extract_ortam_donanimi(docx_path)
    print(f"\nOrtam Donanımı ({len(ortam_donanimi)} items):")
    for item in ortam_donanimi:
        print(f"  - {item}")
    
    # Test ölçme değerlendirme
    olcme_degerlendirme = extract_olcme_degerlendirme(docx_path)
    print(f"\nÖlçme Değerlendirme ({len(olcme_degerlendirme)} items):")
    for item in olcme_degerlendirme:
        print(f"  - {item}")

if __name__ == "__main__":
    test_docx()