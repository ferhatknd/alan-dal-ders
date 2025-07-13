import sys
import os
import pdfplumber # PDF okuma kütüphanesi

# Bu betiğin (oku2.py) bulunduğu dizini al
script_dir = os.path.dirname(os.path.abspath(__file__)) 
# 'modules' klasörünün tam yolunu oluştur
modules_path = os.path.join(script_dir, 'modules')
# Bu yolu Python'ın modül arama yoluna ekle
sys.path.append(modules_path)

try:
    # getir_cop_oku.py dosyasından fonksiyonları içe aktarın
    # Eğer dosya ismi getir_cop_oku.py ise, modül adı getir_cop_oku olacaktır.
    from getir_cop_oku import find_alan_name_in_text, find_dallar_in_text # clean_text ve normalize_to_title_case_tr artık getir_cop_oku.py içinde olduğundan buradan içe aktarmaya gerek yok
except ImportError as e:
    print(f"Hata: 'getir_cop_oku.py' modülü bulunamadı veya içe aktarılamadı. Lütfen yolu ve dosya adını kontrol edin. Hata: {e}")
    sys.exit(1)

def read_pdf_content(pdf_path: str) -> str:
    """
    Belirtilen PDF dosyasının tüm metin içeriğini okur.
    """
    text_content = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text_content += page.extract_text() or ""
    except Exception as e:
        print(f"PDF dosyasını okurken bir hata oluştu: {e}")
        return ""
    return text_content

def main():
    """
    Ana fonksiyon. PDF dosya yolunu alır, metni okur ve alan/dal bilgilerini yazdırır.
    """
    # Test etmek istediğiniz PDF dosyasının adı
    pdf_file_name = "cop_9_sinif_2023_light.pdf"
    
    # PDF dosyasının tam yolu (bu betik ile aynı dizinde veya belirtilen bir alt dizinde)
    # Varsayılan olarak main_script.py ile aynı dizinde olduğunu varsayıyoruz.
    pdf_path = os.path.join(script_dir, pdf_file_name) 

    if not os.path.exists(pdf_path):
        print(f"Hata: Belirtilen PDF dosyası bulunamadı: {pdf_path}")
        print("Lütfen PDF dosyasının doğru yolda olduğundan emin olun.")
        sys.exit(1)

    print(f"'{pdf_file_name}' dosyasından içerik okunuyor...")
    pdf_text = read_pdf_content(pdf_path)

    if not pdf_text:
        print("PDF içeriği okunamadı veya boş.")
        sys.exit(1)

    # Alan adını bul
    # pdf_url argümanı, find_alan_name_in_text fonksiyonunda kullanılmasa bile mevcut imzaya uyum için burada tutulabilir.
    # Alternatif olarak, find_alan_name_in_text fonksiyonunun imzasından kaldırılabilir eğer kullanılmıyorsa.
    alan_adi = find_alan_name_in_text(pdf_text, pdf_file_name) 
    print(f"\nTespit Edilen Alan Adı: {alan_adi}")

    print("-" * 30)

    # Dal isimlerini bul
    dallar = find_dallar_in_text(pdf_text)
    print("Tespit Edilen Dal İsimleri:")
    for dal in dall:
        print(f"- {dal}")

if __name__ == "__main__":
    main()