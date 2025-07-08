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

# Konfigurasi tidak berubah
CONFIG_LENOVO = {
    'start_url': "https://www.lenovo.com/id/id/laptops/",
    'base_url': "https://www.lenovo.com",
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'},
    'selectors': {
        'cookie_button': "#onetrust-accept-btn-handler", 'load_more_button': 'button[data-track-name="load more"]',
        'product_list_container': 'div.stack-system-results', 'product_card': 'div.stack-system-card',
        'product_link_in_card': 'a', 'product_name': 'h1.product-title', 'price': '.price-info .final-price',
        'tech_specs_container': '#tech_specs_container-scroll', 'spec_row': 'div.feature-container',
        'spec_title': 'div.feature-label', 'spec_value': 'div.feature-value',
    },
    'max_retries': 3, 'retry_delay_seconds': 20
}


# Semua fungsi (setup_driver, get_all_laptop_links_from_lenovo, scrape_lenovo_laptop_details) tidak berubah
def setup_driver():
    print("🔧 Inisialisasi Selenium WebDriver (Mode Visual)...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu");
    options.add_argument("--start-maximized")
    options.add_argument(f"user-agent={CONFIG_LENOVO['headers']['User-Agent']}")
    return webdriver.Chrome(options=options)


def get_all_laptop_links_from_lenovo(driver):
    print(f"🌍 Mengakses halaman awal: {CONFIG_LENOVO['start_url']}")
    driver.get(CONFIG_LENOVO['start_url']);
    all_links = set()
    try:
        print("    🍪 Mencari cookie banner...")
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['cookie_button'])))
        cookie_button.click();
        print("    ✅ Cookie banner diterima.");
        time.sleep(2)
    except TimeoutException:
        print("    ℹ️ Tidak ada cookie banner yang ditemukan, melanjutkan proses.")
    try:
        print("    📦 Menunggu kontainer produk utama...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_list_container'])))
        print("    ✅ Kontainer produk berhasil ditemukan.")
        while True:
            try:
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['load_more_button'])))
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button);
                time.sleep(1)
                load_more_button.click();
                print("    🖱️  Mengklik tombol 'LIHAT LAINNYA'...");
                time.sleep(random.uniform(3, 5))
            except (TimeoutException, ElementClickInterceptedException):
                print("    🏁 Semua produk telah dimuat.");
                break
        print("\n    🔗 Mengumpulkan semua tautan produk...")
        product_cards = driver.find_elements(By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_card'])
        for card in product_cards:
            try:
                link_element = card.find_element(By.CSS_SELECTOR, CONFIG_LENOVO['selectors']['product_link_in_card'])
                if href := link_element.get_attribute('href'): all_links.add(href)
            except Exception as e:
                print(f"        ⚠️ Gagal mendapatkan tautan: {e}")
        print(f"    ✅ Berhasil mengumpulkan {len(all_links)} tautan unik.");
        return list(all_links)
    except TimeoutException:
        print("    ❌ Gagal memuat halaman produk awal."); return []


def scrape_lenovo_laptop_details(url):
    try:
        response = requests.get(url, headers=CONFIG_LENOVO['headers']);
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser');
        laptop_data = {"Product_URL": url}
        if name_tag := soup.select_one(CONFIG_LENOVO['selectors']['product_name']): laptop_data[
            "Product_Name"] = name_tag.text.strip()
        if price_tag := soup.select_one(CONFIG_LENOVO['selectors']['price']): laptop_data[
            "Price"] = price_tag.text.strip()
        if specs_container := soup.select_one(CONFIG_LENOVO['selectors']['tech_specs_container']):
            for row in specs_container.select(CONFIG_LENOVO['selectors']['spec_row']):
                if (title_tag := row.select_one(CONFIG_LENOVO['selectors']['spec_title'])) and (
                value_tag := row.select_one(CONFIG_LENOVO['selectors']['spec_value'])):
                    title = title_tag.text.strip();
                    clean_title = re.sub(r'[^A-Za-z0-9_ ]+', '', title).replace(' ', '_')
                    value = ' | '.join([li.text.strip() for li in value_tag.find_all('li')]) or value_tag.text.strip()
                    laptop_data[clean_title] = value
        return laptop_data
    except Exception as e:
        print(f"        -> Terjadi error saat scraping detail: {e}"); return None


# ==============================================================================
# BLOK EKSEKUSI UTAMA
# ==============================================================================
if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🚀 MEMULAI PROSES SCRAPING SEMUA LAPTOP DARI SITUS RESMI LENOVO INDONESIA")
    print("=" * 80)

    all_laptops_data = []
    driver = setup_driver()
    laptop_links = get_all_laptop_links_from_lenovo(driver)

    print("\nMenutup WebDriver...");
    driver.quit();
    print("✅ WebDriver telah ditutup.")

    if not laptop_links:
        print("\n❌ Tidak ada tautan produk yang berhasil dikumpulkan. Proses dihentikan.")
    else:
        # --- PERUBAHAN: Siapkan nama file untuk output .txt dan .csv ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nama_file_txt = f"spesifikasi_laptop_{timestamp}.txt"
        nama_file_csv = f"lenovo_all_laptops_{timestamp}.csv"

        print(f"\n🕵️  Memulai pengambilan detail untuk {len(laptop_links)} laptop...")
        print(f"    📄 Hasil copy-paste akan disimpan di: {nama_file_txt}")
        print(f"    📊 Hasil data tabel akan disimpan di: {nama_file_csv}")

        for i, url in enumerate(laptop_links):
            print(f"\n    [PROSES {i + 1}/{len(laptop_links)}] URL: {url}")
            # Logika scraping tetap sama
            laptop_data = scrape_lenovo_laptop_details(url)  # Menggunakan versi ringkas tanpa retry

            if laptop_data:
                print(f"        👍 [BERHASIL] Data untuk '{laptop_data.get('Product_Name', 'N/A')}' berhasil diambil.")
                all_laptops_data.append(laptop_data)  # Tetap kumpulkan data untuk CSV

                # --- PERUBAHAN: Tulis data ke file .txt dengan format rapi ---
                try:
                    with open(nama_file_txt, 'a', encoding='utf-8') as f:
                        f.write("==================================================\n")
                        f.write(f"Produk: {laptop_data.get('Product_Name', 'N/A')}\n")
                        f.write(f"Harga: {laptop_data.get('Price', 'N/A')}\n")
                        f.write(f"URL: {laptop_data.get('Product_URL', 'N/A')}\n")
                        f.write("--------------------------------------------------\n")

                        # Tulis sisa spesifikasi
                        for key, value in laptop_data.items():
                            if key not in ['Product_Name', 'Price', 'Product_URL']:
                                f.write(f"{key}: {value}\n")
                        f.write("==================================================\n\n")
                except Exception as e:
                    print(f"        ⚠️ Gagal menulis ke file teks: {e}")
            else:
                print(f"        ❌ Gagal mengambil data untuk URL ini.")

            time.sleep(random.uniform(1, 3))  # Jeda singkat antar request

        # --- Penyimpanan ke CSV (logika ini tidak berubah) ---
        print("\n" + "-" * 60)
        print("📦 Menyimpan data tabel ke file CSV...")
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