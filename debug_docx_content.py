#!/usr/bin/env python3
import docx

def debug_specific_cells():
    doc = docx.Document("SOSYAL MEDYA HESAP İŞLEMLERİ DBF.docx")
    
    print("=== Debugging specific cells ===")
    
    for table_idx, table in enumerate(doc.tables):
        print(f"\nTable {table_idx + 1}:")
        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                if cell_text and ('KAZANIM' in cell_text.upper() or 'ÖLÇME' in cell_text.upper() or 'ORTAM' in cell_text.upper()):
                    print(f"  Row {row_idx}, Cell {cell_idx}:")
                    print(f"    Content: {cell_text[:200]}{'...' if len(cell_text) > 200 else ''}")
                    print(f"    Upper: {'DERSİN KAZANIMLARI' in cell_text.upper()}")
                    print(f"    Ortam: {'EĞİTİM-ÖĞRETİM ORTAM' in cell_text.upper()}")
                    print(f"    Ölçme: {'ÖLÇME VE DEĞERLENDİRME' in cell_text.upper()}")
                    print()

if __name__ == "__main__":
    debug_specific_cells()