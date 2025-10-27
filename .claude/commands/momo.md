---
description: Get Momo's momentum reading for current chart context
---

# Momo Momentum Classifier Analysis

Run Momo's multi-timeframe momentum classifier on current chart context.

---

**Usage**: `/momo [symbol] [price]`

**Example**: `/momo BYND 1.15`

---

## Task:

1. Get the symbol and price from arguments (or use BYND and latest price if not provided)
2. Call the Momo API: `POST http://localhost:8000/momo/classify`
   ```json
   {
     "bars": [...],
     "yesterday_close": 0.90
   }
   ```
3. Display Momo's analysis in a clear format:
   - Direction arrow (↑/↓/−)
   - Stars rating (5-7, multi-timeframe alignment)
   - Confidence percentage
   - Action (STRONG_BUY, BUY, WAIT, SELL, STRONG_SELL)
   - VWAP zone (DEEP_VALUE, VALUE, FAIR, EXTENDED, EXTREME)
   - Current leg + next leg probability
   - Time period + bias

## Expected Output Format:

```
🚀 Momo Analysis for BYND @ $1.15

Direction: ↑ (Bullish)
Stars: ★★★★★★★ (7/7 alignment - MAX JUICE!)
Confidence: 85%
Action: STRONG_BUY

📊 VWAP Context:
  Zone: VALUE
  Distance: -3.2% below VWAP
  Assessment: Buying value, not chasing

🌊 Leg Analysis:
  Current Leg: 1
  Next Leg Probability: 65%
  In Pullback Zone: Yes (prime for leg 2)

⏰ Time Context:
  Period: morning_run (9:15 AM)
  Bias: Bullish (prime trading time)

💡 Interpretation:
Strong bullish momentum across all 7 timeframes. Currently in value zone below VWAP - excellent entry opportunity. After initial leg up, now in prime pullback zone for continuation. Morning session provides optimal timing.

Multi-Timeframe Breakdown:
  YEST: +38.4% ✓
  PRE:  +0.6%  ✓
  OPEN: +57.8% ✓
  1H:   +43.0% ✓
  15M:  +37.5% ✓
  5M:   +42.3% ✓
  1M:   +38.5% ✓
```

Do NOT use AI reasoning or LLM processing - this is a direct API call and formatting task only.
