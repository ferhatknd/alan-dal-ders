#!/usr/bin/env python3
import sys
sys.path.append('.')
from oku import extract_kazanim_tablosu

def test():
    result = extract_kazanim_tablosu("ATÖLYE_DBF_10.pdf")
    print("Extracted Kazanim Tablosu:")
    for item in result:
        print(f"  - {item}")

if __name__ == "__main__":
    test()