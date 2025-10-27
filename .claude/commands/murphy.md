---
description: Get Murphy's market reading for current chart context
---

# Murphy Classifier Analysis

Run Murphy's classifier on current chart context to get market reading.

---

**Usage**: `/murphy [symbol] [price]`

**Example**: `/murphy BYND 0.66`

---

## Task:

1. Get the symbol and price from arguments (or use BYND and latest price if not provided)
2. Call the Murphy API: `POST http://localhost:8000/murphy/classify`
   ```json
   {
     "symbol": "BYND",
     "structure_price": 0.66,
     "signal_type": "bos_bullish"
   }
   ```
3. Display Murphy's analysis in a clear format:
   - Direction arrow (↑/↓/−)
   - Stars rating (****)
   - Grade [1-10]
   - Interpretation
   - V2 enhancements (liquidity sweeps, rejections, patterns, FVG momentum)

## Expected Output Format:

```
🔍 Murphy Analysis for BYND @ $0.66

Direction: ↑ (Bullish)
Rating: **** (4 stars)
Grade: [8]
Confidence: 1.45

📊 Interpretation:
Strong bullish momentum with volume confirmation.
Heavy FVG support below creates upward magnetism.

✨ V2 Enhancements:
  • Liquidity Sweep: No
  • Rejection: bullish_rejection
  • Pattern: None
  • FVG Momentum: magnetism_up
```

Do NOT use AI reasoning or LLM processing - this is a direct API call and formatting task only.
