# SMC Confidence Scoring System
## World-Class Trading Agent - Pattern Detection & Prediction Tracking

### Overview
Adaptive pattern detection with confidence scoring (1-10 scale) that accounts for:
- Data quality (bar count, time coverage)
- Pattern characteristics (size, volume, recency)
- Market context (confluence, respect for technicals)

---

## 1. Confidence Scoring Framework

### FVG (Fair Value Gap) Confidence Factors
**Starting Score: 10.0**

Deductions:
- **Gap Size**:
  - < 0.2% of price: -3.0 (too small, noise)
  - 0.2-0.3%: -1.5 (marginal)
  - > 0.3%: No deduction (tradeable)

- **Age (Recency)**:
  - > 40 bars ago: -2.0 (stale)
  - 20-40 bars: -1.0 (aging)
  - < 20 bars: No deduction (fresh)

- **Volume Confirmation**:
  - Gap formed on <80% avg volume: -1.5 (weak)

- **Distance from Current Price**:
  - > 5% away: -2.0 (irrelevant)
  - 2-5%: -1.0 (distant)
  - < 2%: No deduction (actionable)

**Final Score**: max(1.0, calculated_score)

---

### BoS (Break of Structure) Confidence Factors
**Starting Score: 10.0**

Deductions:
- **Structure Significance**:
  - Break < 1% from swing: -2.0 (minor)
  - Break 1-2%: -1.0 (moderate)
  - Break > 2%: No deduction (major)

- **Volume Strength**:
  - Break on <100% avg volume: -2.5 (weak)
  - Break on 100-150%: -1.0 (normal)
  - Break on >150%: +1.0 bonus (strong confirmation)

- **Age**:
  - > 30 bars ago: -2.0
  - 15-30 bars: -1.0
  - < 15 bars: No deduction

- **Subsequent Price Action**:
  - Price retraced >50% of break: -2.0 (failed)
  - Price holding above/below: No deduction

**Additional Bonuses**:
- **Confluence with FVG**: +1.5
- **Multiple swings broken**: +1.0

---

### CHoCH (Change of Character) Confidence Factors
**Starting Score: 10.0**

Deductions:
- **Trend Strength Before Break**:
  - Weak trend (ranging): -2.0 (unreliable reversal signal)
  - Moderate trend: -1.0
  - Strong trend: No deduction (significant reversal)

- **Counter-trend Volume**:
  - <120% avg volume: -2.0 (weak reversal)
  - 120-150%: -1.0
  - >150%: No deduction

- **Multiple Timeframe Confirmation**:
  - No higher TF confirmation: -1.5
  - Higher TF agrees: +1.0 bonus

---

## 2. Data Quality Scoring

### Quality Score (1-10)
```
quality_score = min(10.0, total_bars / 20)
```

**Interpretation**:
- **1-3**: Very limited data (<60 bars). High risk, low probability.
- **4-6**: Moderate data (60-120 bars). Decent patterns visible.
- **7-8**: Good data (120-160 bars). Reliable pattern detection.
- **9-10**: Excellent data (180+ bars). High confidence analysis.

### Time Coverage
- 1-min bars: `time_coverage = bar_count` minutes
- Expected: 150+ bars for intraday = 2.5+ hours of price action

### Data Quality Warnings
LLM should communicate:
```
"⚠️ Limited data (50 bars = 50min). Risk higher, probabilities lower. Score: 3/10"
"✓ Good data (180 bars = 3hrs). Patterns reliable. Score: 9/10"
```

---

## 3. Overall Pattern Confidence

### Combined Confidence
```
overall_confidence = (
    (data_quality_score + best_pattern_score) / 2
)
```

### Confluence Multiplier
When multiple patterns align:
```
if FVG + BoS at same price level:
    overall_confidence *= 1.2  # 20% boost

if FVG + BoS + Volume surge:
    overall_confidence *= 1.3  # 30% boost
```

### Example Output
```json
{
  "patterns": [
    {
      "type": "bullish FVG",
      "entry": 0.5670,
      "confidence": 8.5,
      "gap_pct": 0.45,
      "bars_ago": 12
    }
  ],
  "confluence": {
    "bos_nearby": true,
    "volume_confirmation": true,
    "confluence_score": 9.2
  },
  "data_quality": {
    "bars": 150,
    "quality_score": 7.5,
    "warning": null
  },
  "overall_confidence": 8.4,
  "probability_of_success": "70-75%"
}
```

---

## 4. Prediction Tracking Database

### Table: `trade_predictions`

```sql
CREATE TABLE trade_predictions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- LLM Prediction
    prediction_type TEXT NOT NULL,  -- 'entry_suggestion', 'exit_suggestion', 'analysis'
    direction TEXT,  -- 'long', 'short', 'neutral'
    entry_price DECIMAL(10, 4),
    stop_loss DECIMAL(10, 4),
    take_profit DECIMAL(10, 4),
    risk_reward_ratio DECIMAL(5, 2),

    -- Pattern Data (JSON)
    patterns_detected JSONB,  -- FVG, BoS, CHoCH details

    -- Confidence Scores
    pattern_confidence DECIMAL(3, 1),  -- 1-10
    data_quality_score DECIMAL(3, 1),  -- 1-10
    overall_confidence DECIMAL(3, 1),  -- 1-10

    -- Market Context at Time of Prediction
    price_at_prediction DECIMAL(10, 4),
    volume_at_prediction BIGINT,
    bars_available INTEGER,

    -- Outcome Tracking (filled later by reinforcement learning)
    outcome_evaluated BOOLEAN DEFAULT FALSE,
    outcome_timestamp TIMESTAMP WITH TIME ZONE,
    price_movement_24h DECIMAL(5, 2),  -- % move in 24 bars
    max_favorable_excursion DECIMAL(5, 2),  -- MFE %
    max_adverse_excursion DECIMAL(5, 2),  -- MAE %
    hit_take_profit BOOLEAN,
    hit_stop_loss BOOLEAN,
    actual_outcome TEXT,  -- 'win', 'loss', 'breakeven', 'not_triggered'

    -- Reinforcement Learning
    prediction_accuracy_score DECIMAL(5, 2),  -- How accurate was this prediction?

    INDEX idx_predictions_symbol (symbol),
    INDEX idx_predictions_timestamp (timestamp),
    INDEX idx_predictions_outcome (outcome_evaluated, symbol)
);
```

### Prediction Storage Flow

1. **When LLM suggests entry**:
```python
await store_prediction({
    "conversation_id": conv_id,
    "symbol": "BYND",
    "prediction_type": "entry_suggestion",
    "direction": "long",
    "entry_price": 0.5670,
    "stop_loss": 0.5620,
    "take_profit": 0.5850,
    "patterns_detected": {
        "fvg": {"type": "bullish", "confidence": 8.5},
        "bos": {"type": "bullish", "confidence": 7.2}
    },
    "overall_confidence": 8.4,
    "price_at_prediction": 0.5685
})
```

2. **24-48 bars later (automated job)**:
```python
# Evaluate outcome
prediction = get_prediction(id)
bars_since = get_bars_since(prediction.timestamp, count=48)

# Calculate metrics
mfe = calculate_max_favorable_excursion(bars_since, prediction)
mae = calculate_max_adverse_excursion(bars_since, prediction)
hit_tp = check_if_hit_target(bars_since, prediction.take_profit)
hit_sl = check_if_hit_stop(bars_since, prediction.stop_loss)

# Determine outcome
if hit_tp and not hit_sl:
    outcome = "win"
    accuracy_score = 10.0
elif hit_sl:
    outcome = "loss"
    accuracy_score = 0.0
else:
    # Evaluate partial success based on MFE/MAE
    accuracy_score = calculate_partial_score(mfe, mae)

# Update prediction
update_prediction(id, {
    "outcome_evaluated": True,
    "mfe": mfe,
    "mae": mae,
    "actual_outcome": outcome,
    "prediction_accuracy_score": accuracy_score
})
```

---

## 5. Reinforcement Learning System

### Pattern Success Rate Calculation

```sql
-- Get FVG success rate
SELECT
    patterns_detected->>'fvg'->>'type' as fvg_type,
    AVG(prediction_accuracy_score) as avg_accuracy,
    COUNT(*) as sample_size,
    SUM(CASE WHEN actual_outcome = 'win' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as win_rate
FROM trade_predictions
WHERE patterns_detected ? 'fvg'
  AND outcome_evaluated = TRUE
GROUP BY fvg_type;
```

### Confidence Calibration

Compare predicted confidence vs actual outcomes:
```python
# If FVG confidence=8.5 but only 50% win rate → recalibrate scoring
# Adjust confidence formula based on historical performance
```

### Learning Feedback Loop

1. **Weekly Analysis**:
   - Which patterns had highest win rate?
   - What confidence scores were most accurate?
   - Which market conditions produced best results?

2. **Auto-Adjust Scoring**:
   - If bearish FVGs underperform → reduce their confidence by 10%
   - If BoS with high volume overperforms → increase bonus

3. **Prompt Enhancement**:
   - Feed winning pattern characteristics back into system prompt
   - "Recent analysis shows bullish FVGs with >8.0 confidence have 75% success rate"

---

## 6. LLM Response Format with Scores

### Example: "What do you see?" Response
```
📊 BYND @ $0.5685 | Data: 150 bars (7.5/10 quality)

🎯 Bullish FVG at $0.5650-$0.5670 (12 bars ago)
   Confidence: 8.5/10 | Gap: 0.45% | Volume: ✓

📈 Bullish BoS at $0.5600 (18 bars ago)
   Confidence: 7.2/10 | Volume: Strong (1.6x)

✅ Confluence Score: 9.2/10
   FVG + BoS alignment | High probability setup

💡 Suggested Entry: $0.5670 (FVG retest)
   Stop: $0.5620 | Target: $0.5850
   R:R = 1:3.6 | Win Probability: 70-75%

Overall Confidence: 8.4/10
```

### Low Data Warning
```
📊 BYND @ $0.5685 | Data: 45 bars (2.3/10 quality)
⚠️ Limited data (45min of history)

Detected: Possible bullish FVG at $0.5660
Confidence: 4.2/10 (LOW - insufficient history)

💡 Suggestion: Wait for more data or trade with reduced size.
   Risk is higher due to limited price action visibility.
```

---

## 7. Implementation Checklist

✅ FVG confidence scoring
✅ BoS confidence scoring
✅ CHoCH bug fix + confidence scoring
✅ Create `trade_predictions` table (migration ready: migrations/005_trade_predictions.sql)
✅ Add prediction storage module (ai-service/prediction_storage.py)
✅ Add confluence detection logic (detect_pattern_confluence function)
✅ Integrate confluence detection into SMC agent
⬜ Build outcome evaluation job (automated prediction tracking)
⬜ Implement reinforcement learning queries
⬜ Update system prompt with scoring framework
⬜ Create prediction analytics dashboard

---

## Next Steps

✅ ~~Fix CHoCH trend detection bug~~ **DONE** - Fixed inverted trend logic (lines 578-579)
✅ ~~Add confidence scoring to BoS/CHoCH~~ **DONE** - Both now return confidence scores
✅ ~~Create predictions database table~~ **DONE** - Migration ready in migrations/005_trade_predictions.sql
✅ ~~Add confluence detection~~ **DONE** - detect_pattern_confluence() function created

**Remaining Work**:
1. Run database migration: `python run_predictions_migration.py`
2. Integrate prediction storage into agent responses (store every LLM suggestion)
3. Build automated outcome evaluation job (runs periodically to check prediction accuracy)
4. Create RL feedback loop for continuous improvement
5. Update system prompt to emphasize confidence scores and probabilities

**Goal**: Every "what do you see?" response includes:
- ✅ Pattern confidence scores (1-10) - IMPLEMENTED
- ✅ Data quality warnings - IMPLEMENTED
- ⬜ Win probability estimates - Needs prompt engineering
- ⬜ All predictions stored for future learning - Needs integration into chat handler
