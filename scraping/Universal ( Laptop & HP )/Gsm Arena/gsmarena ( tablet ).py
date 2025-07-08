import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import re
from datetime import datetime
import random

# ==============================================================================
# KONFIGURASI TERPUSAT UNTUK GSMARENA.COM
# ==============================================================================
CONFIG = {
    'base_url': "https://www.gsmarena.com/",
    'search_url_template': "https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={keyword}&iPage={page_num}",
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    },
    'selectors': {
        'product_list': "div.makers > ul > li > a",
        'cookie_button': "#onetrust-accept-btn-handler",
        'phone_name': "h1.specs-phone-name-title",
        'price_button': 'button[data-spec="price"]',
        'popularity_fans': ".specs-fans > a",
        'spec_tables': "#specs-list table",
        'table_category': "th",
        'table_row': "tr",
        'spec_title_cell': "td.ttl",
        'spec_value_cell': "td.nfo",
        'pagination_links': 'div.nav-pages > a'
    },
    'max_retries': 3,
    'retry_delay_seconds': 30
}

# ==============================================================================
# FUNGSI-FUNGSI
# ==============================================================================

def setup_driver():
    print("🔧 Inisialisasi Selenium WebDriver (Headless Mode)...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={CONFIG['headers']['User-Agent']}")
    driver = webdriver.Chrome(options=options)
    return driver

def get_total_pages(driver, keyword):
    print(f"📊 Menghitung total halaman untuk brand '{keyword}'...")
    page_url = CONFIG['search_url_template'].format(keyword=keyword, page_num=1)
    driver.get(page_url)
    try:
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, CONFIG['selectors']['cookie_button'])))
            cookie_button.click()
            time.sleep(1)
        except TimeoutException:
            pass

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CONFIG['selectors']['product_list'])))

        pagination_elements = driver.find_elements(By.CSS_SELECTOR, CONFIG['selectors']['pagination_links'])
        if not pagination_elements:
            print(" ➡️ Hanya ditemukan 1 halaman.")
            return 1

        last_page_href = pagination_elements[-2].get_attribute('href')
        match = re.search(r'iPage=(\d+)', last_page_href)
        if match:
            total_pages = int(match.group(1))
            print(f" ✅ Ditemukan total {total_pages} halaman.")
            return total_pages
        else:
            print(" ⚠️ Tidak dapat menentukan jumlah halaman, diasumsikan 1.")
            return 1
    except TimeoutException:
        print(f" ❌ Tidak ada produk atau halaman tidak dapat dimuat untuk '{keyword}'. Total halaman: 0.")
        return 0

def get_all_device_links(driver, keyword, total_pages):
    all_links = []
    for page_num in range(1, total_pages + 1):
        page_url = CONFIG['search_url_template'].format(keyword=keyword, page_num=page_num)
        print(f"\n [HALAMAN {page_num}/{total_pages}] Mengakses: {page_url}")
        driver.get(page_url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, CONFIG['selectors']['product_list'])))
            product_elements = driver.find_elements(By.CSS_SELECTOR, CONFIG['selectors']['product_list'])

            if not product_elements:
                print(f" ⚠️ Tidak ada perangkat ditemukan di halaman {page_num}. Melanjutkan...")
                continue

            page_links = [elem.get_attribute("href") for elem in product_elements]
            all_links.extend(page_links)
            print(f" 🔗 Berhasil mengumpulkan {len(page_links)} tautan dari halaman ini.")
        except TimeoutException:
            print(f" ❌ Gagal memuat elemen produk di halaman {page_num}. Melewati halaman ini.")
            continue

        time.sleep(random.uniform(1, 3))

    return list(set(all_links))

def scrape_details_with_requests(url):
    try:
        response = requests.get(url, headers=CONFIG['headers'])
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        device_data = {"Product URL": url}
        device_data["Device Name"] = soup.select_one(CONFIG['selectors']['phone_name']).text.strip()

        price_button = soup.select_one(CONFIG['selectors']['price_button'])
        if price_button:
            match = re.search(r'About\s*([\d,.]+\s*\w+)', price_button.decode_contents(), re.IGNORECASE)
            device_data["Estimated_Price"] = match.group(1).strip() if match else "N/A"
        else:
            device_data["Estimated_Price"] = "N/A"

        fans_element = soup.select_one(CONFIG['selectors']['popularity_fans'])
        device_data["Popularity_Fans"] = fans_element.text.strip().split('\n')[0] if fans_element else "N/A"

        spec_tables = soup.select(CONFIG['selectors']['spec_tables'])
        for table in spec_tables:
            category = table.select_one(CONFIG['selectors']['table_category']).text.strip()
            rows = table.select(CONFIG['selectors']['table_row'])
            for row in rows:
                title_tag = row.select_one(CONFIG['selectors']['spec_title_cell'])
                value_tag = row.select_one(CONFIG['selectors']['spec_value_cell'])
                if title_tag and value_tag:
                    title = title_tag.text.strip()
                    value = value_tag.text.strip()
                    clean_category = re.sub(r'[^A-Za-z0-9_]+', '', category)
                    clean_title = re.sub(r'[^A-Za-z0-9_]+', '', title)
                    column_name = f"{clean_category}_{clean_title}"
                    device_data[column_name] = value
        return device_data
    except:
        return None

def is_tablet(specs, min_screen_size_inches=7.0):
    if not specs:
        return False

    os_spec = specs.get('Platform_OS', '').lower()
    if 'wear os' in os_spec or 'watchos' in os_spec or 'tizen' in os_spec:
        return False

    display_size_str = specs.get('Display_Size', '')
    if not display_size_str:
        return False

    match = re.search(r'([\d.]+)\s*inches', display_size_str)
    if match:
        try:
            screen_size = float(match.group(1))
            return screen_size >= min_screen_size_inches
        except:
            return False
    return False

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == '__main__':
    brands_to_scrape = ["Samsung", "Apple", "Xiaomi", "Lenovo", "Huawei"]
    driver = setup_driver()

    total_scraped_count = 0
    total_valid_tablets = 0

    for brand in brands_to_scrape:
        print("\n" + "=" * 80)
        print(f"🚀 MEMULAI PROSES SCRAPING TABLET UNTUK BRAND: {brand.upper()}")
        print("=" * 80)

        brand_specific_list = []
        total_pages = get_total_pages(driver, brand)
        if total_pages == 0:
            continue

        device_links = get_all_device_links(driver, brand, total_pages)
        if not device_links:
            continue

        print(f"\n✅ [PENGUMPULAN TAUTAN SELESAI] Ditemukan {len(device_links)} link unik untuk '{brand}'.")

        for i, url in enumerate(device_links):
            total_scraped_count += 1
            print(f"\n [PROSES {i + 1}/{len(device_links)}] URL: {url}")

            device_data = None
            for attempt in range(CONFIG['max_retries']):
                scraped_data = scrape_details_with_requests(url)
                if scraped_data:
                    device_data = scraped_data
                    break
                else:
                    print(f" [GAGAL] Percobaan {attempt + 1}/{CONFIG['max_retries']} gagal.")
                    if attempt < CONFIG['max_retries'] - 1:
                        print(f" ⏳ Mencoba lagi dalam {CONFIG['retry_delay_seconds']} detik...")
                        time.sleep(CONFIG['retry_delay_seconds'])

            if not device_data:
                continue

            if is_tablet(device_data):
                device_data['Brand'] = brand
                print(f" 👍 [VALID] '{device_data.get('Device Name', 'N/A')}' adalah tablet. Data ditambahkan.")
                brand_specific_list.append(device_data)
                total_valid_tablets += 1
            else:
                print(f" 🚫 [SKIP] '{device_data.get('Device Name', 'N/A')}' bukan tablet.")

            time.sleep(random.uniform(5, 15))

        print("\n" + "-" * 60)
        print(f"📦 Proses untuk brand '{brand}' selesai. Menyimpan data ke file CSV...")

        if brand_specific_list:
            df = pd.DataFrame(brand_specific_list)
            first_cols = ['Brand', 'Device Name', 'Product URL', 'Estimated_Price', 'Popularity_Fans']
            existing_first_cols = [col for col in first_cols if col in df.columns]
            other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
            final_columns = existing_first_cols + other_cols

            df = df.reindex(columns=final_columns).fillna("N/A")
            df.insert(0, 'No', range(1, 1 + len(df)))

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nama_file_output = f"gsmarena_{brand.replace(' ', '_')}_tablet_{timestamp}.csv"
            df.to_csv(nama_file_output, index=False, encoding="utf-8-sig", sep=";")

            print(f" ✅ Data disimpan ke: '{nama_file_output}' - Total Tablet: {len(df)}")
        else:
            print(f" ⚠️ Tidak ada tablet valid yang ditemukan untuk brand '{brand}'.")

    driver.quit()

    print("\n\n" + "=" * 80)
    print("🎉 SELURUH PROSES SCRAPING TABLET TELAH SELESAI 🎉")
    print("=" * 80)
    print("\nREKAPITULASI TOTAL:")
    print(f" - Total Brand Diproses: {len(brands_to_scrape)}")
    print(f" - Total Tautan Diperiksa: {total_scraped_count}")
    print(f" - Total Tablet Valid Disimpan: {total_valid_tablets}")
    print("\nSilakan periksa file-file CSV yang telah dibuat di folder Anda.")
