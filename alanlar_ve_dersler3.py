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
        # Sınıf bilgisini daha kesin bir şekilde çıkar
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
    if not dersler:
        print(f"⚠️ Ders bulunamadı: {alan_adi} ({alan_id})", file=sys.stderr)
    return dersler

def main():
    siniflar = ["9","10","11","12"]
    # Yapıyı değiştiriyoruz: alan_id -> {"isim": ..., "dersler": {link: {"isim":..., "siniflar": set()}}}
    tum_veri = {}
    # Ortak alanları bulmak için link_index'i kullanıyoruz
    link_index = {}  # ders linki → set of alan_id's

    print("Script başladı...")

    for sinif in siniflar:
        print(f"{sinif}. sınıf alanları çekiliyor...")
        for alan in get_alanlar(sinif):
            alan_id = alan["id"]
            ders_listesi = get_dersler_for_alan(alan_id, alan["isim"], sinif)
            # Alan için ana girişi oluştur/getir
            alan_entry = tum_veri.setdefault(alan_id, {"isim": alan["isim"], "dersler": {}})
            for d in ders_listesi:
                ders_link = d["link"]
                # Sınıf numarasını "11.Sınıf" metninden çıkar
                sinif_num = d["sinif"].replace(".Sınıf", "").strip()
                # Ders linkini anahtar olarak kullanarak dersleri grupla
                ders_entry = alan_entry["dersler"].setdefault(ders_link, {
                    "isim": d["isim"],
                    "siniflar": set()
                })
                ders_entry["siniflar"].add(sinif_num)
                # Bu dersin (linkin) hangi alanlarda olduğunu takip et
                link_index.setdefault(ders_link, set()).add(alan_id)

    # 🖨️ Terminal çıktısı
    for alan_id, alan_data in sorted(tum_veri.items(), key=lambda item: item[1]['isim']):
        print(f"\n{alan_data['isim']} Alanı")
        # Dersleri isme göre sırala
        sorted_dersler = sorted(alan_data["dersler"].items(), key=lambda item: item[1]["isim"])
        for ders_link, d in sorted_dersler:
            # Sınıfları birleştir: {"11", "12"} -> "11-12"
            siniflar_sorted = sorted(list(d['siniflar']), key=int)
            sinif_str = "-".join(siniflar_sorted)
            sinif_display_str = f"({sinif_str}. Sınıf)"
            # Ortak alan bilgisini oluştur
            ortak_alanlar = sorted(list(link_index.get(ders_link, set())))
            ortak_str = ""
            if len(ortak_alanlar) > 1:
                ortak_str = f" ({len(ortak_alanlar)} ortak alan - {'-'.join(ortak_alanlar)})"
            print(f"-> {d['isim']} {sinif_display_str}{ortak_str}")

    print("\n==== Özet ====")
    toplam_alan = len(tum_veri)
    toplam_ders = len({l for l in link_index})
    print(f"Toplam Alan: {toplam_alan}")
    print(f"Toplam Benzersiz Ders Link Sayısı: {toplam_ders}")

if __name__ == "__main__":
    main()
