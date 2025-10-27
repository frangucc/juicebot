# Murphy Momentum Trading Strategy
**Context:** Gap up stocks with bullish bias (JuiceBot strategy)

---

## 🎯 THE ACTUAL STRATEGY

### What We Tested (WRONG):
```
✗ Bidirectional swing trading over 7 days
✗ Equal weight to longs and shorts
✗ Hold until direction change or 50 bars
✗ Scale out at fixed profit targets
```

### What You Actually Do (RIGHT):
```
✓ Scan for gap up stocks premarket
✓ Enter LONG biased on bullish days
✓ Ride momentum moves
✓ Cover on pullbacks (take profits)
✓ Don't reverse to short unless very strong signal
```

---

## 🔄 EXECUTION ALGORITHM CHANGES

### 1. **Directional Bias System**

**Morning Scan Results:**
```python
session_bias = "BULLISH"  # From gap up scan
# OR
session_bias = "BEARISH"  # From gap down scan
# OR
session_bias = "NEUTRAL"  # Choppy day
```

**Signal Filtering Based on Bias:**

```python
if session_bias == "BULLISH":
    # LONG signals: More lenient
    if murphy_signal.direction == "↑":
        if murphy_signal.tier <= 2:  # Trade Tier 1-2 longs
            ENTER_LONG()
    
    # SHORT signals: Very strict
    if murphy_signal.direction == "↓":
        if murphy_signal.tier == 1:  # ONLY Premium shorts
            if murphy_signal.rejection_type:  # Must have rejection
                ENTER_SHORT()  # Counter-trend short
        else:
            SKIP()  # Don't fight the trend
```

**Current Test (WRONG):** Treated all signals equally regardless of market bias.

---

### 2. **Entry Timing: Trade the Pullbacks**

**OLD (Bidirectional):**
```python
if murphy_signal.passes_filter():
    ENTER_IMMEDIATELY()
```

**NEW (Momentum):**
```python
if session_bias == "BULLISH":
    if murphy_signal.direction == "↑":
        # Wait for pullback entry on longs
        if is_pullback_complete():
            ENTER_LONG()  # Buy the dip
    else:
        SKIP()  # Don't short into strength
```

**Pullback Detection:**
```python
def is_pullback_complete():
    # Price pulled back from recent high
    recent_high = max(last_20_bars.high)
    current_price = bar.close
    pullback_pct = (recent_high - current_price) / recent_high
    
    # Murphy shows bullish signal at support
    if pullback_pct > 0.02:  # 2%+ pullback
        if murphy.direction == "↑":
            if murphy.rejection_type or murphy.pattern:
                return True  # Buy the dip!
    
    return False
```

---

### 3. **Exit on Momentum Loss (NOT Direction Change)**

**OLD (Bidirectional):**
```python
if murphy.direction_changed():
    EXIT_POSITION()  # Wait for opposite signal
```

**NEW (Momentum):**
```python
# Exit on FIRST SIGN of momentum loss
if detect_momentum_loss():
    EXIT_POSITION()  # Don't wait for reversal!

def detect_momentum_loss():
    # Momentum indicators
    if volume_declining_3_bars():
        return True
    
    if price_consolidating():  # Sideways for 5+ bars
        return True
    
    if broke_rising_trendline():
        return True
    
    # Murphy shows NEUTRAL or weak opposing signal
    if murphy.direction == "−":
        return True
    
    if murphy.direction == opposite_of_position():
        if murphy.tier <= 2:  # Strong opposing signal
            return True
    
    return False
```

**Key Difference:** Exit EARLY when momentum fades, don't wait for full reversal.

---

### 4. **Scale In on STRENGTH (Not on gain %)**

**OLD (Bidirectional):**
```python
# Scale in at +1%, +2% gain
if position_pnl >= 1.0%:
    ADD_TO_POSITION()
```

**NEW (Momentum):**
```python
# Scale in when momentum ACCELERATES
if momentum_accelerating():
    ADD_TO_POSITION()  # Add to winners!

def momentum_accelerating():
    # Volume increasing
    if current_volume > avg_volume * 1.5:
        # Price making new highs
        if current_high > highest_high_last_10_bars:
            # Murphy still bullish
            if murphy.direction == "↑":
                return True
    
    return False
```

**Example: BYND Oct 20**
```
Bar 736: +12% on huge volume → ADD
Bar 737: +21% NEW HIGH      → ADD AGAIN
Bar 738: Pullback -9%       → HOLD (or partial exit)
```

---

### 5. **Scale Out on WEAKNESS (Not fixed targets)**

**OLD (Bidirectional):**
```python
# Take profits at +2%, +4%, +6%, +8%
if position_pnl >= 2.0%:
    EXIT_25%()
```

**NEW (Momentum):**
```python
# Take profits when momentum weakens
if first_sign_of_weakness():
    EXIT_30%()  # Lock in some gains

if momentum_clearly_fading():
    EXIT_50%()  # Take more off

if reversal_imminent():
    EXIT_100%()  # Get out!

def first_sign_of_weakness():
    # Volume drops below average
    if current_volume < avg_volume * 0.8:
        return True
    
    # Price fails to make new high
    if failed_breakout():
        return True
    
    # Murphy shows neutral
    if murphy.direction == "−":
        return True
    
    return False
```

---

### 6. **DON'T Reverse (Go Flat Instead)**

**OLD (Bidirectional):**
```python
if murphy_signal.direction != current_position.side:
    CLOSE_POSITION()
    REVERSE_TO_OPPOSITE_SIDE()  # Go short if was long
```

**NEW (Momentum):**
```python
if murphy_signal.direction != current_position.side:
    CLOSE_POSITION()
    GO_FLAT()  # Don't reverse!
    
    # Only re-enter if VERY strong signal in trend direction
    if session_bias == "BULLISH":
        # Wait for next long setup
        # Don't take shorts unless Premium + rejection
```

**Why?** On bullish gap up days, shorts are counter-trend and risky.

---

### 7. **Time-Based Rules**

```python
# Morning session (first 2 hours): Most momentum
if time_of_day() == "MORNING":
    TRADE_AGGRESSIVELY()
    scale_in_quickly = True
    let_winners_run = True

# Mid-day (lunch): Chop zone
elif time_of_day() == "MIDDAY":
    REDUCE_POSITION_SIZE()
    take_profits_early = True

# Power hour (last hour): Potential reversal
elif time_of_day() == "POWER_HOUR":
    BE_CAUTIOUS()
    tighten_stops = True
```

---

## 📊 EXAMPLE: BYND Oct 20 with NEW Strategy

### **OLD Strategy (Tested):**
```
Bar 736: Murphy ↑ Tier 2 → Enter long 40% @ $1.01
Bar 737: Price +21% → Add 30% @ $1.23
Bar 738: Price -9% → Hold (waiting for direction change)
Bar 740: Murphy ↓ Tier 2 → EXIT long, REVERSE to short @ $1.10
Result: Gave back all gains, then lost on short
```

### **NEW Strategy (Momentum):**
```
Pre-market: BYND gaps up +23% → session_bias = "BULLISH"

Bar 736: Murphy ↑ Tier 2 + volume spike
  → Enter 40% @ $1.01 (pullback from $1.02 high)

Bar 737: New high $1.24, volume 2x avg, Murphy still ↑
  → Add 30% @ $1.10 (on dip from $1.24)
  → Add 30% @ $1.20 (breakout)
  → Now 100% in

Bar 738: Volume drops, price pulls back to $1.11
  → First sign of weakness
  → EXIT 30% @ $1.15 (lock in gains)

Bar 739-741: Consolidation, volume declining
  → Momentum fading
  → EXIT 50% @ $1.08

Bar 742: Murphy shows neutral "−"
  → EXIT 20% @ $1.06 (nearly flat)
  
Result: Caught the run from $0.90-$1.24, scaled out $1.15-$1.06
        Avg exit $1.10 → +22% gain vs +10% open
```

---

## 🎯 UPDATED RISK MODES

### **Momentum-Aware Risk Modes:**

**LOW RISK (Conservative):**
- Trade ONLY Tier 1 signals IN TREND DIRECTION
- Quick profit taking (exit 50% at first weakness)
- No counter-trend trades
- Morning session only

**MEDIUM RISK (Balanced):**
- Trade Tier 1-2 signals WITH trend bias
- Standard profit taking (30/50/20)
- Premium counter-trend trades only
- Morning + early afternoon

**HIGH RISK (Aggressive):**
- Trade Tier 1-2 WITH trend, Tier 3 OK if strong
- Let winners run (hold through small pullbacks)
- Counter-trend trades if Tier 1 + rejection
- Full day trading

---

## 🔧 CODE CHANGES NEEDED

### 1. Add Session Bias Parameter:
```python
class TradingSimulatorV3:
    def __init__(self, session_bias="NEUTRAL"):
        self.session_bias = session_bias  # BULLISH, BEARISH, NEUTRAL
```

### 2. Bias-Aware Signal Filtering:
```python
def should_enter(self, signal):
    # Check trend alignment
    if self.session_bias == "BULLISH":
        if signal.direction == "↓":
            if signal.tier != 1 or not signal.rejection_type:
                return False  # Skip weak shorts on bullish day
    
    # Same for bearish days...
```

### 3. Momentum Exit Logic:
```python
def check_momentum_exit(self, bar_index, bars):
    # Check volume
    recent_volume = [b.volume for b in bars[-5:]]
    if bars[-1].volume < statistics.mean(recent_volume) * 0.8:
        return True, "volume_declining"
    
    # Check price action
    if self.is_consolidating(bars[-10:]):
        return True, "momentum_fading"
    
    return False, None
```

### 4. Re-Entry on Pullbacks:
```python
def check_pullback_reentry(self, signal, bars):
    if not self.position and signal.direction_matches_bias():
        if self.is_pullback_to_support(bars):
            if signal.tier <= 2:
                return True
    return False
```

---

## 💡 WHY THIS MATTERS

**Your Current Test Results:**
- Tested bidirectional over 7 days
- Lost -1.85% to -4.12%
- Win rate 24-30%

**What Should Have Been Tested:**
- Only LONG trades on Oct 20 (gap up day)
- Exit on momentum loss (not direction change)
- Don't reverse to short

**Expected Results with Momentum Strategy:**
- Catch the +37% morning run
- Exit around +20-30% avg
- Maybe 1-3 trades total that day
- Likely PROFITABLE

---

## 🚀 NEXT STEPS

1. **Re-run test with session bias:**
```bash
python murphy_regression_test_v3.py --bias bullish --date 2025-10-20
```

2. **Test ONLY gap up days:**
Filter dataset to days with >5% gap up

3. **Measure differently:**
- Success = catching 50%+ of the run
- Not: bidirectional win rate over weeks

---

**THE BOTTOM LINE:**
We built a Ferrari and tested it like a tractor. Murphy might be GREAT at momentum trading but TERRIBLE at bidirectional swing trading. We need to test the RIGHT strategy!

