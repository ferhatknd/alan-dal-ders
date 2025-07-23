#!/usr/bin/env python3
"""
Final test to verify BERT model is working after download
"""

def test_bert_after_download():
    """Test BERT correction after model download."""
    print("🧪 BERT Model Test Başlıyor...")
    print("=" * 50)
    
    try:
        from modules.nlp_bert import correct_turkish_text_with_bert
        
        test_cases = [
            "Finansal okuryazarlı k ile amacı nı açıklar",
            "kon ulan projeler üzerinde durulur", 
            "sorusu nun incelemesini yapar",
            "kaynakları ndan bahsedilir",
            "Tasarruf -yatırım dengesini a çıklar"
        ]
        
        for i, test_text in enumerate(test_cases, 1):
            corrected = correct_turkish_text_with_bert(test_text)
            status = "FIXED" if corrected != test_text else "SAME"
            print(f"{i}. Original:  {test_text}")
            print(f"   Corrected: {corrected} [{status}]")
            print()
        
        print("🎯 BERT Test Completed!")
        return True
        
    except Exception as e:
        print(f"❌ BERT test failed: {e}")
        return False

def test_pdf_processing():
    """Test with actual PDF file."""
    print("\n" + "=" * 50)
    print("📄 PDF Processing Test")
    print("=" * 50)
    
    try:
        # Import the extract function
        from extract_olcme import extract_ob_tablosu
        
        pdf_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/39_Pazarlama_ve_Perakende/PAZARLAMA VE PERAKENDE ALANI/SEÇMELİ DERSLER/FİNANSAL OKURYAZARLIK(ALAN ORTAK).pdf"
        
        print("Processing PDF with BERT correction...")
        result = extract_ob_tablosu(pdf_path)
        
        # Check if problematic words are fixed
        problematic_words = ["okuryazarlı k", "amacı nı", "kon ulan", "v e", "sorusu nun"]
        found_issues = []
        
        for word in problematic_words:
            if word in result:
                found_issues.append(word)
        
        if found_issues:
            print(f"⚠️  Still found issues: {found_issues}")
            print("BERT correction may not be fully active")
        else:
            print("✅ All spacing issues have been corrected!")
            print("BERT correction is working properly")
        
        return len(found_issues) == 0
        
    except Exception as e:
        print(f"❌ PDF test failed: {e}")
        return False

if __name__ == "__main__":
    bert_ok = test_bert_after_download()
    pdf_ok = test_pdf_processing()
    
    print("\n" + "=" * 50)
    print("🎯 Final Results:")
    print(f"BERT Module: {'✅ WORKING' if bert_ok else '❌ FAILED'}")
    print(f"PDF Processing: {'✅ WORKING' if pdf_ok else '❌ FAILED'}")
    
    if bert_ok and pdf_ok:
        print("\n🎉 SUCCESS: Everything is working perfectly!")
        print("BERT model is now active and correcting Turkish text!")
    else:
        print("\n⚠️  Some issues remain. Check the output above.")