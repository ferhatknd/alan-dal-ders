#!/usr/bin/env python3
"""
Hibrit Parsing Sistemi Test Script
Test eder: Content-based + regex fallback parsing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils_dbf1 import parse_table_row_by_content_type, parse_kazanim_row_robust, ex_kazanim_tablosu

def test_content_based_parsing():
    """Content-based parsing fonksiyonunu test eder"""
    print("🧪 Content-Based Parsing Test")
    print("=" * 50)
    
    test_cases = [
        # Boş sütunlu format (sizin sorununuz)
        "Programlama Yapıları    5",
        "Veri Yapıları           3",
        
        # Normal format
        "Programlama Yapıları    5    18    50.0",
        "Veri Yapıları           3    12    33.3",
        
        # Tire'li format
        "Programlama Yapıları    5    -    -",
        "Veri Yapıları           3    -    -",
        
        # Kesirli format
        "Programlama Yapıları    5    18/36    50",
        
        # Invalid cases
        "TOPLAM",
        "",
        "X",
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Test: '{test_case}'")
        result = parse_table_row_by_content_type(test_case)
        if result:
            print(f"   ✅ Title: '{result['title']}'")
            print(f"   ✅ Values: {result['values']}")
        else:
            print(f"   ❌ Parse başarısız")

def test_robust_parsing():
    """Hibrit parsing fonksiyonunu test eder"""
    print("\n🧪 Hibrit Parsing Test")
    print("=" * 50)
    
    test_cases = [
        # Boş sütunlu format (ana problem)
        "Programlama Yapıları    5",
        "Veri Yapıları           3",
        
        # Normal format
        "Programlama Yapıları    5    18    50.0",
        
        # Regex fallback gereksinimi
        "Programlama Yapıları 5 18 50.0",  # Tek boşluk
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Test: '{test_case}'")
        result = parse_kazanim_row_robust(test_case)
        if result:
            print(f"   ✅ Öğrenme Birimi: '{result['ogrenme_birimi']}'")
            print(f"   ✅ Kazanım Sayısı: {result['kazanim_sayisi']}")
            print(f"   ✅ Ders Saati: {result['ders_saati']}")
            print(f"   ✅ Oran: {result['oran']}")
        else:
            print(f"   ❌ Parse başarısız")

def test_full_table_parsing():
    """Tam tablo parsing'ini test eder"""
    print("\n🧪 Tam Tablo Parsing Test")
    print("=" * 50)
    
    # Sizin probleminize benzer format - sadece kazanım sayısı var
    sample_table = """
KAZANIM SAYISI VE SÜRE TABLOSU
ÖĞRENME BİRİMİ    KAZANIM SAYISI    DERS SAATİ    ORAN (%)

Programlama Yapıları    5
Veri Yapıları           3  
Algoritma Tasarımı      4
Web Programlama         6

TOPLAM                  18
"""
    
    print("Test Table:")
    print(sample_table)
    
    result_str, result_data = ex_kazanim_tablosu(sample_table)
    
    print("\n📊 Parsing Sonucu:")
    print(result_str)
    
    print("\n📋 Structured Data:")
    for item in result_data:
        print(f"  - {item}")
    
    print(f"\n📊 Toplam {len(result_data)} öğrenme birimi bulundu")

if __name__ == "__main__":
    test_content_based_parsing()
    test_robust_parsing() 
    test_full_table_parsing()
    
    print("\n🎯 Test tamamlandı!")