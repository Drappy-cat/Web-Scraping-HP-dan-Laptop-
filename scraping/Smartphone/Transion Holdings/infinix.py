import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import re
from datetime import datetime


def setup_driver():
    """Menginisialisasi dan mengkonfigurasi Selenium WebDriver."""
    print("🔧 Menyiapkan Selenium WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    return driver


def get_phone_links_from_page(driver, page_url):
    """Mengambil semua link detail perangkat dari satu halaman hasil pencarian."""
    driver.get(page_url)
    wait = WebDriverWait(driver, 10)
    try:
        # Menambahkan penanganan cookie untuk stabilitas
        try:
            cookie_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            print("    - Banner cookie ditemukan, mengklik 'Accept'...")
            cookie_button.click()
            time.sleep(1)
        except TimeoutException:
            print("    - Banner cookie tidak ditemukan, melanjutkan proses.")
            pass  # Lanjut jika banner tidak ada

        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.makers > ul > li > a")))
        product_links_elements = driver.find_elements(By.CSS_SELECTOR, "div.makers > ul > li > a")
        return [elem.get_attribute("href") for elem in product_links_elements]
    except TimeoutException:
        return []


def is_smartphone(specs):
    """
    Memvalidasi apakah sebuah perangkat adalah smartphone berdasarkan spesifikasinya.
    Mengembalikan True jika smartphone, False jika bukan.
    """
    os_spec = specs.get('Platform_OS', '').lower()
    network_spec = specs.get('Network_Technology', '').lower()

    if 'android' not in os_spec and 'ios' not in os_spec:
        return False
    if 'wear os' in os_spec or 'watchos' in os_spec or 'tizen' in os_spec:
        return False
    if 'gsm' not in network_spec:
        return False
    return True


def scrape_device_details(driver, url):
    """
    Mengambil semua data detail dari satu URL perangkat.
    """
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.specs-phone-name-title")))
    device_data = {"Product URL": url}
    spec_columns = set()
    device_data["Phone Name"] = driver.find_element(By.CSS_SELECTOR, "h1.specs-phone-name-title").text.strip()
    try:
        price_button = driver.find_element(By.CSS_SELECTOR, 'button[data-spec="price"]')
        price_html = price_button.get_attribute('innerHTML')
        match = re.search(r'About\s*([\d,]+\s*\w+)', price_html, re.IGNORECASE)
        device_data["Estimated_Price"] = match.group(1) if match else "N/A"
    except NoSuchElementException:
        device_data["Estimated_Price"] = "N/A"
    spec_columns.add("Estimated_Price")
    try:
        fans_element = driver.find_element(By.CSS_SELECTOR, ".specs-fans > a")
        device_data["Popularity_Fans"] = fans_element.text.strip().split('\n')[0]
    except NoSuchElementException:
        device_data["Popularity_Fans"] = "N/A"
    spec_columns.add("Popularity_Fans")
    spec_tables = driver.find_elements(By.CSS_SELECTOR, "#specs-list table")
    for table in spec_tables:
        try:
            category = table.find_element(By.CSS_SELECTOR, "th").text.strip()
            rows = table.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                try:
                    title = row.find_element(By.CSS_SELECTOR, "td.ttl").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, "td.nfo").text.strip()
                    if title and value:
                        clean_category = re.sub(r'[^A-Za-z0-9_]+', '', category)
                        clean_title = re.sub(r'[^A-Za-z0-9_]+', '', title)
                        column_name = f"{clean_category}_{clean_title}"
                        # Membersihkan data dari baris baru agar rapi di CSV
                        device_data[column_name] = " ".join(value.splitlines())
                        spec_columns.add(column_name)
                except NoSuchElementException:
                    continue
        except NoSuchElementException:
            continue
    return device_data, spec_columns


def main(keyword, num_pages):
    """Fungsi utama untuk mengorkestrasi proses scraping."""
    driver = setup_driver()
    print(f"🚀 Memulai proses scraping untuk '{keyword}' pada {num_pages} halaman dengan FOKUS PADA SMARTPHONE...")

    ponsel_list = []
    all_spec_columns = set()
    item_counter = 1
    scraped_counter = 0
    for page_num in range(1, num_pages + 1):
        list_page_url = f"https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={keyword}&iPage={page_num}"
        print(f"\n🔄 Mengakses Halaman Daftar Perangkat #{page_num}: {list_page_url}")
        product_links = get_phone_links_from_page(driver, list_page_url)
        if not product_links:
            print(f"    ⚠️ Tidak ditemukan perangkat di halaman {page_num}. Mungkin sudah halaman terakhir.")
            break
        print(f"    🔗 Ditemukan {len(product_links)} tautan. Memulai validasi dan scraping...")
        for url in product_links:
            try:
                scraped_counter += 1
                print(f"    [Cek #{scraped_counter}] Memeriksa: {url}")
                device_data, new_columns = scrape_device_details(driver, url)
                if is_smartphone(device_data):
                    print(f"        ✅ VALID: '{device_data['Phone Name']}' adalah smartphone. Menyimpan data...")
                    ponsel_list.append(device_data)
                    all_spec_columns.update(new_columns)
                    item_counter += 1
                else:
                    print(f"        ❌ SKIP: '{device_data['Phone Name']}' bukan smartphone (atau tablet Wi-Fi).")
                time.sleep(0.2)
            except Exception as e:
                print(f"    ❌❌❌ ERROR tak terduga saat scraping {url}: {e}")
                print("    Melanjutkan ke perangkat berikutnya...")
                continue
    print("\n" + "=" * 60)
    print("📊 Proses scraping selesai. Mempersiapkan data untuk disimpan ke CSV...")
    if not ponsel_list:
        print("❌ Tidak ada smartphone yang berhasil di-scrape sesuai kriteria.")
    else:
        # Mengatur urutan kolom agar lebih rapi
        preferred_columns = [
            'Phone Name', 'Product URL', 'Estimated_Price', 'Popularity_Fans',
            'Network_Technology', 'Launch_Announced', 'Launch_Status',
            'Body_Dimensions', 'Body_Weight', 'Display_Type', 'Display_Size',
            'Platform_OS', 'Platform_Chipset', 'Memory_Internal', 'Battery_Type'
        ]
        other_columns = sorted(list(all_spec_columns - set(preferred_columns)))
        final_columns = [col for col in preferred_columns if col in all_spec_columns] + other_columns

        df = pd.DataFrame(ponsel_list)
        df = df.reindex(columns=final_columns)
        df.fillna("N/A", inplace=True)
        df.insert(0, 'No', range(1, 1 + len(df)))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Nama file akan otomatis menggunakan kata kunci yang baru
        nama_file_output = f"gsmarena_smartphones_{keyword}_{timestamp}.csv"

        df.to_csv(nama_file_output, index=False, encoding="utf-8-sig", sep=";")
        print(f"\n✅ Data lengkap berhasil disimpan ke '{nama_file_output}'")
        print(f"    - Total Perangkat Diperiksa: {scraped_counter}")
        print(f"    - Total Smartphone Ditemukan & Disimpan: {len(df)}")
        print(f"    - Total Kolom Spesifikasi Unik Ditemukan: {len(all_spec_columns)}")
    driver.quit()
    print("🎉 Proses selesai. Browser telah ditutup.")


if __name__ == '__main__':
    # --- PERUBAHAN UTAMA DI SINI ---
    # Cukup ubah nilai variabel di bawah ini lalu jalankan script.

    # 1. Tentukan kata kunci pencarian (merek atau model)
    kata_kunci_pencarian = "infinix" # <--- DIUBAH DARI "samsung" MENJADI "infinix"

    # 2. Tentukan berapa banyak halaman hasil pencarian yang ingin di-scrape
    jumlah_halaman_scrape = 3 # Anda bisa sesuaikan jumlah halaman ini

    # Memanggil fungsi utama dengan nilai yang sudah Anda tentukan di atas
    main(kata_kunci_pencarian, jumlah_halaman_scrape)