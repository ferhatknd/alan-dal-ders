#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import PyPDF2
import re
import json

def pdf_kelime_ara(pdf_path, kelimeler):
    """
    PDF dosyasından belirli kelimeleri arar ve bunların geçtiği satırları bulur.
    """
    results = {}
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Tüm sayfalardan metni çıkar
            full_text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                full_text += f"\n--- SAYFA {page_num + 1} ---\n" + text
            
            # Her kelime için arama yap
            for kelime in kelimeler:
                results[kelime] = {
                    "bulunan_satirlar": [],
                    "toplam_bulunma": 0,
                    "sayfa_numaralari": []
                }
                
                # Satır satır kontrol et
                lines = full_text.split('\n')
                current_page = 1
                
                for i, line in enumerate(lines):
                    # Sayfa numarası takibi
                    if "--- SAYFA" in line:
                        try:
                            current_page = int(re.search(r'--- SAYFA (\d+) ---', line).group(1))
                        except:
                            pass
                        continue
                    
                    # Kelimeyi büyük/küçük harf duyarsız ara
                    if kelime.upper() in line.upper():
                        results[kelime]["bulunan_satirlar"].append({
                            "satir_no": i,
                            "sayfa": current_page,
                            "icerik": line.strip()
                        })
                        results[kelime]["toplam_bulunma"] += 1
                        if current_page not in results[kelime]["sayfa_numaralari"]:
                            results[kelime]["sayfa_numaralari"].append(current_page)
            
            # Tam metni de kaydet
            results["tam_metin"] = full_text
            
    except Exception as e:
        results["hata"] = str(e)
    
    return results

# Ana program
if __name__ == "__main__":
    pdf_dosyasi = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/1_TEKNİK_RESİM_DBF_9.pdf"
    aranan_kelimeler = ["EĞİTİM", "ÖĞRETİM", "ORTAM", "DONANIM"]
    
    print("PDF kelime arama başlıyor...")
    print(f"Dosya: {pdf_dosyasi}")
    print(f"Aranan kelimeler: {aranan_kelimeler}")
    print("-" * 50)
    
    sonuclar = pdf_kelime_ara(pdf_dosyasi, aranan_kelimeler)
    
    # Sonuçları JSON dosyasına kaydet
    with open("kelime_arama_sonuclari.json", "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)
    
    # Sonuçları ekrana yazdır
    for kelime in aranan_kelimeler:
        if kelime in sonuclar:
            print(f"\n🔍 '{kelime}' kelimesi için sonuçlar:")
            print(f"Toplam bulunma sayısı: {sonuclar[kelime]['toplam_bulunma']}")
            print(f"Sayfa numaraları: {sonuclar[kelime]['sayfa_numaralari']}")
            
            if sonuclar[kelime]["bulunan_satirlar"]:
                print("Bulunan satırlar:")
                for satir in sonuclar[kelime]["bulunan_satirlar"]:
                    print(f"  Sayfa {satir['sayfa']}: {satir['icerik']}")
            else:
                print("Bu kelime PDF'de bulunamadı.")
            print("-" * 30)
    
    if "hata" in sonuclar:
        print(f"❌ Hata: {sonuclar['hata']}")
    else:
        print("✅ Arama tamamlandı. Sonuçlar 'kelime_arama_sonuclari.json' dosyasına kaydedildi.")