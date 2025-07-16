# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 MEB Mesleki Eğitim Veri İşleme Projesi - Birleşik Kılavuz

Bu dosya, Claude Code için MEB Mesleki Eğitim Veri İşleme ve Veritabanı Projesinin kapsamlı birleşik kılavuzudur. README.md, is_akisi.md ve teknik detayların tümünü içerir. Proje mantığını koruyarak her seferinde hata yapmaktan kaçınmak için tüm kritik bilgileri içerir.

**Son Güncelleme**: 2025-07-16 (JSON URL format standardizasyonu + Duplicate dal kontrolü eklendi + BOM dizin yapısı sadeleştirildi)

## 🎯 Proje Genel Bakış

[... rest of the existing content remains the same ...]

## 🚨 Kritik Hatalardan Kaçınma Kuralları

[... existing content ...]

### 11. Merkezi Fonksiyon Kullanımı ⭐ **YENİ KURAL**
- `utils.py` içindeki merkezi fonksiyonlara sadık kalalım
- Ortak yardımcı fonksiyonları ve utility metotları `utils.py` üzerinden çağır
- Tekrar eden kod parçaları yerine merkezi fonksiyonları kullan

[... rest of the existing content remains the same ...]