import re
import json
import PyPDF2

def extract_data_from_pdf(pdf_path):
    # PDF'den metni çıkar
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        lines = text.split('\n')
    
    # Ham metni dosyaya kaydet
    with open("data/raw_text.txt", 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Alan ve Dal verilerini saklamak için liste
    alanlar = []
    current_alan = None
    current_dallar = []
    
    # Alan ve Dal bilgilerini çıkaracak regex patternleri
    alan_pattern = re.compile(r'^\d+\s+(.+?)(?:\s+\d+|$)', re.DOTALL)
    dal_pattern = re.compile(r'^\d+\s+(.+?)(?:\s+\d+|$)', re.DOTALL)
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        print(f"Line {i}: {line}")
        if not line or line.startswith("S.NO") or line.startswith("MESLEKİ") or line.startswith("TELAFİ"):
            i += 1
            continue
            
        # Alan adı kontrolü
        if line[0].isdigit() and len(line.split()) > 1:
            parts = line.split()
            if len(parts) > 1 and parts[0].isdigit():
                # Alan tespiti için daha katı bir kontrol
                alan_match = alan_pattern.match(line)
                if alan_match:
                    alan_name = alan_match.group(1).strip()
                    # Alan adını temizle
                    alan_name = re.sub(r'\d+$', '', alan_name).strip()
                    alan_name = re.sub(r'(MESLEKİ.*|TELAFİ.*|S\.NO.*)', '', alan_name).strip()
                    if not alan_name.startswith("ALAN") and not any(char.isdigit() for char in alan_name.split()[0]):
                        print(f"Alan detected: {alan_name}")
                        if current_alan:
                            if current_dallar:
                                current_alan["dallar"] = current_dallar
                            else:
                                current_alan["dallar"] = []
                            alanlar.append(current_alan)
                        current_alan = {"alan": alan_name, "kod": "", "dallar": []}
                        current_dallar = []
                        i += 1
                        continue
                if current_alan:
                    # Dal tespiti
                    dal_match = dal_pattern.match(line)
                    if dal_match:
                        dal_name = dal_match.group(1).strip()
                        if dal_name and not dal_name.startswith("ALAN"):
                            # Dal adını temizle
                            dal_name = re.sub(r'\d+$', '', dal_name).strip()
                            print(f"Dal detected for {current_alan['alan']}: {dal_name}")
                            current_dallar.append({"dal": dal_name, "kod": "", "dersler": []})
                    i += 1
                    continue
                
        i += 1
    
    # Son alan ve dalları ekle
    if current_alan:
        if current_dallar:
            current_alan["dallar"] = current_dallar
        else:
            current_alan["dallar"] = []
        alanlar.append(current_alan)
    
    return alanlar

def save_to_json(data, output_path):
    # JSON dosyasına kaydet
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    pdf_path = "data/alan-dal-listesi-2023.pdf"
    output_path = "data/extracted_alan_dal.json"
    extracted_data = extract_data_from_pdf(pdf_path)
    save_to_json(extracted_data, output_path)
    print(f"Veriler {output_path} dosyasına kaydedildi.")
    print(f"Ham metin data/raw_text.txt dosyasına kaydedildi.")
