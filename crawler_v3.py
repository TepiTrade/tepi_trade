import os, json, requests
from bs4 import BeautifulSoup
def get_amazon():
 url = "https://www.amazon.com.br/gp/bestsellers/kitchen/"
 headers = {"User-Agent": "Mozilla/5.0"}
 products = []
 try:
 r = requests.get(url, headers=headers, timeout=30)
 soup = BeautifulSoup(r.text, "lxml")
 items = soup.select(".zg-grid-general-faceout")
 for card in items:
 try:
 img_tag = card.find("img")
 name = img_tag["alt"]
 link = "https://www.amazon.com.br" + card.find("a")["href"]
 img = img_tag["src"]
 products.append({
 "merchant_domain": "amazon.com.br",
 "affiliate_url": link.split("?")[0] + "?tag=ctctechstore-20",
 "name": name,
 "price": "Oferta",
 "image_url": img
 })
 except: continue
 return products
 except: return []
items = get_amazon()
os.makedirs("alimentar", exist_ok=True)
f = open("alimentar/produtos_novos.json", "w", encoding="utf-8")
json.dump(items, f, ensure_ascii=False, indent=4)
f.close()
print(json.dumps({"count": len(items)}))
