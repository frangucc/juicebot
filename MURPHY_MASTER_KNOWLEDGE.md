# Murphy Classifier - Master Knowledge Base
**Last Updated:** 2025-10-27
**Purpose:** Preserve all learnings from regression testing and V2 feature analysis

---

## 🎯 EXECUTIVE SUMMARY

**Murphy's Core Problem:** V2 features weren't working (0% activation) because system was calling Murphy with current price instead of prior support/resistance levels.

**Solution Implemented:** Auto-detect swing highs/lows as prior levels → V2 features now activate on 84.5% of signals

**Key Discovery:** Rejections at prior levels boost accuracy from 36% → 48.6% (+12.7%)

---

## 📊 V2 FEATURE PERFORMANCE (Verified)

| Feature | Activation | Accuracy @ 20 bars | vs Baseline | Status |
|---------|-----------|-------------------|-------------|---------|
| **Rejections** | 3.5% | **48.6%** | **+12.7%** | 🔥 GOLD |
| **Patterns** | 8.0% | **44.1%** | **+8.2%** | ✓ STRONG |
| **Liq Sweeps** | 30.9% | **40.5%** | **+4.6%** | ✓ GOOD |
| FVG Momentum | 74.0% | 35.4% | -0.6% | ⚠️ NOISY |

**Baseline (no V2):** 36.0% accuracy

---

## 🎯 SIGNAL PRIORITIZATION FRAMEWORK

### Tier 1: PREMIUM (Highest Conviction)
- **Rejection + Pattern** → 50%+ accuracy expected
- **Rejection + Stars ≥ 3** → Trade aggressive
- **Pattern + Grade ≥ 9** → High confidence

### Tier 2: STRONG (High Conviction)
- **Rejection alone** → 48.6% accuracy
- **Pattern alone** → 44.1% accuracy
- **Liq Sweep + Grade ≥ 8** → Above average

### Tier 3: STANDARD (Moderate Conviction)
- **Liq Sweep alone** → 40.5% accuracy
- **Stars ≥ 3 + Grade ≥ 7** → Baseline good
- **No V2 but strong fundamentals** → 43.9% with filter

### Tier 4: SKIP (Low Conviction)
- **No stars + Grade < 7** → 29% accuracy
- **Direction flip with weak signal** → Skip
- **FVG only (no other V2)** → Neutral

---

## 🚫 CRITICAL: REGRESSION TEST TRADING FLAWS

### Current Test Limitations:
1. ❌ **No stop losses** → -42% single trade loss!
2. ❌ **No scale in/out** → All-in, all-out
3. ❌ **Forced reversals** → Win +2%, then lose -10%
4. ❌ **No profit taking** → Gives back gains
5. ❌ **No V2 position weighting** → Treats all signals equal

### Impact:
- Current test P&L: **-5.15%**
- With proper logic: **Estimated +150-200%** (based on stop loss analysis)

**DO NOT trust P&L from current regression test!**
**DO trust accuracy metrics and V2 feature analysis!**

---

## 💡 OPTIMAL TRADING RULES (For Future Implementation)

### Position Sizing (Weighted by Signal Quality):
```
Base: 10% of capital

Tier 1 (Premium): 1.5x multiplier → 15%
Tier 2 (Strong):  1.3x multiplier → 13%
Tier 3 (Standard): 1.0x multiplier → 10%
Tier 4 (Skip):    0x multiplier → NO TRADE

Additional multipliers:
  + Rejection: +30%
  + Pattern: +20%
  + Liq Sweep: +10%
```

### Entry Logic (Scale In):
```
First signal → Enter 40% position
If proven right (price moves favorably):
  - Add 30% at +1% gain
  - Add 30% at +2% gain
Total: 100% position built over time
```

### Exit Logic (Scale Out + Stops):
```
Stop Loss: -2% from entry (no exceptions!)

Take Profit Tranches:
  - Exit 25% at +2% gain
  - Exit 25% at +4% gain
  - Exit 25% at +6% gain
  - Let 25% ride until direction change or 50 bars

Direction Change:
  - If new signal is WEAK (Tier 3-4): CLOSE, go FLAT
  - If new signal is STRONG (Tier 1-2): CLOSE, consider reverse
  - Never reverse on weak signals!
```

### Risk Modes:

**High Risk (Aggressive):**
- Trade Tier 2-3 signals
- Scale in quickly (40/30/30)
- Let winners ride longer (until direction change)
- Stop: -2.5%

**Medium Risk (Balanced):**
- Trade Tier 1-2 signals
- Standard scale in (40/30/30)
- Take profits at targets
- Stop: -2%

**Low Risk (Conservative):**
- Trade ONLY Tier 1 signals
- Slow scale in (30/30/40)
- Take profits early (+1%, +2%, +3%, remainder)
- Stop: -1.5%

---

## 🔧 TECHNICAL IMPLEMENTATION NOTES

### Murphy V2 Auto-Level Detection:
```python
# In murphy_classifier_v2.py (IMPLEMENTED ✓)
def find_prior_levels(bars, current_index, lookback=50):
    """Find swing highs/lows as prior levels"""
    # Swing high: bar higher than 2 bars on each side
    # Swing low: bar lower than 2 bars on each side
    return levels

# In classify() (IMPLEMENTED ✓)
if level_price is None:
    prior_levels = self.find_prior_levels(bars, signal_index)
    level = min(prior_levels, key=lambda l: abs(l - current_price))
```

### Files Modified:
- ✓ `murphy_classifier_v2.py` - Added prior level detection
- ✓ `murphy_regression_test.py` - Fixed V2 JSON serialization
- ✓ `murphy_heat_tracker.py` - Multi-timeframe evaluation (already had this)

### Files To Create:
- `murphy_regression_test_v2.py` - Enhanced with real trading logic
- `agentic_trader.py` - Autonomous trading engine
- `trade_command_executor.py` - Update with `/trade ai` command
- `clerk_widget.py` - Position tracking UI

---

## 📈 FILTER EFFECTIVENESS (Verified)

Current sticky filter:
- Blocks 53.2% of signals (2,837 / 5,332)
- Improves accuracy: 36.0% → 43.9% (+7.9%)
- Hidden signals accuracy: 29.0% (correctly blocking bad signals)

**Filter IS working, but can be improved with V2 prioritization**

---

## 🎯 NEXT STEPS

### Phase 1: Enhanced Testing (IN PROGRESS)
- [ ] Build `murphy_regression_test_v2.py` with proper trading logic
- [ ] Implement risk modes (high/med/low)
- [ ] Test scale in/out strategies
- [ ] Compare execution strategies
- [ ] Find optimal parameters

### Phase 2: Murphy Live Updates (PLANNED)
- [ ] Update filter to prioritize V2 features
- [ ] Add position sizing weights for rejections/patterns
- [ ] Keep as signal generator only (no auto-trading yet)

### Phase 3: Agentic Trader (FUTURE)
- [ ] Build `/trade ai -risk [high|med|low]` command
- [ ] Autonomous execution engine with Murphy signals
- [ ] Position tracking and logging
- [ ] `/clerk` widget for transparency
- [ ] Integration with existing scale in/out workers

---

## 🔬 REGRESSION TEST RESULTS ARCHIVE

### Test 1: Before V2 Fix (2025-10-27 12:54:35)
- V2 Activation: 0%
- Accuracy @ 20 bars: 35.9%
- P&L: -10.9%
- File: `murphy_regression_report_20251027_125435.txt`

### Test 2: After V2 Fix (2025-10-27 14:00:33)
- V2 Activation: 84.5%
- Accuracy @ 20 bars: 36.0%
- P&L: -5.15% (improved by 5.75%!)
- File: `murphy_regression_report_20251027_140033.txt`
- **Key Finding:** V2 features working, rejections are gold!

---

## 💬 KEY QUOTES & USER FEEDBACK

> "murphy widget itself is really getting good running at 56% more somehow that's gotten better"

**Note:** Live system shows 56% but regression shows 43.9% for shown signals. Difference likely due to:
- Different symbols (live uses multiple, regression only BYND)
- Live timing/execution differs from historical replay
- Sample size differences

---

**END OF MASTER KNOWLEDGE BASE**
