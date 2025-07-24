#!/usr/bin/env python3
"""
Test extract_olcme.py performance to find the 30+ second bottleneck
"""

import time
import sys
import os

def test_extract_performance():
    """Test the performance of extract_olcme.py functions"""
    
    print("⏱️  EXTRACT_OLCME.PY PERFORMANCE TEST")
    print("=" * 50)
    
    # Import the functions
    sys.path.append('.')
    
    # Test file - use a known file
    test_file = "data/dbf/13_Geleneksel_Turk_Sanatlari/GELENEKSEL TÜRK SANATLARI/TEZHİP ATÖLYESİ 11.pdf"
    
    if not os.path.exists(test_file):
        print("❌ Test file not found")
        return
    
    print(f"📄 Testing with: {os.path.basename(test_file)}")
    print()
    
    # Step 1: Test KAZANIM TABLOSU extraction
    print("🔄 Step 1: KAZANIM SAYISI VE SÜRE TABLOSU...")
    start_time = time.time()
    
    try:
        from extract_olcme import extract_kazanim_sayisi_sure_tablosu
        result1 = extract_kazanim_sayisi_sure_tablosu(test_file)
        kazanim_time = time.time() - start_time
        print(f"✅ Kazanım extraction: {kazanim_time:.3f}s")
        print(f"   Result length: {len(result1)} chars")
    except Exception as e:
        print(f"❌ Kazanım extraction failed: {e}")
        return
    
    # Step 2: Test ÖĞRENME BİRİMİ extraction (this is likely the bottleneck)
    print("\n🔄 Step 2: ÖĞRENME BİRİMİ ALANI (This may be slow)...")
    start_time = time.time()
    
    try:
        from extract_olcme import extract_ob_tablosu
        result2 = extract_ob_tablosu(test_file)
        ob_time = time.time() - start_time
        print(f"✅ Öğrenme Birimi extraction: {ob_time:.3f}s")
        print(f"   Result length: {len(result2)} chars")
    except Exception as e:
        print(f"❌ Öğrenme Birimi extraction failed: {e}")
        ob_time = 0
    
    # Summary
    total_time = kazanim_time + ob_time
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE ANALYSIS:")
    print("=" * 50)
    print(f"⚡ Kazanım Tablosu: {kazanim_time:.3f}s")
    print(f"⚡ Öğrenme Birimi: {ob_time:.3f}s")
    print(f"⚡ Total: {total_time:.3f}s")
    print()
    
    if ob_time > 20:
        print("🎯 BOTTLENECK FOUND: Öğrenme Birimi extraction >20s")
        print("💡 Likely cause: BERT correction being applied to every title")
        print("💡 Solution: Optimize title correction or add caching")
    elif kazanim_time > 10:
        print("🎯 BOTTLENECK: Kazanım extraction >10s")
    elif total_time > 30:
        print("🎯 BOTTLENECK: Total processing >30s")
    else:
        print("✅ Performance is acceptable")
    
    # Check if BERT was actually used
    print("\n🤖 BERT Usage Check:")
    try:
        from modules.nlp_bert import get_corrector
        corrector = get_corrector()
        print(f"✅ BERT Device: {corrector.device}")
        print(f"✅ BERT Available: {corrector.model is not None}")
    except Exception as e:
        print(f"❌ BERT check failed: {e}")

if __name__ == "__main__":
    test_extract_performance()