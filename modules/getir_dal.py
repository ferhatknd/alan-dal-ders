import requests
import json
import time
import os
import sqlite3
from pathlib import Path
from .utils import normalize_to_title_case_tr

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


    try:
        # Session kullanılarak GET isteği gönderiliyor
        response = session.get(ajax_url, headers=headers, timeout=15) 
        response.raise_for_status()

        response_text = response.text

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


    try:
        # Session kullanılarak POST isteği gönderiliyor
        response = session.post(ajax_url, data=data, headers=headers, timeout=15)
        
        response.raise_for_status()

        response_text = response.text
        # JSONDecodeError'ı daha iyi yakalamak için response_text'i saklıyoruz.

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


    try:
        # Session kullanılarak POST isteği gönderiliyor
        response = session.post(ajax_url, data=data, headers=headers, timeout=15)
        
        response.raise_for_status()
        
        response_text = response.text

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

def find_or_create_database():
    """
    Veritabanı dosyasını bulur veya oluşturur.
    """
    db_path = "data/temel_plan.db"
    if os.path.exists(db_path):
        return db_path
    
    # data klasörü yoksa oluştur
    os.makedirs("data", exist_ok=True)
    
    # Şema dosyasından veritabanını oluştur
    schema_path = "data/schema.sql"
    if os.path.exists(schema_path):
        with sqlite3.connect(db_path) as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
        print(f"Veritabanı şemadan oluşturuldu: {db_path}")
    
    return db_path

def save_area_and_branches_to_db(area_name, branches, db_path):
    """
    Bir alanı ve dallarını veritabanına kaydeder.
    """
    try:
        # Alan adını normalize et
        normalized_area_name = normalize_to_title_case_tr(area_name)
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Alan adına göre alan varsa ID'sini al
            cursor.execute(
                "SELECT id FROM temel_plan_alan WHERE alan_adi = ?",
                (normalized_area_name,)
            )
            result = cursor.fetchone()
            
            if result:
                area_id = result[0]
            else:
                cursor.execute(
                    "INSERT INTO temel_plan_alan (alan_adi) VALUES (?)",
                    (normalized_area_name,)
                )
                area_id = cursor.lastrowid
            
            # Dalları ekle (yineleme kontrolü ile)
            for branch_name in branches:
                if branch_name.strip():  # Boş dal adlarını atla
                    cursor.execute(
                        "SELECT id FROM temel_plan_dal WHERE dal_adi = ? AND alan_id = ?",
                        (branch_name, area_id)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO temel_plan_dal (dal_adi, alan_id) VALUES (?, ?)",
                            (branch_name, area_id)
                        )
            
            conn.commit()
            return area_id
            
    except Exception as e:
        print(f"Veritabanı kayıt hatası ({area_name}): {e}")
        return None

def create_area_directory_structure(area_name):
    """
    Alan için klasör yapısını oluşturur: data/alan/{alan_adi}/
    """
    # Alan adını dosya sistemi için güvenli hale getir
    safe_area_name = area_name.replace('/', '_').replace('\\', '_').replace(':', '_')
    area_dir = Path(f"data/alan/{safe_area_name}")
    
    # Alt klasörleri oluştur
    subdirs = ['dallar', 'cop', 'dbf', 'dm', 'bom']
    for subdir in subdirs:
        (area_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    return area_dir

def save_branches_to_file(area_name, branches, area_dir):
    """
    Dalları JSON dosyasına kaydeder.
    """
    branches_file = area_dir / 'dallar' / 'dallar.json'
    branch_data = {
        'alan_adi': area_name,
        'dallar': branches,
        'toplam_dal_sayisi': len(branches),
        'olusturma_tarihi': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(branches_file, 'w', encoding='utf-8') as f:
        json.dump(branch_data, f, ensure_ascii=False, indent=2)
    

def getir_dal_with_db_integration():
    """
    Ana dal getirme fonksiyonu - veritabanı entegrasyonu ile.
    Generator olarak her adımda ilerleme mesajı döndürür.
    """
    yield {'type': 'status', 'message': 'Veritabanı bağlantısı kontrol ediliyor...'}
    
    db_path = find_or_create_database()
    if not db_path:
        yield {'type': 'error', 'message': 'Veritabanı oluşturulamadı!'}
        return
    
    # Ana dizin yapısını oluştur
    os.makedirs('data/alanlar', exist_ok=True)
    
    # Bu sözlük, tüm illerdeki benzersiz alan-dal kombinasyonlarını tutacak.
    unique_areas_with_branches = {}
    total_areas_found = 0
    total_branches_found = 0
    
    yield {'type': 'status', 'message': 'Ana sayfa ziyareti yapılıyor (oturum çerezini almak için)...'}
    
    try:
        session.get("https://mtegm.meb.gov.tr/kurumlar/", headers=COMMON_HEADERS, timeout=10)
    except requests.exceptions.RequestException as e:
        yield {'type': 'error', 'message': f'Ana sayfa ziyaretinde hata: {e}'}
        return
    
    provinces = get_provinces()
    
    if not provinces:
        yield {'type': 'error', 'message': 'İl bilgileri çekilemedi!'}
        return
    
    yield {'type': 'status', 'message': f'Toplam {len(provinces)} il bulundu. Alan-dal taraması başlıyor...\n'}
    
    total_provinces = len(provinces)
    processed_provinces = 0
    
    for province_id, province_name in provinces.items():
        processed_provinces += 1
        new_areas_in_province = 0
        new_branches_in_province = 0
        
        # İl başlangıç mesajı
        yield {
            'type': 'province_start',
            'province_name': province_name.upper(),
            'province_progress': f"({processed_provinces}/{total_provinces})"
        }
        
        areas = get_areas_for_province(str(province_id))
        
        if not areas:
            # Alan bulunamasa bile ilerleme logunu göster
            yield {
                'type': 'progress',
                'province_name': province_name.upper(),
                'province_progress': f"({processed_provinces}/{total_provinces})",
                'new_areas': 0,
                'total_areas': total_areas_found,
                'new_branches': 0,
                'total_branches': total_branches_found
            }
            time.sleep(1.5) # Sunucuyu yormamak için bekleme
            continue # Sonraki ile geç
        
        total_areas_in_province = len(areas)
        processed_areas_in_province = 0
        
        for area_value, area_name in areas.items():
            processed_areas_in_province += 1
            
            # Alan işleme mesajı
            yield {
                'type': 'area_processing',
                'area_name': area_name,
                'area_progress': f"({processed_areas_in_province}/{total_areas_in_province})"
            }
            
            if area_name not in unique_areas_with_branches:
                branches = get_branches_for_area(str(province_id), area_value)
                
                if branches is not None:
                    unique_areas_with_branches[area_name] = branches
                    new_areas_in_province += 1
                    new_branches_in_province += len(branches)
                    
                    # Dal işleme mesajı
                    yield {
                        'type': 'branches_processing',
                        'branches_count': len(branches),
                        'total_branches': new_branches_in_province
                    }
                    
                    # Veritabanına kaydet
                    area_id = save_area_and_branches_to_db(area_name, branches, db_path)
                    
                    if area_id:
                        area_dir = create_area_directory_structure(area_name)
                        save_branches_to_file(area_name, branches, area_dir)
                    else:
                        yield {'type': 'warning', 'message': f"Alan '{area_name}' veritabanına kaydedilemedi"}
                else:
                    unique_areas_with_branches[area_name] = []
                    yield {'type': 'warning', 'message': f"Alan '{area_name}' için dal bilgisi çekilemedi"}
                
                time.sleep(0.3)
        
        total_areas_found += new_areas_in_province
        total_branches_found += new_branches_in_province

        yield {
            'type': 'progress',
            'province_name': province_name.upper(),
            'province_progress': f"({processed_provinces}/{total_provinces})",
            'new_areas': new_areas_in_province,
            'total_areas': total_areas_found,
            'new_branches': new_branches_in_province,
            'total_branches': total_branches_found
        }

        time.sleep(1.5)  # Her ilin işlenmesi arasında daha uzun bir gecikme
    
    # Sonuç özeti
    
    yield {
        'type': 'success', 
        'message': f'\nAdım 1 tamamlandı! {total_areas_found} alan, {total_branches_found} dal işlendi.'
    }
    
    # Son durum için JSON dosyası da oluştur (yedek)
    output_filename = "data/getir_dal_sonuc.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(unique_areas_with_branches, f, ensure_ascii=False, indent=4)
    
    yield {'type': 'done', 'message': f'Tüm veriler veritabanına kaydedildi. Yedek dosya: {output_filename}'}

def main():
    """
    Ana fonksiyon - komut satırından çalıştırıldığında kullanılır.
    """
    print("Adım 1: Alan-Dal Verilerini Getirme ve Kaydetme")
    print("Veritabanı entegrasyonu ile alan-dal verileri çekiliyor...")
    
    for message in getir_dal_with_db_integration():
        if message['type'] == 'error':
            print(f"❌ HATA: {message['message']}")
            return
        elif message['type'] == 'warning':
            # İlerleme logunu bozmamak için uyarıları daha az belirgin yapabiliriz
            print(f"  -> UYARI: {message['message']}")
        elif message['type'] == 'success':
            print(f"✅ {message['message']}")
        elif message['type'] == 'done':
            print(f"🎉 {message['message']}")
            break
        elif message['type'] == 'province_start':
            print(f"\n🏛️  İl: {message['province_name']} {message['province_progress']}")
        elif message['type'] == 'area_processing':
            print(f"  📋 Alan: {message['area_name']} {message['area_progress']}")
        elif message['type'] == 'branches_processing':
            print(f"    🌿 {message['branches_count']} dal bulundu (Toplam: {message['total_branches']})")
        elif message['type'] == 'progress':
            print(f"✅ {message['province_name']} tamamlandı!")
            print(f"   Yeni Alan: {message['new_areas']} (Toplam: {message['total_areas']})")
            print(f"   Yeni Dal: {message['new_branches']} (Toplam: {message['total_branches']})\n")
        else:
            print(f"ℹ️  {message['message']}")

if __name__ == "__main__":
    main()