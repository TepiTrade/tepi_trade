import os, json, time, hashlib
from typing import List, Dict
import requests
from slugify import slugify

WC_SITE = os.getenv("WC_SITE", "").rstrip("/")
WC_CK   = os.getenv("WC_CK")
WC_CS   = os.getenv("WC_CS")

USE_AMAZON = all([os.getenv("AMZ_ACCESS_KEY"), os.getenv("AMZ_SECRET_KEY"), os.getenv("AMZ_PARTNER_TAG")])
USE_MELI   = all([os.getenv("MELI_APP_ID"), os.getenv("MELI_SECRET"), os.getenv("MELI_TOKEN")])
USE_SHOPEE = all([os.getenv("SHOPEE_PARTNER_ID"), os.getenv("SHOPEE_PARTNER_KEY"), os.getenv("SHOPEE_SHOP_ID")])
USE_ALX    = all([os.getenv("ALX_APP_KEY"), os.getenv("ALX_APP_SECRET")])

CSV_FEEDS  = [u.strip() for u in os.getenv("CSV_FEEDS","").split(",") if u.strip()]

def http_get(url, headers=None, params=None):
    r = requests.get(url, headers=headers or {}, params=params or {}, timeout=40)
    r.raise_for_status()
    return r

def normalize(rec: Dict) -> Dict:
    title = rec.get("title") or rec.get("name") or ""
    affiliate_url = rec.get("affiliate_url") or rec.get("url") or ""
    image_url = rec.get("image_url") or ""
    price = float(str(rec.get("price") or "0").replace(",", ".") or 0)
    currency = rec.get("currency") or "BRL"
    category = rec.get("category") or "Outros"
    merchant = rec.get("merchant") or rec.get("merchant_domain") or "desconhecido"
    sku = rec.get("sku") or ""
    stock = int(float(rec.get("stock") or 0))
    description = rec.get("description") or ""
    brand = rec.get("brand") or ""

    base = f"{brand}|{title}|{merchant}"
    fp = hashlib.sha1(base.encode("utf-8")).hexdigest()

    return {
        "title": title.strip(),
        "description": description.strip(),
        "price": price,
        "currency": currency,
        "image_url": image_url,
        "category": category.strip(),
        "merchant": merchant.strip(),
        "affiliate_url": affiliate_url.strip(),
        "sku": sku.strip(),
        "stock": stock,
        "fingerprint": fp
    }

def fetch_csv_feeds(urls: List[str]) -> List[Dict]:
    out = []
    for url in urls:
        try:
            text = http_get(url).text
            lines = [l for l in text.splitlines() if l.strip()]
            headers = [h.strip() for h in lines[0].split(",")]
            for line in lines[1:]:
                cols = line.split(",")
                row = {headers[i]: (cols[i].strip() if i < len(cols) else "") for i in range(len(headers))}
                mapped = {
                    "title": row.get("name") or row.get("title"),
                    "description": row.get("description"),
                    "price": row.get("price") or row.get("regular_price") or "0",
                    "currency": row.get("currency") or "BRL",
                    "image_url": row.get("image_url") or row.get("images"),
                    "category": row.get("category") or row.get("categories") or "Outros",
                    "merchant": row.get("merchant_domain") or row.get("merchant") or "csv",
                    "affiliate_url": row.get("affiliate_url") or row.get("url") or row.get("link"),
                    "sku": row.get("sku") or "",
                    "stock": row.get("stock") or row.get("in_stock") or "0",
                    "brand": row.get("brand") or ""
                }
                out.append(normalize(mapped))
        except Exception as e:
            print(f"[CSV] Falha em {url}: {e}")
    return out

def fetch_amazon() -> List[Dict]:
    if not USE_AMAZON: return []
    return []

def fetch_meli() -> List[Dict]:
    if not USE_MELI: return []
    return []

def fetch_shopee() -> List[Dict]:
    if not USE_SHOPEE: return []
    return []

def fetch_alx() -> List[Dict]:
    if not USE_ALX: return []
    return []

def dedup_cheapest(items: List[Dict]) -> List[Dict]:
    by_fp = {}
    for it in items:
        fp = it["fingerprint"]
        if fp not in by_fp or it["price"] < by_fp[fp]["price"]:
            by_fp[fp] = it
    return list(by_fp.values())

def wc_upsert(batch: List[Dict]):
    if not (WC_SITE and WC_CK and WC_CS):
        raise RuntimeError("WC_SITE/WC_CK/WC_CS ausentes")
    url = f"{WC_SITE}/wp-json/wc/v3/products/batch"
    headers = {"Content-Type": "application/json"}
    create_payload = []
    for it in batch:
        create_payload.append({
            "name": it["title"][:200],
            "type": "external",
            "regular_price": f'{it["price"]:.2f}',
            "external_url": it["affiliate_url"] or it["merchant"],
            "button_text": "Comprar",
            "description": it["description"],
            "short_description": it["merchant"],
            "categories": [{"name": it["category"]}],
            "images": [{"src": it["image_url"]}] if it["image_url"] else [],
            "sku": it["sku"] or it["fingerprint"],
            "manage_stock": False
        })
    payload = {"create": create_payload}
    r = requests.post(url, auth=(WC_CK, WC_CS), headers=headers, data=json.dumps(payload), timeout=60)
    if r.status_code >= 300:
        print("WC ERROR", r.status_code, r.text)
    else:
        print("WC OK", r.status_code)

def main():
    pool = []
    if CSV_FEEDS:
        pool += fetch_csv_feeds(CSV_FEEDS)
    pool += fetch_amazon()
    pool += fetch_meli()
    pool += fetch_shopee()
    pool += fetch_alx()

    if not pool:
        print("Nada para importar nesta rodada.")
        return

    pool = [p for p in pool if p.get("title") and p.get("affiliate_url")]
    pool = dedup_cheapest(pool)

    for i in range(0, len(pool), 50):
        wc_upsert(pool[i:i+50])
        time.sleep(1)

if __name__ == "__main__":
    main()
