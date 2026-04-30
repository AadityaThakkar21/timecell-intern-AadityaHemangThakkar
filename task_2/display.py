"""
display.py
----------
Pure-stdlib terminal renderer.
Prints a clean, aligned table — no external formatting libraries needed.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fetchers import AssetPrice, FetchError

IST = timezone(timedelta(hours=5, minutes=30))

# ── Column definitions ────────────────────────────────────────────────────────
#   (header label, min width, alignment: '<' left / '>' right)
_COLUMNS = [
    ("Asset",     20, "<"),
    ("Price",     14, ">"),
    ("Currency",   9, "^"),
    ("Source",    14, "<"),
    ("Fetched At", 25, "<"),
]


def _col_widths(rows: list[tuple[str, ...]]) -> list[int]:
    """Return the max of header min-width and actual data width per column."""
    widths = [w for _, w, _ in _COLUMNS]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    return widths


def _divider(widths: list[int], left="├", mid="┼", right="┤", fill="─") -> str:
    return left + mid.join(fill * (w + 2) for w in widths) + right


def _row(cells: tuple[str, ...], widths: list[int], bold: bool = False) -> str:
    parts = []
    for cell, width, (_, _, align) in zip(cells, widths, _COLUMNS):
        parts.append(f" {cell:{align}{width}} ")
    line = "│" + "│".join(parts) + "│"
    return line


def render_table(
    prices: list[AssetPrice],
    errors: list[FetchError],
) -> None:
    """Print the full asset price table to stdout."""

    now_ist = datetime.now(tz=IST).strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"\n  Asset Prices — fetched at {now_ist}\n")

    if not prices and not errors:
        print("  (no data — all fetches were skipped)")
        return

    # Build data rows
    data_rows: list[tuple[str, ...]] = []
    for p in prices:
        data_rows.append((
            p.name,
            p.price_display(),
            p.currency,
            p.source,
            p.timestamp_display(),
        ))

    headers = tuple(h for h, _, _ in _COLUMNS)
    widths   = _col_widths(data_rows)

    top     = _divider(widths, "┌", "┬", "┐", "─")
    head_sep= _divider(widths, "╞", "╪", "╡", "═")
    mid_sep = _divider(widths, "├", "┼", "┤", "─")
    bottom  = _divider(widths, "└", "┴", "┘", "─")

    print("  " + top)
    print("  " + _row(headers, widths))
    print("  " + head_sep)
    for i, row in enumerate(data_rows):
        print("  " + _row(row, widths))
        if i < len(data_rows) - 1:
            print("  " + mid_sep)
    print("  " + bottom)

    # ── Error summary ─────────────────────────────────────────────────────────
    if errors:
        print(f"\n  ⚠  {len(errors)} fetch failure(s):\n")
        for err in errors:
            print(f"     • [{err.source}] {err.symbol} — {err.reason}")

    print()
