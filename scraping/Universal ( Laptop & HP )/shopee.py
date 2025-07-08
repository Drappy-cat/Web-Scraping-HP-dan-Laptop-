import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time

print("🚀 Memulai proses scraping Shopee dengan struktur kode Anda...")

# === SETUP CHROME DALAM MODE HEADLESS (Tidak ada perubahan di sini) ===
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)  # Menaikkan waktu tunggu untuk Shopee yang lebih berat

# === PENYESUAIAN: KATA KUNCI & JUMLAH HALAMAN ===
KATA_KUNCI = "laptop hp"
JUMLAH_HALAMAN_SCRAPE = 2  # Tentukan berapa halaman yang ingin di-scrape
print(f"🎯 Target: '{KATA_KUNCI}', Halaman: {JUMLAH_HALAMAN_SCRAPE}")


# === BARU: FUNGSI UNTUK MENUTUP POP-UP ===
def tutup_popup():
    try:
        # Shopee sering menampilkan pop-up saat pertama kali dibuka
        # Kita tunggu tombol tutupnya muncul dan klik
        tombol_tutup_popup = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "shopee-banner-popup-stateful shopee-popup__close-btn"))
        )
        tombol_tutup_popup.click()
        print("    ✅ Pop-up berhasil ditutup.")
    except TimeoutException:
        print("    ℹ️ Tidak ada pop-up terdeteksi atau sudah tertutup.")


# Buka halaman awal pencarian Shopee
start_url = f"https://shopee.co.id/search?keyword={KATA_KUNCI.replace(' ', '%20')}"
driver.get(start_url)

# Panggil fungsi untuk menutup pop-up jika ada
tutup_popup()

produk_list = []
item_counter = 1

# Loop melalui semua halaman daftar produk (logika dipertahankan dari kode Anda)
for page_num in range(JUMLAH_HALAMAN_SCRAPE):
    # PENYESUAIAN: URL halaman Shopee menggunakan index 0
    list_page_url = f"https://shopee.co.id/search?keyword={KATA_KUNCI.replace(' ', '%20')}&page={page_num}"
    print(f"\n🔄 Mengakses Halaman Daftar Produk #{page_num + 1}: {list_page_url}")
    driver.get(list_page_url)
    time.sleep(2)  # Beri waktu sejenak

    # BARU: Lakukan scroll untuk memuat semua produk di halaman
    print("    📜 Melakukan scroll untuk memuat produk...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # TAHAP 1: Kumpulkan semua tautan produk (logika dipertahankan)
    try:
        # PENYESUAIAN: Menggunakan selector CSS untuk link produk di Shopee
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-sqe='link']")))
        product_links_elements = driver.find_elements(By.CSS_SELECTOR, "a[data-sqe='link']")
        # Memastikan link unik dan valid
        product_links = list(dict.fromkeys(
            [elem.get_attribute("href") for elem in product_links_elements if elem.get_attribute("href")]))
        print(f"    🔗 Ditemukan {len(product_links)} tautan produk unik di halaman ini.")
    except TimeoutException:
        print(f"    ⚠️ Tidak ditemukan produk di halaman {page_num + 1}. Melanjutkan...")
        continue

    # TAHAP 2: Kunjungi setiap tautan untuk mengambil data detail (logika dipertahankan)
    for url in product_links:
        print(f"    🔎 Scraping data dari: {url.split('?')[0]}...")  # Membersihkan URL dari parameter
        try:
            driver.get(url)
            # PENYESUAIAN: Menunggu elemen kunci di halaman detail produk Shopee
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._3_N7-6")))  # Menunggu harga muncul
        except TimeoutException:
            print("    ❌ Gagal memuat halaman detail produk. Melanjutkan ke produk berikutnya.")
            continue

        # --- Mulai mengambil data detail (semua selector disesuaikan untuk Shopee) ---
        try:
            product_name = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div._44qnta > span"))).text.strip()
        except TimeoutException:
            product_name = "N/A"

        try:
            price = driver.find_element(By.CSS_SELECTOR, "div._3_N7-6").text.strip()
        except NoSuchElementException:
            price = "N/A"

        try:
            rating = driver.find_element(By.CSS_SELECTOR, "div._2z65d0").text.strip()
        except NoSuchElementException:
            rating = "N/A"

        try:
            total_reviews_text = driver.find_element(By.xpath,
                                                     "//div[text()='penilaian']/following-sibling::div").text.strip()
            total_sold_text = driver.find_element(By.xpath,
                                                  "//div[text()='terjual']/following-sibling::div").text.strip()
        except NoSuchElementException:
            total_reviews_text = "N/A"
            total_sold_text = "N/A"

        try:
            # Mengambil deskripsi dari container spesifik
            description_container = driver.find_element(By.CSS_SELECTOR, "p.ir202i")
            description = description_container.text.strip()
        except NoSuchElementException:
            description = "N/A"

        try:
            # PENYESUAIAN: Logika pengambilan spesifikasi untuk Shopee
            spec_rows = driver.find_elements(By.CSS_SELECTOR,
                                             "div.product-detail-specifications__body > div.shopee-product-specifications__row")
            specs_list = []
            for row in spec_rows:
                try:
                    title = row.find_element(By.CSS_SELECTOR, ".shopee-product-specifications__label").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, ".shopee-product-specifications__value").text.strip()
                    specs_list.append(f"{title}: {value}")
                except NoSuchElementException:
                    continue
            specifications = " | ".join(specs_list)
        except NoSuchElementException:
            specifications = "N/A"

        produk_list.append({
            "No": item_counter,
            "Product Name": product_name,
            "Price (string)": price,  # Harga di Shopee bisa berupa rentang, jadi disimpan sebagai string
            "Rating": rating,
            "Total Reviews": total_reviews_text,
            "Total Sold": total_sold_text,
            "Description": description,
            "Specifications": specifications,
            "Product URL": url
        })
        item_counter += 1
        time.sleep(1)  # Jeda sopan antar produk

print("\n" + "=" * 60)

# Simpan ke file CSV (logika dipertahankan)
df = pd.DataFrame(produk_list)
df.to_csv("daftar_laptop_shopee_lengkap.csv", index=False, encoding="utf-8-sig", sep=";")
print("\n✅ Data lengkap berhasil disimpan ke 'daftar_laptop_shopee_lengkap.csv'")

# Tutup browser (logika dipertahankan)
driver.quit()
print("🎉 Proses selesai. Browser telah ditutup.")