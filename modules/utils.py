def normalize_to_title_case_tr(name: str) -> str:
    """
    Bir metni, Türkçe karakterleri ve dil kurallarını dikkate alarak
    "Başlık Biçimine" (Title Case) dönüştürür.

    Örnekler:
    - "BİLİŞİM TEKNOLOJİLERİ" -> "Bilişim Teknolojileri"
    - "gıda ve içecek hizmetleri" -> "Gıda ve İçecek Hizmetleri"
    - "ELEKTRİK-ELEKTRONİK TEKNOLOJİSİ" -> "Elektrik-Elektronik Teknolojisi"
    - "elektrik-elektronik teknolojisi" -> "Elektrik-Elektronik Teknolojisi"

    Args:
        name: Standartlaştırılacak metin.

    Returns:
        Başlık biçimine dönüştürülmüş metin.
    """
    if not name:
        return ""

    # Tireyi geçici olarak özel karakter ile değiştir (tire öncesi/sonrası boşlukları da temizle)
    name = name.replace(' - ', '-').replace('- ', '-').replace(' -', '-')
    name = name.replace('-', ' __tire__ ')
    
    # Metni temizle: baştaki/sondaki boşluklar, çoklu boşlukları tek boşluğa indirge
    # ve tamamını küçük harfe çevirerek başla.
    # Türkçe'ye özgü 'İ' -> 'i' ve 'I' -> 'ı' dönüşümü için replace kullanılır.
    cleaned_name = ' '.join(name.strip().split()).replace('İ', 'i').replace('I', 'ı').lower()

    # Bağlaçlar gibi küçük kalması gereken kelimeler.
    lowercase_words = ["ve", "ile", "için", "de", "da", "ki"]

    words = cleaned_name.split(' ')
    final_words = []

    for word in words:
        if not word:
            continue

        if word == '__tire__':
            # Tire durumunda bir önceki kelime ile birleştir
            if final_words:
                final_words[-1] += '-'
            continue  # Bu kelimeyi atlayıp sonraki kelimeyi bekle
        elif word in lowercase_words and len(final_words) > 0:  # İlk kelime asla küçük olmasın
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += word
            else:
                final_words.append(word)
        else:
            capitalized = 'İ' + word[1:] if word.startswith('i') else word.capitalize()
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += capitalized
            else:
                final_words.append(capitalized)

    return ' '.join(final_words)