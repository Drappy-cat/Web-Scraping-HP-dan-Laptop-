import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re

# ==============================================================================
# KONFIGURASI TERPUSAT UNTUK GSMARENA.ID
# ==============================================================================
CONFIG = {
    'base_url': "https://www.gsmarena.id",
    'brand_url_template': "https://www.gsmarena.id/merek/{brand_name}/",
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    },
    'selectors': {
        # --- SELECTOR INI TELAH DIPERBARUI SESUAI LAYOUT BARU ---
        'product_link': 'div.makers > ul > li > a',
        'next_page_link': 'a.page-next',
        'phone_name': 'h1.phone-name',
        'image': 'div.img-phone-wrap > img',
        'spec_table': 'table.table-spec',
        'spec_category': 'caption',
        'spec_row': 'tr',
        'spec_key': 'td.spec-label',
        'spec_value': 'td.spec-value'
    }
}


# ==============================================================================
# FUNGSI-FUNGSI UTAMA
# ==============================================================================

def get_all_phone_urls_for_brand(brand_name):
    """
    Mengambil semua URL produk untuk satu brand, dengan menangani navigasi halaman (pagination).
    """
    all_urls = []
    page_url = CONFIG['brand_url_template'].format(brand_name=brand_name)
    page_counter = 1

    while page_url:
        print(f"🔄 Mengambil URL dari Halaman #{page_counter}...")
        try:
            response = requests.get(page_url, headers=CONFIG['headers'])
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ambil semua link produk di halaman saat ini
            product_links = soup.select(CONFIG['selectors']['product_link'])
            if not product_links:
                print("   - Tidak ada produk ditemukan di halaman ini.")
                break

            for link in product_links:
                full_url = requests.compat.urljoin(CONFIG['base_url'], link['href'])
                all_urls.append(full_url)

            # Cari link ke halaman berikutnya
            next_page_tag = soup.select_one(CONFIG['selectors']['next_page_link'])
            if next_page_tag and next_page_tag.has_attr('href'):
                page_url = requests.compat.urljoin(CONFIG['base_url'], next_page_tag['href'])
                page_counter += 1
                time.sleep(1)  # Jeda sopan sebelum ke halaman berikutnya
            else:
                print("   - Ini adalah halaman terakhir.")
                page_url = None  # Hentikan loop

        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                print(f"   ❌ Halaman tidak ditemukan (404). Pastikan nama brand '{brand_name}' sudah benar.")
            else:
                print(f"   ❌ Gagal mengakses {page_url}: {e}")
            break

    unique_urls = list(set(all_urls))
    print(f"\n✅ Ditemukan total {len(unique_urls)} URL produk unik untuk brand '{brand_name}'.")
    return unique_urls


def scrape_product_details(url):
    """
    Menggunakan Requests & BeautifulSoup untuk mengambil detail dari satu URL produk.
    """
    try:
        response = requests.get(url, headers=CONFIG['headers'])
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        selectors = CONFIG['selectors']
        device_data = {"Product URL": url}

        device_data["Phone Name"] = soup.select_one(selectors['phone_name']).text.strip()

        image_tag = soup.select_one(selectors['image'])
        device_data["Image URL"] = requests.compat.urljoin(CONFIG['base_url'], image_tag['src']) if image_tag else "N/A"

        spec_tables = soup.select(selectors['spec_table'])
        for table in spec_tables:
            category = table.select_one(selectors['spec_category']).text.strip()
            rows = table.select(selectors['spec_row'])
            for row in rows:
                key_tag = row.select_one(selectors['spec_key'])
                value_tag = row.select_one(selectors['spec_value'])
                if key_tag and value_tag:
                    key = f"Spek_{category}_{key_tag.text.strip()}".replace(" ", "_")
                    value = ' '.join(value_tag.text.strip().split())
                    device_data[key] = value

        return device_data

    except Exception as e:
        print(f"    ❌ Gagal mem-parsing {url}: {e}")
        return None


def main(brand_name):
    """Fungsi utama untuk menjalankan scraper gsmarena.id."""
    print(f"\n🚀 Memulai proses scraping untuk brand '{brand_name}' dari gsmarena.id...")

    # Langkah 1: Dapatkan semua link
    phone_urls = get_all_phone_urls_for_brand(brand_name.lower())  # Ubah ke huruf kecil untuk konsistensi URL

    if not phone_urls:
        print("❌ Tidak ada URL yang bisa di-scrape. Proses dihentikan.")
        return

    # Langkah 2: Scrape detail dari setiap link
    product_list = []
    total_links = len(phone_urls)
    for i, url in enumerate(phone_urls):
        # Mengambil nama dari URL untuk ditampilkan di log agar lebih informatif
        phone_name_from_url = url.strip('/').split('/')[-1]
        print(f"    ({i + 1}/{total_links}) Scraping: {phone_name_from_url}")
        details = scrape_product_details(url)
        if details:
            product_list.append(details)
        time.sleep(0.5)  # Jeda sopan antar request

    # Langkah 3: Simpan hasil
    print("\n" + "=" * 60)
    print("📊 Proses scraping selesai. Menyimpan data...")

    if not product_list:
        print("❌ Tidak ada data yang berhasil di-scrape.")
    else:
        df = pd.DataFrame(product_list)

        # Atur urutan kolom
        first_cols = ['Phone Name', 'Product URL', 'Image URL']
        existing_first_cols = [col for col in first_cols if col in df.columns]
        other_cols = sorted([col for col in df.columns if col not in existing_first_cols])
        final_columns = existing_first_cols + other_cols

        df = df.reindex(columns=final_columns).fillna("N/A")
        df.insert(0, 'No', range(1, 1 + len(df)))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"gsmarena_id_{brand_name.lower()}_{timestamp}.csv"

        df.to_csv(output_filename, index=False, encoding="utf-8-sig", sep=";")

        print(f"\n✅ Data lengkap berhasil disimpan ke '{output_filename}'")
        print(f"    - Total Produk Disimpan: {len(df)}")

    print("🎉 Proses selesai.")


if __name__ == '__main__':
    # Cukup ubah nama brand di bawah ini lalu jalankan script.
    # Pastikan nama brand ditulis persis seperti di URL (huruf kecil).
    # Contoh: 'samsung', 'oppo', 'xiaomi', 'apple', 'vivo'
    brand_to_scrape = "samsung"

    main(brand_to_scrape)