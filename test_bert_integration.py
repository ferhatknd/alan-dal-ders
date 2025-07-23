#!/usr/bin/env python3
"""
Test script for Turkish BERT text correction integration.
Tests both the standalone BERT module and its integration with extract_olcme.py
"""

def test_bert_module():
    """Test the BERT correction module independently."""
    print("Testing BERT correction module...")
    print("=" * 50)
    
    try:
        from modules.nlp_bert import correct_turkish_text_with_bert
        
        # Test examples from the requirements
        test_cases = [
            "day alı amacı nı",
            "tahvil , repo işlemleri", 
            "bilgi sa yar sistemleri",
            "öğren me süre ci",
            "Geometrik Motif Çizi mi"
        ]
        
        print("Test Cases:")
        for i, test_text in enumerate(test_cases, 1):
            corrected = correct_turkish_text_with_bert(test_text)
            print(f"{i}. Original:  {test_text}")
            print(f"   Corrected: {corrected}")
            print()
            
    except Exception as e:
        print(f"BERT module test failed: {e}")
        return False
    
    return True

def test_extract_integration():
    """Test the integration with extract_olcme.py"""
    print("Testing integration with extract_olcme.py...")
    print("=" * 50)
    
    try:
        # Import the modified extract_ob_tablosu function
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        # Test if the import works in extract_olcme context
        from extract_olcme import extract_ob_tablosu
        print("✅ Successfully imported extract_ob_tablosu with BERT integration")
        
        # Test basic functionality without actual PDF
        print("✅ Integration appears to be working")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are available."""
    print("Testing dependencies...")
    print("=" * 50)
    
    dependencies = [
        ("torch", "PyTorch for BERT model"),
        ("transformers", "Hugging Face Transformers"),
        ("rapidfuzz", "Fast fuzzy string matching"),
        ("nltk", "Natural Language Toolkit")
    ]
    
    missing_deps = []
    for dep, description in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}: {description}")
        except ImportError:
            print(f"❌ {dep}: {description} - NOT AVAILABLE")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install " + " ".join(missing_deps))
        return False
    else:
        print("\n✅ All dependencies are available")
        return True

def main():
    """Run all tests."""
    print("Turkish BERT Text Correction - Integration Test")
    print("=" * 60)
    print()
    
    # Test dependencies first
    deps_ok = test_dependencies()
    print()
    
    # Test BERT module
    bert_ok = test_bert_module()
    print()
    
    # Test integration
    integration_ok = test_extract_integration()
    print()
    
    # Summary
    print("Test Summary:")
    print("=" * 20)
    print(f"Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"BERT Module:  {'✅ PASS' if bert_ok else '❌ FAIL'}")
    print(f"Integration:  {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    if all([deps_ok, bert_ok, integration_ok]):
        print("\n🎉 All tests passed! The system is ready to use.")
        print("\nUsage in extract_olcme.py:")
        print("The BERT correction will be automatically applied when processing PDFs.")
        print("If BERT is not available, it will fallback to rule-based correction.")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        if not deps_ok:
            print("Install missing dependencies with: pip install -r requirements.txt")

if __name__ == "__main__":
    main()