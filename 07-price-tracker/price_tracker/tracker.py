from datetime import datetime, timezone
import time
from price_tracker.config import DEFAULT_DROP_PERCENTAGE_ALERT
from price_tracker.db import Database
from price_tracker.extractor import PriceExtractor
from price_tracker.models import PriceAlert, PriceRecord, Product, ScrapeResult
from price_tracker.notifier import BaseNotifier, ConsoleNotifier
from price_tracker.scraper import WebScraper


class PriceTracker:
    def __init__(
        self,
        db: Database | None = None,
        scraper: WebScraper | None = None,
        extractor: PriceExtractor | None = None,
        notifier: BaseNotifier | None = None,
        min_drop_percentage: float = DEFAULT_DROP_PERCENTAGE_ALERT,
    ):
        self.db = db or Database()
        self.scraper = scraper or WebScraper()
        self.extractor = extractor or PriceExtractor()
        self.notifier = notifier or ConsoleNotifier()
        self.min_drop_percentage = min_drop_percentage

    def check_product(self, product_id: int) -> tuple[Product | None, list[PriceAlert], str | None]:
        product = self.db.get_product(product_id)
        if not product:
            return None, [], "Product not found"

        html, error = self.scraper.fetch_html(product.url)
        if error or not html:
            return product, [], error or "Failed to fetch webpage"

        result = self.extractor.extract(html, custom_selector=product.selector)
        if not result.success or result.price is None:
            return product, [], result.error or "Failed to extract price"

        alerts = self._process_price_update(product, result)
        return product, alerts, None

    def _process_price_update(self, product: Product, result: ScrapeResult) -> list[PriceAlert]:
        now_str = datetime.now(timezone.utc).isoformat()
        new_price = result.price
        if new_price is None or product.id is None:
            return []

        old_price = product.current_price
        old_stock = product.in_stock
        alerts: list[PriceAlert] = []

        record = PriceRecord(
            product_id=product.id,
            price=new_price,
            currency=result.currency,
            in_stock=result.in_stock,
            recorded_at=now_str,
        )
        self.db.add_price_record(record)

        if product.target_price is not None and new_price <= product.target_price:
            if old_price is None or old_price > product.target_price:
                diff = (product.target_price - new_price) if new_price < product.target_price else 0.0
                alerts.append(
                    PriceAlert(
                        product_id=product.id,
                        product_name=product.name,
                        alert_type="TARGET_REACHED",
                        old_price=old_price,
                        new_price=new_price,
                        target_price=product.target_price,
                        drop_amount=diff,
                        currency=result.currency,
                        triggered_at=now_str,
                        message=f"Hit target {result.currency} {product.target_price:.2f}",
                    )
                )

        if product.lowest_price is not None and new_price < product.lowest_price:
            drop_amt = round(product.lowest_price - new_price, 2)
            drop_pct = round((drop_amt / product.lowest_price) * 100, 2)
            alerts.append(
                PriceAlert(
                    product_id=product.id,
                    product_name=product.name,
                    alert_type="ALL_TIME_LOW",
                    old_price=product.lowest_price,
                    new_price=new_price,
                    target_price=product.target_price,
                    drop_amount=drop_amt,
                    drop_percentage=drop_pct,
                    currency=result.currency,
                    triggered_at=now_str,
                    message=f"New all-time low (dropped {drop_pct}% from prior low)",
                )
            )
        elif old_price is not None and new_price < old_price:
            drop_amt = round(old_price - new_price, 2)
            drop_pct = round((drop_amt / old_price) * 100, 2)
            if drop_pct >= self.min_drop_percentage:
                alerts.append(
                    PriceAlert(
                        product_id=product.id,
                        product_name=product.name,
                        alert_type="PRICE_DROP",
                        old_price=old_price,
                        new_price=new_price,
                        target_price=product.target_price,
                        drop_amount=drop_amt,
                        drop_percentage=drop_pct,
                        currency=result.currency,
                        triggered_at=now_str,
                        message=f"Price dropped by {drop_pct}% (-{result.currency} {drop_amt:.2f})",
                    )
                )

        if not old_stock and result.in_stock:
            alerts.append(
                PriceAlert(
                    product_id=product.id,
                    product_name=product.name,
                    alert_type="BACK_IN_STOCK",
                    old_price=old_price,
                    new_price=new_price,
                    target_price=product.target_price,
                    currency=result.currency,
                    triggered_at=now_str,
                    message="Product is back in stock",
                )
            )

        product.current_price = new_price
        product.currency = result.currency
        product.in_stock = result.in_stock
        product.last_checked = now_str
        product.updated_at = now_str

        if product.lowest_price is None or new_price < product.lowest_price:
            product.lowest_price = new_price
        if product.highest_price is None or new_price > product.highest_price:
            product.highest_price = new_price

        self.db.update_product(product)

        for alert in alerts:
            self.db.add_alert(alert)
            self.notifier.notify(alert)

        return alerts

    def check_all(
        self, tag: str | None = None, delay_seconds: float = 0.5
    ) -> list[tuple[Product, list[PriceAlert], str | None]]:
        products = self.db.list_products(tag=tag)
        results: list[tuple[Product, list[PriceAlert], str | None]] = []

        for i, prod in enumerate(products):
            if i > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)
            if prod.id is not None:
                updated_prod, alerts, error = self.check_product(prod.id)
                if updated_prod:
                    results.append((updated_prod, alerts, error))

        return results
