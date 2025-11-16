from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import requests
from slugify import slugify


# ---------- Configuração básica ----------

BASE_DIR = Path(__file__).resolve().parent.parent
FEED_PATH = BASE_DIR / "alimentar" / "produtos_woo_01.csv"

# Essas variáveis já devem estar configuradas como segredos no GitHub
# WOO_BASE_URL / WC_SITE / WC_URL: ex. https://ctctech.store
# WOO_CONSUMER_KEY / WC_CK, WOO_CONSUMER_SECRET / WC_CS: chaves REST do WooCommerce
WOO_BASE_URL = (
    os.environ.get("WOO_BASE_URL")
    or os.environ.get("WC_SITE")
    or os.environ.get("WC_URL")
)
WOO_CONSUMER_KEY = (
    os.environ.get("WOO_CONSUMER_KEY")
    or os.environ.get("WC_CK")
)
WOO_CONSUMER_SECRET = (
    os.environ.get("WOO_CONSUMER_SECRET")
    or os.environ.get("WC_CS")
)

if not (WOO_BASE_URL and WOO_CONSUMER_KEY and WOO_CONSUMER_SECRET):
    print(
        "[ERRO] Variáveis de ambiente não configuradas. "
        "Defina WOO_BASE_URL ou WC_SITE/WC_URL, "
        "WOO_CONSUMER_KEY ou WC_CK, "
        "e WOO_CONSUMER_SECRET ou WC_CS."
    )
    sys.exit(0)

API_BASE = WOO_BASE_URL.rstrip("/") + "/wp-json/wc/v3"


@dataclass
class AffiliateProduct:
    merchant_domain: str
    affiliate_url: str
    name: str
    price: float
    old_price: float
    currency: str
    category: str
    tags: str
    image_url: str
    description: str
    source: str

    @property
    def sku(self) -> str:
        prefix = self.merchant_domain.split(".")[0].upper() if self.merchant_domain else "AFF"
        base = slugify(self.name)[:40].upper() if self.name else "SEM_NOME"
        return f"AFF-{prefix}-{base}"

    @property
    def button_text(self) -> str:
        loja = self.merchant_domain.split(".")[0].capitalize() if self.merchant_domain else "loja"
        return f"Comprar na {loja}"


def read_feed(path: Path) -> List[AffiliateProduct]:
    if not path.exists():
        print(f"[ERRO] Arquivo de feed não encontrado: {path}")
        return []

    products: List[AffiliateProduct] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("affiliate_url"):
                continue

            def parse_price(v: str) -> float:
                if v is None:
                    return 0.0
                s = str(v).replace("\xa0", "").strip()
                if not s:
                    return 0.0
                # aceita formatos 849.00 ou 849,00
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(".", "").replace(",", ".")
                try:
                    return float(s)
                except ValueError:
                    return 0.0

            price = parse_price(row.get("price", ""))
            old_price = parse_price(row.get("old_price", ""))

            products.append(
                AffiliateProduct(
                    merchant_domain=(row.get("merchant_domain") or row.get("domínio_do_comerciante") or "").strip(),
                    affiliate_url=row.get("affiliate_url", "").strip(),
                    name=row.get("name", "").strip(),
                    price=price,
                    old_price=old_price,
                    currency=(row.get("currency") or row.get("moeda") or "BRL").strip(),
                    category=row.get("category", "").strip(),
                    tags=row.get("tags", "").strip(),
                    image_url=row.get("image_url", "").strip(),
                    description=row.get("description", "").strip(),
                    source=row.get("source", "").strip(),
                )
            )
    return products


def wc_request(method: str, path: str, **kwargs) -> requests.Response:
    url = API_BASE + path
    params = kwargs.pop("params", {})
    params.setdefault("consumer_key", WOO_CONSUMER_KEY)
    params.setdefault("consumer_secret", WOO_CONSUMER_SECRET)
    resp = requests.request(method, url, params=params, timeout=60, **kwargs)
    return resp


def ensure_product(p: AffiliateProduct) -> None:
    # Verifica se já existe produto com este SKU
    r = wc_request("GET", "/products", params={"sku": p.sku, "per_page": 1})
    if r.status_code not in (200, 201):
        print(f"[ERRO] Falha ao consultar produto {p.sku}: {r.status_code} {r.text}")
        return

    items = r.json()
    data: Dict[str, Any] = {
        "name": p.name,
        "type": "external",
        "regular_price": f"{(p.old_price or p.price):.2f}" if (p.old_price or p.price) else "",
        "sale_price": f"{(p.price or p.old_price):.2f}" if (p.price or p.old_price) else "",
        "external_url": p.affiliate_url,
        "button_text": p.button_text,
        "description": p.description or p.name,
        "short_description": p.name,
        "images": [{"src": p.image_url}] if p.image_url else [],
        "meta_data": [
            {"key": "_ctctech_source", "value": p.source or p.merchant_domain},
            {"key": "_ctctech_merchant_domain", "value": p.merchant_domain},
        ],
    }

    # tags simples (Woo cria se não existir)
    if p.tags:
        tag_names = [t.strip() for t in p.tags.split(",") if t.strip()]
        if tag_names:
            data["tags"] = [{"name": t} for t in tag_names]

    if items:
        prod_id = items[0]["id"]
        r2 = wc_request("PUT", f"/products/{prod_id}", json=data)
        if r2.status_code not in (200, 201):
            print(f"[ERRO] Falha ao atualizar {p.sku}: {r2.status_code} {r2.text}")
        else:
            print(f"[OK] Atualizado {p.sku} – {p.name}")
    else:
        data["sku"] = p.sku
        r2 = wc_request("POST", "/products", json=data)
        if r2.status_code not in (200, 201):
            print(f"[ERRO] Falha ao criar {p.sku}: {r2.status_code} {r2.text}")
        else:
            print(f"[OK] Criado {p.sku} – {p.name}")


def main() -> None:
    print(f"[INFO] Lendo feed: {FEED_PATH}")
    products = read_feed(FEED_PATH)
    if not products:
        print("[INFO] Nenhum produto válido encontrado no feed.")
        return

    print(f"[INFO] {len(products)} produto(s) no feed. Enviando para WooCommerce...")
    for p in products:
        try:
            ensure_product(p)
        except Exception as e:
            print(f"[ERRO] Exceção ao processar {p.sku}: {e}")


if __name__ == "__main__":
    main()
