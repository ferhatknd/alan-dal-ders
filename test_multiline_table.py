#!/usr/bin/env python3
"""
Multi-line Tablo Parse Test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils_dbf1 import ex_kazanim_tablosu, reconstruct_multiline_entries

# Kullanıcının verdiği gerçek problematik text
real_multiline_text = """
ÖLÇME VE 
DEĞERLENDİRME 
Bu  derste;  öğrenci  performansı  belirlemeye  yönelik  çalışmalar 
değerlendirilirken  açık  uçlu  maddeler,  çoktan  seçmeli  maddeler,  doğru 
yanlış türünde maddeler, gözlem formu, derecelendirme ölçeği ve dereceli 
puanlama  anahtarı  gibi  ölçme  araçlarından  uygun  olanlar  seçilerek 
kullanılabilir.  Bunun  yanında  öz  değerlendirme  ve  akran  değerlendirme 
formları  kullanılarak  öğrencilerin,  öğretimin  süreç  boyutuna  katılmaları 
sağlanabilir. 
KAZANIM SAYISI VE 
SÜRE TABLOSU 
ÖĞRENME BİRİMİ KAZANIM 
SAYISI DERS SAATİ ORAN (%) 
Defter ve Belgeler 3 20             11 
Vergi Dairesi ve 
Belediye İşlemleri 2 15 8 
Çalışma ve Sosyal 
Güvenlik 3 15 8 
Sosyal Güvenlik 
İşlemleri 3 25 14 
Fatura ve Fatura 
Yerine Geçen 
Belgeler 
3 40 22 
Kıymetli Evraklar 
ve Menkul 
Kıymetler 
2 15 8 
İşletme Defteri 3 40 22 
Serbest Meslek 
Kazanç Defteri 3 10 7 
TOPLAM 22 180  100
"""

print("🔍 Multi-line Tablo Parse Test")
print("=" * 60)

print("\n1. ⭐ ex_kazanim_tablosu() ile Multi-line Test:")
result_str, result_data = ex_kazanim_tablosu(real_multiline_text)
print(result_str)

print(f"\n2. 📋 Structured Data ({len(result_data)} items):")
for i, item in enumerate(result_data, 1):
    print(f"  {i}. {item}")

print(f"\n3. 📊 Expected vs Actual:")
expected_titles = [
    "Defter ve Belgeler",
    "Vergi Dairesi ve Belediye İşlemleri", 
    "Çalışma ve Sosyal Güvenlik",
    "Sosyal Güvenlik İşlemleri",
    "Fatura ve Fatura Yerine Geçen Belgeler",
    "Kıymetli Evraklar ve Menkul Kıymetler",
    "İşletme Defteri",
    "Serbest Meslek Kazanç Defteri"
]

actual_titles = [item['title'] for item in result_data]

print(f"✅ Expected: {len(expected_titles)} öğrenme birimi")
print(f"🔍 Actual: {len(actual_titles)} öğrenme birimi")

print(f"\n4. 🎯 Title Matching:")
for i, expected in enumerate(expected_titles):
    if i < len(actual_titles):
        actual = actual_titles[i] 
        match = "✅" if expected.lower() == actual.lower() else "❌"
        print(f"  {match} Expected: '{expected}' | Actual: '{actual}'")
    else:
        print(f"  ❌ Missing: '{expected}'")

# Multi-line reconstruction testi
print(f"\n5. 🔧 Multi-line Reconstruction Test:")
test_lines = [
    "Vergi Dairesi ve",
    "Belediye İşlemleri 2 15 8",
    "Çalışma ve Sosyal", 
    "Güvenlik 3 15 8",
    "Defter ve Belgeler 3 20 11"
]

reconstructed = reconstruct_multiline_entries(test_lines)
print("Input lines:")
for line in test_lines:
    print(f"  '{line}'")
print("Reconstructed:")
for line in reconstructed:
    print(f"  '{line}'")