import requests
import json
import time

# requests.Session() kullanarak çerezleri ve oturum bilgilerini yönetiyoruz
session = requests.Session()

# Ortak HTTP başlıklarını tanımlıyoruz
COMMON_HEADERS = {
    # Tarayıcıdan kopyalanan güncel User-Agent
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    # Curl çıktısındaki gibi Accept-Language
    "Accept-Language": "tr,en;q=0.9", 
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    # Curl çıktısındaki gibi Origin başlığı
    "Origin": "https://mtegm.meb.gov.tr", 
    # Curl çıktısındaki gibi Referer başlığı
    "Referer": "https://mtegm.meb.gov.tr/kurumlar/",
    # Diğer başlıklar (cache-control, pragma, sec-ch-ua vb.) requests kütüphanesi tarafından
    # ya otomatik olarak eklenir ya da bu API için kritik değildir. Sorun devam ederse eklenebilirler.
}

def get_provinces():
    """
    AJAX isteği ile il bilgilerini çeker.
    """
    ajax_url = "https://mtegm.meb.gov.tr/kurumlar/api/getIller.php" 
    
    headers = {
        **COMMON_HEADERS,
        # getIller için Referer ve Origin zaten COMMON_HEADERS'ta tanımlı, tekrar yazmaya gerek yok.
    }

    print(f"[{time.strftime('%H:%M:%S')}] İller AJAX ile çekiliyor...")
    print(f"[{time.strftime('%H:%M:%S')}] Hedef URL: {ajax_url}")

    try:
        # Session kullanılarak GET isteği gönderiliyor
        response = session.get(ajax_url, headers=headers, timeout=15) 
        response.raise_for_status()

        response_text = response.text
        print(f"[{time.strftime('%H:%M:%S')}] getIller.php yanıtının ilk 200 karakteri: \n{response_text[:200]}")

        json_data = response.json()
        
        provinces = {}
        for item in json_data:
            if 'ilid' in item and 'il' in item:
                provinces[item['ilid']] = item['il']
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Uyarı: Beklenmeyen il JSON öğesi yapısı: {item}")
        return provinces
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] İller çekilirken ağ hatası oluştu: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[{time.strftime('%H:%M:%S')}] İller yanıtı JSON olarak çözümlenemedi: {e}.")
        print(f"Hata anındaki yanıtın ilk 200 karakteri: \n{response_text[:200]}")
        return {}
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] İller çekilirken beklenmeyen bir hata oluştu: {e}")
        return {}

def get_areas_for_province(province_id):
    """
    Belirli bir il ID'si için alan bilgilerini AJAX isteği ile çeker.
    Yanıt JSON formatındadır.
    """
    ajax_url = "https://mtegm.meb.gov.tr/kurumlar/api/getAlanlar.php" 
    
    # KESİN DÜZELTME: Curl çıktısındaki gibi 'k_ilid' parametresini kullanıyoruz.
    data = {
        "k_ilid": province_id,
    }
    
    headers = {
        **COMMON_HEADERS,
        # Referer ve Origin zaten COMMON_HEADERS'ta tanımlı.
    }

    print(f"  [{time.strftime('%H:%M:%S')}] İl ID: {province_id} için alanlar çekiliyor...")
    print(f"  [{time.strftime('%H:%M:%S')}] Hedef URL: {ajax_url}, Gönderilen Data: {data}")

    try:
        # Session kullanılarak POST isteği gönderiliyor
        response = session.post(ajax_url, data=data, headers=headers, timeout=15)
        
        response.raise_for_status()

        response_text = response.text
        # JSONDecodeError'ı daha iyi yakalamak için burada response_text'i yine de yazdırıyoruz.
        print(f"  [{time.strftime('%H:%M:%S')}] Alanlar yanıtının ilk 500 karakteri: \n{response_text[:500]}") 

        json_data = response.json()
        
        areas = {}
        for item in json_data:
            if 'alan' in item and 'alan_adi' in item:
                areas[item['alan']] = item['alan_adi']
            else:
                print(f"  [{time.strftime('%H:%M:%S')}] Uyarı: Beklenmeyen alan JSON öğesi yapısı: {item}")
        return areas
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] İl ID: {province_id} için alanlar çekilirken ağ hatası oluştu: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[{time.strftime('%H:%M:%S')}] İl ID: {province_id} için alanlar yanıtı JSON olarak çözümlenemedi: {e}.")
        print(f"Yanıtın tamamı (JSON hatası anında): \n{response_text}") # Hata anında tüm yanıtı göster
        return {}
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] İl ID: {province_id} için alanlar çekilirken beklenmeyen bir hata oluştu: {e}")
        return {}

def get_branches_for_area(province_id, area_value):
    """
    Belirli bir il ve alan seçimine göre dal bilgilerini AJAX isteği ile çeker.
    Yanıt JSON formatındadır.
    """
    ajax_url = "https://mtegm.meb.gov.tr/kurumlar/api/getDallar.php" 
    
    # NOT: getDallar.php için tam curl çıktınız yok. getAlanlar.php'deki "k_ilid" kalıbını ve
    # "alan" parametresini varsayarak devam ediyoruz. Eğer sorun çıkarsa getDallar için de curl almalıyız.
    data = {
        "k_ilid": province_id, # İl ID'sini 'k_ilid' olarak gönderiyoruz (Alanlarda böyleydi)
        "alan": area_value,   # Alan değerini hala 'alan' olarak gönderiyoruz
    }
    
    headers = {
        **COMMON_HEADERS,
        # Referer ve Origin zaten COMMON_HEADERS'ta tanımlı.
    }

    print(f"    [{time.strftime('%H:%M:%S')}] İl ID: {province_id}, Alan: '{area_value}' için dallar çekiliyor...")
    print(f"    [{time.strftime('%H:%M:%S')}] Hedef URL: {ajax_url}, Gönderilen Data: {data}")

    try:
        # Session kullanılarak POST isteği gönderiliyor
        response = session.post(ajax_url, data=data, headers=headers, timeout=15)
        
        response.raise_for_status()
        
        response_text = response.text
        print(f"    [{time.strftime('%H:%M:%S')}] Dallar yanıtının ilk 500 karakteri: \n{response_text[:500]}")

        json_data = response.json()
        
        branches = []
        for item in json_data:
            if 'dal' in item and 'dal_adi' in item:
                branches.append(item['dal_adi'])
            else:
                print(f"    [{time.strftime('%H:%M:%S')}] Uyarı: Beklenmeyen dal JSON öğesi yapısı: {item}")
        return branches
    except requests.exceptions.RequestException as e:
        print(f"    [{time.strftime('%H:%M:%S')}] Hata: İl ID: {province_id}, Alan: '{area_value}' için dallar çekilemedi: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"    [{time.strftime('%H:%M:%S')}] Hata: İl ID: {province_id}, Alan: '{area_value}' için dallar yanıtı JSON olarak çözümlenemedi: {e}.")
        print(f"Yanıtın tamamı (JSON hatası anında): \n{response_text}") # Hata anında tüm yanıtı göster
        return None
    except Exception as e:
        print(f"    [{time.strftime('%H:%M:%S')}] Hata: İl ID: {province_id}, Alan: '{area_value}' için dallar çekilirken beklenmeyen bir hata oluştu: {e}")
        return None

# ... (Diğer tüm fonksiyonlar ve COMMON_HEADERS, session tanımlamaları yukarıdaki kodla aynı kalacak) ...

def main():
    # Bu sözlük, tüm illerdeki benzersiz alan-dal kombinasyonlarını tutacak.
    # Yapısı: {"ALAN_ADI": ["DAL_ADI_1", "DAL_ADI_2", ...]}
    unique_areas_with_branches = {} 

    # ÖNEMLİ: İlk olarak ana sayfaya bir GET isteği göndererek oturum çerezini almalıyız.
    print(f"[{time.strftime('%H:%M:%S')}] Ana sayfa ziyareti yapılıyor (oturum çerezini almak için)...")
    try:
        session.get("https://mtegm.meb.gov.tr/kurumlar/", headers=COMMON_HEADERS, timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] Ana sayfa ziyareti tamamlandı. Oturum çerezleri: {session.cookies.get_dict()}")
    except requests.exceptions.RequestException as e:
        print(f"[{time.strftime('%H:%M:%S')}] HATA: Ana sayfa ziyareti sırasında ağ hatası oluştu: {e}. Çerez alınamadı, program devam edemez.")
        return 

    provinces = get_provinces()

    if not provinces:
        print(f"[{time.strftime('%H:%M:%S')}] HATA: İl bilgileri çekilemedi. Program sonlandırılıyor.")
        return

    print(f"[{time.strftime('%H:%M:%S')}] Toplam {len(provinces)} il bulundu.")

    for province_id, province_name in provinces.items():
        print(f"\n[{time.strftime('%H:%M:%S')}] '{province_name}' ili için alanlar kontrol ediliyor...")
        
        areas = get_areas_for_province(str(province_id)) 

        if not areas:
            print(f"[{time.strftime('%H:%M:%S')}] Uyarı: '{province_name}' ili için alan bilgisi bulunamadı veya çekilemedi. Bu il geçiliyor.")
            continue

        for area_value, area_name in areas.items():
            # Eğer bu alan daha önce işlenmemişse (yani unique_areas_with_branches içinde yoksa)
            if area_name not in unique_areas_with_branches:
                print(f"    [{time.strftime('%H:%M:%S')}] Yeni alan bulundu: '{area_name}'. Dalları çekiliyor...")
                branches = get_branches_for_area(str(province_id), area_value)
                
                if branches is not None:
                    unique_areas_with_branches[area_name] = branches
                else:
                    unique_areas_with_branches[area_name] = [] # Dal çekilemezse boş liste
                
                time.sleep(0.3) # Dalları çektikten sonra küçük bir gecikme
            else:
                print(f"    [{time.strftime('%H:%M:%S')}] Alan '{area_name}' daha önce işlendi, atlanıyor.")
            
        time.sleep(1.5) # Her ilin işlenmesi arasında daha uzun bir gecikme

    output_filename = "getir_dal_sonuc.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(unique_areas_with_branches, f, ensure_ascii=False, indent=4)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] Benzersiz Alan-Dal verileri başarıyla '{output_filename}' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()