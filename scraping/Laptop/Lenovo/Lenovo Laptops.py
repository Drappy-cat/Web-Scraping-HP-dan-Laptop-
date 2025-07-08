import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time
import re
from datetime import datetime
import random

# --- KONFIGURASI ---
# Ditambahkan selector untuk link kategori merek
CONFIG_LENOVO = {
    'start_url': "https://www.lenovo.com/id/id/laptops/",
    'base_url': "https://www.lenovo.com",
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'},
    'selectors': {
        'cookie_button': "#onetrust-accept-btn-handler",
        # Selector untuk menemukan link ke setiap brand (misal: Legion, Yoga, ThinkPad)
        'brand_category_link': 'a.series-card',
        'load_more_button': 'button[data-track-name="load more"]',
        'product_list_container': 'div.stack-system-results',
        'product_card': 'div.stack-system-card',
        'product_link_in_card': 'a',
        'product_name': 'h1.product-title',
        'price': '.price-info .final-price',
        'tech_specs_container': '#tech_specs_container-scroll',
        'spec_row': 'div.feature-container',
        'spec_title': 'div.feature-label',
        'spec_value': 'div.feature-value',
    },
    'max_retries': 3,
    'retry_delay_seconds': 20
}


# --- FUNGSI-FUNGSI ---

def setup_driver():
    """Inisialisasi Selenium WebDriver."""
    print("🔧 Inisialisasi Selenium WebDriver (Mode Visual)...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument(f"user-agent={CONFIG_LENOVO['headers']['User-Agent']}")
    return webdriver.Chrome(options=options)


def get_links_on_product_list_page(driver):
    """
    Mengambil semua link produk dari halaman daftar produk yang sedang aktif.
    Fungsi ini akan mengklik 'load more' hingga semua produk ditampilkan.
    """
    links_on_page = set()
    try:
        print("    📦 Menunggu kontainer produk...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_list_container'])))
        print("    ✅ Kontainer produk ditemukan.")

        # Loop untuk mengklik tombol "LIHAT LAINNYA"
        while True:
            try:
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['load_more_button'])))
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                load_more_button.click()
                print("    🖱️  Mengklik tombol 'LIHAT LAINNYA'...")
                time.sleep(random.uniform(3, 5))
            except (TimeoutException, ElementClickInterceptedException):
                print("    🏁 Semua produk di kategori ini telah dimuat.")
                break

        print("\n    🔗 Mengumpulkan tautan produk dari kategori ini...")
        product_cards = driver.find_elements(By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_card'])
        for card in product_cards:
            try:
                link_element = card.find_element(By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_link_in_card'])
                if href := link_element.get_attribute('href'):
                    links_on_page.add(href)
            except Exception as e:
                print(f"        ⚠️ Gagal mendapatkan tautan dari satu kartu: {e}")
        print(f"    ✅ Berhasil mengumpulkan {len(links_on_page)} tautan unik dari kategori ini.")
        return list(links_on_page)

    except TimeoutException:
        print("    ❌ Gagal memuat halaman daftar produk untuk kategori ini.")
        return []


def run_multitab_scraping_orchestrator(driver):
    """
    Fungsi utama untuk mengelola navigasi multi-tab dan mengumpulkan semua link.
    """
    print(f"🌍 Mengakses halaman awal: {CONFIG_LENOVO['start_url']}")
    driver.get(CONFIG_LENOVO['start_url'])
    all_product_links = set()

    # Handle cookie banner
    try:
        print("    🍪 Mencari cookie banner...")
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['cookie_button'])))
        cookie_button.click()
        print("    ✅ Cookie banner diterima.")
        time.sleep(2)
    except TimeoutException:
        print("    ℹ️ Tidak ada cookie banner yang ditemukan, melanjutkan proses.")

    # Simpan handle window/tab asli
    original_window = driver.current_window_handle

    # Dapatkan semua URL kategori dari halaman utama
    print("\n🔍 Mencari semua kategori merek laptop...")
    category_elements = driver.find_elements(By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['brand_category_link'])
    category_urls = [elem.get_attribute('href') for elem in category_elements if elem.get_attribute('href')]

    if not category_urls:
        print("❌ Tidak ada kategori merek yang ditemukan. Pastikan selector sudah benar.")
        return []

    print(f"✅ Ditemukan {len(category_urls)} kategori merek. Memulai proses scraping per kategori...")

    # Loop melalui setiap URL kategori
    for i, cat_url in enumerate(category_urls):
        print("\n" + "=" * 50)
        print(f"KATEGORI {i + 1}/{len(category_urls)}: {cat_url.split('/')[-2].upper()}")
        print("=" * 50)

        # Buka kategori di tab baru
        print(f"    - Membuka kategori di tab baru...")
        driver.switch_to.new_window('tab')
        driver.get(cat_url)

        # Panggil fungsi untuk scrape link di halaman aktif (tab baru)
        links_from_category = get_links_on_product_list_page(driver)
        all_product_links.update(links_from_category)

        # Tutup tab saat ini dan kembali ke tab asli
        print("\n    - Menutup tab kategori dan kembali ke halaman utama.")
        driver.close()
        driver.switch_to.window(original_window)
        time.sleep(2)  # Jeda singkat

    print("\n🎉 Semua kategori telah dijelajahi.")
    return list(all_product_links)


def scrape_lenovo_laptop_details(url):
    """Fungsi untuk mengambil detail dari satu URL produk (Tidak Berubah)."""
    try:
        response = requests.get(url, headers=CONFIG_LENOVO['headers'])
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        laptop_data = {"Product_URL": url}
        if name_tag := soup.select_one(CONFIG_LENOVO['selectors']['product_name']):
            laptop_data["Product_Name"] = name_tag.text.strip()
        if price_tag := soup.select_one(CONFIG_LENOVO['selectors']['price']):
            laptop_data["Price"] = price_tag.text.strip()
        if specs_container := soup.select_one(CONFIG_LENOVO['selectors']['tech_specs_container']):
            for row in specs_container.select(CONFIG_LENOVO['selectors']['spec_row']):
                if (title_tag := row.select_one(CONFIG_LENOVO['selectors']['spec_title'])) and \
                        (value_tag := row.select_one(CONFIG_LENOVO['selectors']['spec_value'])):
                    title = title_tag.text.strip()
                    clean_title = re.sub(r'[^A-Za-z0-9_ ]+', '', title).replace(' ', '_')
                    value = ' | '.join([li.text.strip() for li in value_tag.find_all('li')]) or value_tag.text.strip()
                    laptop_data[clean_title] = value
        return laptop_data
    except Exception as e:
        print(f"        -> Terjadi error saat scraping detail: {e}")
        return None


# ==============================================================================
# BLOK EKSEKUSI UTAMA
# ==============================================================================
if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 MEMULAI PROSES SCRAPING MULTI-TAB DARI SITUS LENOVO INDONESIA")
    print("=" * 80)

    all_laptops_data = []
    driver = setup_driver()

    # Panggil fungsi orkestrasi baru untuk mendapatkan semua link
    laptop_links = run_multitab_scraping_orchestrator(driver)

    print("\nMenutup WebDriver...");
    driver.quit();
    print("✅ WebDriver telah ditutup.")

    if not laptop_links:
        print("\n❌ Tidak ada tautan produk yang berhasil dikumpulkan. Proses dihentikan.")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nama_file_txt = f"spesifikasi_laptop_{timestamp}.txt"
        nama_file_csv = f"lenovo_all_laptops_{timestamp}.csv"

        print("\n" + "=" * 80)
        print(f"🕵️  Memulai pengambilan detail untuk {len(laptop_links)} total laptop yang ditemukan...")
        print(f"    📄 Hasil copy-paste akan disimpan di: {nama_file_txt}")
        print(f"    📊 Hasil data tabel akan disimpan di: {nama_file_csv}")
        print("=" * 80)

        for i, url in enumerate(laptop_links):
            print(f"\n[PROSES DETAIL {i + 1}/{len(laptop_links)}] URL: {url}")
            laptop_data = scrape_lenovo_laptop_details(url)

            if laptop_data:
                print(f"    👍 [BERHASIL] Data untuk '{laptop_data.get('Product_Name', 'N/A')}' berhasil diambil.")
                all_laptops_data.append(laptop_data)

                try:
                    with open(nama_file_txt, 'a', encoding='utf-8') as f:
                        f.write("=" * 50 + "\n")
                        f.write(f"Produk: {laptop_data.get('Product_Name', 'N/A')}\n")
                        f.write(f"Harga: {laptop_data.get('Price', 'N/A')}\n")
                        f.write(f"URL: {laptop_data.get('Product_URL', 'N/A')}\n")
                        f.write("-" * 50 + "\n")
                        for key, value in laptop_data.items():
                            if key not in ['Product_Name', 'Price', 'Product_URL']:
                                f.write(f"{key.replace('_', ' ')}: {value}\n")
                        f.write("=" * 50 + "\n\n")
                except Exception as e:
                    print(f"        ⚠️ Gagal menulis ke file teks: {e}")
            else:
                print(f"    ❌ Gagal mengambil data untuk URL ini.")
            time.sleep(random.uniform(1, 3))

        print("\n" + "-" * 60)
        print("📦 Menyimpan semua data ke file CSV...")
        if all_laptops_data:
            df = pd.DataFrame(all_laptops_data)
            first_cols = ['Product_Name', 'Price', 'Product_URL']
            existing_first_cols = [col for col in first_cols if col in df.columns]
            other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
            final_columns = existing_first_cols + other_cols
            df = df.reindex(columns=final_columns).fillna("N/A")
            df.insert(0, 'No', range(1, 1 + len(df)))
            df.to_csv(nama_file_csv, index=False, encoding="utf-8-sig", sep=";")
            print(f"    ✅ Data tabel berhasil disimpan ke: '{nama_file_csv}'")
        else:
            print("    ⚠️ Tidak ada data untuk disimpan ke CSV.")
        print("-" * 60)

    print("\n\n" + "=" * 80)
    print("🎉 SELURUH PROSES SCRAPING TELAH SELESAI 🎉")
    print("=" * 80)