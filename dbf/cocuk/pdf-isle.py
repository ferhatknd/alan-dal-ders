import camelot
import re
from datetime import datetime
import os # pdf_path'ten dosya adını almak için

# DBF PDF Yolu (Her çalıştırmadan önce güncellenecek veya argüman olarak alınacak)
pdf_path = "1.pdf" # Örnek PDF adı
# output_sql_file, ders adı ve sınıfı dinamik olarak PDF'ten alacak
output_sql_file = "1.sql" # Başlangıçta boş bırakıldı

# 1. PDF'ten Metin ve Tablo Çıkarma ve Bilgi Ayrıştırma
def extract_info_from_dbf(pdf_path):
    text_content = ""
    tables = []

    try:
        # Metin çıkarma (Basit anahtar-değer çiftleri için)
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text_content += page.extract_text()
        
        # Camelot ile tablo çıkarma (Kazanım Tablosu için)
        # Tablo sayfalarını spesifik olarak belirleyebilirsiniz, veya 'all' kullanabilirsiniz.
        # Genellikle temel bilgilerin olduğu ilk sayfadan sonraki sayfalarda tablolar bulunur.
        # Bu örnek PDF'te kazanım tablosu 1. sayfada olduğu belirtilmiş.
        tables = camelot.read(pdf_path, pages='1,7-8', flavor='stream') # Sayfa 1 ve Konu/Kazanım sayfaları

    except Exception as e:
        print(f"PDF işlenirken bir hata oluştu: {e}")
        return None

    # --- Temel Bilgileri Çıkarma (Regex ile) ---
    ders_adi_match = re.search(r"DERSİN ADI\s*([^\n]+)", text_content)
    ders_adi = ders_adi_match.group(1).strip() if ders_adi_match else "Bilinmeyen Ders"

    sinif_match = re.search(r"DERSİN SINIFI\s*(\d+)\.\s*Sınıf", text_content)
    ders_sinifi = int(sinif_match.group(1)) if sinif_match else 0

    sure_match = re.search(r"DERSİN SÜRESİ\s*(\d+)\s*Ders Saati", text_content)
    ders_saati = int(sure_match.group(1)) if sure_match else 0

    amac_match = re.search(r"DERSİN AMACI\s*(.*?)(?=DERSİN KAZANIMLARI)", text_content, re.DOTALL)
    dersin_amaclari_raw = amac_match.group(1).strip() if amac_match else ""
    # Amaçları cümle cümle ayırma (nokta ve büyük harf kontrolü ile)
    dersin_amaclari = [s.strip() for s in re.split(r'\.\s*(?=[A-ZÇĞİÖŞÜ])', dersin_amaclari_raw) if s.strip()]
    if dersin_amaclari and not dersin_amaclari[-1].endswith('.'):
        dersin_amaclari[-1] += '.' # Son cümlenin sonunda nokta yoksa ekle

    ortam_donanim_match = re.search(r"EĞİTİM-ÖĞRETİM\s*ORTAM VE\s*DONANIMI\s*Ortam:.*?\s*Donanım:\s*(.*?)(?=ÖLÇME VE)", text_content, re.DOTALL)
    arac_gerecler = []
    if ortam_donanim_match:
        donanim_str = ortam_donanim_match.group(1).strip().replace("sağlanmalıdır.", "").strip()
        # Virgülle veya virgül ve boşlukla ayrılmış öğeleri bul
        arac_gerecler_temp = re.split(r',\s*|\s*,\s*', donanim_str)
        arac_gerecler = [item.strip() for item in arac_gerecler_temp if item.strip()]

    # --- Kazanım Tablosunu İşleme (Camelot'tan) ---
    ogrenme_birimleri = []
    if tables and len(tables) > 0:
        # Kazanım Tablosu genellikle ilk veya belirli bir sayfada bulunur.
        # Bu örnek PDF'te sayfa 1'de 'DERSİN KAZANIM TABLOSU' başlığı altında.
        # Camelot, başlık satırını bazen dahil edebilir, bazen etmeyebilir.
        # Burada varsayılan olarak ilk tablonun ilk df'ini alıyoruz ve başlıkları atlıyoruz.
        # Gerçek uygulamada, doğru tabloyu bulmak için `tables[i].parsing_report['page']` gibi kontroller gerekebilir.
        kazanim_table_df = tables[0].df # İlk algılanan tabloyu al

        # Sütun başlıklarını kontrol et (PDF'teki görsel başlıklar bazen tam olarak algılanmaz)
        # Burada manuel olarak sütun indekslerini kullanıyoruz: 0=Öğrenme Birimi, 1=Kazanım Sayısı, 2=Ders Saati
        for index, row in kazanim_table_df.iloc[1:].iterrows(): # Genellikle ilk satır başlık olduğu için atla
            # Boş satırları veya "TOPLAM" satırını atla
            if row[0].strip() == "" or row[0].strip() == "TOPLAM":
                continue

            ogrenme_birimi = row[0].strip()
            # Değerlerin sayı olup olmadığını kontrol etmeden önce stringe çevirip kontrol et
            kazanim_sayisi = int(row[1]) if str(row[1]).strip().isdigit() else None
            ders_saati_ob = int(row[2]) if str(row[2]).strip().isdigit() else None
            
            ogrenme_birimleri.append({
                'ogrenme_birimi': ogrenme_birimi,
                'kazanim_sayisi': kazanim_sayisi,
                'ders_saati': ders_saati_ob
            })
    
    # --- Konular ve Kazanımlar Çıkarma (Metinden Regex ile) ---
    # Bu kısım PDF'in karmaşık yapısından dolayı en zorlu kısımdır.
    # Genellikle "ÖĞRENME BİRİMİ KAZANIMLARI ve KAZANIM AÇIKLAMALARI" sütunundan alınır.
    # Bu PDF'in yapısı için çok hassas regex veya bir NLP modeli gerekebilir.
    # Basit bir yaklaşım, bilinen başlıkları ve numaralandırmaları takip etmektir.
    
    konular_kazanimlar = []
    # PDF'in metin içeriğini parçalara ayırarak konuları ve kazanımları çıkarmaya çalışın
    # Örnek: Öğrenme birimi başlıkları, Konu numaraları (örn. 1.1.), Kazanım numaraları (örn. 1.)
    
    # Tüm metni öğrenme birimlerine göre ayırın
    # Bu regex, "ÖĞRENME BİRİMİ" başlıklarını (veya benzer kalıpları) kullanarak metni bölmeye çalışır.
    # PDF'teki yapının bir örneği:
    # "ÖĞRENME BİRİMİ/ÜNİTE\nTemel Hukuk Kuralları\n..."
    # "KONULAR\n1. TEMEL HUKUK KURALLARI\n..."
    # "ÖĞRENME BİRİMİ KAZANIMLARI ve\nKAZANIM AÇIKLAMALARI\n1. Toplumsal düzen kurallarını açıklar."

    # Örnek PDF'in metin akışı, bu tip ayrıştırmayı zorlaştırır.
    # Her bir "ÖĞRENME BİRİMİ" bloğunu ayrıştırmak için daha karmaşık bir strateji izlenmeli.
    # Şimdilik, her bir öğrenme biriminin metin içeriğini alıp, sonra içindeki konuları ve kazanımları arayalım.
    
    # Basit bir strateji: PDF'in tüm metnini çekip, regex ile öğrenme birimi, konu ve kazanım kalıplarını bulmak.
    full_text_pages = ""
    for page_num in range(len(reader.pages)):
        full_text_pages += reader.pages[page_num].extract_text() + "\n---PAGE_BREAK---\n" # Sayfa sonu işaretçisi

    # Öğrenme Birimi başlıklarını alıp metni buna göre bölmeye çalışalım
    # Örn: 'Temel Hukuk Kuralları', 'Devletin Temel Organları', 'Yargı Teşkilatı ve Yargı bilişim Sistemleri', 'Hukuk Dili'
    
    # Metindeki ana öğrenme birimi başlıklarını tespit eden bir regex (Örnek PDF'teki yapısına göre)
    # Bu regex, "ÖĞRENME BİRİMİ/ÜNİTE" altındaki öğrenme birimi adlarını bulur.
    # Daha sonra bu isimleri kullanarak metin içindeki ilgili blokları ayırabiliriz.

    # Önceki kodunuzdaki gibi manuel olarak konular_kazanimlar_data'yı doldurmak yerine,
    # burada dinamik çıkarma yapılmalı. Bu, en çok efor gerektiren kısımdır.
    # PDF'in düzensiz formatı göz önüne alındığında, bu kısım en çok özelleştirme gerektirecektir.
    # Örneğin, her bir öğrenme birimi için ayrı ayrı regex kalıpları veya bir durum makinesi kullanılabilir.
    
    # Basit bir örnek (Tüm konuları ve kazanımları tek bir listede toplar):
    # Bu kısım, manuel olarak verdiğiniz örnek verilerin yerine geçmelidir.
    
    # Konu başlıkları (örneğin "1. TEMEL HUKUK KURALLARI") ve kazanımlar (örneğin "1. Toplumsal düzen kurallarını açıklar.")
    # arasındaki ilişkiyi kurmak için daha sofistike bir parsing gerekir.
    
    # Geçici olarak, önceki manuel verilere benzer bir yapı oluşturuyorum,
    # ancak gerçek uygulamada bu kısım PDF metin analiziyle doldurulacaktır.
    # Bu kısmı otomatikleştirmek için her öğrenme biriminin başlangıcını ve sonunu,
    # içindeki konu ve kazanım kalıplarını tespit eden sağlam regex'ler yazılmalıdır.
    
    # Aşağıdaki 'konular_kazanimlar_data' kısmı, önceki manuel girişe dayanmaktadır.
    # PDF'ten otomatik olarak çıkarmak için aşağıdaki gibi bir döngü ve regex'ler kullanılmalıdır:

    # Pseudo-code for automatic extraction of Konular and Kazanımlar:
    # Iterate through pages or sections of text_content
    # Identify current 'Öğrenme Birimi'
    # Use regex to find 'Konu' patterns (e.g., 'X.Y.Z. KONU ADI')
    # Use regex to find 'Kazanım' patterns (e.g., 'X. Kazanım Metni')
    # Associate kazanims with the nearest preceding konu.
    
    # Örnek olarak, Hukuk Dili ve Terminolojisi DBF'deki ilk kazanımı otomatik çekme denemesi:
    # 1. Toplumsal düzen kuralları, hukuk kurallarının özellikleri, kişi ve hak kavramları, insan hakları ve demokrasi ile anayasal hak ve sorumluluklarına ait işlemleri yapar.
    # Regex ile "DERSİN KAZANIMLARI" altındaki maddeleri çekme:
    kazanimlar_ana_match = re.search(r"DERSİN\s*KAZANIMLARI\s*(.*?)(?=EĞİTİM-ÖĞRETİM)", text_content, re.DOTALL)
    if kazanimlar_ana_match:
        kazanimlar_text = kazanimlar_ana_match.group(1).strip()
        # Numaralandırılmış listelerdeki kazanımları ayırma
        # Bu regex, 'X.' veya 'X.' gibi başlayan satırları ayırır.
        ana_kazanimlar_list = re.findall(r'(\d+\.\s*.*?)(?=\s*\d+\.|\s*TOPLAM|$)', kazanimlar_text, re.DOTALL)
        
        # Bu ana kazanımları, öğrenme birimleriyle nasıl ilişkilendireceğimiz, PDF'in yapısına bağlı.
        # Mevcut PDF'te, bu kazanımlar birimlere dağılmış durumda.
        # Bu nedenle, bu kısım için daha detaylı, öğrenme birimi bazlı regexler gerekecek.
        # Şimdilik, sadece bu bölümü dinamikleştirmenin karmaşıklığına dikkat çekmek için bırakıyorum.
        # Bu, büyük olasılıkla manuel olarak girdiğiniz 'konular_kazanimlar_data' yerine geçecektir.
    
    # Eğer bu kısmı tamamen otomatikleştirmek istiyorsanız,
    # her öğrenme birimi bloğunun metnini ayırmalı ve
    # o bloğun içindeki konuları ve kazanımları regex veya NLP ile çıkarmalısınız.
    # Bu, bu dosyanın kapsamı dışında daha sofistike bir NLP projesidir.
    # Şimdilik, bu örnekte 'konular_kazanimlar_data' hala manuel olarak sağlanmış gibi kabul edelim.
    
    # (ÖNEMLİ: Bu kısım hala manuel veriye dayanmaktadır, otomatikleştirilmedi)
    konular_kazanimlar_data = [
        {'ogrenme_birimi': 'Temel Hukuk Kuralları', 'konu': '1. TEMEL HUKUK KURALLARI', 'kazanim': ['1. Toplumsal düzen kurallarını açıklar.']},
        {'ogrenme_birimi': 'Temel Hukuk Kuralları', 'konu': '1.1. TOPLUMSAL DÜZEN KURALLARI', 'kazanim': []},
        {'ogrenme_birimi': 'Temel Hukuk Kuralları', 'konu': '1.1.1. Din Kuralları', 'kazanim': []},
        # ... (Diğer manuel konular ve kazanımlar buraya gelecek) ...
        {'ogrenme_birimi': 'Hukuk Dili', 'konu': '4.3.2.2. Adli Dilekçeler', 'kazanim': []},
        {'ogrenme_birimi': 'Hukuk Dili', 'konu': 'a) Hukuk Yargılamasına İlişkin Dilekçeler', 'kazanim': []},
        # ... (Diğer konular ve kazanımlar) ...
    ]


    return {
        'ders_adi': ders_adi,
        'ders_sinifi': ders_sinifi,
        'ders_saati': ders_saati,
        'dersin_amaclari': dersin_amaclari,
        'arac_gerecler': arac_gerecler,
        'ogrenme_birimleri': ogrenme_birimleri,
        'konular_kazanimlar': konular_kazanimlar_data # Bu kısmı otomatik çekmek için daha çok çaba gerek
    }

# 2. SQL Sorgusu Oluşturma (Bu fonksiyon değişmeden kalır, çünkü mantığı geneldir)
def generate_sql_insert_statements(data, dbf_url):
    sql_statements = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    sql_statements.append("-- =====================================================\n")
    sql_statements.append("-- DERS BİLGİ FORMU (DBF) VERITABANI KAYITLARI\n")
    sql_statements.append("-- =====================================================\n")
    sql_statements.append(f"-- Ders: {data['ders_adi']}\n")
    sql_statements.append(f"-- Sınıf: {data['ders_sinifi']}\n")
    sql_statements.append(f"-- Tarih: {current_date}\n")
    sql_statements.append("-- =====================================================\n\n")

    # 1. ALAN VERİSİ (Varsayımsal olarak "Adalet" alanı)
    sql_statements.append("-- 1. ALAN VERİSİ\n")
    sql_statements.append("-- Hukuk Dili ve Terminolojisi dersi için spesifik bir alan belirtilmemiştir.\n")
    sql_statements.append("-- Ancak, genellikle bu tür dersler Adalet alanı altında bulunur.\n")
    sql_statements.append("-- Bu yüzden varsayımsal bir alan olarak 'Adalet' eklenmiştir.\n")
    sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_alan (alan_adi, cop_url) \nVALUES ('Adalet', NULL);\n\n")

    # 2. DAL VERİSİ (Varsayımsal olarak "Hukuk" dalı)
    sql_statements.append("-- 2. DAL VERİSİ\n")
    sql_statements.append("-- Hukuk Dili ve Terminolojisi dersi için spesifik bir dal belirtilmemiştir.\n")
    sql_statements.append("-- Ancak, genellikle bu tür dersler Hukuk veya Adalet dalları altında bulunur.\n")
    sql_statements.append("-- Bu yüzden varsayımsal bir dal olarak 'Hukuk' eklenmiştir.\n")
    sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_dal (dal_adi, alan_id)\nSELECT 'Hukuk', id FROM temel_plan_alan WHERE alan_adi = 'Adalet';\n\n")

    # 3. DERS VERİSİ
    sql_statements.append("-- 3. DERS VERİSİ\n")
    sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders (ders_adi, sinif, ders_saati, dbf_url)\nSELECT '{data['ders_adi']}', {data['ders_sinifi']}, {data['ders_saati']}, '{dbf_url}'\nWHERE NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders \n    WHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']}\n);\n\n")

    # 4. DERS-DAL İLİŞKİSİ
    sql_statements.append("-- 4. DERS-DAL İLİŞKİSİ\n")
    sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_dal (ders_id, dal_id)\nSELECT \n    d.id, \n    dl.id\nFROM temel_plan_ders d, temel_plan_dal dl, temel_plan_alan a\nWHERE d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']}\nAND dl.dal_adi = 'Hukuk' AND dl.alan_id = a.id AND a.alan_adi = 'Adalet'\nAND NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_dal \n    WHERE ders_id = d.id AND dal_id = dl.id\n);\n\n")

    # 5. DERSİN AMAÇLARI
    sql_statements.append("-- 5. DERSIN AMAÇLARI\n")
    for amac in data['dersin_amaclari']:
        # SQL enjeksiyonuna karşı tırnak işaretlerini kaçırmayı unutmayın, ancak SQLite için genellikle sorun olmaz.
        clean_amac = amac.replace("'", "''") # Tek tırnakları çift tırnak yap
        sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_amac (ders_id, amac)\nSELECT id, '{clean_amac}' FROM temel_plan_ders WHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']}\nWHERE NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_amac \n    WHERE ders_id = (SELECT id FROM temel_plan_ders WHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']})\n    AND amac = '{clean_amac}'\n);\n\n")

    # 6. ARAÇ-GEREÇ VERİLERİ
    sql_statements.append("-- 6. ARAÇ-GEREÇ VERİLERİ\n")
    for arac in data['arac_gerecler']:
        clean_arac = arac.replace("'", "''")
        sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_arac (arac_gerec) VALUES ('{clean_arac}');\n")
    sql_statements.append("\n")

    # 7. DERS-ARAÇ İLİŞKİLERİ
    sql_statements.append("-- 7. DERS-ARAÇ İLİŞKİLERİ\n")
    for arac in data['arac_gerecler']:
        clean_arac = arac.replace("'", "''")
        sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_arac (ders_id, arac_id)\nSELECT d.id, a.id\nFROM temel_plan_ders d, temel_plan_arac a\nWHERE d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']} AND a.arac_gerec = '{clean_arac}'\nAND NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_arac \n    WHERE ders_id = d.id AND arac_id = a.id\n);\n\n")

    # 8. ÖĞRENME BİRİMLERİ
    sql_statements.append("-- 8. ÖĞRENME BİRİMLERİ\n")
    for ob in data['ogrenme_birimleri']:
        clean_ob_adi = ob['ogrenme_birimi'].replace("'", "''")
        sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_ogrenme_birimi (ders_id, ogrenme_birimi, kazanim_sayisi, ders_saati)\nSELECT id, '{clean_ob_adi}', {ob['kazanim_sayisi']}, {ob['ders_saati']}\nFROM temel_plan_ders WHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']}\nWHERE NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_ogrenme_birimi \n    WHERE ders_id = (SELECT id FROM temel_plan_ders WHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']})\n    AND ogrenme_birimi = '{clean_ob_adi}'\n);\n\n")

    # 9. KONULAR ve 10. KAZANIMLAR
    sql_statements.append("-- 9. KONULAR\n")
    sql_statements.append("-- 10. KAZANIMLAR\n")
    for item in data['konular_kazanimlar']:
        clean_konu = item['konu'].replace("'", "''")
        # Konu ekleme
        sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_ob_konu (ogrenme_birimi_id, konu)\nSELECT ob.id, '{clean_konu}'\nFROM temel_plan_ders_ogrenme_birimi ob, temel_plan_ders d\nWHERE ob.ders_id = d.id AND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']}\nAND ob.ogrenme_birimi = '{item['ogrenme_birimi'].replace("'", "''")}'\nAND NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_ob_konu \n    WHERE ogrenme_birimi_id = ob.id AND konu = '{clean_konu}'\n);\n\n")
        
        # Kazanımları ekleme
        for kazanim in item['kazanim']:
            clean_kazanim = kazanim.replace("'", "''")
            sql_statements.append(f"INSERT OR IGNORE INTO temel_plan_ders_ob_konu_kazanim (konu_id, kazanim)\nSELECT k.id, '{clean_kazanim}'\nFROM temel_plan_ders_ob_konu k, temel_plan_ders_ogrenme_birimi ob, temel_plan_ders d\nWHERE k.ogrenme_birimi_id = ob.id AND ob.ders_id = d.id\nAND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']}\nAND ob.ogrenme_birimi = '{item['ogrenme_birimi'].replace("'", "''")}' AND k.konu = '{clean_konu}'\nAND NOT EXISTS (\n    SELECT 1 FROM temel_plan_ders_ob_konu_kazanim \n    WHERE konu_id = k.id AND kazanim = '{clean_kazanim}'\n);\n\n")

    # Doğrulama ve Hata Kontrol Sorguları (Değişmeden kalır)
    # ... (Aynı doğrulama ve hata kontrol sorguları buraya gelecek) ...
    sql_statements.append("-- =====================================================\n")
    sql_statements.append("-- DOĞRULAMA SORGULARI\n")
    sql_statements.append("-- =====================================================\n\n")

    sql_statements.append(f"SELECT 'Ders kaydı:', COUNT(*) as kayit_sayisi \nFROM temel_plan_ders \nWHERE ders_adi = '{data['ders_adi']}' AND sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT 'Öğrenme birimieri:', COUNT(*) as kayit_sayisi\nFROM temel_plan_ders_ogrenme_birimi ob, temel_plan_ders d\nWHERE ob.ders_id = d.id AND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT 'Konular:', COUNT(*) as kayit_sayisi\nFROM temel_plan_ders_ob_konu k, temel_plan_ders_ogrenme_birimi ob, temel_plan_ders d\nWHERE k.ogrenme_birimi_id = ob.id AND ob.ders_id = d.id\nAND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT 'Kazanımlar:', COUNT(*) as kayit_sayisi\nFROM temel_plan_ders_ob_konu_kazanim kz, temel_plan_ders_ob_konu k, \n     temel_plan_ders_ogrenme_birimi ob, temel_plan_ders d\nWHERE kz.konu_id = k.id AND k.ogrenme_birimi_id = ob.id AND ob.ders_id = d.id\nAND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT 'Amaçlar:', COUNT(*) as kayit_sayisi\nFROM temel_plan_ders_amac a, temel_plan_ders d\nWHERE a.ders_id = d.id AND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT 'Araç-gereçler:', COUNT(*) as kayit_sayisi\nFROM temel_plan_ders_arac da, temel_plan_ders d\nWHERE da.ders_id = d.id AND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")

    sql_statements.append("-- =====================================================\n")
    sql_statements.append("-- HATA KONTROL SORGULARI\n")
    sql_statements.append("-- =====================================================\n\n")

    sql_statements.append(f"SELECT 'Ders-Dal ilişkisi eksik mi?', \n       CASE WHEN COUNT(*) = 0 THEN 'EVET' ELSE 'HAYIR' END as durum\nFROM temel_plan_ders_dal dd, temel_plan_ders d\nWHERE dd.ders_id = d.id AND d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']};\n\n")
    sql_statements.append(f"SELECT ob.ogrenme_birimi, COUNT(k.id) as konu_sayisi\nFROM temel_plan_ders_ogrenme_birimi ob\nLEFT JOIN temel_plan_ders_ob_konu k ON ob.id = k.ogrenme_birimi_id\nJOIN temel_plan_ders d ON ob.ders_id = d.id\nWHERE d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']}\nGROUP BY ob.ogrenme_birimi;\n\n")
    sql_statements.append(f"SELECT k.konu, COUNT(kz.id) as kazanim_sayisi\nFROM temel_plan_ders_ob_konu k\nLEFT JOIN temel_plan_ders_ob_konu_kazanim kz ON k.id = kz.konu_id\nJOIN temel_plan_ders_ogrenme_birimi ob ON k.ogrenme_birimi_id = ob.id\nJOIN temel_plan_ders d ON ob.ders_id = d.id\nWHERE d.ders_adi = '{data['ders_adi']}' AND d.sinif = {data['ders_sinifi']}\nGROUP BY k.konu;\n\n")


    return "".join(sql_statements)

# Ana Çalışma Akışı
if __name__ == "__main__":
    extracted_data = extract_info_from_dbf(pdf_path)

    if extracted_data:
        # Dinamik olarak çıktı dosyası adını belirle
        # Ders adından dosya adı için güvenli bir slug oluştur
        ders_adi_slug = re.sub(r'[^\w\s-]', '', extracted_data['ders_adi'].lower())
        ders_adi_slug = re.sub(r'[-\s]+', '-', ders_adi_slug).strip('-_')
        output_sql_file = f"{ders_adi_slug}_{extracted_data['ders_sinifi']}_sinif.sql"

        # SQL oluştur
        sql_output = generate_sql_insert_statements(extracted_data, pdf_path)
        
        try:
            with open(output_sql_file, 'w', encoding='utf-8') as f:
                f.write(sql_output)
            print(f"SQL betiği başarıyla oluşturuldu: {output_sql_file}")
        except IOError as e:
            print(f"SQL dosyası yazılırken bir hata oluştu: {e}")
    else:
        print("PDF dosyasından veri çıkarılamadı.")