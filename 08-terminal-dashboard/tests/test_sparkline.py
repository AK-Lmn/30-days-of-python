from terminal_dashboard.sparkline import format_bytes, format_rate, render_bar, render_sparkline


def test_render_sparkline_empty():
    assert render_sparkline([]) == ""


def test_render_sparkline_single():
    res = render_sparkline([50.0])
    assert len(res) == 1
    assert res == "▄"


def test_render_sparkline_uniform():
    res = render_sparkline([10.0, 10.0, 10.0])
    assert res == "▄▄▄"


def test_render_sparkline_ascending():
    res = render_sparkline([0.0, 50.0, 100.0])
    assert len(res) == 3
    assert res[0] == " "
    assert res[-1] == "█"


def test_render_sparkline_with_bounds():
    res = render_sparkline([0.0, 100.0], min_val=0.0, max_val=100.0)
    assert res[0] == " "
    assert res[1] == "█"


def test_render_bar():
    assert render_bar(0.0, width=10, fill_char="*", empty_char="-") == "----------"
    assert render_bar(100.0, width=10, fill_char="*", empty_char="-") == "**********"
    assert render_bar(50.0, width=10, fill_char="*", empty_char="-") == "*****-----"
    assert render_bar(150.0, width=5, fill_char="*", empty_char="-") == "*****"
    assert render_bar(-10.0, width=5, fill_char="*", empty_char="-") == "-----"


def test_format_bytes():
    assert "500.0 B" in format_bytes(500)
    assert "1.0 KB" in format_bytes(1024)
    assert "1.0 MB" in format_bytes(1024 * 1024)
    assert "1.0 GB" in format_bytes(1024 * 1024 * 1024)
    assert "1.0 TB" in format_bytes(1024 * 1024 * 1024 * 1024)


def test_format_rate():
    assert format_rate(1024) == "1.0 KB/s"
    assert format_rate(5 * 1024 * 1024) == "5.0 MB/s"
