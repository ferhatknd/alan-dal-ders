import requests
from bs4 import BeautifulSoup
import sys
import time
import unicodedata
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import pdfplumber
import argparse
import io

def slugify(text):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    # Türkçe karakterleri Latin karakterlere çevir
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Küçük harfe çevir ve boşlukları kaldır
    return "".join(filter(str.isalnum, text.lower()))

BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
BASE_DERS_ALT_URL = "https://meslek.meb.gov.tr/dmgoster.aspx"
BASE_DBF_URL = "https://meslek.meb.gov.tr/dbflistele.aspx"
BASE_BOM_URL = "https://meslek.meb.gov.tr/moduller"

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

def get_dbf_data_for_class(sinif_kodu):
    """Belirtilen sınıf koduna ait DBF verilerini çeker."""
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

def get_all_dbf_data(siniflar):
    """Tüm sınıflar için DBF verilerini eşzamanlı olarak çeker."""
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

def get_cop_data_for_class(sinif_kodu):
    """Belirtilen sınıf koduna ait Çerçeve Öğretim Programı (ÇÖP) verilerini çeker."""
    params = {"sinif_kodu": sinif_kodu, "kurum_id": "1"}
    class_cop_data = {}
    try:
        # ÇÖP sayfası, alan listesiyle aynı URL'i kullanıyor
        response = requests.get(BASE_OPTIONS_URL, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        alan_columns = soup.find_all('div', class_='col-lg-3')
        for column in alan_columns:
            link_tag = column.find('a', href=True)
            # Linkin bir ÇÖP PDF'i olduğundan emin olalım
            if not link_tag or not link_tag['href'].endswith('.pdf') or 'upload/cop' not in link_tag['href']:
                continue

            cop_link = requests.compat.urljoin(response.url, link_tag['href'])
            
            ul_tag = link_tag.find('ul', class_='list-group')
            if not ul_tag: continue

            alan_adi = ""
            guncelleme_yili = ""

            b_tag = ul_tag.find('b')
            if b_tag:
                alan_adi = b_tag.get_text(strip=True)

            for item in ul_tag.find_all('li'):
                if item.find('i', class_='fa-calendar'):
                    tarih_str = item.get_text(strip=True)
                    guncelleme_yili = tarih_str.split('-')[0].strip() if '-' in tarih_str else tarih_str.strip()
                    break

            if alan_adi and cop_link:
                class_cop_data[alan_adi] = {
                    "link": cop_link,
                    "guncelleme_yili": guncelleme_yili
                }
    except requests.RequestException as e:
        print(f"ÇÖP Hata: {sinif_kodu}. sınıf sayfası çekilemedi: {e}", file=sys.stderr)
    return sinif_kodu, class_cop_data

def get_all_cop_data(siniflar):
    """Tüm sınıflar için ÇÖP verilerini eşzamanlı olarak çeker."""
    all_cop_data = {}
    with ThreadPoolExecutor(max_workers=len(siniflar)) as executor:
        future_to_sinif = {executor.submit(get_cop_data_for_class, sinif): sinif for sinif in siniflar}
        for future in as_completed(future_to_sinif):
            try:
                sinif, data = future.result()
                all_cop_data[sinif] = data
            except Exception as exc:
                print(f"ÇÖP verisi işlenirken hata: {exc}", file=sys.stderr)
    return all_cop_data

def get_aspnet_form_data(soup):
    """Bir BeautifulSoup nesnesinden ASP.NET form verilerini (VIEWSTATE vb.) çıkarır."""
    form_data = {}
    for input_tag in soup.find_all('input', {'type': ['hidden', 'submit', 'text', 'image']}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value
    return form_data

def get_bom_for_alan(alan_id, alan_adi, session):
    """
    Belirtilen bir alan için Bireysel Öğrenme Materyalleri (BÖM) verilerini çeker.
    Bu fonksiyon, ASP.NET postback'lerini yönetmek için bir session nesnesi kullanır.
    """
    bom_data = {"dersler": []}
    try:
        # 1. Adım: Alan ve ders listelerini almak için ilk GET isteği
        initial_resp = session.get(BASE_BOM_URL, headers=HEADERS, timeout=20)
        initial_resp.raise_for_status()
        initial_soup = BeautifulSoup(initial_resp.text, 'html.parser')

        # 2. Adım: Alanı seçmek ve ders listesini doldurmak için ilk POST isteği
        form_data = get_aspnet_form_data(initial_soup)
        form_data['ctl00$ContentPlaceHolder1$DropDownList1'] = alan_id
        form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$DropDownList1'

        ders_list_resp = session.post(BASE_BOM_URL, data=form_data, headers=HEADERS, timeout=20)
        ders_list_resp.raise_for_status()
        ders_list_soup = BeautifulSoup(ders_list_resp.text, 'html.parser')

        # 3. Adım: Doldurulan ders listesini ayrıştır
        ders_select = ders_list_soup.find('select', {'name': 'ctl00$ContentPlaceHolder1$DropDownList2'})
        if not ders_select:
            return bom_data

        ders_options = ders_select.find_all('option')
        if len(ders_options) <= 1:  # Sadece "Seçiniz" varsa
            return bom_data

        # 4. Adım: Her bir ders için modülleri çek
        for ders_option in ders_options:
            ders_value = ders_option.get('value')
            ders_adi = ders_option.text.strip()
            if not ders_value or ders_value == '0':
                continue

            ders_form_data = get_aspnet_form_data(ders_list_soup)
            ders_form_data['ctl00$ContentPlaceHolder1$DropDownList1'] = alan_id
            ders_form_data['ctl00$ContentPlaceHolder1$DropDownList2'] = ders_value
            ders_form_data['ctl00$ContentPlaceHolder1$Button1'] = 'Listele'

            modul_resp = session.post(BASE_BOM_URL, data=ders_form_data, headers=HEADERS, timeout=20)
            modul_resp.raise_for_status()
            modul_soup = BeautifulSoup(modul_resp.text, 'html.parser')

            # 5. Adım: Modül tablosunu ayrıştır
            ders_modulleri = []
            modul_table = modul_soup.find('table', id='ctl00_ContentPlaceHolder1_GridView1')
            if modul_table:
                for row in modul_table.find_all('tr')[1:]:  # Başlık satırını atla
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        modul_adi = cols[0].get_text(strip=True)
                        link_tag = cols[1].find('a', href=True)
                        if link_tag:
                            full_link = requests.compat.urljoin("https://megep.meb.gov.tr/", link_tag['href'])
                            ders_modulleri.append({"isim": modul_adi, "link": full_link})
            
            if ders_modulleri:
                bom_data["dersler"].append({
                    "ders_adi": ders_adi,
                    "moduller": ders_modulleri
                })

    except requests.RequestException as e:
        print(f"BÖM Hata: '{alan_adi}' alanı için veri çekilemedi: {e}", file=sys.stderr)
        return None
    
    return bom_data

def get_all_bom_data(alanlar_listesi):
    """Tüm alanlar için BÖM verilerini eş zamanlı olarak çeker."""
    all_bom_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_alan = {executor.submit(get_bom_for_alan, alan['id'], alan['isim'], requests.Session()): alan for alan in alanlar_listesi if alan['id'] not in ["0", "00"]}
        for future in as_completed(future_to_alan):
            alan = future_to_alan[future]
            try:
                data = future.result()
                if data and data.get("dersler"):
                    all_bom_data[alan['id']] = data
            except Exception as exc:
                print(f"BÖM verisi işlenirken hata ({alan['isim']}): {exc}", file=sys.stderr)
    return all_bom_data

def download_and_parse_pdf(pdf_url):
    """
    Bir URL'den PDF'i indirir, içeriğini ayrıştırır ve yapısal bir sözlük döndürür.
    Bu fonksiyon, README'de bahsedilen detaylı ayrıştırma mantığı için bir başlangıç noktasıdır.
    """
    try:
        response = requests.get(pdf_url, headers=HEADERS, timeout=45, stream=True)
        response.raise_for_status()

        # Gelen içeriğin PDF olup olmadığını kontrol et
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type:
            if pdf_url.endswith(('.rar', '.zip')):
                return {"icerik": f"Bu bir arşiv dosyasıdır ({os.path.basename(pdf_url)}), otomatik ayrıştırma desteklenmiyor."}
            return {"hata": f"İndirilen dosya bir PDF değil. Tür: {content_type}"}

        # Dosyayı hafızada tutarak işle
        pdf_file = io.BytesIO(response.content)

        # --- DETAYLI AYRIŞTIRMA MANTIĞI (KAZANIM, ÜNİTE VB.) BURAYA GELECEK ---
        # Örnek olarak, ilk sayfanın metnini ve toplam sayfa sayısını çekiyoruz.
        # Bu bölümü kendi karmaşık ayrıştırma mantığınızla genişletebilirsiniz.
        text_content = ""
        page_count = 0
        with pdfplumber.open(pdf_file) as pdf:
            page_count = len(pdf.pages)
            if page_count > 0:
                page = pdf.pages[0]
                text_content = page.extract_text(x_tolerance=2, y_tolerance=2) or ""

        return {
            "ozet": text_content[:500].strip() + "..." if text_content else "İçerik okunamadı.",
            "sayfa_sayisi": page_count
        }
    except requests.RequestException as e:
        return {"hata": f"PDF indirilemedi: {e}"}
    except Exception as e:
        return {"hata": f"PDF ayrıştırılırken hata oluştu: {e}"}

def scrape_data():
    """Verileri çeker ve ilerlemeyi yield ile anlık olarak bildirir."""
    siniflar = ["9", "10", "11", "12"]
    tum_veri = {}
    link_index = {}
    
    CACHE_FILE = "data/scraped_data.json"

    # Adım 1: Mevcut önbelleği yükle
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                tum_veri = cached_data.get("alanlar", {})
                link_index = cached_data.get("ortak_alan_indeksi", {})
                yield {"type": "progress", "message": "Mevcut önbellek yüklendi. Eksik veriler tamamlanacak..."}
        except (IOError, json.JSONDecodeError):
            yield {"type": "warning", "message": "Önbellek dosyası bozuk, sıfırdan başlanıyor."}
            tum_veri = {}
            link_index = {}
    else:
        yield {"type": "progress", "message": "Önbellek bulunamadı, veri çekme işlemi başlatılıyor..."}

    # Adım 2: Tüm DBF verilerini en başta çek
    yield {"type": "progress", "message": "DBF verileri çekiliyor..."}
    dbf_data = get_all_dbf_data(siniflar)
    yield {"type": "progress", "message": "DBF verileri çekildi."}

    yield {"type": "progress", "message": "Çerçeve Öğretim Programı (ÇÖP) verileri çekiliyor..."}
    cop_data = get_all_cop_data(siniflar)
    yield {"type": "progress", "message": "ÇÖP verileri çekildi."}
    
    # Adım 3: Toplam iş yükünü hesapla (tüm alanların sayısını bul)
    all_alanlar_by_sinif = {sinif: get_alanlar(sinif) for sinif in siniflar}
    # BÖM için kullanılacak benzersiz alan listesi
    unique_alanlar = list({v['id']:v for k,v_list in all_alanlar_by_sinif.items() for v in v_list}.values())
    total_alan_count = sum(len(alan_list) for alan_list in all_alanlar_by_sinif.values())

    if total_alan_count == 0:
        yield {"type": "warning", "message": "İşlenecek hiç alan bulunamadı. İşlem sonlandırılıyor."}
        yield {"type": "done", "data": {"alanlar": {}, "ortak_alan_indeksi": {}}}
        return

    # Adım 3.5: BÖM verilerini çek
    yield {"type": "progress", "message": "Bireysel Öğrenme Materyalleri (BÖM) verileri çekiliyor..."}
    bom_data = get_all_bom_data(unique_alanlar)
    yield {"type": "progress", "message": "BÖM verileri çekildi. Alanlar işleniyor..."}

    yield {"type": "progress", "message": f"Toplam {total_alan_count} alan/sınıf kombinasyonu işlenecek."}

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
            
            # Alanın zaten işlenip işlenmediğini kontrol et (dersler ve dbf linki)
            alan_entry = tum_veri.get(alan_id, {})
            dersler_dolu = alan_entry.get("dersler") and any(d.get("siniflar") and sinif in d["siniflar"] for d in alan_entry["dersler"].values())
            dbf_link_var = sinif in alan_entry.get("dbf_bilgileri", {})
            cop_link_var = sinif in alan_entry.get("cop_bilgileri", {})

            if dersler_dolu and dbf_link_var and cop_link_var:
                yield {
                    "type": "progress",
                    "message": f"[{sinif}. Sınıf] Alan zaten güncel: {alan_adi} ({processed_alan_count}/{total_alan_count})",
                    "estimation": estimation_str
                }
                continue # Bu alanı atla

            yield {
                "type": "progress",
                "message": f"[{sinif}. Sınıf] Alan işleniyor: {alan_adi} ({processed_alan_count}/{total_alan_count})",
                "estimation": estimation_str
            }
            
            # Alan verisini ve DBF linklerini hazırla, eksik anahtarları güvenli bir şekilde ekle
            alan_entry = tum_veri.setdefault(alan_id, {"isim": alan_adi})
            alan_entry.setdefault("dersler", {})
            alan_entry.setdefault("dbf_bilgileri", {})
            alan_entry.setdefault("cop_bilgileri", {})
            alan_entry.setdefault("bom_materyalleri", bom_data.get(alan_id, {}))
            
            # Kazınan DBF verisini ekle
            sinif_dbf_data = dbf_data.get(sinif, {})
            if alan_adi in sinif_dbf_data:
                dbf_info = sinif_dbf_data[alan_adi]
                alan_entry["dbf_bilgileri"][sinif] = dbf_info

                # YENİ ADIM: PDF'i indir ve ayrıştır
                yield {
                    "type": "progress",
                    "message": f"  -> DBF indiriliyor/ayrıştırılıyor: {alan_adi} ({sinif}. Sınıf)"
                }
                parsed_content = download_and_parse_pdf(dbf_info['link'])
                # Ayrıştırılan içeriği mevcut bilgiye ekle
                alan_entry["dbf_bilgileri"][sinif]['ayristirilan_veri'] = parsed_content
                if "hata" in parsed_content:
                    yield {"type": "warning", "message": f"  -> UYARI: {alan_adi} DBF ayrıştırılamadı: {parsed_content['hata']}"}
                else:
                    yield {"type": "progress", "message": f"  -> DBF başarıyla ayrıştırıldı."}
            
            # Dersleri sadece gerekliyse çek
            # YENİ ADIM: Kazınan ÇÖP verisini ekle
            sinif_cop_data = cop_data.get(sinif, {})
            if alan_adi in sinif_cop_data:
                cop_info = sinif_cop_data[alan_adi]
                alan_entry["cop_bilgileri"][sinif] = cop_info
            
            if not dersler_dolu:
                ders_listesi = get_dersler_for_alan(alan_id, alan["isim"], sinif)
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
    
    # Veriyi dosyaya kaydet
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        yield {"type": "progress", "message": f"Veri başarıyla {CACHE_FILE} dosyasına kaydedildi/güncellendi."}
    except IOError as e:
        yield {"type": "error", "message": f"HATA: Önbellek dosyası yazılamadı: {e}"}

    # Son olarak, tüm veriyi 'done' tipiyle gönder
    yield {"type": "done", "data": final_data}

def print_full_summary():
    """
    Runs the full scrape and prints a summary of all data to the terminal.
    This was the original main() function's behavior.
    """
    # Generator'dan gelen tüm veriyi topla
    print("Tüm veriler çekiliyor ve özet oluşturuluyor... (Bu işlem uzun sürebilir)")
    final_data = None
    for item in scrape_data():
        # Sadece ilerleme ve uyarıları göster, çok fazla çıktı olmasın
        if item['type'] in ['progress', 'warning', 'error']:
            print(f"  -> {item['message']}", file=sys.stderr)
        if item['type'] == 'done':
            final_data = item['data']
            break
    
    if not final_data:
        print("Veri çekme işlemi başarısız oldu veya veri bulunamadı.", file=sys.stderr)
        return

    tum_veri = final_data["alanlar"]
    link_index = final_data["ortak_alan_indeksi"]

    # 🖨️ Terminal çıktısı
    for alan_id, alan_data in sorted(tum_veri.items(), key=lambda item: item[1]['isim']):
        print(f"\n{alan_data['isim']} ({alan_id})")
        
        # DBF Linklerini yazdır
        if alan_data.get("dbf_bilgileri") and any(alan_data["dbf_bilgileri"].values()):
            print("  Ders Bilgi Formları:")
            for sinif, dbf_info in sorted(alan_data["dbf_bilgileri"].items()):
                tarih_str = f" (Güncelleme: {dbf_info['guncelleme_tarihi']})" if dbf_info.get('guncelleme_tarihi') else ""
                print(f"  -> {sinif}. Sınıf: {dbf_info['link']}{tarih_str}")

        # ÇÖP Linklerini yazdır
        if alan_data.get("cop_bilgileri") and any(alan_data["cop_bilgileri"].values()):
            print("  Çerçeve Öğretim Programları (ÇÖP):")
            for sinif, cop_info in sorted(alan_data["cop_bilgileri"].items()):
                yil_str = f" (Yıl: {cop_info['guncelleme_yili']})" if cop_info.get('guncelleme_yili') else ""
                print(f"  -> {sinif}. Sınıf: {cop_info['link']}{yil_str}")

        # BÖM Materyallerini yazdır
        if alan_data.get("bom_materyalleri") and alan_data.get("bom_materyalleri", {}).get("dersler"):
            print("  Bireysel Öğrenme Materyalleri (BÖM):")
            for ders in alan_data["bom_materyalleri"]["dersler"]:
                print(f"    - Ders: {ders['ders_adi']}")
                if ders.get("moduller"):
                    for modul in ders["moduller"]:
                        print(f"      -> {modul['isim']}: {modul['link']}")
        
        # Dersleri isme göre sırala
        sorted_dersler = sorted(alan_data["dersler"].items(), key=lambda item: item[1]["isim"])
        if sorted_dersler:
            print("  Ders Materyalleri (PDF):")
            for ders_link, d in sorted_dersler:
                # Sınıfları birleştir: ["11", "12"] -> "11-12"
                sinif_str = "-".join(d['siniflar'])
                sinif_display_str = f"({sinif_str}. Sınıf)"
                # Ortak alan bilgisini oluştur
                ortak_alanlar = link_index.get(ders_link, [])
                ortak_str = ""
                if len(ortak_alanlar) > 1:
                    ortak_str = f" ({len(ortak_alanlar)} ortak alan)"
                print(f"  -> {d['isim']} {sinif_display_str}{ortak_str}")

    print("\n==== Özet ====")
    toplam_alan = len(tum_veri)
    alan_bazinda_toplam_ders = sum(len(alan_data["dersler"]) for alan_data in tum_veri.values())
    benzersiz_toplam_ders = len({l for l in link_index})
    print(f"Toplam Alan: {toplam_alan}")
    print(f"Alan Bazında Toplam Ders: {alan_bazinda_toplam_ders}")
    print(f"Benzersiz Toplam Ders: {benzersiz_toplam_ders}")

def main():
    parser = argparse.ArgumentParser(description="MEB veri çekme ve test aracı.")
    parser.add_argument(
        '--test', 
        choices=['bom', 'dbf', 'cop', 'dersler', 'alanlar'], 
        help="Belirli bir modülü test et: 'bom', 'dbf', 'cop', 'dersler', 'alanlar'."
    )
    parser.add_argument(
        '--alan-id', 
        type=str, 
        help="Test için belirli bir alan ID'si (örn: '04' Bilişim Teknolojileri için)."
    )
    parser.add_argument(
        '--sinif', 
        type=str, 
        help="Test için belirli bir sınıf (örn: '9', '10', '11', '12')."
    )
    args = parser.parse_args()

    if not args.test:
        # Test argümanı yoksa, tam özet fonksiyonunu çalıştır
        print_full_summary()
        return

    print(f"🚀 Test modu başlatıldı: {args.test}")
    
    if args.test == 'alanlar':
        sinif = args.sinif if args.sinif else "9"
        print(f"Alanlar {sinif}. sınıf için çekiliyor...")
        data = get_alanlar(sinif)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.test == 'dersler':
        if not args.alan_id:
            print("Hata: 'dersler' testi için --alan-id gereklidir.", file=sys.stderr)
            return
        sinif = args.sinif if args.sinif else "9"
        print(f"Dersler, Alan ID: {args.alan_id}, Sınıf: {sinif} için çekiliyor...")
        data = get_dersler_for_alan(args.alan_id, "Test Alanı", sinif)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.test == 'dbf':
        sinif = args.sinif if args.sinif else "9"
        print(f"DBF verileri {sinif}. sınıf için çekiliyor...")
        _, data = get_dbf_data_for_class(sinif)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.test == 'cop':
        sinif = args.sinif if args.sinif else "9"
        print(f"ÇÖP verileri {sinif}. sınıf için çekiliyor...")
        _, data = get_cop_data_for_class(sinif)
        print(json.dumps(data, indent=2, ensure_ascii=False))

    elif args.test == 'bom':
        if not args.alan_id:
            print("Hata: 'bom' testi için --alan-id gereklidir.", file=sys.stderr)
            return
        print(f"BÖM verileri Alan ID: {args.alan_id} için çekiliyor...")
        # get_bom_for_alan bir session nesnesi bekliyor, test için yeni bir tane oluşturalım.
        data = get_bom_for_alan(args.alan_id, "Test Alanı", requests.Session())
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
