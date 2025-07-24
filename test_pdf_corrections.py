#!/usr/bin/env python3
"""
Test BERT corrections for the specific PDF problems found
"""

from modules.nlp_bert import correct_turkish_text_with_bert

def test_pdf_corrections():
    """Test corrections for problematic text from the actual PDF"""
    
    problematic_texts = [
        'Fiziksel ve Elektriksel Büyüklükle r',
        'Lehim leme ve Baskı D evre', 
        'Ölçü m İstasyonu Kurulumu',
        'Bakımı v e Kontrolü',
        'Doğrultma , Filtre',
        'Büyüklükle r',
        'Lehim leme',
        'Ölçü m'
    ]

    print('=== TESTING PDF CORRECTION EXAMPLES ===')
    print()
    
    fixed_count = 0
    total_count = len(problematic_texts)
    
    for text in problematic_texts:
        corrected = correct_turkish_text_with_bert(text)
        if corrected != text:
            status = 'FIXED'
            fixed_count += 1
        else:
            status = 'SAME'
            
        print(f'[{status}] {text}')
        print(f'    -> {corrected}')
        print()
    
    print(f'=== RESULTS: {fixed_count}/{total_count} corrections applied ===')
    print()
    
    if fixed_count > 0:
        print('✅ BERT system successfully corrected Turkish text issues!')
    else:
        print('⚠️  BERT system needs further tuning for these specific cases.')
    
    return fixed_count, total_count

if __name__ == "__main__":
    test_pdf_corrections()