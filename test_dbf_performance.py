#!/usr/bin/env python3
"""
Performance test for DBF processing to identify the 30+ second bottleneck
"""

import time
import os
import sys

def find_test_dbf():
    """Find a small DBF file for testing"""
    base_path = "data/dbf"
    
    # Look for PDF files
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(root, file)
                # Get file size
                size = os.path.getsize(file_path)
                if size < 5 * 1024 * 1024:  # Less than 5MB
                    return file_path
    return None

def test_dbf_processing():
    """Test DBF processing performance step by step"""
    
    print("🔍 DBF PROCESSING PERFORMANCE TEST")
    print("=" * 50)
    
    # Find a test file
    test_file = find_test_dbf()
    if not test_file:
        print("❌ No small DBF file found for testing")
        return
    
    print(f"📄 Test file: {os.path.basename(test_file)}")
    print(f"📐 Size: {os.path.getsize(test_file) / 1024:.1f} KB")
    print()
    
    # Step 1: Test PDF reading
    print("🔄 Step 1: PDF Reading...")
    start_time = time.time()
    
    try:
        import PyPDF2
        with open(test_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
        
        pdf_time = time.time() - start_time
        print(f"✅ PDF reading: {pdf_time:.3f}s ({len(full_text)} chars)")
    except Exception as e:
        print(f"❌ PDF reading failed: {e}")
        return
    
    # Step 2: Test BERT correction loading
    print("\n🔄 Step 2: BERT Model Loading...")
    start_time = time.time()
    
    try:
        from modules.nlp_bert import get_corrector
        corrector = get_corrector()
        bert_load_time = time.time() - start_time
        print(f"✅ BERT loading: {bert_load_time:.3f}s (device: {corrector.device})")
    except Exception as e:
        print(f"❌ BERT loading failed: {e}")
        return
    
    # Step 3: Test text correction
    print("\n🔄 Step 3: Text Correction...")
    start_time = time.time()
    
    try:
        # Test with first 1000 characters to avoid long processing
        test_text = full_text[:1000]
        from modules.nlp_bert import correct_turkish_text_with_bert
        corrected = correct_turkish_text_with_bert(test_text)
        correction_time = time.time() - start_time
        print(f"✅ Text correction: {correction_time:.3f}s (1000 chars)")
    except Exception as e:
        print(f"❌ Text correction failed: {e}")
        return
    
    # Step 4: Test semantic matching
    print("\n🔄 Step 4: Semantic Matching...")
    start_time = time.time()
    
    try:
        from modules.nlp_bert import semantic_find
        pos = semantic_find("test", full_text[:500], threshold=0.7)
        semantic_time = time.time() - start_time
        print(f"✅ Semantic matching: {semantic_time:.3f}s")
    except Exception as e:
        print(f"❌ Semantic matching failed: {e}")
        return
    
    # Summary
    total_time = pdf_time + bert_load_time + correction_time + semantic_time
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE BREAKDOWN:")
    print("=" * 50)
    print(f"📄 PDF Reading: {pdf_time:.3f}s ({pdf_time/total_time*100:.1f}%)")
    print(f"🤖 BERT Loading: {bert_load_time:.3f}s ({bert_load_time/total_time*100:.1f}%)")
    print(f"🔧 Text Correction: {correction_time:.3f}s ({correction_time/total_time*100:.1f}%)")
    print(f"🎯 Semantic Matching: {semantic_time:.3f}s ({semantic_time/total_time*100:.1f}%)")
    print(f"⚡ Total: {total_time:.3f}s")
    print()
    
    if bert_load_time > 10:
        print("⚠️  BOTTLENECK: BERT model loading is slow (>10s)")
    elif correction_time > 5:
        print("⚠️  BOTTLENECK: Text correction is slow (>5s)")
    elif pdf_time > 2:
        print("⚠️  BOTTLENECK: PDF reading is slow (>2s)")
    else:
        print("✅ Performance looks good!")
    
    print("\n🔍 DIAGNOSIS:")
    if total_time > 30:
        print("❌ Total time >30s - Major bottleneck detected!")
        if bert_load_time > 20:
            print("🎯 Issue: BERT model loading taking too long")
            print("💡 Solution: Model caching not working properly")
        elif correction_time > 20:
            print("🎯 Issue: Text correction processing too slow")
            print("💡 Solution: Reduce text size or optimize BERT processing")
    else:
        print("✅ Processing time acceptable")

if __name__ == "__main__":
    test_dbf_processing()