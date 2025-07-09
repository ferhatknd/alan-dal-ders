import requests
from bs4 import BeautifulSoup
import sys

import time
BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"

# Sunucu tarafından engellenmemek için bir tarayıcı gibi davranan başlıklar ekleyelim.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://meslek.meb.gov.tr/"
}

def get_alanlar(sinif_kodu="9"):
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    try:
        resp = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()  # 4xx veya 5xx HTTP durum kodlarında hata fırlatır.
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
        resp.raise_for_status() # 4xx veya 5xx HTTP durum kodlarında hata fırlatır.
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
        # Bu durumu çağıran fonksiyona bildirmek için boş liste yeterli.
        pass
    return dersler

def scrape_data():
    """Verileri çeker ve ilerlemeyi yield ile anlık olarak bildirir."""
    siniflar = ["9","10","11","12"]
    tum_veri = {}
    link_index = {}

    yield {"type": "progress", "message": "Veri çekme işlemi başlatılıyor..."}

    # Adım 1: Toplam iş yükünü hesapla (tüm alanların sayısını bul)
    yield {"type": "progress", "message": "Toplam iş yükü hesaplanıyor..."}
    all_alanlar_by_sinif = {sinif: get_alanlar(sinif) for sinif in siniflar}
    total_alan_count = sum(len(alan_list) for alan_list in all_alanlar_by_sinif.values())

    if total_alan_count == 0:
        yield {"type": "warning", "message": "İşlenecek hiç alan bulunamadı. İşlem sonlandırılıyor."}
        yield {"type": "done", "data": {"alanlar": {}, "ortak_alan_indeksi": {}}}
        return

    yield {"type": "progress", "message": f"Toplam {total_alan_count} alan işlenecek."}

    processed_alan_count = 0
    start_time = time.time()

    for sinif in siniflar:
        alanlar = all_alanlar_by_sinif[sinif]
        if not alanlar:
            yield {"type": "warning", "message": f"Uyarı: {sinif}. sınıf için alan bulunamadı."}
            continue

        for i, alan in enumerate(alanlar):
            # İlerleme ve zaman tahmini
            processed_alan_count += 1
            elapsed_time = time.time() - start_time
            avg_time_per_alan = elapsed_time / processed_alan_count
            remaining_alanlar = total_alan_count - processed_alan_count
            estimated_remaining_time_seconds = remaining_alanlar * avg_time_per_alan
            
            # Zamanı dakika ve saniye olarak formatla
            mins, secs = divmod(estimated_remaining_time_seconds, 60)
            estimation_str = f"Tahmini kalan süre: {int(mins)} dakika {int(secs)} saniye"

            alan_id = alan["id"]
            alan_adi = alan["isim"]
            yield {
                "type": "progress",
                "message": f"[{sinif}. Sınıf] Alan işleniyor: {alan_adi} ({processed_alan_count}/{total_alan_count})",
                "estimation": estimation_str
            }
            ders_listesi = get_dersler_for_alan(alan_id, alan["isim"], sinif)
            alan_entry = tum_veri.setdefault(alan_id, {"isim": alan_adi, "dersler": {}})
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

    # JSON uyumluluğu için set'leri listeye çevir
    for alan_id in tum_veri:
        for ders_link in tum_veri[alan_id]["dersler"]:
            tum_veri[alan_id]["dersler"][ders_link]["siniflar"] = sorted(list(tum_veri[alan_id]["dersler"][ders_link]["siniflar"]), key=int)
    for link in link_index:
        link_index[link] = sorted(list(link_index[link]))

    yield {"type": "progress", "message": "İşlem tamamlandı. Veriler birleştiriliyor..."}
    final_data = {"alanlar": tum_veri, "ortak_alan_indeksi": link_index}
    # Son olarak, tüm veriyi 'done' tipiyle gönder
    yield {"type": "done", "data": final_data}

def main():
    # Generator'dan gelen tüm veriyi topla
    scraped_data = [item for item in scrape_data() if item['type'] == 'done'][0]['data']
    tum_veri = scraped_data["alanlar"]
    link_index = scraped_data["ortak_alan_indeksi"]
    # 🖨️ Terminal çıktısı
    for alan_id, alan_data in sorted(tum_veri.items(), key=lambda item: item[1]['isim']):
        print(f"\n{alan_data['isim']} ({alan_id})")
        # Dersleri isme göre sırala
        sorted_dersler = sorted(alan_data["dersler"].items(), key=lambda item: item[1]["isim"])
        for ders_link, d in sorted_dersler:
            # Sınıfları birleştir: {"11", "12"} -> "11-12"
            sinif_str = "-".join(d['siniflar'])
            sinif_display_str = f"({sinif_str}. Sınıf)"
            # Ortak alan bilgisini oluştur
            ortak_alanlar = link_index.get(ders_link, [])
            ortak_str = ""
            if len(ortak_alanlar) > 1:
                ortak_str = f" ({len(ortak_alanlar)} ortak alan)"
            print(f"-> {d['isim']} {sinif_display_str}{ortak_str}")

    print("\n==== Özet ====")
    toplam_alan = len(tum_veri)
    alan_bazinda_toplam_ders = sum(len(alan_data["dersler"]) for alan_data in tum_veri.values())
    benzersiz_toplam_ders = len({l for l in link_index})
    print(f"Toplam Alan: {toplam_alan}")
    print(f"Alan Bazında Toplam Ders: {alan_bazinda_toplam_ders}")
    print(f"Benzersiz Toplam Ders: {benzersiz_toplam_ders}")

if __name__ == "__main__":
    # print("✅ Bu kod çalışıyor")  # Kontrol satırı - server.py tarafından import edildiği için yoruma alındı.
    main()
