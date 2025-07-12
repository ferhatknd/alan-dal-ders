import os
import json
import unicodedata
from oku import extract_ders_adi, extract_ders_sinifi

def is_pdf(path):
    """
    Dosyanın gerçek PDF olup olmadığını kontrol eder (başında '%PDF' imzasını arar)
    """
    try:
        with open(path, 'rb') as f:
            return f.read(4) == b'%PDF'
    except:
        return False

DBF_ROOT = "dbf"
SCRAPED_DATA_PATH = "data/scraped_data.json"
OUTPUT_PATH = "data/scraped_data_with_dbf.json"

def normalize(s):
    """
    Metni küçük harfe çevirir, unicode ayrımları kaldırır, stop-word'leri temizler.
    """
    if not s:
        return ""
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Temizlemeler
    for ch in ["_", "-", ".", "pdf"]:
        s = s.replace(ch, " ")
    # Türkçe karakterler
    replacements = {"ı":"i", "ş":"s", "ç":"c", "ğ":"g", "ü":"u", "ö":"o"}
    for orig, repl in replacements.items():
        s = s.replace(orig, repl)
    # Fazla boşlukları temizle
    return " ".join(s.split())

def find_all_dbf_pdfs():
    """
    dbf klasöründeki tüm .pdf dosyalarını toplayıp alan bazlı döner.
    """
    alan_to_pdfs = {}
    for alan_klasor in os.listdir(DBF_ROOT):
        alan_path = os.path.join(DBF_ROOT, alan_klasor)
        if not os.path.isdir(alan_path):
            continue
        pdfs = []
        for root, dirs, files in os.walk(alan_path):
            for fname in files:
                full = os.path.join(root, fname)
                if fname.lower().endswith(".pdf") and is_pdf(full):
                    pdfs.append(full)
        if pdfs:
            alan_to_pdfs[alan_klasor] = pdfs
    return alan_to_pdfs

def main():
    # Scraped data yükle
    with open(SCRAPED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    alan_to_pdfs = find_all_dbf_pdfs()

    # PDF metadata extract (ders adı ve sınıf)
    pdf_metadata = {}
    for folder, pdfs in alan_to_pdfs.items():
        for pdf_path in pdfs:
            if not is_pdf(pdf_path):
                continue
            try:
                ders_ad = extract_ders_adi(pdf_path)
                ders_snf = extract_ders_sinifi(pdf_path)
            except Exception:
                ders_ad = None
                ders_snf = None
            pdf_metadata[pdf_path] = {
                "ders_adi_norm": normalize(ders_ad),
                "ders_sinifi": ders_snf
            }

    # Her alan ve ders için eşleştirme yap
    for alan_id, alan in data.get("alanlar", {}).items():
        alan_adi = alan.get("isim", "")
        # Klasör eşleştirme
        alan_klasor = next((k for k in alan_to_pdfs if normalize(k) == normalize(alan_adi)), None)
        if not alan_klasor:
            continue
        pdfs = alan_to_pdfs[alan_klasor]
        for ders_link, ders in alan.get("dersler", {}).items():
            ders_adi_norm = normalize(ders.get("isim"))
            # Sinif listesi
            sinif_list = []
            for s in ders.get("siniflar", []):
                try:
                    sinif_list.append(int(s))
                except:
                    pass
            # Override: metadata eşleştirmesi
            match = next(
                (p for p in pdfs
                 if pdf_metadata.get(p, {}).get("ders_adi_norm") == ders_adi_norm
                 and pdf_metadata.get(p, {}).get("ders_sinifi") in sinif_list),
                None
            )
            if match:
                ders["dbf_pdf_path"] = match
                continue
            # Fallback: isim bazlı benzerlik
            best, best_score = None, 0
            for p in pdfs:
                name_norm = normalize(os.path.basename(p))
                if ders_adi_norm and ders_adi_norm in name_norm:
                    score = len(ders_adi_norm)
                else:
                    score = len(set(ders_adi_norm.split()) & set(name_norm.split()))
                if score > best_score:
                    best, best_score = p, score
            if best and best_score > 0:
                ders["dbf_pdf_path"] = best

    # Çıktıyı kaydet
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
