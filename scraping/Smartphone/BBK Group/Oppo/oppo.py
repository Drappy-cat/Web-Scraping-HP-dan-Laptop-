import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json  # Diperlukan untuk beberapa website yang menyimpan data di script tag

# ==============================================================================
# KONFIGURASI GLOBAL
# ==============================================================================

# Header untuk membuat permintaan kita terlihat seperti dari browser sungguhan.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Connection': 'keep-alive'
}

# ==============================================================================
# OTAK SCRAPER: KONFIGURASI UNTUK SETIAP WEBSITE
# ==============================================================================
WEBSITE_CONFIGS = {
    'OPPO': {
        'base_url': "https://www.oppo.com",  # Base URL tanpa /id/
        'phone_list_url': "https://www.oppo.com/id/smartphones/",
        'selectors': {
            # Selector di halaman daftar produk
            'product_card_link': 'a.card-product',
            # Selector di halaman detail produk
            'product_name': 'h1.pdp-name',
            'tagline': 'p.pdp-slogan',
            'image': 'div.pdp-images-swiper-slide-img img',
            'colors_container': 'div.pdp-version-select-item-wrap',  # Kontainer untuk semua pilihan warna
            'colors_text': 'span.version-name',  # Teks nama warna
            'spec_container': 'div.pdp-spec-item',
            'spec_key': 'div.pdp-spec-item-title',
            'spec_value': 'div.pdp-spec-item-value'
        },
        # Halaman spesifikasi OPPO sudah menyatu dengan halaman produk utama
        'spec_page_suffix': ''
    },
    'VIVO': {
        'base_url': 'https://www.vivo.com',
        'phone_list_url': 'https://www.vivo.com/id/products',
        'selectors': {
            'product_card_link': 'a.product-card',
            'product_name': 'h1.product-name',
            'tagline': 'p.product-slogan',  # Vivo mungkin tidak punya tagline di halaman produk
            'image': 'div.swiper-slide-active img.main-img',
            'colors_container': 'div.color-pick-wrap',
            'colors_text': 'span.color-name',
            'spec_container': 'div.spec-item',
            'spec_key': 'span.spec-key',
            'spec_value': 'span.spec-value'
        },
        'spec_page_suffix': '/specs'  # Halaman spec Vivo ada di /specs
    },
    'XIAOMI': {
        'base_url': 'https://www.mi.co.id',
        'phone_list_url': 'https://www.mi.co.id/id/phone',
        'selectors': {
            'product_card_link': 'a.product-item-v2__link',
            'product_name': 'h1.buy-header-v2__title',
            'tagline': 'p.buy-header-v2__subtitle',
            'image': 'div.gallery-v3__container-image-wrapper picture img',
            'colors_container': 'div.buy-style-v2-selector__container',
            'colors_text': 'p.buy-style-v2-selector-item__text',
            'spec_container': 'div.specification-v2__content-item',
            'spec_key': 'h3.specification-v2__content-title',
            'spec_value': 'div.specification-v2__content-value'
        },
        'spec_page_suffix': '/specs'
    }
}


def get_phone_urls(brand_config):
    """
    Fungsi generik untuk mengambil URL produk berdasarkan konfigurasi brand.
    """
    print(f"Mengambil URL produk dari: {brand_config['phone_list_url']}")
    phone_urls = []
    try:
        response = requests.get(brand_config['phone_list_url'], headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        product_cards = soup.select(brand_config['selectors']['product_card_link'])

        if not product_cards:
            print(
                f"Peringatan: Tidak dapat menemukan link produk menggunakan selector '{brand_config['selectors']['product_card_link']}'. Mungkin struktur website telah berubah.")
            return []

        for card in product_cards:
            href = card.get('href')
            if href:
                # Menggunakan urljoin untuk menggabungkan URL dengan aman
                full_url = requests.compat.urljoin(brand_config['base_url'], href)
                phone_urls.append(full_url)

        print(f"Berhasil menemukan {len(set(phone_urls))} URL produk unik.")
        return list(set(phone_urls))

    except requests.exceptions.RequestException as e:
        print(f"Terjadi kesalahan saat mengakses {brand_config['phone_list_url']}: {e}")
        return []


def scrape_product_details(product_url, brand_config):
    """
    Fungsi generik untuk mengambil detail produk berdasarkan konfigurasi brand.
    """
    print(f"  -> Scraping: {product_url}")
    spec_url = product_url.rstrip('/') + brand_config.get('spec_page_suffix', '')

    # Beberapa website mengarahkan dari URL tanpa slash ke URL dengan slash, kita standarkan
    if not product_url.endswith('/'):
        product_url += '/'

    try:
        # Ambil halaman utama produk
        response_main = requests.get(product_url, headers=HEADERS)
        response_main.raise_for_status()
        soup_main = BeautifulSoup(response_main.text, 'html.parser')

        soup_specs = soup_main
        # Jika halaman spesifikasi terpisah, ambil halamannya
        if brand_config.get('spec_page_suffix'):
            print(f"     -> Mengambil halaman spesifikasi: {spec_url}")
            response_specs = requests.get(spec_url, headers=HEADERS)
            response_specs.raise_for_status()
            soup_specs = BeautifulSoup(response_specs.text, 'html.parser')

        product_data = {}
        selectors = brand_config['selectors']

        product_data['URL Produk'] = product_url
        name_tag = soup_specs.select_one(selectors['product_name'])
        product_data['Nama Produk'] = name_tag.text.strip() if name_tag else 'N/A'

        tagline_tag = soup_main.select_one(selectors['tagline'])
        product_data['Tagline'] = tagline_tag.text.strip() if tagline_tag else 'N/A'

        image_tag = soup_main.select_one(selectors['image'])
        product_data['URL Gambar Utama'] = image_tag.get('src') if image_tag else 'N/A'

        colors = []
        # Menggunakan select untuk mengambil semua elemen warna
        color_elements = soup_main.select(f"{selectors['colors_container']} {selectors['colors_text']}")
        if color_elements:
            colors = [elem.text.strip() for elem in color_elements if elem.text.strip()]
        product_data['Warna'] = ', '.join(list(set(colors))) if colors else 'N/A'

        spec_items = soup_specs.select(selectors['spec_container'])
        for item in spec_items:
            key_tag = item.select_one(selectors['spec_key'])
            value_tag = item.select_one(selectors['spec_value'])
            if key_tag and value_tag:
                key = key_tag.text.strip()
                # Menggabungkan semua teks di dalam value tag, membersihkan spasi berlebih
                value = ' '.join(value_tag.text.strip().split())
                if key and key not in product_data:
                    product_data[key] = value

        return product_data

    except Exception as e:
        print(f"    !! Terjadi error saat memproses {product_url}: {e}")
        return None


def main():
    """
    Fungsi utama yang mengorkestrasi proses scraping untuk semua brand di konfigurasi.
    """
    all_brands_data = []

    for brand, config in WEBSITE_CONFIGS.items():
        print(f"\n{'=' * 20}\nMEMULAI SCRAPING UNTUK BRAND: {brand}\n{'=' * 20}")

        phone_urls = get_phone_urls(config)

        if not phone_urls:
            print(f"Tidak ada URL ditemukan untuk {brand}, lanjut ke brand berikutnya.")
            continue

        for url in phone_urls:
            data = scrape_product_details(url, config)
            if data:
                data['Brand'] = brand
                all_brands_data.append(data)
            time.sleep(1)  # Jeda 1 detik untuk tidak membebani server

    if not all_brands_data:
        print("\nProses selesai, namun tidak ada data yang berhasil di-scrape.")
        return

    print("\n\nProses scraping semua brand selesai. Menyimpan data ke file...")
    df = pd.DataFrame(all_brands_data)
    df = df.fillna('N/A')  # Ganti sel kosong dengan 'N/A'

    # Mengatur urutan kolom agar lebih rapi
    cols = list(df.columns)
    preferred_order = ['Brand', 'Nama Produk', 'Tagline', 'Warna', 'URL Produk', 'URL Gambar Utama']

    # Buat daftar kolom akhir
    final_cols = [col for col in preferred_order if col in cols]
    other_cols = [col for col in cols if col not in final_cols]
    final_cols.extend(other_cols)

    df = df[final_cols]

    output_csv = 'SEMUA_SPESIFIKASI_HP_GABUNGAN.csv'
    output_excel = 'SEMUA_SPESIFIKASI_HP_GABUNGAN.xlsx'

    try:
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        df.to_excel(output_excel, index=False)

        print(f"\nData gabungan berhasil disimpan ke:")
        print(f"1. File CSV: '{output_csv}'")
        print(f"2. File Excel: '{output_excel}'")
    except Exception as e:
        print(f"Gagal menyimpan file: {e}")


if __name__ == "__main__":
    main()