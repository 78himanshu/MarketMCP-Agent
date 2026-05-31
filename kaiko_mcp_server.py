from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

BASE_URL = "https://reference-data-api.kaiko.io/v1"
KAIKO_API_KEY = os.getenv("KAIKO_API_KEY", "").strip()

mcp = FastMCP(
    name="Kaiko Reference Data MCP",
    instructions=(
        "Provides read-only tools over Kaiko Reference Data. "
        "Use these tools to answer questions about available exchanges, "
        "instruments, instrument classes, and trade availability windows."
    ),
)

session = requests.Session()
session.headers.update({"Accept": "application/json"})
if KAIKO_API_KEY:
    session.headers.update({"X-Api-Key": KAIKO_API_KEY})


def _request_kaiko(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Make a GET request to the Kaiko Reference Data API and return parsed JSON.
    """
    url = f"{BASE_URL}{path}"
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _fetch_paginated(
    path: str,
    params: dict[str, Any] | None = None,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """
    Fetch up to max_pages of results using Kaiko continuation_token pagination.
    """
    all_rows: list[dict[str, Any]] = []
    working_params = dict(params or {})

    for _ in range(max_pages):
        payload = _request_kaiko(path, working_params)
        rows = payload.get("data", [])
        if isinstance(rows, list):
            all_rows.extend(rows)

        continuation_token = payload.get("continuation_token")
        if not continuation_token:
            break

        working_params["continuation_token"] = continuation_token

    return all_rows


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


@mcp.tool
def list_exchanges(search: str | None = None, limit: int = 50) -> dict[str, Any]:
    """
    Return available Kaiko exchanges, optionally filtered by a search string.
    """
    data = _request_kaiko("/exchanges")
    rows = data.get("data", [])

    query = _normalize_text(search)
    if query:
        rows = [
            row
            for row in rows
            if query in _normalize_text(row.get("name"))
            or query in _normalize_text(row.get("code"))
            or query in _normalize_text(row.get("kaiko_legacy_slug"))
        ]

    rows = rows[: max(1, limit)]

    return {
        "count": len(rows),
        "exchanges": rows,
    }


@mcp.tool
def list_instruments(
    exchange_code: str | None = None,
    base_asset: str | None = None,
    quote_asset: str | None = None,
    instrument_code: str | None = None,
    instrument_class: str | None = None,
    trade_start_timestamp: str | None = None,
    trade_end_timestamp: str | None = None,
    limit: int = 50,
    max_pages: int = 3,
) -> dict[str, Any]:
    """
    Return Kaiko instruments (exchange trading pairs), with optional filters.
    """
    params: dict[str, Any] = {"limit": max(1, min(limit, 100))}

    if exchange_code:
        params["exchange_code"] = exchange_code.strip().lower()
    if base_asset:
        params["base_asset"] = base_asset.strip().lower()
    if quote_asset:
        params["quote_asset"] = quote_asset.strip().lower()
    if instrument_code:
        params["code"] = instrument_code.strip().lower()
    if instrument_class:
        params["class"] = instrument_class.strip().lower()
    if trade_start_timestamp:
        params["trade_start_timestamp"] = trade_start_timestamp.strip()
    if trade_end_timestamp:
        params["trade_end_timestamp"] = trade_end_timestamp.strip()

    rows = _fetch_paginated("/instruments", params=params, max_pages=max_pages)

    return {
        "count": len(rows),
        "instruments": rows[:limit],
    }


@mcp.tool
def get_last_trade_info(
    exchange_code: str,
    base_asset: str | None = None,
    quote_asset: str | None = None,
    instrument_code: str | None = None,
) -> dict[str, Any]:
    """
    Return the best matching instrument and its last known trade availability info.
    Useful for questions like 'When was X last traded on Coinbase?'
    """
    if not exchange_code or not exchange_code.strip():
        raise ValueError("exchange_code is required")

    params: dict[str, Any] = {
        "exchange_code": exchange_code.strip().lower(),
        "limit": 100,
    }

    if instrument_code:
        params["code"] = instrument_code.strip().lower()
    if base_asset:
        params["base_asset"] = base_asset.strip().lower()
    if quote_asset:
        params["quote_asset"] = quote_asset.strip().lower()

    rows = _fetch_paginated("/instruments", params=params, max_pages=2)

    if not rows:
        return {
            "found": False,
            "message": "No matching instrument was found.",
        }

    def sort_key(row: dict[str, Any]) -> tuple[int, int]:
        end_ts = row.get("trade_end_timestamp")
        start_ts = row.get("trade_start_timestamp")
        ongoing_bonus = 1 if end_ts is None else 0
        safe_end = end_ts if isinstance(end_ts, int) else -1
        safe_start = start_ts if isinstance(start_ts, int) else -1
        return (ongoing_bonus, safe_end if safe_end != -1 else safe_start)

    best = sorted(rows, key=sort_key, reverse=True)[0]

    return {
        "found": True,
        "instrument": {
            "code": best.get("code"),
            "class": best.get("class"),
            "exchange_code": best.get("exchange_code"),
            "exchange_pair_code": best.get("exchange_pair_code"),
            "base_asset": best.get("base_asset"),
            "quote_asset": best.get("quote_asset"),
            "trade_start_time": best.get("trade_start_time"),
            "trade_end_time": best.get("trade_end_time"),
            "trade_start_timestamp": best.get("trade_start_timestamp"),
            "trade_end_timestamp": best.get("trade_end_timestamp"),
            "trade_count": best.get("trade_count"),
        },
        "interpretation": (
            "trade_end_time is null if the instrument is still active; "
            "otherwise it indicates the last available trade time in Kaiko's dataset."
        ),
    }


@mcp.tool
def list_major_derivatives_exchanges(limit: int = 20) -> dict[str, Any]:
    """
    Identify exchanges that have derivatives instruments available by scanning
    Kaiko instruments and grouping exchanges with future / perpetual-future / option classes.
    """
    derivative_classes = {"future", "perpetual-future", "option"}
    rows = _fetch_paginated("/instruments", params={"limit": 100}, max_pages=5)

    summary: dict[str, dict[str, Any]] = {}

    for row in rows:
        instrument_class = str(row.get("class") or "").strip().lower()
        if instrument_class not in derivative_classes:
            continue

        exch = str(row.get("exchange_code") or "").strip().lower()
        if not exch:
            continue

        if exch not in summary:
            summary[exch] = {
                "exchange_code": exch,
                "instrument_classes": set(),
                "example_instruments": [],
                "instrument_count_seen": 0,
            }

        summary[exch]["instrument_classes"].add(instrument_class)
        summary[exch]["instrument_count_seen"] += 1

        if len(summary[exch]["example_instruments"]) < 5:
            summary[exch]["example_instruments"].append(row.get("code"))

    result = []
    for exch, info in summary.items():
        result.append(
            {
                "exchange_code": exch,
                "instrument_classes": sorted(info["instrument_classes"]),
                "instrument_count_seen": info["instrument_count_seen"],
                "example_instruments": info["example_instruments"],
            }
        )

    result.sort(key=lambda x: x["instrument_count_seen"], reverse=True)

    return {
        "count": min(len(result), limit),
        "major_derivatives_exchanges": result[:limit],
        "note": (
            "This is derived from instruments currently visible through the "
            "Kaiko reference-data instruments endpoint."
        ),
    }


if __name__ == "__main__":
    mcp.run()