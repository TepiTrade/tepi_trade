import re, json, time, random, hashlib, html, urllib.parse, requests
from bs4 import BeautifulSoup
from slugify import slugify

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
HDRS = {"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}
TIMEOUT = 20
MAX_PER_RUN = 20

SEARCH_ENGINES = [
    "https://www.bing.com/search?q={q}",
    "https://duckduckgo.com/html/?q={q}"
]

# domínios permitidos (expanda depois)
DOMAINS_OK = [
    "amazon.com.br","mercadolivre.com.br","shopee.com.br","shein.com",
    "aliexpress.com","magazineluiza.com.br","americanas.com.br","submarino.com.br",
    "kabum.com.br","casasbahia.com.br"
]

BAD_PATH = ("login","cart","checkout","track","seller","support","help","mailto:", "account","orders","wishlist","entrar","minha-conta")

PRICE_RX = re.compile(r"(R\$\s*\d{1,3}(\.\d{3})*(,\d{2})?)", re.I)

QUERIES = [
    "iphone 14 128gb preço", "notebook i5 16gb ssd 512",
    "smart tv 50 4k", "ssd nvme 1tb", "roteador wi-fi 6 ax3000",
]

def http_get(url):
    try:
        r = requests.get(url, headers=HDRS, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r.text, r.url
    except:
        return None, url

def extract_meta(html_text):
    soup = BeautifulSoup(html_text, "lxml")

    def m(name):
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return tag.get("content").strip() if tag and tag.get("content") else None

    title = (m("og:title") or (soup.title.string.strip() if soup.title else None))
    img = m("og:image")
    desc = m("og:description") or m("description")

    price = None
    if html_text:
        mprice = PRICE_RX.search(html_text)
        if mprice:
            price = mprice.group(1)

    return {"title": title, "image": img, "description": desc, "price_text": price}

def allowed(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc.lower()
    path = u.path.lower()
    if any(b in path for b in BAD_PATH):
        return False
    return any(host.endswith(d) for d in DOMAINS_OK)

def search_links(query):
    links = []
    q = urllib.parse.quote_plus(query)
    for tmpl in SEARCH_ENGINES:
        html_text, _ = http_get(tmpl.format(q=q))
        if not html_text:
            continue
        soup = BeautifulSoup(html_text, "lxml")
        for a in soup.select("a[href]"):
            href = a["href"]
            if href.startswith("/"):  # relativos em motores
                continue
            if href.startswith("http"):
                links.append(href)
    # dedup simples
    seen = set()
    out = []
    for l in links:
        u = l.split("#")[0]
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def sku_from_url(u):
    return hashlib.md5(u.encode("utf-8")).hexdigest()

def crawl_once():
    random.shuffle(QUERIES)
    created = 0
    items = []
    for q in QUERIES:
        if created >= MAX_PER_RUN:
            break
        for ln in search_links(q):
            if created >= MAX_PER_RUN:
                break
            if not allowed(ln):
                continue
            html_text, final_url = http_get(ln)
            if not html_text:
                continue
            meta = extract_meta(html_text)
            if not (meta["title"] and (meta["price_text"] or meta["image"])):
                continue
            item = {
                "sku": sku_from_url(final_url),
                "url": final_url,
                "query": q,
                "title": meta["title"],
                "image": meta["image"],
                "price_text": meta["price_text"],
                "description": meta["description"],
                "slug": slugify(meta["title"])[:80],
                "ts": int(time.time()),
            }
            items.append(item)
            created += 1
            time.sleep(0.3)
    return items

if __name__ == "__main__":
    data = crawl_once()
    print(json.dumps({"created": len(data), "items": data}, ensure_ascii=False))
