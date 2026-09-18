from web_scraper.models import ItemRule, PaginationConfig, ScrapeJob

PRESETS: dict[str, ScrapeJob] = {
    "quotes": ScrapeJob(
        url="https://quotes.toscrape.com",
        container_selector="div.quote",
        rules=[
            ItemRule(name="quote", selector="span.text", extract="text"),
            ItemRule(name="author", selector="small.author", extract="text"),
            ItemRule(name="author_link", selector="span > a", extract="href"),
            ItemRule(name="tags", selector="div.tags", extract="text"),
        ],
        pagination=PaginationConfig(
            strategy="next_link",
            next_selector="li.next > a",
            max_pages=3,
        ),
        rate_limit_delay=0.5,
    ),
    "books": ScrapeJob(
        url="https://books.toscrape.com",
        container_selector="article.product_pod",
        rules=[
            ItemRule(name="title", selector="h3 > a", extract="attr", attr_name="title"),
            ItemRule(name="price", selector="p.price_color", extract="text", regex=r"[\d.]+", cast="float"),
            ItemRule(name="availability", selector="p.availability", extract="text"),
            ItemRule(name="rating", selector="p.star-rating", extract="attr", attr_name="class"),
            ItemRule(name="link", selector="h3 > a", extract="href"),
        ],
        pagination=PaginationConfig(
            strategy="next_link",
            next_selector="li.next > a",
            max_pages=2,
        ),
        rate_limit_delay=0.5,
    ),
    "hackernews": ScrapeJob(
        url="https://news.ycombinator.com",
        container_selector="tr.athing",
        rules=[
            ItemRule(name="rank", selector="span.rank", extract="text", regex=r"\d+", cast="int"),
            ItemRule(name="title", selector="span.titleline > a", extract="text"),
            ItemRule(name="url", selector="span.titleline > a", extract="href"),
        ],
        pagination=PaginationConfig(
            strategy="next_link",
            next_selector="a.morelink",
            max_pages=2,
        ),
        rate_limit_delay=1.0,
    ),
    "products": ScrapeJob(
        url="https://example.com/products",
        container_selector=".product-card",
        rules=[
            ItemRule(name="name", selector=".product-title", extract="text"),
            ItemRule(name="price", selector=".product-price", extract="text", regex=r"[\d.]+", cast="float"),
            ItemRule(name="image", selector="img.product-thumb", extract="src"),
            ItemRule(name="link", selector="a.product-link", extract="href"),
        ],
        pagination=PaginationConfig(
            strategy="page_param",
            page_param="page",
            start_page=1,
            max_pages=3,
        ),
        rate_limit_delay=0.5,
    ),
}


def list_presets() -> list[str]:
    return sorted(list(PRESETS.keys()))


def get_preset(name: str) -> ScrapeJob | None:
    preset = PRESETS.get(name.lower().strip())
    if preset is None:
        return None
    return ScrapeJob(
        url=preset.url,
        container_selector=preset.container_selector,
        rules=list(preset.rules),
        pagination=PaginationConfig(
            strategy=preset.pagination.strategy,
            next_selector=preset.pagination.next_selector,
            page_param=preset.pagination.page_param,
            start_page=preset.pagination.start_page,
            page_step=preset.pagination.page_step,
            offset_param=preset.pagination.offset_param,
            limit_param=preset.pagination.limit_param,
            start_offset=preset.pagination.start_offset,
            offset_step=preset.pagination.offset_step,
            max_pages=preset.pagination.max_pages,
            max_items=preset.pagination.max_items,
        ),
        headers=dict(preset.headers),
        cookies=dict(preset.cookies),
        timeout=preset.timeout,
        max_retries=preset.max_retries,
        backoff_factor=preset.backoff_factor,
        rate_limit_delay=preset.rate_limit_delay,
        rate_limit_jitter=preset.rate_limit_jitter,
        respect_robots_txt=preset.respect_robots_txt,
        use_cache=preset.use_cache,
        cache_ttl_seconds=preset.cache_ttl_seconds,
        user_agent=preset.user_agent,
    )
