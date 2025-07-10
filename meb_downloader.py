import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse
import re

class MEBRarDownloader:
    def __init__(self, base_url="https://meslek.meb.gov.tr/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def create_directory(self, sinif_kodu):
        """Sınıf koduna göre dizin oluştur"""
        dir_name = f"sinif_{sinif_kodu}"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"'{dir_name}' dizini oluşturuldu.")
        return dir_name
    
    def get_page_content(self, sinif_kodu, kurum_id=1):
        """Belirtilen sınıf kodu için sayfa içeriğini al"""
        url = f"{self.base_url}dbflistele.aspx?sinif_kodu={sinif_kodu}&kurum_id={kurum_id}"
        print(f"Sayfa alınıyor: {url}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Sayfa alınırken hata: {e}")
            return None
    
    def extract_alan_adi_from_url(self, url):
        """URL'den alan adını çıkar"""
        try:
            # URL'den dosya adını al
            filename = url.split('/')[-1]
            # .rar uzantısını kaldır
            filename = filename.replace('.rar', '')
            # Sınıf bilgilerini temizle
            filename = re.sub(r'_\d{4}_\d+', '', filename)  # _2020_11 gibi
            filename = re.sub(r'_dbf_\d+', '', filename)    # _dbf_12 gibi  
            filename = re.sub(r'_\d+$', '', filename)       # sondaki sayılar
            
            # Alan adını temizle ve düzenle
            alan_adi = filename.replace('_', ' ').title()
            return alan_adi if alan_adi else "Bilinmeyen_Alan"
        except:
            return "Bilinmeyen_Alan"
    
    def find_download_links(self, html_content):
        """HTML içeriğinden RAR dosya linklerini bul"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # RAR dosya linklerini ara
        links = []
        
        # Tüm linkleri kontrol et
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            # Sadece RAR dosyası linklerini al
            if (href.endswith('.rar') or 
                'upload/dbf' in href.lower() or
                ('.rar' in href and 'dbf' in href)):
                
                full_url = urljoin(self.base_url, href)
                alan_adi = self.extract_alan_adi_from_url(full_url)
                links.append({
                    'url': full_url,
                    'text': text,
                    'alan_adi': alan_adi
                })
        
        print(f"Toplam {len(links)} RAR dosyası bulundu.")
        return links
    
    def download_file(self, url, file_path):
        """Dosyayı indir"""
        try:
            print(f"İndiriliyor: {url}")
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # Content-Type kontrolü veya URL kontrolü
            content_type = response.headers.get('content-type', '').lower()
            if ('application/rar' in content_type or 
                'application/x-rar' in content_type or 
                'application/octet-stream' in content_type or  # RAR dosyaları genelde bu şekilde gelir
                url.endswith('.rar')):
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(file_path)
                print(f"İndirildi: {file_path} ({file_size} bytes)")
                return True
            else:
                print(f"RAR dosyası değil, content-type: {content_type}, atlanıyor: {url}")
                return False
                
        except requests.RequestException as e:
            print(f"İndirme hatası {url}: {e}")
            return False
        except Exception as e:
            print(f"Genel hata {url}: {e}")
            return False
    
    def process_sinif(self, sinif_kodu, max_files=None):
        """Belirtilen sınıf için dosyaları işle"""
        print(f"\n=== Sınıf {sinif_kodu} işleniyor ===")
        
        # Dizin oluştur
        download_dir = self.create_directory(sinif_kodu)
        
        # Sayfa içeriğini al
        html_content = self.get_page_content(sinif_kodu)
        if not html_content:
            return
        
        # İndirme linklerini bul
        links = self.find_download_links(html_content)
        
        if not links:
            print("RAR dosyası bulunamadı.")
            return
        
        # Dosyaları indir
        downloaded_count = 0
        for i, link_info in enumerate(links):
            if max_files and downloaded_count >= max_files:
                print(f"Maksimum {max_files} dosya indirildi, durduruluyor.")
                break
            
            url = link_info['url']
            alan_adi = link_info['alan_adi']
            
            # Dosya adını oluştur
            file_name = f"{alan_adi.replace(' ', '_')}_sinif_{sinif_kodu}.rar"
            file_name = re.sub(r'[^\w\-_.]', '_', file_name)  # Geçersiz karakterleri temizle
            file_path = os.path.join(download_dir, file_name)
            
            # Dosya zaten varsa atla
            if os.path.exists(file_path):
                print(f"Dosya zaten mevcut, atlanıyor: {file_path}")
                continue
            
            # Dosyayı indir
            if self.download_file(url, file_path):
                downloaded_count += 1
            
            # İndirmeler arası bekleme
            time.sleep(1)
        
        print(f"Sınıf {sinif_kodu} için {downloaded_count} dosya indirildi.")

def main():
    downloader = MEBRarDownloader()
    
    print("MEB RAR Dosya İndiricisi")
    print("========================")
    
    # Önce sadece 9. sınıf, 3 dosya
    print("Önce 9. sınıf için 3 dosya indiriliyor...")
    downloader.process_sinif(9, max_files=3)
    
    # Kullanıcıdan onay al
    devam = input("\n9. sınıf tamamlandı. Diğer sınıfları da indirmek istiyor musunuz? (e/h): ")
    
    if devam.lower() in ['e', 'evet', 'y', 'yes']:
        # Tüm sınıfları indir
        for sinif in [9, 10, 11, 12]:
            downloader.process_sinif(sinif)
            time.sleep(2)  # Sınıflar arası bekleme
    
    print("\nİndirme işlemi tamamlandı!")

if __name__ == "__main__":
    main()