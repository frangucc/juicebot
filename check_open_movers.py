#!/usr/bin/env python3
"""Check for symbols with high % OPEN moves."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_open_movers():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print('='*80)
    print('SYMBOLS WITH % OPEN >= 10%')
    print('='*80)

    cursor.execute('''
        SELECT symbol, current_price, today_open, pct_from_open, pct_from_yesterday
        FROM symbol_state
        WHERE pct_from_open >= 10
        AND today_open IS NOT NULL
        AND today_open > 0
        ORDER BY pct_from_open DESC
        LIMIT 20
    ''')

    results = cursor.fetchall()
    print(f'Found {len(results)} symbols with % OPEN >= 10%')
    print()

    if results:
        print(f'{"Symbol":<8} {"Current":<10} {"Open":<10} {"% OPEN":<10} {"% YEST":<10}')
        print('-'*80)
        for row in results:
            symbol, curr, open_p, pct_open, pct_yest = row
            print(f'{symbol:<8} ${curr:<9.2f} ${open_p:<9.2f} {pct_open:+.2f}%    {pct_yest:+.2f}%')
    else:
        print('❌ NO SYMBOLS FOUND with % OPEN >= 10%')

    print()
    print('='*80)
    print('SYMBOLS WITH % OPEN >= 20%')
    print('='*80)

    cursor.execute('''
        SELECT symbol, current_price, today_open, pct_from_open, pct_from_yesterday
        FROM symbol_state
        WHERE pct_from_open >= 20
        AND today_open IS NOT NULL
        AND today_open > 0
        ORDER BY pct_from_open DESC
        LIMIT 10
    ''')

    results = cursor.fetchall()
    print(f'Found {len(results)} symbols with % OPEN >= 20%')
    print()

    if results:
        print(f'{"Symbol":<8} {"Current":<10} {"Open":<10} {"% OPEN":<10} {"% YEST":<10}')
        print('-'*80)
        for row in results:
            symbol, curr, open_p, pct_open, pct_yest = row
            print(f'{symbol:<8} ${curr:<9.2f} ${open_p:<9.2f} {pct_open:+.2f}%    {pct_yest:+.2f}%')
    else:
        print('❌ NO SYMBOLS FOUND with % OPEN >= 20%')

    print()
    print('='*80)
    print('WHAT TIME IS IT NOW?')
    print('='*80)

    from datetime import datetime
    import pytz

    now_utc = datetime.now(pytz.UTC)
    now_cst = now_utc.astimezone(pytz.timezone('America/Chicago'))

    print(f'Current time (UTC): {now_utc}')
    print(f'Current time (CST): {now_cst}')
    print()

    if now_cst.hour < 8 or (now_cst.hour == 8 and now_cst.minute < 30):
        print('🕐 Markets not open yet (before 8:30 AM CST)')
        print('   % OPEN will be low/zero because stocks haven\'t moved much from open')
    elif now_cst.hour >= 15:
        print('🕐 Markets closed (after 3:00 PM CST)')
        print('   % OPEN shows full day\'s move from open')
    else:
        print('✅ Markets are open - should see active % OPEN moves')

    print()
    print('='*80)
    print('CHECK: Total symbols with ANY % OPEN movement')
    print('='*80)

    cursor.execute('''
        SELECT COUNT(*)
        FROM symbol_state
        WHERE pct_from_open IS NOT NULL
        AND ABS(pct_from_open) >= 1
    ''')
    count = cursor.fetchone()[0]
    print(f'Symbols with |% OPEN| >= 1%: {count}')

    cursor.execute('''
        SELECT COUNT(*)
        FROM symbol_state
        WHERE pct_from_open IS NOT NULL
        AND ABS(pct_from_open) >= 10
    ''')
    count = cursor.fetchone()[0]
    print(f'Symbols with |% OPEN| >= 10%: {count}')

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_open_movers()
