#!/usr/bin/env python3
"""
Single Line Tablo Parse Test - Kullanıcının verdiği tek satırlık tablo metni
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils_dbf1 import ex_kazanim_tablosu, normalize_turkish_text

# Kullanıcının verdiği tek satırlık text
single_line_text = """
KAZANIM SAYISI VE SÜRE TABLOSU ÖĞRENME BİRİMİ KAZANIM SAYISI DERS SAATİ ORAN (%) Defter ve Belgeler 3 20 11 Vergi Dairesi ve Belediye İşlemleri 2 15 8 Çalışma ve Sosyal Güvenlik 3 15 8 Sosyal Güvenlik İşlemleri 3 25 14 Fatura ve Fatura Yerine Geçen Belgeler 3 40 22 Kıymetli Evraklar ve Menkul Kıymetler 2 15 8 İşletme Defteri 3 40 22 Serbest Meslek Kazanç Defteri 3 10 7 TOPLAM 22 180 100 ÖĞRENME BİRİMİ KONULAR ÖĞRENME BİRİMİ KAZANIMLARI
"""

print("🔍 Single Line Tablo Parse Test")
print("=" * 60)

print(f"📝 Input text length: {len(single_line_text)} chars")
print(f"📝 First 200 chars: {repr(single_line_text[:200])}")

# Normalized text kontrol
normalized = normalize_turkish_text(single_line_text)
print(f"\n📝 Normalized text (first 200): {normalized[:200]}")

print("\n1. ⭐ ex_kazanim_tablosu() Test:")
result_str, result_data = ex_kazanim_tablosu(single_line_text)
print(result_str)

print(f"\n2. 📋 Structured Data ({len(result_data)} items):")
for i, item in enumerate(result_data, 1):
    print(f"  {i}. {item}")

# Header detection debug
print(f"\n3. 🔍 Header Detection Debug:")

# Single-line header patterns
table_start_patterns = [
    "KAZANIM SAYISI VE SÜRE TABLOSU", 
    "DERSİN KAZANIM TABLOSU", 
    "TABLOSU",
]

for pattern in table_start_patterns:
    pattern_normalized = normalize_turkish_text(pattern)
    idx = normalized.find(pattern_normalized)
    print(f"  '{pattern}' → index: {idx}")
    if idx != -1:
        print(f"    Found at position {idx}")
        break

# TOPLAM detection
toplam_idx = single_line_text.find("TOPLAM")
print(f"\n  'TOPLAM' → index: {toplam_idx}")

# Section extraction simulation
if toplam_idx != -1:
    section_before_toplam = single_line_text[:toplam_idx]
    print(f"\n4. 📝 Section before TOPLAM:")
    print(f"Length: {len(section_before_toplam)}")
    print(f"Content: {repr(section_before_toplam[-200:])}")

# Manual pattern matching test
print(f"\n5. 🧪 Manual Pattern Test:")
import re

# Test concatenated text detection
test_section = "Defter ve Belgeler 3 20 11 Vergi Dairesi ve Belediye İşlemleri 2 15 8 Çalışma ve Sosyal Güvenlik 3 15 8"
numbers_in_section = re.findall(r'\d+', test_section)
print(f"Numbers in test section: {numbers_in_section}")
print(f"Count: {len(numbers_in_section)} (concatenated: {len(numbers_in_section) >= 3})")

# Test concatenated pattern
concatenated_pattern = r'([A-ZÜĞIŞÖÇI][A-züğışöçıİ\s]+?)\s+(\d+)(?:\s+(\d+(?:[,\.]\d+)?)\s+(\d+(?:[,\.]\d+)?))?(?=\s+[A-ZÜĞIŞÖÇI]|\s+TOPLAM|$)'
matches = re.findall(concatenated_pattern, test_section, re.IGNORECASE)
print(f"Concatenated matches: {len(matches)}")
for match in matches:
    print(f"  - {match}")