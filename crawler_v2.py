# crawler.py
import os, re, time, random, json, logging
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

ENGINES = [
    "https://www.bing.com/search?q=",
    "https://duckduckgo.com/html/?q=",
]

# deixe vazio para buscar globalmente; se quiser restringir, adicione domínios aqui
DOMAINS: List[str] = []

BAD_PATH = (
    "login", "cart", "checkout", "track", "seller", "support", "help", "mailto:",
    "account", "orders", "wishlist", "enter", "minha-conta"
)

PRICE_RX = re.compile(
    r"(?:R\$\s?|US\$\s?|€\s?|£\s?)(?:\d{1,3}(?:[\.\,]\d{3})*|\d+)(?:[\.\,]\d{2})?",
    re.IGNORECASE,
)

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def ok_url(u: str) -> bool:
    if not u or len(u) > 512: 
        return False
    low = u.lower()
    if any(b in low for b in BAD_PATH):
        return False
    if DOMAINS:
        return any(d in low for d in DOMAINS)
    return True

def extract_price(txt: str) -> Optional[str]:
    m = PRICE_RX.search(txt or "")
    return m.group(0) if m else None

def search_once(query: str) -> List[Dict]:
    q = requests.utils.quote(query)
    engine = random.choice(ENGINES)
    url = f"{engine}{q}"
    logging.info("GET %s", url)
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # Bing
    results = soup.select("li.b_algo h2 a, h2 a")
    if not results:
        # DuckDuckGo HTML
        results = soup.select("a.result__a, a[href][rel='nofollow']")
    out = []
    for a in results:
        href = a.get("href")
        title = norm_space(a.get_text())
        if not ok_url(href):
            continue
        out.append({"title": title, "url": href})
        if len(out) >= 20:
            break
    return out

def fetch_product_page(u: str) -> Dict:
    try:
        r = requests.get(u, headers=HEADERS, timeout=25)
        r.raise_for_status()
    except Exception as e:
        return {"url": u, "ok": False, "error": str(e)}

    soup = BeautifulSoup(r.text, "lxml")
    title = norm_space(
        (soup.select_one("meta[property='og:title']") or {}).get("content")
        or soup.title.string if soup.title else ""
    )
    if not title:
        h = soup.select_one("h1") or soup.select_one("h2")
        title = norm_space(h.get_text()) if h else ""

    price = None
    meta_price = soup.select_one("meta[itemprop='price'], meta[property='product:price:amount']")
    if meta_price and meta_price.get("content"):
        price = meta_price.get("content")
    if not price:
        price = extract_price(soup.get_text(" ", strip=True))

    return {
        "url": u, "ok": True,
        "title": title or None,
        "price": price,
    }

def crawl_queries(queries: List[str]) -> List[Dict]:
    all_items: List[Dict] = []
    for q in queries:
        hits = search_once(q)
        for h in hits:
            info = fetch_product_page(h["url"])
            info["query"] = q
            info["hit_title"] = h["title"]
            all_items.append(info)
            time.sleep(random.uniform(1.0, 2.2))
        time.sleep(random.uniform(2.0, 4.0))
    return all_items

def main():
    # edite/alimente por arquivo JSON no repositório se preferir
    QUERIES = [
        "iPhone 15 Pro Max preço", "Samsung S24 Ultra oferta",
        "Rolex Submariner price", "Ferrari F8 Tributo price",
        "Cartier Love Bracelet price", "apartamento de luxo preço m2",
    ]
    data = crawl_queries(QUERIES)
    print(json.dumps({"count": len(data), "items": data[:50]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
