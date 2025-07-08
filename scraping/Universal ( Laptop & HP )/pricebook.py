import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver():
    """Menyiapkan driver Chrome dengan mode headless dan opsi lainnya."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrape_detail_page(driver):
    """Fungsi untuk scrape data dari halaman detail produk."""
    wait = WebDriverWait(driver, 15)

    # 1. Ambil Nama Produk
    try:
        name = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.page-title__title"))).text
    except (NoSuchElementException, TimeoutException):
        name = "N/A"

    # 2. Ambil Harga
    try:
        price = driver.find_element(By.CSS_SELECTOR, "div.pr-price-item__price").text
    except NoSuchElementException:
        price = "N/A"

    # 3. Ambil Spesifikasi
    try:
        spec_container = driver.find_element(By.ID, "spec")
        spec_rows = spec_container.find_elements(By.TAG_NAME, "tr")
        spesifikasi = "\n".join([row.text.replace('\n', ': ') for row in spec_rows])
    except NoSuchElementException:
        spesifikasi = "N/A"

    # 4. Ambil Deskripsi
    try:
        try:
            read_more_button = driver.find_element(By.CSS_SELECTOR, "button.read-more__button")
            driver.execute_script("arguments[0].click();", read_more_button)
            time.sleep(1)
        except NoSuchElementException:
            pass

        deskripsi = driver.find_element(By.CSS_SELECTOR, "div.read-more__content").text
    except NoSuchElementException:
        deskripsi = "N/A"

    return {
        "Nama Produk": name,
        "Harga": price,
        "Link Produk": driver.current_url,
        "Spesifikasi": spesifikasi,
        "Deskripsi": deskripsi.strip()
    }


def scrape_pricebook_interactive():
    """Fungsi utama untuk melakukan scraping dengan metode interaktif."""
    driver = setup_driver()
    base_url = "https://www.pricebook.co.id/smartphone"
    scraped_data = []

    print(f"Mengakses halaman utama: {base_url}")
    driver.get(base_url)

    # Menunggu dan mencoba menutup pop-up cookies
    try:
        wait = WebDriverWait(driver, 10)
        cookie_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Tutup') or contains(text(), 'Setuju')]")))
        cookie_button.click()
        print("Pop-up cookies berhasil ditutup.")
    except (TimeoutException, NoSuchElementException):
        print("Tidak ada pop-up cookies yang ditemukan.")

    # Dapatkan jumlah produk di halaman pertama untuk loop
    try:
        product_cards = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pr-card-default > a"))
        )
        num_products = len(product_cards)
        print(f"Berhasil menemukan {num_products} produk di halaman pertama. Memulai proses scraping...")
    except TimeoutException:
        print("Gagal menemukan kartu produk. Website mungkin berubah atau lambat merespon.")
        driver.quit()
        return

    # Loop berdasarkan jumlah produk yang ditemukan
    for i in range(num_products):
        print(f"\n--- Memproses produk ke-{i + 1} dari {num_products} ---")
        try:
            # PENTING: Cari ulang semua elemen di setiap iterasi untuk menghindari StaleElementReferenceException
            product_cards = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pr-card-default > a"))
            )

            # Pilih kartu produk untuk iterasi saat ini
            card_to_click = product_cards[i]

            # Scroll ke elemen sebelum klik untuk memastikan elemen terlihat
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card_to_click)
            time.sleep(1)  # Beri jeda setelah scroll

            # Klik produk untuk pindah ke halaman detail
            product_name_on_list = card_to_click.find_element(By.CSS_SELECTOR, ".pr-card-default__title").text
            print(f"Mengklik: {product_name_on_list}")
            card_to_click.click()

            # Scrape data dari halaman detail
            product_info = scrape_detail_page(driver)
            scraped_data.append(product_info)
            print(f"-> Data untuk '{product_info['Nama Produk']}' berhasil diambil.")

            # Kembali ke halaman list
            print("Kembali ke halaman daftar produk...")
            driver.back()

            # PENTING: Tunggu hingga halaman list dimuat ulang sepenuhnya
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pr-card-default > a"))
            )
            print("Halaman daftar produk berhasil dimuat ulang.")

        except (StaleElementReferenceException, IndexError):
            print("Error: Elemen menjadi 'stale'. Mencoba lagi pada iterasi berikutnya.")
            # Muat ulang halaman untuk me-refresh semua elemen jika terjadi error serius
            driver.refresh()
            continue
        except Exception as e:
            print(f"Terjadi error pada produk ke-{i + 1}: {e}")
            print("Mencoba kembali ke halaman utama untuk melanjutkan.")
            driver.get(base_url)  # Kembali ke halaman utama jika terjadi error tak terduga
            continue

    driver.quit()

    # Simpan data ke CSV
    if scraped_data:
        df = pd.DataFrame(scraped_data)
        df.to_csv("pricebook_smartphone_detailed.csv", index=False, encoding='utf-8-sig')
        print("\nScraping selesai! Data telah disimpan ke file 'pricebook_smartphone_detailed.csv'")
    else:
        print("\nTidak ada data yang berhasil diambil.")


if __name__ == "__main__":
    scrape_pricebook_interactive()