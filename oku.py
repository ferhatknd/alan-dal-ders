import camelot
import pandas as pd
import re
import os
import glob
import json
from datetime import datetime

# Set Ghostscript path for camelot
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

def clean_text(text):
    """
    Metindeki gereksiz \n karakterlerini ve fazla boşlukları temizle
    """
    if not text:
        return text
    
    # Birden fazla boşluğu tek boşlukla değiştir
    text = re.sub(r'\s+', ' ', text.strip())
    return text

def extract_ders_adi(pdf_path):
    """
    PDF'den ders adını çıkar
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        
        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'DERSİN ADI' in cell.upper():
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                            if content and content != 'nan':
                                return clean_text(content)
                        
                        # Yan hücrede ise
                        if j + 1 < len(row):
                            content = str(row.iloc[j + 1]).strip()
                            if content and content != 'nan':
                                return clean_text(content)
                        
                        # Alt satırda ise
                        if i + 1 < len(df):
                            next_row = df.iloc[i + 1]
                            for next_cell in next_row:
                                content = str(next_cell).strip()
                                if content and content != 'nan':
                                    return clean_text(content)
        
        return None
        
    except Exception as e:
        print(f"Error extracting ders adı: {str(e)}")
        return None

def extract_ders_sinifi(pdf_path):
    """
    PDF'den ders sınıfını çıkar ve sayıya çevir
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        
        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'DERSİN SINIFI' in cell.upper():
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        else:
                            # Yan hücrede ise
                            if j + 1 < len(row):
                                content = str(row.iloc[j + 1]).strip()
                            else:
                                continue
                        
                        if content and content != 'nan':
                            # Sayıyı çıkar (örn: "9. Sınıf" -> 9)
                            match = re.search(r'(\d+)', content)
                            if match:
                                return int(match.group(1))
        
        return None
        
    except Exception as e:
        print(f"Error extracting ders sınıfı: {str(e)}")
        return None

def extract_ders_saati(pdf_path):
    """
    PDF'den haftalık ders saatini çıkar
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        
        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and ('DERSİN SÜRESİ' in cell.upper() or 'HAFTALIK' in cell.upper()):
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        else:
                            # Yan hücrede ise
                            if j + 1 < len(row):
                                content = str(row.iloc[j + 1]).strip()
                            else:
                                continue
                        
                        if content and content != 'nan':
                            # Sayıyı çıkar (örn: "3 Ders Saati" -> 3)
                            match = re.search(r'(\d+)', content)
                            if match:
                                return int(match.group(1))
        
        return None
        
    except Exception as e:
        print(f"Error extracting ders saati: {str(e)}")
        return None

def extract_dersin_amaci(pdf_path):
    """
    PDF'den dersin amacını çıkar (mevcut fonksiyondan uyarlandı)
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        dersin_amaci_content = []
        
        for table in tables:
            df = table.df
            
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'DERSİN AMACI' in cell.upper():
                        content = ""
                        
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        
                        if not content and j + 1 < len(row):
                            content = str(row.iloc[j + 1]).strip()
                        
                        if not content and i + 1 < len(df):
                            next_row = df.iloc[i + 1]
                            for next_cell in next_row:
                                if str(next_cell).strip() and str(next_cell).strip() != 'nan':
                                    content = str(next_cell).strip()
                                    break
                        
                        if content and content != 'nan':
                            dersin_amaci_content.append(content)
        
        if not dersin_amaci_content:
            tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
            
            for table in tables:
                df = table.df
                text = df.to_string()
                pattern = r'DERSİN\s+AMACI[:\s]*([^\n]+(?:\n[^\n]*)*?)(?=\n\s*[A-ZÜÇĞÖŞ]+|$)'
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                if match:
                    content = match.group(1).strip()
                    if content:
                        dersin_amaci_content.append(content)
        
        for content in dersin_amaci_content:
            if content and len(content.strip()) > 0:
                return clean_text(content)
        
        return None
        
    except Exception as e:
        print(f"Error extracting dersin amacı: {str(e)}")
        return None

def extract_genel_kazanimlar(pdf_path):
    """
    PDF'den dersin genel kazanımlarını çıkar
    """
    try:
        # Hem lattice hem stream dene
        tables_lattice = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        tables_stream = camelot.read_pdf(pdf_path, flavor='stream', pages='1')
        
        kazanimlar = []
        
        # Önce lattice ile dene
        for table in tables_lattice:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and ('DERSİN ÖĞRENME KAZANIMLARI' in cell.upper()):
                        print(f"Found DERSİN ÖĞRENME KAZANIMLARI at row {i}, col {j}")
                        
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        else:
                            # Yan hücredeki içeriği al
                            if j + 1 < len(row):
                                content = str(row.iloc[j + 1]).strip()
                                print(f"Content from next cell: {content[:100]}...")
                            else:
                                # Alt satırdaki içeriği al
                                if i + 1 < len(df):
                                    next_row = df.iloc[i + 1]
                                    content = str(next_row.iloc[j]).strip()
                                    print(f"Content from next row: {content[:100]}...")
                                else:
                                    continue
                        
                        if content and content != 'nan' and len(content) > 10:
                            # Madde işaretleriyle ayrılmış kazanımları ayır
                            if '•' in content or content.startswith(('1.', '2.', '3.')):
                                kazanim_items = re.split(r'[•\-]\s*|\d+\.\s*', content)
                                for item in kazanim_items:
                                    clean_item = clean_text(item)
                                    if clean_item and len(clean_item) > 10:
                                        kazanimlar.append(clean_item)
                            else:
                                clean_item = clean_text(content)
                                if clean_item and len(clean_item) > 10:
                                    kazanimlar.append(clean_item)
                        
                        return kazanimlar[:10]  # İlk eşleşmede dön
        
        # Lattice işe yaramazsa stream dene
        for table in tables_stream:
            df = table.df
            text = df.to_string()
            
            # Regex ile DERSİN ÖĞRENME KAZANIMLARI bölümünü bul
            pattern = r'DERSİN\s+ÖĞRENME\s+KAZANIMLARI[:\s]*([^\n]+(?:\n[^\n]*)*?)(?=\n\s*[A-ZÜÇĞÖŞ]{3,}|$)'
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            if match:
                content = match.group(1).strip()
                print(f"Found with regex: {content[:100]}...")
                
                # Madde işaretleriyle ayrılmış kazanımları ayır
                if '•' in content or content.startswith(('1.', '2.', '3.')):
                    kazanim_items = re.split(r'[•\-]\s*|\d+\.\s*', content)
                    for item in kazanim_items:
                        clean_item = clean_text(item)
                        if clean_item and len(clean_item) > 10:
                            kazanimlar.append(clean_item)
                else:
                    clean_item = clean_text(content)
                    if clean_item and len(clean_item) > 10:
                        kazanimlar.append(clean_item)
        
        return kazanimlar[:10]
        
    except Exception as e:
        print(f"Error extracting genel kazanımlar: {str(e)}")
        return []

def extract_ortam_donanimi(pdf_path):
    """
    PDF'den eğitim-öğretim ortam ve donanımını çıkar
    Ortam: X ve Y ortamı. Donanım: A, B ve C araçları formatında parse eder
    """
    try:
        # Hem lattice hem stream dene
        tables_lattice = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        tables_stream = camelot.read_pdf(pdf_path, flavor='stream', pages='1')
        
        ortam_donanimi = []
        
        # Önce lattice ile dene
        for table in tables_lattice:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'EĞİTİM-ÖĞRETİM ORTAM' in cell.upper():
                        print(f"Found EĞİTİM-ÖĞRETİM ORTAM at row {i}, col {j}")
                        
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        else:
                            # Yan hücredeki içeriği al
                            if j + 1 < len(row):
                                content = str(row.iloc[j + 1]).strip()
                                print(f"Content from next cell: {content[:100]}...")
                            else:
                                # Alt satırdaki içeriği al
                                if i + 1 < len(df):
                                    next_row = df.iloc[i + 1]
                                    content = str(next_row.iloc[j]).strip()
                                    print(f"Content from next row: {content[:100]}...")
                                else:
                                    continue
                        
                        if content and content != 'nan' and len(content) > 10:
                            return parse_ortam_donanimi_content(content)
        
        # Lattice işe yaramazsa stream dene
        for table in tables_stream:
            df = table.df
            text = df.to_string()
            
            # Regex ile EĞİTİM-ÖĞRETİM ORTAM bölümünü bul
            pattern = r'EĞİTİM[^\n]*ORTAM[^\n]*DONANIMI?[:\s]*([^\n]+(?:\n[^\n]*)*?)(?=\n\s*[A-ZÜÇĞÖŞ]{3,}|$)'
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            if match:
                content = match.group(1).strip()
                print(f"Found with regex: {content[:100]}...")
                return parse_ortam_donanimi_content(content)
        
        return ortam_donanimi
        
    except Exception as e:
        print(f"Error extracting ortam donanımı: {str(e)}")
        return []

def parse_ortam_donanimi_content(content):
    """
    Ortam ve donanım içeriğini maddelere ayır
    """
    ortam_donanimi = []
    
    # Ortam ve Donanım bölümlerini ayır
    ortam_pattern = r'Ortam:\s*([^.]*?)\.?\s*(?:Donanım:|$)'
    donanim_pattern = r'Donanım:\s*(.+?)(?:sağlanmalıdır|$)'
    
    ortam_match = re.search(ortam_pattern, content, re.IGNORECASE | re.DOTALL)
    donanim_match = re.search(donanim_pattern, content, re.IGNORECASE | re.DOTALL)
    
    # Ortam kısmını parse et
    if ortam_match:
        ortam_text = ortam_match.group(1).strip()
        print(f"Ortam text: {ortam_text}")
        
        # Virgül ve "ve" ile ayrılmış ortamları ayır
        ortam_items = re.split(r',\s*|\s+ve\s+', ortam_text)
        for item in ortam_items:
            clean_item = clean_text(item.strip().rstrip('.,'))
            if clean_item and len(clean_item) > 3:
                ortam_donanimi.append(clean_item.title())
    
    # Donanım kısmını parse et  
    if donanim_match:
        donanim_text = donanim_match.group(1).strip()
        print(f"Donanım text: {donanim_text}")
        
        # "sağlanmalıdır" kısmını temizle
        donanim_text = re.sub(r'\s*(ile\s+)?iş\s+ortam[ıi]\s+sağlanmalıdır.*$', '', donanim_text, flags=re.IGNORECASE)
        
        # Virgül ile ayrılmış donanımları ayır
        donanim_items = re.split(r',\s*', donanim_text)
        for item in donanim_items:
            # Son maddedeki "ve" yi temizle
            if ' ve ' in item:
                ve_parts = re.split(r'\s+ve\s+', item)
                for part in ve_parts:
                    clean_item = clean_text(part.strip().rstrip('.,'))
                    if clean_item and len(clean_item) > 3:
                        ortam_donanimi.append(clean_item.title())
            else:
                clean_item = clean_text(item.strip().rstrip('.,'))
                if clean_item and len(clean_item) > 3:
                    ortam_donanimi.append(clean_item.title())
    
    # Eğer pattern match etmezse basit ayrıştırma yap
    if not ortam_match and not donanim_match:
        # Tüm noktalama ile ayrılmış öğeleri al
        items = re.split(r'[,.;]\s*|\s+ve\s+', content)
        for item in items:
            clean_item = clean_text(item.strip().rstrip('.,'))
            if clean_item and len(clean_item) > 3 and 'sağlanmalıdır' not in clean_item.lower():
                ortam_donanimi.append(clean_item.title())
    
    return ortam_donanimi

def extract_kazanim_tablosu(pdf_path):
    """
    PDF'den kazanım sayısı ve süre tablosunu çıkar
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        
        kazanim_tablosu = []
        
        for table in tables:
            df = table.df
            
            # "KAZANIM SAYISI VE SÜRE TABLOSU" başlığını bul
            found_table = False
            table_start_row = None
            
            for i, row in df.iterrows():
                row_text = ' '.join([str(cell) for cell in row]).upper()
                if 'KAZANIM SAYISI' in row_text and ('SÜRE' in row_text or 'TABLOSU' in row_text):
                    found_table = True
                    table_start_row = i
                    break
            
            if found_table and table_start_row is not None:
                # Tablo başlık satırlarını bul
                header_found = False
                for i in range(table_start_row, len(df)):
                    row = df.iloc[i]
                    row_text = ' '.join([str(cell) for cell in row]).upper()
                    
                    # Sütun başlıklarını bul
                    if any(keyword in row_text for keyword in ['ÖĞRENME BİRİMİ', 'KAZANIM', 'SÜRE', 'DERS SAATİ']):
                        header_found = True
                        # Veri satırlarını oku
                        for k in range(i + 1, len(df)):
                            data_row = df.iloc[k]
                            
                            # Boş satırları atla
                            row_values = [str(cell).strip() for cell in data_row]
                            if all(val in ['', 'nan'] for val in row_values):
                                continue
                            
                            # TOPLAM satırını atla
                            row_text_data = ' '.join(row_values).upper()
                            if 'TOPLAM' in row_text_data:
                                continue
                            
                            # Geçerli veri olan satırları al
                            valid_data = [val for val in row_values if val not in ['', 'nan']]
                            
                            if len(valid_data) >= 2:
                                birim_adi = clean_text(valid_data[0])
                                kazanim_sayisi = clean_text(valid_data[1]) if len(valid_data) > 1 else ""
                                ders_saati = clean_text(valid_data[2]) if len(valid_data) > 2 else ""
                                
                                # Birim adının geçerli olduğunu kontrol et
                                if birim_adi and len(birim_adi) > 3 and not birim_adi.isdigit():
                                    kazanim_tablosu.append({
                                        "birim_adi": birim_adi,
                                        "kazanim_sayisi": kazanim_sayisi,
                                        "ders_saati_orani": ders_saati
                                    })
                        break
                
                if header_found:
                    break
        
        return kazanim_tablosu
        
    except Exception as e:
        print(f"Error extracting kazanım tablosu: {str(e)}")
        return []

def extract_ogrenme_birimleri(pdf_path):
    """
    PDF'den öğrenme birimlerini detaylı olarak çıkar (sayfa 2+)
    3 sütunlu tablo: ÖĞRENME BİRİMİ | KONULAR | KAZANIMLAR
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        ogrenme_birimleri = []
        
        for page_num, table in enumerate(tables):
            df = table.df
            
            # 3 sütunlu öğrenme birimi tablosunu bul
            found_main_table = False
            for i, row in df.iterrows():
                row_text = ' '.join([str(cell) for cell in row]).upper()
                # Ana detay tablosunu bul (3 sütun: birim, konu, kazanım)
                if 'ÖĞRENME BİRİMİ' in row_text and 'KONULAR' in row_text and 'KAZANIM' in row_text:
                    found_main_table = True
                    
                    # Sütun indekslerini belirle
                    birim_col = None
                    konu_col = None  
                    kazanim_col = None
                    
                    for j, header_cell in enumerate(row):
                        header_text = str(header_cell).upper()
                        if 'ÖĞRENME BİRİMİ' in header_text:
                            birim_col = j
                        elif 'KONULAR' in header_text or 'KONU' in header_text:
                            konu_col = j
                        elif 'KAZANIM' in header_text:
                            kazanim_col = j
                    
                    # Veri satırlarını oku
                    current_birim = None
                    current_konular = []
                    current_kazanimlar = []
                    
                    for k in range(i + 1, len(df)):
                        data_row = df.iloc[k]
                        
                        # Tüm sütun değerlerini al
                        row_values = [str(cell).strip() for cell in data_row]
                        
                        # Tamamen boş satırları atla
                        if all(val in ['', 'nan'] for val in row_values):
                            continue
                        
                        # Öğrenme birimi sütununu kontrol et
                        birim_text = row_values[birim_col] if birim_col is not None and birim_col < len(row_values) else ""
                        konu_text = row_values[konu_col] if konu_col is not None and konu_col < len(row_values) else ""
                        kazanim_text = row_values[kazanim_col] if kazanim_col is not None and kazanim_col < len(row_values) else ""
                        
                        # Yeni öğrenme birimi başladığında
                        if birim_text and birim_text != 'nan' and len(birim_text) > 3:
                            # Önceki birimi kaydet
                            if current_birim:
                                ogrenme_birimleri.append({
                                    "birim_adi": current_birim,
                                    "konular": list(set(current_konular)),  # Duplicate'leri kaldır
                                    "kazanimlar": list(set(current_kazanimlar))
                                })
                            
                            # Yeni birim başlat
                            current_birim = clean_text(birim_text)
                            current_konular = []
                            current_kazanimlar = []
                        
                        # Konuları işle
                        if konu_text and konu_text != 'nan' and len(konu_text) > 3:
                            # Numaralı listeler ve satır sonları ile ayrılmış konuları ayır
                            konu_items = re.split(r'\n+|\d+\.\s*', konu_text)
                            for item in konu_items:
                                clean_item = clean_text(item)
                                if clean_item and len(clean_item) > 3:
                                    current_konular.append(clean_item)
                        
                        # Kazanımları işle (sadece ana başlıklar)
                        if kazanim_text and kazanim_text != 'nan' and len(kazanim_text) > 10:
                            # Sadece ana kazanım başlıklarını al, detayları çıkar
                            kazanim_lines = kazanim_text.split('\n')
                            for line in kazanim_lines:
                                clean_line = clean_text(line)
                                # Ana kazanım başlıklarını filtrele (çok uzun detayları atla)
                                if clean_line and 10 < len(clean_line) < 200:
                                    # Sadece kazanım cümlesi gibi görünenleri al
                                    if any(word in clean_line.lower() for word in ['yapar', 'açıklar', 'tanır', 'bilir', 'kullanır', 'uygular']):
                                        current_kazanimlar.append(clean_line)
                    
                    # Son birimi kaydet
                    if current_birim:
                        ogrenme_birimleri.append({
                            "birim_adi": current_birim,
                            "konular": list(set(current_konular)),
                            "kazanimlar": list(set(current_kazanimlar))
                        })
                    
                    break
            
            if found_main_table:
                break
        
        return ogrenme_birimleri
        
    except Exception as e:
        print(f"Error extracting öğrenme birimleri: {str(e)}")
        return []

def extract_uygulama_faaliyetleri(pdf_path):
    """
    PDF'den uygulama faaliyetlerini çıkar
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        uygulama_faaliyetleri = []
        
        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and ('UYGULAMA FAALİYETLERİ' in cell.upper() or 'TEMRİNLER' in cell.upper()):
                        # Alt satırlardaki faaliyetleri topla
                        for k in range(i + 1, len(df)):
                            next_row = df.iloc[k]
                            for next_cell in next_row:
                                content = str(next_cell).strip()
                                if content and content != 'nan' and len(content) > 10:
                                    # Madde işaretleriyle ayrılmış faaliyetleri ayır
                                    if '•' in content or '-' in content or content.startswith(('1.', '2.', '3.')):
                                        faaliyet_items = re.split(r'[•\-]\s*|\d+\.\s*', content)
                                        for item in faaliyet_items:
                                            clean_item = clean_text(item)
                                            if clean_item and len(clean_item) > 10:
                                                uygulama_faaliyetleri.append(clean_item)
                                    else:
                                        clean_item = clean_text(content)
                                        if clean_item and len(clean_item) > 10:
                                            uygulama_faaliyetleri.append(clean_item)
        
        return uygulama_faaliyetleri[:10]  # İlk 10 faaliyet
        
    except Exception as e:
        print(f"Error extracting uygulama faaliyetleri: {str(e)}")
        return []

def extract_olcme_degerlendirme(pdf_path):
    """
    PDF'den ölçme ve değerlendirme yöntemlerini çıkar
    Basit regex ile ölçme araçlarını tespit eder
    """
    try:
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='1')
        
        olcme_yontemleri = []
        
        for table in tables:
            df = table.df
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'ÖLÇME VE DEĞERLENDİRME' in cell.upper():
                        # İçerik aynı hücrede ise
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        else:
                            # Yan hücrede ise
                            if j + 1 < len(row):
                                content = str(row.iloc[j + 1]).strip()
                            else:
                                # Alt satırda ise
                                if i + 1 < len(df):
                                    next_row = df.iloc[i + 1]
                                    content = str(next_row.iloc[0]).strip()
                                else:
                                    continue
                        
                        if content and content != 'nan':
                            # Bilinen ölçme araçlarını tespit et
                            olcme_araclari = [
                                'gözlem formu', 'derecelendirme ölçeği', 'dereceli puanlama anahtarı',
                                'öz değerlendirme', 'akran değerlendirme', 'performans değerlendirme',
                                'portfolyo', 'proje değerlendirme', 'rubrik', 'kontrol listesi',
                                'açık uçlu', 'çoktan seçmeli', 'doğru yanlış', 'eşleştirme'
                            ]
                            
                            content_lower = content.lower()
                            for arac in olcme_araclari:
                                if arac in content_lower:
                                    # Formu/formları kelimelerini temizle
                                    clean_arac = arac.replace(' formu', '').replace(' formları', '')
                                    if clean_arac not in olcme_yontemleri:
                                        olcme_yontemleri.append(clean_arac.title())
        
        return olcme_yontemleri
        
    except Exception as e:
        print(f"Error extracting ölçme değerlendirme: {str(e)}")
        return []

def oku(pdf_path):
    """
    PDF'den tüm ders bilgilerini çıkar ve JSON formatında döndür
    """
    try:
        filename = os.path.basename(pdf_path)
        print(f"Processing: {filename}")
        
        # Temel bilgileri çıkar
        ders_adi = extract_ders_adi(pdf_path)
        ders_sinifi = extract_ders_sinifi(pdf_path) 
        ders_saati = extract_ders_saati(pdf_path)
        dersin_amaci = extract_dersin_amaci(pdf_path)
        genel_kazanimlar = extract_genel_kazanimlar(pdf_path)
        ortam_donanimi = extract_ortam_donanimi(pdf_path)
        olcme_degerlendirme = extract_olcme_degerlendirme(pdf_path)
        kazanim_tablosu = extract_kazanim_tablosu(pdf_path)
        ogrenme_birimleri = extract_ogrenme_birimleri(pdf_path)
        uygulama_faaliyetleri = extract_uygulama_faaliyetleri(pdf_path)
        
        # JSON yapısını oluştur
        result = {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source_file": filename,
                "file_path": pdf_path,
                "status": "success" if any([ders_adi, ders_sinifi, ders_saati, dersin_amaci]) else "partial"
            },
            "ders_bilgileri": {
                "ders_adi": ders_adi,
                "ders_sinifi": ders_sinifi,
                "haftalik_ders_saati": ders_saati,
                "dersin_amaci": dersin_amaci,
                "dersin_genel_kazanimlari": genel_kazanimlar,
                "egitim_ortam_donanimi": ortam_donanimi,
                "olcme_degerlendirme": olcme_degerlendirme
            },
            "ogrenme_birimleri_ozeti": kazanim_tablosu,
            "ogrenme_birimleri_detayi": ogrenme_birimleri,
            "uygulama_faaliyetleri": uygulama_faaliyetleri
        }
        
        return result
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return {
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source_file": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "status": "error",
                "error": str(e)
            },
            "ders_bilgileri": {},
            "ogrenme_birimleri_ozeti": [],
            "ogrenme_birimleri_detayi": [],
            "uygulama_faaliyetleri": []
        }

def process_directory(directory_path, output_json="oku_sonuc.json"):
    """
    Dizindeki tüm PDF'leri işle ve sonuçları JSON'a kaydet
    """
    results = {}
    
    pdf_pattern = os.path.join(directory_path, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    print(f"Found {len(pdf_files)} PDF files in {directory_path}")
    
    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        result = oku(pdf_file)
        results[filename] = result
        
        print(f"✓ Processed {filename}")
        print("-" * 50)
    
    # JSON'a kaydet
    output_data = {
        "metadata": {
            "processed_at": datetime.now().isoformat(),
            "source_directory": os.path.abspath(directory_path),
            "total_files": len(results),
            "successful_files": sum(1 for r in results.values() if r["metadata"]["status"] == "success"),
            "partial_files": sum(1 for r in results.values() if r["metadata"]["status"] == "partial"),
            "failed_files": sum(1 for r in results.values() if r["metadata"]["status"] == "error")
        },
        "results": results
    }
    
    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Results saved to: {output_json}")
    except Exception as e:
        print(f"✗ Error saving JSON file: {str(e)}")
    
    return results

def main():
    """
    Ana fonksiyon - dizindeki PDF'leri işle
    """
    directory_path = "."  # Current directory
    output_json = "oku_sonuc.json"
    
    results = process_directory(directory_path, output_json)
    
    # Özet yazdır
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    for filename, data in results.items():
        print(f"\n{filename}:")
        ders_bilgileri = data.get("ders_bilgileri", {})
        print(f"  Ders Adı: {ders_bilgileri.get('ders_adi', 'N/A')}")
        print(f"  Sınıf: {ders_bilgileri.get('ders_sinifi', 'N/A')}")
        print(f"  Ders Saati: {ders_bilgileri.get('haftalik_ders_saati', 'N/A')}")
        print(f"  Status: {data['metadata']['status']}")

if __name__ == "__main__":
    main()