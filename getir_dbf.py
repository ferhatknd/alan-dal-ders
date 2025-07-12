import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

def getir_dbf(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için DBF (Ders Bilgi Formu) verilerini eşzamanlı olarak çeker.
    """
    def get_dbf_data_for_class(sinif_kodu):
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        class_dbf_data = {}
        try:
            response = requests.get(BASE_DBF_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            alan_columns = soup.find_all('div', class_='col-lg-3')
            for column in alan_columns:
                ul_tag = column.find('ul', class_='list-group')
                if not ul_tag: continue

                link_tag = ul_tag.find_parent('a', href=True)
                if not link_tag or not (link_tag['href'].endswith('.rar') or link_tag['href'].endswith('.zip')):
                    continue

                dbf_link = requests.compat.urljoin(response.url, link_tag['href'])
                
                alan_adi = ""
                tarih = ""

                b_tag = ul_tag.find('b')
                if b_tag:
                    alan_adi = b_tag.get_text(strip=True)

                for item in ul_tag.find_all('li'):
                    if item.find('i', class_='fa-calendar'):
                        tarih = item.get_text(strip=True)
                        break

                if alan_adi and dbf_link:
                    class_dbf_data[alan_adi] = {
                        "link": dbf_link,
                        "guncelleme_tarihi": tarih
                    }
        except requests.RequestException as e:
            print(f"DBF Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
        return sinif_kodu, class_dbf_data

    all_dbf_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_dbf_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_dbf_data[sinif] = data
            except Exception as exc:
                print(f"DBF verisi işlenirken hata: {exc}")
    return all_dbf_data
