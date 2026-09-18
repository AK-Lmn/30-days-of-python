from price_tracker.extractor import PriceExtractor

HTML_JSON_LD = """
<!DOCTYPE html>
<html>
<head>
    <title>Awesome Wireless Headphones</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Awesome Wireless Headphones",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "USD",
            "price": "199.99",
            "availability": "https://schema.org/InStock"
        }
    }
    </script>
</head>
<body>
    <h1>Awesome Wireless Headphones</h1>
</body>
</html>
"""

HTML_META_TAGS = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:title" content="Smart Fitness Watch" />
    <meta property="og:price:amount" content="149.50" />
    <meta property="og:price:currency" content="EUR" />
</head>
<body>
    <h1>Smart Fitness Watch</h1>
    <div class="availability">Temporarily out of stock</div>
</body>
</html>
"""

HTML_MICRODATA = """
<!DOCTYPE html>
<html>
<body>
    <h1>Mechanical Keyboard</h1>
    <div itemprop="price" content="89.99">89.99</div>
    <span itemprop="priceCurrency">GBP</span>
</body>
</html>
"""

HTML_HEURISTICS = """
<!DOCTYPE html>
<html>
<body>
    <h1>Gaming Mouse</h1>
    <div class="product-price">$49.95</div>
</body>
</html>
"""

HTML_CUSTOM_SELECTOR = """
<!DOCTYPE html>
<html>
<body>
    <h1>Ultra 4K Monitor</h1>
    <span id="special-deal-price" data-price="349.00">$349.00 USD</span>
</body>
</html>
"""


def test_extract_json_ld():
    extractor = PriceExtractor()
    result = extractor.extract(HTML_JSON_LD)
    assert result.success is True
    assert result.price == 199.99
    assert result.currency == "USD"
    assert result.in_stock is True
    assert result.title == "Awesome Wireless Headphones"


def test_extract_meta_tags():
    extractor = PriceExtractor()
    result = extractor.extract(HTML_META_TAGS)
    assert result.success is True
    assert result.price == 149.50
    assert result.currency == "EUR"
    assert result.in_stock is False
    assert result.title == "Smart Fitness Watch"


def test_extract_microdata():
    extractor = PriceExtractor()
    result = extractor.extract(HTML_MICRODATA)
    assert result.success is True
    assert result.price == 89.99
    assert result.currency == "GBP"
    assert result.in_stock is True


def test_extract_heuristics():
    extractor = PriceExtractor()
    result = extractor.extract(HTML_HEURISTICS)
    assert result.success is True
    assert result.price == 49.95
    assert result.currency == "USD"
    assert result.in_stock is True


def test_extract_custom_selector():
    extractor = PriceExtractor()
    result = extractor.extract(HTML_CUSTOM_SELECTOR, custom_selector="#special-deal-price")
    assert result.success is True
    assert result.price == 349.00
    assert result.currency == "USD"


def test_parse_price_text():
    extractor = PriceExtractor()
    assert extractor.parse_price_text("$1,299.99") == (1299.99, "USD")
    assert extractor.parse_price_text("€ 89,90") == (89.90, "EUR")
    assert extractor.parse_price_text("£45.00") == (45.00, "GBP")
    assert extractor.parse_price_text("¥5,000") == (5000.0, "JPY")
    assert extractor.parse_price_text("149.99 CAD") == (149.99, "CAD")
    assert extractor.parse_price_text("invalid") == (None, "USD")
    assert extractor.parse_price_text("") == (None, "USD")


def test_empty_html():
    extractor = PriceExtractor()
    result = extractor.extract("")
    assert result.success is False
    assert result.error == "Empty HTML document"
