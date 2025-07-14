"""
MEB ÇÖP (Çerçeve Öğretim Programı) Veri Çekme Modülü

Bu modül MEB sitesinden HTML parsing yaparak ÇÖP linklerini çeker ve
PDF dosyalarını merkezi cache sistemine indirir.

Sorumluluklar:
- HTML scraping ve alan listesi çıkarma
- PDF URL'lerini bulma ve organize etme  
- utils.py üzerinden merkezi indirme
- Sınıf bazlı paralel istek yönetimi
- Cache kontrolü ve metadata yönetimi
"""

import requests
import os
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
from .utils import download_and_cache_pdf, normalize_to_title_case_tr


def get_cop_data_for_class(sinif_kodu: str) -> Tuple[str, Dict[str, Dict[str, str]]]:
    """
    Belirli bir sınıf için ÇÖP verilerini çek
    
    Args:
        sinif_kodu: Sınıf kodu (9, 10, 11, 12)
    
    Returns:
        Tuple[sinif_kodu, alan_dict]: (sınıf, {alan_adi: {link, guncelleme_yili}})
    """
    try:
        url = "https://meslek.meb.gov.tr/cercevelistele.aspx"
        params = {
            'sinif_kodu': sinif_kodu,
            'kurum_id': '1'
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        alanlar = {}
        
        # Alan kartlarını bul
        alan_columns = soup.find_all('div', class_='col-lg-3')
        
        for column in alan_columns:
            try:
                # Link ve alan bilgisini çıkar
                link_tag = column.find('a', href=True)
                if not link_tag:
                    continue
                
                # Alan adını img alt attribute'ından al
                img_tag = link_tag.find('img', alt=True)
                if not img_tag:
                    continue
                
                alan_adi = img_tag.get('alt', '').strip()
                if not alan_adi:
                    continue

                # Hatalı "alan adı" olarak algılanan metinleri filtrele
                invalid_keywords = [
                    "ÇERÇEVE ÖĞRETİM PROGRAMI",
                    "ÖĞRETİM PROGRAMININ AMAÇLARI",
                    "LOGO",
                    "MEB"
                ]
                # Çok uzun veya anlamsız metinleri de filtrele (örn: ... içerenler)
                if any(keyword in alan_adi.upper() for keyword in invalid_keywords) or "..." in alan_adi or len(alan_adi) > 100:
                    continue # Bu geçerli bir alan adı değil, atla.

                
                # ÇÖP PDF linkini al
                href = link_tag.get('href', '').strip()
                if not href.endswith('.pdf') or 'upload/cop' not in href:
                    continue
                
                full_link = requests.compat.urljoin(response.url, href)
                
                # Güncelleme yılını ribbon'dan al
                guncelleme_yili = None
                ribbon = column.find('div', class_='ribbon')
                if ribbon:
                    span_tag = ribbon.find('span')
                    if span_tag:
                        guncelleme_yili = span_tag.get_text(strip=True)
                
                alanlar[alan_adi] = {
                    'link': full_link,
                    'guncelleme_yili': guncelleme_yili or 'Bilinmiyor'
                }
                
            except Exception as e:
                print(f"Alan işleme hatası (sınıf {sinif_kodu}): {e}")
                continue
        
        return sinif_kodu, alanlar
        
    except Exception as e:
        print(f"ÇÖP çekme hatası (sınıf {sinif_kodu}): {e}")
        return sinif_kodu, {}


def getir_cop_links(siniflar: List[str] = ["9", "10", "11", "12"]) -> Dict[str, Any]:
    """
    MEB sitesinden ÇÖP (Çerçeve Öğretim Programı) linklerini çeker.
    
    Args:
        siniflar: Çekilecek sınıf seviyeleri (default: ["9", "10", "11", "12"])
    
    Returns:
        dict: {
            "cop_data": {sınıf: {alan_adi: {link, guncelleme_yili}}},
            "alan_ids": {sınıf: [{id, isim}]}
        }
    """
    cop_data = {}
    alan_ids_data = {}
    
    # Paralel olarak tüm sınıfları işle
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        
        for future in as_completed(futures):
            sinif_kodu, alanlar = future.result()
            
            if alanlar:
                cop_data[sinif_kodu] = alanlar
                
                # Alan ID'leri için basit indexing
                alan_ids_data[sinif_kodu] = [
                    {"id": str(i+1), "isim": alan_adi} 
                    for i, alan_adi in enumerate(alanlar.keys())
                ]
                
                print(f"✅ Sınıf {sinif_kodu}: {len(alanlar)} alan bulundu")
            else:
                print(f"❌ Sınıf {sinif_kodu}: Veri bulunamadı")
    
    return {
        "cop_data": cop_data,
        "alan_ids": alan_ids_data
    }


def download_cop_pdfs(alan_list: List[Dict[str, str]], cache: bool = True, alan_id_mapping: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    ÇÖP PDF'lerini utils.py üzerinden merkezi cache sistemine indirir.
    
    Args:
        alan_list: [{"alan_adi": "...", "link": "...", "sinif": "...", "year": "..."}] formatında alan listesi
        cache: True ise kalıcı cache, False ise geçici indirme
        alan_id_mapping: {"alan_adi": "id"} formatında ID mapping'i (opsiyonel)
    
    Returns:
        Dict[str, str]: {"alan_adi_sinif": "indirilen_dosya_yolu"} formatında sonuç
    """
    if not alan_list:
        return {}
    
    downloaded_files = {}
    
    for alan_info in alan_list:
        alan_adi = alan_info.get("alan_adi", "")
        pdf_url = alan_info.get("link", "")
        sinif = alan_info.get("sinif", "")
        year = alan_info.get("year", "")
        
        if not alan_adi or not pdf_url:
            continue
        
        try:
            # Ek bilgi oluştur (sınıf ve yıl)
            additional_info = f"{sinif}_sinif"
            if year and year != "Bilinmiyor":
                additional_info += f"_{year}"
            
            # Alan ID'si varsa kullan
            alan_id = alan_id_mapping.get(alan_adi) if alan_id_mapping else None
            
            if cache:
                # Kalıcı cache
                file_path = download_and_cache_pdf(
                    url=pdf_url,
                    cache_type="cop",
                    alan_adi=alan_adi,
                    additional_info=additional_info,
                    alan_id=alan_id
                )
            else:
                # Geçici indirme
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()
                    tmp_file.write(response.content)
                    file_path = tmp_file.name
            
            if file_path:
                key = f"{alan_adi}_{sinif}"
                downloaded_files[key] = file_path
                print(f"✅ İndirildi: {alan_adi} ({sinif}. sınıf)")
            else:
                print(f"❌ İndirme başarısız: {alan_adi} ({sinif}. sınıf)")
                
        except Exception as e:
            print(f"❌ İndirme hatası ({alan_adi}): {e}")
    
    return downloaded_files


def get_cop_metadata(save_to_file: bool = True) -> Dict[str, Any]:
    """
    ÇÖP verilerinin metadata'sını toplar ve opsiyonel olarak dosyaya kaydeder.
    
    Args:
        save_to_file: True ise metadata'yı JSON dosyasına kaydet
    
    Returns:
        Dict: ÇÖP metadata'sı
    """
    print("📊 ÇÖP metadata'sı toplanıyor...")
    
    # Tüm sınıflar için veri çek
    cop_data = getir_cop_links()
    
    # İstatistikler
    total_areas = 0
    total_files = 0
    sinif_stats = {}
    
    for sinif, alanlar in cop_data["cop_data"].items():
        alan_count = len(alanlar)
        total_areas += alan_count
        total_files += alan_count  # Her alan için bir PDF
        
        sinif_stats[sinif] = {
            "alan_sayisi": alan_count,
            "alanlar": list(alanlar.keys())
        }
    
    metadata = {
        "toplam_alan_sayisi": total_areas,
        "toplam_pdf_sayisi": total_files,
        "sinif_istatistikleri": sinif_stats,
        "cop_verileri": cop_data["cop_data"],
        "alan_ids": cop_data["alan_ids"],
        "olusturma_tarihi": __import__('datetime').datetime.now().isoformat()
    }
    
    if save_to_file:
        os.makedirs("data/cop", exist_ok=True)
        metadata_file = "data/cop/cop_metadata.json"
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Metadata kaydedildi: {metadata_file}")
    
    print(f"📈 Toplam {total_areas} alan, {total_files} PDF bulundu")
    return metadata


def validate_cop_links(cop_data: Dict[str, Dict[str, Dict[str, str]]]) -> Dict[str, List[str]]:
    """
    ÇÖP linklerinin geçerliliğini kontrol eder.
    
    Args:
        cop_data: getir_cop_links()'den dönen cop_data kısmı
    
    Returns:
        Dict: {"gecerli": [...], "gecersiz": [...], "errors": [...]}
    """
    gecerli_linkler = []
    gecersiz_linkler = []
    hatalar = []
    
    print("🔍 ÇÖP linkleri doğrulanıyor...")
    
    for sinif, alanlar in cop_data.items():
        for alan_adi, alan_info in alanlar.items():
            pdf_url = alan_info.get("link", "")
            
            if not pdf_url:
                gecersiz_linkler.append(f"{alan_adi} ({sinif}): URL boş")
                continue
            
            try:
                # HEAD request ile dosya varlığını kontrol et
                response = requests.head(pdf_url, timeout=10)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'pdf' in content_type.lower():
                        gecerli_linkler.append(f"{alan_adi} ({sinif})")
                    else:
                        gecersiz_linkler.append(f"{alan_adi} ({sinif}): PDF değil ({content_type})")
                else:
                    gecersiz_linkler.append(f"{alan_adi} ({sinif}): HTTP {response.status_code}")
                    
            except Exception as e:
                hatalar.append(f"{alan_adi} ({sinif}): {str(e)}")
    
    result = {
        "gecerli": gecerli_linkler,
        "gecersiz": gecersiz_linkler,
        "errors": hatalar
    }
    
    print(f"✅ Geçerli: {len(gecerli_linkler)}")
    print(f"❌ Geçersiz: {len(gecersiz_linkler)}")
    print(f"⚠️ Hata: {len(hatalar)}")
    
    return result


# Geriye uyumluluk için eski fonksiyon adı
def getir_cop(siniflar: List[str] = ["9", "10", "11", "12"]) -> Dict[str, Any]:
    """
    Geriye uyumluluk wrapper'ı - getir_cop_links() fonksiyonunu çağırır.
    
    DEPRECATED: Bunun yerine getir_cop_links() kullanın.
    """
    import warnings
    warnings.warn(
        "getir_cop() fonksiyonu deprecated. getir_cop_links() kullanın.",
        DeprecationWarning,
        stacklevel=2
    )
    return getir_cop_links(siniflar)


if __name__ == "__main__":
    # Test amaçlı çalıştırma
    print("🚀 ÇÖP veri çekme testi başlatılıyor...")
    
    # Sadece 9. sınıf test et
    cop_data = getir_cop_links(["9"])
    
    if cop_data["cop_data"]:
        print("\n📋 Bulunan alanlar:")
        for sinif, alanlar in cop_data["cop_data"].items():
            print(f"\n{sinif}. Sınıf ({len(alanlar)} alan):")
            for alan_adi, info in alanlar.items():
                print(f"  - {alan_adi} [{info['guncelleme_yili']}]")
        
        # İlk 2 alanı test indirme
        first_areas = list(cop_data["cop_data"]["9"].items())[:2]
        test_list = []
        
        for alan_adi, info in first_areas:
            test_list.append({
                "alan_adi": alan_adi,
                "link": info["link"],
                "sinif": "9",
                "year": info["guncelleme_yili"]
            })
        
        print(f"\n⬇️ Test indirme ({len(test_list)} alan)...")
        downloaded = download_cop_pdfs(test_list, cache=True)
        
        print(f"\n✅ {len(downloaded)} dosya indirildi")
        for key, path in downloaded.items():
            print(f"  - {key}: {path}")
    else:
        print("❌ Hiç veri bulunamadı")