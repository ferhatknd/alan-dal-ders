#!/usr/bin/env python3
"""
Debug script to test why Bireysel Bütçeleme is not matching on user's system
"""

def test_semantic_find():
    print("🔍 Testing semantic_find function...")
    
    try:
        from extract_olcme import semantic_find
        
        # Test 1: Simple test
        test_content = "Bu derste Bireysel Bütçe konuları işlenecektir."
        result = semantic_find("Bireysel Bütçeleme", test_content, 75)
        print(f"Test 1 - Simple semantic_find: {result}")
        
        # Test 2: Test imports
        try:
            from modules.nlp_bert import semantic_find as bert_semantic_find
            print("✅ BERT semantic_find import OK")
            
            result2 = bert_semantic_find("Bireysel Bütçeleme", test_content, 0.75)
            print(f"Test 2 - Direct BERT semantic_find: {result2}")
            
        except ImportError as e:
            print(f"❌ BERT import failed: {e}")
            print("Using fallback...")
            
        # Test 3: Check sentence-transformers
        try:
            from modules.nlp_bert import get_semantic_matcher
            matcher = get_semantic_matcher()
            similarity = matcher.get_similarity("Bireysel Bütçeleme", "Bireysel Bütçe")
            print(f"Test 3 - Semantic similarity: {similarity:.3f} ({similarity*100:.1f}%)")
            
        except Exception as e:
            print(f"❌ Semantic matcher failed: {e}")
            
    except Exception as e:
        print(f"❌ semantic_find import failed: {e}")

def test_pdf_content():
    print("\n🔍 Testing actual PDF content...")
    
    try:
        import PyPDF2
        import re
        from extract_olcme import normalize_turkish_chars, semantic_find
        
        pdf_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/39_Pazarlama_ve_Perakende/PAZARLAMA VE PERAKENDE ALANI/SEÇMELİ DERSLER/FİNANSAL OKURYAZARLIK(ALAN ORTAK).pdf"
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
        
        # Normalizasyon
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = normalize_turkish_chars(full_text)
        
        # BERT correction test
        try:
            from modules.nlp_bert import correct_turkish_text_with_bert
            full_text = correct_turkish_text_with_bert(full_text)
            print("✅ BERT text correction applied")
        except ImportError:
            print("⚠️ BERT text correction not available")
        
        # Check if "Bireysel Bütçe" exists
        if "Bireysel Bütçe" in full_text:
            print("✅ 'Bireysel Bütçe' found in PDF")
            idx = full_text.find("Bireysel Bütçe")
            context = full_text[max(0, idx-30):idx+50]
            print(f"Context: ...{context}...")
        else:
            print("❌ 'Bireysel Bütçe' not found in PDF")
        
        # Test semantic_find on actual content
        result = semantic_find("Bireysel Bütçeleme", full_text, 75)
        print(f"Semantic find on full PDF: {result}")
        
        if result >= 0:
            context = full_text[max(0, result-30):result+50]
            print(f"Found context: ...{context}...")
            
    except Exception as e:
        print(f"❌ PDF test failed: {e}")

if __name__ == "__main__":
    print("🐛 Bireysel Bütçeleme Debug Test")
    print("=" * 50)
    
    test_semantic_find()
    test_pdf_content()
    
    print("\n" + "=" * 50)
    print("Debug test completed. Please share the output.")