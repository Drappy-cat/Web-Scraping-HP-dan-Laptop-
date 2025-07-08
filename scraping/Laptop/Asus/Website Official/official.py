from selenium import webdriver
# from selenium.webdriver.chrome.service import Service # Tidak perlu lagi Service secara eksplisit jika pakai ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Import ChromeDriverManager
from webdriver_manager.chrome import ChromeDriverManager

# --- Konfigurasi Awal ---
# CHROMEDRIVER_PATH = r'D:\Codingan\Phyton code\Web Scraping\drivers\chromedriver.exe' # Baris ini tidak lagi dibutuhkan

URL = 'https://www.asus.com/id/laptops/for-gaming/rog-zephyrus/rog-zephyrus-g14-2023/'

# --- Setup Selenium WebDriver ---
options = webdriver.ChromeOptions()
# options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--log-level=3') # Opsional: Mengurangi output log Selenium yang terlalu banyak

driver = None
try:
    print("Membuka browser...")
    # Gunakan ChromeDriverManager untuk menginstal dan menjalankan driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get(URL)
    print(f"Mengakses: {URL}")

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.title')))

    print("Halaman berhasil dimuat. Mencari spesifikasi...")

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.2);")
    time.sleep(2)

    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')

    product_name_element = soup.select_one('h1.title')
    product_name = product_name_element.text.strip() if product_name_element else "Nama Produk Tidak Ditemukan"
    print(f"\nNama Produk: {product_name}")

    try:
        tech_specs_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tech Specs') or contains(., 'Spesifikasi Teknis')]")))
        if tech_specs_button:
            print("Tombol 'Tech Specs' ditemukan. Mengklik...")
            tech_specs_button.click()
            time.sleep(3)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        print(f"Tombol 'Tech Specs' tidak ditemukan atau tidak dapat diklik: {e}")

    spec_section = soup.find('div', class_=lambda x: x and ('spec' in x or 'features' in x))
    if spec_section:
        print("\nBagian spesifikasi ditemukan.")
        extracted_specs = {}
        spec_items = spec_section.find_all(['li', 'div', 'p', 'span'])
        for item in spec_items:
            text = item.text.strip()
            if ':' in text:
                parts = text.split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip()
                extracted_specs[key] = value
            elif text:
                pass

        if extracted_specs:
            print("\nSpesifikasi yang Ditemukan:")
            for key, value in extracted_specs.items():
                print(f"- {key}: {value}")
        else:
            print("Tidak dapat mengekstrak spesifikasi detail dari bagian yang ditemukan.")
            print("Silakan 'Inspect Element' pada halaman produk ASUS untuk menemukan selector yang tepat.")
            print("Cari elemen yang berisi spesifikasi seperti CPU, GPU, RAM, Storage, dll.")
    else:
        print("Bagian spesifikasi tidak ditemukan dengan selector generik.")
        print("Silakan 'Inspect Element' pada halaman produk ASUS untuk menemukan selector yang tepat.")
        print("Cari bagian seperti 'Spesifikasi Teknis', 'Tech Specs', atau 'Fitur'.")

except Exception as e:
    print(f"Terjadi kesalahan saat menjalankan scraping: {type(e).__name__}: {e}")

finally:
    if driver:
        print("\nMenutup browser...")
        driver.quit()
    print("Selesai.")