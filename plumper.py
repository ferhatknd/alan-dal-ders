import pdfplumber
import re
import sys
import os

# İlk PDF'den Öğrenme Birimleri ve Kazanımları çıkarma (Tabloyu dikkate alarak)
def extract_learning_units(pdf_path):
    print(f"İlk PDF işleniyor: {pdf_path}")
    learning_units = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Toplam sayfa sayısı: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    print(f"Sayfa {i+1} metni çekiliyor...")
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                if row and isinstance(row, list) and len(row) >= 2:
                                    if "Öğrenme Biriminin Adı" in str(row[0]):
                                        unit_name = row[1].strip() if row[1] else "Bilinmeyen Birim"
                                        learning_units.append({"name": unit_name, "outcomes": []})
                                    elif "Kazanım" in str(row[0]) and learning_units:
                                        outcomes = [o.strip() for o in re.split(r"[.;]\s*", str(row[1])) if o and o.strip()]
                                        if outcomes:
                                            learning_units[-1]["outcomes"].extend(outcomes)
                    else:
                        lines = text.split('\n')
                        for line in lines:
                            if "Öğrenme Biriminin Adı" in line:
                                unit_name = re.search(r"Öğrenme Biriminin Adı\s*(.+)", line)
                                if unit_name:
                                    learning_units.append({"name": unit_name.group(1).strip(), "outcomes": []})
                            elif "Kazanım" in line and learning_units:
                                outcomes = re.split(r"[.;]\s*", line.replace("Kazanım", "").strip())
                                outcomes = [o.strip() for o in outcomes if o and o.strip()]
                                if outcomes:
                                    learning_units[-1]["outcomes"].extend(outcomes)
                else:
                    print(f"Sayfa {i+1} metni boş veya okunamadı.")
        if not learning_units:
            print("Hiçbir Öğrenme Birimi bulunamadı.")
        else:
            for unit in learning_units:
                print(f"Bulunan Öğrenme Birimi: {unit['name']}")
                print(f"Bulunan Kazanımlar: {unit['outcomes']}")
        return learning_units
    except Exception as e:
        print(f"İlk PDF işlenirken hata oluştu: {e}")
        return []

# İkinci PDF'den İçindekiler kısmını çıkarma
def extract_toc(pdf_path):
    print(f"İkinci PDF işleniyor: {pdf_path}")
    toc = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Toplam sayfa sayısı: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text and "İÇİNDEKİLER" in text.upper():
                        print(f"İçindekiler sayfası bulundu: Sayfa {i+1}")
                        lines = text.split('\n')
                        for line in lines:
                            match = re.match(r"^(.*?)\s*\.*\s*(\d+)$", line.strip())
                            if match:
                                title, page_num = match.groups()
                                print(f"Bulunan İçindekiler başlığı: {title} (Sayfa {page_num})")
                                toc.append({"title": title.strip(), "page": page_num})
                    else:
                        print(f"Sayfa {i+1} metni: {text[:100] if text else 'Boş'}")
                except Exception as e:
                    print(f"Sayfa {i+1} işlenirken hata: {e}")
                    continue
        if not toc:
            print("İçindekiler kısmı bulunamadı.")
        return toc
    except Exception as e:
        print(f"İkinci PDF işlenirken genel hata: {e}")
        return []

# Verileri eşleştirip formatlı çıktı üretme
def generate_output(learning_units, toc):
    if not learning_units or not toc:
        print("Hata: Öğrenme Birimleri veya İçindekiler verisi eksik.")
        return
    for unit in learning_units:
        print(f"\nÖğrenme Birimi: {unit['name']}")
        print("Kazanımlar:")
        for i, outcome in enumerate(unit['outcomes'], 1):
            print(f"{i}. {outcome}")
        print("\nKitaptaki Konular:\n")
        found = False
        for toc_item in toc:
            if unit['name'].lower() in toc_item['title'].lower():
                print(f"{toc_item['title']} {'...' * 50}{toc_item['page']}")
                found = True
                for sub_item in toc:
                    if sub_item['title'].startswith(toc_item['title'].split()[0]) and sub_item['title'] != toc_item['title']:
                        print(f"{sub_item['title']} {'...' * 50}{sub_item['page']}")
        if not found:
            print(f"Bu Öğrenme Birimi için İçindekiler'de eşleşme bulunamadı: {unit['name']}")
        print("\n" + "="*80 + "\n")

# PDF dosyalarının yolları
first_pdf = "hayvanyetistiriciligi_10.pdf"
second_pdf = "HYS2024ZOO1005.pdf"

# Dosya varlığını kontrol et
if not os.path.exists(first_pdf):
    print(f"Hata: {first_pdf} dosyası bulunamadı.")
    sys.exit(1)
if not os.path.exists(second_pdf):
    print(f"Hata: {second_pdf} dosyası bulunamadı.")
    sys.exit(1)

# Verileri çıkar ve çıktıyı üret
learning_units = extract_learning_units(first_pdf)
toc = extract_toc(second_pdf)
generate_output(learning_units, toc)