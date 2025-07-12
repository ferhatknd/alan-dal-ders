"""
MEB Mesleki ve Teknik Eğitim Genel Müdürlüğü 'Kurum / Alan / Dal' listesini
tüm iller ve tüm alanlar için çekip, alan-dal ilişkisini getir_dal_sonuc.json dosyasına kaydeder.

Çalışma mantığı:
- Tüm iller ve alanlar statik olarak HTML'de mevcut.
- Her alan için dallar dinamik olarak yükleniyor (muhtemelen bir endpoint ile).
- Eğer endpoint bulunamazsa, selenium ile browser otomasyonu yapılabilir.

Kullanım:
    python getir_dal.py

Gereksinimler:
    pip install selenium webdriver-manager tqdm
"""

import json
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Statik olarak HTML'den alınan alan listesi
ALANLAR = [
    "ADALET", "AİLE VE TÜKETİCİ HİZMETLERİ", "AYAKKABI VE SARACİYE TEKNOLOJİSİ", "BİLİŞİM TEKNOLOJİLERİ",
    "BİYOMEDİKAL CİHAZ TEKNOLOJİLERİ", "BÜRO YÖNETİMİ", "BÜRO YÖNETİMİ VE YÖNETİCİ ASİSTANLIĞI",
    "ÇOCUK GELİŞİMİ VE EĞİTİMİ", "DENİZCİLİK", "EL SANATLARI TEKNOLOJİSİ", "ELEKTRİK-ELEKTRONİK TEKNOLOJİSİ",
    "ENDÜSTRİYEL OTOMASYON TEKNOLOJİLERİ", "GAZETECİLİK", "GELENEKSEL TÜRK SANATLARI", "GEMİ YAPIMI",
    "GIDA TEKNOLOJİSİ", "GRAFİK VE FOTOĞRAF", "GÜZELLİK HİZMETLERİ", "HALKLA İLİŞKİLER", "HARİTA-TAPU-KADASTRO",
    "HASTA VE YAŞLI HİZMETLERİ", "HAVACILIK VE UZAY TEKNOLOJİSİ", "HAYVAN YETİŞTİRİCİLİĞİ VE SAĞLIĞI",
    "İNŞAAT TEKNOLOJİSİ", "İTFAİYECİLİK VE YANGIN GÜVENLİĞİ", "KİMYA TEKNOLOJİSİ", "KONAKLAMA VE SEYAHAT HİZMETLERİ",
    "KUYUMCULUK TEKNOLOJİSİ", "LABORATUVAR HİZMETLERİ", "MAKİNE TEKNOLOJİSİ", "MAKİNE VE TASARIM TEKNOLOJİSİ",
    "MATBAA TEKNOLOJİSİ", "METAL TEKNOLOJİSİ", "METALÜRJİ TEKNOLOJİSİ", "MİKROMEKANİK", "MOBİLYA VE İÇ MEKÂN TASARIMI",
    "MODA TASARIM TEKNOLOJİLERİ", "MOTORLU ARAÇLAR TEKNOLOJİSİ", "MUHASEBE VE FİNANSMAN", "PAZARLAMA VE PERAKENDE",
    "PLASTİK SANATLAR", "PLASTİK TEKNOLOJİSİ", "RADYO-TELEVİZYON", "RAYLI SİSTEMLER TEKNOLOJİSİ", "SAĞLIK HİZMETLERİ",
    "SERAMİK VE CAM TEKNOLOJİSİ", "SİBER GÜVENLİK", "TARIM", "TEKSTİL TEKNOLOJİSİ", "TESİSAT TEKNOLOJİSİ VE İKLİMLENDİRME",
    "UÇAK BAKIM", "ULAŞTIRMA HİZMETLERİ", "YENİLENEBİLİR ENERJİ TEKNOLOJİLERİ", "YİYECEK İÇECEK HİZMETLERİ"
]

def get_dallar_for_alan(driver, alan_adi):
    # Alanı seç
    alan_select = Select(driver.find_element(By.ID, "alanSelect"))
    alan_select.select_by_visible_text(alan_adi)

    # Dal select'i güncellenene kadar bekle
    WebDriverWait(driver, 5).until(
        lambda d: len(Select(d.find_element(By.ID, "dalSelect")).options) > 1
    )
    dal_select = Select(driver.find_element(By.ID, "dalSelect"))
    dallar = [opt.text for opt in dal_select.options if opt.get_attribute("value") and "dal" not in opt.text.lower()]
    return dallar

def main():
    url = "https://mtegm.meb.gov.tr/kurumlar/"
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    sonuc = {}
    for alan in tqdm(ALANLAR, desc="Alanlar"):
        try:
            # Sayfayı her seferinde yenile (bazı sitelerde select resetleniyor)
            driver.get(url)
            dallar = get_dallar_for_alan(driver, alan)
            sonuc[alan] = dallar
        except Exception as e:
            sonuc[alan] = []
            print(f"{alan} için hata: {e}")

    driver.quit()

    with open("getir_dal_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
