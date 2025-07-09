# dbf_parser.py

import os
import re
import argparse
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional

# Constants from the briefing
PLACEHOLDER_ALAN = "HASTA VE YAŞLI HİZMETLERİ" # Örnek PDF'lere göre varsayılan alan
PLACEHOLDER_DAL = "YAŞLI BAKIMI" # Örnek PDF'lere göre varsayılan dal

class CourseData:
    """Holds all structured data for a single course."""
    def __init__(self, filename: str):
        self.filename = filename
        self.ders_adi: Optional[str] = None
        self.sinif: Optional[int] = None
        self.ders_saati: Optional[int] = None
        self.amac: Optional[str] = None
        self.kazanimlar_ana: List[str] = []
        self.arac_gerecler: List[str] = []
        self.ogrenme_birimleri: List[Dict[str, Any]] = []
        # Not in sample PDFs, but included for completeness from briefing
        self.olcme_yontemleri: List[str] = [] 
        print(f"[{self.filename}] Nesne oluşturuldu.")

def clean_text(text: str) -> str:
    """Removes extra spaces, newlines and quotes from text."""
    return ' '.join(text.replace('"', '').replace('•', '').strip().split())

def parse_general_info(content: List[str], data: CourseData):
    """Parses the main course details from the first page."""
    print(f"[{data.filename}] Genel Bilgiler işleniyor...")
    
    # A simple regex-based parser for key-value pairs
    patterns = {
        'ders_adi': re.compile(r"DERSİN ADI\s*\"(.*?)\"", re.DOTALL),
        'sinif': re.compile(r"DERSİN SINIFI\s*\"(\d+)\.\s*Sınıf\"", re.DOTALL),
        'ders_saati': re.compile(r"DERSİN SÜRESİ\s*\"(\d+)\s*Ders Saati\"", re.DOTALL),
        'amac': re.compile(r"DERSİN AMACI\s*\"(.*?)\"", re.DOTALL),
        'kazanimlar_ana': re.compile(r"DERSİN\s*ÖĞRENME\s*KAZANIMLARI\s*\"(.*?)\"", re.DOTALL),
        'arac_gerecler': re.compile(r"Donanım:\s*(.*?)\"", re.DOTALL)
    }
    
    full_text = "".join(content)

    data.ders_adi = clean_text(patterns['ders_adi'].search(full_text).group(1)) if patterns['ders_adi'].search(full_text) else "Bilinmiyor"
    
    sinif_match = patterns['sinif'].search(full_text)
    if sinif_match:
        data.sinif = int(sinif_match.group(1))

    ders_saati_match = patterns['ders_saati'].search(full_text)
    if ders_saati_match:
        data.ders_saati = int(ders_saati_match.group(1))

    amac_match = patterns['amac'].search(full_text)
    if amac_match:
        data.amac = clean_text(amac_match.group(1))

    kazanimlar_match = patterns['kazanimlar_ana'].search(full_text)
    if kazanimlar_match:
        # Split numbered outcomes
        raw_kazanimlar = kazanimlar_match.group(1).strip()
        data.kazanimlar_ana = [clean_text(k) for k in re.split(r'\d+\.\s*', raw_kazanimlar) if k.strip()]

    arac_gerecler_match = patterns['arac_gerecler'].search(full_text)
    if arac_gerecler_match:
        raw_gerecler = arac_gerecler_match.group(1).strip()
        # Clean and split the equipment list
        items = re.split(r',\s*(?![^()]*\))', raw_gerecler) # Split by comma, ignoring commas in parentheses
        data.arac_gerecler = [clean_text(item) for item in items if item.strip() and item.strip() != 'vb.)']

    print(f"[{data.filename}] Ders Adı: {data.ders_adi}, Sınıf: {data.sinif}")

def parse_learning_units(content: List[str], data: CourseData):
    """Parses the Learning Units table to get names and hours."""
    print(f"[{data.filename}] Öğrenme Birimi Süreleri işleniyor...")
    
    # Find the table "DERSİN KAZANIM TABLOSU"
    try:
        table_start_index = content.index('"DERSİN KAZANIM\n TABLOSU\n","Kişisel Bakım İhtiyaçları\n\n\nVücut Temizliği\n\n\n4\n\n\n4\n\n\n42\n\n\n44\n\n\n23,3\n\n\n24,4\n"')
        table_str = content[table_start_index-1] + content[table_start_index] + content[table_start_index+1]
        
        # This is a very specific parser for the given PDF table format.
        # It relies on the structure being consistent.
        lines = table_str.replace('"', '').strip().split('\n')
        unit_names = []
        unit_hours = []

        # Extract names and hours based on their position in the messy string
        raw_units = [lines[0], lines[4], lines[7], lines[10]]
        raw_hours = [lines[1], lines[5], lines[8], lines[11]]

        for name in raw_units:
            if name.strip():
                unit_names.append(clean_text(name))
        
        for hour in raw_hours:
            if hour.strip().isdigit():
                unit_hours.append(int(hour))

        for name, hour in zip(unit_names, unit_hours):
             data.ogrenme_birimleri.append({
                "ogrenme_birimi": name,
                "ders_saati": hour,
                "konular": []
            })
             print(f"  -> Birim bulundu: {name} ({hour} saat)")

    except (ValueError, IndexError) as e:
        print(f"[{data.filename}] UYARI: Öğrenme Birimi Süre Tablosu bulunamadı veya format farklı. {e}")


def parse_detailed_tables(content: List[str], data: CourseData):
    """Parses the detailed topic/outcome tables across multiple pages."""
    print(f"[{data.filename}] Detaylı Konu ve Kazanımlar işleniyor...")
    
    # Regex to find all table-like structures
    table_pattern = re.compile(r'source: \d+\] The following table:\n"([^"]*)"', re.DOTALL)
    
    current_unit_name = ""
    current_topic_name = ""
    unit_dict = {unit['ogrenme_birimi']: unit for unit in data.ogrenme_birimleri}

    # Process all found tables
    for match in table_pattern.finditer("".join(content)):
        table_content = match.group(1)
        rows = table_content.strip().split('\n')
        
        for row in rows:
            cells = row.replace('"', '').split(',')
            if len(cells) < 3: continue

            # Heuristics based on the provided PDF structure
            cell_unit = clean_text(cells[0])
            cell_topic = clean_text(cells[1])
            cell_kazanim = " ".join(cells[2:]).strip()

            if cell_unit and cell_unit in unit_dict:
                current_unit_name = cell_unit

            if cell_topic:
                current_topic_name = clean_text(re.sub(r'^\d+\.\s*', '', cell_topic)) # Remove leading numbers
                if current_unit_name in unit_dict:
                    # Check if topic already exists
                    topic_exists = any(t['konu'] == current_topic_name for t in unit_dict[current_unit_name]['konular'])
                    if not topic_exists:
                        unit_dict[current_unit_name]['konular'].append({
                            "konu": current_topic_name,
                            "kazanimlar": []
                        })
                        print(f"    -> Konu eklendi: '{current_unit_name}' -> '{current_topic_name}'")

            if cell_kazanim and current_unit_name in unit_dict:
                # Find the current topic in the unit's topic list
                for topic_obj in unit_dict[current_unit_name]['konular']:
                    if topic_obj['konu'] == current_topic_name:
                        # Split bulleted items into separate outcomes
                        kazanimlar = [clean_text(k) for k in cell_kazanim.split('•') if clean_text(k)]
                        topic_obj['kazanimlar'].extend(kazanimlar)
                        break

def parse_temrinler(content: List[str], data: CourseData):
    """Parses the practical activities (Temrinler) and adds them as outcomes."""
    print(f"[{data.filename}] Uygulama Faaliyetleri (Temrinler) işleniyor...")
    
    try:
        # Find the start of the practical activities section
        temrin_start_index = -1
        for i, line in enumerate(content):
            if "UYGULAMA FAALİYETLERİ/TEMRİNLER" in line:
                temrin_start_index = i
                break
        
        if temrin_start_index == -1:
            print(f"[{data.filename}] UYARI: Uygulama Faaliyetleri bölümü bulunamadı.")
            return

        # Flatten the data for easier lookup
        topic_map = {}
        for unit in data.ogrenme_birimleri:
            for topic in unit['konular']:
                # Normalize topic names for matching
                normalized_topic = topic['konu'].replace(":", "").strip()
                topic_map[normalized_topic] = topic

        current_topic_key = ""
        # Iterate through the lines of the temrin section
        for line in content[temrin_start_index:]:
            cleaned_line = clean_text(line.replace('"',"").split(",")[0])
            
            if not cleaned_line: continue
            
            # Check if the line is a topic heading
            if cleaned_line in topic_map:
                current_topic_key = cleaned_line
                print(f"    -> Temrin konusu bulundu: {current_topic_key}")
                continue
            
            # If it's a bullet point, it's an outcome for the current topic
            if "•" in line and current_topic_key in topic_map:
                kazanim = clean_text(line.split("•")[1])
                if kazanim:
                    topic_map[current_topic_key]['kazanimlar'].append(kazanim)

    except Exception as e:
        print(f"[{data.filename}] HATA: Temrinler işlenirken bir sorun oluştu: {e}")

def generate_sql_for_course(data: CourseData) -> List[str]:
    """Generates a list of SQL commands based on the structured data."""
    print(f"[{data.filename}] SQL komutları oluşturuluyor...")
    
    sql = []
    
    # Use placeholders for Alan and Dal as they are not in the PDF
    alan_adi = PLACEHOLDER_ALAN
    dal_adi = PLACEHOLDER_DAL
    ders_adi_sql = data.ders_adi.replace("'", "''")
    amac_sql = data.amac.replace("'", "''")

    # 1. Alan
    sql.append(f"-- {data.ders_adi.upper()} DERSİ İÇİN VERİ GİRİŞİ --")
    sql.append(f"INSERT OR IGNORE INTO temel_plan_alan (alan_adi) VALUES ('{alan_adi}');")
    
    # 2. Dal
    sql.append("INSERT OR IGNORE INTO temel_plan_dal (dal_adi, alan_id)")
    sql.append(f"SELECT '{dal_adi}', id FROM temel_plan_alan WHERE alan_adi = '{alan_adi}';\n")
    
    # 3. Ders
    sql.append("INSERT OR IGNORE INTO temel_plan_ders (ders_adi, sinif, ders_saati, amac)")
    sql.append(f"VALUES ('{ders_adi_sql}', {data.sinif}, {data.ders_saati}, '{amac_sql}');\n")
    
    # 4. Ders-Dal İlişkisi
    sql.append("INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id)")
    sql.append("SELECT")
    sql.append(f"  (SELECT id FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}'),")
    sql.append(f"  (SELECT id FROM temel_plan_dal WHERE dal_adi = '{dal_adi}');\n")
    
    # 5. Dersin Ana Amaçları (Kazanımları)
    for amac in data.kazanimlar_ana:
        amac_sql_item = amac.replace("'", "''")
        sql.append("INSERT OR IGNORE INTO temel_plan_ders_amac (ders_id, amac)")
        sql.append(f"SELECT id, '{amac_sql_item}' FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}';")
    sql.append("")

    # 6. Araç-Gereçler
    for arac in data.arac_gerecler:
        arac_sql = arac.replace("'", "''")
        sql.append(f"INSERT OR IGNORE INTO temel_plan_arac (arac_gerec) VALUES ('{arac_sql}');")
        sql.append("INSERT OR IGNORE INTO temel_plan_ders_arac (ders_id, arac_id)")
        sql.append("SELECT")
        sql.append(f"  (SELECT id FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}'),")
        sql.append(f"  (SELECT id FROM temel_plan_arac WHERE arac_gerec = '{arac_sql}');")
    sql.append("")

    # 7. Öğrenme Birimleri, Konular ve Kazanımlar
    for unit in data.ogrenme_birimleri:
        unit_name_sql = unit['ogrenme_birimi'].replace("'", "''")
        unit_hours_sql = unit['ders_saati']
        sql.append(f"-- Öğrenme Birimi: {unit['ogrenme_birimi']} --")
        sql.append("INSERT OR IGNORE INTO temel_plan_ders_ogrenme_birimi (ders_id, ogrenme_birimi, ders_saati)")
        sql.append(f"SELECT id, '{unit_name_sql}', {unit_hours_sql} FROM temel_plan_ders WHERE ders_adi = '{ders_adi_sql}';\n")
        
        for topic in unit['konular']:
            topic_name_sql = topic['konu'].replace("'", "''")
            sql.append("INSERT OR IGNORE INTO temel_plan_ders_ob_konu (ogrenme_birimi_id, konu)")
            sql.append("SELECT ob.id, " + f"'{topic_name_sql}'")
            sql.append("FROM temel_plan_ders_ogrenme_birimi ob")
            sql.append("JOIN temel_plan_ders d ON d.id = ob.ders_id")
            sql.append(f"WHERE d.ders_adi = '{ders_adi_sql}' AND ob.ogrenme_birimi = '{unit_name_sql}';\n")

            for kazanim in topic['kazanimlar']:
                kazanim_sql = kazanim.replace("'", "''")
                sql.append("INSERT OR IGNORE INTO temel_plan_ders_ob_konu_kazanim (konu_id, kazanim)")
                sql.append("SELECT k.id, " + f"'{kazanim_sql}'")
                sql.append("FROM temel_plan_ders_ob_konu k")
                sql.append("JOIN temel_plan_ders_ogrenme_birimi ob ON ob.id = k.ogrenme_birimi_id")
                sql.append("JOIN temel_plan_ders d ON d.id = ob.ders_id")
                sql.append(f"WHERE d.ders_adi = '{ders_adi_sql}' AND ob.ogrenme_birimi = '{unit_name_sql}' AND k.konu = '{topic_name_sql}';")
            sql.append("")
    
    print(f"[{data.filename}] SQL oluşturma tamamlandı.")
    return sql

def create_schema_sql() -> str:
    """Creates the SQL for generating the database schema as per the briefing."""
    return """
-- Veritabanı Şeması Oluşturma (SQLite Uyumlu)
-- Bu komutlar, verilerin ekleneceği tabloları oluşturur.

DROP TABLE IF EXISTS temel_plan_alan;
CREATE TABLE temel_plan_alan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alan_adi TEXT NOT NULL UNIQUE,
    cop_url TEXT
);

DROP TABLE IF EXISTS temel_plan_dal;
CREATE TABLE temel_plan_dal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dal_adi TEXT NOT NULL,
    alan_id INTEGER NOT NULL,
    FOREIGN KEY (alan_id) REFERENCES temel_plan_alan(id)
);

DROP TABLE IF EXISTS temel_plan_ders;
CREATE TABLE temel_plan_ders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_adi TEXT NOT NULL UNIQUE,
    sinif INTEGER NOT NULL,
    ders_saati INTEGER NOT NULL,
    amac TEXT,
    dbf_url TEXT
);

DROP TABLE IF EXISTS temel_plan_ders_dal;
CREATE TABLE temel_plan_ders_dal (
    ders_id INTEGER NOT NULL,
    dal_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, dal_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (dal_id) REFERENCES temel_plan_dal(id)
);

DROP TABLE IF EXISTS temel_plan_ders_amac;
CREATE TABLE temel_plan_ders_amac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    amac TEXT NOT NULL,
    UNIQUE(ders_id, amac),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id)
);

DROP TABLE IF EXISTS temel_plan_arac;
CREATE TABLE temel_plan_arac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arac_gerec TEXT NOT NULL UNIQUE
);

DROP TABLE IF EXISTS temel_plan_ders_arac;
CREATE TABLE temel_plan_ders_arac (
    ders_id INTEGER NOT NULL,
    arac_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, arac_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (arac_id) REFERENCES temel_plan_arac(id)
);

DROP TABLE IF EXISTS temel_plan_olcme;
CREATE TABLE temel_plan_olcme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    olcme_degerlendirme TEXT NOT NULL UNIQUE
);

DROP TABLE IF EXISTS temel_plan_ders_olcme;
CREATE TABLE temel_plan_ders_olcme (
    ders_id INTEGER NOT NULL,
    olcme_id INTEGER NOT NULL,
    PRIMARY KEY (ders_id, olcme_id),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id),
    FOREIGN KEY (olcme_id) REFERENCES temel_plan_olcme(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ogrenme_birimi;
CREATE TABLE temel_plan_ders_ogrenme_birimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ders_id INTEGER NOT NULL,
    ogrenme_birimi TEXT NOT NULL,
    ders_saati INTEGER,
    UNIQUE(ders_id, ogrenme_birimi),
    FOREIGN KEY (ders_id) REFERENCES temel_plan_ders(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ob_konu;
CREATE TABLE temel_plan_ders_ob_konu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ogrenme_birimi_id INTEGER NOT NULL,
    konu TEXT NOT NULL,
    UNIQUE(ogrenme_birimi_id, konu),
    FOREIGN KEY (ogrenme_birimi_id) REFERENCES temel_plan_ders_ogrenme_birimi(id)
);

DROP TABLE IF EXISTS temel_plan_ders_ob_konu_kazanim;
CREATE TABLE temel_plan_ders_ob_konu_kazanim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    konu_id INTEGER NOT NULL,
    kazanim TEXT NOT NULL,
    UNIQUE(konu_id, kazanim),
    FOREIGN KEY (konu_id) REFERENCES temel_plan_ders_ob_konu(id)
);

-- Şema Oluşturma Sonu --

"""

def main():
    """Main function to drive the PDF parsing and SQL generation."""
    parser = argparse.ArgumentParser(
        description="MEB Ders Bilgi Formu (DBF) PDF'lerini işleyip SQL çıktısı üreten uygulama.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'directory', 
        type=str, 
        help='İşlenecek PDF dosyalarını içeren dizinin yolu.'
    )
    parser.add_argument(
        '-o', '--output', 
        type=str, 
        default='output.sql',
        help='Oluşturulacak SQL dosyasının adı (varsayılan: output.sql).'
    )
    args = parser.parse_args()

    pdf_directory = args.directory
    output_filename = args.output

    if not os.path.isdir(pdf_directory):
        print(f"Hata: Belirtilen dizin bulunamadı -> '{pdf_directory}'")
        return

    all_sql_commands = [create_schema_sql()]

    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"Uyarı: '{pdf_directory}' dizininde işlenecek PDF dosyası bulunamadı.")
        return

    for filename in pdf_files:
        filepath = os.path.join(pdf_directory, filename)
        print(f"\n{'='*50}\nİşleniyor: {filename}\n{'='*50}")
        
        try:
            # PDF dosyasını PyMuPDF (fitz) ile açıp metin içeriğini oku
            doc = fitz.open(filepath)
            full_text = ""
            for page in doc:
                full_text += page.get_text("text")
            doc.close()
            raw_content = full_text.splitlines()

            # Create a data object for the course
            course_data = CourseData(filename)
            
            # Start parsing different sections of the PDF
            parse_general_info(raw_content, course_data)
            parse_learning_units(raw_content, course_data)
            parse_detailed_tables(raw_content, course_data)
            parse_temrinler(raw_content, course_data)
            
            # Generate SQL for the parsed data
            sql_for_file = generate_sql_for_course(course_data)
            all_sql_commands.extend(sql_for_file)
            all_sql_commands.append("\n-- DERS SONU --\n")

        except Exception as e:
            print(f"HATA: '{filename}' dosyası işlenirken beklenmedik bir hata oluştu: {e}")

    # Write all commands to the output file
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(all_sql_commands))
        print(f"\n{'='*50}\nİşlem Tamamlandı. Tüm veriler '{output_filename}' dosyasına yazıldı.\n{'='*50}")
    except IOError as e:
        print(f"HATA: Çıktı dosyası '{output_filename}' yazılamadı: {e}")


if __name__ == '__main__':
    main()