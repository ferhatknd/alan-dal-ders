import sys
sys.path.append('.')
from extract_olcme import extract_olcme_degerlendirme_from_pdf
import os

# Yeni problemli dosyalar
problem_files = [
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/38_Muhasebe_ve_Finansman/MUHASEBE VE FİNANSMAN ALANI/10.SINIF/TEMEL HUKUK 10.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/38_Muhasebe_ve_Finansman-Protokol/MUHASEBE VE FİNANSMAN ALANI/11.SINIF/MESLEKİ YABANCI DİL 11.pdf"
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