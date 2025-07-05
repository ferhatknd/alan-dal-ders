import requests
from bs4 import BeautifulSoup
import sys

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"

print("✅ Bu kod çalışıyor")  # Kontrol satırı

def get_alanlar(sinif_kodu="9"):
    resp = requests.get(BASE_OPTIONS_URL, params={"sinif_kodu": sinif_kodu, "kurum_id":"1"})
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec")
    if not sel:
        print(f"⚠️ Alan listesi bulunamadı (sınıf {sinif_kodu})", file=sys.stderr)
        return []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value','').strip()
        name = opt.text.strip()
        if val and val not in ("00","0"):
            alanlar.append({"id": val, "isim": name})
    return alanlar

def get_dersler_for_alan(alan_id, alan_adi, sinif_kodu="9"):
    resp = requests.get(BASE_DERS_ALT_URL, params={"sinif_kodu": sinif_kodu, "kurum_id":"1", "alan_id":alan_id})
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")

    dersler = []
    for div in soup.find_all('div', class_='p-0 bg-light'):
        a = div.find('a', href=True)
        if not a: continue
        ul = a.find('ul', class_='list-group')
        if not ul: continue

        # Ders adı → ilk <li>, sınıf bilgisini içeriyor
        items = ul.find_all('li')
        ders_adi = items[0].get_text(" ", strip=True)
        sinif_text = next((li.get_text(" ",strip=True) for li in items if "Sınıf" in li.get_text()), "")
        link = requests.compat.urljoin(resp.url, a['href'].strip())

        dersler.append({"isim": ders_adi,
                        "sinif": sinif_text,
                        "link": link})
    if not dersler:
        print(f"⚠️ Ders bulunamadı: {alan_adi} ({alan_id})", file=sys.stderr)
    return dersler

def main():
    siniflar = ["9","10","11","12"]
    tum_veri = {}  # alan_id → {"isim":..., "dersler":[...]}
    link_index = {}  # ders linki → liste[(alan_id, sinif)]

    print("Script başladı...")

    for sinif in siniflar:
        print(f"{sinif}. sınıf alanları çekiliyor...")
        for alan in get_alanlar(sinif):
            alan_id = alan["id"]
            ders_listesi = get_dersler_for_alan(alan_id, alan["isim"], sinif)
            entry = tum_veri.setdefault(alan_id, {"isim": alan["isim"], "dersler": []})
            for d in ders_listesi:
                entry["dersler"].append(d)
                link_index.setdefault(d["link"], []).append((alan_id, sinif))

    # 🖨️ Terminal çıktısı
    for alan in tum_veri.values():
        print(f"\n{alan['isim']} Alanı")
        for d in alan["dersler"]:
            linkgroups = link_index.get(d["link"], [])
            ortak_alanlar = sorted({alan_id for alan_id,_ in linkgroups})
            ortak_str = ""
            if len(ortak_alanlar) > 1:
                ortak_str = f" ({len(ortak_alanlar)} ortak alan - {'-'.join(ortak_alanlar)})"
            print(f"-> {d['isim']} ({d['sinif']}){ortak_str}")

    print("\n==== Özet ====")
    toplam_alan = len(tum_veri)
    toplam_ders = len({l for l in link_index})
    print(f"Toplam Alan: {toplam_alan}")
    print(f"Toplam Benzersiz Ders Link Sayısı: {toplam_ders}")

if __name__ == "__main__":
    main()