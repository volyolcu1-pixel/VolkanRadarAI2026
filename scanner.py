
import requests

url = "https://api.binance.com/api/v3/ticker/24hr"

try:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    coins = response.json()

    usdt_coins = [
        c for c in coins
        if c["symbol"].endswith("USDT")
    ]

    usdt_coins.sort(
        key=lambda c: float(c["quoteVolume"]),
        reverse=True
    )

    print("VOLKAN KRIPTO RADAR")

    for coin in usdt_coins[:10]:
        print(
            coin["symbol"],
            coin["lastPrice"],
            coin["priceChangePercent"] + "%"
        )

except requests.RequestException as e:
    print("Hata:", e)

