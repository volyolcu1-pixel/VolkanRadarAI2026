
import requests
from datetime import datetime, timezone

URL = "https://data-api.binance.vision/api/v3/ticker/24hr"

def scan():
    response = requests.get(URL, timeout=20)
    response.raise_for_status()
    coins = response.json()

    results = []

    for coin in coins:
        symbol = coin.get("symbol", "")

        if not symbol.endswith("USDT"):
            continue

        volume = float(coin.get("quoteVolume", 0))
        change = float(coin.get("priceChangePercent", 0))

        if volume < 5_000_000:
            continue

        if change > 15 or change < -10:
            continue

        results.append((symbol, change, volume))

    results.sort(key=lambda x: x[2], reverse=True)

    print("VOLKAN KRIPTO RADAR")
    print("Tarama:", datetime.now(timezone.utc).isoformat())

    for symbol, change, volume in results[:20]:
        print(
            f"{symbol} | Degisim: %{change:.2f} "
            f"| 24s Hacim: {volume:,.0f} USDT"
        )

if __name__ == "__main__":
    scan()
