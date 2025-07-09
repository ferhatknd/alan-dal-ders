# dbf_parser_final.py
# Gerekli kütüphaneler: pdfplumber

import os
import re
import argparse
import pdfplumber
from typing import List, Dict, Any, Optional

# --- Alan ve Dal Eşleştirme Haritası ---
ALAN_DAL_MAP = {
    "ANATOMİ VE FİZYOLOJİ": ("SAĞLIK HİZMETLERİ", "HEMŞİRE YARDIMCILIĞI"),
    "ATÖLYE": ("HASTA VE YAŞLI HİZMETLERİ", "YAŞLI BAKIMI")
}
DEFAULT_ALAN = "TANIMSIZ ALAN"
DEFAULT_DAL = "TANIMSIZ DAL"

class CourseData:
    """Bir derse ait tüm yapılandırılmış veriyi tutar."""
    def __init__(self, filename: str):
        self.filename = filename
        self.ders_adi: Optional[str] = None
        self.sinif: Optional[int] = None
        self.ders_saati: Optional[int] = None
        self.amac: Optional[str] = None
        self.kazanimlar_ana: List[str] = []
        self.arac_gerecler: List[str] = []
        self.ogrenme_birimleri: List[Dict[str, Any]] = []
        print(f"[{self.filename}] Nesne oluşturuldu.")

def clean_text(text: Optional[str]) -> str:
    """Metindeki gereksiz karakterleri, boşlukları ve satır sonlarını temizler."""
    if not text:
        return ""
    return ' '.join(text.replace('"', '').replace('•', '').strip().split())

def parse_pdf_content(pdf_path: str, data: CourseData):
    """PDF içeriğini yapısal olarak (tablo bazlı) analiz eder ve verileri ayrıştırır."""
    print(f"[{data.filename}] PDF yapısal olarak analiz ediliyor (tablo bazlı)...")
    
    unit_map = {}  # Öğrenme birimlerini hızlı erişim için haritalar

    with pdfplumber.open(pdf_path) as pdf:
        # 1. Adım: Tüm tabloları işle ve tiplerine göre verileri ayrıştır
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            if not tables:
                continue

            for table in tables:
                if not table or not table[0]: continue

                header = [clean_text(cell) for cell in table[0]]
                
                # Strateji 1: Genel Bilgi Tablosu (genellikle 2 sütunlu olur)
                if len(table[0]) == 2:
                    is_general_info_table = any("DERSİN ADI" in clean_text(row[0]) for row in table if row[0])
                    if is_general_info_table:
                        print(f"  -> Genel Bilgi Tablosu bulundu (Sayfa {page_num}).")
                        for row in table:
                            key = clean_text(row[0])
                            value = clean_text(row[1])
                            if "DERSİN ADI" in key: data.ders_adi = value
                            elif "DERSİN SINIFI" in key: data.sinif = int(re.search(r'\d+', value).group())
                            elif "DERSİN SÜRESİ" in key: data.ders_saati = int(re.search(r'\d+', value).group())
                            elif "DERSİN AMACI" in key: data.amac = value
                            elif "KAZANIMLARI" in key: data.kazanimlar_ana = [clean_text(k) for k in re.split(r'\d+\.\s*', value) if k.strip()]
                            elif "DONATIM" in key and value and value.lower().startswith("donanım:"):
                                data.arac_gerecler = [clean_text(item) for item in value.replace("Donanım:", "").split(',') if item.strip()]
                        continue

                # Strateji 2: Ünite ve Süreleri Tablosu
                if "ÖĞRENME BİRİMİ" in header and "DERS SAATİ" in header and "KONULAR" not in header:
                    print(f"  -> Öğrenme Birimi Süre Tablosu bulundu (Sayfa {page_num}).")
                    for row in table[1:]:
                        if len(row) >= 3 and row[0] and row[2]:
                            unit_name = clean_text(row[0])
                            unit_hours_str = clean_text(row[2])
                            if unit_name and "TOPLAM" not in unit_name and unit_hours_str.isdigit():
                                if not any(u['ogrenme_birimi'] == unit_name for u in data.ogrenme_birimleri):
                                    new_unit = {"ogrenme_birimi": unit_name, "ders_saati": int(unit_hours_str), "konular": []}
                                    data.ogrenme_birimleri.append(new_unit)
                                    unit_map[unit_name] = new_unit
                                    print(f"    -> Birim eklendi: {unit_name}")
                    continue

                # Strateji 3: Detaylı Kazanım Tablosu
                if "ÖĞRENME BİRİMİ" in header and "KONULAR" in header:
                    print(f"  -> Detaylı Kazanım Tablosu bulundu (Sayfa {page_num}).")
                    current_unit_name = ""
                    current_topic = None
                    for row in table[1:]:
                        if len(row) < 3: continue
                        
                        unit_cell = clean_text(row[0]) if row[0] else ""
                        topic_cell = clean_text(row[1]) if row[1] else ""
                        outcome_cell = clean_text(row[2]) if row[2] else ""

                        if unit_cell:
                            current_unit_name = unit_cell
                            current_topic = None # Yeni birime geçince konuyu sıfırla

                        if topic_cell and current_unit_name in unit_map:
                            topic_name = clean_text(re.sub(r'^\d+\.\s*', '', topic_cell))
                            current_unit_obj = unit_map[current_unit_name]
                            
                            topic_obj = next((t for t in current_unit_obj['konular'] if t['konu'] == topic_name), None)
                            if not topic_obj:
                                new_topic = {"konu": topic_name, "kazanimlar": []}
                                current_unit_obj['konular'].append(new_topic)
                                current_topic = new_topic
                                print(f"      -> Konu eklendi: '{current_unit_name}' -> '{topic_name}'")
                            else:
                                current_topic = topic_obj

                        if outcome_cell and current_topic:
                            current_topic['kazanimlar'].append(outcome_cell)
                    continue

        # 2. Adım: Temrinler bölümünü metin olarak işle
        full_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
        parse_temrinler(full_text, data)


def parse_temrinler(full_text: str, data: CourseData):
    """PDF metninden uygulama faaliyetlerini (temrinleri) bulur ve ilgili konulara ekler."""
    print(f"[{data.filename}] Uygulama Faaliyetleri (Temrinler) işleniyor...")
    temrin_section_match = re.search(r"UYGULAMA FAALİYETLERİ/TEMRİNLER(.*)", full_text, re.DOTALL)
    if not temrin_section_match:
        print(f"  [UYARI] Uygulama Faaliyetleri bölümü bulunamadı.")
        return

    temrin_text = temrin_section_match.group(1)
    
    # Tüm konuları ve ait oldukları üniteleri içeren düz bir harita oluştur
    topic_map = {}
    for unit in data.ogrenme_birimleri:
        for topic in unit['konular']:
            # Konu adını temizleyip anahtar yap
            key = clean_text(topic['konu']).replace(":", "")
            topic_map[key] = topic

    current_topic_key = None
    for line in temrin_text.strip().split('\n'):
        cleaned_line = clean_text(line).replace(":", "")
        if not cleaned_line: continue

        # Eğer satır, haritadaki bir konu başlığıyla eşleşiyorsa, onu aktif konu yap
        if cleaned_line in topic_map:
            current_topic_key = cleaned_line
            print(f"    -> Temrin konusu bulundu: {current_topic_key}")
            continue
        
        # Eğer aktif bir konu varsa ve satır bir kazanım ise ekle
        if current_topic_key and cleaned_line:
            kazanim = clean_text(line) # Orijinal, • içeren hali
            if kazanim not in topic_map[current_topic_key]['kazanimlar']:
                topic_map[current_topic_key]['kazanimlar'].append(kazanim)


def generate_sql_for_course(data: CourseData) -> List[str]:
    """Yapılandırılmış veriden SQL komut listesi oluşturur."""
    print(f"[{data.filename}] SQL komutları oluşturuluyor...")
    
    alan_adi, dal_adi = DEFAULT_ALAN, DEFAULT_DAL
    if data.ders_adi:
        for key, (alan, dal) in ALAN_DAL_MAP.items():
            if key in data.ders_adi.upper():
                alan_adi, dal_adi = alan, dal
                break
            
    sql = []
    ders_adi_sql = data.ders_adi.replace("'", "''") if data.ders_adi else "BİLİNMEYEN DERS"
    amac_sql = data.amac.replace("'", "''") if data.amac else ""

    sql.append(f"\n-- {ders_adi_sql.upper()} DERSİ İÇİN VERİ GİRİŞİ --")
    sql.append(f"INSERT OR IGNORE INTO temel_plan_alan (alan_adi) VALUES ('{alan_adi}');")
    sql.append(f"INSERT OR IGNORE INTO temel_plan_dal (dal_adi, alan_id) SELECT '{dal_adi}', id FROM temel_plan_alan WHERE alan_adi = '{alan_adi}';")
    sql.append(f"INSERT OR IGNORE INTO temel_plan_ders (ders_adi, sinif, ders_saati, amac, dbf_url) VALUES ('{ders_adi_sql}', {data.sinif or 'NULL'}, {data.ders_saati or 'NULL'}, '{amac_sql}', '{data.filename}');")
    sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id) SELECT (SELECT id FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}'), (SELECT id FROM temel_plan_dal WHERE dal_adi = '{dal_adi}');\n")
    
    for amac in data.kazanimlar_ana:
        sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_amac (ders_id, amac) SELECT id, '{amac.replace("'", "''")}' FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}';")
    
    for arac in data.arac_gerecler:
        arac_sql = arac.replace("'", "''")
        sql.append(f"INSERT OR IGNORE INTO temel_plan_arac (arac_gerec) VALUES ('{arac_sql}');")
        sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_arac (ders_id, arac_id) SELECT (SELECT id FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}'), (SELECT id FROM temel_plan_arac WHERE arac_gerec = '{arac_sql}');")

    for unit in data.ogrenme_birimleri:
        unit_name_sql = unit['ogrenme_birimi'].replace("'", "''")
        sql.append(f"\n-- Öğrenme Birimi: {unit['ogrenme_birimi']} --")
        sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_ogrenme_birimi (ders_id, ogrenme_birimi, ders_saati) SELECT id, '{unit_name_sql}', {unit['ders_saati']} FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}';")
        
        for topic in unit['konular']:
            topic_name_sql = topic['konu'].replace("'", "''")
            sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_ob_konu (ogrenme_birimi_id, konu) SELECT ob.id, '{topic_name_sql}' FROM temel_plan_ders_ogrenme_birimi ob JOIN temel_plan_ders d ON d.id = ob.ders_id WHERE d.ders_adi = '{ders_adi_sql}' AND ob.ogrenme_birimi = '{unit_name_sql}';")

            for kazanim in topic['kazanimlar']:
                kazanim_sql = kazanim.replace("'", "''")
                sql.append(f"INSERT OR IGNORE INTO temel_plan_ders_ob_konu_kazanim (konu_id, kazanim) SELECT k.id, '{kazanim_sql}' FROM temel_plan_ders_ob_konu k JOIN temel_plan_ders_ogrenme_birimi ob ON ob.id = k.ogrenme_birimi_id JOIN temel_plan_ders d ON d.id = ob.ders_id WHERE d.ders_adi = '{ders_adi_sql}' AND k.konu = '{topic_name_sql}' AND ob.ogrenme_birimi = '{unit_name_sql}';")
    
    print(f"[{data.filename}] SQL oluşturma tamamlandı.")
    return sql

def create_schema_sql() -> str:
    """Veritabanı şemasını oluşturan SQL komutlarını döndürür."""
    # Bu fonksiyon değiştirilmedi.
    return """
-- Veritabanı Şeması Oluşturma (SQLite Uyumlu)
DROP TABLE IF EXISTS temel_plan_ders_ob_konu_kazanim;
DROP TABLE IF EXISTS temel_plan_ders_ob_konu;
DROP TABLE IF EXISTS temel_plan_ders_ogrenme_birimi;
DROP TABLE IF EXISTS temel_plan_ders_olcme;
DROP TABLE IF EXISTS temel_plan_olcme;
DROP TABLE IF EXISTS temel_plan_ders_arac;
DROP TABLE IF EXISTS temel_plan_arac;
DROP TABLE IF EXISTS temel_plan_ders_amac;
DROP TABLE IF EXISTS temel_plan_ders_dal;
DROP TABLE IF EXISTS temel_plan_ders;
DROP TABLE IF EXISTS temel_plan_dal;
DROP TABLE IF EXISTS temel_plan_alan;

CREATE TABLE temel_plan_alan (id INTEGER PRIMARY KEY AUTOINCREMENT, alan_adi TEXT NOT NULL UNIQUE, cop_url TEXT);
CREATE TABLE temel_plan_dal (id INTEGER PRIMARY KEY AUTOINCREMENT, dal_adi TEXT NOT NULL, alan_id INTEGER NOT NULL, FOREIGN KEY (alan_id) REFERENCES temel_plan_alan(id));
CREATE TABLE temel_plan_ders (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_adi TEXT NOT NULL UNIQUE, sinif INTEGER, ders_saati INTEGER, amac TEXT, dbf_url TEXT);
CREATE TABLE temel_plan_ders_dal (ders_id INTEGER NOT NULL, dal_id INTEGER NOT NULL, PRIMARY KEY (ders_id, dal_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (dal_id) REFERENCES temel_plan_dal(id));
CREATE TABLE temel_plan_ders_amac (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER NOT NULL, amac TEXT NOT NULL, UNIQUE(ders_id, amac), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id));
CREATE TABLE temel_plan_arac (id INTEGER PRIMARY KEY AUTOINCREMENT, arac_gerec TEXT NOT NULL UNIQUE);
CREATE TABLE temel_plan_ders_arac (ders_id INTEGER NOT NULL, arac_id INTEGER NOT NULL, PRIMARY KEY (ders_id, arac_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (arac_id) REFERENCES temel_plan_arac(id));
CREATE TABLE temel_plan_olcme (id INTEGER PRIMARY KEY AUTOINCREMENT, olcme_degerlendirme TEXT NOT NULL UNIQUE);
CREATE TABLE temel_plan_ders_olcme (ders_id INTEGER NOT NULL, olcme_id INTEGER NOT NULL, PRIMARY KEY (ders_id, olcme_id), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id), FOREIGN KEY (olcme_id) REFERENCES temel_plan_olcme(id));
CREATE TABLE temel_plan_ders_ogrenme_birimi (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER NOT NULL, ogrenme_birimi TEXT NOT NULL, ders_saati INTEGER, UNIQUE(ders_id, ogrenme_birimi), FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id));
CREATE TABLE temel_plan_ders_ob_konu (id INTEGER PRIMARY KEY AUTOINCREMENT, ogrenme_birimi_id INTEGER NOT NULL, konu TEXT NOT NULL, UNIQUE(ogrenme_birimi_id, konu), FOREIGN KEY (ogrenme_birimi_id) REFERENCES temel_plan_ders_ogrenme_birimi(id));
CREATE TABLE temel_plan_ders_ob_konu_kazanim (id INTEGER PRIMARY KEY AUTOINCREMENT, konu_id INTEGER NOT NULL, kazanim TEXT NOT NULL, UNIQUE(konu_id, kazanim), FOREIGN KEY (konu_id) REFERENCES temel_plan_ders_ob_konu(id));
-- Şema Oluşturma Sonu --
"""

def main():
    """Ana fonksiyon: PDF'leri işler ve SQL dosyası oluşturur."""
    # Bu fonksiyon değiştirilmedi.
    parser = argparse.ArgumentParser(description="MEB Ders Bilgi Formu (DBF) PDF'lerini işleyip SQL çıktısı üreten uygulama.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('directory', type=str, help='İşlenecek PDF dosyalarını içeren dizinin yolu.')
    parser.add_argument('-o', '--output', type=str, default='output.sql', help='Oluşturulacak SQL dosyasının adı (varsayılan: output.sql).')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Hata: Belirtilen dizin bulunamadı -> '{args.directory}'")
        return

    all_sql_commands = [create_schema_sql()]
    pdf_files = [f for f in os.listdir(args.directory) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"Uyarı: '{args.directory}' dizininde işlenecek PDF dosyası bulunamadı.")
        return

    for filename in pdf_files:
        filepath = os.path.join(args.directory, filename)
        print(f"\n{'='*50}\nİşleniyor: {filename}\n{'='*50}")
        try:
            course_data = CourseData(filename)
            parse_pdf_content(filepath, course_data)
            sql_for_file = generate_sql_for_course(course_data)
            all_sql_commands.extend(sql_for_file)
            all_sql_commands.append("\n-- DERS SONU --\n")
        except Exception as e:
            print(f"HATA: '{filename}' dosyası işlenirken beklenmedik bir hata oluştu: {e}")
            import traceback
            traceback.print_exc()

    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_sql_commands))
        print(f"\n{'='*50}\nİşlem Tamamlandı. Tüm veriler '{args.output}' dosyasına yazıldı.\n{'='*50}")
    except IOError as e:
        print(f"HATA: Çıktı dosyası '{args.output}' yazılamadı: {e}")

if __name__ == '__main__':
    main()