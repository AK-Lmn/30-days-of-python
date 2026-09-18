import re
from typing import Any
from bs4 import BeautifulSoup, Tag
from web_scraper.models import ItemRule


class HtmlParser:
    def __init__(self, parser_backend: str = "html.parser") -> None:
        self.parser_backend = parser_backend

    def parse_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, self.parser_backend)

    def cast_value(self, value: Any, target_type: str, default: Any = None) -> Any:
        if value is None:
            return default

        try:
            if target_type == "int":
                clean_num = re.sub(r"[^\d-]", "", str(value))
                return int(clean_num) if clean_num else default
            elif target_type == "float":
                clean_float = re.sub(r"[^\d.-]", "", str(value))
                return float(clean_float) if clean_float else default
            elif target_type == "bool":
                val_str = str(value).strip().lower()
                return val_str in ("true", "1", "yes", "y", "t")
            elif target_type == "list":
                if isinstance(value, list):
                    return value
                return [str(value).strip()]
            return str(value)
        except Exception:
            return default

    def extract_field_value(self, element: Tag, rule: ItemRule) -> Any:
        target_node = element.select_one(rule.selector) if rule.selector else element
        if target_node is None:
            return rule.default

        raw_val: Any = None
        if rule.extract == "text":
            raw_val = target_node.get_text(separator=" ", strip=rule.strip)
        elif rule.extract == "html":
            raw_val = str(target_node)
        elif rule.extract == "href":
            raw_val = target_node.get("href", "")
        elif rule.extract == "src":
            raw_val = target_node.get("src", "")
        elif rule.extract == "attr":
            attr = rule.attr_name or ""
            raw_val = target_node.get(attr, "")
        else:
            raw_val = target_node.get(rule.extract, target_node.get_text(strip=rule.strip))

        if raw_val is None:
            return rule.default

        if isinstance(raw_val, list):
            raw_val = " ".join(str(item) for item in raw_val)
        else:
            raw_val = str(raw_val)

        if rule.strip:
            raw_val = re.sub(r"\s+", " ", raw_val).strip()

        if rule.regex:
            match = re.search(rule.regex, raw_val)
            if match:
                groups = match.groups()
                raw_val = groups[0] if groups else match.group(0)
            else:
                return rule.default

        return self.cast_value(raw_val, rule.cast, rule.default)

    def extract_item(self, element: Tag, rules: list[ItemRule]) -> dict[str, Any]:
        item_data: dict[str, Any] = {}
        for rule in rules:
            item_data[rule.name] = self.extract_field_value(element, rule)
        return item_data

    def extract_collection(
        self,
        html: str,
        container_selector: str,
        rules: list[ItemRule],
    ) -> list[dict[str, Any]]:
        soup = self.parse_soup(html)
        containers = soup.select(container_selector)
        records: list[dict[str, Any]] = []

        for container in containers:
            record = self.extract_item(container, rules)
            records.append(record)

        return records

    def extract_single(self, html: str, rules: list[ItemRule]) -> dict[str, Any]:
        soup = self.parse_soup(html)
        return self.extract_item(soup, rules)

    def query_selector(
        self,
        html: str,
        selector: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        soup = self.parse_soup(html)
        matches = soup.select(selector)
        results: list[dict[str, Any]] = []

        for match in matches[:limit]:
            results.append(
                {
                    "tag": match.name,
                    "text": match.get_text(separator=" ", strip=True)[:100],
                    "html_snippet": str(match)[:150],
                    "attributes": {k: v for k, v in match.attrs.items() if isinstance(v, (str, list))},
                }
            )

        return results
