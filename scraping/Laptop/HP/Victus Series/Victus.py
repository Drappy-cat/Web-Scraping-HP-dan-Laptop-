import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium_stealth import stealth
import time
import re
from datetime import datetime
import random

# ==============================================================================
# KONFIGURASI
# ==============================================================================
CONFIG = {
    'start_url': "https://www.hp.com/id-id/shop/laptops-tablets/personal-laptops/victus-laptops.html",
    'max_retries': 3,
    'retry_delay_seconds': 5,
    'wait_timeout': 30
}


# ==============================================================================
# FUNGSI-FUNGSI
# ==============================================================================

def setup_driver():
    """Menginisialisasi Selenium WebDriver dengan mode Stealth untuk menghindari deteksi."""
    print("🔧 Inisialisasi WebDriver dengan mode Stealth (Anti-Bot)...")
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # Bisa diaktifkan jika tidak ingin melihat browser
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    return driver


def get_all_product_links(driver, start_url):
    """
    Membuka halaman kategori, menavigasi semua halaman, dan mengumpulkan semua tautan produk.
    Ini mengadopsi logika dari kode dasar yang Anda berikan.
    """
    all_links = []
    driver.get(start_url)
    print(f"🌐 Membuka halaman awal: {start_url}")
    time.sleep(3)

    # Menangani cookie jika ada
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-accept-btn-handler")))
        cookie_button.click()
        print("🍪 Tombol cookie diterima.")
        time.sleep(2)
    except TimeoutException:
        print("👍 Tidak ada popup cookie yang ditemukan.")

    current_page = 1
    while True:
        print(f"\n📄 Memindai Halaman {current_page} untuk mengumpulkan tautan...")

        # Tunggu hingga kontainer produk dimuat
        try:
            WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol.product-items"))
            )
        except TimeoutException:
            print(f"❌ Gagal memuat kontainer produk di halaman {current_page}. Menghentikan proses.")
            break

        # Ambil semua tautan dari item produk di halaman saat ini
        product_elements = driver.find_elements(By.CSS_SELECTOR, "li.product-item a.product-item-link")
        page_links = [elem.get_attribute("href") for elem in product_elements]
        if page_links:
            all_links.extend(page_links)
            print(f"    🔗 Berhasil mengumpulkan {len(page_links)} tautan dari halaman ini.")
        else:
            print("    ⚠️ Tidak ada tautan produk ditemukan di halaman ini.")

        # Cari tombol 'Berikutnya' dan klik jika ada dan aktif
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.action.next[title=Berikutnya]")
            # Periksa apakah tombol 'Berikutnya' dinonaktifkan (mencapai halaman terakhir)
            if 'disabled' in next_button.get_attribute('class'):
                print("\n✅ Mencapai halaman terakhir (tombol 'Berikutnya' nonaktif).")
                break

            # Menggunakan klik JavaScript untuk keandalan
            driver.execute_script("arguments[0].click();", next_button)
            print("    ➡️ Mengklik tombol 'Berikutnya'...")
            current_page += 1
            time.sleep(random.uniform(4, 6))  # Jeda lebih lama untuk memuat halaman baru
        except NoSuchElementException:
            print("\n✅ Tidak ada tombol 'Berikutnya'. Pengumpulan tautan selesai.")
            break

    unique_links = list(set(all_links))
    print(f"\n📊 Pengumpulan tautan selesai. Ditemukan total {len(unique_links)} tautan produk unik.")
    return unique_links


def scrape_product_details(driver, url):
    """
    Mengunjungi URL produk, melakukan scroll manusiawi, mengklik tombol,
    dan mengambil detailnya dengan mekanisme retry.
    """
    for attempt in range(CONFIG['max_retries']):
        try:
            driver.get(url)
            WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-ui-id='page-title-wrapper']"))
            )

            print("    🔄 Mensimulasikan scroll manusiawi (menekan Page Down)...")
            body = driver.find_element(By.TAG_NAME, 'body')
            for _ in range(random.randint(5, 8)):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.uniform(0.5, 1.0))
            print("    ✅ Halaman telah di-scroll.")

            product_data = {"URL": url}

            print("    🔍 Mencari tombol 'Pelajari Lebih Lanjut Spesifikasi'...")
            learn_more_button = WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[span[contains(text(), 'Pelajari Lebih Lanjut Spesifikasi')]]"))
            )

            print("    🖱️ Tombol ditemukan. Mensimulasikan gerakan mouse dan klik...")
            actions = ActionChains(driver)
            actions.move_to_element(learn_more_button).pause(1).click().perform()
            print("    👍 Berhasil klik 'Pelajari Lebih Lanjut Spesifikasi'.")

            print("    ⏳ Menunggu tabel spesifikasi untuk muncul...")
            WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.additional-attributes-wrapper"))
            )
            print("    ✍️ Ambil data dari tabel spesifikasi lengkap...")

            product_data["Nama Produk"] = driver.find_element(By.CSS_SELECTOR,
                                                              "h1[data-ui-id='page-title-wrapper']").text.strip()
            try:
                price_text = driver.find_element(By.CSS_SELECTOR, "span.price-wrapper span.price").text
                product_data["Harga"] = re.sub(r'[^\d]', '', price_text)
            except NoSuchElementException:
                product_data["Harga"] = "N/A"

            spec_rows = driver.find_elements(By.CSS_SELECTOR, "table.additional-attributes tbody tr")
            for row in spec_rows:
                try:
                    spec_name = row.find_element(By.CSS_SELECTOR, "th.col.label").text.strip()
                    spec_value = row.find_element(By.CSS_SELECTOR, "td.col.data").text.strip()
                    if spec_name and spec_value:
                        product_data[spec_name] = spec_value
                except NoSuchElementException:
                    continue

            return product_data

        except Exception as e:
            error_line = str(e).split('\n')[0]
            print(
                f"    ⚠️ [Percobaan {attempt + 1}/{CONFIG['max_retries']}] Gagal. Error: {type(e).__name__} - {error_line}")
            if attempt < CONFIG['max_retries'] - 1:
                print(f"    ⏳ Mencoba lagi dalam {CONFIG['retry_delay_seconds']} detik...")
                time.sleep(CONFIG['retry_delay_seconds'])
            else:
                print(
                    f"    ❌ [GAGAL TOTAL] Gagal mengambil data untuk URL setelah {CONFIG['max_retries']} percobaan: {url}")
                return None


# ==============================================================================
# PROSES UTAMA
# ==============================================================================
if __name__ == '__main__':
    driver = setup_driver()
    all_laptops_data = []

    print("\n" + "=" * 80)
    print("🚀 MEMULAI PROSES SCRAPING (PENGEMBANGAN DARI KODE DASAR)")
    print("=" * 80)

    # Langkah 1: Kumpulkan semua link dari semua halaman
    product_links = get_all_product_links(driver, CONFIG['start_url'])

    if not product_links:
        print("❌ Tidak ada produk yang bisa di-scrape. Program berhenti.")
    else:
        # Langkah 2: Kunjungi setiap link untuk scraping detail
        print(f"\n🕵️  Memulai pengambilan detail untuk {len(product_links)} produk...")
        for i, url in enumerate(product_links):
            print(f"\n--- [PROSES PRODUK {i + 1}/{len(product_links)}] URL: {url} ---")

            laptop_details = scrape_product_details(driver, url)

            if laptop_details:
                all_laptops_data.append(laptop_details)
                print(f"    ✅ [SUKSES] Data untuk '{laptop_details.get('Nama Produk', 'N/A')}' berhasil diambil.")
            else:
                print(f"    ❌ [GAGAL] Melewati produk ini setelah beberapa kali percobaan.")

            delay = random.uniform(3, 6)
            print(f"    ⏳ Jeda {delay:.2f} detik sebelum lanjut ke produk berikutnya...")
            time.sleep(delay)

        # Langkah 3: Simpan semua data yang terkumpul ke CSV
        print("\n" + "-" * 60)
        print("📦 Proses scraping selesai. Menyimpan data ke file CSV...")

        if not all_laptops_data:
            print("    ⚠️ Tidak ada data valid yang berhasil dikumpulkan. Tidak ada file CSV yang dibuat.")
        else:
            df = pd.DataFrame(all_laptops_data)

            first_cols = ['Nama Produk', 'Harga', 'URL']
            existing_first_cols = [col for col in first_cols if col in df.columns]
            other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
            final_columns = existing_first_cols + other_cols

            df = df.reindex(columns=final_columns).fillna("N/A")
            df.insert(0, 'No', range(1, 1 + len(df)))

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nama_file_output = f"hp_victus_laptops_lengkap_{timestamp}.csv"

            df.to_csv(nama_file_output, index=False, encoding="utf-8-sig", sep=";")

            print(f"    ✅ Data berhasil disimpan ke: '{nama_file_output}'")
            print(f"    - Total Produk Disimpan: {len(df)}")
        print("-" * 60)

    driver.quit()
    print("\n🎉 SELURUH PROSES SCRAPING TELAH SELESAI 🎉")
