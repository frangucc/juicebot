#!/usr/bin/env python3
"""
Analyze leaderboard data coverage and quality.
Shows what % of symbols have complete data vs gaps.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def analyze_leaderboard():
    """Analyze current leaderboard data quality."""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print('=' * 80)
    print('LEADERBOARD DATA COVERAGE ANALYSIS')
    print('=' * 80)
    print()

    # Get total symbols in leaderboard
    cursor.execute("SELECT COUNT(*) FROM symbol_state WHERE current_price IS NOT NULL")
    total_symbols = cursor.fetchone()[0]
    print(f'Total symbols with current price: {total_symbols}')
    print()

    # Check yesterday_close coverage
    print('1. YESTERDAY_CLOSE COVERAGE:')
    print('-' * 80)

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE yesterday_close IS NOT NULL AND yesterday_close > 0) as has_yest,
            COUNT(*) FILTER (WHERE yesterday_close IS NULL OR yesterday_close = 0) as missing_yest,
            COUNT(*) as total
        FROM symbol_state
        WHERE current_price IS NOT NULL
    """)
    yest_has, yest_missing, yest_total = cursor.fetchone()
    yest_pct = (yest_has / yest_total * 100) if yest_total > 0 else 0

    print(f'  ✅ Has yesterday_close: {yest_has:,} ({yest_pct:.1f}%)')
    print(f'  ❌ Missing yesterday_close: {yest_missing:,} ({100-yest_pct:.1f}%)')
    print()

    # Check today_open coverage
    print('2. TODAY_OPEN COVERAGE:')
    print('-' * 80)

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE today_open IS NOT NULL AND today_open > 0) as has_open,
            COUNT(*) FILTER (WHERE today_open IS NULL OR today_open = 0) as missing_open,
            COUNT(*) as total
        FROM symbol_state
        WHERE current_price IS NOT NULL
    """)
    open_has, open_missing, open_total = cursor.fetchone()
    open_pct = (open_has / open_total * 100) if open_total > 0 else 0

    print(f'  ✅ Has today_open: {open_has:,} ({open_pct:.1f}%)')
    print(f'  ❌ Missing today_open: {open_missing:,} ({100-open_pct:.1f}%)')
    print()

    # Check pre_market_open coverage
    print('3. PRE_MARKET_OPEN COVERAGE:')
    print('-' * 80)

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pre_market_open IS NOT NULL AND pre_market_open > 0) as has_pre,
            COUNT(*) FILTER (WHERE pre_market_open IS NULL OR pre_market_open = 0) as missing_pre,
            COUNT(*) as total
        FROM symbol_state
        WHERE current_price IS NOT NULL
    """)
    pre_has, pre_missing, pre_total = cursor.fetchone()
    pre_pct = (pre_has / pre_total * 100) if pre_total > 0 else 0

    print(f'  ✅ Has pre_market_open: {pre_has:,} ({pre_pct:.1f}%)')
    print(f'  ❌ Missing pre_market_open: {pre_missing:,} ({100-pre_pct:.1f}%)')
    print()

    # Check % YEST accuracy
    print('4. % YEST CALCULATION ACCURACY:')
    print('-' * 80)

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pct_from_yesterday IS NOT NULL AND yesterday_close > 0) as valid_pct_yest,
            COUNT(*) FILTER (WHERE pct_from_yesterday IS NULL OR yesterday_close = 0 OR yesterday_close IS NULL) as invalid_pct_yest,
            COUNT(*) as total
        FROM symbol_state
        WHERE current_price IS NOT NULL
    """)
    valid_yest, invalid_yest, total_yest = cursor.fetchone()
    valid_yest_pct = (valid_yest / total_yest * 100) if total_yest > 0 else 0

    print(f'  ✅ Valid % YEST: {valid_yest:,} ({valid_yest_pct:.1f}%)')
    print(f'  ❌ Invalid % YEST: {invalid_yest:,} ({100-valid_yest_pct:.1f}%)')
    print()

    # Check % OPEN accuracy
    print('5. % OPEN CALCULATION ACCURACY:')
    print('-' * 80)

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pct_from_open IS NOT NULL AND today_open > 0) as valid_pct_open,
            COUNT(*) FILTER (WHERE pct_from_open IS NULL OR today_open = 0 OR today_open IS NULL) as invalid_pct_open,
            COUNT(*) as total
        FROM symbol_state
        WHERE current_price IS NOT NULL
    """)
    valid_open, invalid_open, total_open = cursor.fetchone()
    valid_open_pct = (valid_open / total_open * 100) if total_open > 0 else 0

    print(f'  ✅ Valid % OPEN: {valid_open:,} ({valid_open_pct:.1f}%)')
    print(f'  ❌ Invalid % OPEN: {invalid_open:,} ({100-valid_open_pct:.1f}%)')
    print()

    # Top leaderboard symbols (by % YEST)
    print('6. TOP 20 LEADERBOARD SYMBOLS (By % YEST):')
    print('-' * 80)
    print(f'{"Symbol":<8} {"Current":<10} {"Yest Close":<12} {"Today Open":<12} {"% YEST":<10} {"% OPEN":<10} {"Status"}')
    print('-' * 80)

    cursor.execute("""
        SELECT
            symbol,
            current_price,
            yesterday_close,
            today_open,
            pct_from_yesterday,
            pct_from_open
        FROM symbol_state
        WHERE current_price IS NOT NULL
        AND pct_from_yesterday IS NOT NULL
        ORDER BY ABS(pct_from_yesterday) DESC
        LIMIT 20
    """)

    for row in cursor.fetchall():
        symbol, curr, yest, open_p, pct_yest, pct_open = row

        # Determine status
        status = '✅'
        if yest is None or yest == 0:
            status = '❌ NO YEST'
        elif open_p is None or open_p == 0:
            status = '⚠️  NO OPEN'
        elif abs(pct_yest) > 100:
            status = '🚨 SUSPICIOUS'

        yest_str = f'${yest:.2f}' if yest else 'NULL'
        open_str = f'${open_p:.2f}' if open_p else 'NULL'
        pct_yest_str = f'{pct_yest:+.2f}%' if pct_yest is not None else 'NULL'
        pct_open_str = f'{pct_open:+.2f}%' if pct_open is not None else 'NULL'

        print(f'{symbol:<8} ${curr:<9.2f} {yest_str:<12} {open_str:<12} {pct_yest_str:<10} {pct_open_str:<10} {status}')

    print()

    # Symbols with suspicious data
    print('7. SUSPICIOUS DATA (% YEST > 100% or < -50%):')
    print('-' * 80)

    cursor.execute("""
        SELECT
            symbol,
            current_price,
            yesterday_close,
            pct_from_yesterday,
            last_updated
        FROM symbol_state
        WHERE current_price IS NOT NULL
        AND (pct_from_yesterday > 100 OR pct_from_yesterday < -50)
        ORDER BY ABS(pct_from_yesterday) DESC
        LIMIT 10
    """)

    suspicious = cursor.fetchall()
    if suspicious:
        print(f'Found {len(suspicious)} symbols with suspicious % YEST:')
        print()
        for row in suspicious:
            symbol, curr, yest, pct_yest, last_upd = row
            print(f'  🚨 {symbol}: curr=${curr:.2f}, yest=${yest:.2f}, %YEST={pct_yest:+.2f}%')
            print(f'      Last updated: {last_upd}')
            print()
    else:
        print('  ✅ No symbols with suspicious % YEST')
        print()

    # Check for stale yesterday_close
    print('8. STALE YESTERDAY_CLOSE (Price hasn\'t changed much):')
    print('-' * 80)

    cursor.execute("""
        SELECT
            symbol,
            current_price,
            yesterday_close,
            today_open,
            pct_from_yesterday
        FROM symbol_state
        WHERE current_price IS NOT NULL
        AND yesterday_close IS NOT NULL
        AND yesterday_close > 0
        AND today_open IS NOT NULL
        AND today_open > 0
        AND ABS((today_open - yesterday_close) / yesterday_close * 100) > 50
        ORDER BY ABS((today_open - yesterday_close) / yesterday_close) DESC
        LIMIT 10
    """)

    stale = cursor.fetchall()
    if stale:
        print(f'Found {len(stale)} symbols where today_open differs >50% from yesterday_close:')
        print('(Suggests yesterday_close is stale)')
        print()
        for row in stale:
            symbol, curr, yest, open_p, pct_yest = row
            gap = ((open_p - yest) / yest * 100) if yest else 0
            print(f'  ⚠️  {symbol}: yest=${yest:.2f}, open=${open_p:.2f}, gap={gap:+.1f}%, %YEST={pct_yest:+.2f}%')
    else:
        print('  ✅ No symbols with suspicious yest/open gaps')

    print()
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Total symbols: {total_symbols:,}')
    print(f'Yesterday_close coverage: {yest_pct:.1f}%')
    print(f'Today_open coverage: {open_pct:.1f}%')
    print(f'Pre_market_open coverage: {pre_pct:.1f}%')
    print(f'Valid % YEST: {valid_yest_pct:.1f}%')
    print(f'Valid % OPEN: {valid_open_pct:.1f}%')
    print()
    print(f'Improvement needed:')
    print(f'  - Fill {yest_missing:,} missing yesterday_close values')
    print(f'  - Fill {open_missing:,} missing today_open values')
    print(f'  - Fix {len(suspicious)} suspicious % YEST values')
    print()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_leaderboard()
