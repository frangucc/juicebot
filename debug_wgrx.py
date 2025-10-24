#!/usr/bin/env python3
"""Debug WGRX data in detail."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

def debug_wgrx():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print('=' * 80)
    print('WGRX FULL DATA ANALYSIS')
    print('=' * 80)
    print()

    # Get WGRX from symbol_state
    print('1. SYMBOL_STATE TABLE:')
    cursor.execute("""
        SELECT symbol, current_price, yesterday_close, today_open,
               pre_market_open, rth_open, post_market_open,
               pct_from_pre, pct_from_post,
               pct_from_yesterday, pct_from_open,
               price_5min_ago, pct_from_5min,
               price_15min_ago, pct_from_15min,
               hod_price, hod_pct, lod_price, lod_pct,
               last_updated
        FROM symbol_state
        WHERE symbol = 'WGRX'
    """)
    result = cursor.fetchone()
    if result:
        cols = ['symbol', 'current_price', 'yesterday_close', 'today_open',
                'pre_market_open', 'rth_open', 'post_market_open',
                'pct_from_pre', 'pct_from_post',
                'pct_from_yesterday', 'pct_from_open',
                'price_5min_ago', 'pct_from_5min',
                'price_15min_ago', 'pct_from_15min',
                'hod_price', 'hod_pct', 'lod_price', 'lod_pct',
                'last_updated']
        for col, val in zip(cols, result):
            print(f'  {col:20s}: {val}')
    else:
        print('  ❌ WGRX not found in symbol_state')

    print()
    print('2. ALERTS FOR WGRX (last 20):')
    cursor.execute("""
        SELECT trigger_price, trigger_time
        FROM screener_alerts
        WHERE symbol = 'WGRX'
        ORDER BY trigger_time DESC
        LIMIT 20
    """)
    alerts = cursor.fetchall()
    if alerts:
        print(f'  Found {len(alerts)} recent alerts:')
        for alert in alerts:
            print(f'    price=${alert[0]:7.4f}, time={alert[1]}')
    else:
        print('  ❌ No alerts found')

    print()
    print('3. MANUAL CALCULATIONS (verify against DB):')
    if result:
        current = result[1]
        yesterday_close = result[2]
        today_open = result[3]

        if current and yesterday_close:
            yest_pct = ((current - yesterday_close) / yesterday_close) * 100
            print(f'  % YEST = (current - yesterday_close) / yesterday_close * 100')
            print(f'         = ({current} - {yesterday_close}) / {yesterday_close} * 100')
            print(f'         = {yest_pct:+.2f}%')
            print(f'  DB shows: {result[9]} (pct_from_yesterday)')
        else:
            print(f'  % YEST: Cannot calculate (current={current}, yesterday_close={yesterday_close})')

        if current and today_open and today_open > 0:
            open_pct = ((current - today_open) / today_open) * 100
            print(f'  % OPEN = (current - today_open) / today_open * 100')
            print(f'         = ({current} - {today_open}) / {today_open} * 100')
            print(f'         = {open_pct:+.2f}%')
            print(f'  DB shows: {result[10]} (pct_from_open)')
        else:
            print(f'  % OPEN: Cannot calculate (current={current}, today_open={today_open})')

    print()
    print('4. ISSUE ANALYSIS:')
    print('  From the data above:')
    print(f'    - yesterday_close = {result[2]}')
    print(f'    - today_open = {result[3]}')
    print(f'    - current_price = {result[1]}')
    print()
    print('  THE PROBLEM:')
    if result[2] == 0.4029 and result[3] == 1.135:
        print('    ❌ yesterday_close ($0.40) is MUCH LOWER than today_open ($1.14)')
        print('    ❌ This suggests yesterday_close is WRONG or from an old date')
        print('    ❌ The 184% gain is FAKE - it\'s measuring from stale/incorrect data')
        print()
        print('  EXPECTED BEHAVIOR:')
        print('    - If WGRX opened at $1.14 today, yesterday should be close to that')
        print('    - Real % YEST should be: (1.145 - 1.14) / 1.14 = +0.44%')
        print('    - But we\'re showing 184% because yesterday_close is $0.40')

    print()
    print('5. CHECK ALERTS FROM YESTERDAY:')
    cursor.execute("""
        SELECT trigger_price, trigger_time
        FROM screener_alerts
        WHERE symbol = 'WGRX'
        AND DATE(trigger_time AT TIME ZONE 'UTC') = CURRENT_DATE - INTERVAL '1 day'
        ORDER BY trigger_time DESC
        LIMIT 5
    """)
    yesterday_alerts = cursor.fetchall()
    if yesterday_alerts:
        print(f'  Found {len(yesterday_alerts)} alerts from yesterday:')
        for alert in yesterday_alerts:
            print(f'    price=${alert[0]:7.4f}, time={alert[1]}')
    else:
        print('  ❌ No alerts from yesterday - explains why yesterday_close is stale!')

    cursor.close()
    conn.close()

if __name__ == "__main__":
    debug_wgrx()
