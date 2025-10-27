"""
Quick script to analyze Murphy session accuracy
Run this to see immediate results without restarting
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load env
load_dotenv(Path(__file__).parent.parent / ".env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Get latest session
sessions = supabase.table("murphy_test_sessions")\
    .select("*")\
    .eq("status", "active")\
    .order("started_at", desc=True)\
    .limit(1)\
    .execute()

if not sessions.data:
    print("❌ No active sessions found")
    sys.exit(1)

session = sessions.data[0]
session_id = session['id']
symbol = session['symbol']

print(f"\n📊 MURPHY SESSION ANALYSIS - {symbol}")
print(f"Session: {session_id[:8]}...")
print(f"Started: {session['started_at']}")
print("=" * 60)

# Get all signals
signals = supabase.table("murphy_signal_records")\
    .select("*")\
    .eq("session_id", session_id)\
    .execute()

total = len(signals.data)
shown = len([s for s in signals.data if s['passed_filter']])
hidden = total - shown

print(f"\n📈 TOTALS:")
print(f"  Total Signals: {total}")
print(f"  Shown: {shown}")
print(f"  Hidden: {hidden}")

# Analyze by timeframe
for timeframe in ['5', '10', '20', '50']:
    col = f'result_{timeframe}_bars'
    pnl_col = f'pnl_at_{timeframe}_bars'

    evaluated = [s for s in signals.data if s.get(col)]
    if not evaluated:
        print(f"\n⏳ {timeframe}B: Not evaluated yet")
        continue

    correct = len([s for s in evaluated if s[col] == 'correct'])
    wrong = len([s for s in evaluated if s[col] == 'wrong'])
    neutral = len([s for s in evaluated if s[col] == 'neutral'])

    shown_eval = [s for s in evaluated if s['passed_filter']]
    hidden_eval = [s for s in evaluated if not s['passed_filter']]

    shown_correct = len([s for s in shown_eval if s[col] == 'correct'])
    hidden_correct = len([s for s in hidden_eval if s[col] == 'correct'])

    shown_acc = (shown_correct / len(shown_eval) * 100) if shown_eval else 0
    hidden_acc = (hidden_correct / len(hidden_eval) * 100) if hidden_eval else 0

    avg_pnl = sum(s[pnl_col] for s in evaluated) / len(evaluated) if evaluated else 0

    print(f"\n📊 {timeframe}B Results ({len(evaluated)} evaluated):")
    print(f"  ✓ Correct: {correct} ({correct/len(evaluated)*100:.1f}%)")
    print(f"  ✗ Wrong:   {wrong} ({wrong/len(evaluated)*100:.1f}%)")
    print(f"  ~ Neutral: {neutral} ({neutral/len(evaluated)*100:.1f}%)")
    print(f"  Avg P/L:   {avg_pnl:+.2f}%")
    print(f"  Shown Accuracy:  {shown_acc:.1f}%")
    print(f"  Hidden Accuracy: {hidden_acc:.1f}%")

# Grade analysis
print(f"\n🎯 GRADE ANALYSIS:")
grades = {}
for signal in signals.data:
    grade = signal['grade']
    if grade not in grades:
        grades[grade] = []
    grades[grade].append(signal)

for grade in sorted(grades.keys()):
    sigs = grades[grade]
    # Use 20B as reference
    eval_20 = [s for s in sigs if s.get('result_20_bars')]
    if not eval_20:
        continue
    correct_20 = len([s for s in eval_20 if s['result_20_bars'] == 'correct'])
    acc = (correct_20 / len(eval_20) * 100) if eval_20 else 0
    print(f"  [{grade}]: {len(sigs)} signals, {acc:.1f}% accurate @ 20B")

# Star analysis
print(f"\n⭐ STAR ANALYSIS:")
for stars in range(0, 5):
    sigs = [s for s in signals.data if s['stars'] == stars]
    if not sigs:
        continue
    eval_20 = [s for s in sigs if s.get('result_20_bars')]
    if not eval_20:
        continue
    correct_20 = len([s for s in eval_20 if s['result_20_bars'] == 'correct'])
    acc = (correct_20 / len(eval_20) * 100) if eval_20 else 0
    star_display = '★' * stars if stars > 0 else '☆'
    print(f"  {star_display}: {len(sigs)} signals, {acc:.1f}% accurate @ 20B")

# Early but right analysis
print(f"\n🎬 'EARLY BUT RIGHT' SIGNALS:")
early_right = [
    s for s in signals.data
    if s.get('result_5_bars') == 'wrong' and s.get('result_20_bars') == 'correct'
]
print(f"  Found {len(early_right)} signals wrong at 5B but correct at 20B")

if early_right:
    for sig in early_right[:3]:
        print(f"    - {sig['direction']} {'★' * sig['stars']} [{sig['grade']}] @ {sig['entry_price']:.2f}")

print("\n" + "=" * 60)
print("✅ Analysis complete!")
