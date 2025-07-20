import sys
sys.path.append('.')
from extract_olcme import extract_olcme_degerlendirme_from_pdf
import os

# Problematik dosyalar
problem_files = [
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/28_Laboratuvar_Hizmetleri/laboratuvar_11/İMMÜNOLOJİ VE SEROLOJİ-SEÇMELİ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/25_Kimya_Teknolojisi/KİMYA TEKNOLOJİSİ/11_DBF_ZORUNLU/ENSTRÜMANTAL ANALİZ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/28_Laboratuvar_Hizmetleri/laboratuvar_11/HAYVAN SAĞ.LABORATUVARI-11.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/06_Buro_Yonetimi_ve_Yonetici_Asistanligi/buro-1/9.SINIF/BÜRO TEKNOLOJİLERİ DBF.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/11_Endustriyel_Otomasyon_Teknolojileri/ENDÜSTRİYEL OTOMASYON TEKNOLOJİLERİ/10. SINIF/004_10_MODELLEME_VE_MONTAJ_DBF.pdf"
]

for i, pdf_path in enumerate(problem_files, 1):
    if os.path.exists(pdf_path):
        print(f"\n{'='*100}")
        print(f"DOSYA {i}/{len(problem_files)}: {os.path.basename(pdf_path)}")
        print(f"Dizin: {os.path.dirname(pdf_path).replace('/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/', '')}")
        print(f"{'='*100}")
        
        olcme_text = extract_olcme_degerlendirme_from_pdf(pdf_path)
        
        print(f"ÖLÇME VE DEĞERLENDİRME METNİ:")
        print(f"{'-'*80}")
        print(olcme_text)
        print(f"{'-'*80}")
    else:
        print(f"❌ Dosya bulunamadı: {pdf_path}")