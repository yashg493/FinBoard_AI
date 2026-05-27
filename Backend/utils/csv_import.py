"""
CSV Import — Parse and import portfolio holdings from broker-exported CSV/XLSX files.
Supports:
  - Zerodha Console XLSX/CSV  (console.zerodha.com → Portfolio → Holdings → XLSX)
  - Groww CSV export
  - INDmoney PDF → CSV (converted manually)
  - Generic CSV (symbol, quantity, avg_cost columns)

This is completely FREE — no API keys or subscriptions needed.
"""
import csv
import io
import logging
from typing import Optional

logger = logging.getLogger("boardroom-ai")


class CSVImportResult:
    def __init__(self):
        self.holdings: list[dict] = []
        self.skipped:  list[str]  = []
        self.errors:   list[str]  = []
        self.broker_detected: str = "unknown"


def _clean_num(val: str) -> float:
    """Strip ₹, commas, spaces and convert to float."""
    try:
        return float(str(val).replace("₹", "").replace(",", "").replace(" ", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _detect_broker(headers: list[str]) -> str:
    """Detect which broker's CSV format this is from the column headers."""
    headers_lower = {h.lower().strip() for h in headers}

    if "instrument" in headers_lower and "buy average" in headers_lower:
        return "zerodha"
    if "stock" in headers_lower and "average cost" in headers_lower:
        return "groww"
    if "symbol" in headers_lower and "avg. cost" in headers_lower:
        return "indmoney"
    if "scrip name" in headers_lower or "scripname" in headers_lower:
        return "angel"
    if "trading symbol" in headers_lower and "average price" in headers_lower:
        return "upstox"
    # Generic fallback
    if any(h in headers_lower for h in ("symbol", "ticker", "stock symbol")):
        return "generic"
    return "unknown"


def parse_zerodha_csv(rows: list[dict]) -> list[dict]:
    """
    Parse Zerodha Console Holdings XLSX/CSV.
    Columns: Instrument, Qty., Qty. (Free), Qty. (Pledged), Avg. cost, LTP,
             Cur. val, P&L, Net chg., Day chg.
    """
    holdings = []
    for row in rows:
        symbol = (row.get("Instrument") or row.get("instrument") or "").strip()
        if not symbol or symbol.lower() in ("instrument", "total", ""):
            continue

        qty       = _clean_num(row.get("Qty.") or row.get("Qty") or row.get("qty") or "0")
        avg_cost  = _clean_num(row.get("Avg. cost") or row.get("Avg cost") or row.get("avg cost") or "0")

        if qty <= 0 or avg_cost <= 0:
            continue

        holdings.append({
            "symbol":     symbol.upper(),
            "quantity":   qty,
            "avg_cost":   avg_cost,
            "asset_type": "equity",
            "exchange":   "NSE",
        })
    return holdings


def parse_groww_csv(rows: list[dict]) -> list[dict]:
    """
    Parse Groww portfolio CSV export.
    Columns: Stock, Quantity, Average Cost, Current Price, Current Value, P&L
    """
    holdings = []
    for row in rows:
        symbol = (row.get("Stock") or row.get("stock") or "").strip()
        if not symbol:
            continue

        qty      = _clean_num(row.get("Quantity") or row.get("quantity") or "0")
        avg_cost = _clean_num(row.get("Average Cost") or row.get("average cost") or "0")

        if qty <= 0:
            continue

        holdings.append({
            "symbol":     symbol.upper(),
            "quantity":   qty,
            "avg_cost":   avg_cost,
            "asset_type": "equity",
            "exchange":   "NSE",
        })
    return holdings


def parse_generic_csv(rows: list[dict], headers: list[str]) -> list[dict]:
    """
    Fallback parser for generic CSV with symbol/quantity/cost columns.
    Tries common column name variants.
    """
    SYMBOL_KEYS = ["symbol", "ticker", "stock", "instrument", "scrip", "trading symbol", "stock symbol"]
    QTY_KEYS    = ["quantity", "qty", "qty.", "shares", "units"]
    COST_KEYS   = ["avg cost", "avg. cost", "average cost", "average price", "buy avg", "buy average",
                   "avg price", "purchase price", "invested price"]

    def find_val(row: dict, keys: list[str]) -> str:
        for k in keys:
            for rk, rv in row.items():
                if rk.lower().strip() == k:
                    return str(rv)
        return ""

    holdings = []
    for row in rows:
        symbol   = find_val(row, SYMBOL_KEYS).strip().upper()
        qty      = _clean_num(find_val(row, QTY_KEYS))
        avg_cost = _clean_num(find_val(row, COST_KEYS))

        if not symbol or qty <= 0:
            continue

        holdings.append({
            "symbol":     symbol,
            "quantity":   qty,
            "avg_cost":   avg_cost,
            "asset_type": "equity",
            "exchange":   "NSE",
        })
    return holdings


def parse_csv_content(csv_text: str) -> CSVImportResult:
    """
    Main entry point — auto-detect broker format and parse CSV text.
    Returns CSVImportResult with holdings list and any errors/warnings.
    """
    result = CSVImportResult()

    try:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        rows   = list(reader)
        if not rows:
            result.errors.append("CSV file is empty or has no data rows.")
            return result

        headers = list(rows[0].keys())
        broker  = _detect_broker(headers)
        result.broker_detected = broker
        logger.info(f"[csv_import] Detected broker format: {broker} | {len(rows)} rows | headers: {headers[:6]}")

        if broker == "zerodha":
            result.holdings = parse_zerodha_csv(rows)
        elif broker == "groww":
            result.holdings = parse_groww_csv(rows)
        else:
            # Generic fallback — works for most formats
            result.holdings = parse_generic_csv(rows, headers)

        # Validate
        valid = []
        for h in result.holdings:
            if h["avg_cost"] <= 0:
                result.skipped.append(f"{h['symbol']} — avg cost is 0 (will use live price)")
                h["avg_cost"] = 0.01   # placeholder; yfinance will give LTP
            valid.append(h)
        result.holdings = valid

    except Exception as e:
        result.errors.append(f"Parse error: {str(e)}")
        logger.error(f"[csv_import] Error parsing CSV: {e}")

    return result
