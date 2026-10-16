import json
from datetime import datetime, timezone
import requests

MARKETS = [
    ('Spot', 'https://data-api.binance.vision', '/api/v3'),
    ('Futures', 'https://fapi.binance.com', '/fapi/v1'),
]
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'VolkanKriptoRadar/3.1'})
EXCLUDED = {
    'TSLA', 'TSLAB', 'USDT', 'USDC', 'FDUSD', 'TUSD', 'DAI',
    'BUSD', 'USDE', 'USD1', 'RLUSD', 'BFUSD', 'USDD', 'PYUSD',
    'EUR', 'EURC', 'EURI', 'AEUR', 'WBTC', 'WBETH', 'BETH',
    'USDP', 'USTC', 'LUSD'
}


def get_json(base, path, params=None):
    response = SESSION.get(base + path, params=params, timeout=25)
    response.raise_for_status()
    return response.json()


def scan_market(name, base, prefix):
    exchange = get_json(base, prefix + '/exchangeInfo')
    tickers = get_json(base, prefix + '/ticker/24hr')
    active = set()
    for s in exchange['symbols']:
        asset = s.get('baseAsset', '')
        if s.get('status') != 'TRADING' or s.get('quoteAsset') != 'USDT':
            continue
        if asset in EXCLUDED or asset.endswith(('UP', 'DOWN', 'BULL', 'BEAR')):
            continue
        if name == 'Spot' and not s.get('isSpotTradingAllowed', True):
            continue
        if name == 'Futures' and s.get('contractType') != 'PERPETUAL':
            continue
        active.add(s['symbol'])

    liquid = sorted(
        (t for t in tickers if t.get('symbol') in active
         and float(t.get('quoteVolume', 0)) >= 5_000_000
         and -10 <= float(t.get('priceChangePercent', 0)) <= 12),
        key=lambda t: float(t['quoteVolume']), reverse=True
    )[:100]
    results = []
    failed = 0
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
            price = float(recent[-1][4])
            resistance = max(highs[:-1])
            if price <= 0 or resistance <= 0:
                continue
            width = (max(highs) - min(lows)) / price * 100
            # Kline quote-volume is index 7 for both Spot and USD-M Futures.
            prev_avg = sum(float(c[7]) for c in previous) / 24
            recent_avg = sum(float(c[7]) for c in recent[-3:]) / 3
            ratio = recent_avg / max(prev_avg, 0.000001)
            distance = (resistance - price) / resistance * 100
            if width <= 10 and ratio >= 1.5 and -1.5 <= distance <= 2:
                results.append({
                    'market': name,
                    'symbol': symbol,
                    'width_pct': round(width, 3),
                    'volume_ratio': round(ratio, 3),
                    'distance_to_resistance_pct': round(distance, 3),
                    'volume_usdt_24h': round(float(t['quoteVolume']), 2),
                    'risk_status': 'Seed/Monitoring/delist kontrol edilmedi'
                })
        except (requests.RequestException, ValueError, KeyError,
                IndexError, TypeError, ZeroDivisionError) as exc:
            failed += 1
            print(f'Atlandi: {name} {symbol}: {exc}')
    if liquid and failed == len(liquid):
        raise RuntimeError(f'{name}: tum mum verisi istekleri basarisiz')
    results.sort(key=lambda c: (-c['volume_ratio'],
                                abs(c['distance_to_resistance_pct'])))
    print(f'{name}: {len(results)} aday, {len(liquid)} parite tarandi, {failed} hata')
    return results


def main():
    report = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'status': 'error', 'candidates': [], 'errors': [],
        'risk_filters_verified': False
    }
    successes = 0
    for name, base, prefix in MARKETS:
        try:
            report['candidates'].extend(scan_market(name, base, prefix))
            successes += 1
        except (requests.RequestException, ValueError, KeyError,
                TypeError, RuntimeError) as exc:
            message = f'{name} taramasi basarisiz: {exc}'
            print(message)
            report['errors'].append(message)
    report['status'] = 'ok' if successes == len(MARKETS) else 'error'
    report['candidates'].sort(key=lambda c: -c['volume_ratio'])
    with open('radar.json', 'w', encoding='utf-8') as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print('Tarama durumu:', report['status'])
    print('Toplam aday:', len(report['candidates']))
    for c in report['candidates'][:15]:
        print(c['market'], c['symbol'], 'Hacim:', c['volume_ratio'], 'x')
    if report['status'] != 'ok':
    if report['candidates']:
        print('UYARI: Kismi tarama basarili. Hatalar:', report['errors'])
    else:
        raise SystemExit(1)
