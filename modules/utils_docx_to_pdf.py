#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
utils_docx_to_pdf.py - DOC/DOCX to PDF Conversion Module

CLAUDE.md Prensiplerine Uygun:
- Modüler Import Sistemi (utils_env, utils_file_management)  
- Environment Aware Paths (PROJECT_ROOT bazlı)
- PyMuPDF Unified Processing (DOC/DOCX için tek API)
- File-based Caching System (same directory caching)
- Error Handling & Fallback Mechanisms

Son Güncelleme: 2025-07-28
"""

import os
import fitz  # PyMuPDF - zaten mevcut dependency
from pathlib import Path
import logging
from typing import Optional, Tuple

# CLAUDE.md Prensibi: Modüler Import Sistemi
from modules.utils_env import get_project_root
from modules.utils_normalize import sanitize_filename_tr

# Logger setup
logger = logging.getLogger(__name__)

class DocxToPdfConverter:
    """
    DOC/DOCX dosyalarını PDF'e çeviren sınıf
    
    CLAUDE.md Prensibi: Same directory caching + Smart extension handling
    """
    
    SUPPORTED_EXTENSIONS = ['.doc', '.docx', '.DOC', '.DOCX']
    
    def __init__(self):
        self.project_root = get_project_root()
        logger.info(f"📁 DocxToPdfConverter initialized with PROJECT_ROOT: {self.project_root}")
    
    def get_cached_pdf_path(self, original_path: str) -> str:
        """
        Aynı dizinde cache edilmiş PDF path'ini döndürür
        
        Args:
            original_path: /path/to/document.docx
            
        Returns:
            /path/to/document_converted.pdf
        """
        original_file = Path(original_path)
        
        # Same directory + _converted suffix
        pdf_name = f"{original_file.stem}_converted.pdf"
        cached_pdf_path = original_file.parent / pdf_name
        
        return str(cached_pdf_path)
    
    def is_pdf_cache_valid(self, original_path: str, cached_pdf_path: str) -> bool:
        """
        Cache edilmiş PDF'in geçerli olup olmadığını kontrol eder
        
        CLAUDE.md Prensibi: File validation
        """
        try:
            if not os.path.exists(cached_pdf_path):
                return False
                
            if not os.path.exists(original_path):
                return False
            
            # Modification time karşılaştırması
            original_mtime = os.path.getmtime(original_path)
            cached_mtime = os.path.getmtime(cached_pdf_path)
            
            # Cache daha yeni ise geçerli
            is_valid = cached_mtime >= original_mtime
            
            if is_valid:
                logger.info(f"✅ Valid PDF cache found: {cached_pdf_path}")
            else:
                logger.info(f"⚠️ PDF cache outdated: {cached_pdf_path}")
                
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Cache validation error: {e}")
            return False
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        Dosya formatının desteklenip desteklenmediğini kontrol eder
        
        CLAUDE.md Prensibi: File type detection with case-insensitive
        """
        file_ext = Path(file_path).suffix
        return file_ext in self.SUPPORTED_EXTENSIONS
    
    def convert_to_pdf(self, doc_path: str) -> Tuple[bool, str, str]:
        """
        DOC/DOCX dosyasını PDF'e çevirir
        
        CLAUDE.md Prensibi: PyMuPDF unified processing
        
        Args:
            doc_path: DOC/DOCX dosya yolu
            
        Returns:
            (success: bool, pdf_path: str, error_message: str)
        """
        try:
            if not self.is_supported_format(doc_path):
                return False, "", f"Desteklenmeyen format: {Path(doc_path).suffix}"
            
            if not os.path.exists(doc_path):
                return False, "", f"Dosya bulunamadı: {doc_path}"
            
            # Cache kontrolü
            cached_pdf_path = self.get_cached_pdf_path(doc_path)
            if self.is_pdf_cache_valid(doc_path, cached_pdf_path):
                logger.info(f"🔄 Using cached PDF: {cached_pdf_path}")
                return True, cached_pdf_path, ""
            
            logger.info(f"🔄 Converting {doc_path} to PDF...")
            
            # PyMuPDF ile DOC/DOCX açma
            doc = fitz.open(doc_path)
            
            if len(doc) == 0:
                doc.close()
                return False, "", "Belge boş veya okunamıyor"
            
            # PDF'e dönüştürme
            pdf_doc = fitz.open()  # Yeni PDF oluştur
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Page'i PDF page'e çevir
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x resolution
                img_pdf = fitz.open("pdf", pix.tobytes("pdf"))
                pdf_doc.insert_pdf(img_pdf)
                img_pdf.close()
            
            doc.close()
            
            # PDF'i kaydet
            pdf_doc.save(cached_pdf_path)
            pdf_doc.close()
            
            logger.info(f"✅ Conversion successful: {cached_pdf_path}")
            return True, cached_pdf_path, ""
            
        except Exception as e:
            error_msg = f"Conversion error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, "", error_msg
    
    def get_or_convert_pdf(self, doc_path: str) -> Tuple[bool, str, str]:
        """
        PDF varsa döndürür, yoksa convert eder
        
        Main entry point - Frontend bu fonksiyonu kullanacak
        
        Args:
            doc_path: DOC/DOCX dosya yolu
            
        Returns:
            (success: bool, pdf_path: str, error_message: str)
        """
        logger.info(f"📄 Processing document: {doc_path}")
        
        # Önce cache kontrolü
        cached_pdf_path = self.get_cached_pdf_path(doc_path)
        if self.is_pdf_cache_valid(doc_path, cached_pdf_path):
            return True, cached_pdf_path, ""
        
        # Cache yoksa convert et
        return self.convert_to_pdf(doc_path)

# Global instance - CLAUDE.md Prensibi: Singleton pattern
_converter_instance = None

def get_converter() -> DocxToPdfConverter:
    """
    Converter instance'ını döndürür (Singleton pattern)
    """
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = DocxToPdfConverter()
    return _converter_instance

# Public API Functions - CLAUDE.md Prensibi: Clean API
def convert_docx_to_pdf(doc_path: str) -> Tuple[bool, str, str]:
    """
    DOC/DOCX dosyasını PDF'e çevirir (cache-aware)
    
    Usage:
        success, pdf_path, error = convert_docx_to_pdf("/path/to/document.docx")
        if success:
            print(f"PDF ready: {pdf_path}")
        else:
            print(f"Error: {error}")
    """
    converter = get_converter()
    return converter.get_or_convert_pdf(doc_path)

def is_conversion_supported(file_path: str) -> bool:
    """
    Dosya conversion'ını destekliyor mu kontrol et
    """
    converter = get_converter()
    return converter.is_supported_format(file_path)

def get_pdf_cache_path(doc_path: str) -> str:
    """
    Belirtilen DOC/DOCX için cache edilmiş PDF path'ini döndürür
    """
    converter = get_converter()
    return converter.get_cached_pdf_path(doc_path)

# Test/Debug Functions
if __name__ == "__main__":
    # Test conversion
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"🧪 Testing conversion: {test_file}")
        
        success, pdf_path, error = convert_docx_to_pdf(test_file)
        
        if success:
            print(f"✅ Success: {pdf_path}")
        else:
            print(f"❌ Failed: {error}")
    else:
        print("Usage: python utils_docx_to_pdf.py /path/to/document.docx")