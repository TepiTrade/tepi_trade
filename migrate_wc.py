import os, csv, io, requests, html, re

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

def get_category_by_name(name, parent=0):
    r = api("GET", "/products/categories",
            params={"search": name, "per_page": 1, "parent": parent})
    for c in r or []:
        if c["name"].strip().lower() == name.strip().lower() and c["parent"] == parent:
            return c
    return None

def ensure_category(name, parent=0):
    c = get_category_by_name(name, parent)
    if c: return {"id": c["id"]}
    c = api("POST", "/products/categories", json={"name": name, "parent": parent})
    return {"id": c["id"]}

def ensure_category_path(path_str):
    """
    Aceita: "Afiliados|Acessórios|Relógios" ou "Afiliados > Acessórios"
    Cria hierarquia e retorna a última categoria.
    """
    parts = [p.strip() for p in re.split(r"[|>/]", path_str) if p.strip()]
    if not parts: parts = [DEFAULT_CATEGORY]
    parent_id = 0
    last = None
    for p in parts:
        c = get_category_by_name(p, parent_id)
        if not c:
            c = api("POST", "/products/categories", json={"name": p, "parent": parent_id})
        parent_id = c["id"]
        last = c
    return {"id": last["id"]}

def ensure_categories(cell):
    if not cell:
        return [ensure_category(DEFAULT_CATEGORY)]
    # divide por vírgula OU por ponto e vírgula
    raw = []
    for chunk in re.split(r"[;,]", cell):
        chunk = chunk.strip()
        if chunk: raw.append(chunk)
    seen = set()
    out = []
    for token in raw:
        # token pode ter hierarquia com | ou >
        cat = ensure_category_path(token)
        if cat["id"] not in seen:
            out.append(cat); seen.add(cat["id"])
    return out or [ensure_category(DEFAULT_CATEGORY)]

def ensure_tag(name):
    r = api("GET", "/products/tags", params={"search": name, "per_page": 1})
    for t in r or []:
        if t["name"].strip().lower() == name.strip().lower():
            return {"id": t["id"]}
    t = api("POST", "/products/tags", json={"name": name})
    return {"id": t["id"]}

def ensure_tags(cell):
    names = [x.strip() for x in re.split(r"[;,]", cell or "") if x.strip()]
    return [ensure_tag(n) for n in names]

def parse_images(cell):
    urls = [u.strip() for u in re.split(r"[,\s]+", cell or "") if u.strip().startswith("http")]
    return [{"src": u} for u in urls]

def fallback_description(name):
    ce = f'[content-egg module="GoogleImages" keyword="{name}" limit="6"]'
    return f"<p>{html.escape(name)} — oferta de parceiro. Clique em Comprar.</p>\n\n{ce}"

def upsert(row):
    name  = (row.get("Name") or row.get("Nome") or "").strip()
    if not name: return

    price = (row.get("Regular price") or row.get("Preço") or "").strip()
    ext   = (row.get("External URL") or row.get("Link") or "").strip()
    btn   = (row.get("Button text") or "Comprar").strip()
    desc  = (row.get("Description") or "").strip()
    sdesc = (row.get("Short description") or "").strip()
    imgs  = parse_images(row.get("Images") or "")
    cats  = ensure_categories(row.get("Categories") or row.get("Categoria") or "")
    tags  = ensure_tags(row.get("Tags") or "")

    if not desc:  desc  = fallback_description(name)
    if not sdesc: sdesc = f"{name} — produto afiliado. Compare o preço e compre com segurança."

    payload = {
        "name": name,
        "type": "external" if ext else "simple",
        "regular_price": price or None,
        "external_url": ext or None,
        "button_text": btn if ext else None,
        "images": imgs,             # usa URLs do CSV para capa/galeria
        "categories": cats,         # cria hierarquia se usar |
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
