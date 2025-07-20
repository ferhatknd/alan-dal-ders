#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testdbfolcme.py

Verilen dizin ve alt dizinlerdeki tüm PDF'lerin sadece Ölçme ve Değerlendirme 
kısımlarındaki ham metinleri toplar ve JSON çıktısı üretir.

Kullanım:
    python testdbfolcme.py <dizin_yolu>
    python testdbfolcme.py <sayı>  # Rastgele N tane dosya seçer
    
Örnek:
    python testdbfolcme.py data/dbf/31_Matbaa_Teknolojisi
    python testdbfolcme.py 100  # Rastgele 100 dosya işler
"""

import os
import sys
import json
import random
from datetime import datetime
# from modules.oku_dbf import extract_olcme_degerlendirme  # Artık kullanılmıyor
import pdfplumber

def find_raw_olcme_content(file_path):
    """
    PDF'den ölçme ve değerlendirme kısmındaki ham metni bulur.
    ADVANCED: Tablo çizgilerini guide alarak hücre sınırlarını doğru tespit eder.
    """
    try:
        import re
        
        def clean_measurement_content(content):
            """Clean and improve measurement content quality"""
            if not content:
                return content
            
            # 1. ÖLÇME VE DEĞERLENDİRME başlığını daha agresif temizle
            content = re.sub(r'ÖLÇME\s*VE\s*DEĞERLENDİRME', '', content, flags=re.IGNORECASE)
            content = re.sub(r'DEĞERLENDİRME\s*ÖLÇME\s*VE', '', content, flags=re.IGNORECASE)
            
            # 2. Başlangıçtaki gereksiz karakterleri temizle
            content = re.sub(r'^[\s\-:;.,]*', '', content)
            
            # 3. Sonundaki gereksiz kelimeleri temizle  
            content = re.sub(r'\s*(KAZANIM|YETKİNLİKLER|ÖĞRENME).*$', '', content, flags=re.IGNORECASE)
            
            # 4. Ortalarda kalan ÖLÇME VE DEĞERLENDİRME kalıntılarını temizle
            content = re.sub(r'\s+(ÖLÇME\s*VE\s*|DEĞERLENDİRME)\s+', ' ', content, flags=re.IGNORECASE)
            
            # 5. Çoklu boşlukları normalize et
            content = re.sub(r'\s+', ' ', content.strip())
            
            # 6. Eksik cümle başlangıçlarını düzelt
            if content and len(content) > 0:
                # İlk kelimenin ilk harfini büyük yap
                content = content[0].upper() + content[1:] if len(content) > 1 else content.upper()
            
            return content
        
        def is_valid_measurement_content(content):
            """Check if content is valid for measurement and evaluation - ENHANCED"""
            if not content or len(content) < 15:  # Minimum length increased
                return False
            
            content_upper = content.upper()
            
            # Strict exclusions
            strict_excludes = ['YETKİNLİKLER', 'KAZANIMLAR', 'DERSİN ADI', 'SINIF']
            for pattern in strict_excludes:
                if pattern in content_upper and len(content) < 80:
                    return False
            
            # Positive indicators for measurement content
            positive_indicators = [
                'GÖZLEM', 'PUANLAMA', 'DEĞERLENDİRME', 'RUBRIK', 'ÖLÇEK', 
                'KONTROL LİSTESİ', 'PORTFOLYO', 'ÖZ DEĞERLENDİRME', 'AKRAN',
                'BİÇİMLENDİRİCİ', 'ARAÇLARINDAN', 'SEÇİLEREK', 'FORMU'
            ]
            
            positive_count = sum(1 for indicator in positive_indicators if indicator in content_upper)
            
            # Require at least one measurement keyword for short content
            if len(content) < 100 and positive_count == 0:
                return False
            
            return True
        
        def find_complete_table_cell_content(page, target_phrase="ÖLÇME VE DEĞERLENDİRME"):
            """
            ADVANCED: PDF'deki gerçek çizgileri detect ederek kesin hücre sınırlarını bulur
            """
            
            # STRATEGY A: Önce sayfadaki gerçek çizgileri bulalım
            try:
                lines = page.lines
                rects = page.rects
                
                # Çizgiler yoksa dikdörtgenleri (table borders) kullan
                if lines:
                    # Horizontal ve vertical çizgileri ayır
                    horizontal_lines = [line for line in lines if abs(line['y0'] - line['y1']) < 2]
                    vertical_lines = [line for line in lines if abs(line['x0'] - line['x1']) < 2]
                    
                    if horizontal_lines and vertical_lines:
                        # Çizgileri koordinatlara göre sırala
                        horizontal_lines.sort(key=lambda x: x['y0'])
                        vertical_lines.sort(key=lambda x: x['x0'])
                        
                        # Gerçek çizgi tabanlı tablo extraction
                        table_settings_advanced = {
                            "vertical_strategy": "explicit",
                            "horizontal_strategy": "explicit",
                            "explicit_vertical_lines": [line['x0'] for line in vertical_lines],
                            "explicit_horizontal_lines": [line['y0'] for line in horizontal_lines],
                            "snap_tolerance": 1,
                            "join_tolerance": 1
                        }
                        
                        # Çizgi tabanlı table extraction dene
                        tables = page.extract_tables(table_settings_advanced)
                        if tables:
                            for table in tables:
                                for row_idx, row in enumerate(table):
                                    for col_idx, cell in enumerate(row):
                                        if cell and isinstance(cell, str) and target_phrase in cell.upper():
                                            
                                            # Aynı hücredeki tam içeriği al
                                            if len(cell) > 50:
                                                return cell.strip()
                                            
                                            # Sağ hücreyi kontrol et
                                            if col_idx + 1 < len(row) and row[col_idx + 1]:
                                                right_cell = str(row[col_idx + 1]).strip()
                                                if right_cell and len(right_cell) > 30:
                                                    return right_cell
                
                # Çizgi yoksa RECT (dikdörtgen) borders kullan
                if rects and len(rects) > 10:  # Yeterli dikdörtgen varsa tablo olabilir
                    
                    # Dikdörtgenlerin kenarlarını çizgi gibi kullan
                    horizontal_edges = set()
                    vertical_edges = set()
                    
                    for rect in rects:
                        # Her dikdörtgenin 4 kenarını ekle
                        horizontal_edges.add(rect['y0'])  # Top edge
                        horizontal_edges.add(rect['y1'])  # Bottom edge
                        vertical_edges.add(rect['x0'])    # Left edge
                        vertical_edges.add(rect['x1'])    # Right edge
                    
                    horizontal_lines_from_rects = sorted(list(horizontal_edges))
                    vertical_lines_from_rects = sorted(list(vertical_edges))
                    
                    if len(horizontal_lines_from_rects) > 3 and len(vertical_lines_from_rects) > 1:
                        # Dikdörtgen kenarları ile tablo extraction - ENHANCED TOLERANCE
                        table_settings_rect = {
                            "vertical_strategy": "explicit",
                            "horizontal_strategy": "explicit", 
                            "explicit_vertical_lines": vertical_lines_from_rects,
                            "explicit_horizontal_lines": horizontal_lines_from_rects,
                            "snap_tolerance": 5,      # Çizgiye yakın text için artırıldı
                            "join_tolerance": 5,      # Çizgiye yakın text için artırıldı
                            "text_tolerance": 3,      # Text positioning tolerance
                            "text_x_tolerance": 5,    # Horizontal text tolerance
                            "text_y_tolerance": 10,    # Vertical text tolerance
                            "intersection_tolerance": 5,  # Intersection detection
                            "keep_blank_chars": True, # Boşlukları koru
                            "use_text_flow": True     # Text flow'u kullan
                        }
                        
                        # Multiple tolerance strategies - çizgiye çok yakın text için
                        tolerance_strategies = [
                            # Strategy 1: Standard tolerance
                            table_settings_rect,
                            
                            # Strategy 2: Higher tolerance for very close text
                            {
                                "vertical_strategy": "explicit",
                                "horizontal_strategy": "explicit", 
                                "explicit_vertical_lines": vertical_lines_from_rects,
                                "explicit_horizontal_lines": horizontal_lines_from_rects,
                                "snap_tolerance": 8,      # Daha yüksek tolerance
                                "join_tolerance": 8,      
                                "text_tolerance": 5,      
                                "text_x_tolerance": 8,    
                                "text_y_tolerance": 15,    
                                "intersection_tolerance": 8
                            },
                            
                            # Strategy 3: Very high tolerance for edge cases
                            {
                                "vertical_strategy": "explicit",
                                "horizontal_strategy": "explicit", 
                                "explicit_vertical_lines": vertical_lines_from_rects,
                                "explicit_horizontal_lines": horizontal_lines_from_rects,
                                "snap_tolerance": 12,     # Çok yüksek tolerance
                                "join_tolerance": 12,     
                                "text_tolerance": 8,      
                                "text_x_tolerance": 12,   
                                "text_y_tolerance": 12,   
                                "intersection_tolerance": 12
                            }
                        ]
                        
                        for strategy_idx, strategy_settings in enumerate(tolerance_strategies):
                            tables = page.extract_tables(strategy_settings)
                            if tables:
                                print(f"DEBUG: Tolerance Strategy {strategy_idx+1} ile {len(tables)} tablo bulundu")
                                for table in tables:
                                    print(f"DEBUG: Tablo {len(table)} satır x {len(table[0]) if table else 0} sütun")
                                    for row_idx, row in enumerate(table):
                                        for col_idx, cell in enumerate(row):
                                            if cell and isinstance(cell, str):
                                                # Debug: Tüm hücreleri kontrol et
                                                cell_upper = cell.upper()
                                                if any(word in cell_upper for word in ['ÖLÇME', 'DEĞERLENDİRME', 'OLCME', 'DEGERLENDIRME']):
                                                    print(f"DEBUG: ÖLÇME ile ilgili hücre - Satır: {row_idx}, Sütun: {col_idx}")
                                                    print(f"DEBUG: Hücre içeriği: {cell[:150]}...")
                                                    
                                                if target_phrase in cell_upper:
                                                    print(f"DEBUG: RECT-Hedef hücre bulundu - Satır: {row_idx}, Sütun: {col_idx}")
                                                    print(f"DEBUG: RECT-Hücre içeriği: {cell[:100]}...")
                                                
                                                # Aynı hücredeki tam içeriği al
                                                if len(cell) > 50:
                                                    return cell.strip()
                                                
                                                # Sağ hücreyi kontrol et
                                                if col_idx + 1 < len(row) and row[col_idx + 1]:
                                                    right_cell = str(row[col_idx + 1]).strip()
                                                    if right_cell and len(right_cell) > 30:
                                                        return right_cell
            except Exception as e:
                # print(f"DEBUG: Çizgi tabanlı extraction hatası: {e}")
                pass
            
            # STRATEGY B: Gelişmiş line detection strategies
            table_settings_list = [
                # Strategy 1: Lines with high tolerance for close text
                {
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict", 
                    "snap_tolerance": 3,      # Artırıldı
                    "join_tolerance": 3,      # Artırıldı
                    "edge_min_length": 3,
                    "min_words_vertical": 0,
                    "min_words_horizontal": 0,
                    "intersection_tolerance": 5,  # Artırıldı
                    "text_tolerance": 3,      # Eklendi
                    "text_x_tolerance": 5,    # Eklendi
                    "text_y_tolerance": 5     # Eklendi
                },
                # Strategy 2: Medium tolerance
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,      # Artırıldı
                    "join_tolerance": 5,      # Artırıldı
                    "edge_min_length": 5,
                    "intersection_tolerance": 6,  # Artırıldı
                    "text_tolerance": 4,      # Eklendi
                    "text_x_tolerance": 6,    # Eklendi
                    "text_y_tolerance": 6     # Eklendi
                },
                # Strategy 3: High tolerance hybrid
                {
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "text",
                    "snap_tolerance": 8,      # Çok artırıldı
                    "text_tolerance": 6,      # Artırıldı
                    "text_x_tolerance": 8,    # Artırıldı
                    "text_y_tolerance": 8,    # Eklendi
                    "intersection_tolerance": 8   # Eklendi
                },
                # Strategy 4: Very high tolerance for edge cases
                {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "text_tolerance": 8,      # Çok yüksek
                    "text_x_tolerance": 12,   # Çok yüksek
                    "text_y_tolerance": 12,   # Çok yüksek
                    "snap_tolerance": 12      # Çok yüksek
                }
            ]
            
            for table_idx, table_settings in enumerate(table_settings_list):
                try:
                    # Bu ayarlar ile tabloları çıkar
                    tables = page.extract_tables(table_settings)
                    
                    for table in tables:
                        for row_idx, row in enumerate(table):
                            for col_idx, cell in enumerate(row):
                                if cell and isinstance(cell, str) and target_phrase in cell.upper():
                                    
                                    # CASE 1: Aynı hücrede başlık + içerik (en yaygın durum)
                                    if len(cell) > 50:
                                        # İçerik aynı hücrede ve uzunsa (multi-line)
                                        full_content = str(cell).strip()
                                        if target_phrase in full_content.upper():
                                            # Başlığı çıkar, sadece içeriği al
                                            if '\n' in full_content:
                                                lines = full_content.split('\n')
                                                content_lines = []
                                                found_header = False
                                                for line in lines:
                                                    if target_phrase in line.upper():
                                                        found_header = True
                                                        continue
                                                    if found_header:
                                                        content_lines.append(line.strip())
                                                if content_lines:
                                                    content = ' '.join(content_lines).strip()
                                                    if len(content) > 30:
                                                        return content
                                            else:
                                                # Tek satırda ise split ile ayır
                                                parts = full_content.split(target_phrase, 1)
                                                if len(parts) > 1:
                                                    content = parts[1].strip()
                                                    if len(content) > 30:
                                                        return content
                                    
                                    # CASE 2: Sol hücrede başlık, sağ hücrede içerik
                                    if col_idx + 1 < len(row) and row[col_idx + 1]:
                                        right_cell = str(row[col_idx + 1]).strip()
                                        if right_cell and len(right_cell) > 30:
                                            return right_cell
                                    
                                    # CASE 3: İki nokta ile ayrılmış (: sonrası)
                                    if ':' in cell:
                                        parts = cell.split(':', 1)
                                        if len(parts) > 1:
                                            content = parts[1].strip()
                                            if len(content) > 30:
                                                return content
                                    
                                    # CASE 4: Bir alt satırdaki sağ hücre
                                    if (row_idx + 1 < len(table) and 
                                        col_idx + 1 < len(table[row_idx + 1]) and
                                        table[row_idx + 1][col_idx + 1]):
                                        bottom_right_cell = str(table[row_idx + 1][col_idx + 1]).strip()
                                        if bottom_right_cell and len(bottom_right_cell) > 30:
                                            return bottom_right_cell
                                            
                except Exception as e:
                    continue
            
            return None
        
        with pdfplumber.open(file_path) as pdf:
            # PRIORITY STRATEGY: Gelişmiş tablo çizgi algılama ile tam hücre içeriği 
            for page_idx, page in enumerate(pdf.pages):
                complete_content = find_complete_table_cell_content(page)
                if complete_content:
                    print(f"DEBUG: ✅ PRIORITY STRATEGY başarılı - Sayfa {page_idx+1}")
                    cleaned_content = clean_measurement_content(complete_content)
                    if cleaned_content and is_valid_measurement_content(cleaned_content):
                        return cleaned_content
            
            # FALLBACK Strategy 1: Enhanced table extraction with improved cleaning
            print(f"DEBUG: FALLBACK Strategy 1 başlatılıyor...")
            for page_idx, page in enumerate(pdf.pages):
                all_tables = page.extract_tables()
                print(f"DEBUG: Sayfa {page_idx+1} - Default extraction ile {len(all_tables)} tablo bulundu")
                
                for table_idx, table in enumerate(all_tables):
                    for i, row in enumerate(table):
                        for j, cell in enumerate(row):
                            if cell and isinstance(cell, str) and 'ÖLÇME VE DEĞERLENDİRME' in cell.upper():
                                print(f"DEBUG: FALLBACK - ÖLÇME hücre bulundu Tablo:{table_idx}, Satır:{i}, Sütun:{j}")
                                print(f"DEBUG: FALLBACK - Hücre içeriği: {cell[:150]}...")
                                # Strategy 1A: String split approach (ENHANCED)
                                if len(cell) > 30:
                                    parts = cell.split('ÖLÇME VE DEĞERLENDİRME', 1)
                                    if len(parts) > 1:
                                        content = clean_measurement_content(parts[1])
                                        if content and is_valid_measurement_content(content):
                                            print(f"DEBUG: ✅ FALLBACK Strategy 1A başarılı!")
                                            return content
                                
                                # Strategy 1B: Colon separation (ENHANCED)
                                if ':' in cell:
                                    content = clean_measurement_content(cell.split(':', 1)[1])
                                    if content and is_valid_measurement_content(content):
                                        return content
                                
                                # Strategy 1C: Adjacent cell (ENHANCED)
                                if j + 1 < len(row) and row[j + 1]:
                                    content = clean_measurement_content(str(row[j + 1]))
                                    if content and is_valid_measurement_content(content):
                                        return content
                                
                                # Strategy 1D: Next row (ENHANCED)
                                if i + 1 < len(table) and len(table[i + 1]) > 0:
                                    next_row = table[i + 1]
                                    if next_row[0]:
                                        content = clean_measurement_content(str(next_row[0]))
                                        if content and is_valid_measurement_content(content):
                                            return content
            
            # Strategy 2: Multiple table detection strategies
            for page in pdf.pages:
                table_strategies = [
                    {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict", "snap_tolerance": 2, "join_tolerance": 2},
                    {"vertical_strategy": "text", "horizontal_strategy": "text", "text_tolerance": 3, "text_x_tolerance": 5},
                    {"vertical_strategy": "lines", "horizontal_strategy": "text", "snap_tolerance": 5, "text_tolerance": 5}
                ]
                
                for table_settings in table_strategies:
                    try:
                        tables_strict = page.extract_tables(table_settings)
                        
                        for table in tables_strict:
                            for i, row in enumerate(table):
                                header_cells = []
                                content_cells = []
                                
                                for j, cell in enumerate(row):
                                    if cell and isinstance(cell, str):
                                        cell_upper = str(cell).upper().strip()
                                        if 'ÖLÇME VE DEĞERLENDİRME' in cell_upper:
                                            header_cells.append((j, cell))
                                        elif len(str(cell).strip()) > 20:
                                            content_cells.append((j, cell))
                                
                                # Pair headers with content (simplified)
                                for header_idx, header_cell in header_cells:
                                    # Check immediate next cell
                                    if header_idx + 1 < len(row) and row[header_idx + 1]:
                                        next_cell = str(row[header_idx + 1]).strip()
                                        if (next_cell and len(next_cell) > 10 and 
                                            'ÖLÇME VE DEĞERLENDİRME' not in next_cell.upper()):
                                            content = clean_measurement_content(next_cell)
                                            if content and is_valid_measurement_content(content):
                                                return content
                                    
                                    # Check other cells in row
                                    for content_idx, content_cell in content_cells:
                                        if abs(content_idx - header_idx) > 1:
                                            content = clean_measurement_content(str(content_cell))
                                            if content and is_valid_measurement_content(content):
                                                return content
                    except:
                        continue
            
            # Strategy 3: Advanced text-based search
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Line-by-line with context
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if ('ÖLÇME' in line.upper() and 'VE' in line.upper()) or 'DEĞERLENDİRME' in line.upper():
                            for context_size in [3, 5, 8]:
                                context_lines = []
                                for j in range(max(0, i-1), min(len(lines), i+context_size)):
                                    context_lines.append(lines[j])
                                
                                full_context = ' '.join(context_lines)
                                
                                if 'ÖLÇME VE DEĞERLENDİRME' in full_context.upper():
                                    parts = full_context.split('ÖLÇME VE DEĞERLENDİRME', 1)
                                    if len(parts) > 1:
                                        content = clean_measurement_content(parts[1])
                                        if content and is_valid_measurement_content(content):
                                            return content
            
            # Strategy 4: Fallback - look for measurement content in text
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if ('ÖLÇME' in line.upper() and 'VE' in line.upper()) or 'DEĞERLENDİRME' in line.upper():
                            # Bağlam satırlarını birleştir
                            context_lines = []
                            for j in range(max(0, i-1), min(len(lines), i+5)):
                                context_lines.append(lines[j])
                            
                            full_context = ' '.join(context_lines)
                            if 'ÖLÇME' in full_context.upper() and 'DEĞERLENDİRME' in full_context.upper():
                                content = clean_measurement_content(full_context)
                                if content and is_valid_measurement_content(content):
                                    return content
        
        return None
        
    except Exception as e:
        print(f"Hata ({os.path.basename(file_path)}): {e}")
        return None

def find_all_pdfs(directory):
    """
    Verilen dizin ve alt dizinlerdeki tüm PDF dosyalarını bulur.
    """
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

def find_all_pdfs_in_project():
    """
    Proje içindeki tüm PDF dosyalarını bulur (data/dbf klasöründe).
    """
    pdf_files = []
    base_dirs = ['data/dbf']
    
    for base_dir in base_dirs:
        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
    
    return pdf_files

def sample_random_pdfs(pdf_files, sample_size):
    """
    PDF listesinden rastgele N tane seçer.
    """
    if len(pdf_files) <= sample_size:
        return pdf_files
    
    return random.sample(pdf_files, sample_size)


def process_pdf_list(pdf_files, description="PDF dosyaları"):
    """
    Verilen PDF listesindeki dosyaların ölçme değerlendirme metinlerini toplar.
    """
    results = []
    processed_count = 0
    found_count = 0
    
    for pdf_file in pdf_files:
        processed_count += 1
        file_name = os.path.basename(pdf_file)
        
        print(f"[{processed_count}/{len(pdf_files)}] {file_name}")
        
        # Debug: KLAVYE TEKNİKLERİ dosyası için özel debug
        if "KLAVYE" in file_name:
            print(f"    🔍 DEBUG: KLAVYE dosyası bulundu - detaylı analiz yapılıyor...")
        
        # Ham metni bul
        raw_content = find_raw_olcme_content(pdf_file)
        
        if raw_content:
            found_count += 1
            # Ders adını dosya adından çıkar (uzantıyı kaldır)
            ders_adi = os.path.splitext(file_name)[0]
            
            results.append({
                "source_file": file_name,
                "file_path": pdf_file,
                "ders_adi": ders_adi,
                "olcme_degerlendirme": raw_content
            })
            print(f"    📝 Metin: {raw_content}")
        else:
            print(f"    ❌ İçerik bulunamadı")
    
    print("="*60)
    print(f"   Toplam durum: {found_count}/{len(pdf_files)}")    
    return results

def test_specific_file(file_path):
    """Belirli bir dosyayı test et - debug output ile"""
    print(f"🔍 Spesifik dosya testi: {os.path.basename(file_path)}")
    print("="*60)
    
    if not os.path.exists(file_path):
        print(f"❌ Dosya bulunamadı: {file_path}")
        return
    
    # Ham metni bul
    raw_content = find_raw_olcme_content(file_path)
    
    if raw_content:
        print(f"✅ İçerik bulundu")
        print(f"📝 Tam Metin:")
        print(f"    {raw_content}")
        print(f"📏 Uzunluk: {len(raw_content)} karakter")
    else:
        print(f"❌ İçerik bulunamadı")
    
    print("="*60)

def main():
    if len(sys.argv) != 2:
        print("Kullanım:")
        print("  python test_dbf_olcme.py <dizin_yolu>")
        print("  python test_dbf_olcme.py <sayı>")
        print("  python test_dbf_olcme.py klavye    # KLAVYE TEKNİKLERİ dosyasını test et")
        print()
        print("Örnekler:")
        print("  python test_dbf_olcme.py data/dbf/31_Matbaa_Teknolojisi")
        print("  python test_dbf_olcme.py 100  # Rastgele 100 dosya işler")
        print("  python test_dbf_olcme.py klavye  # KLAVYE dosyasını test et")
        sys.exit(1)
    
    argument = sys.argv[1]
    
    # Özel komutlar
    if argument.lower() == "klavye":
        klavye_file = "data/dbf/01_Adalet/adalet/9.SINIF/KLAVYE TEKNİKLERİ DBF.pdf"
        test_specific_file(klavye_file)
        return
    
    # Sayı mı yoksa dizin yolu mu kontrol et
    try:
        sample_size = int(argument)
        # Sayı verildi - rastgele örnekleme
        print(f"🎯 Rastgele {sample_size} dosya seçiliyor...")
        print("="*60)
        
        # Tüm PDF'leri bul
        all_pdfs = find_all_pdfs_in_project()
        
        if not all_pdfs:
            print("❌ Projede PDF dosyası bulunamadı!")
            print("   data/dbf klasörünü kontrol edin.")
            sys.exit(1)
        
        # Rastgele seç
        selected_pdfs = sample_random_pdfs(all_pdfs, sample_size)
        
        # İşle
        results = process_pdf_list(selected_pdfs, f"Rastgele seçilen {len(selected_pdfs)} dosya")
        
        output_suffix = f"random_{sample_size}"
        
    except ValueError:
        # Dizin yolu verildi - normal işlem
        directory_path = argument
        
        if not os.path.exists(directory_path):
            print(f"❌ Hata: Dizin bulunamadı - {directory_path}")
            sys.exit(1)
        
        pdf_files = find_all_pdfs(directory_path)
        
        if not pdf_files:
            print(f"❌ Dizinde PDF dosyası bulunamadı: {directory_path}")
            sys.exit(1)
        
        # İşle
        results = process_pdf_list(pdf_files, f"Dizin: {directory_path}")
        
        output_suffix = os.path.basename(directory_path)
    
    if not results:
        print("❌ Hiçbir dosyada ölçme değerlendirme içeriği bulunamadı!")
        sys.exit(1)
    
    # JSON dosyasını kaydet
    output_file = f"olcme_metinleri_{output_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
if __name__ == "__main__":
    main()