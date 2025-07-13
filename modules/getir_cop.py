import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

def getir_cop(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar için Çerçeve Öğretim Programı (ÇÖP) verilerini eşzamanlı olarak çeker.
    """
    def get_cop_data_for_class(sinif_kodu):
        params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
        class_cop_data = {}
        try:
            response = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            alan_columns = soup.find_all('div', class_='col-lg-3')
            for column in alan_columns:
                link_tag = column.find('a', href=True)
                if not link_tag or not link_tag['href'].endswith('.pdf') or 'upload/cop' not in link_tag['href']:
                    continue

                cop_link = requests.compat.urljoin(response.url, link_tag['href'])
                
                # COP yapısı farklı - img tagının alt attribute'ından alan adını al
                img_tag = link_tag.find('img', alt=True)
                if not img_tag:
                    continue

                alan_adi = img_tag.get('alt', '').strip()
                
                # Güncelleme yılını ribbon'dan al
                guncelleme_yili = ""
                ribbon = column.find('div', class_='ribbon')
                if ribbon:
                    span_tag = ribbon.find('span')
                    if span_tag:
                        guncelleme_yili = span_tag.get_text(strip=True)

                if alan_adi and cop_link:
                    class_cop_data[alan_adi] = {
                        "link": cop_link,
                        "guncelleme_yili": guncelleme_yili
                    }
        except requests.RequestException as e:
            print(f"ÇÖP Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}")
        return sinif_kodu, class_cop_data

    all_cop_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_cop_data[sinif] = data
            except Exception as exc:
                print(f"ÇÖP verisi işlenirken hata: {exc}")
    return all_cop_data
