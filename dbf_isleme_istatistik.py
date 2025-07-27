#!/usr/bin/env python3
"""
DBF Dosya İşleme İstatistik Script'i
====================================

Bu script data/dbf dizinindeki tüm PDF ve DOCX dosyalarını işler ve aşağıdaki istatistikleri sunar:
- Toplam işlenen dosya sayısı
- Başlık çıkarılan dosya sayısı
- Başlıklarda eşleşme olmayan dosya sayısı ve adresleri
- Detaylı eşleşme istatistikleri

Kullanım:
    python dbf_isleme_istatistik.py

Bu script extract_olcme.py'deki fonksiyonları kullanır.
"""

import fitz  # PyMuPDF
import re
import os
import sys
import time
from datetime import datetime

# extract_olcme.py'den fonksiyonları import et
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from extract_olcme import ex_kazanim_tablosu, extract_ob_tablosu, komutlar, normalize_turkish_text, ex_temel_bilgiler

class DBFProcessingStats:
    """DBF dosya işleme istatistiklerini takip eden sınıf"""
    
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.files_with_headers = 0
        self.files_with_matching_headers = 0
        self.files_with_perfect_matches = 0
        self.files_without_matches = []
        self.processing_errors = []
        self.header_extraction_details = []
        self.perfect_match_courses = []
        self.start_time = None
        self.end_time = None
        
    def start_processing(self):
        """İşleme başlangıcını kaydet"""
        self.start_time = time.time()
        print(f"📊 DBF Dosya İşleme İstatistik Analizi")
        print(f"⏰ Başlangıç Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    def process_file(self, file_path):
        """Tek dosyayı işle ve istatistikleri güncelle"""
        self.processed_files += 1
        file_stats = {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'has_headers': False,
            'has_matches': False,
            'is_perfect_match': False,
            'course_name': None,
            'header_count': 0,
            'match_count': 0,
            'no_match_headers': [],
            'error': None
        }
        
        try:
            print(f"\n📄 [{self.processed_files}/{self.total_files}] {file_stats['filename']}")
            print("-" * 60)
            
            # Dosyayı oku
            doc = fitz.open(file_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()
            
            # Metni normalize et
            full_text = re.sub(r'\s+', ' ', full_text)
            
            if not full_text.strip():
                file_stats['error'] = "Dosya içeriği boş"
                self.processing_errors.append(file_stats)
                print("❌ HATA: Dosya içeriği boş")
                return file_stats
            
            # Ders adını çıkar
            temel_bilgiler = ex_temel_bilgiler(full_text)
            for key, value in temel_bilgiler.items():
                if "ADI" in key.upper() and value.strip():
                    file_stats['course_name'] = value.strip()
                    print(f"📚 Ders Adı: {file_stats['course_name']}")
                    break
            
            if not file_stats['course_name']:
                print("⚠️  Ders adı bulunamadı")
            
            # Kazanım tablosunu çıkar
            kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text=full_text)
            
            if kazanim_tablosu_data:
                file_stats['has_headers'] = True
                file_stats['header_count'] = len(kazanim_tablosu_data)
                self.files_with_headers += 1
                
                print(f"✅ Başlık Çıkarma: {file_stats['header_count']} başlık bulundu")
                
                # Öğrenme birimi analizi
                result = extract_ob_tablosu(full_text=full_text)
                
                # Eşleşme analizini yap
                match_analysis = self._analyze_matches(result, kazanim_tablosu_data)
                file_stats.update(match_analysis)
                
                if file_stats['match_count'] > 0:
                    file_stats['has_matches'] = True
                    self.files_with_matching_headers += 1
                    print(f"🎯 Eşleşme Analizi: {file_stats['match_count']}/{file_stats['header_count']} başlık eşleşti")
                    
                    # Tam eşleşme kontrolü
                    if file_stats['match_count'] == file_stats['header_count']:
                        file_stats['is_perfect_match'] = True
                        self.files_with_perfect_matches += 1
                        if file_stats['course_name']:
                            self.perfect_match_courses.append({
                                'course_name': file_stats['course_name'],
                                'filename': file_stats['filename'],
                                'path': file_stats['path'],
                                'header_count': file_stats['header_count']
                            })
                        print("🏆 TAM EŞLEŞME: Tüm başlıklar eşleşti!")
                else:
                    print(f"⚠️  Eşleşme Analizi: Hiçbir başlık eşleşmedi")
                    self.files_without_matches.append(file_stats)
                
                # Eşleşmeyen başlıkları göster
                if file_stats['no_match_headers']:
                    print(f"❌ Eşleşmeyen Başlıklar: {', '.join(file_stats['no_match_headers'])}")
                    
            else:
                file_stats['error'] = "Kazanım tablosu bulunamadı"
                print(f"❌ HATA: Kazanım tablosu bulunamadı")
                self.processing_errors.append(file_stats)
                
        except Exception as e:
            file_stats['error'] = str(e)
            self.processing_errors.append(file_stats)
            print(f"❌ HATA: {str(e)}")
        
        self.header_extraction_details.append(file_stats)
        return file_stats
    
    def _analyze_matches(self, ob_result, kazanim_data):
        """Öğrenme birimi eşleşme sonuçlarını analiz et"""
        match_count = 0
        no_match_headers = []
        
        if not ob_result or "eşleşme" not in ob_result:
            return {
                'match_count': 0,
                'no_match_headers': [item['title'] for item in kazanim_data]
            }
        
        # Eşleşme satırlarını analiz et
        lines = ob_result.split('\n')
        for line in lines:
            if "eşleşme" in line and "->" in line:
                # Format: "1-Başlık Adı (3) -> 1 eşleşme"
                if " -> 0 eşleşme" in line:
                    # Eşleşmeyen başlığı çıkar
                    header_part = line.split(" -> 0 eşleşme")[0]
                    if "-" in header_part:
                        header_name = header_part.split("-", 1)[1]
                        header_name = header_name.split(" (")[0].strip()
                        no_match_headers.append(header_name)
                elif ("1 eşleşme" in line or "eşleşme (alternatif)" in line) and " -> 0 eşleşme" not in line:
                    match_count += 1
        
        return {
            'match_count': match_count,
            'no_match_headers': no_match_headers
        }
    
    def finish_processing(self):
        """İşlemi tamamla ve özet raporu hazırla"""
        self.end_time = time.time()
        processing_time = self.end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 ÖZET İSTATİSTİKLER")
        print("=" * 80)
        
        print(f"⏱️  Toplam İşlem Süresi: {processing_time:.2f} saniye")
        print(f"📁 Toplam Dosya Sayısı: {self.total_files}")
        print(f"✅ İşlenen Dosya Sayısı: {self.processed_files}")
        print(f"📋 Başlık Çıkarılan Dosya Sayısı: {self.files_with_headers}")
        print(f"🎯 Başlıklarda Eşleşme Olan Dosya Sayısı: {self.files_with_matching_headers}")
        print(f"🏆 TAM Eşleşme Olan Dosya Sayısı: {self.files_with_perfect_matches}")
        print(f"⚠️  Başlıklarda Eşleşme Olmayan Dosya Sayısı: {len(self.files_without_matches)}")
        print(f"❌ Hata Alan Dosya Sayısı: {len(self.processing_errors)}")
        
        # Yüzdelik oranlar
        if self.processed_files > 0:
            success_rate = (self.files_with_headers / self.processed_files) * 100
            match_rate = (self.files_with_matching_headers / self.processed_files) * 100
            perfect_rate = (self.files_with_perfect_matches / self.processed_files) * 100
            print(f"\n📈 BAŞARI ORANLARI:")
            print(f"   📋 Başlık Çıkarma Başarı Oranı: {success_rate:.1f}%")
            print(f"   🎯 Eşleşme Başarı Oranı: {match_rate:.1f}%")
            print(f"   🏆 Tam Eşleşme Oranı: {perfect_rate:.1f}%")
        
        # TAM EŞLEŞMELİ DERSLER LİSTESİ
        if self.perfect_match_courses:
            print(f"\n🏆 TAM EŞLEŞME OLAN DERSLER ({len(self.perfect_match_courses)} adet):")
            print("-" * 60)
            for i, course in enumerate(self.perfect_match_courses, 1):
                course_name = course.get('course_name', 'İsim Bulunamadı')
                print(f"{i:2d}. {course_name}")
                print(f"     📄 {course['filename']} ({course['header_count']} başlık)")
                print(f"     📂 {course['path']}")
                print()
        else:
            print(f"\n🏆 TAM EŞLEŞME OLAN DERSLER ({self.files_with_perfect_matches} adet):")
            print("⚠️  Ders adları çıkarılamadı. Sadece dosya sayısı mevcut.")
        
        # Eşleşmeyen dosyaların listesi
        if self.files_without_matches:
            print(f"\n⚠️  EŞLEŞMEYİ OLMAYAN DOSYALAR ({len(self.files_without_matches)} adet):")
            print("-" * 60)
            for i, file_stats in enumerate(self.files_without_matches, 1):
                course_name_info = f" - {file_stats['course_name']}" if file_stats['course_name'] else ""
                print(f"{i:2d}. {file_stats['filename']}{course_name_info}")
                print(f"     📂 {file_stats['path']}")
                if file_stats['no_match_headers']:
                    print(f"     ❌ Eşleşmeyen başlıklar: {', '.join(file_stats['no_match_headers'])}")
                print()
        
        # Hata alan dosyaların listesi
        if self.processing_errors:
            print(f"\n❌ HATA ALAN DOSYALAR ({len(self.processing_errors)} adet):")
            print("-" * 60)
            for i, file_stats in enumerate(self.processing_errors, 1):
                course_name_info = f" - {file_stats['course_name']}" if file_stats['course_name'] else ""
                print(f"{i:2d}. {file_stats['filename']}{course_name_info}")
                print(f"     📂 {file_stats['path']}")
                print(f"     ❌ Hata: {file_stats['error']}")
                print()
        
        # Detaylı başlık istatistikleri
        self._print_detailed_header_stats()
        
        print("=" * 80)
        print(f"⏰ Bitiş Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📊 Analiz tamamlandı!")
    
    def _print_detailed_header_stats(self):
        """Detaylı başlık istatistiklerini yazdır"""
        print(f"\n📊 DETAYLI BAŞLIK İSTATİSTİKLERİ:")
        print("-" * 60)
        
        # Toplam başlık sayısı
        total_headers = sum(file_stats['header_count'] for file_stats in self.header_extraction_details if file_stats['has_headers'])
        total_matches = sum(file_stats['match_count'] for file_stats in self.header_extraction_details)
        
        print(f"📋 Toplam Çıkarılan Başlık Sayısı: {total_headers}")
        print(f"🎯 Toplam Eşleşen Başlık Sayısı: {total_matches}")
        
        if total_headers > 0:
            overall_match_rate = (total_matches / total_headers) * 100
            print(f"📈 Genel Başlık Eşleşme Oranı: {overall_match_rate:.1f}%")
        
        # En çok bulunan başlıklar
        header_frequency = {}
        for file_stats in self.header_extraction_details:
            if file_stats['has_headers']:
                # Kazanım tablosundan başlık isimlerini çıkar (bu bilgi şu an mevcut değil, opsiyonel)
                pass
        
        print(f"⚡ Ortalama Dosya Başına Başlık: {total_headers/max(self.files_with_headers,1):.1f}")
        print(f"⚡ Ortalama Dosya Başına Eşleşme: {total_matches/max(self.processed_files,1):.1f}")

def main():
    """Ana işlev"""
    print("🔍 DBF Dosya İşleme İstatistik Analizi Başlatılıyor...")
    print("📋 Dosya bütünlüğü kontrolü yapılıyor...")
    
    # Tüm dosyaları bul (dosya bütünlüğü kontrolü ile)
    all_files = komutlar(validate_files=True)
    
    if not all_files:
        print("❌ HATA: data/dbf dizininde hiç PDF/DOCX dosyası bulunamadı.")
        sys.exit(1)
    
    # İstatistik nesnesini oluştur
    stats = DBFProcessingStats()
    stats.total_files = len(all_files)
    
    # İşleme başla
    stats.start_processing()
    
    # Her dosyayı işle
    for file_path in all_files:
        stats.process_file(file_path)
    
    # İşlemi tamamla ve raporu yazdır
    stats.finish_processing()

if __name__ == "__main__":
    main()