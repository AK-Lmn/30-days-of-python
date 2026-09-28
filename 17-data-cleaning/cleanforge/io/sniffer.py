import csv
from pathlib import Path


def detect_csv_dialect(sample: str) -> tuple[str, str, bool]:
    default_delimiter = ","
    default_quotechar = '"'
    default_has_header = True

    if not sample.strip():
        return default_delimiter, default_quotechar, default_has_header

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
        has_header = sniffer.has_header(sample)
        return dialect.delimiter, dialect.quotechar or default_quotechar, has_header
    except Exception:
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {
            ",": first_line.count(","),
            ";": first_line.count(";"),
            "\t": first_line.count("\t"),
            "|": first_line.count("|"),
        }
        best_delimiter = max(counts, key=counts.get)
        if counts[best_delimiter] == 0:
            best_delimiter = default_delimiter
        return best_delimiter, default_quotechar, default_has_header


def detect_encoding(file_path: Path) -> str:
    encodings_to_try = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
    return "utf-8"
