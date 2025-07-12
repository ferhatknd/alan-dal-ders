#!/usr/bin/env python3
import pdfplumber

def debug_kazanim_table():
    """
    Page 2'deki kazanım tablosunu debug et
    """
    pdf_path = "ATÖLYE_DBF_10.pdf"
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[1]  # Page 2 (0-indexed)
        tables = page.extract_tables()
        
        print("=== Page 2 Tables ===")
        for table_idx, table in enumerate(tables):
            print(f"\nTable {table_idx + 1}:")
            print(f"Dimensions: {len(table)} rows x {len(table[0]) if table else 0} cols")
            
            for row_idx, row in enumerate(table):
                print(f"Row {row_idx}: {row}")
                
                # Bu satırda öğrenme birimi var mı kontrol et
                if row and len(row) > 0:
                    first_cell = str(row[0]) if row[0] else ""
                    if len(first_cell) > 5 and any(keyword in first_cell for keyword in ['Arama', 'Kurtarma', 'Asansör', 'Kuyu', 'İlkyardım', 'Yüksek']):
                        print(f"  *** Potential learning unit: {first_cell} ***")
                        
                        # Sonraki sütunları kontrol et (kazanım sayısı ve saat)
                        if len(row) > 1:
                            second_cell = str(row[1]) if row[1] else ""
                            print(f"  Second cell: {second_cell}")
                        if len(row) > 2:
                            third_cell = str(row[2]) if row[2] else ""
                            print(f"  Third cell: {third_cell}")
                        if len(row) > 3:
                            fourth_cell = str(row[3]) if row[3] else ""
                            print(f"  Fourth cell: {fourth_cell}")

if __name__ == "__main__":
    debug_kazanim_table()