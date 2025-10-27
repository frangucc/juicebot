# Murphy Regression Test Findings
**Date:** 2025-10-27
**Dataset:** BYND - 5,352 bars (Oct 17-24, 2025)
**Test:** murphy_regression_test.py

---

## 🚨 CRITICAL PROBLEMS IDENTIFIED

### 1. **Overall Performance: BELOW RANDOM**
- **Overall Accuracy @ 20 bars: 35.9%** (worse than 50% random)
- **Best Filtered Accuracy: 48.5%** (still below random!)
- **Trading Simulation: -10.9% loss** on $100k capital
- **Win Rate: 35.6%** (need 50%+ minimum)

### 2. **Signal Spam: Firing on Almost Every Bar**
- **5,332 signals on 5,352 bars = 99.6% density**
- Current filter reduces to 47.5% density (still way too high)
- Optimal filter achieves 12.1% density but accuracy still poor

### 3. **Grade [10] is OVERFITTING**
- Grade [10]: 45.3% accuracy, confidence 0.245 (overconfident)
- Grade [9]: 50.2% accuracy, confidence 0.055 (realistic)
- **The "perfect" signals are performing WORSE**

### 4. **V2 Features Completely Broken**
All V2 enhancements show **0% usage** on 5,332 signals:
- ❌ Liquidity Sweeps: 0/5332 (0.0%)
- ❌ Rejections: 0/5332 (0.0%)
- ❌ Patterns: 0/5332 (0.0%)
- ❌ FVG Momentum: 0/5332 (0.0%)

**These features were supposed to improve accuracy but aren't working at all!**

---

## ✅ WHAT'S WORKING (Barely)

### Stars Are The Most Predictive Feature
- **ANY stars (★+): ~48% accuracy**
- **NO stars (☆): 24% accuracy**
- Stars are 2x more predictive than no stars

### Current Filter Is Helping
- Shown signals: 43.3%
- Hidden signals: ~28%
- Filter is correctly blocking worse signals

### 537 "Early But Right" Signals Detected
- Wrong at 5 bars, correct at 20 bars
- These might reveal optimal entry timing patterns

---

## 📊 OPTIMAL FILTER RECOMMENDATIONS

Based on regression testing, best filter combinations:

| Filter | Accuracy | Signals | Density |
|--------|----------|---------|---------|
| **Current** | 43.3% | 2,543 | 47.5% |
| **Stars >= 2** | 48.0% | 1,396 | 26.1% |
| **Stars >= 3** | 47.8% | 687 | 12.8% |
| **Stars >= 2 AND Grade >= 8** | 48.2% | 1,248 | 23.3% |
| **Stars >= 3 AND Grade >= 8** ⭐ | 48.5% | 650 | 12.1% |

**Recommended: "Stars >= 3 AND Grade >= 8"**
- Most selective (12.1% density)
- Best accuracy (48.5%)
- Still below 50% - **filtering alone won't fix this**

---

## 🎯 ACTION PLAN TO FIX MURPHY

### Priority 1: Fix V2 Feature Architecture (ROOT CAUSE FOUND ✅)

**ROOT CAUSE:** Murphy is being called with the **current price** as `level_price`, but V2 features are designed to detect interactions with **prior support/resistance levels**.

**Current (broken) usage:**
```python
murphy.classify(
    bars=bars,
    signal_index=len(bars) - 1,
    structure_age_bars=10,
    level_price=data['price']  # ❌ Current bar's close price
)
```

**Intended (correct) usage:**
```python
murphy.classify(
    bars=bars,
    signal_index=250,
    structure_age_bars=10,
    level_price=0.66  # ✅ An actual prior support/resistance level
)
```

**Why V2 features never trigger:**
- **Liquidity Sweep:** Checks if price swept through `level_price` then reversed. Can't sweep through current price!
- **Rejection:** Checks if price rejected from `level_price` with wick. Can't reject from current close!
- **FVG Momentum:** Checks if gaps are near `level_price`. Current price has no context!

**Solutions:**

**Option A: Auto-detect prior levels** (RECOMMENDED)
```python
# In murphy_classifier_v2.py
def find_prior_levels(bars: List[Bar], lookback: int = 50) -> List[float]:
    """Find swing highs/lows as prior levels"""
    levels = []
    for i in range(len(bars) - lookback, len(bars)):
        if i < 2 or i >= len(bars) - 2:
            continue
        bar = bars[i]
        # Swing high
        if bar.high > bars[i-1].high and bar.high > bars[i-2].high and \
           bar.high > bars[i+1].high and bar.high > bars[i+2].high:
            levels.append(bar.high)
        # Swing low
        if bar.low < bars[i-1].low and bar.low < bars[i-2].low and \
           bar.low < bars[i+1].low and bar.low < bars[i+2].low:
            levels.append(bar.low)
    return levels

def classify(self, bars, signal_index, structure_age_bars, level_price=None):
    # If no level provided, auto-detect nearest prior level
    if level_price is None:
        prior_levels = self.find_prior_levels(bars, 50)
        current_price = bars[signal_index].close
        # Find nearest level
        level_price = min(prior_levels, key=lambda l: abs(l - current_price))

    # Continue with classification...
```

**Option B: Test multiple levels**
```python
# Test each prior level and aggregate signals
prior_levels = find_prior_levels(bars, 50)
best_signal = None
for level in prior_levels:
    signal = murphy.classify(bars, signal_index, structure_age_bars, level)
    if signal.grade > (best_signal.grade if best_signal else 0):
        best_signal = signal
```

**Option C: Make V2 features work without level_price**
Redesign V2 features to work with current bar context only:
- Liquidity Sweep → detect recent swing high/low breaks
- Rejection → detect large wicks on current bar
- FVG → detect gaps relative to recent bars, not fixed level

**Action:** Implement Option A (auto-detect prior levels) as it preserves V2 design intent.

### Priority 2: Fix Grade Calculation (grade [10] Overfits)
Current grading logic is too sensitive. Grade [10] requires too many conditions.

**Hypothesis:** Murphy uses additive scoring where:
- BOS = +1-3 points
- CHoCH = +1-3 points
- Liquidity sweep = +bonus (but this never triggers!)
- etc.

Grade [10] = needs ALL conditions perfect = overfitting

**Action:** Review `calculate_grade()` method in murphy_classifier_v2.py

### Priority 3: Reduce Signal Spam
Murphy fires on 99.6% of bars. This is noise, not signal.

**Recommendation:** Add minimum thresholds INSIDE the classifier:
```python
# In murphy_classifier_v2.py classify() method
if signal.stars < 2 and signal.grade < 7:
    return NeutralSignal()  # Don't even generate signal
```

### Priority 4: Analyze "Early But Right" Signals
537 signals were wrong at 5 bars but correct at 20 bars.

**These might reveal:**
- Strong levels take time to prove right
- Optimal entry delay (wait 5-10 bars after signal?)
- Better understanding of market microstructure

**Action:** Create script to analyze these 537 signals in detail.

---

## 🔬 TECHNICAL DEEP DIVE

### Accuracy By Bar Range
No significant degradation - consistently poor across all ranges:

| Bar Range | Accuracy | Shown Accuracy |
|-----------|----------|----------------|
| 0-256 | 36.9% | 43.8% |
| 257-512 | 36.1% | 40.8% |
| 513-1000 | 29.2% | 38.8% |
| 1001-2000 | 35.5% | 44.4% |
| 2001+ | 36.9% | 43.9% |

**Insight:** User reported Murphy "started failing after bar 256" - but data shows consistent poor performance throughout. The issue isn't degradation, it's baseline poor accuracy.

### Accuracy By Grade @ 20 Bars
| Grade | Signals | Accuracy |
|-------|---------|----------|
| [10] | 747 | 45.3% ⚠️ |
| [9] | 453 | 50.2% ✓ |
| [8] | 1,538 | 43.1% |
| [7] | 790 | 38.0% |
| [6] | 969 | 29.2% |
| [5] | 835 | 12.1% |

### Accuracy By Stars @ 20 Bars
| Stars | Signals | Accuracy |
|-------|---------|----------|
| ★★★★ | 445 | 47.4% |
| ★★★ | 242 | 48.5% |
| ★★ | 709 | 48.1% |
| ★ | 1,218 | 48.4% |
| ☆ | 2,718 | 24.1% |

---

## 💡 WHY LIVE WIDGET SHOWS 56% BUT REGRESSION SHOWS 43%

**Possible explanations:**
1. **Different symbols** - BYND might be harder to predict than other symbols
2. **Live filter is stricter** - Murphy Live applies "sticky directional logic"
3. **Evaluation timing** - Live system might use different bar counting
4. **Sample size** - Live might be cherry-picking better entry points

**Recommendation:** Run regression test on multiple symbols to see if BYND is an outlier.

---

## 📁 FILES GENERATED

1. **murphy_regression_report_20251027_125435.txt** - Full report
2. **murphy_signals_20251027_125435.json** - All 5,332 signals with results
3. **MURPHY_REGRESSION_FINDINGS.md** - This document

---

## 🚀 NEXT STEPS

1. ✅ **Regression test complete** - Identified fundamental flaws
2. 🔧 **Debug V2 features** - Figure out why they never trigger
3. 🔧 **Fix grade calculation** - Prevent grade [10] overfitting
4. 🔧 **Reduce signal spam** - Add stricter thresholds in classifier
5. 🔬 **Analyze "early but right"** - Extract insights from 537 signals
6. 🧪 **Test on multiple symbols** - See if BYND is representative
7. 🎨 **Update live widget** - Apply optimal filter (Stars >= 3 AND Grade >= 8)

---

## 💬 USER FEEDBACK VALIDATION

**User said:** "murphy widget itself is really getting good running at 56%"
**Regression shows:** 43.3% for shown signals (35.9% overall)

**User said:** "signals themselves were pretty dang good around bar 256 they started failing a little"
**Regression shows:** Consistent 30-37% accuracy across all bar ranges

**Conclusion:** Either:
- Live system is working better than historical replay
- User's perception is optimistic
- BYND is a particularly hard symbol
- Need to test on live data to validate

---

**END OF REPORT**
