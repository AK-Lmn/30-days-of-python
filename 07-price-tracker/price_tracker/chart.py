SPARKLINE_CHARS: list[str] = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def render_sparkline(prices: list[float]) -> str:
    if not prices:
        return ""
    if len(prices) == 1:
        return "▅"

    min_p = min(prices)
    max_p = max(prices)
    price_range = max_p - min_p

    if price_range == 0:
        return "▅" * len(prices)

    num_levels = len(SPARKLINE_CHARS) - 1
    chars = []
    for p in prices:
        idx = int(((p - min_p) / price_range) * num_levels)
        idx = max(0, min(idx, num_levels))
        chars.append(SPARKLINE_CHARS[idx])

    return "".join(chars)


def render_ascii_chart(prices: list[float], height: int = 6, width: int = 40) -> str:
    if not prices:
        return "No historical price data."
    if len(prices) == 1:
        return f"Single data point: {prices[0]:.2f}"

    min_p = min(prices)
    max_p = max(prices)
    price_range = max_p - min_p

    sampled: list[float]
    if len(prices) > width:
        step = len(prices) / width
        sampled = [prices[int(i * step)] for i in range(width)]
    else:
        sampled = prices

    w = len(sampled)
    grid = [[" " for _ in range(w)] for _ in range(height)]

    if price_range == 0:
        mid_row = height // 2
        for x in range(w):
            grid[mid_row][x] = "─"
    else:
        for x, p in enumerate(sampled):
            ratio = (p - min_p) / price_range
            row = height - 1 - int(ratio * (height - 1))
            row = max(0, min(row, height - 1))
            grid[row][x] = "●"

    lines = []
    max_label_len = max(len(f"{max_p:.2f}"), len(f"{min_p:.2f}"))

    for row_idx, row in enumerate(grid):
        if row_idx == 0:
            prefix = f"{max_p:>{max_label_len}.2f} ┤"
        elif row_idx == height - 1:
            prefix = f"{min_p:>{max_label_len}.2f} ┤"
        else:
            prefix = f"{' ' * max_label_len} │"
        lines.append(prefix + "".join(row))

    bottom_axis = " " * max_label_len + " └" + "─" * w
    lines.append(bottom_axis)
    return "\n".join(lines)


def format_change(old_val: float | None, new_val: float | None, currency: str = "USD") -> str:
    if old_val is None or new_val is None or old_val == 0:
        return "─ 0.0%"

    diff = new_val - old_val
    pct = (diff / old_val) * 100

    if diff < 0:
        return f"▼ {pct:.1f}% (-{currency} {abs(diff):.2f})"
    elif diff > 0:
        return f"▲ +{pct:.1f}% (+{currency} {diff:.2f})"
    return "─ 0.0%"
