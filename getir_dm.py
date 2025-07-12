import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

def get_alanlar(sinif_kodu="9"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    try:
        resp = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return []

    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec")
    if not sel:
        return []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value','').strip()
        name = opt.text.strip()
        if val and val not in ("00","0"):
            alanlar.append({"id": val, "isim": name})
    return alanlar

def get_dersler_for_alan(alan_id, alan_adi, sinif_kodu="9"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1", "alan_id": alan_id}
    try:
        resp = requests.get(BASE_DERS_ALT_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return []

    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    dersler = []
    for div in soup.find_all('div', class_='p-0 bg-light'):
        a = div.find('a', href=True)
        if not a: continue
        ul = a.find('ul', class_='list-group')
        if not ul: continue

        items = ul.find_all('li')
        ders_adi = items[0].get_text(" ", strip=True)
        sinif_text = ""
        for li in items:
            text = li.get_text(" ", strip=True)
            if "Sınıf" in text and any(char.isdigit() for char in text):
                sinif_text = text
                break
        link = requests.compat.urljoin(resp.url, a['href'].strip())

        dersler.append({"isim": ders_adi,
                        "sinif": sinif_text,
                        "link": link})
    return dersler

def getir_dm(siniflar=["9", "10", "11", "12"]):
    """
    Tüm sınıflar ve alanlar için Ders Materyali (PDF) verilerini çeker.
    """
    all_dm_data = {}
    for sinif in siniflar:
        alanlar = get_alanlar(sinif)
        sinif_dm = {}
        for alan in alanlar:
            dersler = get_dersler_for_alan(alan["id"], alan["isim"], sinif)
            sinif_dm[alan["isim"]] = dersler
        all_dm_data[sinif] = sinif_dm
    return all_dm_data
