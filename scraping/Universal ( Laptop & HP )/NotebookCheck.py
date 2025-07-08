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
from datetime import datetime
import random
from urllib.parse import quote

# ==============================================================================
# KONFIGURASI
# ==============================================================================
CONFIG = {
    # URL dasar untuk pencarian. Format: {search_term} akan diganti
    'search_url_template': "https://www.notebookcheck.net/index.php?id=129&search={search_term}&model=1&company=1&show=1",

    # Definisikan brand dan kategori yang ingin di-scrape
    'brands_and_categories': {
        "ASUS": [
            "Gaming",
            "ZenBook",  # Contoh untuk Ultrabook
            "VivoBook",  # Contoh untuk Entry-level/Mainstream
            "ProArt"  # Contoh untuk Content Creation
        ],
        # Anda bisa menambahkan brand lain di sini, contoh:
        # "Dell": ["XPS", "Alienware"],
        # "Lenovo": ["ThinkPad", "Legion"]
    },

    'max_pages_per_category': 3,  # Batasi jumlah halaman per kategori
    'max_retries': 3,
    'retry_delay_seconds': 5,
    'wait_timeout': 20
}


# ==============================================================================
# FUNGSI-FUNGSI
# ==============================================================================

def setup_driver():
    """Menginisialisasi Selenium WebDriver dengan mode Stealth dan Headless."""
    print("🔧 Inisialisasi WebDriver dengan mode Stealth (Headless)...")
    options = webdriver.ChromeOptions()
    # --- PERUBAHAN: Mengaktifkan mode headless ---
    options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")  # Penting untuk headless
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


def get_all_review_links(driver, search_url, max_pages):
    """Membuka halaman pencarian, menavigasi halaman, dan mengumpulkan tautan ulasan."""
    all_links = []
    driver.get(search_url)
    print(f"🌐 Membuka halaman pencarian: {search_url}")
    time.sleep(3)

    # Menangani cookie jika ada
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ACCEPT ALL')]")))
        cookie_button.click()
        print("🍪 Tombol cookie diterima.")
        time.sleep(2)
    except TimeoutException:
        print("👍 Tidak ada popup cookie yang ditemukan.")

    for page_num in range(1, max_pages + 1):
        print(f"\n📄 Memindai Halaman {page_num}/{max_pages} untuk mengumpulkan tautan...")

        try:
            WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.presence_of_element_located((By.ID, "news_list"))
            )
        except TimeoutException:
            print(f"❌ Gagal memuat kontainer ulasan di halaman {page_num}. Menghentikan proses.")
            break

        review_elements = driver.find_elements(By.CSS_SELECTOR, "article.news_list_item > a")
        page_links = [elem.get_attribute("href") for elem in review_elements]
        if page_links:
            all_links.extend(page_links)
            print(f"    🔗 Berhasil mengumpulkan {len(page_links)} tautan dari halaman ini.")
        else:
            print("    ⚠️ Tidak ada tautan ulasan ditemukan di halaman ini. Mungkin akhir dari hasil pencarian.")
            break

        if page_num == max_pages:
            print(f"\n✅ Telah mencapai batas maksimum {max_pages} halaman untuk di-scrape.")
            break

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.pagenav_next")
            driver.execute_script("arguments[0].scrollIntoView();", next_button)
            time.sleep(1)
            next_button.click()
            print("    ➡️ Mengklik tombol 'next'...")
            time.sleep(random.uniform(3, 5))
        except NoSuchElementException:
            print("\n✅ Tidak ada tombol 'next'. Pengumpulan tautan selesai.")
            break

    unique_links = list(set(all_links))
    print(f"\n📊 Pengumpulan tautan selesai. Ditemukan total {len(unique_links)} tautan ulasan unik.")
    return unique_links


def scrape_review_details(driver, url):
    """Mengunjungi URL ulasan dan mengambil data detailnya."""
    for attempt in range(CONFIG['max_retries']):
        try:
            driver.get(url)
            WebDriverWait(driver, CONFIG['wait_timeout']).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )

            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)

            review_data = {"URL": url}
            review_data["Title"] = driver.find_element(By.TAG_NAME, "h1").text.strip()

            try:
                meta_data = driver.find_element(By.CSS_SELECTOR, "div.news_meta_data").text.strip()
                review_data["Author & Date"] = meta_data
            except NoSuchElementException:
                review_data["Author & Date"] = "N/A"

            try:
                score = driver.find_element(By.CSS_SELECTOR, "div.score-value").text.strip()
                review_data["Overall Score (%)"] = score
            except NoSuchElementException:
                review_data["Overall Score (%)"] = "N/A"

            print("    ✍️ Mengambil data dari tabel spesifikasi...")
            try:
                spec_rows = driver.find_elements(By.CSS_SELECTOR, "table.specs tr")
                for row in spec_rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            spec_name = cells[0].text.strip().replace(":", "")
                            spec_value = cells[1].text.strip()
                            if spec_name and spec_value:
                                review_data[f"Spec_{spec_name}"] = spec_value
                    except Exception:
                        continue
            except Exception as e:
                print(f"    ⚠️ Gagal mengambil tabel spesifikasi: {e}")

            return review_data

        except Exception as e:
            error_line = str(e).split('\n')[0]
            print(
                f"    ⚠️ [Percobaan {attempt + 1}/{CONFIG['max_retries']}] Gagal. Error: {type(e).__name__} - {error_line}")
            if attempt < CONFIG['max_retries'] - 1:
                print(f"    ⏳ Mencoba lagi dalam {CONFIG['retry_delay_seconds']} detik...")
                time.sleep(CONFIG['retry_delay_seconds'])
            else:
                print(f"    ❌ [GAGAL TOTAL] Gagal mengambil data untuk URL: {url}")
                return None


# ==============================================================================
# PROSES UTAMA
# ==============================================================================
if __name__ == '__main__':
    driver = setup_driver()

    # --- PERUBAHAN: Loop melalui setiap brand dan kategori ---
    for brand, categories in CONFIG['brands_and_categories'].items():
        for category in categories:
            all_reviews_data = []
            search_term = f"{brand} {category}"
            # Membuat URL pencarian yang valid dengan mengganti spasi menjadi '+'
            search_url = CONFIG['search_url_template'].format(search_term=quote(search_term))

            print("\n" + "=" * 80)
            print(f"🚀 MEMULAI PROSES SCRAPING UNTUK: {brand.upper()} - {category.upper()}")
            print("=" * 80)

            review_links = get_all_review_links(driver, search_url, CONFIG['max_pages_per_category'])

            if not review_links:
                print(f"❌ Tidak ada ulasan ditemukan untuk '{search_term}'. Lanjut ke kategori berikutnya.")
                continue

            print(f"\n🕵️  Memulai pengambilan detail untuk {len(review_links)} ulasan...")
            for i, url in enumerate(review_links):
                print(f"\n--- [PROSES ULASAN {i + 1}/{len(review_links)}] URL: {url} ---")

                review_details = scrape_review_details(driver, url)

                if review_details:
                    # Menambahkan Brand dan Kategori ke data untuk identifikasi
                    review_details['Brand'] = brand
                    review_details['Category'] = category
                    all_reviews_data.append(review_details)
                    print(f"    ✅ [SUKSES] Data untuk '{review_details.get('Title', 'N/A')}' berhasil diambil.")
                else:
                    print(f"    ❌ [GAGAL] Melewati ulasan ini setelah beberapa kali percobaan.")

                delay = random.uniform(2, 4)
                print(f"    ⏳ Jeda {delay:.2f} detik sebelum lanjut...")
                time.sleep(delay)

            print("\n" + "-" * 60)
            print(f"📦 Proses untuk '{search_term}' selesai. Menyimpan data ke file CSV...")

            if not all_reviews_data:
                print("    ⚠️ Tidak ada data valid yang berhasil dikumpulkan.")
            else:
                df = pd.DataFrame(all_reviews_data)

                first_cols = ['Brand', 'Category', 'Title', 'Overall Score (%)', 'Author & Date', 'URL']
                existing_first_cols = [col for col in first_cols if col in df.columns]
                other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
                final_columns = existing_first_cols + other_cols

                df = df.reindex(columns=final_columns).fillna("N/A")
                df.insert(0, 'No', range(1, 1 + len(df)))

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # --- PERUBAHAN: Nama file dinamis berdasarkan brand dan kategori ---
                safe_brand = brand.replace(' ', '_')
                safe_category = category.replace(' ', '_')
                nama_file_output = f"notebookcheck_{safe_brand}_{safe_category}_{timestamp}.csv"

                df.to_csv(nama_file_output, index=False, encoding="utf-8-sig", sep=";")

                print(f"    ✅ Data berhasil disimpan ke: '{nama_file_output}'")
                print(f"    - Total Ulasan Disimpan: {len(df)}")
            print("-" * 60)

    driver.quit()
    print("\n🎉 SELURUH PROSES SCRAPING TELAH SELESAI 🎉")
