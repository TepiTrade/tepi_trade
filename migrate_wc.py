import os, csv, io, requests, html, re

WC_URL  = os.environ.get("WC_URL","").rstrip("/")
WC_CK   = os.environ.get("WC_CK","")
WC_CS   = os.environ.get("WC_CS","")
CSV_URL = os.environ.get("CSV_URL","")

REQUIRED = ("Name","External URL","Images","Description")
DEFAULT_CATEGORY = "Afiliados"

def api(m,p,**k):
    u=f"{WC_URL}/wp-json/wc/v3{p}"
    r=requests.request(m,u,auth=(WC_CK,WC_CS),timeout=40,**k)
    if not r.ok: raise SystemExit(f"Erro {r.status_code}: {r.text[:400]}")
    return r.json()

def find_by_name(name):
    r=api("GET","/products",params={"search":name,"per_page":1})
    return r[0] if r else None

def get_cat(name,parent=0):
    r=api("GET","/products/categories",params={"search":name,"per_page":1,"parent":parent})
    for c in r or []:
        if c["name"].strip().lower()==name.strip().lower() and c["parent"]==parent: return c
    return None

def ensure_cat_path(path):
    parts=[p.strip() for p in re.split(r"[|>/]",path) if p.strip()]
    if not parts: parts=[DEFAULT_CATEGORY]
    parent=0; last=None
    for p in parts:
        c=get_cat(p,parent)
        if not c: c=api("POST","/products/categories",json={"name":p,"parent":parent})
        parent=c["id"]; last=c
    return {"id":last["id"]}

def ensure_cats(cell):
    if not cell: return [ensure_cat_path(DEFAULT_CATEGORY)]
    out=[]; seen=set()
    for tok in re.split(r"[;,]",cell):
        tok=tok.strip()
        if not tok: continue
        c=ensure_cat_path(tok)
        if c["id"] not in seen: out.append(c); seen.add(c["id"])
    return out or [ensure_cat_path(DEFAULT_CATEGORY)]

def ensure_tags(cell):
    names=[x.strip() for x in re.split(r"[;,]",cell or "") if x.strip()]
    out=[]
    for n in names:
        q=api("GET","/products/tags",params={"search":n,"per_page":1})
        t=next((t for t in q if t["name"].lower()==n.lower()),None)
        if not t: t=api("POST","/products/tags",json={"name":n})
        out.append({"id":t["id"]})
    return out

def parse_imgs(cell):
    urls=[u.strip() for u in re.split(r"[,\s]+",cell or "") if u.strip().startswith("http")]
    return [{"src":u} for u in urls]

def valid(row):
    # obrigatório: Name, External URL, Images, Description
    return all((row.get("Name") or row.get("Nome"),
                row.get("External URL") or row.get("Link"),
                (row.get("Images") or "").strip(),
                (row.get("Description") or "").strip()))

def upsert(row):
    if not valid(row):
        print(f"Pulado (incompleto): {row.get('Name') or row.get('Nome')}")
        return

    name=(row.get("Name") or row.get("Nome")).strip()
    url =(row.get("External URL") or row.get("Link")).strip()
    btn =(row.get("Button text") or "Comprar").strip()
    desc=(row.get("Description") or "").strip()
    sdesc=(row.get("Short description") or f"{name} — produto afiliado.").strip()
    imgs=parse_imgs(row.get("Images"))
    cats=ensure_cats(row.get("Categories") or row.get("Categoria") or "")
    tags=ensure_tags(row.get("Tags") or "")
    price=(row.get("Regular price") or "").strip() or None

    payload={
      "name":name,
      "type":"external",
      "external_url":url,
      "button_text":btn,
      "regular_price":price,
      "images":imgs,
      "categories":cats,
      "tags":tags,
      "description":html.unescape(desc),
      "short_description":html.unescape(sdesc),
      "catalog_visibility":"visible",
      "status":"publish",
    }

    ex=find_by_name(name)
    if ex: api("PUT",f"/products/{ex['id']}",json=payload); print(f"Atualizado: {name}")
    else:  api("POST","/products",json=payload);           print(f"Criado: {name}")

def run():
    if not (WC_URL and WC_CK and WC_CS and CSV_URL):
        raise SystemExit("Defina WC_URL, WC_CK, WC_CS e CSV_URL.")
    r=requests.get(CSV_URL,timeout=40); r.raise_for_status()
    for row in csv.DictReader(io.StringIO(r.text)):
        upsert(row)

if __name__=="__main__": run()
