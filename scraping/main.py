import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from urllib.parse import urlparse, parse_qs
import time
import pandas as pd

print("🚀 Memulai proses scraping tingkat lanjut...")

# === SETUP CHROME DALAM MODE HEADLESS ===
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36") # Menambahkan User-Agent

# Inisialisasi browser dengan opsi headless
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10) # Menambahkan explicit wait untuk stabilitas

# Buka halaman awal
start_url = "https://www.hp.com/id-id/shop/laptops-tablets.html"
driver.get(start_url)
time.sleep(3)

# Deteksi jumlah halaman terakhir
try:
    last_page_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.Last_list-page a")))
    last_page_url = last_page_elem.get_attribute("href")
    parsed_url = urlparse(last_page_url)
    last_page = int(parse_qs(parsed_url.query)['p'][0])
    print(f"🔢 Halaman terakhir terdeteksi: {last_page}")
except TimeoutException:
    last_page = 1
    print("⚠️ Tidak bisa mendeteksi halaman terakhir, default ke 1")

produk_list = []
item_counter = 1

# Loop melalui semua halaman daftar produk
for page_num in range(1, last_page + 1):
    list_page_url = f"https://www.hp.com/id-id/shop/laptops-tablets.html?p={page_num}"
    print(f"\n🔄 Mengakses Halaman Daftar Produk #{page_num}: {list_page_url}")
    driver.get(list_page_url)

    # TAHAP 1: Kumpulkan semua tautan produk di halaman saat ini
    try:
        # Tunggu hingga item produk muncul
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.item.product a.product-item-link")))
        product_links_elements = driver.find_elements(By.CSS_SELECTOR, "li.item.product a.product-item-link")
        product_links = [elem.get_attribute("href") for elem in product_links_elements]
        print(f"    🔗 Ditemukan {len(product_links)} tautan produk di halaman ini.")
    except TimeoutException:
        print(f"    ⚠️ Tidak ditemukan produk di halaman {page_num}. Melanjutkan...")
        continue

    # TAHAP 2: Kunjungi setiap tautan untuk mengambil data detail
    for url in product_links:
        print(f"    🔎 Scraping data dari: {url}")
        try:
            driver.get(url)
            # Beri waktu halaman detail untuk memuat sepenuhnya
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page-title")))
        except TimeoutException:
            print("    ❌ Gagal memuat halaman detail produk. Melanjutkan ke produk berikutnya.")
            continue

        # --- Mulai mengambil data detail ---
        try:
            product_name = driver.find_element(By.CSS_SELECTOR, "h1.page-title").text.strip()
        except NoSuchElementException:
            product_name = "N/A"

        try:
            price_element = driver.find_element(By.CSS_SELECTOR, "span.price-wrapper[data-price-amount]")
            price = price_element.get_attribute("data-price-amount")
        except NoSuchElementException:
            price = "N/A"

        try:
            sku = driver.find_element(By.CSS_SELECTOR, ".product-info-sku .value").text.strip()
        except NoSuchElementException:
            sku = "N/A"

        try:
            rating = driver.find_element(By.CSS_SELECTOR, ".bv_averageRating_component_container .bv_text").get_attribute("textContent").strip()
        except NoSuchElementException:
            rating = "N/A"

        try:
            total_reviews = driver.find_element(By.CSS_SELECTOR, ".bv_numReviews_component_container .bv_text").get_attribute("textContent").strip().replace("(", "").replace(")", "")
        except NoSuchElementException:
            total_reviews = "N/A"

        try:
            description_elements = driver.find_elements(By.CSS_SELECTOR, ".product.attribute.description .value p")
            description = "\n".join([p.text for p in description_elements if p.text]).strip()
        except NoSuchElementException:
            description = "N/A"
            
        try:
            # Mengambil semua baris spesifikasi
            spec_rows = driver.find_elements(By.CSS_SELECTOR, "#specifications .spectable-container .spec-row")
            specs_list = []
            for row in spec_rows:
                try:
                    title = row.find_element(By.CSS_SELECTOR, ".spec-title").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, ".spec-value").text.strip()
                    specs_list.append(f"{title}: {value}")
                except NoSuchElementException:
                    continue # Lewati jika baris tidak lengkap
            specifications = " | ".join(specs_list) # Gabungkan dengan pemisah '|'
        except NoSuchElementException:
            specifications = "N/A"

        produk_list.append({
            "No": item_counter,
            "Product Name": product_name,
            "SKU": sku,
            "Price (IDR)": price,
            "Rating": rating,
            "Total Reviews": total_reviews,
            "Description": description,
            "Specifications": specifications,
            "Product URL": url
        })
        item_counter += 1

print("\n" + "="*60)

# Simpan ke file CSV
df = pd.DataFrame(produk_list)
df.to_csv("daftar_laptop_hp_lengkap.csv", index=False, encoding="utf-8-sig", sep=";")
print("\n✅ Data lengkap berhasil disimpan ke 'daftar_laptop_hp_lengkap.csv'")

# Tutup browser
driver.quit()
print("🎉 Proses selesai. Browser telah ditutup.")