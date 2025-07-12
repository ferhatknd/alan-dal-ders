import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_BOM_URL = "https://meslek.meb.gov.tr/moduller"
BASE_OPTIONS_URL = "https://meslek.meb.gov.tr/cercevelistele.aspx"
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

def get_aspnet_form_data(soup):
    form_data = {}
    for input_tag in soup.find_all('input', {'type': ['hidden', 'submit', 'text', 'image']}):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value
    return form_data

def get_bom_for_alan(alan_id, alan_adi, session):
    bom_data = {"dersler": []}
    try:
        initial_resp = session.get(BASE_BOM_URL, headers=HEADERS, timeout=20)
        initial_resp.raise_for_status()
        initial_soup = BeautifulSoup(initial_resp.text, 'html.parser')

        form_data = get_aspnet_form_data(initial_soup)
        form_data['ctl00$ContentPlaceHolder1$DropDownList1'] = alan_id
        form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$DropDownList1'

        ders_list_resp = session.post(BASE_BOM_URL, data=form_data, headers=HEADERS, timeout=20)
        ders_list_resp.raise_for_status()
        ders_list_soup = BeautifulSoup(ders_list_resp.text, 'html.parser')

        ders_select = ders_list_soup.find('select', {'name': 'ctl00$ContentPlaceHolder1$DropDownList2'})
        if not ders_select:
            return bom_data

        ders_options = ders_select.find_all('option')
        if len(ders_options) <= 1:
            return bom_data

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

            ders_modulleri = []
            modul_table = modul_soup.find('table', id='ctl00_ContentPlaceHolder1_GridView1')
            if modul_table:
                for row in modul_table.find_all('tr')[1:]:
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
        print(f"BÖM Hata: '{alan_adi}' alanı için veri çekilemedi: {e}")
        return None
    
    return bom_data

def getir_bom(siniflar=["9", "10", "11", "12"]):
    """
    Tüm alanlar için Bireysel Öğrenme Materyali (BÖM) verilerini eş zamanlı olarak çeker.
    """
    # Tüm sınıflardan benzersiz alanları topla
    all_alanlar_by_sinif = {sinif: get_alanlar(sinif) for sinif in siniflar}
    unique_alanlar = list({v['id']:v for k,v_list in all_alanlar_by_sinif.items() for v in v_list}.values())

    all_bom_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_alan = {executor.submit(get_bom_for_alan, alan['id'], alan['isim'], requests.Session()): alan for alan in unique_alanlar if alan['id'] not in ["0", "00"]}
        for future in as_completed(future_to_alan):
            alan = future_to_alan[future]
            try:
                data = future.result()
                if data and data.get("dersler"):
                    all_bom_data[alan['id']] = data
            except Exception as exc:
                print(f"BÖM verisi işlenirken hata ({alan['isim']}): {exc}")
    return all_bom_data
