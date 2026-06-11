import urllib.request
import os
import time

OUTPUT_DIR = r"C:\Users\USER\Documents\GitHub\Boutique\asiko-boutique\static\uploads"
MIN_SIZE = 10 * 1024

PRODUCTS = [
    ("Ivory Agbada Set",     "prod_agbada.jpg",        "29133975"),
    ("Adire Bubu Dress",     "prod_bubu_dress.jpg",    "34249461"),
    ("Kano Leather Loafers", "prod_loafers.jpg",       "20763458"),
    ("Aso-Oke Dinner Jacket","prod_aso_oke_jacket.jpg","34584331"),
    ("Benin Bronze Cuff",    "prod_bronze_cuff.jpg",   "20493839"),
    ("Calabar Mermaid Skirt","prod_mermaid_skirt.jpg", "35845304"),
    ("Hausa Embroidered Cap","prod_embroidered_cap.jpg","32919054"),
    ("Sahel Kimono Jacket",  "prod_kimono_jacket.jpg", "34586666"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def try_download(photo_id, dest_path):
    url = f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=800"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < MIN_SIZE:
            print(f"    Too small ({len(data)} bytes)")
            return False
        with open(dest_path, "wb") as f:
            f.write(data)
        print(f"    OK - {len(data)/1024:.1f} KB")
        return True
    except Exception as e:
        print(f"    FAILED: {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []

    for product_name, filename, photo_id in PRODUCTS:
        dest = os.path.join(OUTPUT_DIR, filename)
        print(f"\n{product_name:35s} -> {filename:30s} (photo ID: {photo_id})")

        if os.path.isfile(dest) and os.path.getsize(dest) > MIN_SIZE:
            print(f"  Already exists ({os.path.getsize(dest)/1024:.1f} KB)")
            results.append((product_name, filename, dest))
            continue

        if try_download(photo_id, dest):
            results.append((product_name, filename, dest))
        else:
            print(f"  [FAIL] {product_name}")
            results.append((product_name, filename, None))

        time.sleep(0.5)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for product_name, filename, path in results:
        if path and os.path.isfile(path):
            size = os.path.getsize(path) / 1024
            print(f"  {product_name:35s} -> {filename:30s} ({size:.1f} KB) [OK]")
        else:
            print(f"  {product_name:35s} -> {filename:30s} [FAILED]")


if __name__ == "__main__":
    main()
