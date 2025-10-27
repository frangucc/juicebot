# Momo Advanced - Trader Logic Encoded
**Date:** 2025-10-27
**Version:** 1.0

---

## 🎯 What Is Momo Advanced?

Momo Advanced is a **momentum trading system that thinks like a trader**, not just a statistical model. It combines:

1. **Multi-timeframe momentum** (YEST/PRE/OPEN/1H/15M/5M/1M)
2. **VWAP positioning** (value zone vs chasing)
3. **Synthetic shadow trading** (P&L as signal)
4. **Leg detection** (wave analysis)
5. **Time-of-day patterns** (when things happen)
6. **Reverse psychology** (do opposite when consistently wrong)

---

## 🧠 The Five Trader Logic Modules

### 1. VWAP Context - "Am I Chasing or Buying Value?"

```python
# Real trader thinking:
# "Stock ran to $1.20, VWAP is $1.10, now at $1.08"
# "I'm BELOW VWAP = buying value, not chasing!"

Distance from VWAP:
  < -5%:  DEEP_VALUE     → AGGRESSIVE_BUY
  -5 to -2%: VALUE       → BUY_PULLBACK
  -2 to +2%: FAIR        → NEUTRAL
  +2 to +5%: EXTENDED    → CHASE_WARNING
  > +5%:  EXTREME        → NO_BUY (too stretched)
```

**Example:**
```
Bar 756: Price $1.04, VWAP $1.05
Distance: -0.95% (just below VWAP)
Zone: FAIR
Action: Good entry point, not stretched
```

---

### 2. Synthetic Shadow Trading - "Where's the Support?"

```python
# Real trader thinking:
# "Let me buy 1 share at $1.10... now $1.08... now $1.06"
# "I'm down 4% but I'm accumulating LOWER each time"
# "This means I'm FINDING THE BOTTOM!"

Synthetic Entry Logic:
1. Buy 1 share at $1.10 (shadow trade)
2. Price drops to $1.08 → buy another
3. Price drops to $1.06 → buy another
4. Calculate: I'm down 3.8% unrealized
5. Pattern: Each entry was LOWER
6. Signal: STRONG_BUY (found support!)
```

**Key Insight:**
- The MORE you accumulate while losing, the BETTER the setup
- If you can keep buying LOWER, you're finding the floor
- When it bounces, you have perfect average

**Example:**
```
Entries: $1.10, $1.08, $1.06 (3 entries, descending)
Current: $1.07 (starting to bounce)
Unrealized P&L: -4.2%
Signal: STRONG_BUY (accumulated into support, now bouncing)
Confidence: 80% (3 entries * 10% each + 50% base)
```

---

### 3. Leg Detection - "What Wave Are We In?"

```python
# Real trader thinking:
# "Stock ran from $0.90 to $1.24 = Leg 1 (+37.8%)"
# "Pulled back to $1.10 = -11% from top"
# "This is prime for Leg 2!"

Leg Probabilities:
  Leg 1: 85% chance it happens (initial spike always goes)
  Leg 2: 65% chance (continuation is likely)
  Leg 3: 45% chance (still possible)
  Leg 4: 25% chance (getting rare)
  Leg 5+: 10% chance (very rare)

Pullback Sweet Spot:
  3-8% pullback from leg top = PRIME ENTRY for next leg
```

**Example:**
```
Leg 1: $0.90 → $1.24 (+37.8%, 30 bars)
Current: $1.10
Pullback: 11.3% from $1.24

Analysis:
- Current Leg: 1
- Next Leg Probability: 65%
- Pullback: 11.3% (a bit deep, but OK)
- In Pullback Zone: False (need 3-8%)

Wait for: Price to stabilize around $1.14-$1.18 (3-8% pullback zone)
```

---

### 4. Time-of-Day Patterns - "When Does This Happen?"

```python
# Real trader knowledge:
# "3-6am: Thin books, easy to run"
# "7am: ALWAYS a pullback"
# "8:30-9am: Open sweeps, chaos"
# "9-11am: PRIME TIME, continuation"
# "Lunch: Chop, avoid"
# "1-3pm: Power hour, second wind"

Time Periods:
  3-6am:   Premarket Early    → Bullish bias (thin books)
  6-7am:   Premarket Pullback → Bearish bias (expected)
  7-8:30am: Premarket Coil    → Neutral (coiling)
  8:30-9am: Market Open       → Volatile (sweeps)
  9-11am:  Morning Run        → Bullish (PRIME TIME!)
  11am-1pm: Lunch Chop        → Neutral (avoid)
  1-3pm:   Power Hour         → Bullish (second wind)
  3-4pm:   Close              → Neutral (positioning)
  4-8pm:   After Hours        → Bullish (thin continuation)
```

**Impact on Confidence:**
```python
if time == "morning_run":
    confidence += 10%  # Prime trading time!

if time == "lunch_chop":
    confidence -= 15%  # Avoid, choppy

if time == "premarket_pullback" and direction == "↓":
    confidence += 10%  # Expected bearish at 7am
```

**Example:**
```
Bar at 9:15am (Morning Run period)
Basic signal: ↑ (bullish)
Time bonus: +10% confidence
Reason: "Morning continuation period, prime time"
```

---

### 5. Reverse Psychology - "Do the Opposite When Consistently Wrong"

```python
# Real trader observation:
# "Every time I buy at 7am, I'm wrong"
# "10 signals at 7am, 9 were wrong"
# "What if I just do the OPPOSITE?"

Logic:
1. Track last 50 signals by time period
2. Calculate accuracy for each period
3. If accuracy < 35% for a period → INVERT signals!

Example:
- 7am signals: 12 bullish, 10 were wrong
- Accuracy: 16.7% (terrible!)
- Enable inversion rule for "premarket_pullback"
- New signal at 7am: System says "↑"
- INVERT TO: "↓"
- Reason: "Consistently wrong at 7am, doing opposite"
```

**This is advanced:** The system learns which times/conditions produce bad signals and automatically inverts them!

---

## 🎯 How Signals Are Combined

### The Decision Flow:

```python
def generate_signal():
    # Start neutral
    confidence = 50%

    # 1. VWAP Context
    if in_value_zone and bullish_alignment:
        confidence += 15-25%
        # "Buying value, not chasing"

    if in_extreme_zone:
        confidence -= 20%
        # "Too stretched, dangerous"

    # 2. Leg Context
    if in_pullback_zone and next_leg_prob > 60%:
        confidence += 20%
        # "Prime for next leg"

    # 3. Shadow Trading
    if accumulated_3_times_lower:
        confidence += 20%
        # "Found support via accumulation"

    # 4. Time Period
    if morning_run_time:
        confidence += 10%
        # "Prime trading time"

    if lunch_chop:
        confidence -= 15%
        # "Choppy period, avoid"

    # 5. Max Juice Bonus
    if 7_out_of_7_aligned:
        confidence += 10%
        # "All timeframes aligned"

    # 6. Reverse Psychology
    if consistently_wrong_at_this_time:
        INVERT_DIRECTION()
        # "Do opposite"

    return signal
```

---

## 📊 Real Example: BYND Oct 20, Bar 821

```python
Bar 821: 2025-10-20 04:28:00
Price: $1.03
VWAP: $1.15

# Analysis:

# 1. VWAP Context
distance = (1.03 - 1.15) / 1.15 = -10.4%
zone = "DEEP_VALUE"  # Way below VWAP!
action_bias = "AGGRESSIVE_BUY"

# 2. Leg Context
current_leg = 5
next_leg_prob = 10%  # Low (5th leg rare)
pullback = -10.4%
in_pullback_zone = False  # Too deep

# 3. Shadow Trading
entries = [$1.10, $1.08, $1.06, $1.03]  # 4 entries, descending
unrealized_pnl = -5.2%
signal = "STRONG_BUY"  # Accumulated 4x while dropping!

# 4. Time Period
time = "premarket_early" (4:28am)
behavior = "thin_books"
bias = "bullish"

# 5. Combine

confidence = 50%  # Start
  + 25%  # Deep value zone
  + 0%   # Leg 5 rare (no bonus)
  + 20%  # Shadow found support (4 entries)
  + 0%   # Premarket early (neutral)
  = 95%  # STRONG BUY!

final_signal = {
    direction: "↑",
    confidence: 95%,
    action: "STRONG_BUY",
    reason: "Deep value (-10.4% from VWAP) | Shadow found support (4 entries) | Thin premarket books"
}
```

**Interpretation:**
- Stock pulled back DEEP (-10% from VWAP)
- We synthetically accumulated 4 times while it dropped
- Each entry was LOWER (finding support)
- Now at deep value zone
- **Signal: STRONG BUY with 95% confidence!**

---

## 💡 Why This Works Better Than Basic Indicators

### Basic Indicator (Murphy/Momo):
```
"Price moving up + volume high = bullish signal"
```

### Momo Advanced:
```
"Price pulled back 8% to VWAP (value zone)
 + I accumulated 3 times while dropping (found support)
 + After 37% Leg 1, now in prime pullback zone (65% chance of Leg 2)
 + It's 9:15am (morning run, prime time)
 + 6 out of 7 timeframes aligned (strong juice)
 = 85% confidence STRONG BUY"
```

**The difference:** Context, pattern recognition, trader intuition encoded.

---

## 🎯 How to Use Momo Advanced

### For Entry Decisions:

```python
signal = momo_advanced.classify(bars, current_index)

if signal.action == "STRONG_BUY":
    if signal.vwap_context.zone in ["VALUE", "DEEP_VALUE"]:
        # Buying value, not chasing
        ENTER_LARGE()

elif signal.action == "BUY":
    if signal.leg_context.in_pullback_zone:
        # Prime for next leg
        ENTER_MEDIUM()

elif signal.action == "WAIT":
    # Neutral, wait for better setup
    HOLD_CASH()
```

### For Position Sizing:

```python
base_size = $5000

# Adjust by confidence
adjusted_size = base_size * signal.confidence

# Examples:
# 95% confidence → $4,750 (near full size)
# 65% confidence → $3,250 (medium size)
# 45% confidence → $2,250 (small size)
```

### For Exit Decisions:

```python
if in_position:
    signal = momo_advanced.classify(bars, current_index)

    # Exit on extreme extension
    if signal.vwap_context.zone == "EXTREME":
        EXIT_PARTIAL()  # Take profits, too stretched

    # Exit on confidence drop
    if signal.confidence < 0.40:
        EXIT_ALL()  # Confidence collapsed

    # Exit on leg exhaustion
    if signal.leg_context.current_leg >= 4:
        if signal.leg_context.next_leg_probability < 0.30:
            EXIT_ALL()  # 4th leg, unlikely to continue
```

---

## 🔧 Configuration Options

```python
# Initialize with custom settings
momo = MomoAdvanced()

# Shadow trader settings
momo.shadow_trader = SyntheticTracker(max_entries=5)

# Leg detector settings
momo.leg_detector = LegDetector(min_leg_magnitude=5.0)  # 5% min leg

# Reverse detector history
momo.reverse_detector = ReverseSignalDetector(history_size=50)
```

---

## 📈 Expected Performance

### Compared to Basic Momo:

**Basic Momo:**
- 41.0% accuracy at 20 bars
- 47.8% accuracy at 50 bars
- No context awareness

**Momo Advanced:**
- Expected: 50-55% accuracy (improved by context)
- Confidence scoring helps position sizing
- Better entries (value zones, pullbacks)
- Better exits (extension detection)

### Best Use Cases:

✅ Gap-up momentum days
✅ Trending days with legs
✅ VWAP-respecting price action
✅ Morning session (9-11am)

❌ Range-bound chop
❌ Lunch period (11am-1pm)
❌ Low volume after hours

---

## 🚀 Next Steps

### Testing:

1. **Run on BYND Oct 20 with full analysis**
   ```bash
   python momo_advanced.py --data bynd_historical_data.json --date 2025-10-20
   ```

2. **Compare to basic Momo accuracy**
   - Test both systems side-by-side
   - Measure if trader logic improves accuracy

3. **Backtest with execution strategy**
   - Pair with Accumulation strategy
   - Use confidence for position sizing
   - Track actual P&L

### Integration:

```python
# In your trading system
from momo_advanced import MomoAdvanced

momo = MomoAdvanced()

# On each bar
signal = momo.classify(bars, current_index, yesterday_close)

# Use signal
if signal.action == "STRONG_BUY":
    size = calculate_size(signal.confidence)
    enter_long(symbol, size)

# Track outcomes (for reverse psychology)
momo.reverse_detector.track_signal(
    timestamp=bar.timestamp,
    period=signal.time_period.period,
    signal_type="momentum",
    direction=signal.direction,
    was_correct=check_if_correct(signal, bars)
)
```

---

## 💬 The Trader Philosophy

This system encodes real trader thinking:

> "I don't just look at if it's going up. I ask:
> - Am I buying value or chasing?
> - Have I found support by accumulating lower?
> - What leg are we in?
> - Is it the right time of day?
> - Am I consistently wrong at this time?"

**This is the hybrid human-machine approach:**
- Machine tracks patterns (multi-timeframe, VWAP, legs)
- Human logic encoded (value zones, accumulation, time patterns)
- Learning system (reverse psychology)
- Context-aware decisions (not just statistics)

---

**END OF GUIDE**
