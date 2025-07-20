import PyPDF2
import re
import os

def debug_pdf_content(pdf_path):
    """PDF dosyasının içeriğini debug eder"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"\n🔍 Dosya: {os.path.basename(pdf_path)}")
            print(f"📄 Sayfa sayısı: {len(pdf_reader.pages)}")
            
            full_text = ""
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                full_text += page_text + "\n"
                print(f"Sayfa {i+1} karakter sayısı: {len(page_text)}")
            
            print(f"📊 Toplam karakter sayısı: {len(full_text)}")
            
            # ÖLÇME kelimesini ara
            if "ÖLÇME" in full_text.upper():
                print("✅ 'ÖLÇME' kelimesi bulundu")
                
                # ÖLÇME VE DEĞERLENDİRME'nin etrafındaki metni göster
                lines = full_text.split('\n')
                for i, line in enumerate(lines):
                    if "ÖLÇME VE DEĞERLENDİRME" in line.upper():
                        print(f"\n🎯 'ÖLÇME VE DEĞERLENDİRME' satır {i+1}'de bulundu")
                        print("📝 Önceki 3 satır:")
                        for j in range(max(0, i-3), i):
                            if j < len(lines):
                                print(f"  {j+1}: '{lines[j].strip()}'")
                        print(f"📝 Hedef satır:")
                        print(f"  {i+1}: '{line.strip()}'")
                        print("📝 Sonraki 10 satır:")
                        for j in range(i+1, min(i+11, len(lines))):
                            if j < len(lines):
                                print(f"  {j+1}: '{lines[j].strip()}'")
                        break
                else:
                    # Sadece ÖLÇME kelimesini ara
                    for i, line in enumerate(lines):
                        if "ÖLÇME" in line.upper():
                            print(f"\n🔍 'ÖLÇME' içeren satır {i+1}: '{line.strip()}'")
                            print("📝 Sonraki 5 satır:")
                            for j in range(i+1, min(i+6, len(lines))):
                                if j < len(lines):
                                    print(f"  {j+1}: '{lines[j].strip()}'")
                            break
            else:
                print("❌ 'ÖLÇME' kelimesi bulunamadı")
                # İlk 1000 karakteri göster
                preview = full_text[:1000].replace('\n', ' ')
                print(f"📝 İlk 1000 karakter: {preview}")
            
            print("-" * 100)
            
    except Exception as e:
        print(f"❌ Hata: {str(e)}")

# Test dosyaları
test_files = [
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/28_Laboratuvar_Hizmetleri/laboratuvar_11/İMMÜNOLOJİ VE SEROLOJİ-SEÇMELİ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/25_Kimya_Teknolojisi/KİMYA TEKNOLOJİSİ/11_DBF_ZORUNLU/ENSTRÜMANTAL ANALİZ.pdf",
    "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/06_Buro_Yonetimi_ve_Yonetici_Asistanligi/buro-1/9.SINIF/BÜRO TEKNOLOJİLERİ DBF.pdf"
]

for pdf_file in test_files:
    if os.path.exists(pdf_file):
        debug_pdf_content(pdf_file)
    else:
        print(f"❌ Dosya bulunamadı: {pdf_file}")