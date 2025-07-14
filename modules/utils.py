import os
import requests
from typing import Optional

def download_and_cache_pdf(url: str, cache_type: str, alan_adi: str, additional_info: str = None, alan_id: str = None) -> Optional[str]:
    """
    PDF'yi indirir ve organize şekilde cache'ler.
    
    Args:
        url: PDF URL'si
        cache_type: 'cop', 'dbf', 'dm', 'bom' gibi dosya tipi
        alan_adi: Alan adı (klasör adı için)
        additional_info: Ek bilgi (sınıf, dal vb.)
        alan_id: Alan ID'si (organizasyon için, opsiyonel)
    
    Returns:
        İndirilen dosyanın yolu veya None
    """
    if not url or not cache_type or not alan_adi:
        return None
    
    try:
        # Normalize alan adı (klasör adı için)
        safe_alan_adi = alan_adi.replace(' ', '_').replace('/', '_').replace('\\', '_')
        
        # Klasör yapısı belirleme
        if alan_id and cache_type in ['cop', 'dbf', 'dm', 'bom']:
            # ID bazlı organizasyon: {ID:02d}_-_{alan_adi}
            folder_name = f"{int(alan_id):02d}_-_{safe_alan_adi}"
        else:
            # Eski format: {alan_adi}
            folder_name = safe_alan_adi
            
        cache_dir = os.path.join("data", cache_type, folder_name)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Dosya adını URL'den çıkar
        filename = url.split('/')[-1]
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        # Ek bilgi varsa dosya adına ekle
        if additional_info:
            name_part, ext = os.path.splitext(filename)
            filename = f"{name_part}_{additional_info}{ext}"
        
        file_path = os.path.join(cache_dir, filename)
        
        # Dosya zaten varsa indirme
        if os.path.exists(file_path):
            print(f"📁 Cache'den alınıyor: {file_path}")
            return file_path
        
        # PDF'yi indir
        print(f"⬇️ İndiriliyor: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Dosyayı kaydet
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Kaydedildi: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ PDF indirme hatası ({url}): {e}")
        return None


def get_temp_pdf_path(url: str) -> str:
    """
    Geçici PDF dosyası için güvenli yol oluştur
    """
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"temp_pdf_{url_hash}.pdf"


def get_cop_cache_path(alan_adi: str, sinif: str, year: str = None, alan_id: str = None) -> str:
    """
    ÇÖP PDF'i için organize cache yolu oluştur
    
    Args:
        alan_adi: Alan adı
        sinif: Sınıf seviyesi (9, 10, 11, 12)
        year: Güncelleme yılı (opsiyonel)
        alan_id: Alan ID'si (opsiyonel)
    
    Returns:
        Cache dosya yolu
    """
    # Normalize alan adı
    safe_alan_adi = alan_adi.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Klasör adı oluştur
    if alan_id:
        folder_name = f"{int(alan_id):02d}_-_{safe_alan_adi}"
    else:
        folder_name = safe_alan_adi
    
    # Dosya adı oluştur
    filename = f"cop_{sinif}_sinif"
    if year and year != "Bilinmiyor":
        filename += f"_{year}"
    filename += ".pdf"
    
    return os.path.join("data", "cop", folder_name, filename)


def validate_pdf_file(file_path: str) -> bool:
    """
    PDF dosyasının geçerliliğini kontrol eder
    
    Args:
        file_path: PDF dosya yolu
    
    Returns:
        True ise geçerli PDF, False ise değil
    """
    if not os.path.exists(file_path):
        return False
    
    if not file_path.lower().endswith('.pdf'):
        return False
    
    try:
        # Dosya boyutunu kontrol et (çok küçük ise bozuk olabilir)
        file_size = os.path.getsize(file_path)
        if file_size < 1024:  # 1KB'den küçük
            return False
        
        # PDF header kontrolü
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF-'):
                return False
        
        return True
        
    except Exception:
        return False


def cleanup_temp_files(temp_dir: str = None) -> int:
    """
    Geçici PDF dosyalarını temizler
    
    Args:
        temp_dir: Temizlenecek dizin (None ise mevcut dizin)
    
    Returns:
        Temizlenen dosya sayısı
    """
    if temp_dir is None:
        temp_dir = "."
    
    if not os.path.exists(temp_dir):
        return 0
    
    cleaned_count = 0
    
    try:
        for filename in os.listdir(temp_dir):
            if filename.startswith('temp_pdf_') and filename.endswith('.pdf'):
                file_path = os.path.join(temp_dir, filename)
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    print(f"🗑️ Temizlendi: {filename}")
                except Exception as e:
                    print(f"⚠️ Temizleme hatası ({filename}): {e}")
        
        if cleaned_count > 0:
            print(f"✅ {cleaned_count} geçici dosya temizlendi")
        
    except Exception as e:
        print(f"❌ Temp dizin temizleme hatası: {e}")
    
    return cleaned_count


def create_cache_structure(base_path: str = "data") -> bool:
    """
    Cache klasör yapısını oluşturur
    
    Args:
        base_path: Ana data klasörü
    
    Returns:
        True ise başarılı, False ise hata
    """
    try:
        cache_dirs = [
            os.path.join(base_path, "cop"),
            os.path.join(base_path, "dbf"), 
            os.path.join(base_path, "dm"),
            os.path.join(base_path, "bom")
        ]
        
        for cache_dir in cache_dirs:
            os.makedirs(cache_dir, exist_ok=True)
            print(f"📁 Oluşturuldu: {cache_dir}")
        
        print("✅ Cache yapısı oluşturuldu")
        return True
        
    except Exception as e:
        print(f"❌ Cache yapısı oluşturma hatası: {e}")
        return False


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