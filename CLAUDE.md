# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 MEB Mesleki Eğitim Veri İşleme Projesi - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı birleşik kılavuzudur. README.md, is_akisi.md ve teknik detayların tümünü içerir. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-22 (extract_olcme.py Türkçe karakter eşleştirme sistemi iyileştirildi + normalize_for_matching() fonksiyonu eklendi + DBF PDF header matching sorunu çözüldü + Türkçe I/ı, Ç/ç karakterleri için ASCII normalizasyonu + Başlık eşleştirme oranları %0'dan %80+ seviyesine çıkarıldı)

## 🚨 Kritik Hatalardan Kaçınma Kuralları

### 10. Fonksiyon Sabitliği Kuralları ⭐ **YENİ KURAL**
- **ASLA** word based hardcoded fix function kullanma
- **Her zaman** dinamik ve esnek fonksiyonlar tercih et
- Statik kelime listeleri yerine **normalizasyon ve pattern matching** kullan
- Fonksiyonlar generic olmalı, spesifik kelimelerle sınırlandırılmamalı
