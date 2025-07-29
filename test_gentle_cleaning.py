#!/usr/bin/env python3
"""
Gentle Title Cleaning Test
"""

import re

def gentle_title_cleaning(title):
    """Gentle title temizleme - sadece gerçek artık karakterleri temizle"""
    title = title.strip()
    
    # Sadece tek karakter artıkları temizle (kelime başını koruyarak)
    if len(title) > 0 and title[0] in 'UBG':  # Tek karakterlik artıklar
        # Sonraki karakterleri kontrol et - boşluk atla ve gerçek harf ara
        remaining = title[1:].strip()
        # Sadece boşluk varsa ve sonraki kelime büyük harfle başlıyorsa artık olabilir
        # "U Gastronomi" → remove U, "UYGULAMA" → keep as is
        if remaining and remaining[0].isupper() and len(title) > len(remaining) + 1:
            # Orijinal title'da space var ise artık olabilir
            if ' ' in title[:2]:  # İlk 2 karakterde space var mı?
                title = remaining
    
    # TABLOSU kelime artığını temizle (sadece başta varsa)
    if title.upper().startswith('TABLOSU '):
        title = title[8:].strip()
    elif title.upper().startswith('BLOSU '):
        title = title[6:].strip()
    elif title.upper().startswith('LOSU '):
        title = title[5:].strip()
    
    return title

# Test cases
test_cases = [
    "U Gastronomi ve Sosyal Medya İlişkisi",  # Should clean U
    "U  Gastronomi ve Sosyal Medya İlişkisi",  # Should clean U (with extra spaces)
    "RİSK YÖNETİMİ",  # Should NOT touch
    "İkna Edici İletişim",  # Should NOT touch
    "Tüketici Davranışları",  # Should NOT touch  
    "Takıda Detay Çizimleri",  # Should NOT touch
    "TABLOSU Gastronomi",  # Should clean TABLOSU
    "BLOSU Veri Yapıları",  # Should clean BLOSU
    "UYGULAMA",  # Should NOT touch (not followed by uppercase)
    "U uygulama",  # Should NOT touch (next char is lowercase)
]

print("🔍 Gentle Title Cleaning Test")
print("=" * 50)

for i, test_case in enumerate(test_cases, 1):
    cleaned = gentle_title_cleaning(test_case)
    print(f"{i}. '{test_case}' → '{cleaned}'")