import pdfplumber
import os
import sys

def extract_ders_bilgileri(pdf_path):
    """
    Belirtilen PDF dosyasındaki tablolardan dersle ilgili temel bilgileri bulur
    ve bir sözlük olarak döndürür.

    Args:
        pdf_path (str): İşlenecek PDF dosyasının yolu.

    Returns:
        dict: Bulunan ders bilgilerini içeren bir sözlük veya bir hata durumunda None.
    """
    # Dosyanın var olup olmadığını kontrol et
    if not os.path.exists(pdf_path):
        print(f"Hata: '{pdf_path}' dosyası bulunamadı.", file=sys.stderr)
        return None

    ders_bilgileri = {}
    aranacak_alanlar = [
        "DERSİN ADI",
        "DERSİN SINIFI",
        "DERSİN SÜRESİ",
        "DERSİN AMACI",
        "DERSİN KAZANIMLARI",
        "EĞİTİM-ÖĞRETİM ORTAM VE DONANIMI"
    ]

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # PDF'in tüm sayfalarını dolaş
            for page in pdf.pages:
                # Sayfadaki tabloları çıkar
                tables = page.extract_tables()
                if not tables:
                    continue

                # Her tabloyu ve satırı kontrol et
                for table in tables:
                    for row in table:
                        # Satırın ve hücrelerin geçerli olduğundan emin ol
                        if not row or len(row) < 2 or not row[0]:
                            continue

                        # İlk hücredeki metni temizle (satır sonu karakterleri vb.)
                        key_text = " ".join(str(row[0]).split())

                        # Aranacak alanlardan biriyle eşleşiyor mu kontrol et
                        for alan in aranacak_alanlar:
                            if alan in key_text:
                                # Değeri al ve temizle
                                value = row[1].strip() if row[1] else "Değer bulunamadı"
                                ders_bilgileri[alan] = value
                                break  # Bu satır için başka alan aramaya gerek yok
    except Exception as e:
        print(f"PDF işlenirken bir hata oluştu: {e}", file=sys.stderr)
        return None
    
    return ders_bilgileri

if __name__ == "__main__":
    pdf_dosya_yolu = "9. SINIF MÜZİK VE DRAMATİK ETK ATÖLYESİ.pdf"
    bilgiler = extract_ders_bilgileri(pdf_dosya_yolu)
    
    if bilgiler:
        print(f"'{pdf_dosya_yolu}' dosyasından okunan bilgiler:")
        for anahtar, deger in bilgiler.items():
            # Değerdeki olası satır sonu karakterlerini boşlukla değiştirerek yazdır
            temiz_deger = deger.replace('\n', ' ').replace('\r', '')
            print(f"- {anahtar}: {temiz_deger}")
    else:
        print(f"'{pdf_dosya_yolu}' içinde ilgili bilgiler bulunamadı.", file=sys.stderr)