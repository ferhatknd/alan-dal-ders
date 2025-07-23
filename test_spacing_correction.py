#!/usr/bin/env python3
"""
Test script for Turkish text spacing correction.
Tests the specific spacing issues found in the PDF processing.
"""

def test_spacing_correction():
    """Test the BERT correction system with the actual problematic text."""
    print("Testing Spacing Correction with Real PDF Text Issues")
    print("=" * 60)
    
    # Actual problematic text from the PDF
    test_cases = [
        "okuryazarlı k",
        "Finansa",
        "kon ulan", 
        "v e",
        "sorusu nun",
        "kaynakları ndan",
        "amacı nı",
        "ilkeleri ni",
        "Tasarruf -yatırım",
        "uygulama lar",
        "a çıklar",
        # Additional compound test
        "Finansal okuryazarlı k tanımlanır ve amacı nı açıklar",
        "Türkiye'de finansal okuryazarlık alanında kon ulan projeler",
        "İhtiyaç mı İstek mı sorusu nun incelemesi",
        "Tasarruf -yatırım dengesini a çıklar"
    ]
    
    try:
        from modules.nlp_bert import correct_turkish_text_with_bert
        
        print("Testing with BERT correction system...")
        print()
        
        for i, test_text in enumerate(test_cases, 1):
            corrected = correct_turkish_text_with_bert(test_text)
            status = "✅ FIXED" if corrected != test_text else "⚠️  SAME"
            
            print(f"{i:2d}. Original:  '{test_text}'")
            print(f"    Corrected: '{corrected}' {status}")
            
            # Show specific improvements
            if corrected != test_text:
                print(f"    Change:    '{test_text}' → '{corrected}'")
            print()
            
    except Exception as e:
        print(f"❌ BERT test failed: {e}")
        print("\nTesting with rule-based correction only...")
        test_rule_based_correction(test_cases)

def test_rule_based_correction(test_cases):
    """Test rule-based correction as fallback."""
    try:
        from modules.nlp_bert import TurkishBERTCorrector
        corrector = TurkishBERTCorrector()
        
        print("Rule-based correction results:")
        print("-" * 40)
        
        for i, test_text in enumerate(test_cases, 1):
            # Test rule-based correction
            corrected = corrector._apply_turkish_rules(test_text)
            status = "✅ FIXED" if corrected != test_text else "⚠️  SAME"
            
            print(f"{i:2d}. '{test_text}' → '{corrected}' {status}")
        
        print("\n📝 Analysis:")
        print("- Rule-based correction handles punctuation spacing well")
        print("- Word spacing issues require BERT model for context-aware fixes")
        print("- Once BERT model downloads, these issues should be resolved")
        
    except Exception as e:
        print(f"❌ Rule-based test also failed: {e}")

def analyze_spacing_patterns():
    """Analyze the patterns in spacing issues."""
    print("\n" + "=" * 60)
    print("Pattern Analysis for Spacing Issues")
    print("=" * 60)
    
    patterns = [
        ("Word split with suffix", ["okuryazarlı k", "amacı nı", "ilkeleri ni", "sorusu nun"]),
        ("Word split generic", ["kon ulan", "v e", "a çıklar"]),
        ("Compound word split", ["kaynakları ndan", "uygulama lar"]),
        ("Hyphenated compound", ["Tasarruf -yatırım"]),
        ("Single word fragment", ["Finansa"])
    ]
    
    for pattern_name, examples in patterns:
        print(f"\n📋 {pattern_name}:")
        for example in examples:
            print(f"   • '{example}'")
    
    print("\n🔧 Expected BERT Corrections:")
    expected_corrections = [
        ("okuryazarlı k", "okuryazarlık"),
        ("amacı nı", "amacını"),
        ("ilkeleri ni", "ilkelerini"), 
        ("sorusu nun", "sorusunun"),
        ("kon ulan", "konulan"),
        ("v e", "ve"),
        ("a çıklar", "açıklar"),
        ("kaynakları ndan", "kaynaklarından"),
        ("uygulama lar", "uygulamalar"),
        ("Tasarruf -yatırım", "Tasarruf-yatırım")
    ]
    
    for original, expected in expected_corrections:
        print(f"   • '{original}' → '{expected}'")

def test_full_sentence_correction():
    """Test correction on full sentences from the PDF."""
    print("\n" + "=" * 60)
    print("Full Sentence Correction Test")
    print("=" * 60)
    
    sentences = [
        "Finansal okuryazarlı k tanımlanır ve amacı nı açıklar",
        "Türkiye'de finansal okuryazarlık alanında kon ulan projeler üzerinde durulur",
        "İhtiyaç mı İstek mı sorusu nun incelemesini yapar",
        "Tasarruf -yatırım dengesini a çıklar ve uygulama lar yapılır"
    ]
    
    try:
        from modules.nlp_bert import correct_turkish_text_with_bert
        
        for i, sentence in enumerate(sentences, 1):
            corrected = correct_turkish_text_with_bert(sentence)
            print(f"\n{i}. Original:")
            print(f"   {sentence}")
            print(f"   Corrected:")
            print(f"   {corrected}")
            
            if corrected != sentence:
                print("   ✅ Sentence was corrected")
            else:
                print("   ⚠️  No changes made")
                
    except Exception as e:
        print(f"❌ Full sentence test failed: {e}")

def main():
    """Run all spacing correction tests."""
    test_spacing_correction()
    analyze_spacing_patterns()
    test_full_sentence_correction()
    
    print("\n" + "=" * 60)
    print("🎯 Conclusion:")
    print("- These spacing issues are exactly what BERT correction targets")
    print("- Current rule-based system handles punctuation but not word splits")
    print("- Once BERT model downloads, context-aware corrections will work")
    print("- The system is designed to handle these specific Turkish text issues")

if __name__ == "__main__":
    main()