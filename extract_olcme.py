import fitz  # PyMuPDF
import re
import os
import sys
import random
import glob

# Suppress warnings for cleaner output
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import warnings
warnings.filterwarnings("ignore", message=".*resume_download.*")
warnings.filterwarnings("ignore", message=".*torch.load.*")


def extract_fields_from_text(text):
    # Varyasyonlarla case-sensitive yapı
    patterns = [
        (["DERSİN ADI", "ADI"], ["DERSİN", "DERSĠN"]),                                  # Dersin Adı
        (["DERSİN SINIFI", "SINIFI"], ["DERSİN", "DERSĠN"]),                            # Sinifi (metin olarak)!!
        (["DERSİN SÜRESİ", "SÜRESİ"], ["DERSİN", "DERSĠN"]),                            # Süre/Ders saati (metin olarak)!!
        (["DERSİN AMACI", "AMACI"], ["DERSİN", "DERSĠN"]),                              # Dersin Amacı
        (["DERSİN KAZANIMLARI", "KAZANIMLARI"], ["EĞİTİM", "EĞĠTĠM", "EĞ", "DONAT"]),   # Kazanım -> Madde yapılmalı
        (["DONANIMI"], ["ÖLÇ", "DEĞERLENDİRME"]),                                       # Ortam/Donanım
        (["DEĞERLENDİRME"], ["DERSİN", "DERSĠN", "KAZANIM", "ÖĞRENME"]),                # Ölçme-Değerlendirme
    ]
    result = {}

    for i, (start_keys, end_keys) in enumerate(patterns, 1):
        start_index = None
        start_match = ""
        for sk in start_keys:
            idx = text.find(sk)
            if idx != -1 and (start_index is None or idx < start_index):
                start_index = idx + len(sk)
                start_match = sk
        if start_index is None:
            continue
        end_index = None
        for ek in end_keys:
            idx = text.find(ek, start_index)
            if idx != -1 and (end_index is None or idx < end_index):
                end_index = idx
        if end_index is not None:
            section = text[start_index:end_index].strip()
        else:
            section = text[start_index:].strip()
        section = re.sub(r'\s+', ' ', section)
        result[f"Case{i}_{start_match}"] = section
    return result

def extract_kazanim_sayisi_sure_tablosu(pdf_path):
    """PDF'den KAZANIM SAYISI VE SÜRE TABLOSU'nu çıkarır ve formatlı string döndürür"""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        
        for page in doc:
            full_text += page.get_text() + "\n"
        
        doc.close()
        
        # Normalizasyon
        full_text = re.sub(r'\s+', ' ', full_text)
        
        # KAZANIM SAYISI VE SÜRE TABLOSU bölümünü bul (varyasyonlarla)
        table_start_patterns = [
            "KAZANIM SAYISI VE SÜRE TABLOSU",
            "DERSİN KAZANIM TABLOSU",
            "TABLOSU",
            "TABLOS U",
            "TABLO SU",
            "TABL OSU",
            "TAB LOSU",
            "TA BLOSU"
        ]
        
        # Tüm pattern'leri kontrol et ve en erken başlayanı bul
        earliest_start = None
        earliest_idx = len(full_text)
        table_start = None
        
        for pattern in table_start_patterns:
            if pattern in full_text:
                idx = full_text.find(pattern)
                if idx < earliest_idx:
                    earliest_idx = idx
                    earliest_start = idx + len(pattern)
                    table_start = pattern
        
        start_idx = earliest_start
        
        if table_start is None:
            return "KAZANIM SAYISI VE SÜRE TABLOSU bulunamadı"
        
        # Bitiş noktasını bul
        end_markers = ["TOPLAM", "ÖĞRENME BİRİMİ"]
        end_idx = len(full_text)
        for marker in end_markers:
            idx = full_text.find(marker, start_idx + 50)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        
        table_section = full_text[start_idx:end_idx].strip()
        
        # TOPLAM satırını bul ve sonrasını kes
        if "TOPLAM" in table_section:
            toplam_idx = table_section.find("TOPLAM")
            # TOPLAM'dan sonra sayıları bul ve ondan sonrasını kes
            after_toplam = table_section[toplam_idx:]
            # TOPLAM satırının sonunu bul (genelde 100 ile biter)
            toplam_end = re.search(r'TOPLAM.*?100', after_toplam)
            if toplam_end:
                table_section = table_section[:toplam_idx + toplam_end.end()]
        
        # Başlık satırını kaldır (ÖĞRENME BİRİMİ KAZANIM SAYISI DERS SAATİ ORAN)
        header_pattern = r'ÖĞRENME BİRİMİ.*?ORAN.*?\(\s*%\s*\)'
        table_section = re.sub(header_pattern, '', table_section).strip()
        
        # Satırları ayır ve parse et
        lines = []
        
        # Her satır: İsim + 2 sayı + 1 sayı veya % pattern'i
        patterns = [
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s*/\s*(\d+)\s+(\d+(?:[,\.]\d+)?)', # Kesirli format + oran
            r'([^0-9]+?)\s+(\d+)\s+(\d+)\s+(\d+(?:[,\.]\d+)?)',             # Normal format + oran
            r'([^0-9]+?)\s+(\d+)\s+(\d+)(?:\s|$)'                           # Sadece 2 sütun (oran yok)
        ]

        matches = []
        for pattern in patterns:
            matches = re.findall(pattern, table_section)
            if matches:
                break
        
        for match in matches:
            ogrenme_birimi = match[0].strip()
            kazanim_sayisi = match[1]

            # Pattern'e göre ders saati ve oran belirleme
            if len(match) == 3:  # Oran yok
                ders_saati = match[2]
                oran = "-"  # Boş oran için
            elif len(match) == 4:  # Normal format
                ders_saati = match[2]
                oran = match[3]
            elif len(match) == 5:  # Kesirli format
                ders_saati = match[3]  # / sonrası sayı
                oran = match[4]
            
            # Öğrenme birimi adını temizle
            ogrenme_birimi = re.sub(r'\s+', ' ', ogrenme_birimi).strip()
            
            # TOPLAM satırını atla
            if ogrenme_birimi.upper() != "TOPLAM":
                line = f"{ogrenme_birimi}, {kazanim_sayisi}, {ders_saati}, {oran}"
                lines.append(line)
        
        if lines:
            result = "KAZANIM SAYISI VE SÜRE TABLOSU:\n"
            for idx, line in enumerate(lines, 1):
                result += f"{idx}-{line}\n"
            return result.strip()
        else:
            return "Tablo verileri parse edilemedi"
                
    except Exception as e:
        return f"Hata: {str(e)}"

def extract_ob_tablosu(pdf_path):
    """PDF'den Öğrenme Birimi Alanını çıkarır - Sadece başlangıç ve bitiş sınırları arasındaki metni"""
    import time
    
    print(f"\n🔄 EXTRACT_OB_TABLOSU PROCESSING: {os.path.basename(pdf_path)}")
    print("=" * 60)
    total_start = time.time()
    
    try:
        # Step 1: PDF Reading
        step1_start = time.time()
        doc = fitz.open(pdf_path)
        full_text = ""
        
        for page in doc:
            full_text += page.get_text() + "\n"
        
        doc.close()
        
        step1_time = time.time() - step1_start
        print(f"📄 Step 1 - PDF Reading: {step1_time:.3f}s ({len(full_text)} chars)")
        
        # Step 2: Text Normalization
        step2_start = time.time()
        full_text = re.sub(r'\s+', ' ', full_text)
        step2_time = time.time() - step2_start
        print(f"🔧 Step 2 - Text Normalization: {step2_time:.3f}s")
        
        # Step 3: Area Extraction (Before BERT for efficiency)
        step3_start = time.time()
        
        # TOPLAM metnini bul (ana başlangıç noktası) - case insensitive
        toplam_idx = full_text.upper().find("TOPLAM")
        
        # Backup plan: If TOPLAM not found, look for "100" (total percentage)
        if toplam_idx == -1:
            print("⚠️  TOPLAM not found, trying backup search for '100'...")
            
            # Find all occurrences of "100" 
            backup_positions = []
            search_pos = 0
            while True:
                pos = full_text.find("100", search_pos)
                if pos == -1:
                    break
                backup_positions.append(pos)
                search_pos = pos + 1
            
            if not backup_positions:
                return "Öğrenme Birimi Alanı - TOPLAM metni bulunamadı ve '100' backup da bulunamadı"
            
            # Check each "100" position for validity
            for pos in backup_positions:
                # Check the context around "100" (within 9 chars before and after)
                start_check = max(0, pos - 9)
                end_check = min(len(full_text), pos + 9)
                context = full_text[start_check:end_check]
                
                print(f"🔍 Checking '100' at position {pos}: '{context}'")
                
                # Look for table headers after this "100"
                search_start = pos + 3  # Start after "100"
                search_end = min(len(full_text), search_start + 200)  # Search within 200 chars
                search_area = full_text[search_start:search_end]
                
                # Check if any table header appears within reasonable distance
                table_headers_check = [
                    "ÖĞRENME BİRİMİ",
                    "KONULAR", 
                    "ÖĞRENME BİRİMİ KAZANIMLARI",
                    "KAZANIM AÇIKLAMLARI",
                    "AÇIKLAMALARI"
                ]
                
                header_found = False
                for header in table_headers_check:
                    if header in search_area:
                        toplam_idx = pos
                        header_found = True
                        print(f"✅ Backup match found! Using '100' at position {pos} (found header: {header})")
                        break
                
                if header_found:
                    break
            
            # If still no valid match found
            if toplam_idx == -1:
                return "Öğrenme Birimi Alanı - TOPLAM metni bulunamadı ve '100' backup da geçerli eşleşme vermedi"
        
        # TOPLAM'dan sonra başlangıç kelimeleri ara
        table_headers = [
            "ÖĞRENME BİRİMİ",
            "KONULAR", 
            "ÖĞRENME BİRİMİ KAZANIMLARI",
            "KAZANIM AÇIKLAMLARI",
            "AÇIKLAMALARI"
        ]
        
        # TOPLAM'dan sonra başlangıç pozisyonunu bul (en son bulunan başlığın sonundan itibaren)
        table_start_idx = None
        last_header_end = None
        
        for header in table_headers:
            idx = full_text.find(header, toplam_idx)
            if idx != -1:
                header_end = idx + len(header)
                if last_header_end is None or header_end > last_header_end:
                    last_header_end = header_end
                    table_start_idx = header_end
        
        if table_start_idx is None:
            return "Öğrenme Birimi Alanı - Başlangıç kelimeleri bulunamadı"
        
        # Bitiş kelimeleri - herhangi birini bulduğunda bitir
        stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
        table_end_idx = len(full_text)
        
        for stop_word in stop_words:
            stop_idx = full_text.find(stop_word, table_start_idx)
            if stop_idx != -1 and stop_idx < table_end_idx:
                table_end_idx = stop_idx
        
        # Belirlenen alan içindeki metni al
        ogrenme_birimi_alani = full_text[table_start_idx:table_end_idx].strip()
        
        step3_time = time.time() - step3_start
        print(f"📍 Step 3 - Area Extraction: {step3_time:.3f}s ({len(ogrenme_birimi_alani)} chars)")
        
        # Step 4: BERT Text Correction (Only on OB section for efficiency)
        step4_start = time.time()
        
        # Display text preview before BERT processing (on OB section only)
        if len(ogrenme_birimi_alani) > 400:
            preview_text = f"OB Section First 200: '{ogrenme_birimi_alani[:200]}'\nOB Section Last 200: '{ogrenme_birimi_alani[-200:]}'"
        else:
            preview_text = f"OB Section ({len(ogrenme_birimi_alani)} chars): '{ogrenme_birimi_alani}'"
        
        print(f"🔍 Step 4 - BERT Input Preview (OB Section Only):\n{preview_text}")
        
        # Step 4: Basic Text Normalization (BERT removed)
        ogrenme_birimi_alani = re.sub(r'\s+', ' ', ogrenme_birimi_alani).strip()
        step4_time = time.time() - step4_start
        print(f"🔧 Step 4 - Basic Text Normalization: {step4_time:.3f}s")
        
        # Display normalized text preview
        if len(ogrenme_birimi_alani) > 400:
            normalized_preview = f"Normalized OB First 200: '{ogrenme_birimi_alani[:200]}'\nNormalized OB Last 200: '{ogrenme_birimi_alani[-200:]}'"
        else:
            normalized_preview = f"Normalized OB Section ({len(ogrenme_birimi_alani)} chars): '{ogrenme_birimi_alani}'"
        
        print(f"✅ Step 4 - Normalization Output Preview (OB Section):\n{normalized_preview}")
        
        # Step 5: Kazanım Table Processing
        step5_start = time.time()
        kazanim_tablosu_result = extract_kazanim_sayisi_sure_tablosu(pdf_path)
        step5_time = time.time() - step5_start
        print(f"📊 Step 5 - Kazanım Table Processing: {step5_time:.3f}s")
        
        # Step 6: String Matching Processing
        step6_start = time.time()
        header_match_info = ""
        formatted_content = ""
        
        if "KAZANIM SAYISI VE SÜRE TABLOSU:" in kazanim_tablosu_result:
            # Tablo satırlarını al
            lines = kazanim_tablosu_result.split('\n')[1:]  # İlk satır başlık, onu atla
            
            header_match_info = "\n"
            formatted_content_parts = []
            all_matched_headers = []  # Tüm eşleşen başlıkların pozisyon bilgileri
            
            # Önce tüm eşleşen başlıkları topla (sadece pozisyon bilgileri için)
            for line in lines:
                if line.strip() and '-' in line:
                    parts = line.split('-', 1)[1].split(',')
                    if parts:
                        baslik = parts[0].strip()
                        
                        # Simple text normalization (BERT removed)
                        baslik_for_matching = re.sub(r'\s+', ' ', baslik.strip())
                        
                        try:
                            konu_sayisi_int = int(parts[1].strip())
                        except (ValueError, IndexError):
                            konu_sayisi_int = 0
                        
                        # Bu başlığın geçerli eşleşmelerini bul - Doğrudan semantic matching
                        start_pos = 0
                        
                        while True:
                            # Use simple case-insensitive string matching (BERT removed)
                            baslik_upper = baslik_for_matching.upper()
                            content_upper = ogrenme_birimi_alani[start_pos:].upper()
                            string_idx = content_upper.find(baslik_upper)
                            if string_idx >= 0:
                                idx = start_pos + string_idx
                            else:
                                break
                            
                            after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                            if konu_sayisi_int > 0:
                                found_numbers = 0
                                for rakam in range(1, konu_sayisi_int + 1):
                                    if str(rakam) in after_baslik[:500]:
                                        found_numbers += 1
                                
                                if found_numbers == konu_sayisi_int:
                                    all_matched_headers.append({
                                        'title': baslik,
                                        'position': idx,
                                        'konu_sayisi': konu_sayisi_int
                                    })
                                    break  # İlk geçerli eşleşmeyi bulduk
                            
                            start_pos = idx + 1
                
            # Şimdi başlıkları işle ve header_match_info oluştur (tek kez)
            for line in lines:
                if line.strip() and '-' in line:
                    # Satır formatı: "1-Başlık, kazanim_sayisi, ders_saati, oran"
                    # Extract line number from the beginning
                    line_number = line.split('-')[0].strip()
                    parts = line.split('-', 1)[1].split(',')
                    if parts:
                        baslik = parts[0].strip()
                        
                        # Simple text normalization (BERT removed)
                        baslik_for_display = baslik
                        baslik_for_matching = re.sub(r'\s+', ' ', baslik.strip())
                        
                        # Konu sayısını al
                        konu_sayisi_str = parts[1].strip() if len(parts) > 1 else "?"
                        
                        # Geçerli eşleşmeleri kontrol et
                        try:
                            konu_sayisi_int = int(konu_sayisi_str)
                        except ValueError:
                            konu_sayisi_int = 0
                        
                        gecerli_eslesme = 0
                        
                        # Her potansiyel eşleşmeyi kontrol et - Doğrudan semantic matching
                        start_pos = 0
                        while True:
                            # Use simple case-insensitive string matching (BERT removed)
                            baslik_upper = baslik_for_matching.upper()
                            content_upper = ogrenme_birimi_alani[start_pos:].upper()
                            string_idx = content_upper.find(baslik_upper)
                            if string_idx >= 0:
                                idx = start_pos + string_idx
                            else:
                                break
                            
                            # Başlıktan sonraki metni al
                            after_baslik = ogrenme_birimi_alani[idx + len(baslik):]
                            
                            # Konu sayısı kadar rakamı kontrol et
                            if konu_sayisi_int > 0:
                                found_numbers = 0
                                for rakam in range(1, konu_sayisi_int + 1):
                                    if str(rakam) in after_baslik[:500]:  # İlk 500 karakterde ara
                                        found_numbers += 1
                                
                                # Tüm rakamlar bulunduysa geçerli eşleşme
                                if found_numbers == konu_sayisi_int:
                                    gecerli_eslesme += 1
                            
                            start_pos = idx + 1
                        
                        header_match_info += f"{line_number}-{baslik_for_display} ({konu_sayisi_str}) -> {gecerli_eslesme} eşleşme\n"
                        
                        # Eğer geçerli eşleşme yoksa alternatif arama yap
                        if gecerli_eslesme == 0 and konu_sayisi_int > 0:
                            # Son eşleşen başlıktan sonra "1" rakamını ara
                            alternative_match = extract_ob_tablosu_konu_bulma_yedek_plan(
                                ogrenme_birimi_alani, baslik_for_matching, konu_sayisi_int
                            )
                            if alternative_match:
                                gecerli_eslesme = 1
                                header_match_info = header_match_info.replace(
                                    f"{line_number}-{baslik_for_display} ({konu_sayisi_str}) -> 0 eşleşme\n",
                                        f"{line_number}-{baslik_for_display} ({konu_sayisi_str}) -> 1 eşleşme (alternatif)\n"
                                    )
                        
                        # Geçerli eşleşme varsa, detaylı doğrulama yap
                        if gecerli_eslesme > 0:
                            # Kazanım tablosundan konu sayısını al
                            konu_sayisi = None
                            if len(parts) > 1:
                                try:
                                    konu_sayisi = int(parts[1].strip())
                                except ValueError:
                                    konu_sayisi = None
                            
                            # İlk geçerli eşleşmeyi bul - Doğrudan semantic matching
                            start_pos = 0
                            first_valid_match_found = False
                            
                            while True:
                                # Use simple case-insensitive string matching
                                baslik_upper = baslik_for_matching.upper()
                                content_upper = ogrenme_birimi_alani[start_pos:].upper()
                                string_idx = content_upper.find(baslik_upper)
                                if string_idx >= 0:
                                    idx = start_pos + string_idx
                                else:
                                    break
                                
                                # Başlıktan sonraki metni al ve geçerlilik kontrol et
                                after_baslik = ogrenme_birimi_alani[idx + len(baslik_for_matching):]
                                
                                # Konu sayısı kadar rakamı kontrol et (BERT-uyumlu pattern matching)
                                is_valid_match = True
                                if konu_sayisi and konu_sayisi > 0:
                                    found_numbers = 0
                                    for rakam in range(1, konu_sayisi + 1):
                                        # BERT-corrected text için pattern matching kullan
                                        # "1. Topic" veya "1 Topic" formatlarını arar
                                        patterns = [f"{rakam}. ", f"{rakam} "]
                                        pattern_found = False
                                        for pattern in patterns:
                                            if pattern in after_baslik[:500]:
                                                pattern_found = True
                                                break
                                        if pattern_found:
                                            found_numbers += 1
                                    is_valid_match = (found_numbers == konu_sayisi)
                                
                                # Sadece ilk geçerli eşleşmeyi işle
                                if is_valid_match and not first_valid_match_found:
                                    first_valid_match_found = True
                                    
                                    # Detaylı doğrulama yap
                                    validation_result = ""
                                    if konu_sayisi:
                                        validation_result = extract_ob_tablosu_konu_sinirli_arama(
                                            ogrenme_birimi_alani, idx, baslik_for_matching, konu_sayisi, all_matched_headers
                                        )
                                    
                                    formatted_content_parts.append(
                                        f"{line_number}-{baslik_for_display} ({konu_sayisi}) -> 1. Eşleşme\n"
                                        f"{validation_result}\n"
                                    )
                                    break  # İlk geçerli eşleşmeyi bulduk, çık
                                
                                start_pos = idx + 1
                
                # Eğer eşleşmeler varsa onları göster, yoksa eski formatı kullan
                if formatted_content_parts:
                    formatted_content = "\n".join(formatted_content_parts)
                else:
                    # Hiç eşleşme yoksa eski formatı kullan
                    if len(ogrenme_birimi_alani) <= 400:
                        formatted_content = ogrenme_birimi_alani
                    else:
                        first_200 = ogrenme_birimi_alani[:200]
                        last_200 = ogrenme_birimi_alani[-200:]
                        formatted_content = f"{first_200}\n...\n{last_200}"
        else:
            # Kazanım tablosu bulunamadıysa eski formatı kullan
            if len(ogrenme_birimi_alani) <= 400:
                formatted_content = ogrenme_birimi_alani
            else:
                first_200 = ogrenme_birimi_alani[:200]
                last_200 = ogrenme_birimi_alani[-200:]
                formatted_content = f"{first_200}\n...\n{last_200}"
        
        step6_time = time.time() - step6_start
        print(f"🎯 Step 6 - String Matching Processing: {step6_time:.3f}s")
        
        # Step 7: Results Formatting and Final Statistics
        step7_start = time.time()
        result = f"{'-'*50}\nÖğrenme Birimi Alanı:{header_match_info}{'-'*50}\n{formatted_content}"
        step7_time = time.time() - step7_start
        print(f"📋 Step 7 - Results Formatting: {step7_time:.3f}s")
        
        # Final timing statistics
        total_time = time.time() - total_start
        print(f"\n⚡ TOTAL PROCESSING TIME: {total_time:.3f}s")
        print("=" * 60)
        print("📊 PERFORMANCE BREAKDOWN:")
        print(f"📄 PDF Reading: {step1_time:.3f}s ({step1_time/total_time*100:.1f}%)")
        print(f"🔧 Text Normalization: {step2_time:.3f}s ({step2_time/total_time*100:.1f}%)")
        print(f"📍 Area Extraction: {step3_time:.3f}s ({step3_time/total_time*100:.1f}%)")
        print(f"🔧 Basic Text Normalization: {step4_time:.3f}s ({step4_time/total_time*100:.1f}%)")
        print(f"📊 Kazanım Table Processing: {step5_time:.3f}s ({step5_time/total_time*100:.1f}%)")
        print(f"🎯 String Matching Processing: {step6_time:.3f}s ({step6_time/total_time*100:.1f}%)")
        print(f"📋 Results Formatting: {step7_time:.3f}s ({step7_time/total_time*100:.1f}%)")
        
        if step6_time > 20:
            print(f"\n⚠️  BOTTLENECK IDENTIFIED: String matching taking {step6_time:.1f}s (>{step6_time/total_time*100:.0f}% of total time)")
            print("💡 OPTIMIZATION TARGET: String matching algorithms")
        elif total_time > 30:
            print(f"\n⚠️  PERFORMANCE WARNING: Total processing time {total_time:.1f}s >30s")
        else:
            print(f"\n✅ PERFORMANCE ACCEPTABLE: {total_time:.1f}s total processing time")
        
        print("=" * 60)
        
        return result
            
    except Exception as e:
        return f"Hata: {str(e)}"

def extract_ob_tablosu_konu_sinirli_arama(text, baslik_idx, baslik, konu_sayisi, all_matched_headers=None):
    """Başlık eşleşmesinden sonra konu yapısını sıralı rakamlarla doğrular - 2 döngü"""
    import re
    
    # Başlık eşleşmesinden sonraki tüm metni al
    after_baslik = text[baslik_idx + len(baslik):]
    
    # Sonraki eşleşen başlığın pozisyonunu bul (eğer varsa)
    next_matched_header_pos = len(after_baslik)
    
    if all_matched_headers:
        current_pos_in_text = baslik_idx + len(baslik)
        
        for other_header_info in all_matched_headers:
            other_pos = other_header_info.get('position', -1)
            # Bu başlıktan sonra gelen eşleşen başlıkları ara
            if other_pos > current_pos_in_text:
                relative_pos = other_pos - current_pos_in_text
                if relative_pos < next_matched_header_pos:
                    next_matched_header_pos = relative_pos
    
    # Eğer sonraki eşleşen başlık yoksa, genel pattern'leri ara
    if next_matched_header_pos == len(after_baslik):
        next_header_patterns = [
            r'\n[A-ZÜĞIŞÖÇ][A-ZÜĞIŞÖÇ\s]{10,}',
            r'\n\d+\.\s*[A-ZÜĞIŞÖÇ]', 
            r'DERSİN|DERSĠN',
            r'UYGULAMA|FAALİYET|TEMRİN'
        ]
        
        for pattern in next_header_patterns:
            match = re.search(pattern, after_baslik)
            if match and match.start() < next_matched_header_pos:
                next_matched_header_pos = match.start()
    
    work_area = after_baslik[:next_matched_header_pos]
    validation_info = []
    
    # TEK DÖNGÜ ÇALISTIR
    current_pos = 0
    for konu_no in range(1, konu_sayisi + 1):
        konu_str = str(konu_no)
        
        # Madde numarası pattern'lerini dene: "1. " veya "1 "
        patterns = [f"{konu_str}. ", f"{konu_str} "]
        found_pos = -1
        for pattern in patterns:
            pos = work_area.find(pattern, current_pos)
            if pos != -1:
                found_pos = pos
                break
        
        if found_pos != -1:
            # Sonraki rakama kadar olan metni al
            if konu_no < konu_sayisi:
                next_konu_str = str(konu_no + 1)
                # Sonraki madde numarasını da pattern ile ara
                next_patterns = [f"{next_konu_str}. ", f"{next_konu_str} "]
                next_found_pos = -1
                for next_pattern in next_patterns:
                    pos = work_area.find(next_pattern, found_pos + 1)
                    if pos != -1:
                        next_found_pos = pos
                        break
                if next_found_pos != -1:
                    konu_content = work_area[found_pos:next_found_pos].strip()
                else:
                    konu_content = work_area[found_pos:].strip()
            else:
                konu_content = work_area[found_pos:].strip()
            
            # Sadece gerçek konu numarasını temizle (tarihleri koruyarak)
            cleaned_content = konu_content.strip()
            
            # Pattern ile bulduğumuz madde numarasını temizle
            if cleaned_content.startswith(f"{konu_no}. "):
                cleaned_content = cleaned_content.replace(f"{konu_no}. ", "", 1)
            elif cleaned_content.startswith(f"{konu_no} "):
                cleaned_content = cleaned_content.replace(f"{konu_no} ", "", 1)
            
            validation_info.append(f"{konu_no}. {cleaned_content.strip()}")
            current_pos = found_pos + 1
        else:
            current_pos += 1
    
    return "\n".join(validation_info)

def extract_ob_tablosu_konu_bulma_yedek_plan(text, original_baslik, konu_sayisi):
    """Son eşleşen başlıktan sonra '1' rakamını bulup alternatif eşleşme arar"""
    import re
    
    # "1" rakamını ara (cümle başında veya nokta sonrası)
    one_pattern = r'(?:^|\.|\\n|\\s)1(?:\.|\\s)'
    matches = list(re.finditer(one_pattern, text))
    
    if not matches:
        return None
    
    # Her "1" pozisyonu için kontrol et
    for match in matches:
        one_pos = match.start()
        
        # "1" den önceki cümleyi bul (maksimum 100 karakter geriye git)
        start_search = max(0, one_pos - 100)
        before_one = text[start_search:one_pos]
        
        # Cümle başlangıcını bul (büyük harf ile başlayan kelimeler)
        sentences = re.split(r'[.!?]', before_one)
        if sentences:
            potential_title = sentences[-1].strip()
            
            # Potansiyel başlık çok kısaysa atla
            if len(potential_title) < 10:
                continue
                
            # "1" den sonra konu sayısı kadar rakamı kontrol et
            after_one = text[one_pos:]
            found_numbers = 0
            for rakam in range(1, konu_sayisi + 1):
                if str(rakam) in after_one[:500]:  # İlk 500 karakterde ara
                    found_numbers += 1
            
            # Tüm rakamlar bulunduysa alternatif eşleşme geçerli
            if found_numbers == konu_sayisi:
                return {
                    'title': potential_title,
                    'position': one_pos,
                    'numbers_found': found_numbers
                }
    
    return None

## Yardımcı fonksiyonlar ##
def find_all_pdfs_in_dbf_directory():
    """data/dbf dizinindeki tüm PDF dosyalarını bulur"""
    base_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf"
    
    # Tüm PDF dosyalarını bul
    pdf_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    
    return pdf_files

def find_pdf_by_name(filename):
    """data/dbf dizininde dosya adına göre ilk eşleşen PDF'i bulur"""
    base_path = "/Users/ferhat/Library/Mobile Documents/com~apple~CloudDocs/Projeler/ProjectDogru/repos/alan-dal-ders/data/dbf"
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith('.pdf') and filename.lower() in file.lower():
                return os.path.join(root, file)
    return None


# Debug için full text body verir.
def print_full_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    doc.close()
    print(full_text)

def main():
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) != 2:
        print("Kullanım:")
        print("  python extract_olcme.py <sayı>        # Rastgele N dosya")
        print("  python extract_olcme.py \"dosya_adi\"   # Belirli dosya")
        sys.exit(1)
    
    param = sys.argv[1]
    
    try:
        sample_count = int(param)
        # Sayı ise rastgele seçim
        if sample_count <= 0:
            print("Hata: Sayı parametresi pozitif bir tam sayı olmalıdır.")
            sys.exit(1)
        
        all_pdfs = find_all_pdfs_in_dbf_directory()
        
        if not all_pdfs:
            print("data/dbf dizininde hiç PDF dosyası bulunamadı.")
            sys.exit(1)
           
        # Rastgele örnekleme yap
        if sample_count > len(all_pdfs):
            print(f"Uyarı: İstenen sayı ({sample_count}) toplam dosya sayısından ({len(all_pdfs)}) büyük. Tüm dosyalar işlenecek.")
            selected_pdfs = all_pdfs
        else:
            selected_pdfs = random.sample(all_pdfs, sample_count)
    except ValueError:
        # Dosya adı ise
        found_pdf = find_pdf_by_name(param)
        if found_pdf:
            selected_pdfs = [found_pdf]
            all_pdfs = find_all_pdfs_in_dbf_directory()  # Toplam sayı için
        else:
            print(f"'{param}' adında dosya data/dbf dizininde bulunamadı.")
            sys.exit(1)
    
    print(f"Seçilen {len(selected_pdfs)}/{len(all_pdfs)} dosya işleniyor...\n")
    
    # Her dosyayı işle
    for i, pdf_path in enumerate(selected_pdfs, 1):
        # 1. Dizin ve dosya adı satırı
        print(pdf_path)
        
        # 2. Çizgi
        print("-" * 80)

        # PDF'ten tüm metni alalım
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # normalize et
        full_text = re.sub(r'\s+', ' ', full_text)

        # Tüm sayfa ekrana yaz.
        # print_full_pdf_text(pdf_path)  # tüm PDF metni burada görünür
        
        # Ardından tüm metin üzerinden başlıkları çıkart
        extracted_fields = extract_fields_from_text(full_text)
        for key, value in extracted_fields.items():
            title = key.split("_", 1)[-1].capitalize()
            print(f"\n{title}: {value}")
        print()

        # KAZANIM SAYISI VE SÜRE TABLOSU
        result1 = extract_kazanim_sayisi_sure_tablosu(pdf_path)
        print(result1)
        
        # ÖĞRENİM BİRİMLERİ TABLOSU
        result2 = extract_ob_tablosu(pdf_path)
        print(result2)
        print("-"*80)
        print(pdf_path)

if __name__ == "__main__":
    main()