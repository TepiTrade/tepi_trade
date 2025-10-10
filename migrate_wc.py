import os, csv, io, requests, html

WC_URL  = os.environ.get("WC_URL","").rstrip("/")
WC_CK   = os.environ.get("WC_CK","")
WC_CS   = os.environ.get("WC_CS","")
CSV_URL = os.environ.get("CSV_URL","")

DEFAULT_CATEGORY = "Afiliados"

def api(method, path, **kw):
    u = f"{WC_URL}/wp-json/wc/v3{path}"
    r = requests.request(method, u, auth=(WC_CK, WC_CS), timeout=40, **kw)
    if not r.ok:
        raise SystemExit(f"Erro {r.status_code}: {r.text[:400]}")
    return r.json()

def find_product_by_name(name):
    r = api("GET", "/products", params={"search": name, "per_page": 1})
    return r[0] if r else None

def ensure_category(name):
    q = api("GET", "/products/categories", params={"search": name, "per_page": 1})
    if q and q[0]["name"].lower() == name.lower():
        return {"id": q[0]["id"]}
    c = api("POST", "/products/categories", json={"name": name})
    return {"id": c["id"]}

def ensure_categories(cell):
    names = [x.strip() for x in (cell or "").split(",") if x.strip()]
    if not names:
        names = [DEFAULT_CATEGORY]
    return [ensure_category(n) for n in names]

def ensure_tag(name):
    q = api("GET", "/products/tags", params={"search": name, "per_page": 1})
    if q and q[0]["name"].lower() == name.lower():
        return {"id": q[0]["id"]}
    t = api("POST", "/products/tags", json={"name": name})
    return {"id": t["id"]}

def ensure_tags(cell):
    names = [x.strip() for x in (cell or "").split(",") if x.strip()]
    return [ensure_tag(n) for n in names]

def parse_images(cell):
    urls = [u.strip() for u in (cell or "").split(",") if u.strip()]
    return [{"src": u} for u in urls]

def fallback_description(name):
    ce = f'[content-egg module="GoogleImages" keyword="{name}" limit="6"]'
    txt = f"<p>{html.escape(name)} — oferta de parceiro. Clique em Comprar para ver detalhes na loja parceira.</p>\n\n{ce}"
    return txt

def upsert(row):
    name  = (row.get("Name") or row.get("Nome") or "").strip()
    if not name:
        return
    price = (row.get("Regular price") or "").strip()
    ext   = (row.get("External URL") or row.get("Link") or "").strip()
    btn   = (row.get("Button text") or "Comprar").strip()
    desc  = (row.get("Description") or "").strip()
    sdesc = (row.get("Short description") or "").strip()
    imgs  = parse_images(row.get("Images") or "")
    cats  = ensure_categories(row.get("Categories") or "")
    tags  = ensure_tags(row.get("Tags") or "")

    if not desc:
        desc = fallback_description(name)
    if not sdesc:
        sdesc = f"{name} — produto afiliado. Compare o preço e compre com segurança."

    payload = {
        "name": name,
        "type": "external" if ext else "simple",
        "regular_price": price or None,
        "external_url": ext or None,
        "button_text": btn if ext else None,
        "images": imgs,
        "categories": cats,
        "tags": tags,
        "description": html.unescape(desc),
        "short_description": html.unescape(sdesc),
        "catalog_visibility": "visible",
        "status": "publish",
    }

    exist = find_product_by_name(name)
    if exist:
        api("PUT", f"/products/{exist['id']}", json=payload)
        print(f"Atualizado: {name}")
    else:
        api("POST", "/products", json=payload)
        print(f"Criado: {name}")

def run():
    if not (WC_URL and WC_CK and WC_CS and CSV_URL):
        raise SystemExit("Defina WC_URL, WC_CK, WC_CS e CSV_URL.")
    r = requests.get(CSV_URL, timeout=40); r.raise_for_status()
    for row in csv.DictReader(io.StringIO(r.text)):
        upsert(row)

if __name__ == "__main__":
    run()
