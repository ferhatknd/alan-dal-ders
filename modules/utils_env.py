"""
modules/utils_env.py
====================

Environment variable ve path yönetimi için yardımcı fonksiyonlar.

Bu modül, proje genelinde tutarlı path yönetimi sağlar ve 
.env dosyasından PROJECT_ROOT değerini okur.
"""

import os
from dotenv import load_dotenv

def get_project_root():
    """
    PROJECT_ROOT environment variable'ını .env dosyasından okur.
    
    Returns:
        str: Proje root dizini
    """
    load_dotenv()
    return os.getenv('PROJECT_ROOT', os.getcwd())

def get_data_path(*subdirs):
    """
    data/ klasörü altında path oluşturur.
    
    Args:
        *subdirs: Alt dizin isimleri
        
    Returns:
        str: Tam dosya yolu
        
    Example:
        get_data_path("cop") -> "/proje/root/data/cop"
        get_data_path("dbf", "alan1") -> "/proje/root/data/dbf/alan1"
    """
    project_root = get_project_root()
    return os.path.join(project_root, "data", *subdirs)

def get_output_json_path(filename):
    """
    JSON çıktı dosyası için path oluşturur.
    
    Args:
        filename (str): JSON dosya adı (örn: "get_cop.json")
        
    Returns:
        str: Tam dosya yolu
    """
    return get_data_path(filename)