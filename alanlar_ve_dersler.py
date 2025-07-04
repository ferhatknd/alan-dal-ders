import requests
from bs4 import BeautifulSoup
import sys

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"

def get_alanlar(sinif_kodu="9", kurum_id="1"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": kurum_id}
    resp = requests.get(BASE_OPTIONS_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec") or []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value', '').strip()
        name = opt.text.strip()
        if val:
            alanlar.append({"id": val, "isim": name})
    return alanlar

def get_dersler_for_alan(alan_id, alan_adi, sinif_kodu="9", kurum_id="1"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": kurum_id, "alan_id": alan_id}
    resp = requests.get(BASE_DERS_ALT_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    dersler = []
    for div in soup.find_all('div', class_='p-0 bg-light'):
        ul = div.find('ul', class_='list-group')
        if not ul: continue
        items = ul.find_all('li')
        if not items: continue
        ders = items[0].get_text(" ", strip=True)
        sinif = next((li.get_text(" ",strip=True) for li in items if "Sınıf" in li.get_text()), "")
        if ders:
            dersler.append((ders, sinif))
    if not dersler:
        print(f"⚠️ Ders bulunamadı: {alan_adi} ({alan_id})", file=sys.stderr)
    return dersler

def main():
    siniflar = ["9", "10", "11", "12"]
    tum_veri = {}  # {ders_adi: {"siniflar": set(), "alanlar": set()}}

    alan_map = {}  # alan_id -> alan_adi (for reverse lookup)

    for sinif in siniflar:
        alanlar = get_alanlar(sinif_kodu=sinif)
        for alan in alanlar:
            alan_map[alan["id"]] = alan["isim"]
            dersler = get_dersler_for_alan(alan["id"], alan["isim"], sinif_kodu=sinif)
            for ders, sinif_bilgi in dersler:
                record = tum_veri.setdefault(ders, {"siniflar": set(), "alanlar": set()})
                record["siniflar"].add(sinif_bilgi)
                record["alanlar"].add(alan["id"])

    print("\n===== Dersler Listesi =====")
    for ders in sorted(tum_veri.keys()):
        siniflar = sorted(tum_veri[ders]["siniflar"])
        alanlar = sorted(tum_veri[ders]["alanlar"])
        sinif_str = ",".join(siniflar)
        ortak_str = ""
        if len(alanlar) > 1:
            ortak_str = f" ortak:{','.join(alanlar)}"
        print(f"- {ders} ({sinif_str}){ortak_str}")

    print("\n==== Özet ====")
    print(f"Toplam Benzersiz Ders: {len(tum_veri)}")