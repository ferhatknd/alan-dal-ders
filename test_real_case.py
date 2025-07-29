#!/usr/bin/env python3
"""
Real Case Test - Gerçek PDF'den çıkan problematik text'i test eder
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils_dbf1 import parse_kazanim_row_robust, ex_kazanim_tablosu

# Gerçek problematik text
real_text = """
KAZANIM SAYISI VE SÜRE TABLOSU ÖĞRENME BİRİMİ KAZANIM SAYISI DERS SAATİ ORAN (%) Gastronomi ve Sosyal Medya İlişkisi 3 Gastronomi ile İlgili Medya Alanları 6 Gastronomi ve Sosyoloji 2 TOPLAM ÖĞRENME BİRİMİ KONULAR ÖĞRENME BİRİMİ KAZANIMLARI
"""

print("🔍 Real Case Debug")
print("=" * 50)
print(f"📝 Input text: {repr(real_text)}")

print("\n📊 ex_kazanim_tablosu() Sonucu:")
result_str, result_data = ex_kazanim_tablosu(real_text)
print(result_str)

print(f"\n📋 Structured Data:")
for item in result_data:
    print(f"  - {item}")

print(f"\n📊 Toplam {len(result_data)} öğrenme birimi bulundu")

# Manuel satır parsing deneyelim
print(f"\n🧪 Manuel Satır Parsing:")

# Bu text'i sayılardan bölelim
import re
parts = re.split(r'(\d+)', real_text)
print(f"📝 Split by numbers: {parts}")

# Daha akıllı approach: öğrenme birimi pattern'lerini ara
# "Kelimeler + sayı" pattern'i
pattern = r'([A-ZÜĞIŞÖÇI][A-züğışöçıİ\s]+?)\s+(\d+)'
matches = re.findall(pattern, real_text)
print(f"\n📝 Pattern matches:")
for match in matches:
    print(f"  - '{match[0].strip()}' → {match[1]}")