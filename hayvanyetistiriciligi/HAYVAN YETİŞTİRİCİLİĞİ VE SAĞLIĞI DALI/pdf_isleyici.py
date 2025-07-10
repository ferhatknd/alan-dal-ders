import pdfplumber
import pandas as pd
import re # Metin içinde desen aramak için kullanılacak kütüphane

def pdf_verilerini_isle(pdf_yolu):
    """
    Belirtilen PDF dosyasını okur, içindeki ders bilgilerini ayrıştırır
    ve bir pandas DataFrame olarak döndürür.

    Args:
        pdf_yolu (str): İşlenecek PDF dosyasının konumu.

    Returns:
        pandas.DataFrame: Ayrıştırılmış verileri içeren DataFrame.
    """
    # --- 1. ADIM: PDF'ten tüm metni çıkarma ---
    ham_metin = ""
    try:
        with pdfplumber.open(pdf_yolu) as pdf:
            # PDF'in tüm sayfalarını dolaşarak metinleri birleştiriyoruz.
            for sayfa in pdf.pages:
                # sayfa.extract_text() None dönerse diye kontrol ekliyoruz.
                sayfa_metni = sayfa.extract_text()
                if sayfa_metni:
                    ham_metin += sayfa_metni + "\n"
    except Exception as e:
        print(f"Hata: PDF dosyası okunamadı veya bulunamadı. Dosya yolu: {pdf_yolu}")
        print(f"Detay: {e}")
        return None

    # --- 2. ADIM: Metni ayrıştırma (Parsing) ---
    # Bu kısım, PDF'nin yapısına özel olarak düzenlenmiştir.
    
    # Öğrenme birimlerini ve onlara ait kazanımları ana tablodan bulalım.
    # den gelen bilgiye göre birimler ve kazanım sayıları
    birimler = [
        "Kişisel Hijyen ve iş güvenliği kuralları",
        "Mikroorganizmaların Özellikleri",
        "Dezenfeksiyon ve Antisepsi",
        "Sterilizasyon"
    ]
    
    # den gelen detaylı kazanımlar
    kazanimlar_desenleri = {
        "Kişisel Hijyen ve iş güvenliği kuralları": r"1\. Gerekli araç gereci kullanarak.*?2\. Bulaşıcı ve zoonoz hastalıklara.*?3\. Mevzuata uygun olarak iş sağlığı.*?",
        "Mikroorganizmaların Özellikleri": r"1\. Mikroskop ayarları ve preparat inceleme.*?2\. Bakterilerin özelliklerini açıklar.*?3\. Mantarların özelliklerini açıklar.*?4\. Virüslerin özelliklerini açıklar",
        "Dezenfeksiyon ve Antisepsi": r"1\. Talimata uygun şekilde dezenfeksiyon.*?2\. Kişisel hijyen tedbirlerini alarak.*?3\. İş sağlığı ve güvenliği tedbirlerini alarak.*?",
        "Sterilizasyon": r"1\. Uygulanacak sterilizasyon yöntemine göre.*?2\. İş sağlığı ve güvenliği tedbirlerini alarak ısı.*?3\. İş sağlığı ve güvenliği tedbirlerini alarak uygun kimyasal.*?"
    }

    # den gelen konular
    konular_desenleri = {
        "Kişisel Hijyen ve iş güvenliği kuralları": r"1\.\s*Kişisel hijyen\s*2\.\s*Bulaşıcı hastalıklara.*?3\.\s*Mevzuata uygun genel iş güvenliği",
        "Mikroorganizmaların Özellikleri": r"1\.\s*Mikroskop ayarları.*?2\.\s*Bakterilerin.*?3\.\s*Mantarların.*?4\.\s*Virüslerin",
        "Dezenfeksiyon ve Antisepsi": r"1\.\s*Dezenfeksiyon öncesi hazırlıklar\s*2\.\s*Dezenfeksiyon yöntemleri\s*3\.\s*Antisepsi",
        "Sterilizasyon": r"1\.\s*Sterilizasyon öncesi hazırlıklar\s*2\.\s*Isı uygulayarak.*?3\.\s*Kimyasal yöntemle"
    }
    
    ayristirilmis_veri = []

    for birim in birimler:
        try:
            # Konuları bulmak için regex kullanıyoruz. re.DOTALL, desenin yeni satırları da kapsamasına izin verir.
            konular_eslesme = re.search(konular_desenleri[birim], ham_metin, re.DOTALL)
            konular = konular_eslesme.group(0).strip().replace('\n', ' ') if konular_eslesme else "Bulunamadı"
            
            # Kazanımları bulmak için regex kullanıyoruz.
            kazanimlar_eslesme = re.search(kazanimlar_desenleri[birim], ham_metin, re.DOTALL)
            kazanimlar = kazanimlar_eslesme.group(0).strip().replace('\n', ' ') if kazanimlar_eslesme else "Bulunamadı"
            
            ayristirilmis_veri.append({
                "Öğrenme Birimi": birim,
                "Konular": konular,
                "Kazanımlar": kazanimlar
            })
        except Exception as e:
            print(f"'{birim}' birimi işlenirken bir hata oluştu: {e}")
            ayristirilmis_veri.append({
                "Öğrenme Birimi": birim,
                "Konular": "Hata",
                "Kazanımlar": "Hata"
            })
            
    # --- 3. ADIM: Veriyi DataFrame'e dönüştürme ---
    df = pd.DataFrame(ayristirilmis_veri)
    
    return df

# --- KODU ÇALIŞTIRMA ---

# PDF dosyanızın tam yolunu buraya yazın.
# Eğer kod ile PDF aynı klasördeyse sadece dosya adını yazmanız yeterlidir.
pdf_dosya_yolu = "MİKROBİYOLOJİ VE HİJYEN 10.pdf" 

# Fonksiyonu çağırıp verileri işliyoruz.
ders_tablosu_df = pdf_verilerini_isle(pdf_dosya_yolu)

# Sonucu kontrol edip ekrana yazdırıyoruz.
if ders_tablosu_df is not None:
    # DataFrame'i daha okunaklı bir Markdown tablosu olarak yazdır.
    print(ders_tablosu_df.to_markdown(index=False))