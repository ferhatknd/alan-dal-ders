import camelot
import pandas as pd
import re

def extract_dersin_amaci(pdf_path):
    """
    Extract 'DERSİN AMACI' section from PDF using camelot-py
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted 'DERSİN AMACI' content or None if not found
    """
    try:
        # Read all tables from PDF
        tables = camelot.read_pdf(pdf_path, flavor='lattice', pages='all')
        
        dersin_amaci_content = []
        
        # Search through all tables
        for table in tables:
            df = table.df
            
            # Search for 'DERSİN AMACI' in all cells
            for i, row in df.iterrows():
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and 'DERSİN AMACI' in cell.upper():
                        # Found the cell containing 'DERSİN AMACI'
                        # Try to extract content from same row or next cells
                        content = ""
                        
                        # Check if content is in the same cell after 'DERSİN AMACI'
                        if ':' in cell:
                            content = cell.split(':', 1)[1].strip()
                        
                        # If not found in same cell, check adjacent cells
                        if not content and j + 1 < len(row):
                            content = str(row.iloc[j + 1]).strip()
                        
                        # If still not found, check next row
                        if not content and i + 1 < len(df):
                            next_row = df.iloc[i + 1]
                            for next_cell in next_row:
                                if str(next_cell).strip() and str(next_cell).strip() != 'nan':
                                    content = str(next_cell).strip()
                                    break
                        
                        if content and content != 'nan':
                            dersin_amaci_content.append(content)
        
        # If no tables found, try text extraction
        if not dersin_amaci_content:
            tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
            
            for table in tables:
                df = table.df
                
                # Convert entire dataframe to text and search
                text = df.to_string()
                
                # Use regex to find DERSİN AMACI content
                pattern = r'DERSİN\s+AMACI[:\s]*([^\n]+(?:\n[^\n]*)*?)(?=\n\s*[A-ZÜÇĞÖŞ]+|$)'
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                if match:
                    content = match.group(1).strip()
                    if content:
                        dersin_amaci_content.append(content)
        
        # Return the first non-empty result
        for content in dersin_amaci_content:
            if content and len(content.strip()) > 0:
                return content.strip()
        
        return None
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None

def main():
    # Example usage
    pdf_path = "muzik.pdf"  # Replace with your PDF file path
    
    result = extract_dersin_amaci(pdf_path)
    
    if result:
        print("DERSİN AMACI found:")
        print("-" * 50)
        print(result)
    else:
        print("DERSİN AMACI not found in the PDF")

if __name__ == "__main__":
    main()