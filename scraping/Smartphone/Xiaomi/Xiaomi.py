import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
import time

# === SETUP CHROME DALAM MODE HEADLESS ===
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

# Inisialisasi browser dengan opsi headless
driver = webdriver.Chrome(options=options)

# --- PERUBAHAN 1: MENGGANTI URL TARGET ---
start_url = "https://www.mi.co.id/id/product-list/phone/poco/"
driver.get(start_url)
print(f"🔗 Membuka halaman: {start_url}")
time.sleep(5) # Beri waktu lebih agar halaman & javascript-nya termuat penuh

# --- PERUBAHAN 2: LOGIKA BARU UNTUK TOMBOL "MUAT LEBIH BANYAK" ---
# Logika lama untuk deteksi halaman terakhir dihapus
print("🔄 Mencari dan mengklik tombol 'Muat Lebih Banyak'...")
while True:
    try:
        # Cari tombolnya
        load_more_button = driver.find_element(By.CSS_SELECTOR, ".load-more-btn")
        
        # Gulir ke tombol agar terlihat dan bisa diklik
        driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
        time.sleep(1) # Jeda singkat setelah scroll
        
        # Klik tombol
        load_more_button.click()
        print("    ✅ Tombol 'Muat Lebih Banyak' diklik. Menunggu produk baru...")
        time.sleep(3) # Tunggu produk baru dimuat
    except NoSuchElementException:
        # Jika tombol tidak lagi ditemukan, berarti semua produk sudah dimuat
        print("👍 Semua produk telah dimuat.")
        break
    except ElementClickInterceptedException:
        # Kadang tombol tertutup elemen lain (misal: notif cookie)
        print("⚠️ Tombol tertutup elemen lain, proses berhenti. Semua produk yang terlihat akan diambil.")
        break
    except Exception as e:
        print(f"❌ Terjadi error tak terduga: {e}")
        break

print("\n scraping data produk...")
produk_list = []

# --- PERUBAHAN 3: MENGGUNAKAN SELECTOR CSS BARU ---
# Selector lama diganti dengan yang sesuai untuk situs Xiaomi
items = driver.find_elements(By.CSS_SELECTOR, "div.list-item")

for i, item in enumerate(items, 1):
    try:
        # Selector untuk nama produk diubah
        product_name = item.find_element(By.CSS_SELECTOR, "h3.title").text.strip()
    except:
        product_name = "Product is not found"

    # --- PERUBAHAN 4: HAPUS BAGIAN RATING & REVIEW ---
    # Rating & Review tidak ada di halaman ini, jadi kita hapus
    
    try:
        # Selector untuk harga diubah
        price = item.find_element(By.CSS_SELECTOR, "div.price").text.strip()
    except:
        price = "N/A"

    print(f"{i}. {product_name}; Price: {price}")
    produk_list.append({
        "No": i,
        "Product Name": product_name,
        "Price": price
    })

print("=" * 60)

# Simpan ke file CSV baru
df = pd.DataFrame(produk_list)
# Nama file diubah agar tidak menimpa file lama
df.to_csv("daftar_hp_poco_xiaomi.csv", index=False, encoding="utf-8-sig", sep=";")
print("\n✅ Data berhasil disimpan ke 'daftar_hp_poco_xiaomi.csv'")

# Tutup browser
driver.quit()