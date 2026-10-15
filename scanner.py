
import requests
from datetime import datetime, timezone

SPOT = 'https://data-api.binance.vision'
FUTURES = 'https://fapi.binance.com'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'KriptoRadar/2.0'})


def get_json(base, path, params=None):
    r = SESSION.get(base + path, params=params, timeout=20)
    print(f"API: {r.url}")
    print(f"Durum: {r.status_code}")
    print(f"Veri tipi: {r.headers.get('Content-Type')}")
    print(f"Yanıt: {r.text[:300]!r}")
    r.raise_for_status()
    return r.json()


def scan_market(name, base, prefix):
    tickers = get_json(base, prefix + '/ticker/24hr')
    exchange = get_json(base, prefix + '/exchangeInfo')
    active = {
        s['symbol'] for s in exchange['symbols']
        if s.get('status') == 'TRADING'
        and s.get('quoteAsset') == 'USDT'
        and s.get('baseAsset') not in {'USDT', 'USDC', 'FDUSD', 'TUSD', 'DAI', 'BUSD', 'USDE', 'USD1'}
        and (name == 'Spot' or s.get('contractType') == 'PERPETUAL')
    }
    liquid = sorted((t for t in tickers if t['symbol'] in active
                     and float(t.get('quoteVolume', 0)) >= 5_000_000
                     and -10 <= float(t.get('priceChangePercent', 0)) <= 12),
                    key=lambda t: float(t['quoteVolume']), reverse=True)[:60]
    matches = []
    for t in liquid:
        symbol = t['symbol']
        try:
            candles = get_json(base, prefix + '/klines',
                               {'symbol': symbol, 'interval': '1h', 'limit': 73})
            if len(candles) < 73:
                continue
            closed = candles[:-1]
            recent = closed[-24:]
            previous = closed[-48:-24]
            highs = [float(c[2]) for c in recent]
            lows = [float(c[3]) for c in recent]
            closes = [float(c[4]) for c in recent]
            volumes = [float(c[7]) for c in recent]
            prev_volumes = [float(c[7]) for c in previous]
            price = closes[-1]
            resistance = max(highs[:-1])
            width = (max(highs) - min(lows)) / price * 100
            vol_ratio = (sum(volumes[-3:]) / 3) / max(sum(prev_volumes) / 24, 1)
            distance = (resistance - price) / resistance * 100
            if width <= 10 and vol_ratio >= 1.5 and -1.5 <= distance <= 2:
                matches.append((symbol, width, vol_ratio, distance,
                                float(t['quoteVolume'])))
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            print(f'Atlandi: {name} {symbol}: {exc}')
    matches.sort(key=lambda x: (-x[2], abs(x[3])))
    print(f'\n{name}: {len(matches)} teknik aday (ilk 60 likit parite tarandi)')
    for symbol, width, ratio, distance, volume in matches[:15]:
        print(f'{symbol} | 24s aralik %{width:.1f} | hacim oranı {ratio:.1f}x '
              f'| dirence uzaklik %{distance:.1f} | 24s hacim {volume:,.0f} USDT')


def main():
    print('KRIPTO RADAR 2.0 -', datetime.now(timezone.utc).isoformat())
    print('UYARI: Seed/Monitoring ve delist etiketleri dogrulanmadi; alim sinyali degildir.')
    for name, base, prefix in [('Spot', SPOT, '/api/v3')]:
        try:
            scan_market(name, base, prefix)
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f'{name} taramasi basarisiz: {exc}')


if __name__ == '__main__':
    main()
