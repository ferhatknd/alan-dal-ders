import requests
from bs4 import BeautifulSoup

url = "https://meslek.meb.gov.tr/cercevelistele.aspx?sinif_kodu=9&kurum_id=1"
resp = requests.get(url)
resp.encoding = resp.apparent_encoding
soup = BeautifulSoup(resp.text, "html.parser")

select_box = soup.find('select', id="ContentPlaceHolder1_drpalansec")
options = select_box.find_all('option')import requests
from bs4 import BeautifulSoup
import sys

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_URL = "https://meslek.meb.gov.tr/cercevegoster.aspx"

def get_alanlar(sinif_kodu="9", kurum_id="1"):
    """Tüm alanları (alan_id ve isim) döndür."""
    params = {"sinif_kodu": sinif_kodu, "kurum_id": kurum_id}
    resp = requests.get(BASE_OPTIONS_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    sel = soup.find('select', id="ContentPlaceHolder1_drpalansec")
    if not sel:
        print("Alanlar dropdown'u bulunamadı!", file=sys.stderr)
        return []
    alanlar = []
    for opt in sel.find_all('option'):
        val = opt.get('value').strip()
        name = opt.text.strip()
        if val:
            alanlar.append({"id": val, "isim": name})
    return alanlar

def get_dersler_for_alan(alan_id, sinif_kodu="9", kurum_id="1"):
    """Belirli bir alan için ders listesini döndür."""
    params = {"alan_id": alan_id, "sinif_kodu": sinif_kodu, "kurum_id": kurum_id}
    resp = requests.get(BASE_DERS_URL, params=params)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    # HTML yapısına göre sınıfı güncelle
    # Örnek: <ul class="ders-list"> yoksa <table> veya başka olabilir
    ul = soup.find('ul', class_='ders-list')
    if ul:
        return [li.text.strip() for li in ul.find_all('li') if li.text.strip()]
    # Alternatif table yapısı
    table = soup.find('table', class_='tblListe')
    if table:
        return [td.text.strip() for td in table.find_all('td') if td.text.strip()]
    print(f"Alan ID {alan_id} için dersler bulunamadı!", file=sys.stderr)
    return []

def main():
    alanlar = get_alanlar()
    if not alanlar:
        return

    ders_to_alan = {}
    alan_to_ders = {}

    for alan in alanlar:
        alan_id = alan["id"]
        alan_name = alan["isim"]
        dersler = get_dersler_for_alan(alan_id)
        alan_to_ders[alan_name] = dersler
        for ders in dersler:
            ders_to_alan.setdefault(ders, set()).add(alan_name)

    # Terminal çıktısı
    print("\n== Alan → Dersler ==")
    for alan_name, dersler in alan_to_ders.items():
        print(f"\n📘 {alan_name} ({len(dersler)} ders):")
        for d in sorted(dersler):
            print(f"  - {d}")

    print("\n== Ders → Alan(lar) ==")
    for ders_name, alan_set in sorted(ders_to_alan.items()):
        print(f"\n📗 {ders_name} ({len(alan_set)} alan):")
        for a in sorted(alan_set):
            print(f"  - {a}")

if __name__ == "__main__":
    main()

for opt in options:
    value = opt.get('value')
    text = opt.text.strip()
    print(f"{value} — {text}")