from web_scraper.models import ItemRule
from web_scraper.parser import HtmlParser

SAMPLE_HTML = (
    "<html><body>"
    "<div class='product' data-id='101'>"
    "<h2 class='title'>  Laptop Pro 16  </h2>"
    "<span class='price'>$1,299.99</span>"
    "<a class='link' href='/products/101'>View Details</a>"
    "<img class='thumbnail' src='/images/laptop.png' />"
    "<span class='in-stock'>True</span>"
    "</div>"
    "<div class='product' data-id='102'>"
    "<h2 class='title'>Wireless Mouse</h2>"
    "<span class='price'>$49.50</span>"
    "<a class='link' href='/products/102'>View Details</a>"
    "<img class='thumbnail' src='/images/mouse.png' />"
    "<span class='in-stock'>false</span>"
    "</div>"
    "</body></html>"
)


def test_cast_value():
    parser = HtmlParser()
    assert parser.cast_value("123", "int") == 123
    assert parser.cast_value("$1,250", "int") == 1250
    assert parser.cast_value("$99.95", "float") == 99.95
    assert parser.cast_value("true", "bool") is True
    assert parser.cast_value("False", "bool") is False
    assert parser.cast_value("hello", "list") == ["hello"]
    assert parser.cast_value(None, "int", default=0) == 0


def test_extract_collection():
    parser = HtmlParser()
    rules = [
        ItemRule(name="item_id", selector="", extract="attr", attr_name="data-id", cast="int"),
        ItemRule(name="title", selector="h2.title", extract="text"),
        ItemRule(name="price", selector="span.price", extract="text", regex=r"[\d,.]+", cast="float"),
        ItemRule(name="url", selector="a.link", extract="href"),
        ItemRule(name="image", selector="img.thumbnail", extract="src"),
        ItemRule(name="available", selector="span.in-stock", extract="text", cast="bool"),
    ]

    items = parser.extract_collection(SAMPLE_HTML, "div.product", rules)
    assert len(items) == 2

    assert items[0]["item_id"] == 101
    assert items[0]["title"] == "Laptop Pro 16"
    assert items[0]["price"] == 1299.99
    assert items[0]["url"] == "/products/101"
    assert items[0]["image"] == "/images/laptop.png"
    assert items[0]["available"] is True

    assert items[1]["item_id"] == 102
    assert items[1]["title"] == "Wireless Mouse"
    assert items[1]["price"] == 49.50
    assert items[1]["available"] is False


def test_extract_single():
    parser = HtmlParser()
    rules = [
        ItemRule(name="first_title", selector="h2.title", extract="text"),
        ItemRule(name="first_price", selector="span.price", extract="text"),
    ]
    item = parser.extract_single(SAMPLE_HTML, rules)
    assert item["first_title"] == "Laptop Pro 16"
    assert item["first_price"] == "$1,299.99"


def test_query_selector():
    parser = HtmlParser()
    matches = parser.query_selector(SAMPLE_HTML, "div.product")
    assert len(matches) == 2
    assert matches[0]["tag"] == "div"
    assert matches[0]["attributes"].get("data-id") == "101"
    assert "Laptop Pro" in matches[0]["text"]
