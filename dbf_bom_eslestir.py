import os
import json
import unicodedata

DBF_ROOT = "dbf"
SCRAPED_DATA_PATH = "data/scraped_data.json"
OUTPUT_PATH = "data/scraped_data_with_dbf.json"

def normalize(s):
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = s.replace("_", " ").replace("-", " ").replace(".", " ").replace("pdf", "")
    s = s.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g").replace("ü", "u").replace("ö", "o")
    s = " ".join(s.split())
    return s

def find_all_dbf_pdfs():
    alan_to_pdfs = {}
    for alan_klasor in os.listdir(DBF_ROOT):
        alan_path = os.path.join(DBF_ROOT, alan_klasor)
        if not os.path.isdir(alan_path):
            continue
        pdfs = []
        for root, dirs, files in os.walk(alan_path):
            for fname in files:
                if fname.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(root, fname))
        if pdfs:
            alan_to_pdfs[alan_klasor] = pdfs
    return alan_to_pdfs

def main():
    with open(SCRAPED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    alan_to_pdfs = find_all_dbf_pdfs()

    for alan_id, alan in data["alanlar"].items():
        alan_adi = alan["isim"]
        # DBF dizininde karşılık gelen klasörü bul
        alan_klasor = None
        for k in alan_to_pdfs:
            if normalize(k) == normalize(alan_adi):
                alan_klasor = k
                break
        if not alan_klasor:
            continue
        pdfs = alan_to_pdfs[alan_klasor]
        # Her ders için eşleşen PDF bul
        for ders_link, ders in alan.get("dersler", {}).items():
            ders_adi_norm = normalize(ders["isim"])
            best_match = None
            best_score = 0
            for pdf_path in pdfs:
                pdf_name = os.path.basename(pdf_path)
                pdf_name_norm = normalize(pdf_name)
                # Basit benzerlik: ders adı pdf adında geçiyorsa
                if ders_adi_norm in pdf_name_norm:
                    score = len(ders_adi_norm)
                else:
                    # Ortak kelime sayısı
                    score = len(set(ders_adi_norm.split()) & set(pdf_name_norm.split()))
                if score > best_score:
                    best_score = score
                    best_match = pdf_path
            if best_match and best_score > 0:
                ders["dbf_pdf_path"] = best_match

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
