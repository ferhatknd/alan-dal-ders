import sys
sys.path.append('.')
from extract_olcme import extract_olcme_degerlendirme_from_pdf
import os

# Önceki problemli dosyalar
problem_files = [
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/50_Ucak_Bakim/UÇAK BAKIM/9.SINIF/1- UÇAK MALZEME VE DONANIM ATÖLYESİ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/53_Yiyecek_Icecek_Hizmetleri/YİYECEK 2023/11.SINIF/yöresel yemekler.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/23_Insaat_Teknolojisi/insaat/11 SINIF/seçmeli dersler/20_BİNA VE YERLEŞİM RÖLÖVESİ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/16_Grafik_ve_Fotograf/GRAFİK VE FOTOĞRAF ALANI/11/VİDEO ÇEKİM.pdf"
]

for i, pdf_path in enumerate(problem_files, 1):
    if os.path.exists(pdf_path):
        print(f"{os.path.dirname(pdf_path).replace('/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/', '')} / {os.path.basename(pdf_path)}")
        print("-" * 80)
        
        olcme_text = extract_olcme_degerlendirme_from_pdf(pdf_path)
        print(olcme_text)
        print()
    else:
        print(f"❌ Dosya bulunamadı: {pdf_path}")
        print()