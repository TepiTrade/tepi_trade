import os, csv, io, requests, html

WC_URL = os.environ.get("WC_URL", "").rstrip("/")
WC_CK  = os.environ.get("WC_CK", "")
WC_CS  = os.environ.get("WC_CS", "")
CSV_URL = os.environ.get("CSV_URL", "")

def api(method, path, **kw):
    if not WC_URL or not WC_CK or not WC_CS:
        raise SystemExit("Defina WC_URL, WC_CK e WC_CS nos segredos.")
    u = f"{WC_URL}/wp-json/wc/v3{path}"
    r = requests.request(method, u, auth=(WC_CK, WC_CS), timeout=40, **kw)
    if not r.ok:
        raise SystemExit(f"Erro {r.status_code}: {r.text[:400]}")
    return r.json()

def find_product_by_name(name):
    r = api("GET", "/products", params={"search": name, "per_page": 1})
    return r[0] if r else None

def parse_images(cell):
    return [{"src": u.strip()} for u in (cell or "").split(",") if u.strip()]

def ensure_categories(cell):
    names = [c.strip() for c in (cell or "").split(",") if c.strip()]
    out = []
    for n in names:
        q = api("GET", "/products/categories", params={"search": n, "per_page": 1})
        if q and q[0]["name"].lower() == n.lower():
            out.append({"id": q[0]["id"]})
        else:
            c = api("POST", "/products/categories", json={"name": n})
            out.append({"id": c["id"]})
    return out

def upsert(row):
    name  = row.get("Name") or row.get("Nome") or ""
    if not name: 
        return
    price = (row.get("Regular price") or "").strip()
    ext   = (row.get("External URL") or "").strip()
    btn   = (row.get("Button text") or "Comprar").strip()
    desc  = html.unescape(row.get("Description") or "")
    sdesc = html.unescape(row.get("Short description") or "")
    imgs  = parse_images(row.get("Images") or "")
    cats  = ensure_categories(row.get("Categories") or "")
    vis   = (row.get("Visibility in catalog") or "visible").strip().lower()
    pub   = str(row.get("Published") or "1").strip().lower() in ("1","true","yes","sim")

    payload = {
        "name": name,
        "type": "external" if ext else "simple",
        "regular_price": price or None,
        "external_url": ext or None,
        "button_text": btn if ext else None,
        "images": imgs,
        "categories": cats,
        "description": desc,
        "short_description": sdesc,
        "catalog_visibility": vis if vis in ("visible","catalog","search","hidden") else "visible",
        "status": "publish" if pub else "draft",
    }

    exist = find_product_by_name(name)
    if exist:
        api("PUT", f"/products/{exist['id']}", json=payload)
        print(f"Atualizado: {name}")
    else:
        api("POST", "/products", json=payload)
        print(f"Criado: {name}")

def run():
    if not CSV_URL:
        raise SystemExit("Defina CSV_URL nos segredos.")
    r = requests.get(CSV_URL, timeout=40)
    r.raise_for_status()
    for row in csv.DictReader(io.StringIO(r.text)):
        upsert(row)

if __name__ == "__main__":
    run()
