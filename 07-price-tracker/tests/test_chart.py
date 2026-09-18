from price_tracker.chart import format_change, render_ascii_chart, render_sparkline


def test_render_sparkline():
    assert render_sparkline([]) == ""
    assert render_sparkline([50.0]) == "▅"
    assert render_sparkline([10.0, 10.0, 10.0]) == "▅▅▅"

    spark = render_sparkline([10.0, 20.0, 30.0, 40.0])
    assert len(spark) == 4
    assert spark[0] == " "
    assert spark[-1] == "█"


def test_render_ascii_chart():
    assert "No historical price data" in render_ascii_chart([])
    assert "Single data point" in render_ascii_chart([100.0])

    chart = render_ascii_chart([100.0, 90.0, 85.0, 80.0])
    assert "100.00" in chart
    assert "80.00" in chart
    assert "●" in chart


def test_format_change():
    assert "▼ -20.0%" in format_change(100.0, 80.0, "USD")
    assert "▲ +25.0%" in format_change(80.0, 100.0, "EUR")
    assert "─ 0.0%" in format_change(50.0, 50.0, "USD")
    assert "─ 0.0%" in format_change(None, 50.0, "USD")
