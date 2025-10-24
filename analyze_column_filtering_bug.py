#!/usr/bin/env python3
"""
Analyze the column filtering bug in the leaderboard.

THE BUG:
- Backend API fetches symbols based on % YEST (by default)
- Columns are populated based on % YEST ranges: 20%+, 10-20%, 1-10%
- Frontend just sorts/displays those pre-populated columns
- When user switches from "% YEST" to "% OPEN", the COLUMNS DON'T CHANGE
- Frontend just sorts the same symbols by % OPEN instead of % YEST
- Result: Symbols that are 20%+ from YEST but only 5% from OPEN stay in the 20%+ column

WHAT SHOULD HAPPEN:
- When user switches baseline, the columns should RE-CATEGORIZE based on that baseline
- A symbol with % YEST = +25%, % OPEN = +5% should:
  - Be in "20%+" column when viewing % YEST
  - Move to "1-10%" column when viewing % OPEN
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

def analyze_bug():
    """Show examples of symbols that demonstrate the bug."""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print('=' * 80)
    print('LEADERBOARD COLUMN FILTERING BUG ANALYSIS')
    print('=' * 80)
    print()

    print('THE BUG:')
    print('-' * 80)
    print('When you switch from "% YEST" to "% OPEN":')
    print('  ❌ Symbols stay in their original columns (based on % YEST)')
    print('  ❌ They just get re-sorted by % OPEN within those columns')
    print('  ❌ A symbol with % YEST = +25%, % OPEN = +2% stays in the "20%+" column')
    print()
    print('WHAT SHOULD HAPPEN:')
    print('  ✅ Columns should RE-CATEGORIZE based on the selected baseline')
    print('  ✅ % YEST = +25%, % OPEN = +2% should move from "20%+" to "1-10%" column')
    print()

    print('=' * 80)
    print('EXAMPLE 1: Symbols in WRONG column when viewing % OPEN')
    print('=' * 80)
    print()

    # Find symbols that are 20%+ from yesterday but < 20% from open
    cursor.execute("""
        SELECT
            symbol,
            current_price,
            pct_from_yesterday,
            pct_from_open,
            pct_from_pre,
            pct_from_15min,
            pct_from_5min
        FROM symbol_state
        WHERE current_price IS NOT NULL
        AND pct_from_yesterday >= 20  -- Would be in "20%+" column by default
        AND ABS(pct_from_open) < 20    -- But NOT 20%+ from open
        ORDER BY pct_from_yesterday DESC
        LIMIT 10
    """)

    wrong_column = cursor.fetchall()
    if wrong_column:
        print('These symbols are in the "20%+" column when viewing % YEST:')
        print('But they DON\'T belong in "20%+" when viewing % OPEN:')
        print()
        print(f'{"Symbol":<8} {"% YEST":<10} {"% OPEN":<10} {"Current":<12} {"Correct Column (OPEN)"}')
        print('-' * 80)

        for row in wrong_column:
            symbol, price, pct_yest, pct_open, pct_pre, pct_15m, pct_5m = row

            # Determine correct column based on % OPEN
            if pct_open is None:
                correct_col = 'NONE (NULL)'
            elif abs(pct_open) >= 20:
                correct_col = '20%+'
            elif abs(pct_open) >= 10:
                correct_col = '10-20%'
            elif abs(pct_open) >= 1:
                correct_col = '1-10%'
            else:
                correct_col = '< 1% (should be hidden)'

            pct_open_str = f'{pct_open:+.2f}%' if pct_open is not None else 'NULL'
            print(f'{symbol:<8} {pct_yest:+.2f}%   {pct_open_str:<10} ${price:<11.2f} {correct_col}')

        print()
        print(f'🚨 Found {len(wrong_column)} symbols that are in WRONG column when viewing % OPEN')
    else:
        print('✅ No symbols found in wrong column (good sign!)')

    print()
    print('=' * 80)
    print('EXAMPLE 2: Symbols that should DISAPPEAR from 20%+ column')
    print('=' * 80)
    print()

    # Find symbols that are 20%+ from yesterday but NEGATIVE from open
    cursor.execute("""
        SELECT
            symbol,
            current_price,
            pct_from_yesterday,
            pct_from_open
        FROM symbol_state
        WHERE current_price IS NOT NULL
        AND pct_from_yesterday >= 20
        AND pct_from_open < 0
        ORDER BY pct_from_yesterday DESC
        LIMIT 10
    """)

    should_disappear = cursor.fetchall()
    if should_disappear:
        print('These symbols are in the "20%+" column when viewing % YEST:')
        print('But they are NEGATIVE when viewing % OPEN (should move to different column or disappear):')
        print()
        print(f'{"Symbol":<8} {"% YEST":<10} {"% OPEN":<10} {"Current":<12}')
        print('-' * 80)

        for row in should_disappear:
            symbol, price, pct_yest, pct_open = row
            pct_open_str = f'{pct_open:+.2f}%' if pct_open is not None else 'NULL'
            print(f'{symbol:<8} {pct_yest:+.2f}%   {pct_open_str:<10} ${price:<11.2f}')

        print()
        print(f'🚨 Found {len(should_disappear)} symbols that should MOVE OUT of 20%+ column')

    print()
    print('=' * 80)
    print('HOW TO FIX THIS')
    print('=' * 80)
    print()

    print('OPTION 1: Frontend-only fix (SIMPLE, but slower)')
    print('-' * 80)
    print('  - When user switches baseline, RE-CATEGORIZE symbols on frontend')
    print('  - Take the flat list of all symbols, filter by selected baseline')
    print('  - Rebuild col_20_plus, col_10_to_20, col_1_to_10 based on selected baseline')
    print('  - Pros: Simple, no backend changes')
    print('  - Cons: Frontend has to process all symbols on every switch')
    print()

    print('OPTION 2: Backend dynamic columns (PROPER, but requires API change)')
    print('-' * 80)
    print('  - Frontend tells backend which baseline to use')
    print('  - Backend fetches symbols and categorizes by THAT baseline')
    print('  - API endpoint already accepts "baseline" parameter, just not used correctly')
    print('  - Pros: Correct behavior, backend does the work')
    print('  - Cons: Need to update frontend to pass baseline param')
    print()

    print('OPTION 3: Gap direction toggle (NEW FEATURE)')
    print('-' * 80)
    print('  - Add dropdown: "Gap Ups" vs "Gap Downs"')
    print('  - Gap Ups: Sort by positive % moves (current behavior)')
    print('  - Gap Downs: Sort by negative % moves (largest drops first)')
    print('  - When "Gap Downs" selected, filter for symbols with negative %')
    print('  - Example: % YEST = -25%, -15%, -8% (largest drops first)')
    print()

    print('=' * 80)
    print('RECOMMENDATION')
    print('=' * 80)
    print()
    print('Do OPTION 2 (Backend dynamic columns):')
    print('  1. Frontend already has baseline dropdown (% YEST, % OPEN, etc.)')
    print('  2. Update frontend to pass "baseline" parameter to API')
    print('  3. Backend already categorizes by that baseline - just need to wire it up')
    print('  4. Add "direction" parameter for gap ups vs gap downs')
    print()
    print('Example API call:')
    print('  /symbols/leaderboard?threshold=1.0&baseline=open&direction=up')
    print('  /symbols/leaderboard?threshold=1.0&baseline=yesterday&direction=down')
    print()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_bug()
