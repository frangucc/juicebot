#!/usr/bin/env python3
"""
Quick fix for today's leaderboard data.
Fixes yesterday_close and today_open using our captured alerts.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def fix_todays_baselines():
    """Fix yesterday_close and today_open for all symbols in leaderboard."""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print('=' * 80)
    print('QUICK FIX: TODAY\'S BASELINE DATA')
    print('=' * 80)
    print()

    # Step 1: Fix yesterday_close using yesterday's latest alert (around 4-8 PM)
    print('Step 1: Fixing yesterday_close...')
    print('-' * 80)

    cursor.execute("""
        WITH yesterday_closes AS (
            SELECT DISTINCT ON (symbol)
                symbol,
                trigger_price as yesterday_close
            FROM screener_alerts
            WHERE DATE(trigger_time AT TIME ZONE 'America/Chicago') = CURRENT_DATE - INTERVAL '1 day'
            AND EXTRACT(HOUR FROM trigger_time AT TIME ZONE 'America/Chicago') >= 15  -- After 3 PM CDT
            ORDER BY symbol, trigger_time DESC
        )
        SELECT symbol, yesterday_close FROM yesterday_closes
    """)

    yesterday_data = cursor.fetchall()
    print(f'Found yesterday close prices for {len(yesterday_data)} symbols')

    # Update symbol_state with corrected yesterday_close
    updates_yest = 0
    for symbol, yest_close in yesterday_data:
        # Get current values to recalculate pct_from_yesterday
        cursor.execute("""
            SELECT current_price FROM symbol_state WHERE symbol = %s
        """, (symbol,))
        result = cursor.fetchone()

        if result:
            current_price = result[0]
            pct_from_yesterday = ((current_price - yest_close) / yest_close) * 100 if yest_close else None

            cursor.execute("""
                UPDATE symbol_state
                SET yesterday_close = %s,
                    pct_from_yesterday = %s
                WHERE symbol = %s
            """, (yest_close, pct_from_yesterday, symbol))
            updates_yest += 1

    conn.commit()
    print(f'✅ Updated yesterday_close for {updates_yest} symbols')
    print()

    # Step 2: Fix today_open using earliest alert around 8:30 AM (regular hours start)
    print('Step 2: Fixing today_open...')
    print('-' * 80)

    # Get earliest price for each symbol around market open (8:00-9:00 AM CDT)
    cursor.execute("""
        WITH open_prices AS (
            SELECT DISTINCT ON (symbol)
                symbol,
                trigger_price as open_price
            FROM screener_alerts
            WHERE DATE(trigger_time AT TIME ZONE 'America/Chicago') = CURRENT_DATE
            AND EXTRACT(HOUR FROM trigger_time AT TIME ZONE 'America/Chicago') BETWEEN 8 AND 9
            ORDER BY symbol, trigger_time ASC
        )
        SELECT symbol, open_price FROM open_prices
    """)

    open_data = cursor.fetchall()
    print(f'Found open prices for {len(open_data)} symbols')

    # Update symbol_state with corrected today_open
    updates_open = 0
    for symbol, open_price in open_data:
        # Get current values to recalculate pct_from_open
        cursor.execute("""
            SELECT current_price FROM symbol_state WHERE symbol = %s
        """, (symbol,))
        result = cursor.fetchone()

        if result:
            current_price = result[0]
            pct_from_open = ((current_price - open_price) / open_price) * 100 if open_price else None

            cursor.execute("""
                UPDATE symbol_state
                SET today_open = %s,
                    rth_open = %s,
                    pct_from_open = %s
                WHERE symbol = %s
            """, (open_price, open_price, pct_from_open, symbol))
            updates_open += 1

    conn.commit()
    print(f'✅ Updated today_open for {updates_open} symbols')
    print()

    # Step 3: Show sample results
    print('Step 3: Verification - Sample symbols:')
    print('-' * 80)

    test_symbols = ['WGRX', 'RKLB', 'QQQ', 'NVDA', 'SPY', 'TSLA']
    for symbol in test_symbols:
        cursor.execute("""
            SELECT symbol, current_price, yesterday_close, today_open,
                   pct_from_yesterday, pct_from_open
            FROM symbol_state
            WHERE symbol = %s
        """, (symbol,))
        result = cursor.fetchone()

        if result:
            sym, curr, yest, open_p, pct_yest, pct_open = result
            print(f'{sym:6s}: curr=${curr:.2f}, yest=${yest:.2f} ({pct_yest:+.2f}%), open=${open_p:.2f} ({pct_open:+.2f}%)')
        else:
            print(f'{symbol:6s}: Not in symbol_state')

    print()
    print('=' * 80)
    print('✅ BASELINE FIX COMPLETE')
    print('=' * 80)
    print()
    print(f'Summary:')
    print(f'  - Fixed yesterday_close for {updates_yest} symbols')
    print(f'  - Fixed today_open for {updates_open} symbols')
    print(f'  - Recalculated % YEST and % OPEN')
    print()
    print('Note: Symbols without alerts in those time windows remain unchanged.')
    print('This is a one-time fix. Deploy price_bars solution for permanent accuracy.')

    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_todays_baselines()
