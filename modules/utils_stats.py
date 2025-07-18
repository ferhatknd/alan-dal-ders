"""
modules/utils_stats.py - İstatistik ve Monitoring Modülü

Bu modül, veritabanı istatistikleri ve sistem monitoring fonksiyonlarını içerir.
utils_database.py'den ayrıştırılmıştır.

İçerdiği fonksiyonlar:
- get_database_statistics: Kapsamlı veritabanı istatistikleri
- format_database_statistics_message: İstatistikleri konsol formatına çevirir
"""

import os
import sqlite3
from typing import Dict, Any

# Database connection'ı utils_database.py'den import et
try:
    from .utils_database import with_database
except ImportError:
    from utils_database import with_database


@with_database
def get_database_statistics(cursor) -> Dict[str, Any]:
    """
    Merkezi veritabanı istatistikleri çekme fonksiyonu.
    CLAUDE.md kurallarına uygun olarak @with_database decorator kullanır.
    
    Returns:
        dict: Kapsamlı veritabanı istatistikleri
        {
            "alan_count": int,
            "cop_url_count": int,
            "dbf_url_count": int,
            "ders_count": int,
            "dal_count": int,
            "ders_dal_relations": int,
            "ogrenme_birimi_count": int,
            "konu_count": int,
            "kazanim_count": int
        }
    """
    stats = {}
    
    try:
        # Alan sayıları
        cursor.execute('SELECT COUNT(*) FROM temel_plan_alan')
        stats['alan_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM temel_plan_alan WHERE cop_url IS NOT NULL')
        stats['cop_url_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM temel_plan_alan WHERE dbf_urls IS NOT NULL')
        stats['dbf_url_count'] = cursor.fetchone()[0]
        
        # Ders sayıları
        cursor.execute('SELECT COUNT(*) FROM temel_plan_ders')
        stats['ders_count'] = cursor.fetchone()[0]
        
        # Dal sayıları  
        cursor.execute('SELECT COUNT(*) FROM temel_plan_dal')
        stats['dal_count'] = cursor.fetchone()[0]
        
        # Ders-Dal ilişkileri
        cursor.execute('SELECT COUNT(*) FROM temel_plan_ders_dal')
        stats['ders_dal_relations'] = cursor.fetchone()[0]
        
        # Öğrenme birimi sayıları (varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM temel_plan_ogrenme_birimi')
            stats['ogrenme_birimi_count'] = cursor.fetchone()[0]
        except:
            stats['ogrenme_birimi_count'] = 0
        
        # Konu sayıları (varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM temel_plan_konu')
            stats['konu_count'] = cursor.fetchone()[0]
        except:
            stats['konu_count'] = 0
        
        # Kazanım sayıları (varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM temel_plan_kazanim')
            stats['kazanim_count'] = cursor.fetchone()[0]
        except:
            stats['kazanim_count'] = 0
            
        return stats
        
    except Exception as e:
        print(f"❌ İstatistik çekme hatası: {e}")
        return {
            "alan_count": 0,
            "cop_url_count": 0, 
            "dbf_url_count": 0,
            "ders_count": 0,
            "dal_count": 0,
            "ders_dal_relations": 0,
            "ogrenme_birimi_count": 0,
            "konu_count": 0,
            "kazanim_count": 0,
            "error": str(e)
        }


def format_database_statistics_message(stats: Dict[str, Any]) -> str:
    """
    İstatistikleri konsol mesajı formatına çevirir.
    
    Args:
        stats: get_database_statistics() dönüş değeri
        
    Returns:
        str: Formatlanmış mesaj
    """
    if not stats or 'error' in stats:
        return "📊 İstatistik alınamadı"
    
    return f"📊 Veritabanı Durumu: {stats['alan_count']} toplam alan | {stats['cop_url_count']} COP URL | {stats['dbf_url_count']} DBF URL | {stats['ders_count']} ders | {stats['dal_count']} dal"


def get_file_statistics(data_root: str = "data") -> Dict[str, int]:
    """
    Dosya sistemindeki dosya sayılarını hesaplar.
    
    Args:
        data_root: Data klasörünün yolu (varsayılan: "data")
        
    Returns:
        Dict: Dosya türü sayıları
        {
            "cop_pdf": int,
            "dbf_rar": int,
            "dbf_pdf": int,
            "dbf_docx": int,
            "dbf_total": int,  # Toplam DBF dosya sayısı
            "dm_pdf": int,
            "bom_pdf": int,
            "bom_total": int  # Toplam BOM dosya sayısı
        }
    """
    stats = {
        "cop_pdf": 0,
        "dbf_rar": 0,
        "dbf_pdf": 0,
        "dbf_docx": 0,
        "dbf_total": 0,  # Toplam DBF dosya sayısı
        "dm_pdf": 0,
        "bom_pdf": 0,
        "bom_total": 0  # Toplam BOM dosya sayısı
    }
    
    if not os.path.exists(data_root):
        return stats
    
    try:
        # COP PDF'leri say
        cop_dir = os.path.join(data_root, "cop")
        if os.path.exists(cop_dir):
            for root, dirs, files in os.walk(cop_dir):
                stats["cop_pdf"] += len([f for f in files if f.lower().endswith('.pdf')])
        
        # DBF dosyalarını say
        dbf_dir = os.path.join(data_root, "dbf")
        if os.path.exists(dbf_dir):
            for root, dirs, files in os.walk(dbf_dir):
                for file in files:
                    if file.lower().endswith('.rar'):
                        stats["dbf_rar"] += 1
                        stats["dbf_total"] += 1
                    elif file.lower().endswith('.pdf'):
                        stats["dbf_pdf"] += 1
                        stats["dbf_total"] += 1
                    elif file.lower().endswith('.docx'):
                        stats["dbf_docx"] += 1
                        stats["dbf_total"] += 1
        
        # DM PDF'leri say
        dm_dir = os.path.join(data_root, "dm")
        if os.path.exists(dm_dir):
            for root, dirs, files in os.walk(dm_dir):
                stats["dm_pdf"] += len([f for f in files if f.lower().endswith('.pdf')])
        
        # BOM dosyalarını say
        bom_dir = os.path.join(data_root, "bom")
        if os.path.exists(bom_dir):
            for root, dirs, files in os.walk(bom_dir):
                pdf_count = len([f for f in files if f.lower().endswith('.pdf')])
                stats["bom_pdf"] += pdf_count
                stats["bom_total"] += pdf_count  # BOM'da sadece PDF dosyaları var
                
    except Exception as e:
        print(f"❌ Dosya istatistik hesaplama hatası: {e}")
    
    return stats


def get_combined_statistics() -> Dict[str, Any]:
    """
    Hem veritabanı hem de dosya sisteminden birleşik istatistikleri döner.
    
    Returns:
        Dict: Birleşik istatistikler
    """
    try:
        # Veritabanı istatistikleri
        db_stats = get_database_statistics()
        
        # Dosya istatistikleri
        file_stats = get_file_statistics()
        
        # Birleştir
        combined = {**db_stats, **file_stats}
        
        # Özet mesaj oluştur
        combined["summary_message"] = format_database_statistics_message(db_stats)
        
        return combined
        
    except Exception as e:
        print(f"❌ Birleşik istatistik hesaplama hatası: {e}")
        return {
            "error": str(e),
            "summary_message": "❌ İstatistikler hesaplanamadı"
        }