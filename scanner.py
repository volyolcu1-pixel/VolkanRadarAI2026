import json
from datetime import datetime, timezone
import requests

SPOT = "https://data-api.binance.vision"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "KriptoRadar/2.1"})

EXCLUDED = {
   "TSLA", "TSLAB", "TSLAUSDT", 
    "USDT", "USDC", "FDUSD", "TUSD", "DAI", "BUSD",
    "USDE", "USD1", "RLUSD", "BFUSD", "USDD", "PYUSD",
    "EUR", "EURC", "EURI", "AEUR", "WBTC", "WBETH",
    "BETH", "ETHFI", "USDP", "USTC", "LUSD"
}

def get_json(path, params=None):
    r = SESSION.get(SPOT + path, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def scan():
    exchange = get_json("/api/v3/exchangeInfo")
    tickers = get_json("/api/v3/ticker/24hr")

    active = set()
    for s in exchange["symbols"]:
        base = s.get("baseAsset", "")
        if (
            s.get("status") == "TRADING"
            and s.get("quoteAsset") == "USDT"
            and s.get("isSpotTradingAllowed", True)
            and base not in EXCLUDED
            and not base.endswith(("UP", "DOWN", "BULL", "BEAR"))
        ):
            active.add(s["symbol"])

    liquid = sorted(
        (
            t for t in tickers
            if t["symbol"] in active
            and float(t.get("quoteVolume", 0)) >= 5000000
            and -10 <= float(t.get("priceChangePercent", 0)) <= 12
        ),
        key=lambda t: float(t["quoteVolume"]),
        reverse=True
    )[:100]

    results = []
    for t in liquid:
        symbol = t["symbol"]
        try:
            candles = get_json(
                "/api/v3/klines",
                {"symbol": symbol, "interval": "1h", "limit": 73}
            )
            if len(candles) < 73:
                continue

            closed = candles[:-1]
            recent = closed[-24:]
            previous = closed[-48:-24]

            highs = [float(c[2]) for c in recent]
            lows = [float(c[3]) for c in recent]
            closes = [float(c[4]) for c in recent]
            price = closes[-1]
            resistance = max(highs[:-1])

            width = (max(highs) - min(lows)) / price * 100
            previous_vol = sum(float(c[7]) for c in previous) / 24
            last3_vol = sum(float(c[7]) for c in recent[-3:]) / 3
            ratio = last3_vol / max(previous_vol, 0.000001)
            distance = (resistance - price) / resistance * 100

            if width <= 10 and ratio >= 1.5 and -1.5 <= distance <= 2:
                results.append({
                    "market": "Spot",
                    "symbol": symbol,
                    "width_pct": round(width, 3),
                    "volume_ratio": round(ratio, 3),
                    "distance_to_resistance_pct": round(distance, 3),
                    "volume_usdt_24h": round(float(t["quoteVolume"]), 2),
                    "risk_status": "Seed/Monitoring/delist kontrol edilmedi"
                })
        except (requests.RequestException, ValueError, KeyError,
                IndexError, TypeError, ZeroDivisionError) as e:
            print("Atlandi:", symbol, str(e))

    results.sort(key=lambda x: (-x["volume_ratio"],
                                abs(x["distance_to_resistance_pct"])))
    return results

def main():
    report = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "candidates": [],
        "errors": []
    }
    try:
        report["candidates"] = scan()
        report["status"] = "ok"
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        report["errors"].append(str(e))

    with open("radar.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Tarama durumu:", report["status"])
    print("Bulunan aday:", len(report["candidates"]))
    for c in report["candidates"][:15]:
        print(c["symbol"], "Hacim:", c["volume_ratio"], "x")

    if report["status"] != "ok":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
