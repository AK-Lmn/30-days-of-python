import json
import re
from bs4 import BeautifulSoup
from price_tracker.config import CURRENCY_SYMBOLS
from price_tracker.models import ScrapeResult

COMMON_PRICE_SELECTORS: list[str] = [
    ".price",
    ".product-price",
    ".price_color",
    "p.price_color",
    ".current-price",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    ".a-price .a-offscreen",
    "span.a-price-whole",
    ".price-current",
    ".offer-price",
    "[data-test='product-price']",
    ".pdp-price",
]

OUT_OF_STOCK_KEYWORDS: list[str] = [
    "out of stock",
    "sold out",
    "currently unavailable",
    "temporarily out of stock",
    "schema.org/outofstock",
    "schema.org/discontinued",
]

IN_STOCK_KEYWORDS: list[str] = [
    "in stock",
    "available",
    "schema.org/instock",
    "schema.org/onlineonly",
    "schema.org/limitedavailability",
]


class PriceExtractor:
    def extract(self, html: str, custom_selector: str = "") -> ScrapeResult:
        if not html:
            return ScrapeResult(success=False, error="Empty HTML document")

        soup = BeautifulSoup(html, "html.parser")
        title = self._extract_title(soup)
        stock_status = self._extract_stock(soup)

        if custom_selector:
            selected_price, selected_currency = self._extract_by_selector(soup, custom_selector)
            if selected_price is not None:
                return ScrapeResult(
                    success=True,
                    price=selected_price,
                    currency=selected_currency,
                    in_stock=stock_status,
                    title=title,
                )

        ld_price, ld_currency, ld_stock, ld_title = self._extract_json_ld(soup)
        if ld_price is not None:
            return ScrapeResult(
                success=True,
                price=ld_price,
                currency=ld_currency,
                in_stock=ld_stock if ld_stock is not None else stock_status,
                title=ld_title or title,
            )

        meta_price, meta_currency = self._extract_meta(soup)
        if meta_price is not None:
            return ScrapeResult(
                success=True,
                price=meta_price,
                currency=meta_currency,
                in_stock=stock_status,
                title=title,
            )

        micro_price, micro_currency = self._extract_microdata(soup)
        if micro_price is not None:
            return ScrapeResult(
                success=True,
                price=micro_price,
                currency=micro_currency,
                in_stock=stock_status,
                title=title,
            )

        heuristic_price, heuristic_currency = self._extract_heuristics(soup)
        if heuristic_price is not None:
            return ScrapeResult(
                success=True,
                price=heuristic_price,
                currency=heuristic_currency,
                in_stock=stock_status,
                title=title,
            )

        return ScrapeResult(
            success=False,
            title=title,
            in_stock=stock_status,
            error="Could not identify price using any strategy",
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return str(og_title.get("content")).strip()

        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            return h1.get_text(strip=True)

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        return ""

    def _extract_by_selector(self, soup: BeautifulSoup, selector: str) -> tuple[float | None, str]:
        try:
            element = soup.select_one(selector)
            if not element:
                return None, "USD"

            raw_text = element.get("content") or element.get("value") or element.get_text(strip=True)
            return self.parse_price_text(str(raw_text))
        except Exception:
            return None, "USD"

    def _extract_json_ld(self, soup: BeautifulSoup) -> tuple[float | None, str, bool | None, str]:
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "{}")
                extracted = self._parse_json_ld_node(data)
                if extracted[0] is not None:
                    return extracted
            except Exception:
                continue
        return None, "USD", None, ""

    def _parse_json_ld_node(self, node: object) -> tuple[float | None, str, bool | None, str]:
        if isinstance(node, list):
            for item in node:
                res = self._parse_json_ld_node(item)
                if res[0] is not None:
                    return res
            return None, "USD", None, ""

        if not isinstance(node, dict):
            return None, "USD", None, ""

        if "@graph" in node and isinstance(node["@graph"], list):
            for item in node["@graph"]:
                res = self._parse_json_ld_node(item)
                if res[0] is not None:
                    return res

        node_type = str(node.get("@type", "")).lower()
        title = str(node.get("name", "")).strip()

        if "product" in node_type or "offer" in node_type:
            offers = node.get("offers", node if "offer" in node_type else None)
            if offers:
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    raw_price = offers.get("price") or offers.get("lowPrice")
                    currency = str(offers.get("priceCurrency", "USD")).upper()
                    availability = str(offers.get("availability", "")).lower()
                    stock: bool | None = None
                    if any(term in availability for term in ["instock", "onlineonly"]):
                        stock = True
                    elif any(term in availability for term in ["outofstock", "discontinued"]):
                        stock = False

                    if raw_price is not None:
                        parsed_val = self._clean_number(str(raw_price))
                        if parsed_val is not None:
                            return parsed_val, currency, stock, title

        return None, "USD", None, title

    def _extract_meta(self, soup: BeautifulSoup) -> tuple[float | None, str]:
        for prop in ["product:price:amount", "og:price:amount"]:
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                price = self._clean_number(str(tag.get("content")))
                if price is not None:
                    currency_tag = soup.find("meta", property=prop.replace(":amount", ":currency"))
                    currency = "USD"
                    if currency_tag and currency_tag.get("content"):
                        currency = str(currency_tag.get("content")).upper().strip()
                    return price, currency

        itemprop_price = soup.find("meta", itemprop="price")
        if itemprop_price and itemprop_price.get("content"):
            price = self._clean_number(str(itemprop_price.get("content")))
            if price is not None:
                currency_elem = soup.find("meta", itemprop="priceCurrency")
                currency = str(currency_elem.get("content", "USD")).upper() if currency_elem else "USD"
                return price, currency

        return None, "USD"

    def _extract_microdata(self, soup: BeautifulSoup) -> tuple[float | None, str]:
        elem = soup.find(attrs={"itemprop": "price"})
        if elem:
            raw_text = elem.get("content") or elem.get_text(strip=True)
            price, currency = self.parse_price_text(str(raw_text))
            if price is not None:
                curr_elem = soup.find(attrs={"itemprop": "priceCurrency"})
                if curr_elem:
                    currency = (curr_elem.get("content") or curr_elem.get_text(strip=True)).upper()
                return price, currency
        return None, "USD"

    def _extract_heuristics(self, soup: BeautifulSoup) -> tuple[float | None, str]:
        for selector in COMMON_PRICE_SELECTORS:
            elem = soup.select_one(selector)
            if elem:
                price, currency = self.parse_price_text(elem.get_text(strip=True))
                if price is not None:
                    return price, currency
        return None, "USD"

    def _extract_stock(self, soup: BeautifulSoup) -> bool:
        body_text = soup.get_text(separator=" ", strip=True).lower()
        for kw in OUT_OF_STOCK_KEYWORDS:
            if kw in body_text:
                return False
        return True

    def parse_price_text(self, text: str) -> tuple[float | None, str]:
        if not text:
            return None, "USD"

        currency = "USD"
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in text:
                currency = code
                break
        else:
            code_match = re.search(r"\b([A-Z]{3})\b", text)
            if code_match and code_match.group(1) in ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "INR", "CHF"]:
                currency = code_match.group(1)

        cleaned_val = self._clean_number(text)
        return cleaned_val, currency

    def _clean_number(self, text: str) -> float | None:
        match = re.search(r"[\d\s.,]+", text)
        if not match:
            return None

        num_str = match.group(0).strip()
        num_str = num_str.replace(" ", "")

        if not re.search(r"\d", num_str):
            return None

        if "." in num_str and "," in num_str:
            if num_str.rfind(",") > num_str.rfind("."):
                num_str = num_str.replace(".", "").replace(",", ".")
            else:
                num_str = num_str.replace(",", "")
        elif "," in num_str:
            parts = num_str.split(",")
            if len(parts[-1]) == 2:
                num_str = "".join(parts[:-1]) + "." + parts[-1]
            else:
                num_str = "".join(parts)

        try:
            val = float(num_str)
            return round(val, 2)
        except ValueError:
            return None
