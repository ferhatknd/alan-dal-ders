"""
modules/utils_normalize.py - String Normalizasyon Modülü

Bu modül, string normalizasyon işlemlerini içerir.
Önceki utils.py'den ayrıştırılmıştır.

İçerdiği fonksiyonlar:
- sanitize_filename_tr: Dosya/klasör adı güvenlik normalizasyonu
- normalize_to_title_case_tr: Türkçe dil kurallarına uygun başlık formatı
"""

import os
import requests
import json
import re
import time
import unicodedata
from bs4 import BeautifulSoup

def sanitize_filename_tr(name: str) -> str:
    """
    Dosya/klasör ismi olarak kullanılabilir hale getir.
    Türkçe karakterleri normalize eder ve dosya sistemi uyumlu yapar.
    
    Args:
        name: Normalize edilecek dosya/klasör adı
        
    Returns:
        Güvenli dosya/klasör adı
    """
    if not name:
        return "bilinmeyen_alan"
    
    # Protokol alanları için özel formatlama
    if " - Protokol" in name:
        # "Alan Adı - Protokol" -> "Alan_Adi-Protokol" formatında
        base_name = name.replace(" - Protokol", "")
        safe_base = base_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        # Türkçe karakterleri düzelt (normal + PDF'den gelen bozuk karakterler)
        safe_base = safe_base.replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
        safe_base = safe_base.replace('Ç', 'C').replace('Ğ', 'G').replace('İ', 'I').replace('Ö', 'O').replace('Ş', 'S').replace('Ü', 'U')
        # PDF'den gelen bozuk karakterleri düzelt
        safe_base = safe_base.replace('Ġ', 'I').replace('ġ', 'i').replace('Ģ', 'S').replace('ģ', 's')
        safe_base = safe_base.replace('Ĝ', 'G').replace('ĝ', 'g')
        return f"{safe_base}-Protokol"
    
    # Normal alan adları için standart formatlama
    safe_name = name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    # Türkçe karakterleri düzelt (normal + PDF'den gelen bozuk karakterler)
    safe_name = safe_name.replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    safe_name = safe_name.replace('Ç', 'C').replace('Ğ', 'G').replace('İ', 'I').replace('Ö', 'O').replace('Ş', 'S').replace('Ü', 'U')
    
    # PDF'den gelen bozuk karakterleri düzelt (PyMuPDF extraction sorunları)
    safe_name = safe_name.replace('Ġ', 'I').replace('ġ', 'i').replace('Ģ', 'S').replace('ģ', 's')
    safe_name = safe_name.replace('Ĝ', 'G').replace('ĝ', 'g')
    
    return safe_name

def normalize_to_title_case_tr(name: str) -> str:
    """
    Bir metni, Türkçe karakterleri ve dil kurallarını dikkate alarak
    "Başlık Biçimine" (Title Case) dönüştürür.

    Örnekler:
    - "BİLİŞİM TEKNOLOJİLERİ" -> "Bilişim Teknolojileri"
    - "gıda ve içecek hizmetleri" -> "Gıda ve İçecek Hizmetleri"
    - "ELEKTRİK-ELEKTRONİK TEKNOLOJİSİ" -> "Elektrik-Elektronik Teknolojisi"
    - "elektrik-elektronik teknolojisi" -> "Elektrik-Elektronik Teknolojisi"

    Args:
        name: Standartlaştırılacak metin.

    Returns:
        Başlık biçimine dönüştürülmüş metin.
    """
    if not name:
        return ""

    # Tireyi geçici olarak özel karakter ile değiştir (tire öncesi/sonrası boşlukları da temizle)
    name = name.replace(' - ', '-').replace('- ', '-').replace(' -', '-')
    name = name.replace('-', ' __tire__ ')
    
    # Metni temizle: baştaki/sondaki boşluklar, çoklu boşlukları tek boşluğa indirge
    # ve tamamını küçük harfe çevirerek başla.
    # Türkçe'ye özgü 'İ' -> 'i' ve 'I' -> 'ı' dönüşümü için replace kullanılır.
    cleaned_name = ' '.join(name.strip().split()).replace('İ', 'i').replace('I', 'ı').lower()

    # Bağlaçlar gibi küçük kalması gereken kelimeler.
    lowercase_words = ["ve", "ile", "için", "de", "da", "ki"]

    words = cleaned_name.split(' ')
    final_words = []

    for word in words:
        if not word:
            continue

        if word == '__tire__':
            # Tire durumunda bir önceki kelime ile birleştir
            if final_words:
                final_words[-1] += '-'
            continue  # Bu kelimeyi atlayıp sonraki kelimeyi bekle
        elif word in lowercase_words and len(final_words) > 0:  # İlk kelime asla küçük olmasın
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += word
            else:
                final_words.append(word)
        else:
            capitalized = 'İ' + word[1:] if word.startswith('i') else word.capitalize()
            # Tire modunda isek boşluksuz ekle
            if final_words and final_words[-1].endswith('-'):
                final_words[-1] += capitalized
            else:
                final_words.append(capitalized)

    return ' '.join(final_words)