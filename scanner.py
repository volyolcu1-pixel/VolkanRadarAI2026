import json
from datetime import datetime, timezone

import requests

SPOT = 'https://data-api.binance.vision'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'KriptoRadar/2.0'})


def get_json(base, path, params=None):
    response = SESSION.get(base + path, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def scan_market(name, base, prefix):
    tickers = get_json(base, prefix + '/ticker/24hr')
    exchange = get_json(base, prefix + '/exchangeInfo')
    active = {
        s['symbol'] for s in exchange['symbols']
        if s.get('status') == 'TRADING'
        and s.get('quoteAsset') == 'USDT'
        and s.get('baseAsset') not in {
            'USDT', 'USDC', 'FDUSD', 'TUSD', 'DAI', 'BUSD', 'USDE', 'USD1'
        }
    }
    liquid = sorted(
        (
            t for t in tickers
            if t['symbol'] in active
            and float(t.get('quoteVolume', 0)) >= 5_000_000
            and -10 <= float(t.get('priceChangePercent', 0)) <= 12
        ),
        key=lambda t: float(t['quoteVolume']),
        reverse=True
    )[:60]

    matches = []
    for t in liquid:
        symbol = t['symbol']
        try:
            candles = get_json(
                base, prefix + '/klines',
                {'symbol': symbol, 'interval': '1h', 'limit': 73}
            )
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
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            print(f'Atlandi: {name} {symbol}: {exc}')

    matches.sort(key=lambda x: (-x[2], abs(x[3])))
    print(f'\n{name}: {len(matches)} teknik aday (ilk 60 likit parite tarandi)')
    for symbol, width, ratio, distance, volume in matches[:15]:
        print(f'{symbol} | 24s aralik %{width:.1f} | hacim orani {ratio:.1f}x '
              f'| dirence uzaklik %{distance:.1f} | 24s hacim {volume:,.0f} USDT')
    return matches


def main():
    now = datetime.now(timezone.utc).isoformat()
    print('KRIPTO RADAR 2.0 -', now)
    print('UYARI: Seed/Monitoring ve delist etiketleri dogrulanmadi; alim sinyali degildir.')

    report = {'updated_at': now, 'status': 'error', 'candidates': [], 'errors': []}
    for name, base, prefix in [('Spot', SPOT, '/api/v3')]:
        try:
            matches = scan_market(name, base, prefix)
            report['candidates'].extend([
                {
                    'market': name,
                    'symbol': symbol,
                    'width_pct': round(width, 3),
                    'volume_ratio': round(ratio, 3),
                    'distance_to_resistance_pct': round(distance, 3),
                    'volume_usdt_24h': round(volume, 2)
                }
                for symbol, width, ratio, distance, volume in matches
            ])
            report['status'] = 'ok'
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            message = f'{name} taramasi basarisiz: {exc}'
            print(message)
            report['errors'].append(message)

    with open('radar.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"radar.json yazildi: {len(report['candidates'])} aday")
    if report['status'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
