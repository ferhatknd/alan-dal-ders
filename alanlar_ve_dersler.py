import requests
from bs4 import BeautifulSoup
import sys

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"

def get_alanlar(sinif_kodu="9", kurum_id="1"):
    """Tüm alanları (alan_id ve isim) çeker."""
    params = {"sinif_kodu": sinif_kodu, "kurum_id": kurum_id}
    resp = requests.get(BASE_OPTIONS_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec")
    alanlar = []
    if not sel:
        print("Alanlar dropdown'u bulunamadı!", file=sys.stderr)
        return alanlar

    for opt in sel.find_all('option'):
        val = opt.get('value', '').strip()
        name = opt.text.strip()
        if val:
            alanlar.append({"id": val, "isim": name})
    return alanlar

def get_dersler_for_alan(alan_id, sinif_kodu="9", kurum_id="1"):
    """dmgoster.aspx sayfasından dersleri çeker."""
    params = {"sinif_kodu": sinif_kodu, "kurum_id": kurum_id, "alan_id": alan_id}
    resp = requests.get(BASE_DERS_ALT_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    dersler = []
    for div in soup.find_all('div', class_='p-0 bg-light'):
        ul = div.find('ul', class_='list-group')
        if not ul:
            continue
        li0 = ul.find('li')
        if not li0:
            continue
        ders_adi = li0.get_text(" ", strip=True)
        if ders_adi and ders_adi not in dersler:
            dersler.append(ders_adi)

    if not dersler:
        print(f"Alan ID {alan_id} için dersler bulunamadı!", file=sys.stderr)
    return dersler

def main():
    alanlar = get_alanlar()
    alan_to_ders = {}
    ders_to_alan = {}

    for alan in alanlar:
        dersler = get_dersler_for_alan(alan["id"])
        alan_to_ders[alan["isim"]] = dersler
        for d in dersler:
            ders_to_alan.setdefault(d, set()).add(alan["isim"])

    print("== Alan → Dersler ==")
    for a, dersler in alan_to_ders.items():
        print(f"\n📘 {a} ({len(dersler)} ders):")
        for d in dersler:
            print(f"  - {d}")

    print("\n== Ders → Alan(lar) ==")
    for d, alan_set in ders_to_alan.items():
        print(f"\n📗 {d} ({len(alan_set)} alan):")
        for a in alan_set:
            print(f"  - {a}")

if __name__ == "__main__":
    main()