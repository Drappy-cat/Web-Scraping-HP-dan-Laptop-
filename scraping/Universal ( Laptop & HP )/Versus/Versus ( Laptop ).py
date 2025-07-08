import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime
import random

# ==============================================================================
# KONFIGURASI TERPUSAT UNTUK VERSUS.COM
# ==============================================================================
CONFIG = {
    'base_url': "https://versus.com",
    'start_url': "https://versus.com/en/laptop",
    'selectors': {
        'cookie_button': "#uc-btn-accept-banner",
        'product_card': 'a[data-test-id="product-card"]',
        'product_name': 'h1[data-test-id="product-name"]',
        'versus_score': 'div[data-test-id="total-score-card-score"]',
        'specs_container': 'div[data-test-id="specs-list"]',
        'spec_category_title': 'div[data-test-id="category-title"]',
    },
    'scroll_pause_time': 4,
    'max_retries': 3,
    'retry_delay_seconds': 20
}

# ==============================================================================
# FUNGSI-FUNGSI
# ==============================================================================

def setup_driver():
    """Menginisialisasi Selenium WebDriver dengan opsi penyamaran."""
    print("🔧 Inisialisasi Selenium WebDriver (Mode Normal dengan Penyamaran)...")
    options = webdriver.ChromeOptions()
    
    # <--- PERUBAIKAN UTAMA: Opsi untuk menyamarkan deteksi otomasi ---
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # --- Akhir Perbaikan Utama ---

    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)

    # <--- PERUBAIKAN UTAMA: Menjalankan skrip untuk 'menipu' situs web ---
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    # --- Akhir Perbaikan Utama ---
    
    return driver


def get_all_laptop_links_with_scrolling(driver):
    """
    Menggunakan Selenium untuk menggulir halaman hingga ke bawah untuk memuat
    semua laptop, lalu mengumpulkan semua link produk.
    """
    print(f"🌍 Mengakses halaman utama: {CONFIG['start_url']}")
    driver.get(CONFIG['start_url'])

    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG['selectors']['cookie_button'])))
        cookie_button.click()
        print("    ✅ Cookie banner diterima.")
        time.sleep(2)
    except TimeoutException:
        print("    ℹ️ Tidak ada cookie banner yang ditemukan atau sudah diterima.")

    print("📜 Memulai proses 'infinite scroll' untuk memuat semua laptop...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print("    ...scrolling...")
        time.sleep(CONFIG['scroll_pause_time'])
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # Lakukan satu scroll terakhir untuk memastikan
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(CONFIG['scroll_pause_time'])
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                 print("    🏁 Telah mencapai bagian bawah halaman.")
                 break
        last_height = new_height

    try:
        print("\n🔗 Mengumpulkan semua tautan laptop dari halaman...")
        # <--- PERUBAIKAN: Menggunakan kondisi 'visibility_of_all_elements_located' yang lebih andal
        WebDriverWait(driver, 25).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, CONFIG['selectors']['product_card'])))
        
        product_elements = driver.find_elements(By.CSS_SELECTOR, CONFIG['selectors']['product_card'])
        
        all_links = [elem.get_attribute("href") for elem in product_elements]
        unique_links = list(set(all_links))
        
        if not unique_links:
            print("    ❌ Gagal menemukan tautan produk meskipun sudah menunggu. Coba periksa koneksi atau selektor lagi.")
            return []
            
        print(f"    ✅ Berhasil mengumpulkan {len(unique_links)} tautan laptop unik.")
        return unique_links
    except TimeoutException:
        print("    ❌ Gagal menemukan kartu produk setelah scrolling selesai. Kemungkinan diblokir atau terjadi perubahan layout.")
        return []

# Fungsi scrape_laptop_details dan blok if __name__ == '__main__' tidak perlu diubah.
# Salin dan tempel semua kode di atas, termasuk bagian yang tidak berubah.
def scrape_laptop_details(driver, url):
    """
    Menggunakan Selenium untuk membuka halaman detail dan mengambil semua spesifikasi.
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CONFIG['selectors']['product_name'])))

        laptop_data = {"Product URL": url}
        
        laptop_data["Device Name"] = driver.find_element(By.CSS_SELECTOR, CONFIG['selectors']['product_name']).text.strip()
        try:
            laptop_data["Versus Score"] = driver.find_element(By.CSS_SELECTOR, CONFIG['selectors']['versus_score']).text.strip()
        except NoSuchElementException:
            laptop_data["Versus Score"] = "N/A"

        specs_container = driver.find_element(By.CSS_SELECTOR, CONFIG['selectors']['specs_container'])
        all_children = specs_container.find_elements(By.XPATH, "./*")

        current_category = "General"
        for child in all_children:
            if child.get_attribute("data-test-id") == "category-title":
                current_category = child.text.strip().replace(' ', '_').replace('&', 'and')
            else:
                try:
                    spec_parts = child.find_elements(By.XPATH, "./div")
                    if len(spec_parts) >= 2:
                        spec_name = spec_parts[0].text.strip()
                        spec_value = spec_parts[1].text.strip()
                        clean_title = re.sub(r'[^A-Za-z0-9_]+', '', spec_name.replace(' ', '_'))
                        column_name = f"{current_category}_{clean_title}"
                        laptop_data[column_name] = spec_value
                except Exception:
                    continue
        
        return laptop_data
    except TimeoutException:
        print(f"        ❌ Timeout saat memuat detail dari URL: {url}")
        return None
    except Exception as e:
        print(f"        ❌ Terjadi error tak terduga saat memproses URL {url}: {e}")
        return None


if __name__ == '__main__':
    driver = setup_driver()
    all_laptops_data = []

    print("\n" + "=" * 80)
    print("🚀 MEMULAI PROSES SCRAPING LAPTOP DARI VERSUS.COM")
    print("=" * 80)

    product_links = get_all_laptop_links_with_scrolling(driver)

    if not product_links:
        print("❌ Tidak ada tautan produk yang berhasil dikumpulkan. Proses dihentikan.")
    else:
        print(f"\n🕵️  Memulai pengambilan detail untuk {len(product_links)} laptop...")
        
        for i, url in enumerate(product_links):
            print(f"\n    [PROSES {i + 1}/{len(product_links)}] URL: {url}")

            laptop_details = None
            for attempt in range(CONFIG['max_retries']):
                scraped_data = scrape_laptop_details(driver, url)
                if scraped_data:
                    laptop_details = scraped_data
                    print(f"        👍 [VALID] Data untuk '{laptop_details.get('Device Name', 'N/A')}' berhasil diambil.")
                    break
                else:
                    print(f"        [GAGAL] Percobaan {attempt + 1}/{CONFIG['max_retries']} gagal.")
                    if attempt < CONFIG['max_retries'] - 1:
                        print(f"        ⏳ Mencoba lagi dalam {CONFIG['retry_delay_seconds']} detik...")
                        time.sleep(CONFIG['retry_delay_seconds'])
            
            if laptop_details:
                all_laptops_data.append(laptop_details)
            else:
                print(f"        ❌ [FINAL] Gagal total mengambil data untuk URL setelah {CONFIG['max_retries']} percobaan. Melewati URL ini.")

            delay = random.uniform(3, 8) 
            print(f"        ⏳ Jeda acak {delay:.2f} detik sebelum lanjut...")
            time.sleep(delay)

        print("\n" + "-" * 60)
        print("📦 Proses scraping selesai. Menyimpan data ke file CSV...")
        if not all_laptops_data:
            print("    ⚠️ Tidak ada data laptop valid yang terkumpul. Tidak ada file CSV yang dibuat.")
        else:
            df = pd.DataFrame(all_laptops_data)
            
            first_cols = ['Device Name', 'Versus Score', 'Product URL']
            existing_first_cols = [col for col in first_cols if col in df.columns]
            other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
            final_columns = existing_first_cols + other_cols

            df = df.reindex(columns=final_columns).fillna("N/A")
            df.insert(0, 'No', range(1, 1 + len(df)))

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nama_file_output = f"versus_laptops_{timestamp}.csv"
            df.to_csv(nama_file_output, index=False, encoding="utf-8-sig", sep=";")

            print(f"    ✅ Data berhasil disimpan ke: '{nama_file_output}'")
            print(f"    - Total Laptop Disimpan: {len(df)}")
        print("-" * 60)

    driver.quit()
    print("\n\n" + "=" * 80)
    print("🎉 SELURUH PROSES SCRAPING TELAH SELESAI 🎉")
    print("=" * 80)
    print("\nREKAPITULASI TOTAL:")
    print(f"    - Total Tautan Diperiksa: {len(product_links)}")
    print(f"    - Total Laptop Valid Ditemukan & Disimpan: {len(all_laptops_data)}")
    print("\nSilakan periksa file CSV yang telah dibuat di folder Anda.")