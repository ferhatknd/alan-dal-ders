# DBF2 Öğrenme Birimi Okuma Sistemi

## 📋 Genel Bakış

`modules/utils_dbf2.py` modülü, DBF PDF dosyalarının **2. sayfa ve sonrasındaki** öğrenme birimi içeriklerini çıkarmak için tasarlanmıştır. Bu modül **fitz kullanmaz**, tüm metin verilerini `utils_dbf1.py` modülünden alır.

## 🎯 Ana Amaç

DBF PDF'lerinden **hiyerarşik öğrenme birimi yapısını** çıkarmak:
```
Öğrenme Birimi → Konular → Kazanımlar
```

**Kazanımlar Nedir?**
Her dersin öğrenme birimlerine bağlı konuların öğrenilmesi sonucu öğrenen kişiye hangi yetenekleri kazandıracağını gösteren eğitim hedefleridir. Bu ifadeler MEB müfredatının temel yapı taşlarıdır ve öğrencilerin neleri öğrenmesi gerektiğini detaylandırır.

## 🔧 Çalışma Prensibi

### 1. İki Aşamalı Veri Entegrasyonu

```python
# Aşama 1: Kazanım tablosundan başlık bilgileri al (utils_dbf1'den)
kazanim_tablosu_str, kazanim_tablosu_data = ex_kazanim_tablosu(full_text)

# Aşama 2: Bu başlıkları öğrenme birimi alanında bul ve kazanımları çıkar
boundaries = extract_table_boundaries(full_text, kazanim_tablosu_data)
```

### 2. Tablo Sınır Tespiti

**`extract_table_boundaries()` Fonksiyonu:**
- **Başlangıç Noktası**: `TOPLAM` kelimesini bulur
- **Header Tespiti**: `ÖĞRENME BİRİMİ`, `KONULAR`, `KAZANIM AÇIKLAMLARI` gibi başlıkları arar  
- **Bitiş Tespiti**: Stop word'leri tablo başlangıcından itibaren arar
- **Sınırsız Arama**: Stop word bulunduğu yerde durur, karakter sınırı yoktur

```python
# Stop word'ler - tablo başlangıcından itibaren sınırsız arama
stop_words = ["UYGULAMA", "FAALİYET", "TEMRİN", "DERSİN", "DERSĠN"]
stop_idx = full_text_normalized_for_search.find(stop_word_normalized, table_start)
```

### 3. Header Eşleştirme ve Doğrulama

**`find_header_matches_with_validation()` Fonksiyonu:**
- **Normalize Edilmiş Arama**: Türkçe karakter sorunlarını çözer
- **Pattern Validation**: Her başlık için konu numaralarının varlığını kontrol eder
- **Multiple Match Handling**: Çoklu eşleştirmeleri yönetir

**Doğrulama Algoritması:**
```python
def validate_konu_patterns(text, konu_sayisi, start_pos=0, search_limit=4000):
    patterns = [
        f"{rakam}. ",     # "1. Konu" 
        f"{rakam} ",      # "1 Konu"
        f"{rakam}.",      # "1.Konu" (boşluksuz)
        f" {rakam}. ",    # " 1. Konu"
        f" {rakam}.",     # " 1.Konu"
        f"\n{rakam}. ",   # Satır başında
        f"\n{rakam}."     # Satır başında boşluksuz
    ]
```

### 4. Kazanım Çıkarma Süreci

**`ex_ob_tablosu_konu_sinirli_arama()` Fonksiyonu:**

#### 4.1 Sınırlı Çalışma Alanı Belirleme
```python
# Başlıktan sonraki metni al
after_baslik = text[baslik_idx + len(baslik):]

# Sonraki başlığın pozisyonunu bul
next_matched_header_pos = len(after_baslik)
for header in all_matched_headers:
    if header['position'] > baslik_idx:
        relative_pos = header['position'] - (baslik_idx + len(baslik))
        if 0 < relative_pos < next_matched_header_pos:
            next_matched_header_pos = relative_pos
```

#### 4.2 Sıralı Konu Çıkarma
```python
for konu_no in range(1, konu_sayisi + 1):
    # Gelişmiş pattern arama
    patterns = [f"{konu_str}. ", f"{konu_str} ", f"{konu_str}.", ...]
    
    # Konu pozisyonunu bul
    found_pos = work_area.find(pattern, current_pos)
    
    # Sonraki konu numarasına kadar olan metni al
    if konu_no < konu_sayisi:
        next_patterns = [f"{next_konu_str}. ", ...]
        konu_content = work_area[found_pos:next_found_pos]
    else:
        konu_content = work_area[found_pos:]  # Son konu - sona kadar
```

#### 4.3 Kazanım İçeriği Temizleme
```python
# Kazanım içeriğini temizle
cleaned_content = konu_content.strip()

# Konu numarasını temizle (sadece gerçek konu numaralarını)
if cleaned_content.startswith(f"{konu_no}. "):
    cleaned_content = cleaned_content.replace(f"{konu_no}. ", "", 1)

# Whitespace normalize et
cleaned_content = re.sub(r'\s+', ' ', cleaned_content.strip())
```

**Not**: Bu temizleme işlemi sonrasında elde edilen `cleaned_content`, o konunun kazanımlarını içerir. Örneğin "Kişisel Bakım" konusu için çıkarılan metin: "Tekniğine uygun kişisel bakımını yapar. Kişisel hijyenin önemi açıklanır..." gibi eğitim hedeflerini listeler.

## 📊 Çıktı Formatı

### Ana Fonksiyon: `ex_ob_tablosu(full_text)`

**Dönen Değer**: Formatlı string
```
--------------------------------------------------
Öğrenme Birimi Alanı:
1-Kişisel Hijyen (4) -> 1 eşleşme
2-Hijyen ve Sanitasyon (4) -> 1 eşleşme
3-Mutfak Üniteleri (5) -> 1 eşleşme
--------------------------------------------------
1-Kişisel Hijyen (4) -> 1. Eşleşme
1. Kişisel Bakım
2. İş Kıyafetlerini giyme
3. Vücut Mekaniklerine Uygun Hareketler
4. Personelin Üzerinde ve Dolabında Bulundurulması Gereken Araç ve Gereçler
[Her konunun eğitim hedefleri ve kazanımları...]
```

### Kazanım Çıkarma Fonksiyonu: `ex_ob_tablosu_konu_sinirli_arama()`

**Dönen Değer**: Dictionary
```python
{
    'success': True,
    'content_lines': [
        "1. Kişisel Bakım [kazanımlar ve eğitim hedefleri...]",
        "2. İş Kıyafetlerini giyme [kazanımlar ve eğitim hedefleri...]"
    ],
    'konu_contents': [
        {
            'konu_no': 1,
            'konu_adi': "Kişisel Bakım",
            'konu_icerigi': "Tekniğine uygun kişisel bakımını yapar. Kişisel hijyenin önemi açıklanır ve konuklar üzerinde işletmenin imajı anlamında etkili olduğu vurgulanır..."
        }
    ],
    'baslik': "Kişisel Hijyen",
    'konu_sayisi': 4
}
```

**Önemli**: `konu_icerigi` alanı, o konunun tüm kazanımlarını ve eğitim hedeflerini içeren metindir. Bu metin MEB müfredatının o konu için belirlediği öğrenme çıktılarını detaylandırır.

## 🛠️ Yardımcı Fonksiyonlar

### TextProcessor Class
```python
class TextProcessor:
    def __init__(self, text):
        self.original = text
        self.normalized = normalize_turkish_text(text)
        self._cache = {}  # Performans için cache
```

### Normalize Fonksiyonu
```python
def normalize_turkish_text(text):
    # İ -> I, ı -> i, ğ -> g, ü -> u, ş -> s, ö -> o, ç -> c
    char_map = {
        'İ': 'I', 'ı': 'i', 'Ğ': 'G', 'ğ': 'g',
        'Ü': 'U', 'ü': 'u', 'Ş': 'S', 'ş': 's', 
        'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'
    }
```

### Yedek Plan Fonksiyonu
```python
def ex_ob_tablosu_konu_bulma_yedek_plan(text, original_baslik, konu_sayisi):
    # Ana eşleştirme başarısız olduğunda
    # "1" rakamı tabanlı pattern matching ile alternatif yöntem
    one_pattern = r'(?:^|\.|\\n|\\s)1(?:\.|\\s)'
```

## 🔄 İş Akışı Özeti

1. **Kazanım Tablosundan Referans**: `utils_dbf1.ex_kazanim_tablosu()` ile başlık listesi al
2. **Tablo Sınırları**: `extract_table_boundaries()` ile öğrenme birimi alanını belirle  
3. **Header Validation**: `find_header_matches_with_validation()` ile geçerli başlıkları doğrula
4. **Kazanım Çıkarma**: `ex_ob_tablosu_konu_sinirli_arama()` ile her başlığın konularını ve kazanımlarını çıkar
5. **Format ve Döndür**: Structured data ve formatlı string olarak sonuçları döndür

## 🚨 Kritik Özellikler

### 1. Gelişmiş Pattern Matching
- **9 farklı pattern** ile konu numaralarını arar
- **Boşluksuz format** desteği (`1.Konu`)
- **Search limit** 4000 karakter

### 2. Sınırsız Boundary Tespiti
- **Stop word tabanlı** doğal sınır belirleme
- **Tablo başlangıcından itibaren** sınırsız arama
- **Multiple header support** ile çoklu başlık formatları

### 3. Performans Optimizasyonu
- **TextProcessor cache** sistemi
- **Sınırlı arama alanları** (4000 karakter limit)
- **Early termination** pattern'leri

### 4. Hata Yönetimi
- **Yedek plan fonksiyonu** alternatif eşleştirme için
- **Graceful degradation** başlık bulunamazsa 
- **Detailed error reporting** debug için

## 📈 Başarı Metrikleri

Test dosyası örneği:
- ✅ **Kişisel Hijyen**: 4/4 konu
- ✅ **Hijyen ve Sanitasyon**: 4/4 konu  
- ✅ **Mutfak Üniteleri**: 5/5 konu
- ✅ **Besin Öğeleri**: 6/6 konu
- ✅ **Besin Grupları**: 6/6 konu

**Toplam Başarı Oranı**: %100 (tüm başlıklar ve konular başarıyla çıkarıldı)