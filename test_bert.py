import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.nlp_bert import get_semantic_matcher, correct_turkish_text_with_bert

def run_tests():
    """
    Tests the semantic similarity and text correction functionalities.
    """
    # --- Test 1: Semantic Similarity ---
    print("--- Semantic Similarity Test ---")
    matcher = get_semantic_matcher()
    
    text1 = "Canlılar"
    text2 = "Can lılar"
    
    similarity = matcher.get_similarity(text1, text2)
    print(f"Similarity between '{text1}' and '{text2}': {similarity:.2f}")
    print("\n" + "="*30 + "\n")

    # --- Test 2: Text Correction ---
    print("--- Text Correction Tests ---")
    test_phrases = [
        "Can lılar için su çok önemlidir.",
        "Bu birleşik bir ke lime dir.",
        "Yazı lım geliştir me süreci.",
        "Veri tabanı yönet im sistemleri.",
        "Türk iye'nin başkenti Ankara'dır."
    ]

    for i, phrase in enumerate(test_phrases):
        corrected_phrase = correct_turkish_text_with_bert(phrase)
        print(f"Test {i+1}:")
        print(f"  Original:  '{phrase}'")
        print(f"  Corrected: '{corrected_phrase}'")
        print("-" * 20)

if __name__ == "__main__":
    run_tests()