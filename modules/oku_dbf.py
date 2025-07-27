"""
modules/oku_dbf.py
==================

DBF işleme ve veritabanı entegrasyon modülü.

Bu modül, `data/dbf` klasöründeki PDF/DOCX dosyalarını işler,
ders adlarını çıkarır ve bu bilgiyi `temel_plan_ders` tablosundaki
ilgili ders kaydının `dbf_url` sütununu günceller.

İşlevsellik:
- DBF dosyalarından ders adlarını çıkarmak.
- Çıkarılan ders adlarını veritabanındaki derslerle eşleştirmek.
- Eşleşen derslerin `dbf_url` alanını dosya yolu ile güncellemek.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from .utils_database import with_database
    from .utils_oku_dbf import get_all_dbf_files, process_dbf_file
    from .utils_normalize import normalize_to_title_case_tr
except ImportError:
    # Test ortamları veya bağımsız çalıştırma için
    from modules.utils_database import with_database
    from modules.utils_oku_dbf import get_all_dbf_files, process_dbf_file
    from modules.utils_normalize import normalize_to_title_case_tr
    

@with_database
def link_dbf_files_to_database(cursor):
    """
    Tüm DBF dosyalarını tarayarak ders adları ile eşleştirir ve temel_plan_ders tablosundaki
    dbf_url alanını günceller. Bu temel fonksiyon, ileride amaç, kazanım, ders saati gibi
    ek bilgileri eklemek için genişletilebilir.

    Args:
        cursor: Veritabanı cursor nesnesi.

    Yields:
        Dict: SSE (Server-Sent Events) için işlem durumu mesajları.
    """
    yield {"type":"info","message":f"Kullanılan DB dosyası: {cursor.connection}"}
    try:
        # 1. Veritabanından mevcut dersleri yükle ve bir harita oluştur
        yield {"type": "status", "message": "Veritabanındaki dersler önbelleğe alınıyor..."}
        cursor.execute("SELECT id, ders_adi FROM temel_plan_ders")
        all_dersler = cursor.fetchall()
        
        # Normalize edilmiş ders adlarını anahtar, ID'leri değer olarak tutan harita
        ders_map = {normalize_to_title_case_tr(row['ders_adi']): row['id'] for row in all_dersler}
        yield {"type": "info", "message": f"{len(ders_map)} ders veritabanından yüklendi."}

        # 2. Tüm DBF dosyalarını bul
        yield {"type": "status", "message": "DBF dosyaları taranıyor..."}
        dbf_files = get_all_dbf_files(validate_files=True)
        if not dbf_files:
            yield {"type": "warning", "message": "İşlenecek DBF dosyası bulunamadı."}
            yield {"type": "done", "message": "İşlem tamamlandı, ancak işlenecek dosya yoktu."}
            return

        yield {"type": "info", "message": f"{len(dbf_files)} adet DBF dosyası bulundu."}

        # 3. Dosyaları işle, eşleştir ve güncellenecekleri topla
        updates_to_execute = []
        processed_count = 0
        matched_count = 0

        for file_path in dbf_files:
            processed_count += 1
            filename = os.path.basename(file_path)
            yield {"type": "progress", "message": f"[{processed_count}/{len(dbf_files)}] İşleniyor: {filename}"}

            # Dosyadan ders adını çıkar
            result = process_dbf_file(file_path)
            if not result or not result.get("success"):
                yield {"type": "warning", "message": f"Okunamadı: {filename} - {result.get('error', 'Bilinmeyen hata')}"}
                continue

            temel_bilgiler = result.get("temel_bilgiler", {})
            ders_adi_extracted = None
            for key, value in temel_bilgiler.items():
                if "ADI" in key.upper() and value.strip():
                    ders_adi_extracted = value.strip()
                    break
            
            if not ders_adi_extracted:
                yield {"type": "warning", "message": f"Ders adı bulunamadı: {filename}"}
                continue

            # Eşleştirme yap
            normalized_ders_adi = normalize_to_title_case_tr(ders_adi_extracted)
            
            # Haritadan ders ID'sini bul
            ders_id = ders_map.get(normalized_ders_adi)

            if ders_id:
                matched_count += 1
                updates_to_execute.append((file_path, ders_id))
                yield {"type": "success", "message": f"Eşleşti: '{ders_adi_extracted}' -> DB ID: {ders_id}"}
            else:
                yield {"type": "info", "message": f"Eşleşmedi: '{ders_adi_extracted}' veritabanında bulunamadı."}

        # 4. Toplu veritabanı güncellemesi
        if updates_to_execute:
            yield {"type": "status", "message": f"Toplam {len(updates_to_execute)} eşleşme bulundu. Veritabanı güncelleniyor..."}
            try:
                cursor.executemany(
                    "UPDATE temel_plan_ders SET dbf_url = ? WHERE id = ?",
                    updates_to_execute
                )
                cursor.connection.commit() # Explicit commit here
                print(f"✅ DBF yolları veritabanına başarıyla kaydedildi: {cursor.rowcount} kayıt güncellendi.") # Terminal log
                yield {"type": "success", "message": f"{cursor.rowcount} dersin DBF yolu başarıyla güncellendi."}
            except Exception as db_error:
                yield {"type": "error", "message": f"Veritabanı güncelleme hatası: {db_error}"}
        else:
            yield {"type": "info", "message": "Veritabanında güncellenecek eşleşme bulunamadı."}

        yield {"type": "done", "message": f"İşlem tamamlandı. {processed_count} dosya işlendi, {matched_count} eşleşme bulundu."}

    except Exception as e:
        yield {"type": "error", "message": f"DBF işleme sırasında beklenmedik bir hata oluştu: {str(e)}"}
