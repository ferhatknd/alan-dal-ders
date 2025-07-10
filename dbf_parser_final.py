import requests
from bs4 import BeautifulSoup
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}
OUTPUT_FILE = "data/dbf_data_final.json"

def parse_dbf_page(sinif_kodu):
    """Belirtilen sınıf koduna ait sayfayı ayrıştırır ve verileri çeker."""
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    page_data = []
    
    try:
        response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # Sayfadaki tüm alan kartlarını doğrudan bul
        alan_columns = soup.find_all('div', class_='col-lg-3')
        
        for column in alan_columns:
            # İki 'a' tag'i var, bilgileri içeren ikincisi.
            # Bu yüzden doğrudan 'ul' etiketini aramak daha güvenli.
            ul_tag = column.find('ul', class_='list-group')
            if not ul_tag:
                continue
            
            # Linki, ul'nin ebeveyni olan 'a' etiketinden al
            link_tag = ul_tag.find_parent('a', href=True)
            if not link_tag or not (link_tag['href'].endswith('.rar') or link_tag['href'].endswith('.zip')):
                continue

            dbf_link = requests.compat.urljoin(response.url, link_tag['href'])
            
            list_items = ul_tag.find_all('li')
            
            alan_adi = ""
            sinif = ""
            tarih = ""

            # Alan adını bul
            b_tag = ul_tag.find('b')
            if b_tag:
                alan_adi = b_tag.get_text(strip=True)

            # Diğer bilgileri ikonlarına göre bul
            for item in list_items:
                icon = item.find('i')
                if not icon:
                    continue
                
                if 'fa-chalkboard-teacher' in icon.get('class', []):
                    sinif = item.get_text(strip=True)
                elif 'fa-calendar' in icon.get('class', []):
                    tarih = item.get_text(strip=True)

            if alan_adi and dbf_link:
                page_data.append({
                    "alan_adi": alan_adi,
                    "sinif": sinif,
                    "link": dbf_link,
                    "guncelleme_tarihi": tarih
                })

    except requests.RequestException as e:
        print(f"Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
    
    return page_data

def main():
    """Tüm sınıflar için verileri çeker ve JSON dosyasına yazar."""
    siniflar = ["9", "10", "11", "12"]
    all_data = []
    
    print("DBF veri çekme işlemi başlatılıyor...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_sinif = {executor.submit(parse_dbf_page, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            sinif = future_to_sinif[future]
            try:
                data = future.result()
                if data:
                    all_data.extend(data)
                    print(f"✅ {sinif}. sınıf için {len(data)} adet DBF bilgisi başarıyla çekildi.")
                else:
                    print(f"⚠️ {sinif}. sınıf için veri bulunamadı.")
            except Exception as exc:
                print(f"❌ {sinif}. sınıf işlenirken bir hata oluştu: {exc}")

    # Veriyi alan adına ve sonra sınıfa göre sırala
    all_data.sort(key=lambda x: (x['alan_adi'], x.get('sinif', '')))

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\nBaşarılı! Toplam {len(all_data)} kayıt {OUTPUT_FILE} dosyasına yazıldı.")
    except IOError as e:
        print(f"\n❌ Hata: Sonuçlar dosyaya yazılamadı: {e}")

    end_time = time.time()
    print(f"İşlem {end_time - start_time:.2f} saniyede tamamlandı.")

if __name__ == "__main__":
    main()
