#!/usr/bin/env python3
"""
Quick test of title correction functionality
"""

def test_title_correction():
    """Test the title correction logic"""
    
    # Simulate the problematic titles from the PDF output
    test_titles = [
        "Yenilenebilir Enerji Kaynakları",  # Should not be corrected (normal)
        "Fiziksel ve Elektriksel Büyüklükle r",  # Should be corrected
        "Temel Mekanik İşlemler",  # Should not be corrected (normal)
        "Lehim leme ve Baskı D evre",  # Should be corrected
        "Ölçü m İstasyonu Kurulumu",  # Should be corrected
        "Bakımı v e Kontrolü"  # Should be corrected
    ]
    
    print("=== TESTING TITLE CORRECTION LOGIC ===")
    print()
    
    for baslik in test_titles:
        # Test the problematic title detection
        needs_correction = any(problem in baslik.lower() for problem in ['büyüklükle r', 'lehim leme', 'ölçü m', ' v e ', ' d evre'])
        
        if needs_correction:
            print(f"🔧 WILL CORRECT: '{baslik}'")
            try:
                from modules.nlp_bert import correct_turkish_text_with_bert
                corrected = correct_turkish_text_with_bert(baslik)
                if corrected != baslik:
                    print(f"   ✅ CORRECTED: '{corrected}'")
                else:
                    print(f"   ⚠️  NO CHANGE: '{corrected}'")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        else:
            print(f"✅ SKIP (normal): '{baslik}'")
        print()

if __name__ == "__main__":
    test_title_correction()