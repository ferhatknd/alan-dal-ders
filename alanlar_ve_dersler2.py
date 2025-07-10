print("✅ Bu script çalışıyor")

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
    if not sel:
        print(f"⚠️ Alan listesi bulunamadı (sınıf: {sinif_kodu})")
        return []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value', '').strip()
        name = opt.text.strip()
        if val and val != "00":
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
    print("Script başladı...")
    siniflar = ["9", "10", "11", "12"]
    tum_veri = {}  # {alan_id: {"isim": str, "dersler": {ders_adi: {"siniflar": set(), "alanlar": set()}}}}

    for sinif in siniflar:
        print(f"{sinif}. sınıf alanları çekiliyor...")
        alanlar = get_alanlar(sinif_kodu=sinif)
        for alan in alanlar:
            alan_id = alan["id"]
            if alan_id == "00":
                continue
            alan_adi = alan["isim"]
            dersler = get_dersler_for_alan(alan_id, alan_adi, sinif_kodu=sinif)
            alan_entry = tum_veri.setdefault(alan_id, {"isim": alan_adi, "dersler": {}})
            for ders, sinif_bilgi in dersler:
                ders_entry = alan_entry["dersler"].setdefault(ders, {"siniflar": set(), "alanlar": set()})
                ders_entry["siniflar"].add(sinif_bilgi)
                ders_entry["alanlar"].add(alan_id)

    print("\n===== Alanlara Göre Dersler Listesi =====")
    for alan_id, data in sorted(tum_veri.items(), key=lambda x: x[1]["isim"]):
        print(f"\n{data['isim']} Alanı")
        for ders, info in sorted(data["dersler"].items()):
            siniflar = sorted(info["siniflar"])
            sinif_str = "-".join(sinif.replace(".Sınıf", "") for sinif in siniflar)
            sinif_str += ". Sınıf" if len(siniflar) == 1 else ". Sınıf"
            ortak_alanlar = sorted(info["alanlar"])
            ortak_str = ""
            if len(ortak_alanlar) > 1:
                ortak_str = f" ({len(ortak_alanlar)} Alan Ortak {'-'.join(ortak_alanlar)})"
            print(f"-> {ders} ({sinif_str}){ortak_str}")

    toplam_ders = set()
    for data in tum_veri.values():
        toplam_ders.update(data["dersler"].keys())

    print("\n==== Özet ====")
    print(f"Toplam Alan: {len(tum_veri)}")
    print(f"Toplam Benzersiz Ders: {len(toplam_ders)}")

if __name__ == "__main__":
    main()