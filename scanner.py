"""Volkan Kripto Radar 3.2 - public market data, no trading orders."""
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

SPOT = 'https://data-api.binance.vision'
FUTURES = 'https://fapi.binance.com'
MARKETS = [('Spot', SPOT, '/api/v3'), ('Futures', FUTURES, '/fapi/v1')]
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'VolkanKriptoRadar/3.2'})

# Manual exclusions are not a substitute for live exchange risk-tag verification.
EXCLUDED = {
    'USDT', 'USDC', 'FDUSD', 'TUSD', 'DAI', 'BUSD', 'USDE',
    'USD1', 'RLUSD', 'BFUSD', 'USDD', 'PYUSD', 'USDP',
    'USTC', 'LUSD', 'XUSD', 'EUR', 'EURC', 'EURI', 'AEUR',
    'WBTC', 'WBETH', 'BETH', 'TSLA', 'TSLAB',
}
EXCLUDED_SUFFIXES = ('UP', 'DOWN', 'BULL', 'BEAR')


def get_json(base, path, params=None):
    response = SESSION.get(base + path, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def eligible(symbol, market):
    base = symbol.get('baseAsset', '')
    if (symbol.get('status') != 'TRADING'
            or symbol.get('quoteAsset') != 'USDT'
            or base in EXCLUDED
            or base.endswith(EXCLUDED_SUFFIXES)):
        return False
    if market == 'Spot':
        return symbol.get('isSpotTradingAllowed', True)
    return symbol.get('contractType') == 'PERPETUAL'


def scan_market(name, base, prefix):
    exchange = get_json(base, prefix + '/exchangeInfo')
    tickers = get_json(base, prefix + '/ticker/24hr')
    active = {s['symbol'] for s in exchange['symbols'] if eligible(s, name)}
    liquid = sorted(
        (t for t in tickers
         if t.get('symbol') in active
         and float(t.get('quoteVolume', 0)) >= 5_000_000
         and -10 <= float(t.get('priceChangePercent', 0)) <= 12),
        key=lambda t: float(t['quoteVolume']), reverse=True
    )[:100]

    results = []
    failed = 0
    for ticker in liquid:
        symbol = ticker['symbol']
        try:
            candles = get_json(base, prefix + '/klines',
                               {'symbol': symbol, 'interval': '1h', 'limit': 73})
            if len(candles) < 73:
                failed += 1
                continue
            closed = candles[:-1]
            recent, previous = closed[-24:], closed[-48:-24]
            highs = [float(c[2]) for c in recent]
            lows = [float(c[3]) for c in recent]
            price = float(recent[-1][4])
            resistance = max(highs[:-1])
            if price <= 0 or resistance <= 0:
                continue
            width = (max(highs) - min(lows)) / price * 100
            old_avg = sum(float(c[7]) for c in previous) / len(previous)
            new_avg = sum(float(c[7]) for c in recent[-3:]) / 3
            ratio = new_avg / max(old_avg, 0.000001)
            distance = (resistance - price) / resistance * 100
            if width <= 10 and ratio >= 1.5 and -1.5 <= distance <= 2:
                results.append({
                    'market': name,
                    'symbol': symbol,
                    'width_pct': round(width, 3),
                    'volume_ratio': round(ratio, 3),
                    'distance_to_resistance_pct': round(distance, 3),
                    'volume_usdt_24h': round(float(ticker['quoteVolume']), 2),
                    'risk_status': 'Seed/Monitoring/delist kontrol edilmedi'
                })
        except (requests.RequestException, ValueError, KeyError,
                IndexError, TypeError, ZeroDivisionError) as exc:
            failed += 1
            print(f'Atlandi: {name} {symbol}: {exc}')
    results.sort(key=lambda x: (-x['volume_ratio'],
                                abs(x['distance_to_resistance_pct'])))
    print(f'{name}: {len(results)} aday, {len(liquid)} parite tarandi, {failed} hata')
    return results


def main():
    report = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'status': 'error', 'candidates': [], 'errors': [],
        'risk_filters_verified': False,
        'markets': {}
    }
    successes = 0
    for name, base, prefix in MARKETS:
        try:
            found = scan_market(name, base, prefix)
            report['candidates'].extend(found)
            report['markets'][name] = 'ok'
            successes += 1
        except (requests.RequestException, ValueError, KeyError,
                IndexError, TypeError, RuntimeError) as exc:
            message = f'{name} taramasi basarisiz: {exc}'
            print(message)
            report['errors'].append(message)
            report['markets'][name] = 'error'

    report['status'] = ('ok' if successes == len(MARKETS)
                        else 'partial' if successes else 'error')
    report['candidates'].sort(key=lambda c: (-c['volume_ratio'],
                                              abs(c['distance_to_resistance_pct'])))
    Path('radar.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Tarama durumu:', report['status'])
    print('Toplam aday:', len(report['candidates']))
    for c in report['candidates'][:15]:
        print(c['market'], c['symbol'], 'Hacim:', c['volume_ratio'], 'x')
    if report['errors']:
        print('UYARI: Basarisiz piyasalar:', report['errors'])
    if successes == 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
