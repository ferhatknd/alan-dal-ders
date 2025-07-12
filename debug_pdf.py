#!/usr/bin/env python3
import pdfplumber
import sys

def debug_pdf_tables(pdf_path):
    """
    PDF'deki tabloları debug ederek yapıyı incele
    """
    print(f"=== Debugging {pdf_path} ===")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        for page_num, page in enumerate(pdf.pages):
            print(f"\n--- Page {page_num + 1} ---")
            
            # Metin içeriğini kontrol et
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if 'KAZANIM' in line.upper() and ('SAYISI' in line.upper() or 'TABLOSU' in line.upper()):
                        print(f"Found KAZANIM reference at line {i}: {line}")
                        # Çevresindeki satırları da göster
                        for j in range(max(0, i-2), min(len(lines), i+5)):
                            print(f"  {j}: {lines[j]}")
                        print()
            
            # Tabloları kontrol et
            tables = page.extract_tables()
            print(f"Found {len(tables)} tables")
            
            for table_idx, table in enumerate(tables):
                print(f"\n  Table {table_idx + 1}:")
                print(f"    Dimensions: {len(table)} rows x {len(table[0]) if table else 0} cols")
                
                # İlk 10 satırı göster
                for row_idx, row in enumerate(table[:10]):
                    print(f"    Row {row_idx}: {row}")
                    
                    # Bu satırda KAZANIM kelimesi var mı?
                    row_text = ' '.join([str(cell) if cell else '' for cell in row]).upper()
                    if 'KAZANIM' in row_text:
                        print(f"      *** KAZANIM found in this row! ***")
                        
                        # Bu tablodan sonraki 10 satırı göster
                        print(f"      Next rows from this table:")
                        for next_idx in range(row_idx + 1, min(len(table), row_idx + 11)):
                            print(f"        Row {next_idx}: {table[next_idx]}")

if __name__ == "__main__":
    pdf_path = "ATÖLYE_DBF_10.pdf"
    debug_pdf_tables(pdf_path)