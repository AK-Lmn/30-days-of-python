from typing import Sequence

SPARK_CHARS: tuple[str, ...] = (" ", "▂", "▃", "▄", "▅", "▆", "▇", "█")


def render_sparkline(
    values: Sequence[float],
    min_val: float | None = None,
    max_val: float | None = None,
) -> str:
    if not values:
        return ""

    actual_min = min_val if min_val is not None else min(values)
    actual_max = max_val if max_val is not None else max(values)

    if actual_max <= actual_min:
        return SPARK_CHARS[3] * len(values)

    num_levels = len(SPARK_CHARS)
    range_val = actual_max - actual_min
    result = []

    for v in values:
        clamped = max(actual_min, min(v, actual_max))
        normalized = (clamped - actual_min) / range_val
        index = int(normalized * (num_levels - 1))
        index = max(0, min(index, num_levels - 1))
        result.append(SPARK_CHARS[index])

    return "".join(result)


def render_bar(
    percent: float,
    width: int = 20,
    fill_char: str = "■",
    empty_char: str = "□",
) -> str:
    clamped = max(0.0, min(percent, 100.0))
    filled_len = int(round((clamped / 100.0) * width))
    empty_len = width - filled_len
    return (fill_char * filled_len) + (empty_char * empty_len)


def format_bytes(num_bytes: float | int) -> str:
    val = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(val) < 1024.0:
            return f"{val:3.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} EB"


def format_rate(bytes_per_sec: float) -> str:
    return f"{format_bytes(bytes_per_sec)}/s"
