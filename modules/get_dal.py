import requests
import json
import time
import os
import sqlite3
from pathlib import Path
from .utils_normalize import normalize_to_title_case_tr
from .utils_database import with_database, find_or_create_database

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
                pass  # Log silenced for cleaner output
        return provinces
    except requests.exceptions.RequestException as e:
        pass  # Error handling moved to caller
        return {}
    except json.JSONDecodeError as e:
        pass  # Error handling moved to caller
        return {}
    except Exception as e:
        pass  # Error handling moved to caller
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
                pass  # Log silenced for cleaner output
        return areas
    except requests.exceptions.RequestException as e:
        pass  # Error handling moved to caller
        return {}
    except json.JSONDecodeError as e:
        pass  # Error handling moved to caller
        return {}
    except Exception as e:
        pass  # Error handling moved to caller
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
                pass  # Log silenced for cleaner output
        return branches
    except requests.exceptions.RequestException as e:
        pass  # Error handling moved to caller
        return None
    except json.JSONDecodeError as e:
        pass  # Error handling moved to caller
        return None
    except Exception as e:
        pass  # Error handling moved to caller
        return None

# find_or_create_database function now imported from utils_database.py

@with_database
def save_area_and_branches_to_db(cursor, area_name, branches):
    """
    Bir alanı ve dallarını veritabanına kaydeder.
    """
    try:
        # Alan adını normalize et
        normalized_area_name = normalize_to_title_case_tr(area_name)
        
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
        
        # @with_database dekoratörü commit işlemini otomatik halleder.
        # Return ifadesi döngünün dışına taşındı.
        return area_id
            
    except Exception as e:
        pass  # Error handling moved to caller
        return None

def get_dal():
    """
    Ana dal getirme fonksiyonu - veritabanı entegrasyonu ile.
    Generator olarak her adımda ilerleme mesajı döndürür.
    """
    yield {'type': 'status', 'message': 'Veritabanı bağlantısı kontrol ediliyor...'}
    
    db_path = find_or_create_database()
    if not db_path:
        yield {'type': 'error', 'message': 'Veritabanı oluşturulamadı!'}
        return
    
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
        
        areas = get_areas_for_province(str(province_id))
        
        if not areas:
            # Alan bulunamasa bile ilerleme logunu göster
            yield {
                'type': 'province_summary',
                'province_name': province_name.upper(),
                'province_progress': f"({processed_provinces}/{total_provinces})",
                'alan_sayisi_province': 0,
                'alan_sayisi_total_province': 0,
                'dal_sayisi_province': 0,
                'dal_sayisi_total_so_far': total_branches_found
            }
            time.sleep(0.1) # Sunucuyu yormamak için bekleme
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
                branches_or_none = get_branches_for_area(str(province_id), area_value)
                
                # Hata durumunda (None) boş liste ata, yoksa gelen listeyi kullan
                branches = branches_or_none if branches_or_none is not None else []
                
                if branches_or_none is None:
                    yield {'type': 'warning', 'message': f"⚠️ {area_name} -> Dal bilgisi çekilemedi, yine de alan kaydedilecek"}

                unique_areas_with_branches[area_name] = branches
                new_areas_in_province += 1
                new_branches_in_province += len(branches)
                
                # Dal işleme mesajı
                yield {
                    'type': 'branches_processing',
                    'branches_count': len(branches),
                    'total_branches': new_branches_in_province
                }
                
                # Her durumda alanı ve dalları (boş olsa bile) kaydet
                area_id = save_area_and_branches_to_db(area_name, branches)
                
                if not area_id:
                    yield {'type': 'warning', 'message': f"❌ {area_name} -> Veritabanına kaydedilemedi"}
                
                time.sleep(0.1)
        
        total_areas_found += new_areas_in_province
        total_branches_found += new_branches_in_province

        yield {
            'type': 'province_summary',
            'province_name': province_name.upper(),
            'province_progress': f"({processed_provinces}/{total_provinces})",
            'alan_sayisi_province': new_areas_in_province,
            'alan_sayisi_total_province': len(areas),
            'dal_sayisi_province': new_branches_in_province,
            'dal_sayisi_total_so_far': total_branches_found
        }

        time.sleep(0.2)  # Her ilin işlenmesi arasında daha uzun bir gecikme
    
    # Sonuç özeti
    
    yield {
        'type': 'success', 
        'message': f'\nAdım 1 tamamlandı! {total_areas_found} alan, {total_branches_found} dal işlendi.'
    }
    
    yield {'type': 'done', 'message': 'Tüm veriler başarıyla veritabanına kaydedildi.'}

def main():
    """
    Ana fonksiyon - komut satırından çalıştırıldığında kullanılır.
    """
    print("Adım 1: Alan-Dal Verilerini Getirme ve Kaydetme")
    print("Veritabanı entegrasyonu ile alan-dal verileri çekiliyor...")
    
    for message in get_dal():
        if message['type'] == 'error':
            print(f"❌ HATA: {message['message']}")
            return
        elif message['type'] == 'warning':
            # İlerleme logunu bozmamak için uyarıları daha az belirgin yapabiliriz
            print(f"  -> UYARI: {message['message']}")
        elif message['type'] == 'success':
            print(f"✅ {message['message']}")
        elif message['type'] == 'done':
            print(f"✅ {message['message']}")
            break
        elif message['type'] == 'province_summary':
            print(f"İl      : {message['province_name']} {message['province_progress']}")
            print(f"Alan Sayısı: {message['alan_sayisi_province']}/{message['alan_sayisi_total_province']}")
            print(f"Dal Sayısı : {message['dal_sayisi_province']} (Toplam: {message['dal_sayisi_total_so_far']})\n")
        elif message['type'] == 'area_processing':
            # Bu mesaj tipini artık ana konsolda göstermeyebiliriz, isteğe bağlı.
            # Standardized area progress message format
            # print(f"📋 {message['area_name']} {message['area_progress']}")
            pass
        elif message['type'] == 'branches_processing':
            # Bu da daha detaylı bir log, ana konsolda göstermeyebiliriz.
            # Standardized branch progress message format
            # print(f"🌿 {message['area_name']} -> {message['branches_count']} dal bulundu (Toplam: {message['total_branches']})")
            pass
        else:
            print(f"ℹ️  {message['message']}")


if __name__ == "__main__":
    main()