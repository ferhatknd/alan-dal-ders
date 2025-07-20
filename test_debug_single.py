import PyPDF2
import re
import os

def debug_extract_olcme_degerlendirme_from_pdf(pdf_path):
    """PDF dosyasından ÖLÇME VE DEĞERLENDİRME bölümünü çıkarır - debug version"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            # Tüm sayfaları oku
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # Normalizasyon: fazla boşlukları temizle
            full_text = re.sub(r'\s+', ' ', full_text)
            
            # ÖLÇME kelimesini ara
            if "ÖLÇME" in full_text.upper():
                lines = full_text.split('\n')
                
                # ÖLÇME VE DEĞERLENDİRME başlığını bul (birden fazla satıra yayılmış olabilir)
                start_idx = -1
                
                # Önce tam ifadeyi ara
                for i, line in enumerate(lines):
                    if "ÖLÇME VE DEĞERLENDİRME" in line.upper():
                        start_idx = i
                        print(f"🎯 Tam ifade bulundu satır {i}: '{line.strip()}'")
                        break
                
                # Bulamazsa, ÖLÇME VE ve DEĞERLENDİRME'yi ayrı satırlarda ara
                if start_idx == -1:
                    for i, line in enumerate(lines):
                        if "ÖLÇME VE" in line.upper():
                            print(f"🔍 'ÖLÇME VE' bulundu satır {i}: '{line.strip()}'")
                            # Sonraki birkaç satırda DEĞERLENDİRME var mı bak
                            for j in range(i+1, min(i+4, len(lines))):
                                if j < len(lines) and "DEĞERLENDİRME" in lines[j].upper():
                                    start_idx = j  # DEĞERLENDİRME satırından başla
                                    print(f"🎯 'DEĞERLENDİRME' bulundu satır {j}: '{lines[j].strip()}'")
                                    break
                            if start_idx != -1:
                                break
                
                if start_idx >= 0:
                    print(f"📝 Başlangıç indeksi: {start_idx}")
                    
                    # ÖLÇME VE DEĞERLENDİRME'den sonraki metni topla (kısa format)
                    result_lines = []
                    
                    # ÖLÇME VE DEĞERLENDİRME başlığından sonraki 10-15 satırı kontrol et
                    for j in range(start_idx + 1, min(start_idx + 15, len(lines))):
                        if j >= len(lines):
                            break
                            
                        current_line = lines[j].strip()
                        print(f"  Satır {j}: '{current_line}' (Uzunluk: {len(current_line)})")
                        
                        # Boş satırları atla
                        if not current_line:
                            continue
                        
                        # Yeni büyük başlık gelirse dur (ARAÇ-GEREÇ, KAYNAKÇA, DERSİN KAZANIM TABLOSU vb.)
                        if (current_line.isupper() and len(current_line) > 10 and 
                            any(keyword in current_line for keyword in ["ARAÇ", "GEREÇ", "KAYNAK", "DERSİN UYGULANMASINA", "UYGULAMA FAALİYETLERİ", "DERSİN KAZANIM TABLOSU", "ÖĞRENME BİRİMİ"])):
                            print(f"  ⛔ Büyük başlık bulundu, dur: '{current_line}'")
                            break
                        
                        # Değerlendirme metni olabilecek satırları topla
                        if (len(current_line) > 15 and 
                            (any(keyword in current_line.lower() for keyword in ["derste", "öğrenci", "değerlendirme", "ölçme", "performans", "gözlem", "form", "puanlama", "akran", "belirlenen", "hedef"]) or
                             "bu derste" in current_line.lower())):
                            print(f"  ✅ İçerik satırı eklendi: '{current_line[:100]}...'")
                            result_lines.append(current_line)
                        else:
                            print(f"  ❌ İçerik kriterleri karşılamadı")
                        
                        # Yeterli metin toplandıysa dur (2-3 satır yeterli)
                        if len(result_lines) >= 2:
                            print(f"  ✅ Yeterli satır toplandı ({len(result_lines)})")
                            break
                    
                    print(f"📊 Toplanan satır sayısı: {len(result_lines)}")
                    
                    if result_lines:
                        # Toplanan satırları birleştir
                        result = ' '.join(result_lines)
                        
                        # Temizlik
                        result = re.sub(r'\s+', ' ', result)  # Fazla boşlukları temizle
                        
                        # Çok uzun ise kısalt (400 karakter limit)
                        if len(result) > 400:
                            result = result[:400].rsplit(' ', 1)[0] + "..."
                        
                        return result.strip()
                
            return "ÖLÇME VE DEĞERLENDİRME bölümü bulunamadı"
    except Exception as e:
        return f"Hata: {str(e)}"

# Test et
test_file = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf/06_Buro_Yonetimi_ve_Yonetici_Asistanligi/buro-1/9.SINIF/BÜRO TEKNOLOJİLERİ DBF.pdf"

if os.path.exists(test_file):
    print(f"🔍 Test dosyası: {os.path.basename(test_file)}")
    print("="*80)
    result = debug_extract_olcme_degerlendirme_from_pdf(test_file)
    print("="*80)
    print(f"📋 SONUÇ: {result}")
else:
    print(f"❌ Dosya bulunamadı: {test_file}")