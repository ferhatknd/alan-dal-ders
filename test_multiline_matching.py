#!/usr/bin/env python3
"""
Test script to verify multi-line text matching algorithm
"""

import re

def test_multiline_matching():
    # Test case: Text with line breaks like in PDF tables
    test_content = """
Perde Duvar Detayları 
Çizimi 
3 
10 
2,8 
Bilgisayarla Belirlenen 
İstikamete Göre Yol Güzergâhı 
Çizimi 
6 
15 
4,2 
Bilgisayarla Yol Projelerinde 
Boy Kesit Çizimleri 
6 
10 
2,8 
Bilgisayarla Yol Projelerinde En 
Kesit Çizimleri 
6 
15 
4,2
"""
    
    # Test header that should be found
    header_to_find = "Bilgisayarla Yol Projelerinde Boy Kesit Çizimleri"
    
    print(f"Looking for: '{header_to_find}'")
    print("In content that contains:")
    print("=" * 50)
    print(test_content.strip())
    print("=" * 50)
    
    # Test the new algorithm
    header_normalized = re.sub(r'\s+', ' ', header_to_find.strip().upper())
    content_normalized = re.sub(r'\s+', ' ', test_content.strip().upper())
    
    print(f"\nNormalized header: '{header_normalized}'")
    print(f"Normalized content sample: '{content_normalized[:200]}...'")
    
    match_pos = content_normalized.find(header_normalized)
    
    if match_pos >= 0:
        print(f"\n✅ SUCCESS: Found match at position {match_pos}")
        
        # Show the matched text in context
        start = max(0, match_pos - 50)
        end = min(len(content_normalized), match_pos + len(header_normalized) + 50)
        context = content_normalized[start:end]
        print(f"Context: '...{context}...'")
        
    else:
        print(f"\n❌ FAILED: Could not find '{header_normalized}' in normalized content")
        
        # Test individual words
        words = header_normalized.split()
        print(f"\nTesting individual words:")
        for word in words:
            if word in content_normalized:
                print(f"  ✅ '{word}' found")
            else:
                print(f"  ❌ '{word}' NOT found")

if __name__ == "__main__":
    test_multiline_matching()