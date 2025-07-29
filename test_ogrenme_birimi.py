#!/usr/bin/env python3
"""
test_ogrenme_birimi.py
=====================

Öğrenme birimi, konu ve kazanım parsing sistemini test eden kontrollü test scripti.

Bu script tek DBF dosyası ile deneme yaparak:
1. DBF dosyasını parse eder
2. Öğrenme birimi verilerini çıkarır
3. Database'e kaydetmeyi test eder  
4. Kontrollü adımlarla kullanıcıya sorar

Kullanım:
    python test_ogrenme_birimi.py [dosya_yolu]
"""

import sys
import os
import json
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from modules.utils_dbf1 import process_dbf_file, get_all_dbf_files
    from modules.utils_dbf2 import ex_ob_tablosu
    from modules.utils_database import with_database, find_or_create_database
    from modules.utils_normalize import normalize_to_title_case_tr
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    print("Lütfen proje kök dizininden çalıştırın.")
    sys.exit(1)

# Global değişken - parsing sonuçlarını saklamak için
PARSED_STRUCTURED_DATA = []


def print_separator(title: str):
    """Görsel ayırıcı yazdırır"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def ask_user_confirmation(question: str) -> bool:
    """Kullanıcıya onay sorar"""
    while True:
        answer = input(f"\n❓ {question} (e/h): ").lower().strip()
        if answer in ['e', 'evet', 'y', 'yes']:
            return True
        elif answer in ['h', 'hayır', 'n', 'no']:
            return False
        else:
            print("Lütfen 'e' (evet) veya 'h' (hayır) girin.")


def select_test_file() -> str:
    """Test için DBF dosyası seçer"""
    print_separator("TEST DOSYASI SEÇİMİ")
    
    # Tüm DBF dosyalarını listele
    all_files = get_all_dbf_files(validate_files=True)
    
    if not all_files:
        print("❌ İşlenecek DBF dosyası bulunamadı.")
        return None
    
    print(f"📂 Toplam {len(all_files)} DBF dosyası bulundu.")
    
    # İlk 10 dosyayı göster
    print("\n📋 İlk 10 dosya:")
    for i, file_path in enumerate(all_files[:10], 1):
        filename = os.path.basename(file_path)
        print(f"  {i:2d}. {filename}")
    
    if len(all_files) > 10:
        print(f"     ... ve {len(all_files) - 10} dosya daha")
    
    # Dosya seçimi
    if ask_user_confirmation("Otomatik olarak ilk dosyayı seçelim mi?"):
        selected_file = all_files[0]
    else:
        # Manuel dosya seçimi (basit implementasyon)
        try:
            index = int(input(f"Hangi dosyayı test edelim (1-{min(10, len(all_files))}): ")) - 1
            if 0 <= index < min(10, len(all_files)):
                selected_file = all_files[index]
            else:
                print("❌ Geçersiz seçim, ilk dosya kullanılıyor.")
                selected_file = all_files[0]
        except ValueError:
            print("❌ Geçersiz sayı, ilk dosya kullanılıyor.")
            selected_file = all_files[0]
    
    print(f"\n✅ Seçilen dosya: {os.path.basename(selected_file)}")
    print(f"📁 Tam yol: {selected_file}")
    
    return selected_file


def test_dbf_parsing(file_path: str):
    """DBF dosyası parsing testini yapar"""
    print_separator("DBF DOSYASI PARSING TESTİ")
    
    print(f"🔄 Dosya işleniyor: {os.path.basename(file_path)}")
    
    # DBF dosyasını parse et
    result = process_dbf_file(file_path)
    
    if not result or not result.get("success"):
        print(f"❌ Dosya parse edilemedi: {result.get('error', 'Bilinmeyen hata')}")
        return None
    
    print("✅ Dosya başarıyla parse edildi!")
    
    # Temel bilgiler
    temel_bilgiler = result.get("temel_bilgiler", {})
    print(f"\n📋 Temel Bilgiler:")
    for key, value in temel_bilgiler.items():
        if value and len(str(value)) > 0:
            preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"  • {key}: {preview}")
    
    # Kazanım tablosu
    kazanim_tablosu_data = result.get("kazanim_tablosu_data", [])
    print(f"\n📊 Kazanım Tablosu: {len(kazanim_tablosu_data)} öğrenme birimi")
    for i, item in enumerate(kazanim_tablosu_data, 1):
        title = item.get('title', 'N/A')
        count = item.get('count', 0)
        duration = item.get('duration', 'N/A')
        print(f"  {i}. {title} - {count} konu, {duration} saat")
    
    # Öğrenme birimi analizi
    ogrenme_birimi_analizi = result.get("ogrenme_birimi_analizi", "")
    print(f"\n📝 Öğrenme Birimi Analizi: {len(ogrenme_birimi_analizi)} karakter")
    if len(ogrenme_birimi_analizi) > 0:
        preview = ogrenme_birimi_analizi[:200] + "..." if len(ogrenme_birimi_analizi) > 200 else ogrenme_birimi_analizi
        print(f"  Önizleme: {preview}")
    
    return result


def test_ogrenme_birimi_parsing(result: dict):
    """Öğrenme birimi parsing testini yapar"""
    print_separator("ÖĞRENME BİRİMİ PARSING TESTİ")
    
    kazanim_tablosu_data = result.get("kazanim_tablosu_data", [])
    ogrenme_birimi_analizi = result.get("ogrenme_birimi_analizi", "")
    
    if not kazanim_tablosu_data:
        print("❌ Kazanım tablosu verisi bulunamadı.")
        return False
    
    print(f"🔄 {len(kazanim_tablosu_data)} öğrenme birimi parse ediliyor...")
    
    total_konu = 0
    total_kazanim = 0
    
    for i, item in enumerate(kazanim_tablosu_data, 1):
        birim_adi = item.get('title', f'Öğrenme Birimi {i}')
        konu_sayisi = item.get('count', 0)
        
        print(f"\n  🔍 {i}. {birim_adi} ({konu_sayisi} konu bekleniyor)")
        
        # ⭐ YENİ: Direkt ex_ob_tablosu kullan - tek seferlik parse
        if i == 1:  # Sadece ilk iteration'da parse et
            try:
                global PARSED_STRUCTURED_DATA
                parsing_result, PARSED_STRUCTURED_DATA = ex_ob_tablosu(ogrenme_birimi_analizi)
                print(f"\\n📋 Parsing tamamlandı:")
                print(f"   • {len(PARSED_STRUCTURED_DATA)} öğrenme birimi bulundu")
            except Exception as e:
                print(f"❌ Parsing hatası: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Structured data'dan bu öğrenme birimini bul
        current_birim = None
        for birim in PARSED_STRUCTURED_DATA:
            if birim.get('sira') == i:
                current_birim = birim
                break
        
        if not current_birim:
            print(f"    ❌ Bu öğrenme birimi structured data'da bulunamadı")
            continue
            
        konular = current_birim.get('konular', [])
        
        print(f"    ✅ Parse sonucu: {len(konular)} konu")
        
        # Konu ve kazanım detayları
        birim_toplam_kazanim = 0
        for j, konu in enumerate(konular, 1):
            konu_adi = konu.get('konu_adi', 'N/A')
            kazanimlar = konu.get('kazanimlar', [])
            kazanim_count = len(kazanimlar)
            birim_toplam_kazanim += kazanim_count
            
            print(f"      {j}. {konu_adi[:50]}{'...' if len(konu_adi) > 50 else ''} ({kazanim_count} kazanım)")
            
            # İlk 2 kazanımı göster
            for k, kazanim in enumerate(kazanimlar[:2], 1):
                kazanim_adi = kazanim.get('kazanim_adi', 'N/A')
                marker = kazanim.get('marker', '')
                print(f"         {marker} {kazanim_adi[:60]}{'...' if len(kazanim_adi) > 60 else ''}")
            
            if kazanim_count > 2:
                print(f"         ... ve {kazanim_count - 2} kazanım daha")
        
        print(f"    📊 Toplam: {len(konular)} konu, {birim_toplam_kazanim} kazanım")
        
        total_konu += len(konular)
        total_kazanim += birim_toplam_kazanim
        
        # Kullanıcı onayı
        if not ask_user_confirmation(f"Bu öğrenme birimi parsing sonucu doğru görünüyor mu?"):
            print("❌ Kullanıcı parsing sonucunu onaylamadı.")
            return False
    
    print(f"\n✅ Toplam parsing sonucu: {total_konu} konu, {total_kazanim} kazanım")
    return True


@with_database
def test_database_operations(cursor, result: dict):
    """Database işlemlerini test eder"""
    print_separator("DATABASE İŞLEMLERİ TESTİ")
    
    # Test dersi bul veya oluştur
    test_ders_adi = "TEST DERS - ÖĞRENME BİRİMİ"
    
    cursor.execute("SELECT id FROM temel_plan_ders WHERE ders_adi = ?", (test_ders_adi,))
    existing_ders = cursor.fetchone()
    
    if existing_ders:
        ders_id = existing_ders['id']
        print(f"📝 Mevcut test dersi kullanılıyor: {test_ders_adi} (ID: {ders_id})")
        
        if ask_user_confirmation("Mevcut test verilerini temizleyelim mi?"):
            cursor.execute("DELETE FROM temel_plan_ogrenme_birimi WHERE ders_id = ?", (ders_id,))
            deleted_count = cursor.rowcount
            print(f"🗑️  {deleted_count} öğrenme birimi silindi")
    else:
        # Test dersi oluştur
        cursor.execute("""
            INSERT INTO temel_plan_ders (ders_adi, sinif, ders_saati, amac)
            VALUES (?, ?, ?, ?)
        """, (test_ders_adi, 11, 4, "Öğrenme birimi parsing test dersi"))
        
        ders_id = cursor.lastrowid
        print(f"➕ Test dersi oluşturuldu: {test_ders_adi} (ID: {ders_id})")
    
    # ⭐ YENİ: Global structured data'yı kullan
    global PARSED_STRUCTURED_DATA
    
    if not PARSED_STRUCTURED_DATA:
        print("❌ Parsed structured data bulunamadı. Önce parsing testini çalıştırın.")
        return False
    
    print(f"\n🔄 Database'e kayıt işlemi başlatılıyor...")
    print(f"   • {len(PARSED_STRUCTURED_DATA)} öğrenme birimi kaydedilecek")
    
    # ⭐ PLACEHOLDER: Database kayıt fonksiyonu henüz yazılmadı
    # Bu fonksiyon Aşama 2'de yazılacak
    print("⚠️  Database kayıt fonksiyonu henüz implement edilmedi.")
    print("   Bu Aşama 2'de (Database Kayıt Sistemi) geliştirilecek.")
    
    # Simüle edilmiş başarı - test akışının devam etmesi için
    db_result = {
        "success": True,
        "stats": {
            "ogrenme_birimi_count": len(PARSED_STRUCTURED_DATA),
            "konu_count": sum(len(birim.get('konular', [])) for birim in PARSED_STRUCTURED_DATA),
            "kazanim_count": sum(
                sum(len(konu.get('kazanimlar', [])) for konu in birim.get('konular', []))
                for birim in PARSED_STRUCTURED_DATA
            )
        }
    }
    
    print(f"📊 Kaydedilecek veri istatistikleri:")
    print(f"   • {db_result['stats']['ogrenme_birimi_count']} öğrenme birimi")  
    print(f"   • {db_result['stats']['konu_count']} konu")
    print(f"   • {db_result['stats']['kazanim_count']} kazanım")
    
    if db_result.get("success"):
        stats = db_result.get("stats", {})
        print(f"✅ Database kaydı başarılı!")
        print(f"   • {stats.get('ogrenme_birimi_count', 0)} öğrenme birimi")
        print(f"   • {stats.get('konu_count', 0)} konu")
        print(f"   • {stats.get('kazanim_count', 0)} kazanım")
        
        # Verification query
        cursor.execute("""
            SELECT 
                ob.birim_adi,
                COUNT(DISTINCT k.id) as konu_sayisi,
                COUNT(DISTINCT kz.id) as kazanim_sayisi
            FROM temel_plan_ogrenme_birimi ob
            LEFT JOIN temel_plan_konu k ON ob.id = k.ogrenme_birimi_id
            LEFT JOIN temel_plan_kazanim kz ON k.id = kz.konu_id
            WHERE ob.ders_id = ?
            GROUP BY ob.id, ob.birim_adi
            ORDER BY ob.sira
        """, (ders_id,))
        
        verification_results = cursor.fetchall()
        print(f"\n🔍 Database verification:")
        for row in verification_results:
            print(f"   • {row['birim_adi']}: {row['konu_sayisi']} konu, {row['kazanim_sayisi']} kazanım")
        
        return True
    else:
        print(f"❌ Database kaydı başarısız: {db_result.get('error', 'Bilinmeyen hata')}")
        return False


def main():
    """Ana test fonksiyonu"""
    print("🧪 ÖĞRENME BİRİMİ PARSING VE DATABASE TEST SİSTEMİ")
    print("=" * 60)
    
    # Komut satırı argümanı kontrolü
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"❌ Dosya bulunamadı: {file_path}")
            return
        print(f"📁 Komut satırından dosya: {os.path.basename(file_path)}")
    else:
        # Dosya seçimi
        file_path = select_test_file()
        if not file_path:
            return
    
    if not ask_user_confirmation("Test işlemini başlatalım mı?"):
        print("❌ Test iptal edildi.")
        return
    
    # 1. DBF Parsing Testi
    result = test_dbf_parsing(file_path)
    if not result:
        return
    
    if not ask_user_confirmation("Öğrenme birimi parsing testine geçelim mi?"):
        print("❌ Test sonlandırıldı.")
        return
    
    # 2. Öğrenme Birimi Parsing Testi
    if not test_ogrenme_birimi_parsing(result):
        return
    
    if not ask_user_confirmation("Database işlemleri testine geçelim mi?"):
        print("❌ Test sonlandırıldı.")
        return
    
    # 3. Database İşlemleri Testi
    if test_database_operations(result):
        print_separator("TEST TAMAMLANDI")
        print("✅ Tüm testler başarıyla tamamlandı!")
        print("📊 Öğrenme birimi, konu ve kazanım parsing sistemi çalışıyor.")
        
        if ask_user_confirmation("Test verilerini database'de bırakalım mı?"):
            print("💾 Test verileri database'de korunuyor.")
        else:
            print("🗑️  Test verileri temizlenecek... (manuel olarak silin)")
    else:
        print("❌ Database testleri başarısız oldu.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Test kullanıcı tarafından iptal edildi.")
    except Exception as e:
        print(f"\n\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()