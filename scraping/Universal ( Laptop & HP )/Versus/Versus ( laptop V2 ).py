import requests
import pandas as pd
from datetime import datetime

# 1. Definisikan endpoint dan payload
api_url = "https://versus.com/api/search/search"

# Payload untuk mengambil data laptop dari Halaman 4, diurutkan berdasarkan skor
payload = {
    "query": "",
    "page": 3,  # Ingat: Halaman 4 di situs = page 3 di API
    "hitsPerPage": 30,
    "facetFilters": [
        [
            "category.id:laptop"
        ]
    ],
    "sort": "totalScore:desc"
}

# Header standar untuk meniru browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}

print("🚀 Mengirim permintaan ke API Versus...")

# 2. Kirim request POST dengan payload JSON
try:
    response = requests.post(api_url, headers=headers, json=payload)
    # Memeriksa apakah permintaan berhasil (status code 200)
    response.raise_for_status()

    # 3. Ubah respons menjadi format JSON
    data = response.json()

    # 4. Ekstrak daftar produk dari struktur data JSON
    # Lokasi data: resultGroups -> elemen pertama [0] -> hits
    products = data.get('resultGroups', [{}])[0].get('hits', [])

    if not products:
        print("✅ Permintaan berhasil, namun tidak ada produk yang ditemukan di halaman ini.")
    else:
        print(f"✅ Berhasil mendapatkan {len(products)} data produk.")

        # 5. Konversi list of dictionaries menjadi DataFrame Pandas
        df = pd.DataFrame(products)

        # 6. Tampilkan beberapa kolom penting dari DataFrame
        print("\n--- Contoh Data Laptop dari Halaman 4 ---")
        kolom_pilihan = ['fullname', 'brand', 'totalScore', 'releaseDate', 'url']
        # Pastikan kolom yang dipilih ada di DataFrame
        kolom_untuk_ditampilkan = [kolom for kolom in kolom_pilihan if kolom in df.columns]

        # Tambahkan URL lengkap
        df['url'] = 'https://versus.com/id' + df['url']

        print(df[kolom_untuk_ditampilkan])

        # 7. Simpan ke file CSV (opsional)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nama_file = f"versus_laptop_page4_{timestamp}.csv"
        df.to_csv(nama_file, index=False, encoding='utf-8-sig', sep=';')
        print(f"\n💾 Data lengkap telah disimpan ke file: {nama_file}")


except requests.exceptions.HTTPError as errh:
    print(f"Http Error: {errh}")
except requests.exceptions.ConnectionError as errc:
    print(f"Error Connecting: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Timeout Error: {errt}")
except requests.exceptions.RequestException as err:
    print(f"Oops: Something Else: {err}")